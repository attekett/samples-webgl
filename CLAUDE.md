# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **WebGL/WebGL2 fuzzing corpus project** containing **405 validated test files** designed for mutation-based fuzzing with Radamsa. The corpus is split between `agent_outputs/` (38 mutation seeds, batches b55–b66) and `samples-webgl/` (367 files across themed subdirectories — `mutations/`, `seeds/`, `creative/`, `webgl2/`, `extensions/`, etc.).

**Critical distinction**: This is NOT a conformance test suite. Test cases are "high-biomass" seeds for mutation-based fuzzing, featuring "spaghetti-like" valid resource usage patterns that mutators can corrupt into security vulnerabilities.

**Corpus status**: Production-ready. All critical, high, and medium 3-way feature combination gaps are closed. WebGL 2.0 reference card is 100% covered across methods, constants, GLSL functions, and GLSL built-in variables. See `docs/plans/2026-01-28-round8-completion-summary.md` for the round-8 milestone and recent commits (b62–b66) for follow-up coverage work.

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

# Run all tests with batch processing
python run_all_tests.py
```

**Important**: Always test with **Firefox** for extension-heavy tests, as it has superior WebGL extension support compared to Chromium in Playwright.

### Test Validation

After running tests, check the generated `.json` file for success criteria:

```json
{
  "passed": true,
  "console_logs": [],
  "javascript_errors": [],
  "webgl_errors": [],
  "errors": []
}
```

**Never assume fixes work - always re-run validation after changes.**

### Coverage Analysis

```bash
# Feature combination matrix analysis (legacy shell wrapper)
bash scripts/feature_matrix.sh

# Corpus statistics (file count, lines, try-catch density, gl.* call density)
bash scripts/analyze_corpus.sh

# Primary coverage tool (AST-based, replaces grep-based feature_matrix.sh)
python3 scripts/feature_coverage.py                       # Feature matrix with depth (P/M/D)
python3 scripts/feature_coverage.py --combinations 3      # 3-way feature combination gaps
python3 scripts/feature_coverage.py --api-surface-coverage # Per-method WebGL2 API coverage
python3 scripts/feature_coverage.py --glsl-detail          # Per-GLSL-builtin seed counts
python3 scripts/feature_coverage.py --glsl-vars-detail     # Per-GLSL-built-in-variable seed counts
python3 scripts/feature_coverage.py --passed-only          # Filter to seeds that pass at runtime
python3 scripts/feature_coverage.py --snapshot FILE        # Save coverage to JSON for diffing
python3 scripts/feature_coverage.py --diff PREV_SNAPSHOT   # Compare against an earlier snapshot
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

**`agent_outputs/` (38 files):** Recent agent-generated mutation seeds, batches b55–b66, targeting specific feature-combination and reference-card coverage gaps. New seeds typically land here.

**`samples-webgl/` (367 files):** Bulk corpus, organized into themed subdirectories.

| Subdirectory | Files | Purpose |
|---|---|---|
| `mutations/` | 259 | Mutation seeds, batches b1–b54 (the corpus core) |
| `seeds/` | 21 | Hypercomplex / high-biomass seeds combining many features |
| `creative/` | 18 | Visual effect demos |
| `webgl2/` | 16 | WebGL2 core feature tests |
| `extensions/` | 14 | Extension-specific seeds |
| `integrated/` | 7 | Multi-feature integration tests |
| `multipass/` | 6 | Rendering pipeline tests |
| `errors/` | 5 | Error path and boundary tests |
| `rendering/` | 4 | Rendering pipeline tests |
| `limits/` | 4 | WebGL limit tests |
| `edge_cases/` | 4 | Error path and boundary tests |
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

Python-based Playwright test runner (~960 lines) that:

- Executes HTML test files in real browsers (Firefox, Chromium, Edge)
- Captures JavaScript errors, WebGL errors, and console output
- Generates detailed JSON reports per test file
- Takes screenshots of rendered output
- Supports parallel test execution
- Configures Firefox with optimized WebGL preferences (fingerprinting disabled, EGL backend, draft extensions enabled)

### Key Scripts

| Script | Purpose |
|--------|---------|
| `run_tests.sh` | Main test launcher with venv auto-detection |
| `webgl_test_runner.py` | Playwright-based test execution engine (~960 lines) |
| `run_all_tests.py` | Batch test execution across the corpus |
| `run_tests.py` | Python wrapper for venv management |
| `setup_venv.sh` | Virtual environment initialization |
| `cleanup_js_comments.py` | Strip comments from HTML test files |
| `check_gl.py` | WebGL capability detection via Playwright |
| `verify_firefox.py` | Firefox WebGL validation with ASAN logging |
| `scripts/feature_coverage.py` | Primary AST-based coverage tool (matrix, combinations, API surface, GLSL functions/variables, snapshots) |
| `scripts/feature_matrix.sh` | Legacy shell wrapper around feature_coverage.py |
| `scripts/analyze_corpus.sh` | Corpus statistics (file count, line count, try-catch/gl.* call density) |
| `scripts/api_audit/` | Python package: tree-sitter-based JS parsing, GLSL extraction, feature detection, combination matrix |

