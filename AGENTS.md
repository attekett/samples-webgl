# WebGL/WebGL2 Fuzzing Test Case Creation Instructions

## Core Mission
Create **fuzzable WebGL/WebGL2 test cases** that systematically increase coverage of the WebGL specifications while producing visually interesting outputs. Test cases must be **minimalist, self-contained, and machine-parseable** for mutation-based fuzzing, while demonstrating advanced WebGL features through complex visual demos.

## Prerequisites
- **Read CONTRIBUTING_LLM.md thoroughly** - understand the fuzzing-first mentality
- **Read docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md** - comprehensive guide for creating mutation-optimized seeds for radamsa (CRITICAL FOR SEED CREATION)
- **Review TODO.md** - identify under-tested features and edge cases
- **Examine existing test cases** in `examples/` and `testcases/` directories
- **Study WebGL/WebGL2 specifications** for accurate feature implementation
- **Check UNSUPPORTED.md** - avoid features known to be unsupported

## Test Case Requirements

### Technical Constraints
- **Self-contained HTML file** - no external dependencies, libraries, or resources
- **No user interaction** required - demos run automatically on page load
- **256x256 canvas** (standard test resolution)
- **No console logging** - test runner captures all necessary information
- **No code comments** - code must be self-documenting
- **Simple structures** - avoid complex classes, verbose patterns, or abstractions
- **Fuzzing-friendly** - inline some values, parameterize others for mutation testing
- **Extension-aware** - check for required WebGL extensions before use

### Visual Output
- **Complex visual demo** as primary validation method
- **Deterministic output** for reliable testing
- **Feature demonstration** through visual results (not just API calls)
- **Edge case coverage** that produces visible differences

## Development Workflow

### Step 1: Feature Selection
1. **Consult TODO.md** - identify under-covered features or edge cases
2. **Check existing coverage** in project documentation
3. **Select target feature** - focus on one specific WebGL/WebGL2 capability
4. **Plan visual demonstration** - how will the feature's behavior be made visible?
5. **Check UNSUPPORTED.md** - ensure feature isn't known to be unsupported

### Step 2: Directory and Naming
- **Output directory**: Output files to `agent_outputs/` and leave them there
- **Naming convention**: `category_feature_description.html` (snake_case, descriptive)

### Step 3: Implementation Guidelines

#### WebGL Setup (Required Boilerplate)
```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgl-canvas" width="256" height="256"></canvas>
<script>
// CONFIGURATION: Define required extensions here
const REQUIRED_EXTENSIONS = [
    // e.g., 'WEBGL_draw_buffers', 'OES_texture_float'
];

async function main() {
    const canvas = document.getElementById('webgl-canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) throw new Error("WebGL2 not supported - required for all tests");

    // EXTENSION GATING (no try-catch here - must fail fast if unsupported)
    const missingExtensions = REQUIRED_EXTENSIONS.filter(ext => !gl.getExtension(ext));
    if (missingExtensions.length > 0) {
        throw new Error(`UNSUPPORTED_EXTENSIONS: ${missingExtensions.join(', ')}`);
    }
    REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));

    // ============ DECLARATION ZONE ============
    // Tier 1: Amplification variables
    const texSize = 256;
    const bufSize = texSize * texSize * 4;
    // Tier 3: Enum constants
    const bufferTarget = gl.ARRAY_BUFFER;

    // ============ SETUP ZONE ============
    // Block 1: Buffer operations
    try {
        const buffer = gl.createBuffer();
        gl.bindBuffer(bufferTarget, buffer);
        gl.bufferData(bufferTarget, bufSize, gl.STATIC_DRAW);
    } catch(e) { console.log(e); }

    // Block 2: Texture operations
    try {
        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 512, 512, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    } catch(e) { console.log(e); }

    // ============ EXECUTION ZONE ============
    // Block N: Draw calls
    try {
        gl.drawArrays(gl.TRIANGLES, 0, 6);
    } catch(e) { console.log(e); }
}

main().catch(err => {
    // If the error string contains "UNSUPPORTED_EXTENSIONS", the Python runner
    // knows to log it to UNSUPPORTED.md and skip.
    // Otherwise, it counts as a test failure/crash.
    // Also handling Playwright Firefox limitations.
    throw err;
});
</script>
</body>
</html>
```

