# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **WebGL/WebGL2 fuzzing corpus project** containing **572 test files** designed for mutation-based fuzzing with Radamsa. The corpus is split between `agent_outputs/` (207 HTML files at the top level, including mutation seed batches b55–b99, plus the `mutator_baseline/` symlink set) and `samples-webgl/` (365 files across themed subdirectories — `mutations/`, `seeds/`, `creative/`, `webgl2/`, `extensions/`, etc.).

**Critical distinction**: This is NOT a conformance test suite. Test cases are "high-biomass" seeds for mutation-based fuzzing, featuring "spaghetti-like" valid resource usage patterns that mutators can corrupt into security vulnerabilities.

**Corpus status**: The coverage model was widened on 2026-10-18 (54 categories, 252 topology edges), which reopened gaps: 3-way 1719/2440 and 4-way 11792/24178 connected combos are covered (see Coverage Milestones). 225/226 API surface methods are exercised; only `makeXRCompatible` is missing (see Coverage Milestones). Every seed runs strictly clean in at least one browser lane (see Browser Compatibility). See `docs/plans/2026-01-28-round8-completion-summary.md` for the round-8 milestone and recent commits (b71–b99) for newer coverage work.

## Project-Specific Rules

**ALWAYS read these files before making any changes:**

1. **`.cursorrules`** - Core mission, test case requirements, and development workflow
2. **`docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md`** - Comprehensive design for mutation-optimized seeds (CRITICAL for seed creation)
3. **`CODING_RULES.md`** - Step-by-step test case creation and verification procedures
4. **`AGENTS.md`** - Detailed agent instructions for fuzzing-first approach
5. **`UNSUPPORTED.md`** - Known browser/extension limitations to avoid

**Key constraints for test cases:**

- Self-contained single HTML files (no external dependencies)
- 256x256 canvas resolution
- No console logging or code comments in production seeds
- No user interaction required
- Extension checking required before advanced features
- WebGL2 context required for all tests
- Output files go to `agent_outputs/` directory
- Seeds must not call `loseContext`: the runner always fails on context loss

## Build & Test Commands

### Virtual Environment Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Deactivate when done
deactivate
```

### Running Tests

```bash
# Test a single file (automatically uses venv if available)
./run_tests.sh --test-file agent_outputs/your_test.html --browsers firefox

# Test with specific browser
./run_tests.sh --test-file samples-webgl/some_test.html --browsers chromium

# Test multiple files
./run_tests.sh --test-dir samples-webgl --browsers firefox

# Chrome lanes (ANGLE-Vulkan, ANGLE-GL)
./run_tests.sh --test-file <f> --browsers chromium --browser-config config/angle_vulkan.json
./run_tests.sh --test-file <f> --browsers chromium --browser-config config/angle_gl.json

# Unit tests (581 passed after the 2026-10-18 model change)
python -m pytest -q scripts/tests scripts/api_audit/tests
```

**Important**: Test with **Firefox** first, then with the Chrome lane the seed targets (see Browser Compatibility).

### Test Validation

After running tests, check the generated `.json` file for success criteria:

```json
{
  "passed": true,
  "console_logs": [],
  "warnings": [],
  "javascript_errors": [],
  "webgl_errors": [],
  "errors": []
}
```

`webgl_test_runner.py` sets `passed` only when there are no errors, JS errors, WebGL errors or warnings. Console `warn` counts as a warning and console `error`/`assert` counts as an error. Context loss, an unfinished test or a missing canvas also fails. A clean seed additionally needs empty `console_logs`. Known perf-warning traps: every `PIXEL_UNPACK_BUFFER` texture upload warns in Firefox (target those seeds at Chrome), and Chrome warns on synchronous `readPixels` stalls (read through a `PIXEL_PACK_BUFFER`).

**Never assume fixes work - always re-run validation after changes.**

### Coverage Analysis

```bash
# Feature combination matrix analysis (legacy shell wrapper)
bash scripts/feature_matrix.sh

# Corpus statistics (file count, lines, try-catch density, gl.* call density)
bash scripts/analyze_corpus.sh

# Screenshot analysis: blank frames, visual duplicates, determinism
./venv/bin/python scripts/analyze_screenshots.py --json /tmp/shots.json

