"""Gap-driven seed recipe generation.

Consumes combination matrix gap output and produces structured recipe JSON
that an LLM (or seed author) can use to write seeds covering specific
3-way feature combinations.
"""
from __future__ import annotations

from api_audit.combination_matrix import UBIQUITOUS, SECURITY_RELEVANT


def _load_categories(categories_config):
    """Accept dict with or without outer 'categories' wrapping; return inner."""
    if isinstance(categories_config, dict) and "categories" in categories_config:
        return categories_config["categories"]
    return categories_config


def derive_extension_categories(categories_config):
    """Return the set of category names that have a non-empty `extensions` list.

    Reading this from feature_categories.json (instead of a hardcoded set)
    means adding a new ext_* category to the JSON automatically participates
    in the relevance filter without code changes.
    """
    cats = _load_categories(categories_config)
    return {name for name, defn in cats.items()
            if defn.get("extensions")}


def is_relevant(combo, extension_categories):
    """Filter out low-value gaps before recipe generation.

    Skip if:
      - every feature is in UBIQUITOUS (combo carries no signal)
      - combo is extension-only AND contains nothing from SECURITY_RELEVANT

    Args:
        combo: iterable of feature names.
        extension_categories: set of category names flagged as extensions
            (derive from categories_config via derive_extension_categories).
    """
    combo_set = set(combo)
    if all(f in UBIQUITOUS for f in combo_set):
        return False
    non_ext = [f for f in combo_set if f not in extension_categories]
    if not non_ext and not (combo_set & SECURITY_RELEVANT):
        return False
    return True


def select_references(target_features, corpus_features, max_refs=3):
    """Pick reference seeds ranked by (overlap_count, depth_score) descending.

    Args:
        target_features: list[str] — features the recipe wants to cover.
        corpus_features: dict[str, dict] — {filepath: fingerprint} where each
            fingerprint has "features" (list[str]) and "depth_ratios"
            (dict[str, float]).
        max_refs: int — cap on returned references.

    Returns:
        list[str] of filepaths sorted from best to worst match. Empty if
        no seed has any overlap with target_features.
    """
    target_set = set(target_features)
    scored = []
    for filepath, fp in corpus_features.items():
        overlap = len(target_set & set(fp.get("features", [])))
        if overlap == 0:
            continue
        depth_score = sum(
            fp.get("depth_ratios", {}).get(f, 0.0) for f in target_set
        )
        scored.append((overlap, depth_score, filepath))
    scored.sort(reverse=True)
    return [filepath for _, _, filepath in scored[:max_refs]]


REQUIRED_METHOD_CAP = 5


def split_required_bonus_methods(category_def):
    """Split a category's methods into required (core) and bonus (optional).

    Heuristic: first REQUIRED_METHOD_CAP methods are required, remainder is
    bonus. extension_methods and glsl_functions are always required because
    the category match rules depend on them.
    """
    methods = list(category_def.get("methods", []))
    extension_methods = list(category_def.get("extension_methods", []))
    glsl_functions = list(category_def.get("glsl_functions", []))

    required_methods = methods[:REQUIRED_METHOD_CAP]
    bonus_methods = methods[REQUIRED_METHOD_CAP:]

    required = required_methods + extension_methods + glsl_functions
    return required, bonus_methods


SEED_CONSTRAINTS = {
    "tier1_vars": {"min": 5, "max": 8},
    "tier3_enums": {"min": 4, "max": 6},
    "try_catch_blocks": {"min": 6, "max": 10},
    "line_repetition_patterns": {"min": 3},
    "total_lines": {"min": 150, "max": 300},
}


def build_recipe(gap, categories_config, interaction_topology,
                 corpus_features, recipe_id, missing_categories=None):
    """Build a single recipe from one gap entry.

    Args:
        gap: dict with keys {combo, priority, seed_count, topology_connected}
            (from matrix report).
        categories_config: parsed feature_categories.json
            (either {"categories": {...}} or the inner dict).
        interaction_topology: parsed interaction_topology.json
            (with "edges" list).
        corpus_features: {filepath: fingerprint} from feature_detection.
        recipe_id: stable string ID like "gap_001".
        missing_categories: optional set; if provided, this function appends
            target features that have no category definition or no methods.
            Lets the caller surface a single warning at the end.

    Returns:
        dict matching the recipe schema in the plan header.
    """
    categories = _load_categories(categories_config)
    target = sorted(gap["combo"])

    required = {}
    bonus = {}
    for feature in target:
        cat_def = categories.get(feature)
        if cat_def is None:
            if missing_categories is not None:
                missing_categories.add(feature)
            required[feature] = []
            bonus[feature] = []
            continue
        req, bon = split_required_bonus_methods(cat_def)
        if not req and missing_categories is not None:
            missing_categories.add(feature)
        required[feature] = req
        bonus[feature] = bon

    target_set = set(target)
    edges = []
    for edge in interaction_topology.get("edges", []):
        pair = edge.get("pair", [])
        if len(pair) == 2 and set(pair) <= target_set:
            edges.append({
                "pair": list(pair),
                "relationship": edge.get("relationship", ""),
            })

    refs = select_references(target, corpus_features, max_refs=3)

    reason = f"Uncovered {len(target)}-way: {' + '.join(target)}"

    return {
        "recipe_id": recipe_id,
        "priority": gap.get("priority", "medium"),
        "target_features": target,
        "topology_connected": gap.get("topology_connected", True),
        "reason": reason,
        "required_methods": required,
        "bonus_methods": bonus,
        "topology_edges": edges,
        "seed_constraints": dict(SEED_CONSTRAINTS),
        "reference_seeds": refs,
    }
