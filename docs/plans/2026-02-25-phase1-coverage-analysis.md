# Phase 1: Coverage Analysis Foundation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement feature detection, combination matrix, and topology-filtered gap identification for the WebGL fuzzing corpus — replacing grep-based `feature_matrix.sh` with AST-based analysis.

**Architecture:** Two new Python modules (`feature_detection.py`, `combination_matrix.py`) consume existing pipeline output (call_analysis, glsl, context) plus two new JSON config files. New CLI flags on `__main__.py` expose the pipeline. All code lives in `scripts/api_audit/`.

**Tech Stack:** Python 3, tree-sitter (existing), pytest, existing api_audit pipeline

---

## Reference: Key Existing Code

- **`scripts/api_audit/__main__.py`**: CLI entry, `analyze_file()` pipeline, `aggregate_results()`, `main()`
- **`scripts/api_audit/call_analysis.py`**: `CallAnalysisResult` (methods dict, extension_methods dict, return_constants set), `CallRecord` dataclass
- **`scripts/api_audit/context.py`**: `ContextInfo` (api_version, context_vars, extensions, extension_aliases, helper_functions)
- **`scripts/api_audit/glsl.py`**: `extract_glsl_builtins()` returns `set[str]`
- **`scripts/api_audit/const_propagation.py`**: `resolve_constants()` returns `dict[str, str|list[str]]`
- **`scripts/api_audit/report.py`**: `GapReport`, `DeltaReport`, `generate_report()`, `generate_delta_report()`
- **`scripts/api_audit/cache.py`**: `FileCache` with per-file SHA256 + aggregated corpus caching
- **`scripts/api_audit/parse.py`**: `parse_js()` — tree-sitter JS parser
- **`scripts/api_audit/html_extract.py`**: `extract_script()` — BeautifulSoup
- **`docs/webgl_api_surface.json`**: 225 methods, 559 constants, 28 extensions, 6 GLSL sections
- **Design doc**: `docs/plans/2026-02-24-coverage-analysis-upgrade-design.md` (canonical spec for all algorithms)

---

### Task 1: Create `docs/feature_categories.json`

**Files:**
- Create: `docs/feature_categories.json`

**Step 1: Write the config file**

Create the complete feature categories config from the design doc (lines 122-481). This is a data file, not code — copy the exact JSON from the design doc.

The file must contain all 30 categories: `buffer_ops`, `transform_feedback`, `fbo`, `texture_ops`, `texture_3d`, `texture_arrays`, `sampler`, `sync`, `query`, `vao`, `instancing`, `mrt`, `ubo`, `integer_textures`, `depth_stencil`, `blending`, `pixel_ops`, `renderbuffer`, `shader_pipeline`, `uniforms`, `attributes`, `draw_calls`, `viewport_scissor`, `ext_float_textures`, `ext_color_buffer_float`, `ext_draw_buffers_indexed`, `ext_texture_filter_anisotropic`, `ext_compressed_textures`, `ext_disjoint_timer_query`, `glsl_builtins`.

Each category has: `description`, `methods` (list), `constants` (list), `min_methods_for_match` (int). Some have additional flags: `requires_any_constant`, `min_constants_for_match`, `requires_any_extension`, `extensions`, `extension_methods`, `glsl_functions`, `min_glsl_for_match`.

Extension categories (`ext_*`) have `"min_methods_for_match": 0` and `"requires_any_extension": true`.

The `glsl_builtins` category has `"min_glsl_for_match": 1` and `glsl_functions` list.

```json
{
  "version": 1,
  "categories": {
    "buffer_ops": { ... },
    ...all 30 categories from design doc lines 127-478...
  }
}
```

**Step 2: Validate JSON is parseable**

Run: `python3 -c "import json; json.load(open('docs/feature_categories.json')); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add docs/feature_categories.json
git commit -m "feat: add feature_categories.json config for Phase 1 coverage analysis"
```

---

### Task 2: Create `docs/interaction_topology.json`

**Files:**
- Create: `docs/interaction_topology.json`

**Step 1: Write the topology config**

Create the interaction topology graph from design doc lines 710-774. Contains ~55 edges defining which feature pairs can meaningfully interact.

```json
{
  "version": 1,
  "description": "Static feature interaction graph. Edges represent feature pairs that CAN meaningfully interact in a WebGL seed. An N-way combo is topology-connected if all pairs are connected (directly or via shared neighbor).",
  "edges": [
    {"pair": ["buffer_ops", "vao"], "relationship": "buffers feed vertex attributes"},
    {"pair": ["buffer_ops", "transform_feedback"], "relationship": "TF captures to buffers"},
    ...all ~55 edges from design doc...
  ]
}
```

**Step 2: Validate JSON is parseable**

Run: `python3 -c "import json; d=json.load(open('docs/interaction_topology.json')); print(f'OK: {len(d[\"edges\"])} edges')"`
Expected: `OK: 55 edges` (approximately)

**Step 3: Commit**

```bash
git add docs/interaction_topology.json
git commit -m "feat: add interaction_topology.json with ~55 feature interaction edges"
```

---

### Task 3: Create test infrastructure and config validation tests

**Files:**
- Create: `scripts/api_audit/tests/__init__.py`
- Create: `scripts/api_audit/tests/conftest.py`
- Create: `scripts/api_audit/tests/test_config_validation.py`

**Step 1: Create test directory and `__init__.py`**

```python
# scripts/api_audit/tests/__init__.py
# (empty file)
```

**Step 2: Write `conftest.py` with shared fixtures**

```python
# scripts/api_audit/tests/conftest.py
import json
import pytest
from pathlib import Path

# Project root is 3 levels up from tests/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

@pytest.fixture
def feature_categories():
    """Load feature_categories.json config."""
    path = PROJECT_ROOT / "docs" / "feature_categories.json"
    return json.loads(path.read_text())

@pytest.fixture
def interaction_topology():
    """Load interaction_topology.json config."""
    path = PROJECT_ROOT / "docs" / "interaction_topology.json"
    return json.loads(path.read_text())

@pytest.fixture
def api_surface():
    """Load webgl_api_surface.json."""
    path = PROJECT_ROOT / "docs" / "webgl_api_surface.json"
    return json.loads(path.read_text())

@pytest.fixture
def corpus_dirs():
    """Return paths to corpus directories."""
    return [
        PROJECT_ROOT / "samples-webgl",
        PROJECT_ROOT / "agent_outputs",
    ]
```

