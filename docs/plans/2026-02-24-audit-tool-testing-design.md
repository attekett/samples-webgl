# Audit Tool Testing Design

## Problem

The API surface auditor (`scripts/api_audit/`) is a complex tool with 8 interacting analysis passes. It will be the authoritative coverage oracle for the fuzzing corpus. Without a testing strategy, bugs introduced during the M2-M5 milestone progression accumulate silently and corrupt coverage measurements.

## Goals

1. **Regression safety net** (primary): Catch breakage when the auditor is modified. Fast, runs on every change.
2. **Correctness oracle** (secondary): Prove each analysis pass handles tricky edge cases. Added incrementally per milestone.

## Auditor module structure

The auditor is structured as a multi-module package with one module per analysis pass:

```
scripts/api_audit/
├── __init__.py
├── __main__.py            # CLI entry point
├── html_extract.py        # <script> content extraction
├── parse.py               # tree-sitter JS parsing
├── context.py             # Context aliases, extension detection
├── const_propagation.py   # Two-pass const/template/array resolution
├── call_analysis.py       # Method call analysis, overload disambiguation
├── glsl.py                # Shader extraction, GLSL built-in matching
├── lint.py                # Convention violation detection
├── cache.py               # Two-layer SHA256-keyed caching
└── report.py              # Gap report generation (full + delta)
```

Each module exposes pure functions that accept AST nodes or intermediate data structures and return results. This makes each pass independently testable without running the full pipeline.

## Test directory structure

```
tests/
├── conftest.py                  # Shared pytest fixtures
├── fixtures/
│   ├── synthetic/               # Purpose-built HTML files (10-30 lines each)
│   │   ├── basic_draw.html
│   │   ├── const_forward_ref.html
│   │   ├── const_gl_alias.html
│   │   ├── ext_array_pattern.html
│   │   ├── ext_direct_assign.html
│   │   ├── ext_both_patterns.html
│   │   ├── ext_bare_enable.html
│   │   ├── helper_single_level.html
│   │   ├── overload_size.html
│   │   ├── overload_data.html
│   │   ├── shader_template.html
│   │   ├── glsl_builtins.html
│   │   ├── return_compare.html
│   │   └── lint_violations.html
│   ├── seeds/                   # Pinned copies of real corpus seeds
│   │   ├── README.md
│   │   └── (3-5 copied seeds with expected_output.json each)
│   └── surface/
│       └── test_surface.json    # Minimal hand-written API surface
├── test_html_extract.py
├── test_context.py
├── test_const_propagation.py
├── test_call_analysis.py
├── test_glsl.py
├── test_lint.py
├── test_cache.py
├── test_report.py
└── test_integration.py
```

Key decisions:

- **Each test file maps 1:1 to an auditor module.** When a test fails, you immediately know which pass broke.
- **Synthetic fixtures isolate one behavior per file.** 10-30 lines of HTML, named for the behavior they test.
- **Pinned real seeds** are copied into `tests/fixtures/seeds/` so corpus edits don't break tests. Each has a companion `expected_output.json` with manually verified call data.
- **Frozen test surface JSON** contains ~5 methods, ~15 constants, 1 extension, a few GLSL builtins. Hand-written, not generated. Test failures always indicate auditor bugs, never spec drift.

## Shared fixtures

`conftest.py` provides reusable fixtures:

```python
import pytest
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.fixture
def surface():
    """Minimal API surface for testing."""
    return json.loads((FIXTURES / "surface" / "test_surface.json").read_text())

@pytest.fixture
def parse_html():
    """Returns a function that extracts script and parses AST."""
    from api_audit.html_extract import extract_script
    from api_audit.parse import parse_js
    def _parse(filename):
        html = (FIXTURES / "synthetic" / filename).read_text()
        script = extract_script(html)
        return parse_js(script)
    return _parse
```

The test surface JSON contains only what tests need:

- Methods: `bufferData`, `texImage2D`, `drawArrays`, `shaderSource`, `enable` (with known overloads)
- Constants: `TRIANGLES`, `RGBA`, `FLOAT`, `UNSIGNED_BYTE`, `DEPTH_TEST`, `FRAMEBUFFER_COMPLETE`, `ARRAY_BUFFER` (across different roles)
- Extension: `OES_vertex_array_object` (with methods and constants)
- GLSL builtins: `texelFetch`, `packHalf2x16`, `dFdx`

## Unit tests by module

### test_html_extract.py

- Extracts `<script>` content from HTML
- Multiple `<script>` tags concatenated in order
- Empty script tag returns empty string
- Malformed HTML (unclosed tags) doesn't crash

### test_context.py

- `getContext('webgl2')` assigns to variable: detected as WebGL2
- `getContext('webgl2') || getContext('webgl')`: tagged as WebGL1-capable
- Array pattern: `REQUIRED_EXTENSIONS` forEach: extension names extracted
- Direct assignment: `const ext = gl.getExtension('...')`: alias tracked
- Both patterns in same file: both detected, no duplicates
- Bare enable: `gl.getExtension('...')` as expression statement: extension recorded, no alias
- Empty `REQUIRED_EXTENSIONS = []`: no extensions, no crash
- Helper function: `createShader(gl, type, source)` called with known context: `gl` tracked inside function body

### test_const_propagation.py