#### Feature Implementation
- **Direct WebGL API usage** - no helper libraries
- **GLSL shaders embedded as template literals** - no external shader files
- **Resource creation with explicit parameters** - mix inline values and variables for fuzzing
- **Extension checking** - validate extension availability before use
- **Error handling through exceptions** - let test runner capture validation errors

#### Fuzzing Optimization

Follow the **Three-Zone Architecture** and **Variable Tier System** from docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md:

**Zone 1 - Declaration Zone:**
- Tier 1: Amplification variables (5-8 per seed): `const texSize = 256; const bufSize = texSize * texSize * 4;`
- Tier 3: Enum constants (4-6 per seed): `const bufferTarget = gl.ARRAY_BUFFER;`

**Zone 2 - Setup Zone (4-8 try-catch blocks):**
- Resource creation with line repetition patterns (bind ping-pong, creation redundancy, FBO swapping)
- Mix Tier 2 hot spot inlines (20-40 literals) with variable references

**Zone 3 - Execution Zone (2-4 try-catch blocks):**
- State configuration with enable/disable thrashing
- Draw calls with FBO switching
- Resource cleanup with deletion patterns

**Key Patterns:**
- Bind ping-pong (2-4 redundant binds per resource)
- Enable/disable thrashing (3-5 toggles per state group)
- FBO attachment swapping (4-6 switches)
- Deletion and reuse patterns for UAF potential

See the design document for complete template and pattern catalog.

### Step 4: Validation Process

#### Automated Testing
```bash
# Test with Firefox (Required for extensions)
./run_tests.sh --test-file agent_outputs/your_test.html --browsers firefox
```

#### Result Validation
- **Check JSON output** for your test file (created automatically)
- **Required success criteria**:
  - `"passed": true`
  - `"console_logs": []` (no warnings/errors)
  - `"javascript_errors": []` (empty array)
  - `"webgl_errors": []` (empty array)
  - `"errors": []` (empty array)

#### Iterative Fixing
- **If warnings/errors exist**: Fix the code and re-run tests
- **No compromises**: Remove test case if it cannot pass cleanly
- **Verify fixes work**: Never assume - always re-run validation

### Step 5: Documentation Updates
After successful validation:
1. **Update coverage documentation** in project files
2. **Ensure feature coverage** is accurately reflected
3. **Verify no external files** were created or required

## Quality Standards

### Code Quality
- **Machine-readable**: Simple, consistent patterns for fuzzing tools
- **Self-documenting**: Clear variable names, obvious logic flow
- **Specification compliant**: Accurate WebGL/WebGL2 API usage
- **Cross-browser aware**: Handle extension availability appropriately
- **Extension-safe**: Proper extension checking and fallback

### Feature Coverage
- **Advanced extensions**: Use rarely-tested WebGL extensions (float textures, multiple render targets, etc.)
- **Edge cases**: Test boundary conditions and unusual combinations
- **Performance characteristics**: Demonstrate real-world usage patterns
- **Integration testing**: Combine multiple API components and extensions

### Visual Validation
- **Deterministic results**: Same output on repeated runs
- **Feature demonstration**: Visual output clearly shows the tested capability
- **Complexity appropriate**: Advanced enough to stress-test, simple enough to validate

## Browser Compatibility
## Browser Compatibility
- **Primary testing**: Firefox (Best extension support for fuzzer)
- **Chromium**: Do not use for extension-heavy tests
- **Extension detection**: Check for extension availability before using advanced features

## Common Pitfalls to Avoid
- **Overly complex logic** - breaks fuzzing capability
- **External dependencies** - violates self-containment requirement
- **Non-deterministic output** - makes validation unreliable
- **Console logging** - interferes with automated error detection
- **User interaction** - prevents automated testing
- **Comments in code** - reduces fuzzing effectiveness
- **Missing extension checks** - causes crashes on unsupported platforms

## Error Handling Strategy

You must distinguish between different types of errors:

| Error Type | Example | Action |
|------------|---------|--------|
| Logic/Syntax | Variable 'x' not defined | FIX IT. Rewrite code to work |
| API Misuse | Invalid enum value, wrong parameter | FIX IT. Use correct WebGL constants |
| Missing Extension | Extension not supported | STOP. Add to UNSUPPORTED.md |
| Context Loss | WebGL context lost | FIX IT. Add context loss handling |
| Shader Compilation | GLSL syntax error | FIX IT. Fix shader code |

**Try-Catch Block Strategy for Mutation-Based Fuzzing:**

For seeds optimized for radamsa, use try-catch blocks strategically to exploit driver error path bugs. See **docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md** for complete details:

- **Purpose**: Allow driver state corruption in error paths to accumulate, triggering crashes in subsequent operations
- **Development**: Use `catch(e) { console.log(e); }` for debugging with run_tests.sh
- **Production**: Strip console.log, use `catch(e) {}` (silent) for fuzzing
- **Block Structure**: One try-catch per logical operation group (6-10 blocks per seed)
- **Signal Preservation**: Driver crashes/segfaults are NOT masked by try-catch - these are the target bugs

This approach maximizes detection of driver memory corruption vulnerabilities (UAF, double-free, heap corruption) that manifest when error paths leave driver state corrupted.

## Verification Protocol

You must verify the generated test case using the automated test runner.

### 1. Run the Test

Execute the following command in the terminal:

```bash
./run_tests.sh --test-file agent_outputs/your_filename.html --browsers firefox
```

### 2. Analyze JSON Output

The command generates a JSON file with the same name as your test file, but with a .json extension (e.g., `agent_outputs/your_filename.json`). Read this file to check the results. Focus on the `results` array (specifically `results[0]`).

**Success Criteria (The test is GOOD):**
- `"passed": true`
- `"javascript_errors": []` (Empty array)
- `"webgl_errors": []` (Empty array)

**Failure Criteria (The test is BAD or UNSUPPORTED):**
- `"passed": false`
- `"javascript_errors"` contains entries.

### 3. Verification Decision Logic

If `passed` is `false`, examine the message inside `javascript_errors` or `webgl_errors`.

**Case A: Unsupported Extension**
- **Symptom:** Error message mentions extension not supported or matches your UNSUPPORTED_EXTENSIONS error.
- **Action:** DO NOT FIX. Log the extension to UNSUPPORTED.md and mark the test as valid but skipped. Move to `agent_outputs/unsupported`.

**Case B: Validation/Logic Error**
- **Symptom:** "Invalid enum", "Shader compilation failed", "Invalid operation".
- **Action:** FIX IT. The logic is flawed. You must rewrite the code to satisfy the spec. Retry the verification.

**Case C: Context Loss / Crash**
- **Symptom:** Test runner reports context lost or crashes.
- **Action:** FIX IT. The code is likely invalid or triggers a driver bug.

## Development Workflow

1. Check UNSUPPORTED.md: Ensure your target extensions aren't banned.
2. Plan the Complexity: Define at least 2 distinct passes (e.g., render-to-texture then post-process).
3. Generate Code: Use the required boilerplate with extension checking.
4. Verify: Run `./run_tests.sh`, read the resulting `.json` file, and apply the Verification Decision Logic.
5. **Pass:** Success.
6. **Fail (Bug):** Fix code -> Goto Step 4.
7. **Fail (Unsupported):** Log to UNSUPPORTED.md -> Stop.
8. **Final Output:** Ensure the clean, working file is in `agent_outputs/`.

## Advanced Targeting Instructions

Create test cases that leverage the full power of WebGL pipeline interactions:

- **Multi-pass rendering**: Render to texture, then use as input for subsequent passes
- **Complex shader interactions**: Vertex shaders writing to varyings consumed by fragment shaders
- **Extension combinations**: Mix multiple extensions in single test (e.g., float textures + multiple render targets)
- **State management**: Heavy interleaving of state changes, texture binding, and draw calls
- **Buffer/texture sharing**: Same data used as different types across multiple shader stages
- **Framebuffer operations**: Complex render-to-texture with multiple attachments and blending
- **Sampler state variations**: Different filtering, wrapping modes, and LOD settings

Focus on creating "spaghetti-like" valid resource usage where textures and buffers are shared across multiple shaders and passes, giving the mutation engine rich material to work with.