**Step 3: Write config validation tests**

`test_config_validation.py` must test:

1. `feature_categories.json` schema: every category has `methods` (list of str), `constants` (list of str), `min_methods_for_match` (int >= 0)
2. All method names in categories exist in `webgl_api_surface.json` methods or extension methods
3. All constant names in categories exist in `webgl_api_surface.json` constants
4. `interaction_topology.json` schema: every edge `pair` references categories in `feature_categories.json`
5. Warn about categories with zero topology edges
6. No duplicate edges in topology
7. Completeness check: every method in `webgl_api_surface.json` appears in at least one category (warning, not failure)

```python
# scripts/api_audit/tests/test_config_validation.py
import pytest


def test_categories_schema(feature_categories):
    """Every category has required fields with correct types."""
    cats = feature_categories["categories"]
    assert len(cats) >= 25, f"Expected at least 25 categories, got {len(cats)}"
    for name, cat in cats.items():
        assert isinstance(cat.get("methods", []), list), f"{name}: methods must be a list"
        assert isinstance(cat.get("constants", []), list), f"{name}: constants must be a list"
        assert isinstance(cat.get("min_methods_for_match", 1), int), f"{name}: min_methods_for_match must be int"
        assert cat.get("min_methods_for_match", 1) >= 0, f"{name}: min_methods_for_match must be >= 0"


def test_category_methods_exist_in_surface(feature_categories, api_surface):
    """All method names in categories exist in the API surface."""
    surface_methods = set(api_surface.get("methods", {}).keys())
    ext_methods = set()
    for ext_info in api_surface.get("extensions", {}).values():
        ext_methods.update(ext_info.get("methods", {}).keys())
    all_known = surface_methods | ext_methods

    unknown = []
    for cat_name, cat in feature_categories["categories"].items():
        for method in cat.get("methods", []):
            if method not in all_known:
                unknown.append(f"{cat_name}.{method}")
        for method in cat.get("extension_methods", []):
            if method not in ext_methods:
                unknown.append(f"{cat_name}.ext:{method}")
    assert not unknown, f"Unknown methods in categories: {unknown}"


def test_category_constants_exist_in_surface(feature_categories, api_surface):
    """All constant names in categories exist in the API surface."""
    surface_constants = set(api_surface.get("constants", {}).keys())
    unknown = []
    for cat_name, cat in feature_categories["categories"].items():
        for const in cat.get("constants", []):
            if const not in surface_constants:
                unknown.append(f"{cat_name}.{const}")
    assert not unknown, f"Unknown constants in categories: {unknown}"


def test_topology_references_valid_categories(interaction_topology, feature_categories):
    """Every topology edge references categories that exist."""
    valid_cats = set(feature_categories["categories"].keys())
    invalid = []
    for edge in interaction_topology["edges"]:
        for cat in edge["pair"]:
            if cat not in valid_cats:
                invalid.append(f"{cat} in edge {edge['pair']}")
    assert not invalid, f"Invalid category references in topology: {invalid}"


def test_topology_no_duplicates(interaction_topology):
    """No duplicate edges in topology."""
    seen = set()
    dupes = []
    for edge in interaction_topology["edges"]:
        key = tuple(sorted(edge["pair"]))
        if key in seen:
            dupes.append(key)
        seen.add(key)
    assert not dupes, f"Duplicate topology edges: {dupes}"


def test_categories_with_zero_topology_edges(interaction_topology, feature_categories):
    """Warn about categories with zero topology edges (potentially missing connections)."""
    connected = set()
    for edge in interaction_topology["edges"]:
        connected.update(edge["pair"])
    all_cats = set(feature_categories["categories"].keys())
    disconnected = all_cats - connected
    # This is a warning, not a hard failure — some categories may intentionally lack edges
    if disconnected:
        import warnings
        warnings.warn(f"Categories with zero topology edges: {disconnected}")


def test_surface_method_completeness(feature_categories, api_surface):
    """Every surface method appears in at least one category (warning)."""
    categorized = set()
    for cat in feature_categories["categories"].values():
        categorized.update(cat.get("methods", []))
    surface_methods = set(api_surface.get("methods", {}).keys())
    uncategorized = surface_methods - categorized
    if uncategorized:
        import warnings
        warnings.warn(f"Uncategorized methods ({len(uncategorized)}): {sorted(uncategorized)[:10]}...")
```

**Step 4: Run config validation tests**

