# gap_spec Recipe Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `scripts/api_audit/gap_spec.py` plus CLI flags so the audit pipeline can emit structured seed recipes from the combination matrix's gap list, completing Step 2 of `docs/plans/2026-02-25-phase2-next-steps-design.md`.

**Architecture:** A new module that consumes `generate_matrix_report()` output and `corpus_features` (already produced by the existing pipeline), filters gaps for relevance, builds per-recipe specifications by joining gap data with `feature_categories.json` and `interaction_topology.json`, picks reference seeds by feature-overlap score, distributes recipes into batches with a per-feature concentration cap, and emits a single JSON file. The CLI gains `--gap-recipes`, `--max-recipes`, `--max-batches`, `--max-per-batch` flags.

**Tech Stack:** Python 3, pytest (`scripts/api_audit/tests/`), existing modules in `scripts/api_audit/`, JSON config in `docs/feature_categories.json` and `docs/interaction_topology.json`.

---

## Test command

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

Targeted run for this plan's new tests:

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py -v
```

End-to-end smoke after Task 7:

```bash
cd /home/attekett/git/samples-webgl && PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix.json \
  --gap-recipes /tmp/recipes.json \
  --n-way 3
```

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `scripts/api_audit/gap_spec.py` | Create | Pure functions: `is_relevant`, `select_references`, `split_required_bonus_methods`, `build_recipe`, `plan_batches`, `generate_recipes` |
| `scripts/api_audit/__main__.py` | Modify (lines 107-308) | Add CLI flags + call `generate_recipes` when `--gap-recipes` provided |
| `scripts/api_audit/tests/test_gap_spec.py` | Create | Unit + integration tests (mirror `test_combination_matrix.py` style) |

No changes to `feature_categories.json`, `interaction_topology.json`, or any other module. The existing `combination_matrix.py` already exposes `UBIQUITOUS`, `SECURITY_RELEVANT`, `priority_label`, `compute_priority_key` — reuse them.

---

## Recipe JSON Schema (target output)

This is what `--gap-recipes recipes.json` must produce. Every Task aligns to this shape. The `required_methods` / `bonus_methods` lists below are illustrative only — actual contents come from the first-5 split of each category's `methods` array in `docs/feature_categories.json`, which may differ in ordering from this example.

```json
{
  "generated_from_matrix": "/tmp/matrix.json",
  "n_way": 3,
  "total_gaps_considered": 50,
  "missing_categories": [],
  "recipes": [
    {
      "recipe_id": "gap_001",
      "priority": "high",
      "target_features": ["ext_float_textures", "fbo", "sampler"],
      "topology_connected": true,
      "reason": "Uncovered 3-way: ext_float_textures + fbo + sampler",
      "required_methods": {
        "ext_float_textures": ["getExtension"],
        "fbo": ["createFramebuffer", "bindFramebuffer", "deleteFramebuffer", "framebufferTexture2D", "framebufferTextureLayer"],
        "sampler": ["createSampler", "bindSampler", "samplerParameteri", "samplerParameterf", "deleteSampler"]
      },
      "bonus_methods": {
        "ext_float_textures": [],
        "fbo": ["framebufferRenderbuffer", "checkFramebufferStatus", "blitFramebuffer", "readBuffer", "invalidateFramebuffer", "invalidateSubFramebuffer"],
        "sampler": ["getSamplerParameter", "isSampler"]
      },
      "topology_edges": [
        {"pair": ["ext_float_textures", "fbo"], "relationship": "Float texture as FBO color attachment"},
        {"pair": ["ext_float_textures", "sampler"], "relationship": "OES_texture_float_linear filtering"}
      ],
      "seed_constraints": {
        "tier1_vars": {"min": 5, "max": 8},
        "tier3_enums": {"min": 4, "max": 6},
        "try_catch_blocks": {"min": 6, "max": 10},
        "line_repetition_patterns": {"min": 3},
        "total_lines": {"min": 150, "max": 300}
      },
      "reference_seeds": ["agent_outputs/mutation_b42_s3_fbo_sampler.html"]
    }
  ],
  "batches": [
    {"batch_id": 1, "recipe_ids": ["gap_001", "gap_004", "..."]},
    {"batch_id": 2, "recipe_ids": ["..."]}
  ]
}
```

`plan_batches()` internally returns `{"batch_id": int, "recipes": [recipe, ...]}` (full recipes for testability); `generate_recipes()` then projects each batch's `recipes` to a `recipe_ids` list before emitting the JSON. The two-stage shape is intentional — tests for `plan_batches` assert against full recipes; the on-disk schema uses ID lists.

---

## Task 1: Create `gap_spec.py` skeleton + the relevance filter

**Files:**
- Create: `scripts/api_audit/gap_spec.py`
- Create: `scripts/api_audit/tests/test_gap_spec.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/api_audit/tests/test_gap_spec.py`:

```python
"""Tests for gap_spec module — recipe generation from combination gaps."""
import pytest

