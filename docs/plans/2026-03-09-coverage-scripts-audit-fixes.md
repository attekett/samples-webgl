# Coverage Scripts Audit Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 12 identified defects in the coverage detection pipeline — cache invalidation, corpus scope, runtime filtering, depth surfacing, combination coverage integration, method overlap, API surface report, GLSL detail, and temporal snapshots.

**Architecture:** Fixes are layered bottom-up: cache → corpus scope → CLI flags on `feature_coverage.py` → new combo/surface reports → minor cosmetics. All changes must pass existing tests in `scripts/api_audit/tests/` before new tests are added.

**Tech Stack:** Python 3, pytest (`scripts/api_audit/tests/`), tree-sitter-javascript, `docs/feature_categories.json`, `docs/webgl_api_surface.json`, `scripts/api_audit/combination_matrix.py` (already exists).

---

## Test command
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

All tasks follow TDD: write the failing test, confirm it fails, implement, confirm it passes, commit.

---

## Task 1: Fix cache invalidation when `feature_categories.json` changes

**Problem:** `FileCache.lookup/store` keys on `SHA256(seed_content)` only. Changing
`feature_categories.json` returns stale per-file feature results from cache with no
invalidation.

**Files:**
- Modify: `scripts/api_audit/cache.py`
- Modify: `scripts/feature_coverage.py:66-114` (the `analyze_file` function)
- Test: `scripts/api_audit/tests/test_cache.py` (new file)

**Step 1: Write the failing test**

Create `scripts/api_audit/tests/test_cache.py`:

```python
"""Tests for FileCache invalidation behaviour."""
import json
import tempfile
from pathlib import Path

import pytest

from api_audit.cache import FileCache


@pytest.fixture
def tmp_cache(tmp_path):
    return FileCache(tmp_path / "cache")


def test_store_and_lookup_same_config(tmp_cache):
    """Cache hit when both content and config hash are identical."""
    tmp_cache.store("f.html", "content", {"features": ["fbo"]}, config_hash="abc")
    result = tmp_cache.lookup("f.html", "content", config_hash="abc")
    assert result == {"features": ["fbo"]}


def test_different_config_hash_is_miss(tmp_cache):
    """Cache miss when config hash changes even if seed content is identical."""
    tmp_cache.store("f.html", "content", {"features": ["fbo"]}, config_hash="abc")
    result = tmp_cache.lookup("f.html", "content", config_hash="xyz")
    assert result is None


def test_different_content_is_miss(tmp_cache):
    """Cache miss when seed content changes."""
    tmp_cache.store("f.html", "contentA", {"features": ["fbo"]}, config_hash="abc")
    result = tmp_cache.lookup("f.html", "contentB", config_hash="abc")
    assert result is None


def test_no_config_hash_backward_compat(tmp_cache):
    """Empty config_hash (default) still works."""
    tmp_cache.store("f.html", "content", {"features": []})
    result = tmp_cache.lookup("f.html", "content")
    assert result == {"features": []}
```

**Step 2: Run to confirm failure**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_cache.py -v
```
Expected: `test_different_config_hash_is_miss` and `test_store_and_lookup_same_config` fail because the current signatures don't accept `config_hash`.

**Step 3: Implement the fix in `cache.py`**

Change `store` and `lookup` signatures to accept an optional `config_hash`:

```python
def store(self, filename: str, content: str, data: dict, config_hash: str = ""):
    self._layer1_dir.mkdir(parents=True, exist_ok=True)
    combined = content + "\x00" + config_hash
    content_hash = self._hash(combined)
    cache_file = self._layer1_dir / f'{content_hash}.json'
    cache_file.write_text(json.dumps(data))

def lookup(self, filename: str, content: str, config_hash: str = "") -> dict | None:
    combined = content + "\x00" + config_hash
    content_hash = self._hash(combined)
    cache_file = self._layer1_dir / f'{content_hash}.json'
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    return None
```

**Step 4: Thread the config hash through `feature_coverage.py`**

In `main()`, compute the hash once from the categories file bytes. In `analyze_file()`, accept and forward it:

```python
# In main(), after loading cats_config:
import hashlib
cats_config_hash = hashlib.sha256(args.categories.read_bytes()).hexdigest()[:16]

# Pass to analyze_file:
fp = analyze_file(f, surface, cats_config, cache, config_hash=cats_config_hash)
```

```python
# analyze_file signature change:
def analyze_file(filepath, surface, cats_config, cache=None, config_hash=""):
    content = filepath.read_text()
    if cache:
        cached = cache.lookup(filepath.name, content, config_hash=config_hash)
        if cached and "features" in cached:
            return cached
    # ... existing logic ...
    if cache:
        cache.store(filepath.name, content, {...}, config_hash=config_hash)