# Generate recipes for closing 3-way gaps (--availability ranks gaps by extensions testable here)
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --availability docs/browser_webgl_info.txt \
  --combination-matrix /tmp/matrix.json \
  --gap-recipes /tmp/recipes.json \
  --n-way 3

# Primary coverage tool (AST-based, replaces grep-based feature_matrix.sh)
python3 scripts/feature_coverage.py                       # Feature matrix with depth (P/M/D)
python3 scripts/feature_coverage.py --combinations 3      # 3-way feature combination gaps
python3 scripts/feature_coverage.py --combinations 4      # 4-way feature combination gaps
python3 scripts/feature_coverage.py --api-surface-coverage # Per-method WebGL2 API coverage
python3 scripts/feature_coverage.py --glsl-detail          # Per-GLSL-builtin seed counts
python3 scripts/feature_coverage.py --glsl-vars-detail     # Per-GLSL-built-in-variable seed counts
python3 scripts/feature_coverage.py --passed-only          # Filter to seeds that pass at runtime
python3 scripts/feature_coverage.py --snapshot FILE        # Save coverage to JSON for diffing
python3 scripts/feature_coverage.py --diff PREV_SNAPSHOT   # Compare against an earlier snapshot

# Inventory, per-lane mutation profile, coverage report (usage: docs/webgl_corpus_metrics.md)
python scripts/corpus_metrics.py inventory|profile|report ...
```

## Architecture Overview

### Test File Structure

All test files follow the three-zone boilerplate (see `docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md` for complete template):

```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgl-canvas" width="256" height="256"></canvas>
<script>
const REQUIRED_EXTENSIONS = [];

// ============ DECLARATION ZONE ============
// Tier 1: Amplification Variables (5-8 per seed)
const texSize = 256;
const bufSize = texSize * texSize * 4;
// Tier 3: Enum Constants (4-6 per seed)
const bufferTarget = gl.ARRAY_BUFFER;

async function main() {
    const canvas = document.getElementById('webgl-canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) throw new Error("WebGL2 not supported");

    const missingExtensions = REQUIRED_EXTENSIONS.filter(ext => !gl.getExtension(ext));
    if (missingExtensions.length > 0) {
        throw new Error(`UNSUPPORTED_EXTENSIONS: ${missingExtensions.join(', ')}`);
    }
    REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));

    // ============ SETUP ZONE (4-8 try-catch blocks) ============
    try {
        const buffer = gl.createBuffer();
        gl.bindBuffer(bufferTarget, buffer);
        gl.bufferData(bufferTarget, bufSize, gl.STATIC_DRAW);
    } catch(e) {}

    // ============ EXECUTION ZONE (2-4 try-catch blocks) ============
    try {
        gl.drawArrays(gl.TRIANGLES, 0, 6);
    } catch(e) {}
}