from api_audit.gap_spec import is_relevant, derive_extension_categories


EXT_CATS = {"ext_float_textures", "ext_color_buffer_float",
            "ext_draw_buffers_indexed", "ext_texture_filter_anisotropic",
            "ext_compressed_textures", "ext_disjoint_timer_query"}


class TestDeriveExtensionCategories:
    def test_picks_categories_with_non_empty_extensions(self):
        cfg = {"categories": {
            "fbo": {"methods": ["createFramebuffer"]},
            "ext_float_textures": {"methods": ["getExtension"],
                                   "extensions": ["OES_texture_float"]},
            "ext_empty_list": {"extensions": []},
            "ext_anisotropic": {"extensions": ["EXT_texture_filter_anisotropic"]},
        }}
        assert derive_extension_categories(cfg) == {
            "ext_float_textures", "ext_anisotropic",
        }

    def test_accepts_flat_dict(self):
        flat = {"ext_float_textures": {"extensions": ["OES_texture_float"]}}
        assert derive_extension_categories(flat) == {"ext_float_textures"}


class TestIsRelevant:
    def test_all_ubiquitous_combo_skipped(self):
        # Every feature is in UBIQUITOUS → not relevant for recipes
        assert is_relevant(
            ["shader_pipeline", "draw_calls", "uniforms"], EXT_CATS) is False

    def test_combo_with_one_non_ubiquitous_kept(self):
        # fbo is non-ubiquitous → relevant
        assert is_relevant(
            ["shader_pipeline", "draw_calls", "fbo"], EXT_CATS) is True

    def test_extension_only_combo_without_security_skipped(self):
        # All three are extension categories, no security-relevant feature
        assert is_relevant(["ext_float_textures",
                            "ext_texture_filter_anisotropic",
                            "ext_compressed_textures"], EXT_CATS) is False

    def test_extension_only_combo_with_security_kept(self):
        # ext_color_buffer_float is in SECURITY_RELEVANT
        assert is_relevant(["ext_color_buffer_float",
                            "ext_float_textures",
                            "ext_compressed_textures"], EXT_CATS) is True

    def test_normal_mixed_combo_kept(self):
        assert is_relevant(["fbo", "sampler", "texture_ops"], EXT_CATS) is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py -v
```

Expected: ImportError / ModuleNotFoundError on `api_audit.gap_spec`.

- [ ] **Step 3: Implement `gap_spec.py` with `is_relevant`**

Create `scripts/api_audit/gap_spec.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/gap_spec.py scripts/api_audit/tests/test_gap_spec.py
git commit -m "feat(gap_spec): add is_relevant gap filter"
```

---

## Task 2: Reference-seed selection by overlap + depth score

**Files:**
- Modify: `scripts/api_audit/gap_spec.py`
- Modify: `scripts/api_audit/tests/test_gap_spec.py`

- [ ] **Step 1: Write the failing tests**

Append to `scripts/api_audit/tests/test_gap_spec.py`:

```python
from api_audit.gap_spec import select_references


class TestSelectReferences:
    def test_picks_seed_with_most_overlap(self):
        corpus = {
            "seedA": {"features": ["fbo"], "depth_ratios": {"fbo": 0.5}},
            "seedB": {"features": ["fbo", "sampler"],
                      "depth_ratios": {"fbo": 0.5, "sampler": 0.5}},
            "seedC": {"features": ["fbo", "sampler", "ext_float_textures"],
                      "depth_ratios": {"fbo": 1.0, "sampler": 1.0, "ext_float_textures": 1.0}},
        }
        target = ["fbo", "sampler", "ext_float_textures"]
        refs = select_references(target, corpus, max_refs=1)
        assert refs == ["seedC"]

    def test_skips_seeds_with_no_overlap(self):
        corpus = {
            "seedX": {"features": ["draw_calls"], "depth_ratios": {"draw_calls": 1.0}},
        }
        refs = select_references(["fbo", "sampler"], corpus, max_refs=3)
        assert refs == []

    def test_breaks_ties_by_depth_score(self):
        corpus = {
            "shallow": {"features": ["fbo", "sampler"],
                        "depth_ratios": {"fbo": 0.1, "sampler": 0.1}},
            "deep": {"features": ["fbo", "sampler"],
                     "depth_ratios": {"fbo": 0.9, "sampler": 0.9}},
        }
        refs = select_references(["fbo", "sampler"], corpus, max_refs=1)
        assert refs == ["deep"]

    def test_caps_at_max_refs(self):
        corpus = {
            f"seed{i}": {"features": ["fbo"], "depth_ratios": {"fbo": 0.5}}
            for i in range(10)
        }
        refs = select_references(["fbo"], corpus, max_refs=3)
        assert len(refs) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py::TestSelectReferences -v