```

**Step 5: Run all tests to confirm pass**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```
Expected: all tests pass including the 4 new cache tests.

**Step 6: Commit**
```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/cache.py scripts/feature_coverage.py scripts/api_audit/tests/test_cache.py
git commit -m "fix: invalidate feature cache when feature_categories.json changes"
```

---

## Task 2: Fix `analyze_corpus.sh` to cover the full corpus

**Problem:** Every metric in `analyze_corpus.sh` hardcodes `agent_outputs/mutation_b*.html`,
silently omitting ~30% of seeds: `seed_*`, `creative_*`, `edge_cases_*`, `webgl2_*`, and all
66 files in `samples-webgl/`.

**Files:**
- Modify: `scripts/analyze_corpus.sh`

No new tests needed — this is a shell script correction.

**Step 1: Identify the lines that need changing**

Open `scripts/analyze_corpus.sh`. Every occurrence of `agent_outputs/mutation_b*.html` is
a scope bug. The fix depends on context:

- File count, total lines, total size, average lines → use `agent_outputs/*.html samples-webgl/*.html` (all seeds)
- Try-catch density, API call density, mutation patterns → same all-seed glob
- Keep a separate **"## 2b. Mutation Seed Batch Stats"** section with the `mutation_b*` glob for batch-specific metrics

**Step 2: Apply the fix**

Replace every `agent_outputs/mutation_b*.html` with:
```bash
$(find agent_outputs/ samples-webgl/ -maxdepth 1 -name "*.html")
```

But keep the batch-specific section using the old glob, under a renamed heading.

Minimal diff — only the glob strings change. Do not restructure the script.

**Step 3: Manually verify output**
```bash
cd /home/attekett/git/samples-webgl && bash scripts/analyze_corpus.sh 2>/dev/null | head -40
```
Expected: "File Count" should now read ~367, not ~259.

**Step 4: Commit**
```bash
git add scripts/analyze_corpus.sh
git commit -m "fix: analyze_corpus.sh now covers full corpus (367 seeds), not just mutation_b*"
```

---

## Task 3: Add `--passed-only` flag to `feature_coverage.py`

**Problem:** Seeds that fail the extension guard (`throw new Error("UNSUPPORTED_EXTENSIONS: ...")`)
still count toward extension coverage because the AST analysis sees the `getExtension` calls
regardless of runtime outcome. Adding `--passed-only` restricts coverage to seeds whose
Playwright test run reported `"passed": true`.

**Files:**
- Modify: `scripts/feature_coverage.py`
- Test: `scripts/api_audit/tests/test_passed_filter.py` (new file)

**Step 1: Write the failing test**

Create `scripts/api_audit/tests/test_passed_filter.py`:

```python
"""Tests for the passed-only seed filter."""
import json
import tempfile
from pathlib import Path

import pytest


def write_seed_pair(directory: Path, name: str, passed: bool) -> Path:
    """Write an HTML seed and its sibling JSON result file."""
    html = directory / f"{name}.html"
    js_result = directory / f"{name}.json"
    html.write_text("<html><body><script>const gl = null;</script></body></html>")
    js_result.write_text(json.dumps({"passed": passed, "console_logs": []}))
    return html


def test_is_passed_true(tmp_path):
    from feature_coverage import is_passed
    html = write_seed_pair(tmp_path, "seed_pass", passed=True)
    assert is_passed(html) is True


def test_is_passed_false(tmp_path):
    from feature_coverage import is_passed
    html = write_seed_pair(tmp_path, "seed_fail", passed=False)
    assert is_passed(html) is False


def test_is_passed_no_json(tmp_path):
    from feature_coverage import is_passed
    html = tmp_path / "seed_no_result.html"
    html.write_text("<html></html>")
    assert is_passed(html) is False


def test_is_passed_malformed_json(tmp_path):
    from feature_coverage import is_passed
    html = tmp_path / "seed.html"
    html.write_text("<html></html>")
    (tmp_path / "seed.json").write_text("not json {{{")
    assert is_passed(html) is False
```

**Step 2: Run to confirm failure**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_passed_filter.py -v
```
Expected: ImportError — `is_passed` not yet defined.

**Step 3: Implement `is_passed` and wire `--passed-only` in `feature_coverage.py`**

Add after the imports section in `feature_coverage.py`:

```python
def is_passed(filepath: Path) -> bool:
    """Return True if the seed's sibling .json result reports passed: true."""
    json_path = filepath.with_suffix('.json')
    if not json_path.exists():
        return False
    try:
        data = json.loads(json_path.read_text())
        return bool(data.get('passed', False))
    except Exception:
        return False
```

Add the CLI argument in `main()`:
```python
parser.add_argument("--passed-only", action="store_true",
                    help="Only count seeds whose sibling .json result has passed:true")