Run: `cd /path/to/project && PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_config_validation.py -v`
Expected: All tests PASS (some may produce warnings for uncategorized methods — that's fine)

**Step 5: Fix any failures**

If methods/constants are misspelled or missing from the API surface, fix `feature_categories.json` or `interaction_topology.json`.

**Step 6: Run tests again to verify fixes**

Run: same pytest command
Expected: All PASS

**Step 7: Commit**

```bash
git add scripts/api_audit/tests/
git commit -m "test: add config validation tests for feature_categories and interaction_topology"
```

---

### Task 4: Implement `feature_detection.py` — matching algorithm

**Files:**
- Create: `scripts/api_audit/feature_detection.py`
- Create: `scripts/api_audit/tests/test_feature_detection.py`

**Step 1: Write failing tests for `is_category_match`**

```python
# scripts/api_audit/tests/test_feature_detection.py
import pytest
from api_audit.feature_detection import is_category_match, detect_features


class TestIsCategoryMatch:
    """Test the category matching algorithm."""

    def test_basic_method_match(self):
        """Category with 1 matching method passes."""
        cat = {"methods": ["createBuffer", "bindBuffer"], "constants": [],
               "min_methods_for_match": 1}
        match, methods, count = is_category_match(
            cat, methods_found={"createBuffer"},
            constants_found=set(), extensions_loaded=set(),
            glsl_found=set(), extension_methods_found={})
        assert match is True
        assert "createBuffer" in methods
        assert count == 1

    def test_method_count_below_threshold(self):
        """Category requiring 2 methods rejects seed with 1."""
        cat = {"methods": ["createShader", "shaderSource", "compileShader"],
               "constants": [], "min_methods_for_match": 2}
        match, _, _ = is_category_match(
            cat, methods_found={"createShader"},
            constants_found=set(), extensions_loaded=set(),
            glsl_found=set(), extension_methods_found={})
        assert match is False

    def test_requires_any_constant_gate(self):
        """Category with requires_any_constant rejects seed without constant."""
        cat = {"methods": ["texImage3D"], "constants": ["TEXTURE_2D_ARRAY"],
               "min_methods_for_match": 1, "requires_any_constant": True}
        # Has method but missing constant
        match, _, _ = is_category_match(
            cat, methods_found={"texImage3D"},
            constants_found=set(), extensions_loaded=set(),
            glsl_found=set(), extension_methods_found={})
        assert match is False

    def test_requires_any_constant_passes(self):
        """Category with requires_any_constant passes when constant present."""
        cat = {"methods": ["texImage3D"], "constants": ["TEXTURE_2D_ARRAY"],
               "min_methods_for_match": 1, "requires_any_constant": True}
        match, _, _ = is_category_match(
            cat, methods_found={"texImage3D"},
            constants_found={"TEXTURE_2D_ARRAY"}, extensions_loaded=set(),
            glsl_found=set(), extension_methods_found={})
        assert match is True

    def test_requires_any_extension_gate(self):
        """Extension category rejects seed without extension loaded."""
        cat = {"methods": [], "constants": [],
               "extensions": ["OES_texture_float"],
               "min_methods_for_match": 0, "requires_any_extension": True}
        match, _, _ = is_category_match(
            cat, methods_found=set(), constants_found=set(),
            extensions_loaded=set(), glsl_found=set(),
            extension_methods_found={})
        assert match is False

    def test_requires_any_extension_passes(self):
        """Extension category passes when extension is loaded."""
        cat = {"methods": [], "constants": [],
               "extensions": ["OES_texture_float"],
               "min_methods_for_match": 0, "requires_any_extension": True}
        match, _, _ = is_category_match(
            cat, methods_found=set(), constants_found=set(),
            extensions_loaded={"OES_texture_float"}, glsl_found=set(),
            extension_methods_found={})
        assert match is True

    def test_glsl_gate(self):
        """GLSL category requires min_glsl_for_match builtins."""
        cat = {"methods": [], "constants": [],
               "glsl_functions": ["smoothstep", "refract"],
               "min_methods_for_match": 0, "min_glsl_for_match": 1}
        # No GLSL builtins
        match, _, _ = is_category_match(
            cat, methods_found=set(), constants_found=set(),
            extensions_loaded=set(), glsl_found=set(),
            extension_methods_found={})
        assert match is False
        # With GLSL builtin
        match, _, _ = is_category_match(
            cat, methods_found=set(), constants_found=set(),
            extensions_loaded=set(), glsl_found={"smoothstep"},
            extension_methods_found={})
        assert match is True

    def test_min_constants_for_match(self):
        """Category with min_constants_for_match gate."""
        cat = {"methods": [], "constants": ["R8I", "R16I", "R32I"],
               "min_methods_for_match": 0, "min_constants_for_match": 1}
        # No constants
        match, _, _ = is_category_match(
            cat, methods_found=set(), constants_found=set(),
            extensions_loaded=set(), glsl_found=set(),
            extension_methods_found={})
        assert match is False
        # With constant
        match, _, _ = is_category_match(
            cat, methods_found=set(), constants_found={"R8I"},
            extensions_loaded=set(), glsl_found=set(),
            extension_methods_found={})
        assert match is True

    def test_extension_methods_count_toward_methods(self):
        """Extension methods contribute to method count."""
        cat = {"methods": [], "constants": [],
               "extension_methods": ["enableiOES", "disableiOES"],
               "extensions": ["OES_draw_buffers_indexed"],
               "min_methods_for_match": 0, "requires_any_extension": True}
        match, methods, count = is_category_match(
            cat, methods_found=set(), constants_found=set(),
            extensions_loaded={"OES_draw_buffers_indexed"},
            glsl_found=set(),
            extension_methods_found={"OES_draw_buffers_indexed": {"enableiOES"}})
        assert match is True
        assert count == 1
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_feature_detection.py -v`
Expected: FAIL (module doesn't exist yet)

**Step 3: Implement `feature_detection.py`**

```python
# scripts/api_audit/feature_detection.py
"""Feature detection: AST-based feature categorization per seed.

Replaces grep-based feature_matrix.sh with data-driven category matching
using call_analysis, glsl, and context pipeline outputs.
"""
from __future__ import annotations

import json
from pathlib import Path


def is_category_match(category_def, methods_found, constants_found,
                      extensions_loaded, glsl_found, extension_methods_found):
    """Determine if a seed matches a feature category.

    Returns (matched: bool, matched_methods: set, method_count: int).
    """
    cat = category_def

    # Method count check
    cat_methods = set(cat.get("methods", []))
    matched_methods = methods_found & cat_methods
    method_count = len(matched_methods)

    # Extension methods contribute to method count
    cat_ext_methods = set(cat.get("extension_methods", []))
    all_ext_methods = set()
    for ext_methods in extension_methods_found.values():
        all_ext_methods |= (ext_methods if isinstance(ext_methods, set)
                            else set(ext_methods))
    matched_ext_methods = all_ext_methods & cat_ext_methods
    method_count += len(matched_ext_methods)

    min_methods = cat.get("min_methods_for_match", 1)
    if min_methods > 0 and method_count < min_methods:
        return False, set(), 0

    # Constant gate (AND)
    if cat.get("requires_any_constant", False):
        cat_constants = set(cat.get("constants", []))
        if not (constants_found & cat_constants):
            return False, set(), 0

    # Constant count gate (AND)
    min_constants = cat.get("min_constants_for_match", 0)
    if min_constants > 0:
        cat_constants = set(cat.get("constants", []))
        if len(constants_found & cat_constants) < min_constants:
            return False, set(), 0

    # Extension gate (AND)
    if cat.get("requires_any_extension", False):
        cat_extensions = set(cat.get("extensions", []))
        if not (extensions_loaded & cat_extensions):
            return False, set(), 0

    # GLSL gate
    min_glsl = cat.get("min_glsl_for_match", 0)
    if min_glsl > 0:
        cat_glsl = set(cat.get("glsl_functions", []))
        matched_glsl = glsl_found & cat_glsl
        if len(matched_glsl) < min_glsl:
            return False, set(), 0

    all_matched = matched_methods | matched_ext_methods
    return True, all_matched, method_count


def _compute_depth(method_count, category_def):
    """Compute depth level and ratio for a matched category."""
    available = len(category_def.get("methods", []))
    available += len(category_def.get("extension_methods", []))
    if available == 0:
        # GLSL-only or extension-only categories
        return "deep", 1.0
    ratio = method_count / available
    if ratio >= 0.66:
        return "deep", ratio
    if ratio >= 0.33:
        return "meaningful", ratio
    return "present", ratio


def detect_features(call_analysis_result, glsl_builtins, categories_config,
                    extensions=None, extension_methods=None):
    """Detect feature categories present in a single seed.

    Args:
        call_analysis_result: CallAnalysisResult from call_analysis.py
        glsl_builtins: set of GLSL builtin names from glsl.py
        categories_config: parsed feature_categories.json dict
        extensions: set of extension names from context.py (optional)
        extension_methods: dict from call_analysis.extension_methods (optional)

    Returns:
        dict with keys: features, feature_depth, depth_ratios,
        method_counts, methods_per_feature
    """
    # Extract method names from call_analysis
    methods_found = set(call_analysis_result.methods.keys()
                        if hasattr(call_analysis_result, 'methods')
                        else call_analysis_result.get('methods', {}).keys())

    # Extract constant names — strip 'gl.' prefix from const_propagation output
    constants_found = set()
    raw_constants = (call_analysis_result.get('constants', {})
                     if isinstance(call_analysis_result, dict)
                     else {})
    # From call_analysis, constants are already resolved names
    # But we also need to handle the aggregated format
    if hasattr(call_analysis_result, 'methods'):
        # It's a CallAnalysisResult — get constants from call records
        for method_records in call_analysis_result.methods.values():
            for record in method_records:
                constants_found.update(record.constants)
    else:
        # Dict format from analyze_file result
        constants_found = set(call_analysis_result.get('constants', {}).keys())

    extensions_loaded = extensions or set()
    glsl_found = glsl_builtins if isinstance(glsl_builtins, set) else set(glsl_builtins)

    # Build extension methods found dict: {ext_name: set(method_names)}
    ext_methods_found = {}
    if extension_methods:
        if isinstance(extension_methods, dict):
            for ext_name, methods in extension_methods.items():
                if isinstance(methods, dict):
                    ext_methods_found[ext_name] = set(methods.keys())
                elif isinstance(methods, set):
                    ext_methods_found[ext_name] = methods

    categories = categories_config["categories"]
    result = {
        "features": [],
        "feature_depth": {},
        "depth_ratios": {},
        "method_counts": {},
        "methods_per_feature": {},
    }

    for cat_name, cat_def in categories.items():
        matched, matched_methods, method_count = is_category_match(
            cat_def, methods_found, constants_found,
            extensions_loaded, glsl_found, ext_methods_found)
        if matched:
            depth_level, ratio = _compute_depth(method_count, cat_def)
            result["features"].append(cat_name)
            result["feature_depth"][cat_name] = depth_level
            result["depth_ratios"][cat_name] = round(ratio, 2)
            result["method_counts"][cat_name] = method_count
            result["methods_per_feature"][cat_name] = sorted(matched_methods)

    result["features"].sort()
    return result
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_feature_detection.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add scripts/api_audit/feature_detection.py scripts/api_audit/tests/test_feature_detection.py
git commit -m "feat: implement feature_detection.py with is_category_match and detect_features"
```

---

### Task 5: Add `detect_features` tests and depth level tests

**Files:**
- Modify: `scripts/api_audit/tests/test_feature_detection.py`

**Step 1: Write failing tests for `detect_features` and depth levels**

Append to `test_feature_detection.py`:

```python
from dataclasses import dataclass, field


@dataclass
class MockCallAnalysis:
    """Minimal mock of CallAnalysisResult for testing."""
    methods: dict = field(default_factory=dict)
    extension_methods: dict = field(default_factory=dict)
    return_constants: set = field(default_factory=set)


@dataclass
class MockCallRecord:
    constants: set = field(default_factory=set)
    constant_roles: dict = field(default_factory=dict)
    arity: int = 0
    overload_tag: str = None


class TestDetectFeatures:
    """Test the detect_features function."""

    def _make_categories(self):
        return {
            "categories": {
                "buffer_ops": {
                    "methods": ["createBuffer", "bindBuffer", "bufferData",
                                "bufferSubData", "copyBufferSubData",
                                "getBufferSubData", "deleteBuffer",
                                "getBufferParameter", "isBuffer"],
                    "constants": ["ARRAY_BUFFER", "ELEMENT_ARRAY_BUFFER"],
                    "min_methods_for_match": 1,
                },
                "mrt": {
                    "methods": ["drawBuffers"],
                    "constants": ["COLOR_ATTACHMENT1"],
                    "min_methods_for_match": 1,
                },
                "texture_arrays": {
                    "methods": ["texImage3D", "texSubImage3D", "texStorage3D",
                                "framebufferTextureLayer"],
                    "constants": ["TEXTURE_2D_ARRAY"],
                    "min_methods_for_match": 1,
                    "requires_any_constant": True,
                },
            }
        }

    def test_buffer_only_seed(self):
        """Seed with only buffer ops detected correctly."""
        calls = MockCallAnalysis(methods={
            "createBuffer": [MockCallRecord(constants={"ARRAY_BUFFER"})],
        })
        result = detect_features(calls, set(), self._make_categories())
        assert "buffer_ops" in result["features"]
        assert "mrt" not in result["features"]

    def test_depth_present(self):
        """1 of 9 buffer methods = ratio 0.11 = 'present'."""
        calls = MockCallAnalysis(methods={
            "createBuffer": [MockCallRecord()],
        })
        result = detect_features(calls, set(), self._make_categories())
        assert result["feature_depth"]["buffer_ops"] == "present"
        assert result["depth_ratios"]["buffer_ops"] < 0.33

    def test_depth_meaningful(self):
        """4 of 9 buffer methods = ratio 0.44 = 'meaningful'."""
        calls = MockCallAnalysis(methods={
            "createBuffer": [MockCallRecord()],
            "bindBuffer": [MockCallRecord()],
            "bufferData": [MockCallRecord()],
            "deleteBuffer": [MockCallRecord()],
        })
        result = detect_features(calls, set(), self._make_categories())
        assert result["feature_depth"]["buffer_ops"] == "meaningful"

    def test_depth_deep(self):
        """7 of 9 buffer methods = ratio 0.78 = 'deep'."""
        calls = MockCallAnalysis(methods={
            "createBuffer": [MockCallRecord()],
            "bindBuffer": [MockCallRecord()],
            "bufferData": [MockCallRecord()],
            "bufferSubData": [MockCallRecord()],
            "copyBufferSubData": [MockCallRecord()],
            "getBufferSubData": [MockCallRecord()],
            "deleteBuffer": [MockCallRecord()],
        })
        result = detect_features(calls, set(), self._make_categories())
        assert result["feature_depth"]["buffer_ops"] == "deep"

    def test_small_category_depth(self):
        """mrt with 1/1 method = ratio 1.0 = 'deep'."""
        calls = MockCallAnalysis(methods={
            "drawBuffers": [MockCallRecord()],
        })
        result = detect_features(calls, set(), self._make_categories())
        assert result["feature_depth"]["mrt"] == "deep"

    def test_texture_arrays_requires_constant(self):
        """texture_arrays requires TEXTURE_2D_ARRAY constant."""
        calls = MockCallAnalysis(methods={
            "texImage3D": [MockCallRecord(constants=set())],
        })
        result = detect_features(calls, set(), self._make_categories())
        assert "texture_arrays" not in result["features"]

    def test_texture_arrays_with_constant(self):
        """texture_arrays matches when constant is present."""
        calls = MockCallAnalysis(methods={
            "texImage3D": [MockCallRecord(constants={"TEXTURE_2D_ARRAY"})],
        })
        result = detect_features(calls, set(), self._make_categories())
        assert "texture_arrays" in result["features"]

    def test_methods_per_feature_populated(self):
        """methods_per_feature contains the matched method names."""
        calls = MockCallAnalysis(methods={
            "createBuffer": [MockCallRecord()],
            "bindBuffer": [MockCallRecord()],
        })
        result = detect_features(calls, set(), self._make_categories())
        assert "createBuffer" in result["methods_per_feature"]["buffer_ops"]
        assert "bindBuffer" in result["methods_per_feature"]["buffer_ops"]
```

**Step 2: Run tests**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_feature_detection.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add scripts/api_audit/tests/test_feature_detection.py
git commit -m "test: add detect_features and depth level tests"
```

---

### Task 6: Implement `combination_matrix.py` — core algorithm

**Files:**
- Create: `scripts/api_audit/combination_matrix.py`
- Create: `scripts/api_audit/tests/test_combination_matrix.py`

**Step 1: Write failing tests for `combination_matrix.py`**

```python
# scripts/api_audit/tests/test_combination_matrix.py
import pytest
from api_audit.combination_matrix import (
    compute_matrix, identify_gaps, compute_priority_key,
    priority_label, is_topology_connected,
)


class TestIsTopologyConnected:
    def _topology(self, edges):
        return {"edges": [{"pair": e} for e in edges]}

    def test_2way_direct_edge(self):
        t = self._topology([["A", "B"]])
        assert is_topology_connected(["A", "B"], t) is True

    def test_2way_no_edge(self):
        t = self._topology([["A", "C"]])
        assert is_topology_connected(["A", "B"], t) is False

    def test_3way_all_connected(self):
        t = self._topology([["A", "B"], ["B", "C"]])
        assert is_topology_connected(["A", "B", "C"], t) is True

    def test_3way_disconnected(self):
        t = self._topology([["A", "B"]])
        assert is_topology_connected(["A", "B", "C"], t) is False

    def test_single_feature(self):
        t = self._topology([])
        assert is_topology_connected(["A"], t) is True


class TestComputeMatrix:
    def test_basic_2way(self):
        corpus = {
            "seed1": {"features": ["A", "B"], "methods_per_feature": {"A": ["m1"], "B": ["m2"]}},
            "seed2": {"features": ["A"], "methods_per_feature": {"A": ["m1"]}},
            "seed3": {"features": ["B", "C"], "methods_per_feature": {"B": ["m2"], "C": ["m3"]}},
        }
        matrix = compute_matrix(corpus, n=2)
        assert matrix[("A", "B")]["seed_count"] == 1
        assert matrix[("A", "C")]["seed_count"] == 0
        assert matrix[("B", "C")]["seed_count"] == 1

    def test_distinct_fingerprints(self):
        corpus = {
            "seed1": {"features": ["A", "B"],
                       "methods_per_feature": {"A": ["m1"], "B": ["m2"]}},
            "seed2": {"features": ["A", "B"],
                       "methods_per_feature": {"A": ["m1", "m3"], "B": ["m2"]}},
        }
        matrix = compute_matrix(corpus, n=2)
        assert matrix[("A", "B")]["distinct_fingerprints"] == 2

    def test_topology_filtering(self):
        corpus = {
            "seed1": {"features": ["A", "B", "C"],
                       "methods_per_feature": {"A": ["m1"], "B": ["m2"], "C": ["m3"]}},
        }
        topology = {"edges": [{"pair": ["A", "B"]}]}
        matrix = compute_matrix(corpus, n=2, interaction_topology=topology)
        assert matrix[("A", "B")]["topology_connected"] is True
        assert matrix[("A", "C")]["topology_connected"] is False
        assert matrix[("A", "C")]["seed_count"] == 0  # disconnected = 0 seeds


class TestIdentifyGaps:
    def test_finds_zero_seed_gaps(self):
        matrix = {
            ("A", "B"): {"seed_count": 3, "topology_connected": True},
            ("A", "C"): {"seed_count": 0, "topology_connected": True},
        }
        gaps = identify_gaps(matrix, min_seeds=1)
        assert ("A", "C") in gaps
        assert ("A", "B") not in gaps


class TestPriorityKey:
    def test_non_ubiquitous_beats_ubiquitous(self):
        """Non-ubiquitous combo ranks above all-ubiquitous."""
        non_ubiq = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        all_ubiq = compute_priority_key(
            ("shader_pipeline", "draw_calls"), seed_count=0, depth_levels=[])
        assert non_ubiq > all_ubiq

    def test_connected_beats_disconnected(self):
        topology = {"edges": [{"pair": ["fbo", "texture_ops"]}]}
        connected = compute_priority_key(
            ("fbo", "texture_ops"), seed_count=0, depth_levels=[],
            interaction_topology=topology)
        disconnected = compute_priority_key(
            ("fbo", "sync"), seed_count=0, depth_levels=[],
            interaction_topology=topology)
        assert connected > disconnected

    def test_zero_seed_beats_thin(self):
        zero = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        thin = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=2, depth_levels=["present", "present"])
        assert zero > thin

    def test_more_security_beats_less(self):
        more = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        less = compute_priority_key(
            ("fbo", "sampler"), seed_count=0, depth_levels=[])
        assert more >= less  # fbo+buffer_ops has 2 security, fbo+sampler has 1

    def test_2way_beats_3way(self):
        two = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        three = compute_priority_key(
            ("fbo", "buffer_ops", "sync"), seed_count=0, depth_levels=[])
        # 2-way has n_way_pref=-2, 3-way has -3
        assert two > three

    def test_priority_label_skip_for_ubiquitous(self):
        key = compute_priority_key(
            ("shader_pipeline", "draw_calls"), seed_count=0, depth_levels=[])
        assert priority_label(key) == "skip"

    def test_priority_label_high_for_security_zero_seed(self):
        key = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        assert priority_label(key) == "high"

    def test_priority_label_medium_for_zero_seed_no_security(self):
        key = compute_priority_key(
            ("vao", "sampler"), seed_count=0, depth_levels=[])
        assert priority_label(key) == "medium"
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_combination_matrix.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Implement `combination_matrix.py`**

```python
# scripts/api_audit/combination_matrix.py
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
        n: combination size (2, 3, or 4)
        interaction_topology: parsed interaction_topology.json (optional)

    Returns:
        dict {combo_tuple: {seed_count, distinct_fingerprints, seeds, topology_connected}}
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

    # Adjusted count: exclude pairs where both are UBIQUITOUS
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

    # Build gap list
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

    # Sort gaps by priority
    gaps.sort(key=lambda g: {"high": 0, "medium": 1, "low": 2}.get(g["priority"], 3))

    # Low diversity: high seed count but few fingerprints
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


# Known tautological overlapping pairs from design doc
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
```

**Step 4: Run tests**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_combination_matrix.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add scripts/api_audit/combination_matrix.py scripts/api_audit/tests/test_combination_matrix.py
git commit -m "feat: implement combination_matrix.py with topology filtering and lexicographic priority"
```

---

### Task 7: Add incremental merge and report generation tests

**Files:**
- Modify: `scripts/api_audit/tests/test_combination_matrix.py`

**Step 1: Write tests for incremental merge and report generation**

Append to `test_combination_matrix.py`:

```python
from api_audit.combination_matrix import merge_seed_into_matrix, generate_matrix_report


class TestIncrementalMerge:
    def test_merge_updates_seed_count(self):
        baseline = {
            ("A", "B"): {"seed_count": 1, "seeds": ["s1"],
                          "distinct_fingerprints": 1,
                          "topology_connected": True},
        }
        new_fp = {"features": ["A", "B"], "file": "s2",
                  "methods_per_feature": {"A": ["m1"], "B": ["m2"]}}
        merge_seed_into_matrix(baseline, new_fp, n_way=2)
        assert baseline[("A", "B")]["seed_count"] == 2
        assert "s2" in baseline[("A", "B")]["seeds"]

    def test_merge_creates_new_combo(self):
        baseline = {}
        new_fp = {"features": ["X", "Y"], "file": "s1",
                  "methods_per_feature": {"X": ["mx"], "Y": ["my"]}}
        merge_seed_into_matrix(baseline, new_fp, n_way=2)
        assert ("X", "Y") in baseline
        assert baseline[("X", "Y")]["seed_count"] == 1

    def test_merge_tracks_distinct_fingerprints(self):
        baseline = {
            ("A", "B"): {"seed_count": 1, "seeds": ["s1"],
                          "distinct_fingerprints": 1,
                          "_fingerprint_set": {(("m1",), ("m2",))},
                          "topology_connected": True},
        }
        # Different methods = new fingerprint
        new_fp = {"features": ["A", "B"], "file": "s2",
                  "methods_per_feature": {"A": ["m1", "m3"], "B": ["m2"]}}
        merge_seed_into_matrix(baseline, new_fp, n_way=2)
        assert baseline[("A", "B")]["distinct_fingerprints"] == 2

    def test_merge_same_fingerprint_no_duplicate(self):
        baseline = {
            ("A", "B"): {"seed_count": 1, "seeds": ["s1"],
                          "distinct_fingerprints": 1,
                          "_fingerprint_set": {(("m1",), ("m2",))},
                          "topology_connected": True},
        }
        # Same methods = same fingerprint
        new_fp = {"features": ["A", "B"], "file": "s2",
                  "methods_per_feature": {"A": ["m1"], "B": ["m2"]}}
        merge_seed_into_matrix(baseline, new_fp, n_way=2)
        assert baseline[("A", "B")]["distinct_fingerprints"] == 1
        assert baseline[("A", "B")]["seed_count"] == 2


class TestGenerateReport:
    def test_report_structure(self):
        corpus = {
            "s1": {"features": ["A", "B"],
                    "methods_per_feature": {"A": ["m1"], "B": ["m2"]},
                    "feature_depth": {"A": "deep", "B": "present"}},
        }
        matrix = compute_matrix(corpus, n=2)
        report = generate_matrix_report(matrix, corpus)
        assert "total" in report
        assert "covered" in report
        assert "gaps" in report
        assert report["phase2_enriched"] is False
```

**Step 2: Run tests**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_combination_matrix.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add scripts/api_audit/tests/test_combination_matrix.py
git commit -m "test: add incremental merge and report generation tests"
```

---

### Task 8: Add CLI flags to `__main__.py`

**Files:**
- Modify: `scripts/api_audit/__main__.py`

**Step 1: Write failing integration test**

Create `scripts/api_audit/tests/test_phase1_integration.py`:

```python
# scripts/api_audit/tests/test_phase1_integration.py
"""Integration tests for Phase 1 pipeline."""
import json
import subprocess
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture
def venv_python():
    """Path to venv python if it exists, else system python."""
    venv = PROJECT_ROOT / "venv" / "bin" / "python"
    if venv.exists():
        return str(venv)
    return sys.executable


class TestCLIFlags:
    def test_combination_matrix_flag(self, venv_python, tmp_path):
        """--combination-matrix produces valid JSON output."""
        output = tmp_path / "matrix.json"
        result = subprocess.run(
            [venv_python, "-m", "api_audit",
             "--surface", str(PROJECT_ROOT / "docs" / "webgl_api_surface.json"),
             "--corpus-dirs", str(PROJECT_ROOT / "samples-webgl"),
             "--feature-categories", str(PROJECT_ROOT / "docs" / "feature_categories.json"),
             "--interaction-topology", str(PROJECT_ROOT / "docs" / "interaction_topology.json"),
             "--combination-matrix", str(output),
             "--n-way", "2"],
            cwd=str(PROJECT_ROOT),
            env={"PYTHONPATH": str(PROJECT_ROOT / "scripts")},
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert output.exists()
        data = json.loads(output.read_text())
        assert "2way_combinations" in data
        assert data["2way_combinations"]["total"] > 0
        assert data["2way_combinations"]["covered"] > 0
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_phase1_integration.py -v -k test_combination_matrix_flag`
Expected: FAIL (flag doesn't exist yet)

**Step 3: Add CLI flags and pipeline integration to `__main__.py`**

Modify `scripts/api_audit/__main__.py` to add:

1. New imports: `from api_audit.feature_detection import detect_features` and `from api_audit.combination_matrix import compute_matrix, generate_matrix_report, merge_seed_into_matrix`
2. New argparse flags: `--feature-categories`, `--interaction-topology`, `--combination-matrix`, `--n-way`, `--min-seeds`, `--baseline`
3. In the full corpus analysis path (`else` branch), after `aggregate_results()`:
   - Load configs if `--feature-categories` provided
   - Run `detect_features()` on each file's analysis result
   - Compute combination matrix if `--combination-matrix` provided
   - Write matrix report to output file
4. In delta mode (`--file` branch), optionally use `--baseline` for incremental merge

Key implementation additions to `main()`:

```python
# After existing argparse flags:
parser.add_argument('--feature-categories', type=Path, default=None,
                    help='Path to feature_categories.json config')
parser.add_argument('--interaction-topology', type=Path, default=None,
                    help='Path to interaction_topology.json config')
parser.add_argument('--combination-matrix', type=Path, default=None,
                    help='Output combination matrix report (JSON)')
parser.add_argument('--n-way', type=int, default=2,
                    help='Compute N-way combinations (default: 2, max: 4)')
parser.add_argument('--min-seeds', type=int, default=1,
                    help='Minimum seeds per combination (default: 1)')
parser.add_argument('--baseline', type=Path, default=None,
                    help='Baseline matrix for incremental merge')
```

In the full corpus path, after existing analysis:

```python
if args.feature_categories:
    from api_audit.feature_detection import detect_features
    from api_audit.combination_matrix import (
        compute_matrix, generate_matrix_report)

    categories_config = json.loads(args.feature_categories.read_text())
    topology = None
    if args.interaction_topology:
        topology = json.loads(args.interaction_topology.read_text())

    # Run feature detection on each result
    corpus_features = {}
    for r in results:
        filepath = r['file']
        # Build inputs for detect_features from per-file result
        fp = detect_features(
            r, set(r.get('glsl_builtins', {}).keys()),
            categories_config,
            extensions=...,  # need to preserve from context
            extension_methods=r.get('extension_methods'))
        fp['file'] = filepath
        corpus_features[filepath] = fp

    if args.combination_matrix:
        n = min(args.n_way, 4)
        matrix = compute_matrix(corpus_features, n=n,
                                interaction_topology=topology)
        report = generate_matrix_report(matrix, corpus_features, topology)

        output_data = {
            "corpus_size": len(results),
            "feature_count": len(set(f for fp in corpus_features.values()
                                      for f in fp["features"])),
            "phase2_enriched": False,
            f"{n}way_combinations": report,
        }

        args.combination_matrix.parent.mkdir(parents=True, exist_ok=True)
        args.combination_matrix.write_text(
            json.dumps(output_data, indent=2, default=str))
        print(f"Combination matrix written to {args.combination_matrix}")
        print(f"  {n}-way: {report['total']} combos, "
              f"{report['covered']} covered, "
              f"{report['uncovered']} uncovered")
        if report['gaps']:
            print(f"  Top gaps: {len(report['gaps'])}")
            for g in report['gaps'][:5]:
                print(f"    {g['priority']}: {g['combo']}")
```

**Important**: The existing `analyze_file()` returns a per-file result dict, but it doesn't preserve the `ContextInfo` (extensions). We need to either:
- (a) Modify `analyze_file()` to include extensions in the result dict, or
- (b) Re-detect context for feature detection

Option (a) is cleaner. Add `'extensions': list(ctx.extensions)` and `'extension_aliases': dict(ctx.extension_aliases)` to the result dict in `analyze_file()`.

**Step 4: Run integration test**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_phase1_integration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/api_audit/__main__.py scripts/api_audit/tests/test_phase1_integration.py
git commit -m "feat: add Phase 1 CLI flags and pipeline integration for combination matrix"
```

---

### Task 9: Add edge case tests

**Files:**
- Create: `scripts/api_audit/tests/test_edge_cases.py`

**Step 1: Write edge case tests**

```python
# scripts/api_audit/tests/test_edge_cases.py
"""Edge case tests for Phase 1 pipeline."""
import pytest
from api_audit.feature_detection import detect_features, is_category_match
from api_audit.combination_matrix import compute_matrix, compute_priority_key


class TestEdgeCases:
    def test_empty_seed_produces_empty_fingerprint(self):
        """Seed with no methods produces empty feature list."""
        result = detect_features(
            {"methods": {}, "constants": {}, "extension_methods": {}},
            set(),
            {"categories": {"buffer_ops": {"methods": ["createBuffer"],
                                            "constants": [], "min_methods_for_match": 1}}})
        assert result["features"] == []

    def test_empty_corpus_matrix(self):
        """Empty corpus produces empty matrix."""
        matrix = compute_matrix({}, n=2)
        assert matrix == {}

    def test_single_feature_corpus(self):
        """Corpus with only 1 feature produces no 2-way combos."""
        corpus = {
            "s1": {"features": ["A"], "methods_per_feature": {"A": ["m1"]}},
        }
        matrix = compute_matrix(corpus, n=2)
        assert len(matrix) == 0

    def test_priority_key_with_empty_depth(self):
        """Priority key handles empty depth_levels (zero-seed gap)."""
        key = compute_priority_key(("fbo", "buffer_ops"), 0, [])
        assert key[5] == 1.0  # depth_deficit = 1.0 for no seeds

    def test_priority_key_all_deep(self):
        """All deep coverage = minimum depth deficit."""
        key = compute_priority_key(
            ("fbo", "buffer_ops"), 5, ["deep", "deep"])
        assert key[5] == 0.0

    def test_category_match_empty_everything(self):
        """Empty category def with min_methods 0 always matches."""
        cat = {"methods": [], "constants": [], "min_methods_for_match": 0}
        match, _, _ = is_category_match(
            cat, set(), set(), set(), set(), {})
        assert match is True

    def test_very_large_combo(self):
        """4-way combo priority key has correct n_way_pref."""
        key = compute_priority_key(
            ("fbo", "buffer_ops", "sync", "transform_feedback"),
            0, [])
        assert key[4] == -4  # n_way_pref
```

**Step 2: Run tests**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_edge_cases.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add scripts/api_audit/tests/test_edge_cases.py
git commit -m "test: add edge case tests for feature detection and combination matrix"
```

---

### Task 10: Run full corpus validation and benchmark

**Files:**
- Create: `scripts/api_audit/tests/test_benchmark.py`

**Step 1: Write benchmark test**

```python
# scripts/api_audit/tests/test_benchmark.py
"""Performance benchmark for Phase 1 pipeline."""
import json
import time
import pytest
from pathlib import Path

from api_audit.html_extract import extract_script
from api_audit.parse import parse_js
from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants
from api_audit.call_analysis import analyze_calls
from api_audit.glsl import extract_glsl_builtins
from api_audit.feature_detection import detect_features
from api_audit.combination_matrix import compute_matrix

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture
def full_corpus_data(api_surface, feature_categories):
    """Run analysis pipeline on full corpus and return feature fingerprints."""
    corpus_features = {}
    corpus_dirs = [PROJECT_ROOT / "samples-webgl", PROJECT_ROOT / "agent_outputs"]
    html_files = []
    for d in corpus_dirs:
        if d.exists():
            html_files.extend(d.rglob("*.html"))

    for filepath in sorted(html_files)[:50]:  # Limit to 50 for reasonable test time
        try:
            content = filepath.read_text()
            script = extract_script(content)
            if not script.strip():
                continue
            root = parse_js(script)
            consts = resolve_constants(root)
            ctx = detect_context(root, consts)
            calls = analyze_calls(root, ctx, consts, api_surface)
            glsl = extract_glsl_builtins(root, ctx, consts, api_surface)

            fp = detect_features(
                calls, glsl, feature_categories,
                extensions=ctx.extensions,
                extension_methods=calls.extension_methods)
            fp["file"] = str(filepath)
            corpus_features[str(filepath)] = fp
        except Exception:
            continue

    return corpus_features


class TestBenchmark:
    def test_feature_detection_performance(self, full_corpus_data):
        """Feature detection on 50 files completes in reasonable time."""
        assert len(full_corpus_data) > 0
        # Just verify it completed — timing is informational
        print(f"\nAnalyzed {len(full_corpus_data)} files")

    def test_matrix_computation_performance(self, full_corpus_data, interaction_topology):
        """2-way matrix computation on corpus subset completes."""
        start = time.time()
        matrix = compute_matrix(full_corpus_data, n=2,
                                interaction_topology=interaction_topology)
        elapsed = time.time() - start
        print(f"\n2-way matrix: {len(matrix)} combos in {elapsed:.2f}s")
        assert len(matrix) > 0

    def test_3way_matrix_performance(self, full_corpus_data, interaction_topology):
        """3-way matrix computation completes."""
        start = time.time()
        matrix = compute_matrix(full_corpus_data, n=3,
                                interaction_topology=interaction_topology)
        elapsed = time.time() - start
        print(f"\n3-way matrix: {len(matrix)} combos in {elapsed:.2f}s")
        assert len(matrix) > 0
```

**Step 2: Run benchmark test**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/test_benchmark.py -v -s`
Expected: PASS with timing output

**Step 3: Run full CLI pipeline on corpus**

Run:
```bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix_report.json \
  --n-way 2
```

Expected: Completes successfully, prints coverage summary, writes `/tmp/matrix_report.json`

**Step 4: Review matrix output**

Run: `python3 -c "import json; d=json.load(open('/tmp/matrix_report.json')); c=d['2way_combinations']; print(f'Total: {c[\"total\"]}, Covered: {c[\"covered\"]}, Gaps: {len(c[\"gaps\"])}')" `

Expected: Shows real coverage numbers from the corpus

**Step 5: Run 3-way analysis**

Run:
```bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix_3way.json \
  --n-way 3
```

Expected: Completes (may take longer), shows 3-way coverage

**Step 6: Commit benchmark test**

```bash
git add scripts/api_audit/tests/test_benchmark.py
git commit -m "test: add benchmark tests for Phase 1 pipeline performance"
```

---

### Task 11: Run all tests and final validation

**Files:** None (validation only)

**Step 1: Run all tests**

Run: `PYTHONPATH=scripts ./venv/bin/python -m pytest scripts/api_audit/tests/ -v`
Expected: All PASS

**Step 2: Run full CLI pipeline end-to-end**

Run:
```bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/final_matrix.json \
  --n-way 3
```

Expected: Success with meaningful output

**Step 3: Verify output makes sense**

Inspect `/tmp/final_matrix.json`:
- Feature count should be ~20-28 (not all 30 categories will be present)
- 2-way covered should be > 50% of total
- Gaps should include known uncovered combinations
- Low diversity list should be non-empty (common combos with few distinct approaches)

**Step 4: Final commit with any remaining fixes**

```bash
git add -A
git commit -m "feat: Phase 1 coverage analysis complete — feature detection + combination matrix + CLI integration"
```

---

## Summary of Deliverables

| Task | What | Files |
|------|------|-------|
| 1 | Feature categories config | `docs/feature_categories.json` |
| 2 | Interaction topology config | `docs/interaction_topology.json` |
| 3 | Test infrastructure + config validation | `tests/__init__.py`, `conftest.py`, `test_config_validation.py` |
| 4 | Feature detection core | `feature_detection.py`, `test_feature_detection.py` |
| 5 | Feature detection depth tests | `test_feature_detection.py` (extended) |
| 6 | Combination matrix core | `combination_matrix.py`, `test_combination_matrix.py` |
| 7 | Incremental merge + report tests | `test_combination_matrix.py` (extended) |
| 8 | CLI integration | `__main__.py` (modified), `test_phase1_integration.py` |
| 9 | Edge case tests | `test_edge_cases.py` |
| 10 | Benchmark + full corpus validation | `test_benchmark.py` |
| 11 | Final validation | (no new files) |
