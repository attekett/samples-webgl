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
    """Split a category's gate items into required (core) and bonus (optional).

    Items are strings: methods, 'method(CONST)' call-constant pairs,
    'gl.CONST', 'glsl:<name>', markers verbatim and getExtension('X'). The
    required list can satisfy every gate the category has; for any-of gates
    the first JSON entry is the representative. Methods: first
    REQUIRED_METHOD_CAP required.
    """
    required, bonus = [], []

    def add(lst, item):
        if item not in required and item not in bonus:
            lst.append(item)

    def pairs(key):
        return [f"{m}({c})" for m, cs in category_def.get(key, {}).items()
                for c in cs]

    methods = list(category_def.get("methods", []))
    markers = list(category_def.get("markers", []))
    extension_methods = list(category_def.get("extension_methods", []))

    rcc = pairs("requires_call_constant")
    if rcc:
        add(required, rcc[0])
        for item in rcc[1:]:
            add(bonus, item)
        first = next(iter(category_def["requires_call_constant"]))
        methods = [m for m in methods if m != first]

    for i, m in enumerate(methods):
        add(required if i < REQUIRED_METHOD_CAP else bonus, m)
    for m in extension_methods + list(category_def.get("glsl_functions", [])):
        add(required, m)

    for item in pairs("match_if_call_constant"):
        add(bonus, item)

    if not rcc:
        consts = list(category_def.get("constants", []))
        if category_def.get("requires_any_constant"):
            n = 1
        else:
            n = category_def.get("min_constants_for_match", 0)
        for c in consts[:n]:
            add(required, f"gl.{c}")

    glsl = ([f"glsl:{n}" for n in category_def.get("glsl_patterns", {})]
            + [f"glsl:{v}" for v in category_def.get("glsl_variables", [])])
    n = category_def.get("min_glsl_patterns_for_match", 0)
    for i, item in enumerate(glsl):
        add(required if i < n else bonus, item)

    for i, item in enumerate(markers):
        add(required if i == 0 and not methods and not rcc else bonus, item)

    exts = category_def.get("extensions")
    if (category_def.get("requires_any_extension") and exts
            and not any(m in required for m in extension_methods)):
        required.insert(0, "getExtension('" + exts[0] + "')")

    return required, bonus


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


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
MAX_FEATURE_PER_BATCH = 3


def plan_batches(recipes, max_batches=4, max_per_batch=5):
    """Distribute recipes across batches with feature concentration cap.

    Args:
        recipes: list of recipe dicts (must have "priority" and
            "target_features" keys).
        max_batches: int — at most this many batches emitted.
        max_per_batch: int — at most this many recipes per batch.

    Returns:
        list[dict] of batches, each shaped:
            {"batch_id": int, "recipes": [recipe, ...]}
        Earliest batch first. Recipes that exceed the per-feature cap on
        a given batch defer to the next.
    """
    if not recipes:
        return []

    sorted_recipes = sorted(
        recipes,
        key=lambda r: (PRIORITY_ORDER.get(r.get("priority"), 99),
                       r.get("recipe_id", "")),
    )

    batches = []
    remaining = list(sorted_recipes)

    for batch_idx in range(max_batches):
        if not remaining:
            break
        batch = []
        feature_counts = {}
        deferred = []
        for recipe in remaining:
            if len(batch) >= max_per_batch:
                deferred.append(recipe)
                continue
            over_limit = any(
                feature_counts.get(f, 0) >= MAX_FEATURE_PER_BATCH
                for f in recipe["target_features"]
            )
            if over_limit:
                deferred.append(recipe)
                continue
            batch.append(recipe)
            for f in recipe["target_features"]:
                feature_counts[f] = feature_counts.get(f, 0) + 1
        if batch:
            batches.append({"batch_id": batch_idx + 1, "recipes": batch})
        remaining = deferred

    return batches


def generate_recipes(matrix_report, corpus_features, categories_config,
                     interaction_topology, n_way, max_recipes=20,
                     max_batches=4, max_per_batch=5):
    """Top-level entry: matrix report → recipes JSON.

    Args:
        matrix_report: dict from generate_matrix_report() — must contain a
            "gaps" list. Each gap has {combo, priority, seed_count,
            topology_connected}.
        corpus_features: {filepath: fingerprint} for reference selection.
        categories_config: parsed feature_categories.json.
        interaction_topology: parsed interaction_topology.json.
        n_way: int — N for the N-way analysis the matrix was built with.
            Passed in from the CLI (do not derive from gap shapes — gap
            list could be empty or hand-built).
        max_recipes: int — emit at most this many recipes after filtering.
        max_batches: int — at most this many batches.
        max_per_batch: int — at most this many recipes per batch.

    Returns:
        dict with keys:
            n_way, total_gaps_considered, recipes, batches,
            missing_categories (sorted list — features the recipes target
            that have no entry in categories_config or no methods).
    """
    gaps_in = matrix_report.get("gaps", [])
    extension_categories = derive_extension_categories(categories_config)

    relevant = [g for g in gaps_in
                if is_relevant(g["combo"], extension_categories)]

    missing = set()
    recipes = []
    for idx, gap in enumerate(relevant[:max_recipes], start=1):
        recipe_id = f"gap_{idx:03d}"
        recipe = build_recipe(
            gap, categories_config, interaction_topology,
            corpus_features, recipe_id,
            missing_categories=missing,
        )
        recipes.append(recipe)

    batches_full = plan_batches(
        recipes, max_batches=max_batches, max_per_batch=max_per_batch,
    )
    batches = [
        {"batch_id": b["batch_id"],
         "recipe_ids": [r["recipe_id"] for r in b["recipes"]]}
        for b in batches_full
    ]

    return {
        "n_way": n_way,
        "total_gaps_considered": len(gaps_in),
        "recipes": recipes,
        "batches": batches,
        "missing_categories": sorted(missing),
    }