```

In the file-walking loop, after `for f in html_files:`, add:
```python
        if args.passed_only and not is_passed(f):
            continue
```

**Step 4: Run all tests**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

**Step 5: Manual sanity check**
```bash
cd /home/attekett/git/samples-webgl
python scripts/feature_coverage.py --passed-only 2>/dev/null | head -30
python scripts/feature_coverage.py            2>/dev/null | head -30
```
The `--passed-only` run should show equal or lower seed counts for extension categories.

**Step 6: Commit**
```bash
git add scripts/feature_coverage.py scripts/api_audit/tests/test_passed_filter.py
git commit -m "feat: add --passed-only flag to feature_coverage.py to exclude runtime-failing seeds"
```

---

## Task 4: Surface feature depth in the main coverage table

**Problem:** `feature_depth` (present / meaningful / deep) is computed and cached but never
shown. Depth "present" and depth "deep" are equally weighted in the current report, so 20%
coverage at "present" looks identical to 20% at "deep".

**Files:**
- Modify: `scripts/feature_coverage.py`
- Test: `scripts/api_audit/tests/test_depth_display.py` (new file)

**Step 1: Write the failing test**

Create `scripts/api_audit/tests/test_depth_display.py`:

```python
"""Tests for depth column formatting helpers."""
import pytest


def test_depth_summary_format():
    from feature_coverage import format_depth_summary
    result = format_depth_summary({"present": 3, "meaningful": 5, "deep": 2})
    assert result == "P:3 M:5 D:2"


def test_depth_summary_all_zero():
    from feature_coverage import format_depth_summary
    result = format_depth_summary({"present": 0, "meaningful": 0, "deep": 0})
    assert result == "P:0 M:0 D:0"


def test_depth_summary_only_deep():
    from feature_coverage import format_depth_summary
    result = format_depth_summary({"present": 0, "meaningful": 0, "deep": 10})
    assert result == "P:0 M:0 D:10"
```

**Step 2: Run to confirm failure**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_depth_display.py -v
```
Expected: ImportError — `format_depth_summary` not yet defined.

**Step 3: Implement the changes**

Add helper to `feature_coverage.py`:
```python
def format_depth_summary(depth_counts: dict) -> str:
    """Format {present: N, meaningful: N, deep: N} as 'P:N M:N D:N'."""
    p = depth_counts.get("present", 0)
    m = depth_counts.get("meaningful", 0)
    d = depth_counts.get("deep", 0)
    return f"P:{p} M:{m} D:{d}"
```

In `main()`, accumulate depth counts per feature alongside `feature_counts`:
```python
feature_depths = {}  # {feat: {"present": N, "meaningful": N, "deep": N}}
...
for feat in fp["features"]:
    ...
    fd = fp.get("feature_depth", {}).get(feat, "present")
    if feat not in feature_depths:
        feature_depths[feat] = {"present": 0, "meaningful": 0, "deep": 0}
    feature_depths[feat][fd] = feature_depths[feat].get(fd, 0) + 1
```

Note: the cache currently only stores `"features"` and `"feature_depth"` per file. That's
sufficient — `fp["feature_depth"]` is already returned by `analyze_file()`.

Update the table header and rows:
```python
print(f"| {'Feature Category':<40} | {'Seeds':>7} | {'Coverage':>9} | {'Depth':<14} |")
print(f"|{'-'*42}|{'-'*9}|{'-'*11}|{'-'*16}|")
...
depth_str = format_depth_summary(feature_depths.get(feat, {}))
print(f"| {display:<40} | {count:>4}/{total:<3} | {pct:>4}% {bar} | {depth_str:<14} |")
```

**Step 4: Run all tests**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

**Step 5: Visual check**
```bash
cd /home/attekett/git/samples-webgl && python scripts/feature_coverage.py 2>/dev/null
```
The table should now have a `Depth` column.

**Step 6: Commit**
```bash
git add scripts/feature_coverage.py scripts/api_audit/tests/test_depth_display.py
git commit -m "feat: add depth breakdown column (P/M/D) to feature coverage table"
```

---

## Task 5: Add combination coverage summary to `feature_coverage.py`

**Problem:** `feature_coverage.py` reports only marginal per-feature counts. The 2-way and
3-way combination gaps (the core corpus purpose) are invisible without running a separate,
undocumented internal script. `combination_matrix.py` already exists and is complete.

**Files:**
- Modify: `scripts/feature_coverage.py`
- Test: `scripts/api_audit/tests/test_combination_summary.py` (new file)

**Step 1: Write the failing test**

Create `scripts/api_audit/tests/test_combination_summary.py`:

