"""N-way feature combination coverage analysis.

Computes coverage matrix, identifies gaps, and ranks them by
lexicographic priority ordering with topology connectivity filtering.
"""
from __future__ import annotations

from itertools import combinations


SECURITY_RELEVANT = {"fbo", "buffer_ops", "transform_feedback",
                     "renderbuffer", "sync", "ext_color_buffer_float"}

UBIQUITOUS = {"shader_pipeline", "draw_calls", "attributes", "uniforms",
              "viewport_scissor", "pixel_ops"}


def is_topology_connected(combo, topology):
    """Check if all features in an N-way combo are connected in the topology.

    For N=1: always True.
    For N=2: direct edge check.
    For N>=3: BFS on induced subgraph to check single connected component.
    """
    if len(combo) < 2:
        return True

    edges = set()
    for edge in topology["edges"]:
        pair = tuple(sorted(edge["pair"]))
        edges.add(pair)

    if len(combo) == 2:
        return tuple(sorted(combo)) in edges

    combo_set = set(combo)
    adjacency = {f: set() for f in combo_set}
    for edge in topology["edges"]:
        a, b = edge["pair"]
        if a in combo_set and b in combo_set:
            adjacency[a].add(b)
            adjacency[b].add(a)

    visited = set()
    queue = [combo[0] if isinstance(combo, list) else list(combo)[0]]
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        queue.extend(adjacency[node] - visited)

    return visited == combo_set


def compute_matrix(corpus_features, n=2, interaction_topology=None):
    """Compute n-way feature combination coverage.

    Args:
        corpus_features: dict {seed_name: feature_fingerprint}
            Each fingerprint has "features" (list of str) and
            "methods_per_feature" (dict {feature: [method_names]}).
        n: combination size (2, 3, or 4)
        interaction_topology: parsed interaction_topology.json (optional)

    Returns:
        dict {combo_tuple: {seed_count, distinct_fingerprints, seeds,
                            topology_connected}}
    """
    all_features = sorted(set(
        f for fp in corpus_features.values() for f in fp["features"]))

    matrix = {}
    for combo in combinations(all_features, n):
        combo_key = tuple(sorted(combo))

        if interaction_topology and not is_topology_connected(
                list(combo_key), interaction_topology):
            matrix[combo_key] = {
                "seed_count": 0,
                "distinct_fingerprints": 0,
                "seeds": [],
                "topology_connected": False,
            }
            continue

        seeds_with_combo = [
            f for f, fp in corpus_features.items()
            if all(c in fp["features"] for c in combo)
        ]

        fingerprints = set()
        for f in seeds_with_combo:
            fp = corpus_features[f]
            fp_key = tuple(
                tuple(sorted(fp.get("methods_per_feature", {}).get(c, [])))
                for c in combo_key
            )
            fingerprints.add(fp_key)

        matrix[combo_key] = {
            "seed_count": len(seeds_with_combo),
            "distinct_fingerprints": len(fingerprints),
            "seeds": seeds_with_combo,
            "topology_connected": True,
        }

    return matrix


def identify_gaps(matrix, min_seeds=1):
    """Find combinations below minimum seed threshold."""
    gaps = {}
    for combo, data in matrix.items():
        if data["seed_count"] < min_seeds:
            gaps[combo] = {
                "seed_count": data["seed_count"],
                "topology_connected": data.get("topology_connected", True),
            }
    return gaps


def compute_priority_key(combo, seed_count, depth_levels,
                         interaction_topology=None):
    """Lexicographic priority key. Higher = more important gap.

    Dimensions (most significant first):
      1. ubiquitous_penalty (0=all-ubiq, 1=has non-ubiq)
      2. topology_connected (1=connected, 0=disconnected)
      3. seed_count_bucket (2=zero, 1=thin<=2, 0=covered)
      4. security_count
      5. n_way_preference (-2 > -3 > -4)
      6. depth_deficit (1.0 - avg_depth)
    """
    ubiq = 0 if all(f in UBIQUITOUS for f in combo) else 1

    if interaction_topology:
        connected = 1 if is_topology_connected(list(combo), interaction_topology) else 0
    else:
        connected = 1

    if seed_count == 0:
        seed_bucket = 2
    elif seed_count <= 2:
        seed_bucket = 1
    else:
        seed_bucket = 0

    security_count = sum(1 for f in combo if f in SECURITY_RELEVANT)

    n_way_pref = -len(combo)

    DEPTH_WEIGHT = {"present": 0.0, "meaningful": 0.5, "deep": 1.0}
    if depth_levels:
        avg_depth = sum(DEPTH_WEIGHT.get(d, 0) for d in depth_levels) / len(depth_levels)
        depth_deficit = 1.0 - avg_depth
    else:
        depth_deficit = 1.0

    return (ubiq, connected, seed_bucket, security_count, n_way_pref, depth_deficit)