```

Expected: ImportError on `select_references`.

- [ ] **Step 3: Add `select_references` to `gap_spec.py`**

Append to `scripts/api_audit/gap_spec.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py -v
```

Expected: 11 passed (7 from Task 1 + 4 new).

- [ ] **Step 5: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/gap_spec.py scripts/api_audit/tests/test_gap_spec.py
git commit -m "feat(gap_spec): add reference seed selection by overlap and depth"
```

---

## Task 3: Required vs bonus method split

**Files:**
- Modify: `scripts/api_audit/gap_spec.py`
- Modify: `scripts/api_audit/tests/test_gap_spec.py`

The recipe schema separates `required_methods` (core methods every seed must call to actually exercise the feature) from `bonus_methods` (additional optional methods). For each feature category, take the **first 5 listed methods** as required and the remainder as bonus. Categories list methods in order of importance by hand-curation convention. `extension_methods` (called on the extension object, not `gl`) are always required because the category's match rule depends on them. `glsl_functions` are added to required when present.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/api_audit/tests/test_gap_spec.py`:

```python
from api_audit.gap_spec import split_required_bonus_methods


class TestSplitMethods:
    def test_short_list_all_required(self):
        cat_def = {"methods": ["createA", "bindA", "deleteA"]}
        required, bonus = split_required_bonus_methods(cat_def)
        assert required == ["createA", "bindA", "deleteA"]
        assert bonus == []

    def test_long_list_split_at_five(self):
        cat_def = {
            "methods": ["m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8"]
        }
        required, bonus = split_required_bonus_methods(cat_def)
        assert required == ["m1", "m2", "m3", "m4", "m5"]
        assert bonus == ["m6", "m7", "m8"]

    def test_extension_methods_added_to_required(self):
        cat_def = {
            "methods": ["getExtension"],
            "extension_methods": ["drawArraysInstancedANGLE"],
        }
        required, bonus = split_required_bonus_methods(cat_def)
        assert "drawArraysInstancedANGLE" in required
        assert "getExtension" in required

    def test_glsl_functions_added_to_required(self):
        cat_def = {
            "methods": [],
            "glsl_functions": ["texture", "textureLod"],
        }
        required, bonus = split_required_bonus_methods(cat_def)
        assert "texture" in required
        assert "textureLod" in required

    def test_missing_methods_key_returns_empty(self):
        required, bonus = split_required_bonus_methods({})
        assert required == []
        assert bonus == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py::TestSplitMethods -v
```

Expected: ImportError on `split_required_bonus_methods`.

- [ ] **Step 3: Add `split_required_bonus_methods` to `gap_spec.py`**

Append to `scripts/api_audit/gap_spec.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py -v
```

Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/gap_spec.py scripts/api_audit/tests/test_gap_spec.py
git commit -m "feat(gap_spec): split feature methods into required and bonus"
```

---

## Task 4: Build a single recipe

**Files:**
- Modify: `scripts/api_audit/gap_spec.py`
- Modify: `scripts/api_audit/tests/test_gap_spec.py`

This is the core join: gap (from matrix) + categories config + topology + corpus → one recipe dict.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/api_audit/tests/test_gap_spec.py`:

```python
from api_audit.gap_spec import build_recipe


class TestBuildRecipe:
    def _categories(self):
        return {
            "categories": {
                "fbo": {
                    "methods": ["createFramebuffer", "bindFramebuffer",
                                "framebufferTexture2D", "checkFramebufferStatus",
                                "blitFramebuffer", "readBuffer",
                                "deleteFramebuffer"],
                },
                "sampler": {
                    "methods": ["createSampler", "bindSampler",
                                "samplerParameteri", "deleteSampler",
                                "samplerParameterf"],
                },
                "ext_float_textures": {
                    "methods": ["getExtension"],
                    "extensions": ["OES_texture_float", "EXT_color_buffer_float"],
                },
            }
        }

    def _topology(self):
        return {
            "edges": [
                {"pair": ["fbo", "sampler"],
                 "relationship": "Sampler bound to texture read from FBO"},
                {"pair": ["ext_float_textures", "fbo"],
                 "relationship": "Float texture as FBO color attachment"},
            ]
        }

    def test_recipe_has_required_keys(self):
        gap = {"combo": ["fbo", "sampler", "ext_float_textures"],
               "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features={}, recipe_id="gap_001"
        )
        assert recipe["recipe_id"] == "gap_001"
        assert recipe["priority"] == "high"
        assert recipe["target_features"] == ["ext_float_textures", "fbo", "sampler"]
        assert recipe["topology_connected"] is True
        assert "reason" in recipe
        assert "required_methods" in recipe
        assert "bonus_methods" in recipe
        assert "topology_edges" in recipe
        assert "seed_constraints" in recipe
        assert "reference_seeds" in recipe

    def test_recipe_required_methods_per_feature(self):
        gap = {"combo": ["fbo", "sampler"], "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features={}, recipe_id="gap_002"
        )
        # fbo has 7 methods, top 5 are required
        assert recipe["required_methods"]["fbo"][:5] == [
            "createFramebuffer", "bindFramebuffer",
            "framebufferTexture2D", "checkFramebufferStatus",
            "blitFramebuffer",
        ]
        assert recipe["bonus_methods"]["fbo"] == [
            "readBuffer", "deleteFramebuffer"
        ]

    def test_recipe_topology_edges_filtered_to_combo(self):
        gap = {"combo": ["fbo", "sampler"], "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features={}, recipe_id="gap_003"
        )
        # Only the fbo↔sampler edge involves both target features
        assert len(recipe["topology_edges"]) == 1
        assert sorted(recipe["topology_edges"][0]["pair"]) == ["fbo", "sampler"]

    def test_recipe_includes_reference_seeds(self):
        corpus = {
            "agent_outputs/seedA.html": {
                "features": ["fbo", "sampler"],
                "depth_ratios": {"fbo": 0.8, "sampler": 0.8},
            },
        }
        gap = {"combo": ["fbo", "sampler"], "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features=corpus, recipe_id="gap_004"
        )
        assert recipe["reference_seeds"] == ["agent_outputs/seedA.html"]

    def test_recipe_seed_constraints_are_static(self):
        gap = {"combo": ["fbo", "sampler"], "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features={}, recipe_id="gap_005"
        )
        c = recipe["seed_constraints"]
        assert c["tier1_vars"] == {"min": 5, "max": 8}
        assert c["tier3_enums"] == {"min": 4, "max": 6}
        assert c["try_catch_blocks"] == {"min": 6, "max": 10}
        assert c["line_repetition_patterns"] == {"min": 3}
        assert c["total_lines"] == {"min": 150, "max": 300}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py::TestBuildRecipe -v
```

Expected: ImportError on `build_recipe`.

- [ ] **Step 3: Add `build_recipe` to `gap_spec.py`**

Append to `scripts/api_audit/gap_spec.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py -v
```

Expected: 21 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/gap_spec.py scripts/api_audit/tests/test_gap_spec.py
git commit -m "feat(gap_spec): build per-recipe spec from gap + topology + corpus"
```

---

## Task 5: Batch planning with feature concentration cap

**Files:**
- Modify: `scripts/api_audit/gap_spec.py`
- Modify: `scripts/api_audit/tests/test_gap_spec.py`

The batch planner distributes recipes across batches so that no single feature dominates one batch (cap of 3 recipes per feature per batch). Higher-priority recipes go first. Recipes that would exceed the cap are deferred to the next batch.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/api_audit/tests/test_gap_spec.py`:

```python
from api_audit.gap_spec import plan_batches


class TestPlanBatches:
    def _recipe(self, rid, features, priority="high"):
        return {
            "recipe_id": rid,
            "priority": priority,
            "target_features": features,
        }

    def test_high_priority_packed_first(self):
        recipes = [
            self._recipe("a", ["fbo"], priority="medium"),
            self._recipe("b", ["sampler"], priority="high"),
            self._recipe("c", ["renderbuffer"], priority="high"),
        ]
        batches = plan_batches(recipes, max_batches=1, max_per_batch=2)
        assert len(batches) == 1
        ids = [r["recipe_id"] for r in batches[0]["recipes"]]
        # Both high-priority recipes go in batch 1
        assert "b" in ids and "c" in ids
        assert "a" not in ids

    def test_feature_concentration_cap(self):
        # 4 recipes all targeting fbo — only 3 fit per batch
        recipes = [
            self._recipe(f"r{i}", ["fbo", f"other{i}"]) for i in range(4)
        ]
        batches = plan_batches(recipes, max_batches=2, max_per_batch=5)
        first_ids = [r["recipe_id"] for r in batches[0]["recipes"]]
        second_ids = [r["recipe_id"] for r in batches[1]["recipes"]]
        assert len(first_ids) == 3
        assert len(second_ids) == 1

    def test_max_per_batch_respected(self):
        recipes = [
            self._recipe(f"r{i}", [f"feat{i}"]) for i in range(10)
        ]
        batches = plan_batches(recipes, max_batches=2, max_per_batch=3)
        assert len(batches[0]["recipes"]) == 3
        assert len(batches[1]["recipes"]) == 3

    def test_max_batches_respected(self):
        recipes = [
            self._recipe(f"r{i}", [f"feat{i}"]) for i in range(20)
        ]
        batches = plan_batches(recipes, max_batches=2, max_per_batch=3)
        assert len(batches) == 2

    def test_empty_recipes_returns_empty(self):
        assert plan_batches([], max_batches=4, max_per_batch=5) == []

    def test_batch_id_starts_at_1(self):
        recipes = [self._recipe("r1", ["fbo"])]
        batches = plan_batches(recipes, max_batches=4, max_per_batch=5)
        assert batches[0]["batch_id"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py::TestPlanBatches -v
```