## Corpus Statistics

| Metric | Value |
|--------|-------|
| Total HTML test files | 405 (38 in `agent_outputs/`, 367 in `samples-webgl/`) |
| Mutation seed batches | 66 (b1–b66; b1–b54 in `samples-webgl/mutations/`, b55–b66 in `agent_outputs/`) |
| Mutation seeds | 297 |
| Iterative rounds completed | 8 (round 8 complete; ongoing follow-up batches b62–b66 closing PDF reference gaps) |
| Feature categories tracked | 23 (matrix) + 6 ubiquitous |
| Average seed complexity | ~250 lines |
| Total `gl.*` API calls | ~40,700 (avg 100/seed) |
| Try-catch blocks | ~3,700 (avg 7.3/seed) |

Run `bash scripts/analyze_corpus.sh` for live numbers.

### Coverage Milestones

- All critical 2-way feature gaps closed
- All critical/high/medium 3-way feature gaps closed (83% reduction)
- WebGL 2.0 reference card: **100% coverage** across methods (178/178), constants (235/235), GLSL builtin functions (44/44), GLSL builtin variables (22/22)
- API surface: **225/225 methods exercised (100%)** across the corpus
- GLSL builtins: **54/54** (function union of surface + categories)
- 3-way feature combinations: **467/467 covered (100%)** topology-connected combos
- Per-category coverage thresholds (Transform Feedback, Pixel Operations, Texture Arrays, etc.) all exceeded

## Browser Compatibility

- **Primary**: Firefox (best extension support for fuzzing, 24 extensions)
- **Secondary**: Chromium (core WebGL2 only, ANGLE limits extension exposure)
- **Extension Detection**: Always check extension availability before use
- **Playwright Firefox**: Configured with optimized prefs for WebGL2 + extensions (see `UNSUPPORTED.md` for details)
- **Known unsupported**: `EXT_disjoint_timer_query_webgl2` in Firefox, various WebGL1 extensions in Chromium

## Development Workflow

1. Check `UNSUPPORTED.md` for known limitations
2. Read `.cursorrules`, `CODING_RULES.md`, `AGENTS.md`, and **mutation-fuzzing-seed-structure-design.md**
3. Identify target feature from project documentation or coverage gaps
4. Create test file in `agent_outputs/` following three-zone architecture with try-catch blocks
5. **Include `console.log(e)` in all catch blocks during development**
6. Run `./run_tests.sh --test-file <file> --browsers firefox`
7. Read generated `.json` file - check `console_logs` array for caught errors
8. Fix issues (syntax, undefined vars, wrong enums) and re-verify (never assume fixes work)
9. **Strip all `console.log(e)` statements** - replace with `catch(e) {}`
10. Final validation run - verify `passed: true` and `console_logs: []`
11. Commit clean seed file (no console.log statements)
12. Run `python3 scripts/feature_coverage.py` to verify category coverage; add `--combinations 3` to check that the new seed closes its target gap

## File Organization

```
samples-webgl/
├── agent_outputs/           # Recent agent-generated seeds (38 HTML, batches b55–b66)
├── samples-webgl/           # Bulk corpus (367 HTML across themed subdirs)
│   ├── mutations/           # 259 mutation seeds, batches b1–b54
│   ├── seeds/               # 21 hypercomplex / high-biomass seeds
│   ├── creative/            # 18 visual effect demos
│   ├── webgl2/              # 16 WebGL2 core feature tests
│   ├── extensions/          # 14 extension-specific seeds
│   ├── integrated/          # 7 multi-feature integration tests
│   ├── multipass/           # 6 rendering pipeline tests
│   ├── errors/              # 5 error path tests
│   ├── rendering/           # 4 rendering pipeline tests
│   ├── limits/              # 4 WebGL limit tests
│   ├── edge_cases/          # 4 boundary tests
│   ├── texture_tech/        # 3 texture technique tests
│   ├── compute/             # 3 compute-style pattern tests
│   ├── shaders/             # 2 shader-focused tests
│   └── resource/            # 1 resource lifecycle test
├── screenshots/             # Visual output from test execution
├── docs/
│   ├── plans/               # Design docs and round completion summaries
│   ├── snapshots/           # Coverage snapshots (JSON, used by --snapshot/--diff)
│   ├── feature_categories.json    # AST-based feature category definitions
│   ├── webgl_api_surface.json     # WebGL2 API surface (methods, constants, GLSL builtins/variables)
│   ├── interaction_topology.json  # Connected-combo topology for n-way matrix
│   └── *.md                 # Reference docs (Radamsa guide, spec docs, etc.)
├── scripts/
│   ├── feature_coverage.py  # Primary coverage tool
│   ├── feature_matrix.sh    # Legacy shell wrapper
│   ├── analyze_corpus.sh    # Corpus statistics
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