```python
"""Tests for combination coverage summary helpers."""
import pytest


def test_combination_summary_counts():
    from feature_coverage import summarize_combinations
    matrix = {
        ("fbo", "sync"): {"seed_count": 3, "topology_connected": True},
        ("fbo", "query"): {"seed_count": 0, "topology_connected": True},
        ("sync", "query"): {"seed_count": 1, "topology_connected": True},
        ("fbo", "vao"): {"seed_count": 0, "topology_connected": False},
    }
    result = summarize_combinations(matrix)
    assert result["total"] == 4
    assert result["connected"] == 3
    assert result["covered"] == 2      # fbo+sync, sync+query
    assert result["gap_count"] == 1    # fbo+query only (fbo+vao is disconnected)


def test_combination_summary_full_coverage():
    from feature_coverage import summarize_combinations
    matrix = {
        ("a", "b"): {"seed_count": 5, "topology_connected": True},
    }
    result = summarize_combinations(matrix)
    assert result["gap_count"] == 0
    assert result["pct"] == 100
```

**Step 2: Run to confirm failure**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_combination_summary.py -v
```

**Step 3: Implement `summarize_combinations` and wire it in**

Add to `feature_coverage.py`:
```python
def summarize_combinations(matrix: dict) -> dict:
    """Summarize n-way combination matrix stats for display.

    Args:
        matrix: {combo_tuple: {seed_count, topology_connected, ...}}

    Returns:
        dict with total, connected, covered, gap_count, pct keys.
    """
    total = len(matrix)
    connected = sum(1 for d in matrix.values() if d.get("topology_connected", True))
    covered = sum(
        1 for d in matrix.values()
        if d.get("topology_connected", True) and d["seed_count"] >= 1
    )
    gap_count = connected - covered
    pct = round(covered * 100 / connected, 1) if connected else 0
    return {"total": total, "connected": connected, "covered": covered,
            "gap_count": gap_count, "pct": pct}
```

Add CLI argument:
```python
parser.add_argument("--combinations", type=int, default=0, metavar="N",
                    help="Also report N-way combination coverage gaps (2 or 3)")
```

In `main()`, after printing the feature table, if `args.combinations >= 2`:
```python
if args.combinations >= 2:
    from api_audit.combination_matrix import compute_matrix
    topology_path = Path("docs/interaction_topology.json")
    topology = json.loads(topology_path.read_text()) if topology_path.exists() else None
    corpus = {str(f): fp for f, fp in zip(html_files, fingerprints) if fp}
    matrix = compute_matrix(corpus, n=args.combinations,
                             interaction_topology=topology,
                             categories_config=cats_config)
    summary = summarize_combinations(matrix)
    n = args.combinations
    print(f"## {n}-Way Combination Coverage")
    print(f"Connected combos: {summary['connected']}, "
          f"covered: {summary['covered']} ({summary['pct']}%), "
          f"gaps: {summary['gap_count']}")
    # Print top-10 gaps by combo name
    gaps = sorted(
        [(c, d) for c, d in matrix.items()
         if d.get("topology_connected", True) and d["seed_count"] == 0],
        key=lambda x: x[0]
    )[:10]
    if gaps:
        print("Top uncovered combos:")
        for combo, _ in gaps:
            print(f"  - {' + '.join(combo)}")
    print()
```

Note: This requires tracking fingerprints alongside the file loop. Refactor the file loop to
collect `fingerprints` list in parallel with `html_files`.

**Step 4: Run all tests**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

**Step 5: Integration check**
```bash
cd /home/attekett/git/samples-webgl && python scripts/feature_coverage.py --combinations 2 2>/dev/null | tail -20
```
Expected: a combination coverage section after the feature table.

**Step 6: Commit**
```bash
git add scripts/feature_coverage.py scripts/api_audit/tests/test_combination_summary.py
git commit -m "feat: add --combinations N flag to feature_coverage.py for n-way gap summary"
```

---

## Task 6: Add API surface method coverage report

**Problem:** There is no way to see which individual WebGL2 API methods are never exercised
by any seed. The feature category report only shows categories — rare methods like
`getBufferSubData`, `invalidateSubFramebuffer`, or `copyTexSubImage3D` could be completely
absent and you would not know.

**Files:**
- Modify: `scripts/feature_coverage.py`
- Test: `scripts/api_audit/tests/test_api_surface_report.py` (new file)

**Step 1: Write the failing test**

Create `scripts/api_audit/tests/test_api_surface_report.py`:

```python
"""Tests for API surface method coverage helpers."""
import pytest


def test_compute_method_coverage_basic():
    from feature_coverage import compute_method_coverage
    surface_methods = {"createBuffer", "bindBuffer", "bufferData", "deleteBuffer"}
    seen_methods = {"createBuffer", "bindBuffer"}
    result = compute_method_coverage(surface_methods, seen_methods)
    assert result["total"] == 4
    assert result["exercised"] == 2
    assert result["pct"] == 50
    assert "bufferData" in result["never_seen"]
    assert "deleteBuffer" in result["never_seen"]
    assert "createBuffer" not in result["never_seen"]