Expected: ImportError on `plan_batches`.

- [ ] **Step 3: Add `plan_batches` to `gap_spec.py`**

Append to `scripts/api_audit/gap_spec.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py -v
```

Expected: 27 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/gap_spec.py scripts/api_audit/tests/test_gap_spec.py
git commit -m "feat(gap_spec): plan recipe batches with feature concentration cap"
```

---

## Task 6: Top-level `generate_recipes` orchestrator

**Files:**
- Modify: `scripts/api_audit/gap_spec.py`
- Modify: `scripts/api_audit/tests/test_gap_spec.py`

This stitches the pieces together: take a matrix report (output of `generate_matrix_report`), filter gaps via `is_relevant`, build recipes, plan batches, and return the final JSON-shaped dict.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/api_audit/tests/test_gap_spec.py`:

```python
from api_audit.gap_spec import generate_recipes


class TestGenerateRecipes:
    def _matrix_report(self):
        return {
            "total": 100,
            "covered": 50,
            "uncovered": 50,
            "gaps": [
                {"combo": ["fbo", "sampler", "ext_float_textures"],
                 "priority": "high", "seed_count": 0,
                 "topology_connected": True},
                {"combo": ["shader_pipeline", "draw_calls", "uniforms"],
                 "priority": "low", "seed_count": 0,
                 "topology_connected": True},
                {"combo": ["fbo", "renderbuffer"],
                 "priority": "high", "seed_count": 0,
                 "topology_connected": True},
            ],
        }

    def _categories(self):
        return {
            "categories": {
                "fbo": {"methods": ["createFramebuffer", "bindFramebuffer"]},
                "sampler": {"methods": ["createSampler", "bindSampler"]},
                "ext_float_textures": {"methods": ["getExtension"]},
                "renderbuffer": {"methods": ["createRenderbuffer"]},
                "shader_pipeline": {"methods": ["createProgram"]},
                "draw_calls": {"methods": ["drawArrays"]},
                "uniforms": {"methods": ["uniform1f"]},
            }
        }

    def _topology(self):
        return {"edges": [
            {"pair": ["fbo", "sampler"], "relationship": "fbo binds sampler"},
            {"pair": ["fbo", "renderbuffer"], "relationship": "fbo holds renderbuffer"},
            {"pair": ["ext_float_textures", "fbo"], "relationship": "float fbo"},
        ]}

    def test_emits_recipes_and_batches(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
            max_recipes=20, max_batches=4, max_per_batch=5,
        )
        assert "recipes" in out
        assert "batches" in out
        assert "n_way" in out
        assert out["n_way"] == 3
        assert "total_gaps_considered" in out
        assert "missing_categories" in out
        assert isinstance(out["recipes"], list)
        assert isinstance(out["batches"], list)

    def test_filters_irrelevant_gaps(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        # All-ubiquitous combo {shader_pipeline, draw_calls, uniforms} dropped
        ids = [r["target_features"] for r in out["recipes"]]
        assert ["draw_calls", "shader_pipeline", "uniforms"] not in ids
        assert sorted(["fbo", "sampler", "ext_float_textures"]) in ids

    def test_assigns_sequential_recipe_ids(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        ids = [r["recipe_id"] for r in out["recipes"]]
        assert ids == sorted(ids)
        assert ids[0].startswith("gap_")

    def test_high_priority_recipes_emitted_before_low(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        priorities = [r["priority"] for r in out["recipes"]]
        # Both relevant gaps in this fixture are "high" — confirm none are low
        assert "low" not in priorities

    def test_max_recipes_caps_output(self):
        # Build a matrix with 10 relevant gaps
        gaps = [
            {"combo": ["fbo", f"feat{i}"], "priority": "high", "seed_count": 0,
             "topology_connected": True}
            for i in range(10)
        ]
        cats = {"categories": {"fbo": {"methods": ["createFramebuffer"]}}}
        for i in range(10):
            cats["categories"][f"feat{i}"] = {"methods": [f"createF{i}"]}
        topo = {"edges": [
            {"pair": ["fbo", f"feat{i}"], "relationship": ""}
            for i in range(10)
        ]}
        out = generate_recipes(
            {"gaps": gaps}, corpus_features={},
            categories_config=cats,
            interaction_topology=topo,
            n_way=2,
            max_recipes=3,
        )
        assert len(out["recipes"]) == 3

    def test_total_gaps_considered_counts_input(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        assert out["total_gaps_considered"] == 3

    def test_missing_categories_surfaced(self):
        # Gap targets a feature with no category definition
        gaps = [{"combo": ["fbo", "nonexistent_feature"],
                 "priority": "high", "seed_count": 0,
                 "topology_connected": True}]
        cats = {"categories": {"fbo": {"methods": ["createFramebuffer"]}}}
        topo = {"edges": [{"pair": ["fbo", "nonexistent_feature"],
                           "relationship": "synthetic"}]}
        out = generate_recipes(
            {"gaps": gaps}, corpus_features={},
            categories_config=cats,
            interaction_topology=topo, n_way=2,
        )
        assert "nonexistent_feature" in out["missing_categories"]

    def test_empty_gaps_returns_empty_recipes(self):
        out = generate_recipes(
            {"gaps": []}, corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        assert out["recipes"] == []
        assert out["batches"] == []
        assert out["total_gaps_considered"] == 0
        assert out["n_way"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py::TestGenerateRecipes -v
```