def priority_label(key):
    """Map priority key to display tier."""
    ubiq, connected, seed_bucket, security_count, n_way_pref, _ = key
    if ubiq == 0:
        return "skip"
    if connected == 0:
        return "low"
    if seed_bucket == 2 and security_count >= 1:
        return "high"
    if seed_bucket == 2:
        return "medium"
    if seed_bucket == 1:
        return "low"
    return "skip"


def merge_seed_into_matrix(baseline_matrix, new_seed_fingerprint, n_way=2):
    """Incrementally update a combination matrix with one new seed.

    O(C(k, n)) where k = features in new seed.
    """
    features = new_seed_fingerprint["features"]
    combos = baseline_matrix.get("combinations", baseline_matrix)

    for n in range(2, min(len(features), n_way) + 1):
        for combo in combinations(sorted(features), n):
            key = tuple(combo)
            if key in combos:
                entry = combos[key]
                entry["seed_count"] += 1
                entry["seeds"].append(new_seed_fingerprint.get("file", "unknown"))

                fp_key = tuple(
                    tuple(sorted(new_seed_fingerprint.get(
                        "methods_per_feature", {}).get(c, [])))
                    for c in key
                )
                existing_fps = entry.setdefault("_fingerprint_set", set())
                existing_fps.add(fp_key)
                entry["distinct_fingerprints"] = len(existing_fps)
                entry["stale"] = True
            else:
                fp_key = tuple(
                    tuple(sorted(new_seed_fingerprint.get(
                        "methods_per_feature", {}).get(c, [])))
                    for c in key
                )
                combos[key] = {
                    "seed_count": 1,
                    "seeds": [new_seed_fingerprint.get("file", "unknown")],
                    "distinct_fingerprints": 1,
                    "_fingerprint_set": {fp_key},
                    "topology_connected": True,
                    "stale": True,
                }

    return baseline_matrix


def generate_matrix_report(matrix, corpus_features, interaction_topology=None):
    """Generate JSON-serializable report from matrix."""
    total = len(matrix)
    covered = sum(1 for d in matrix.values() if d["seed_count"] >= 1)
    uncovered = total - covered

    ubiq_only = sum(1 for combo in matrix
                    if all(f in UBIQUITOUS for f in combo))
    tautological = sum(1 for combo, d in matrix.items()
                       if d.get("topology_connected", True) and d["seed_count"] > 0
                       and _is_tautological(combo))
    disconnected = sum(1 for d in matrix.values()
                       if not d.get("topology_connected", True))
    covered_adjusted = covered - sum(
        1 for combo, d in matrix.items()
        if d["seed_count"] >= 1 and all(f in UBIQUITOUS for f in combo))

    gaps = []
    for combo, data in sorted(matrix.items()):
        if data["seed_count"] == 0 and data.get("topology_connected", True):
            depth_levels = []
            for seed in data.get("seeds", []):
                if seed in corpus_features:
                    for f in combo:
                        d = corpus_features[seed].get("feature_depth", {}).get(f)
                        if d:
                            depth_levels.append(d)
            key = compute_priority_key(
                combo, data["seed_count"], depth_levels, interaction_topology)
            label = priority_label(key)
            if label != "skip":
                gaps.append({
                    "combo": list(combo),
                    "seed_count": data["seed_count"],
                    "priority": label,
                    "topology_connected": True,
                })

    gaps.sort(key=lambda g: {"high": 0, "medium": 1, "low": 2}.get(g["priority"], 3))

    low_diversity = []
    for combo, data in matrix.items():
        if (data["seed_count"] >= 5
                and data.get("distinct_fingerprints", 0) <= 2
                and data.get("topology_connected", True)):
            low_diversity.append({
                "combo": list(combo),
                "seed_count": data["seed_count"],
                "distinct_fingerprints": data["distinct_fingerprints"],
                "note": "high seed count but near-duplicate coverage",
            })

    return {
        "total": total,
        "covered": covered,
        "covered_adjusted": covered_adjusted,
        "uncovered": uncovered,
        "tautological_pairs": tautological,
        "ubiquitous_only_pairs": ubiq_only,
        "topology_disconnected": disconnected,
        "gaps": gaps,
        "low_diversity": low_diversity,
        "phase2_enriched": False,
    }


_TAUTOLOGICAL_PAIRS = {
    frozenset(("draw_calls", "instancing")),
    frozenset(("integer_textures", "draw_calls")),
    frozenset(("fbo", "texture_arrays")),
    frozenset(("texture_3d", "texture_arrays")),
}


def _is_tautological(combo):
    if len(combo) == 2:
        return frozenset(combo) in _TAUTOLOGICAL_PAIRS
    return False
