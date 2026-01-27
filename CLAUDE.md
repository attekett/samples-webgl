# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **WebGL/WebGL2 fuzzing corpus project** designed to create mutation-based fuzzing test cases. The primary goal is to generate self-contained HTML test files that exercise complex WebGL state machines and API interactions to uncover bugs in WebGL implementations.

**Critical distinction**: This is NOT a conformance test suite. Test cases are designed as "high-biomass" seeds for mutation-based fuzzing, featuring "spaghetti-like" valid resource usage patterns that mutators can corrupt into security vulnerabilities.

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
- No console logging or code comments
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

## Architecture Overview

### Test File Structure

All test files follow this boilerplate pattern (see mutation-fuzzing-seed-structure-design.md for complete template):

```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgl-canvas" width="256" height="256"></canvas>
<script>
const REQUIRED_EXTENSIONS = [
    // List required extensions here
];

// ============ DECLARATION ZONE ============
// Tier 1: Amplification Variables
const texSize = 256;
const bufSize = texSize * texSize * 4;
// Tier 3: Enum Constants
const bufferTarget = gl.ARRAY_BUFFER;

async function main() {
    const canvas = document.getElementById('webgl-canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) throw new Error("WebGL2 not supported");

    // Extension gating (no try-catch here)
    const missingExtensions = REQUIRED_EXTENSIONS.filter(ext => !gl.getExtension(ext));
    if (missingExtensions.length > 0) {
        throw new Error(`UNSUPPORTED_EXTENSIONS: ${missingExtensions.join(', ')}`);
    }
    REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));

    // ============ SETUP ZONE ============
    // Block 1: Buffer operations
    try {
        const buffer = gl.createBuffer();
        gl.bindBuffer(bufferTarget, buffer);
        gl.bufferData(bufferTarget, bufSize, gl.STATIC_DRAW);
    } catch(e) { console.log(e); } // Remove console.log for production

    // ============ EXECUTION ZONE ============
    // Block N: Draw calls
    try {
        gl.drawArrays(gl.TRIANGLES, 0, 6);
    } catch(e) { console.log(e); } // Remove console.log for production
}

main().catch(err => { throw err; });
</script>
</body>
</html>
```

### Test Design Philosophy

Tests should maximize "fuzzing biomass" for mutation-based fuzzing (radamsa). See **docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md** for complete design:

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

Tests are organized by feature complexity:

- **Integrated Pipelines**: "Kitchen sink" seeds combining multiple features (MRT + Float Textures + Instancing + UBOs)
- **Extensions**: Tests targeting specific WebGL extensions
- **Compute-style**: Transform feedback and data processing patterns
- **Creative**: Complex visual demos demonstrating advanced features

### Error Handling Strategy

The test runner distinguishes between error types:

| Error Type | Example | Action |
|------------|---------|--------|
| Logic/Syntax | Variable not defined | Fix the code |
| API Misuse | Invalid enum value | Fix WebGL constants |
| Missing Extension | Extension not supported | Add to UNSUPPORTED.md, stop |
| Context Loss | WebGL context lost | Fix context handling |

**Try-Catch Block Strategy (for mutation-based fuzzing):**

Use try-catch blocks strategically to maximize driver error path exploitation:

- **Development Phase**: `catch(e) { console.log(e); }` - debug with run_tests.sh, check JSON console_logs
- **Production Phase**: `catch(e) {}` - silent for fuzzing, strip console.log before commit
- **Block Structure**: One try-catch per logical operation group (6-10 blocks per seed)
- **Purpose**: Allow driver state corruption in error paths to accumulate, triggering crashes in subsequent operations
- **Signal Preservation**: Driver crashes/segfaults are NOT masked - these are the target bugs

See **docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md** for complete rationale and implementation details.

### Test Runner (`webgl_test_runner.py`)

Python-based Playwright test runner that:

- Executes HTML test files in real browsers (Firefox, Chromium, Edge)
- Captures JavaScript errors, WebGL errors, and console output
- Generates detailed JSON reports per test file
- Takes screenshots of rendered output
- Supports parallel test execution

### Key Scripts

- **`run_tests.sh`**: Main test launcher with virtual environment auto-detection
- **`webgl_test_runner.py`**: Playwright-based test execution engine
- **`setup_venv.sh`**: Virtual environment initialization script

## Browser Compatibility

- **Primary**: Firefox (best extension support for fuzzing)
- **Secondary**: Chromium (avoid for extension-heavy tests)
- **Extension Detection**: Always check extension availability before use
- **Playwright Limitation**: Headless browsers have reduced extension support compared to native browsers

## Development Workflow

1. Check `UNSUPPORTED.md` for known limitations
2. Read `.cursorrules`, `CODING_RULES.md`, `AGENTS.md`, and **mutation-fuzzing-seed-structure-design.md**
3. Identify target feature from project documentation
4. Create test file in `agent_outputs/` following three-zone architecture with try-catch blocks
5. **Include `console.log(e)` in all catch blocks during development**
6. Run `./run_tests.sh --test-file <file> --browsers firefox`
7. Read generated `.json` file - check `console_logs` array for caught errors
8. Fix issues (syntax, undefined vars, wrong enums) and re-verify (never assume fixes work)
9. **Strip all `console.log(e)` statements** - replace with `catch(e) {}`
10. Final validation run - verify `passed: true` and `console_logs: []`
11. Commit clean seed file (no console.log statements)
12. Update coverage documentation after successful validation

## File Organization

- **`agent_outputs/`**: Output directory for newly created test files
- **`samples-webgl/`**: Main test corpus directory with existing test cases
- **`screenshots/`**: Visual output from test execution
- **`docs/`**: Additional documentation
- **`venv/`**: Python virtual environment (auto-created)

## Dependencies

- Python 3.x
- Playwright (`playwright>=1.40.0`)
- BeautifulSoup4 (`beautifulsoup4>=4.12.0`)

## Code Style

- Minimalist, machine-parseable code
- No comments in test files
- No console.log() statements
- Simple control flow (avoid complex abstractions)
- Inline some values, parameterize others for fuzzing
- Self-documenting variable names