main().catch(err => { throw err; });
</script>
</body>
</html>
```

### Test Design Philosophy

Tests maximize "fuzzing biomass" for Radamsa mutation. See **docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md** for complete design:

**Three-Zone Architecture:**
- **Declaration Zone**: Amplification variables + enum constants (strategic coupling)
- **Setup Zone**: Resource creation with line repetition patterns (4-8 try-catch blocks)
- **Execution Zone**: State configuration + draw calls + cleanup (2-4 try-catch blocks)

**Line Repetition Patterns:**
- **Bind Ping-Pong**: Redundant bind operations (2-4 per resource)
- **Enable/Disable Thrashing**: State toggles (3-5 per state group)
- **FBO Attachment Swapping**: Complex FBO operations (4-6 switches)
- **Resource Creation Redundancy**: Multiple creates without cleanup
- **Deletion and Reuse**: Use-after-delete patterns for UAF potential

**Variable Tier System:**
- **Tier 1**: Amplification variables where mutations cascade (5-8 per seed)
- **Tier 2**: Hot spot inline literals for localized corruption (20-40 per seed)
- **Tier 3**: Enum constants for line-repetition based corruption (4-6 per seed)

**Try-Catch Strategy:**
- Development: `catch(e) { console.log(e); }` for debugging
- Production: `catch(e) {}` (silent) for fuzzing
- Purpose: Exploit driver error path bugs where corrupted state accumulates

### Test Categories

**`agent_outputs/` (207 HTML files):** Agent-generated mutation seeds, batches b55–b99 (the local b66–b70 line was renumbered b94–b98), plus targeted WebGL2 seeds. New seeds typically land here. `agent_outputs/mutator_baseline/` holds symlinks to the deployable mutator input: `core/` (12 seeds, Firefox or Chrome) and `chrome_extensions/` (2 seeds, Chrome ANGLE-Vulkan only).

**`samples-webgl/` (365 files):** Bulk corpus, organized into themed subdirectories.

| Subdirectory | Files | Purpose |
|---|---|---|
| `mutations/` | 259 | Mutation seeds, batches b1–b54 (the corpus core) |
| `seeds/` | 20 | Hypercomplex / high-biomass seeds combining many features |
| `creative/` | 18 | Visual effect demos |
| `webgl2/` | 16 | WebGL2 core feature tests |
| `extensions/` | 14 | Extension-specific seeds |
| `integrated/` | 7 | Multi-feature integration tests |
| `multipass/` | 6 | Rendering pipeline tests |
| `errors/` | 5 | Error path and boundary tests |
| `rendering/` | 4 | Rendering pipeline tests |
| `limits/` | 4 | WebGL limit tests |
| `edge_cases/` | 3 | Error path and boundary tests |
| `texture_tech/` | 3 | Texture technique tests |
| `compute/` | 3 | Compute-style patterns |
| `shaders/` | 2 | Shader-focused tests |
| `resource/` | 1 | Resource lifecycle test |

### Error Handling Strategy

| Error Type | Example | Action |
|------------|---------|--------|
| Logic/Syntax | Variable not defined | Fix the code |
| API Misuse | Invalid enum value | Fix WebGL constants |
| Missing Extension | Extension not supported | Add to UNSUPPORTED.md, stop |
| Context Loss | WebGL context lost | Fix context handling |

**Try-Catch Block Strategy (for mutation-based fuzzing):**

- **Development Phase**: `catch(e) { console.log(e); }` - debug with run_tests.sh, check JSON console_logs
- **Production Phase**: `catch(e) {}` - silent for fuzzing, strip console.log before commit
- **Block Structure**: One try-catch per logical operation group (6-10 blocks per seed)
- **Purpose**: Allow driver state corruption in error paths to accumulate, triggering crashes in subsequent operations
- **Signal Preservation**: Driver crashes/segfaults are NOT masked - these are the target bugs

See **docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md** for complete rationale.

### Test Runner (`webgl_test_runner.py`)

Python-based Playwright test runner that:

- Executes HTML test files in real browsers (Firefox, Chromium with `--browser-config` lane files, WebKit)
- Captures JavaScript errors, WebGL errors, and console output
- Generates detailed JSON reports per test file
- Takes screenshots of rendered output
- Supports parallel test execution
- Configures Firefox with optimized WebGL preferences (fingerprinting disabled, EGL backend, draft extensions enabled)

### Key Scripts

| Script | Purpose |
|--------|---------|
| `run_tests.sh` | Main test launcher with venv auto-detection |
| `webgl_test_runner.py` | Playwright-based test execution engine; strict pass/fail; `--browser-config` selects the Chrome ANGLE lane |
| `run_all_tests.py` | Stale: scans the missing `testcases/`; use `run_tests.sh --test-dir` |
| `config/angle_vulkan.json`, `config/angle_gl.json` | Chrome lane flags |
| `run_tests.py` | Python wrapper for venv management |
| `setup_venv.sh` | Virtual environment initialization |
| `cleanup_js_comments.py` | Strip comments from HTML test files |
| `check_gl.py` | WebGL capability detection via Playwright |
| `verify_firefox.py` | Firefox WebGL validation with ASAN logging |
| `scripts/feature_coverage.py` | Primary AST-based coverage tool (matrix, combinations, API surface, GLSL functions/variables, snapshots) |
| `scripts/feature_matrix.sh` | Legacy shell wrapper around feature_coverage.py |
| `scripts/analyze_corpus.sh` | Corpus statistics (file count, line count, try-catch/gl.* call density) |
| `scripts/api_audit/` | Python package: tree-sitter-based JS parsing, GLSL extraction, feature detection, combination matrix |
| `scripts/analyze_screenshots.py` | Blank-frame detection, perceptual-hash dedupe, determinism diffing |
| `scripts/corpus_metrics.py` | Inventory, per-lane mutation profile, coverage report and seed manifest; see `docs/webgl_corpus_metrics.md` |
| `scripts/webgl_mutator.py` | Valid-flow WebGL mutator |
| `scripts/calibrate_webgl_lifecycle.py` | Grizzly lifecycle calibration for `corpus_metrics` |
| `scripts/api_audit/availability.py` | Availability-aware gap ranking (joins the surface with `check_gl.py` output) |

## Corpus Statistics

| Metric | Value |
|--------|-------|
| Total HTML test files | 572 (207 in `agent_outputs/`, 365 in `samples-webgl/`) |
| Mutation seed batches | b1–b99 (b1–b54 in `samples-webgl/mutations/`, b55–b99 in `agent_outputs/`) |
| Mutation seeds | 455 |
| Feature categories tracked | 54 (`docs/feature_categories.json`), 7 of them ubiquitous and left out of the matrix (Uniforms, Viewport/Scissor, Vertex Attributes, Buffer Operations, Shader Pipeline, Draw Calls, Pipeline State) |
| Average seed complexity | ~235 lines |
| Total lines | 134,827 |
| Total `gl.*` API calls | 57,045 (avg 99/seed) |
| Try-catch blocks | 4,842 (avg 7.1/seed) |

Run `bash scripts/analyze_corpus.sh` for live numbers.

### Coverage Milestones

- 2-way feature combinations: **231/252** topology-connected combos covered; 21 gaps
- 3-way feature combinations: **1719/2440** covered (70%); 721 gaps, 280 of them involving a category no seed matches yet
- 4-way feature combinations: **11792/24178** covered (49%); 12386 gaps, 4047 of them involving a zero-seed category
- Low-diversity (monoculture) flags: 64 at 3-way, 318 at 4-way (api_audit combination matrix)
- Zero-seed categories: `ext_multiview`, `ext_blend_func_extended`, `ext_renderable_formats`, `ext_debug_info` (all exposed on Chrome ANGLE-Vulkan; norm16 and the debug extensions also on Firefox)
- Before the 2026-10-18 model change the same corpus scored 526/526 at 3-way and 2947/2947 at 4-way
- API surface (226 methods, 559 constants, 56 extensions): **225/226 methods exercised (99.6%)**. The only gap, `makeXRCompatible`, stays in the surface by decision because it needs a WebXR device.
- GLSL builtin functions: **54/54**. GLSL built-in variables: **22/22**.
- These figures are relative to the current coverage model. `docs/coverage-mapping-gaps-2026-10-17.md` lists what the model could not see; its "Applied 2026-10-18" section says which proposals are now in the model and which still need detector work.

## Browser Compatibility

- **Lanes**: Firefox (Playwright build); Chrome ANGLE-Vulkan (`--browser-config config/angle_vulkan.json`); Chrome ANGLE-GL (`--browser-config config/angle_gl.json`), the only lane that exposes `WEBGL_clip_cull_distance`
- Every corpus seed runs strictly clean (no console output, warning, WebGL error or JS error) in at least one lane. The per-seed lane from before the fix round is in `docs/snapshots/webgl-corpus-runtime-sweep-2026-10-17.tsv`.
- Per-lane extension availability: see `UNSUPPORTED.md`
- **Extension Detection**: Always check extension availability before use
- **Playwright Firefox**: Configured with optimized prefs for WebGL2 + extensions (see `UNSUPPORTED.md` for details)
- **Known unsupported**: `EXT_disjoint_timer_query_webgl2` in Firefox, various WebGL1 extensions in Chromium

## Development Workflow

1. Check `UNSUPPORTED.md` for known limitations
2. Read `.cursorrules`, `CODING_RULES.md`, `AGENTS.md`, and **mutation-fuzzing-seed-structure-design.md**
3. Identify target feature from project documentation or coverage gaps
4. Create test file in `agent_outputs/` following three-zone architecture with try-catch blocks
5. **Include `console.log(e)` in all catch blocks during development**
6. Run `./run_tests.sh --test-file <file> --browsers firefox`, or the Chrome lane the seed targets (`--browsers chromium --browser-config config/angle_vulkan.json` or `angle_gl.json`)
7. Read generated `.json` file - check `console_logs` array for caught errors
8. Fix issues (syntax, undefined vars, wrong enums) and re-verify (never assume fixes work)
9. **Strip all `console.log(e)` statements** - replace with `catch(e) {}`
10. Final validation run - verify `passed: true` with empty `console_logs`, `warnings`, `errors`, `javascript_errors` and `webgl_errors`
11. Commit clean seed file (no console.log statements)
12. Run `python3 scripts/feature_coverage.py` to verify category coverage; add `--combinations 3` and `--combinations 4` to check that the new seed closes its target gap

## File Organization

```
samples-webgl/
├── agent_outputs/           # Agent-generated seeds (207 HTML, batches b55–b99)
│   └── mutator_baseline/    # core/ (12) + chrome_extensions/ (2) symlinks: deployable mutator input
├── samples-webgl/           # Bulk corpus (365 HTML across themed subdirs)
│   ├── mutations/           # 259 mutation seeds, batches b1–b54
│   ├── seeds/               # 20 hypercomplex / high-biomass seeds
│   ├── creative/            # 18 visual effect demos
│   ├── webgl2/              # 16 WebGL2 core feature tests
│   ├── extensions/          # 14 extension-specific seeds
│   ├── integrated/          # 7 multi-feature integration tests
│   ├── multipass/           # 6 rendering pipeline tests
│   ├── errors/              # 5 error path tests
│   ├── rendering/           # 4 rendering pipeline tests
│   ├── limits/              # 4 WebGL limit tests
│   ├── edge_cases/          # 3 boundary tests
│   ├── texture_tech/        # 3 texture technique tests
│   ├── compute/             # 3 compute-style pattern tests
│   ├── shaders/             # 2 shader-focused tests
│   └── resource/            # 1 resource lifecycle test
├── screenshots/             # Visual output from test execution
├── config/                  # Chrome lane browser configs (angle_vulkan.json, angle_gl.json)
├── docs/
│   ├── plans/               # Design docs and round completion summaries
│   ├── snapshots/           # Coverage snapshots (JSON), corpus_metrics reports, runtime sweep TSV
│   ├── webgl_corpus_metrics.md    # corpus_metrics.py usage
│   ├── 2026-10-17-webgl-corpus-tooling-handoff.md  # Corpus tooling handoff
│   ├── feature_categories.json    # AST-based feature category definitions
│   ├── webgl_api_surface.json     # WebGL2 API surface (methods, constants, GLSL builtins/variables)
│   ├── interaction_topology.json  # Connected-combo topology for n-way matrix
│   └── *.md                 # Reference docs (Radamsa guide, spec docs, etc.)
├── scripts/
│   ├── feature_coverage.py  # Primary coverage tool
│   ├── feature_matrix.sh    # Legacy shell wrapper
│   ├── analyze_corpus.sh    # Corpus statistics
│   ├── corpus_metrics.py    # Inventory, mutation profile, coverage report
│   ├── webgl_mutator.py     # Valid-flow WebGL mutator
│   ├── calibrate_webgl_lifecycle.py  # Grizzly lifecycle calibration
│   ├── analyze_screenshots.py  # Screenshot checks
│   ├── tests/               # Unit tests
│   └── api_audit/           # Python package: parsing, GLSL, feature detection, combination matrix
├── tests/fixtures/          # Synthetic seeds used by api_audit unit tests
├── old_docs/                # Archived documentation
├── venv/                    # Python virtual environment (auto-created)
├── webgl_test_runner.py     # Main test runner
├── run_tests.sh             # Test launcher
├── .cursorrules             # Core mission
├── CODING_RULES.md          # Test creation procedures
├── AGENTS.md                # Agent instructions
├── UNSUPPORTED.md           # Browser/extension limitations
└── requirements.txt         # Python dependencies
```

## Dependencies

- Python 3.x
- Playwright (`playwright>=1.40.0`)
- BeautifulSoup4 (`beautifulsoup4>=4.12.0`)

## Code Style

- Minimalist, machine-parseable code
- No comments in production test files
- No console.log() statements in production seeds
- Simple control flow (avoid complex abstractions)
- Inline some values, parameterize others for fuzzing
- Self-documenting variable names
- 150-300 lines per seed (excluding shader source)