- `const RGBA = gl.RGBA`: resolves to constant
- Forward reference (variable used before declaration): resolves in pass 2
- Template literal: `` const vs = `#version 300 es...` ``: string content captured
- Array literal: `const arr = ['A', 'B']`: elements extracted
- Chain: `const A = gl.RGBA; const B = A`: B resolves to `gl.RGBA`
- Unresolvable: `const x = someFunction()`: stays unresolved, no crash

### test_call_analysis.py

- `gl.drawArrays(gl.TRIANGLES, 0, 6)`: method recorded, TRIANGLES in target role
- Const-propagated argument: `const mode = gl.TRIANGLES; gl.drawArrays(mode, 0, 6)`: same result
- Overload by arity: `texImage2D` with 6 args vs 9 args: correct overload selected
- Constructor disambiguation: `gl.bufferData(target, new Float32Array(...), usage)`: data overload
- Numeric disambiguation: `gl.bufferData(target, 1024, usage)`: size overload
- Bitwise OR: `gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)`: both constants recorded
- Extension method: `ext.createVertexArrayOES()` where ext is tracked alias: recorded under extension
- Unknown receiver: `foo.drawArrays(...)`: ignored

### test_glsl.py

- Shader containing `texelFetch(...)`: matched
- Shader containing `packHalf2x16(x)`: matched
- `myTexelFetch(...)`: not matched (word boundary)
- GLSL comment `// texelFetch(...)`: stripped, not matched
- GLSL block comment `/* dFdx(...) */`: stripped, not matched
- `#define texelFetch myFunc`: accepted as known false positive, documented
- Shader resolved from helper function parameter: source traced back to call site

### test_lint.py

- `gl[methodName]()`: flagged as computed property
- `const { TRIANGLES } = gl`: flagged as destructuring
- `gl.shaderSource(s, part1 + part2)`: flagged as concatenated shader
- Normal code: no flags
- Flagged file still produces analysis results, marked as partial coverage

### test_cache.py

- Same file content: Layer 1 cache hit, no re-parse
- Modified file content: Layer 1 cache miss, re-parse triggered
- Same surface JSON + same aggregated data: Layer 2 hit
- Changed surface JSON: Layer 2 miss, Layer 1 still valid
- Cache directory missing: created automatically, no crash

### test_report.py

- Tier 1 gap: method with 0 seeds appears in "Missing Methods"
- Tier 2 gap: constant never used in expected role appears in "Missing Constants"
- Delta mode: new seed covering a Tier 1 gap reported as "adds coverage for"
- Delta mode with no prior cache: falls back gracefully with warning

## Integration tests

`test_integration.py` runs the complete pipeline (extract, parse, analyze, report) against each pinned seed. Asserts:

- Expected method set
- Expected constant set
- Expected extensions detected

Each pinned seed has a companion `expected_output.json` in `tests/fixtures/seeds/` containing the manually verified expected call data. The integration test compares actual output against this file.

Selection criteria for pinned seeds (3-5 total):

- One minimal seed (few methods, no extensions) — baseline
- One seed using both extension patterns in the same file — tests pattern overlap
- One seed with helper functions and template literal shaders — tests const propagation + GLSL extraction
- One seed with overload-ambiguous bufferData calls — tests disambiguation
- One complex seed combining most features — integration stress test

## Test patterns

**Parametrized tests** keep test files compact:

```python
@pytest.mark.parametrize("fixture,expected_extensions", [
    ("ext_array_pattern.html", ["EXT_color_buffer_float"]),
    ("ext_direct_assign.html", ["OES_vertex_array_object"]),
    ("ext_both_patterns.html", ["EXT_color_buffer_float", "OES_vertex_array_object"]),
    ("ext_bare_enable.html", ["OES_standard_derivatives"]),
])
def test_extension_detection(parse_html, fixture, expected_extensions):
    ast = parse_html(fixture)
    result = detect_extensions(ast)
    assert sorted(result.names) == sorted(expected_extensions)
```

Adding new edge cases is trivial: add a fixture HTML file and a new tuple to the parametrize list.

## What not to test

- **tree-sitter itself.** Tests assume tree-sitter parses correctly. Test the auditor's interpretation of AST nodes.
- **The real surface JSON.** The extractor has its own canary checks. Auditor tests use the frozen test surface.
- **Report formatting aesthetics.** Assert content (right method names in right tiers), not whitespace or markdown formatting.
- **Full corpus snapshots.** A golden file against 367 seeds breaks on any corpus change. Pinned seeds serve this purpose in a controlled way.
- **Mocked tree-sitter ASTs.** Parsing a 15-line synthetic fixture is faster than hand-crafting fake AST nodes and more trustworthy.

## Performance target

- Full synthetic suite (no real seeds): < 3 seconds
- Integration tests (3-5 pinned seeds): < 5 seconds additional
- Total: < 10 seconds — fast enough to run on every save during development

## Milestone alignment

Tests are added alongside each auditor milestone:

| Milestone | Tests added |
|-----------|------------|
| M2 (basic auditor) | `test_html_extract`, `test_call_analysis` (basic cases), first pinned seed |
| M3 (const propagation + extensions) | `test_const_propagation`, `test_context`, add 2 more pinned seeds |
| M4 (overloads + GLSL) | `test_glsl`, overload cases in `test_call_analysis`, add final pinned seeds |
| M5 (caching + delta) | `test_cache`, `test_report`, `test_lint`, full integration suite |

## Dependencies

Added to `requirements.txt`:

```
pytest>=7.0.0
```