def test_compute_method_coverage_empty_corpus():
    from feature_coverage import compute_method_coverage
    result = compute_method_coverage({"m1", "m2"}, set())
    assert result["exercised"] == 0
    assert result["pct"] == 0
    assert set(result["never_seen"]) == {"m1", "m2"}


def test_compute_method_coverage_full():
    from feature_coverage import compute_method_coverage
    methods = {"a", "b", "c"}
    result = compute_method_coverage(methods, methods)
    assert result["pct"] == 100
    assert result["never_seen"] == []
```

**Step 2: Run to confirm failure**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_api_surface_report.py -v
```

**Step 3: Implement `compute_method_coverage` and wire `--api-surface-coverage`**

Add to `feature_coverage.py`:
```python
def compute_method_coverage(surface_methods: set, seen_methods: set) -> dict:
    """Compute what fraction of API surface methods appear in the corpus.

    Args:
        surface_methods: set of method names from webgl_api_surface.json
        seen_methods: set of method names actually found across all corpus files

    Returns:
        dict with total, exercised, pct, never_seen (sorted list)
    """
    total = len(surface_methods)
    exercised = len(seen_methods & surface_methods)
    pct = round(exercised * 100 / total, 1) if total else 0
    never_seen = sorted(surface_methods - seen_methods)
    return {"total": total, "exercised": exercised, "pct": pct, "never_seen": never_seen}
```

Add CLI argument:
```python
parser.add_argument("--api-surface-coverage", action="store_true",
                    help="Show per-method API surface coverage report")
```

In `main()`, after the feature table (and combination section), if `args.api_surface_coverage`:
```python
if args.api_surface_coverage:
    surface_method_names = set(surface.get("methods", {}).keys())
    # Accumulate seen methods from all file analyses
    all_seen = set()
    for fp in fingerprints:
        if fp:
            for feat_methods in fp.get("methods_per_feature", {}).values():
                all_seen.update(feat_methods)
    report = compute_method_coverage(surface_method_names, all_seen)
    print(f"## API Surface Method Coverage")
    print(f"{report['exercised']}/{report['total']} methods exercised "
          f"({report['pct']}%)")
    if report["never_seen"]:
        print(f"Never-seen methods ({len(report['never_seen'])}):")
        for m in report["never_seen"]:
            print(f"  - {m}")
    print()
```

**Step 4: Run all tests**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

**Step 5: Integration check**
```bash
cd /home/attekett/git/samples-webgl && python scripts/feature_coverage.py --api-surface-coverage 2>/dev/null | grep -A 30 "API Surface"
```

**Step 6: Commit**
```bash
git add scripts/feature_coverage.py scripts/api_audit/tests/test_api_surface_report.py
git commit -m "feat: add --api-surface-coverage flag to report never-seen WebGL2 methods"
```

---

## Task 7: Document/fix method overlap between `instancing` and `draw_calls` categories

**Problem:** `drawArraysInstanced` and `drawElementsInstanced` appear in both `instancing`
and `draw_calls` in `feature_categories.json`. This is intentional (instanced draws ARE draw
calls) but undocumented and causes the two categories to always co-occur, inflating the
effective draw_calls coverage number.

**Files:**
- Modify: `docs/feature_categories.json`

No code changes. No new tests (the existing `test_feature_detection.py` tests will catch
regressions if the category definitions break something).

**Step 1: Run existing tests to establish baseline**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_feature_detection.py -v
```
All must pass.

**Step 2: Add `overlap_note` fields to both categories**

In `docs/feature_categories.json`, add a `"overlap_note"` field (ignored by the pipeline,
purely documentary) to both `draw_calls` and `instancing`:

```json
"draw_calls": {
  "description": "...",
  "overlap_note": "drawArraysInstanced and drawElementsInstanced intentionally appear in both draw_calls and instancing: any instanced draw is also a draw call. instancing seeds always match draw_calls.",
  "methods": [...],
  ...
}
```

```json
"instancing": {
  "description": "...",
  "overlap_note": "drawArraysInstanced and drawElementsInstanced also appear in draw_calls. This is intentional. instancing is not in SKIP_UBIQUITOUS; draw_calls is.",
  "methods": [...],
  ...
}
```

**Step 3: Verify tests still pass**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

**Step 4: Commit**
```bash
git add docs/feature_categories.json
git commit -m "docs: add overlap_note to instancing+draw_calls categories explaining intentional method overlap"
```

---

## Task 8: Add `--glsl-detail` flag for per-builtin GLSL breakdown

**Problem:** The report shows `GLSL Builtins: N/367` as one number in the ubiquitous
footer. There is no visibility into which specific GLSL builtins (e.g. `inverse`,
`textureGather`, `packSnorm2x16`) are never used.

**Files:**
- Modify: `scripts/feature_coverage.py`
- Test: `scripts/api_audit/tests/test_glsl_detail.py` (new file)

**Step 1: Write the failing test**

Create `scripts/api_audit/tests/test_glsl_detail.py`:

```python
"""Tests for GLSL per-builtin detail helpers."""
import pytest