Expected: ImportError on `generate_recipes`.

- [ ] **Step 3: Add `generate_recipes` to `gap_spec.py`**

Append to `scripts/api_audit/gap_spec.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py -v
```

Expected: 34 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/gap_spec.py scripts/api_audit/tests/test_gap_spec.py
git commit -m "feat(gap_spec): add generate_recipes orchestrator"
```

---

## Task 7: CLI integration

**Files:**
- Modify: `scripts/api_audit/__main__.py` (lines 107-308)
- Modify: `scripts/api_audit/tests/test_gap_spec.py`

Add three CLI flags and call `generate_recipes()` when `--gap-recipes` is provided. The hookpoint is right after `args.combination_matrix` is written (around line 299 of `__main__.py`).

- [ ] **Step 1: Write the failing CLI test**

Append to `scripts/api_audit/tests/test_gap_spec.py`. Uses a tiny synthetic corpus on disk and invokes `main()` directly — fast, no subprocess, no real-corpus dependency:

```python
import json
import sys
from pathlib import Path

import pytest


class TestCLIIntegration:
    def test_main_writes_recipes_json(self, tmp_path, monkeypatch):
        # Tiny synthetic corpus
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        (corpus / "seed1.html").write_text(
            "<html><body><script>"
            "const gl = canvas.getContext('webgl2');"
            "const fb = gl.createFramebuffer();"
            "gl.bindFramebuffer(gl.FRAMEBUFFER, fb);"
            "const s = gl.createSampler();"
            "gl.bindSampler(0, s);"
            "</script></body></html>"
        )

        # Tiny categories config — two real categories so a 2-way matrix exists
        cats = {"categories": {
            "fbo": {"methods": ["createFramebuffer", "bindFramebuffer"],
                    "min_methods_for_match": 1},
            "sampler": {"methods": ["createSampler", "bindSampler"],
                        "min_methods_for_match": 1},
        }}
        cats_path = tmp_path / "cats.json"
        cats_path.write_text(json.dumps(cats))

        topo = {"edges": [{"pair": ["fbo", "sampler"],
                           "relationship": "synthetic"}]}
        topo_path = tmp_path / "topo.json"
        topo_path.write_text(json.dumps(topo))

        # Minimal API surface: only the methods our seed calls
        surface = {"meta": {}, "constants": {},
                   "methods": {"createFramebuffer": {}, "bindFramebuffer": {},
                               "createSampler": {}, "bindSampler": {}},
                   "extensions": {}, "glsl_builtins": {}}
        surface_path = tmp_path / "surface.json"
        surface_path.write_text(json.dumps(surface))

        matrix_path = tmp_path / "matrix.json"
        recipes_path = tmp_path / "recipes.json"

        monkeypatch.setattr(sys, "argv", [
            "api_audit",
            "--surface", str(surface_path),
            "--corpus-dirs", str(corpus),
            "--feature-categories", str(cats_path),
            "--interaction-topology", str(topo_path),
            "--combination-matrix", str(matrix_path),
            "--gap-recipes", str(recipes_path),
            "--cache-dir", str(tmp_path / "cache"),
            "--n-way", "2",
            "--max-recipes", "5",
        ])

        from api_audit.__main__ import main
        main()

        assert recipes_path.exists()
        data = json.loads(recipes_path.read_text())
        assert "recipes" in data
        assert "batches" in data
        assert "n_way" in data
        assert data["n_way"] == 2
        assert "missing_categories" in data
        assert "generated_from_matrix" in data
        assert len(data["recipes"]) <= 5
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py::TestCLIIntegration -v
```

Expected: argparse error — unrecognized arguments `--gap-recipes` / `--max-recipes`.

- [ ] **Step 3: Add CLI flags to `__main__.py`**

In `scripts/api_audit/__main__.py`, locate the `argparse.ArgumentParser` block (lines 108-132). Add four arguments after the existing `--baseline` argument:

```python
    parser.add_argument('--gap-recipes', type=Path, default=None,
                        help='Output gap recipes JSON path')
    parser.add_argument('--max-recipes', type=int, default=20,
                        help='Maximum recipes to emit (default: 20)')
    parser.add_argument('--max-batches', type=int, default=4,
                        help='Maximum batches to plan (default: 4)')
    parser.add_argument('--max-per-batch', type=int, default=5,
                        help='Maximum recipes per batch (default: 5)')
```

- [ ] **Step 4: Wire `generate_recipes` into the corpus-mode pipeline**

Still in `scripts/api_audit/__main__.py`, locate the block that writes the combination matrix (search for `print(f"Combination matrix written to {args.combination_matrix}")`). Immediately **after** that print statement and the gap-counting print block (i.e. after line ~306, before the closing of the `if args.feature_categories:` block), insert:

```python
                if args.gap_recipes:
                    from api_audit.gap_spec import generate_recipes

                    recipes_data = generate_recipes(
                        report_matrix,
                        corpus_features,
                        categories_config,
                        topology if topology is not None else {"edges": []},
                        n_way=n,
                        max_recipes=args.max_recipes,
                        max_batches=args.max_batches,
                        max_per_batch=args.max_per_batch,
                    )
                    recipes_data["generated_from_matrix"] = str(args.combination_matrix)

                    args.gap_recipes.parent.mkdir(parents=True, exist_ok=True)
                    args.gap_recipes.write_text(
                        json.dumps(recipes_data, indent=2, default=str))
                    print(f"Gap recipes written to {args.gap_recipes}")
                    print(f"  {len(recipes_data['recipes'])} recipes "
                          f"in {len(recipes_data['batches'])} batches")
                    if recipes_data.get("missing_categories"):
                        print(f"  Warning: {len(recipes_data['missing_categories'])} "
                              f"target features lack category definitions: "
                              f"{', '.join(recipes_data['missing_categories'])}")
```

The indentation must match the surrounding `if args.combination_matrix:` block (16 spaces). `n`, `report_matrix`, `corpus_features`, `categories_config`, and `topology` are already in scope from the existing block (`n` is the `min(args.n_way, 4)` already computed at line 276).

- [ ] **Step 5: Run the failing CLI test to verify it now passes**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_gap_spec.py::TestCLIIntegration -v
```

Expected: 1 passed.

- [ ] **Step 6: Run the full test suite**

```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

Expected: all prior 114 tests still pass + 35 new (Tasks 1-7) = **149 passing**.

- [ ] **Step 7: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/__main__.py scripts/api_audit/tests/test_gap_spec.py
git commit -m "feat(api_audit): add --gap-recipes CLI flag for recipe generation"
```

---

## Task 8: Validate end-to-end on the real corpus

**Files:** none modified — verification only.

The test in Task 7 confirms the CLI runs cleanly. This task confirms the **output shape and content** match expectations against the real corpus.

- [ ] **Step 1: Run the full pipeline against the real corpus**

```bash
cd /home/attekett/git/samples-webgl
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix.json \
  --gap-recipes /tmp/recipes.json \
  --n-way 3 \
  --max-recipes 20
```

Expected stdout includes:
```
Analyzed 402 files
Methods: 225/225 covered
Combination matrix written to /tmp/matrix.json
  3-way: 4060 combos, 467 covered, 3593 uncovered
Gap recipes written to /tmp/recipes.json
  N recipes in M batches
```

- [ ] **Step 2: Inspect the recipes JSON for shape correctness**

```bash
./venv/bin/python -c "
import json
data = json.load(open('/tmp/recipes.json'))
print('Top-level keys:', sorted(data.keys()))
print('Recipe count:', len(data['recipes']))
print('Batch count:', len(data['batches']))
if data['recipes']:
    r = data['recipes'][0]
    print('First recipe keys:', sorted(r.keys()))
    print('First recipe target:', r['target_features'])
    print('First recipe priority:', r['priority'])
    print('First recipe required_methods features:', sorted(r['required_methods'].keys()))
    print('First recipe edge count:', len(r['topology_edges']))
    print('First recipe ref count:', len(r['reference_seeds']))
print('First batch:', data['batches'][0] if data['batches'] else None)
"
```

Expected fields per recipe: `recipe_id`, `priority`, `target_features`, `topology_connected`, `reason`, `required_methods`, `bonus_methods`, `topology_edges`, `seed_constraints`, `reference_seeds`.

- [ ] **Step 3: Sanity-check at least one recipe matches the design example shape**

The current matrix shows 0 active gaps (all 3593 uncovered combos are topology-disconnected per the earlier audit). To force recipes for validation, lower the priority threshold by feeding the `low_diversity` combos as if they were gaps. Run this **read-only** synthetic check:

```bash
./venv/bin/python -c "
import json
from api_audit.gap_spec import generate_recipes

matrix = json.load(open('/tmp/matrix.json'))
report = matrix['3way_combinations']
# Synthesize gaps from low_diversity entries for shape validation
synthetic = {'gaps': [
    {'combo': ld['combo'], 'priority': 'medium', 'seed_count': ld['seed_count']}
    for ld in report.get('low_diversity', [])
]}
cats = json.load(open('docs/feature_categories.json'))
topo = json.load(open('docs/interaction_topology.json'))
out = generate_recipes(synthetic, {}, cats, topo, max_recipes=5)
print(json.dumps(out['recipes'][0] if out['recipes'] else {}, indent=2))
" 2>&1 | head -80
```

Expected: a recipe printed with all schema fields populated. No exceptions.

- [ ] **Step 4: Optional cleanup commit**

If Steps 1-3 surfaced any docstring or default-value tweaks worth committing, do so now. Otherwise no commit needed.

---

## Task 9: Document the new flag in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (Coverage Analysis section)

- [ ] **Step 1: Add `--gap-recipes` to the documented commands**

In `CLAUDE.md`, locate the `### Coverage Analysis` section. After the existing `bash scripts/feature_matrix.sh` and `bash scripts/analyze_corpus.sh` block, append:

```bash
# Generate recipes for closing 3-way gaps
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix.json \
  --gap-recipes /tmp/recipes.json \
  --n-way 3
```

- [ ] **Step 2: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add CLAUDE.md
git commit -m "docs: document --gap-recipes CLI flag in CLAUDE.md"
```

---

## Self-Review Checklist

| Spec requirement | Where in plan |
|---|---|
| `is_relevant(combo)` filter, extension-set derived from JSON | Task 1 |
| Recipe JSON schema (recipe_id, priority, target_features, ...) | Task 4 + plan header schema |
| `select_references(target_features, corpus_features, max_refs=3)` | Task 2 |
| Required vs bonus method split | Task 3 |
| Topology edges filtered to combo | Task 4 |
| `seed_constraints` static block | Task 4 |
| `plan_batches(recipes, max_batches=4, max_per_batch=5)` | Task 5 |
| Feature concentration cap (max 3 per feature per batch) | Task 5 |
| `n_way` passed in (not derived from gaps) | Task 6 |
| Missing-category warning surfaced | Task 6 + Task 7 wiring |
| CLI flags `--gap-recipes`, `--max-recipes`, `--max-batches`, `--max-per-batch` | Task 7 |
| End-to-end: `--gap-recipes recipes.json --combination-matrix matrix.json` | Task 7-8 |

**Type/name consistency check** (verified):
- `is_relevant(combo, extension_categories)` — second arg is the set derived via `derive_extension_categories()`, not a hardcoded constant.
- `select_references(target_features, corpus_features, max_refs=3)` — matches design.
- `build_recipe(gap, categories_config, interaction_topology, corpus_features, recipe_id, missing_categories=None)` — reads `priority` and `topology_connected` from `gap` dict (not hardcoded); optionally records features lacking category definitions.
- `plan_batches(recipes, max_batches=4, max_per_batch=5)` — internal shape `{"batch_id", "recipes"}` (full recipes). `generate_recipes` projects to `{"batch_id", "recipe_ids"}` for the on-disk schema. Documented in plan header.
- `generate_recipes(matrix_report, corpus_features, categories_config, interaction_topology, n_way, max_recipes, max_batches, max_per_batch)` — `n_way` is now a required positional arg sourced from CLI.
- `MAX_FEATURE_PER_BATCH = 3` matches design spec.
- Recipe dict keys exactly match the schema in this plan's header.

**Pre-execution review fixes applied** (from `2026-05-06` Opus review pass):
- Read `priority` / `topology_connected` from gap dict instead of hardcoding.
- `n_way` passed from CLI rather than derived from `gaps[0]`.
- `EXTENSION_CATEGORIES` derived from `feature_categories.json` (no hardcoded duplicate).
- Missing-category set surfaced in output + CLI warning.
- Removed unused `combinations as _combinations` import.
- Replaced subprocess-based corpus-wide CLI test with in-process `main()` invocation on a synthetic tmp_path corpus (fast, deterministic, no real-corpus dependency).
- Documented `recipes` vs `recipe_ids` two-stage shape in plan header.
- Added explicit empty-gaps test (`test_empty_gaps_returns_empty_recipes`).
- Added priority-ordering test (`test_high_priority_recipes_emitted_before_low`).
- Added `derive_extension_categories` tests including flat-dict acceptance.

**Out-of-scope (deferred)**: Step 4 of the design ("Weak Coverage Recipes" for monoculture combos) is not implemented here — explicitly deferred per the design doc itself ("Defer until after initial recipe generation proves useful"). Tracked for a follow-up plan once recipes prove valuable in practice.