def test_aggregate_glsl_builtins_basic():
    from feature_coverage import aggregate_glsl_builtins
    fingerprints = [
        {"glsl_builtins": {"smoothstep", "texelFetch"}},
        {"glsl_builtins": {"smoothstep", "inverse"}},
        {"glsl_builtins": set()},
    ]
    result = aggregate_glsl_builtins(fingerprints)
    assert result["smoothstep"] == 2
    assert result["texelFetch"] == 1
    assert result["inverse"] == 1


def test_aggregate_glsl_builtins_empty():
    from feature_coverage import aggregate_glsl_builtins
    result = aggregate_glsl_builtins([])
    assert result == {}


def test_aggregate_glsl_builtins_missing_key():
    from feature_coverage import aggregate_glsl_builtins
    # fingerprint without glsl_builtins key is handled gracefully
    result = aggregate_glsl_builtins([{"features": ["fbo"]}])
    assert result == {}
```

Note: `aggregate_glsl_builtins` receives a list of `analyze_file()` result dicts.
To make this work, `analyze_file()` must also return the `glsl_builtins` set in its
result dict. Check if it currently does — if not, add `"glsl_builtins": set(glsl)` to
the result dict in `analyze_file()`.

**Step 2: Run to confirm failure**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_glsl_detail.py -v
```

**Step 3: Implement `aggregate_glsl_builtins` and wire `--glsl-detail`**

Add to `feature_coverage.py`:
```python
def aggregate_glsl_builtins(fingerprints: list) -> dict:
    """Count how many seeds use each GLSL builtin.

    Args:
        fingerprints: list of analyze_file() result dicts, each may have
            a "glsl_builtins" set.

    Returns:
        dict {builtin_name: seed_count}
    """
    counts = {}
    for fp in fingerprints:
        if fp is None:
            continue
        for b in fp.get("glsl_builtins", set()):
            counts[b] = counts.get(b, 0) + 1
    return counts
```

Update `analyze_file()` to also return `glsl_builtins` in its result:
```python
# After computing fp = detect_features(...)
return {**fp, "glsl_builtins": set(glsl)}
```

Add CLI argument:
```python
parser.add_argument("--glsl-detail", action="store_true",
                    help="Show per-GLSL-builtin seed counts")
```

In `main()`, after the feature table, if `args.glsl_detail`:
```python
if args.glsl_detail:
    glsl_counts = aggregate_glsl_builtins(fingerprints)
    all_builtins = set()
    for cat in cats_config.get("categories", {}).values():
        all_builtins.update(cat.get("glsl_functions", []))
    print("## GLSL Builtin Coverage")
    never = sorted(all_builtins - set(glsl_counts))
    used = sorted(glsl_counts.items(), key=lambda x: x[1], reverse=True)
    print(f"Used builtins ({len(used)}/{len(all_builtins)}):")
    for name, count in used:
        print(f"  {name:<30} {count:>4} seeds")
    if never:
        print(f"Never used ({len(never)}): {', '.join(never)}")
    print()
```

**Step 4: Run all tests**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

**Step 5: Integration check**
```bash
cd /home/attekett/git/samples-webgl && python scripts/feature_coverage.py --glsl-detail 2>/dev/null | grep -A 50 "GLSL Builtin"
```

**Step 6: Commit**
```bash
git add scripts/feature_coverage.py scripts/api_audit/tests/test_glsl_detail.py
git commit -m "feat: add --glsl-detail flag for per-builtin GLSL seed count breakdown"
```

---

## Task 9: Add temporal snapshot and diff commands

**Problem:** Coverage is always a snapshot with no visibility into how coverage changed
between rounds or batches. There is no way to measure the incremental value of new seeds.

**Files:**
- Modify: `scripts/feature_coverage.py`
- Test: `scripts/api_audit/tests/test_snapshot_diff.py` (new file)

**Step 1: Write the failing test**

Create `scripts/api_audit/tests/test_snapshot_diff.py`:

```python
"""Tests for coverage snapshot diff helpers."""
import pytest


def test_diff_coverage_added():
    from feature_coverage import diff_coverage_snapshots
    prev = {"fbo": {"seeds": 10, "pct": 5}, "sync": {"seeds": 3, "pct": 2}}
    curr = {"fbo": {"seeds": 15, "pct": 7}, "sync": {"seeds": 3, "pct": 2},
            "query": {"seeds": 2, "pct": 1}}
    result = diff_coverage_snapshots(prev, curr)
    # fbo grew
    assert result["changed"]["fbo"]["delta_seeds"] == 5
    assert result["changed"]["fbo"]["delta_pct"] == pytest.approx(2.0)
    # sync unchanged
    assert "sync" not in result["changed"]
    # query is new
    assert "query" in result["new_features"]


def test_diff_coverage_removed():
    from feature_coverage import diff_coverage_snapshots
    prev = {"fbo": {"seeds": 5, "pct": 3}, "ubo": {"seeds": 2, "pct": 1}}
    curr = {"fbo": {"seeds": 5, "pct": 3}}
    result = diff_coverage_snapshots(prev, curr)
    assert "ubo" in result["removed_features"]


def test_diff_coverage_no_change():
    from feature_coverage import diff_coverage_snapshots
    snap = {"fbo": {"seeds": 5, "pct": 3}}
    result = diff_coverage_snapshots(snap, snap)
    assert result["changed"] == {}
    assert result["new_features"] == []
    assert result["removed_features"] == []
```

**Step 2: Run to confirm failure**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_snapshot_diff.py -v
```

**Step 3: Implement snapshot/diff in `feature_coverage.py`**

Add the diff helper:
```python
def diff_coverage_snapshots(prev: dict, curr: dict) -> dict:
    """Compute delta between two coverage snapshots.

    Each snapshot is {feature_name: {seeds: N, pct: float}}.

    Returns:
        dict with:
          changed: {feature: {delta_seeds, delta_pct}} — only non-zero deltas
          new_features: [feature names appearing in curr but not prev]
          removed_features: [feature names in prev but not curr]
    """
    prev_keys = set(prev)
    curr_keys = set(curr)
    changed = {}
    for feat in prev_keys & curr_keys:
        ds = curr[feat]["seeds"] - prev[feat]["seeds"]
        dp = round(curr[feat]["pct"] - prev[feat]["pct"], 1)
        if ds != 0 or dp != 0.0:
            changed[feat] = {"delta_seeds": ds, "delta_pct": dp}
    return {
        "changed": changed,
        "new_features": sorted(curr_keys - prev_keys),
        "removed_features": sorted(prev_keys - curr_keys),
    }
```

Add CLI arguments:
```python
parser.add_argument("--snapshot", type=Path, metavar="FILE",
                    help="Save current coverage to FILE as JSON snapshot")
parser.add_argument("--diff", type=Path, metavar="PREV_SNAPSHOT",
                    help="Compare current coverage against PREV_SNAPSHOT and show delta")
```

In `main()`, after computing `feature_counts`, build the snapshot dict:
```python
snapshot = {feat: {"seeds": count, "total": total,
                    "pct": round(count * 100 / total, 1) if total else 0}
            for feat, count in feature_counts.items()}

if args.snapshot:
    args.snapshot.write_text(json.dumps(snapshot, indent=2))
    print(f"Snapshot saved to {args.snapshot}")

if args.diff and args.diff.exists():
    prev_snapshot = json.loads(args.diff.read_text())
    delta = diff_coverage_snapshots(prev_snapshot, snapshot)
    print("## Coverage Delta")
    if delta["new_features"]:
        print(f"New features: {', '.join(delta['new_features'])}")
    if delta["removed_features"]:
        print(f"Removed features: {', '.join(delta['removed_features'])}")
    if delta["changed"]:
        for feat, d in sorted(delta["changed"].items()):
            sign = "+" if d["delta_seeds"] >= 0 else ""
            print(f"  {feat:<40} {sign}{d['delta_seeds']} seeds  "
                  f"({sign}{d['delta_pct']}%)")
    else:
        print("No coverage changes.")
    print()
```

**Step 4: Run all tests**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

**Step 5: Integration check**
```bash
cd /home/attekett/git/samples-webgl
python scripts/feature_coverage.py --snapshot /tmp/coverage_before.json 2>/dev/null
python scripts/feature_coverage.py --diff /tmp/coverage_before.json 2>/dev/null | grep -A 20 "Coverage Delta"
```
Expected: "No coverage changes." (same run).

**Step 6: Commit**
```bash
git add scripts/feature_coverage.py scripts/api_audit/tests/test_snapshot_diff.py
git commit -m "feat: add --snapshot and --diff flags to feature_coverage.py for temporal tracking"
```

---

## Task 10: Handle chained extension method calls in `call_analysis.py`

**Problem:** `gl.getExtension('OES_draw_buffers_indexed').enableiOES(0, gl.BLEND)` —
an inline chained call — is silently dropped. `_process_call` requires `obj.type == 'identifier'`
but the receiver here is a `call_expression`. This pattern appears rarely but is valid.

**Files:**
- Modify: `scripts/api_audit/call_analysis.py`
- Test: `scripts/api_audit/tests/test_chained_ext.py` (new file)

**Step 1: Write the failing test**

Create `scripts/api_audit/tests/test_chained_ext.py`:

```python
"""Tests for chained extension method call detection."""
import pytest
from api_audit.parse import parse_js
from api_audit.const_propagation import resolve_constants
from api_audit.context import detect_context
from api_audit.call_analysis import analyze_calls


SURFACE = {
    "methods": {"viewport": {"overloads": [{"arity": 4, "params": []}]}},
    "extensions": {
        "OES_draw_buffers_indexed": {
            "methods": {
                "enableiOES": {"overloads": [{"arity": 2, "params": []}]},
                "blendFunciOES": {"overloads": [{"arity": 4, "params": []}]},
            }
        }
    }
}


def _analyze(js_source: str):
    root = parse_js(js_source)
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    return analyze_calls(root, ctx, consts, SURFACE)


def test_chained_extension_method_detected():
    """gl.getExtension('ext').method() should be tracked."""
    js = """
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2');
    gl.getExtension('OES_draw_buffers_indexed').enableiOES(0, gl.BLEND);
    """
    result = _analyze(js)
    assert "OES_draw_buffers_indexed" in result.extension_methods
    assert "enableiOES" in result.extension_methods["OES_draw_buffers_indexed"]


def test_chained_unknown_extension_ignored():
    """Chained call on unknown extension is silently dropped."""
    js = """
    const gl = document.createElement('canvas').getContext('webgl2');
    gl.getExtension('UNKNOWN_EXT').someMethod(0);
    """
    result = _analyze(js)
    assert result.extension_methods == {}
```

**Step 2: Run to confirm failure**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/test_chained_ext.py -v
```
Expected: `test_chained_extension_method_detected` fails — chained call not detected.

**Step 3: Implement the fix in `call_analysis.py`**

In `_process_call`, after the existing `obj.type != 'identifier'` early return, add a
special case for chained `getExtension().method()`:

```python
# Check for chained pattern: gl.getExtension('EXT_NAME').method(args)
if obj.type == 'call_expression':
    # obj is a call_expression — check if it's a getExtension call
    inner_callee = obj.child_by_field_name('function')
    if inner_callee is not None and inner_callee.type == 'member_expression':
        inner_obj = inner_callee.child_by_field_name('object')
        inner_prop = inner_callee.child_by_field_name('property')
        if (inner_obj and inner_prop
                and inner_obj.type == 'identifier'
                and _node_text(inner_obj) in context_vars
                and _node_text(inner_prop) == 'getExtension'):
            # Extract the extension name argument
            inner_args = obj.child_by_field_name('arguments')
            if inner_args:
                for child in inner_args.children:
                    if child.type == 'string':
                        fragments = [c for c in child.children
                                     if c.type == 'string_fragment']
                        if fragments:
                            ext_name_str = fragments[0].text.decode('utf-8')
                            ext_info = surface.get('extensions', {}).get(ext_name_str, {})
                            if method_name in ext_info.get('methods', {}):
                                result.extension_methods.setdefault(ext_name_str, {})
                                result.extension_methods[ext_name_str].setdefault(
                                    method_name, []).append(
                                    CallRecord(constants=set(), arity=arity))
                            return
    return  # Unknown chained receiver, ignore
```

This block goes immediately after the existing `if not is_context_call and ext_name is None: return` line.

**Step 4: Run all tests**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v
```

**Step 5: Commit**
```bash
git add scripts/api_audit/call_analysis.py scripts/api_audit/tests/test_chained_ext.py
git commit -m "fix: detect chained gl.getExtension('EXT').method() calls in call_analysis"
```

---

## Final Verification

After all 10 tasks are complete:

**Step 1: Run the full test suite**
```bash
cd /home/attekett/git/samples-webgl/scripts && python -m pytest api_audit/tests/ -v --tb=short
```
Expected: all tests pass, no failures.

**Step 2: Run the full coverage pipeline with all new flags**
```bash
cd /home/attekett/git/samples-webgl
python scripts/feature_coverage.py \
  --passed-only \
  --combinations 2 \
  --api-surface-coverage \
  --glsl-detail \
  --snapshot /tmp/coverage_$(date +%Y%m%d).json \
  2>/dev/null
```
Expected: no errors, complete output with all sections.

**Step 3: Run the corpus analysis**
```bash
cd /home/attekett/git/samples-webgl && bash scripts/analyze_corpus.sh 2>/dev/null | head -20
```
Expected: "File Count" shows ~367.

**Step 4: Final commit tag**
```bash
git log --oneline -12
```
Should show 10 commits from this plan.
