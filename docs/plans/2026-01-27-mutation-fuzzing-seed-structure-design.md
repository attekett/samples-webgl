# Mutation-Based Fuzzing Seed Structure Design

**Date**: 2026-01-27
**Purpose**: Comprehensive agent instructions for creating WebGL seed files optimized for mutation-based fuzzers (radamsa)
**Target**: Driver memory corruption bugs (UAF, buffer overflows, heap corruption)

## Executive Summary

This design optimizes WebGL test seeds for mutation-based fuzzing with radamsa. Unlike traditional conformance tests, these seeds are "mutation amplifiers" - valid code that becomes dangerous when corrupted. The design focuses on:

1. **Line repetition effectiveness** - Redundant state changes that break when duplicated
2. **Numeric mutation impact** - Strategic variable placement for maximum corruption
3. **Error path exploitation** - Try-catch blocks that allow driver state corruption to accumulate
4. **Driver crash detection** - Silent error handling that preserves crash signals

**Key Insight**: We're not testing correctness - we're creating "high-biomass" seeds that mutate into interesting crashes.

## Mutation Strategy

**Primary Mutation Operators:**
- **Line repetition/deletion** - Radamsa duplicates or removes entire lines
- **Numeric mutations** - Buffer sizes, indices, offsets, dimensions mutated

**Target Vulnerabilities:**
- Driver memory corruption (UAF, double-free, heap overflow)
- Error path bugs where driver state corrupts after validation failures
- Resource lifetime bugs (use-after-delete)
- State machine corruption from invalid operation sequences

**Fuzzing Workflow:**
1. Radamsa mutates seed HTML file (byte/line level)
2. External tool feeds mutated file to browser
3. Driver crashes/segfaults indicate interesting bugs
4. JavaScript errors are NOT the primary signal (driver crashes are)

## Three-Zone Architecture

Every seed file follows this structure:

### Zone 1: Declaration Zone (Top of Script)

```javascript
// Tier 1: Amplification Variables (strategic coupling)
const texSize = 256;
const texPixels = texSize * texSize;
const bufferSize = texPixels * 4;
const vertexCount = 6;
const instanceCount = vertexCount * 2;

// Tier 3: Enum Constants (mutation via line repetition)
const bufferTarget = gl.ARRAY_BUFFER;
const bufferUsage = gl.STATIC_DRAW;
const textureTarget = gl.TEXTURE_2D;
const textureFormat = gl.RGBA;
```

**Purpose**: Create "amplification points" where one numeric mutation cascades through multiple operations.

**Design Rules**:
- 5-8 amplification variables per seed
- 4-6 enum constant variables per seed
- Use derived values (e.g., `bufferSize = texSize * texSize * 4`)
- Variables affect 2+ operations later in the code

### Zone 2: Setup Zone (Resource Creation)

```javascript
// Block 1: Buffer creation with bind ping-pong
try {
    const buffer1 = gl.createBuffer();
    const buffer2 = gl.createBuffer();
    gl.bindBuffer(bufferTarget, buffer1);
    gl.bindBuffer(bufferTarget, buffer2);
    gl.bindBuffer(bufferTarget, buffer1);
    gl.bufferData(bufferTarget, bufferSize, bufferUsage); // Uses amplification variable
    gl.bufferSubData(bufferTarget, 0, new Float32Array(128)); // Inline literal
} catch(e) { console.log(e); }
```

**Purpose**: Create WebGL resources with redundant operations and mixed variable/literal usage.

**Design Rules**:
- 4-8 try-catch blocks in setup zone
- Each block: buffer, texture, shader, FBO, or renderbuffer setup
- Mix inline literals (Tier 2) with variable references (Tier 1 & 3)
- 3-5 inline numeric literals per block
- Reference 2-3 amplification/enum variables per block

### Zone 3: Execution Zone (Rendering/Computation)

```javascript
// Block 7: Multi-pass rendering with FBO switching
try {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
    gl.viewport(0, 0, texSize, texSize); // Uses amplification variable
    gl.drawArrays(gl.TRIANGLES, 0, vertexCount); // Uses amplification variable

    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo2);
    gl.viewport(0, 0, 512, 512); // Inline literal
    gl.drawArrays(gl.TRIANGLES, 0, 18); // Inline literal

    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, 256, 256); // Inline literal
    gl.drawArrays(gl.TRIANGLES, 0, vertexCount);
} catch(e) { console.log(e); }
```

**Purpose**: Execute rendering/computation with accumulated driver state corruption.

**Design Rules**:
- 2-4 try-catch blocks in execution zone
- State configuration, attribute setup, draw calls, resource cleanup
- Maximum mixing of literals and variables
- Operations use resources created in Setup Zone

## Variable Tier System

### Tier 1: Amplification Variables

**Location**: Declaration Zone
**Purpose**: One mutation affects multiple operations
**Examples**:
```javascript
const texSize = 256;           // Used in: texImage2D, viewport, buffer sizing
const vertexCount = 6;          // Used in: drawArrays, buffer sizing, instance count
const mipLevels = 4;            // Used in: texStorage, loop bounds, framebuffer setup
```

**Design Rules**:
- 5-8 per seed
- Used in 2+ operations
- Create derived values (e.g., `bufSize = texSize * texSize * 4`)
- Mutating to -1, 0, or huge values should cause constraint violations

### Tier 2: Hot Spot Inlines

**Location**: Within operation blocks
**Purpose**: Independent mutation targets for localized corruption
**Examples**:
```javascript
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 512, 512, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 32, 0);
gl.drawArrays(gl.TRIANGLES, 0, 18);
```

**Design Rules**:
- 3-5 per try-catch block
- Critical values: buffer sizes, texture dimensions, stride, offset, vertex count
- No variables - direct literals only
- Values should be "dangerous" if mutated (sizes, indices, offsets)

### Tier 3: Enum Constants

**Location**: Declaration Zone
**Purpose**: Line repetition creates enum corruption
**Examples**:
```javascript
const bufferTarget = gl.ARRAY_BUFFER;
const bufferUsage = gl.STATIC_DRAW;
const textureTarget = gl.TEXTURE_2D;
```

**Design Rules**:
- 4-6 per seed
- Used in 3+ operations
- Radamsa duplicating declaration lines with different values creates enum corruption
- Common targets: buffer targets, texture targets, usage hints, formats

## Line Repetition Patterns

These patterns work correctly as written but become dangerous when radamsa repeats or deletes lines.

### Pattern 1: Bind Ping-Pong

```javascript
try {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer1);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer2);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer1);
    gl.bufferData(gl.ARRAY_BUFFER, 1024, gl.STATIC_DRAW);
} catch(e) { console.log(e); }
```

**Mutation Impact**: Repeating any bind line → wrong buffer bound → bufferData targets unexpected buffer

**Design Rules**:
- 2-4 redundant binds per resource type
- Use with: buffers, textures, framebuffers
- Final operation assumes specific binding

### Pattern 2: Enable/Disable State Thrashing

```javascript
try {
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.DEPTH_TEST);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.depthMask(true);
} catch(e) { console.log(e); }
```

**Mutation Impact**: Repeating enable/disable → configuration applied to wrong state

**Design Rules**:
- 3-5 enable/disable toggles per state group
- Apply to: depth test, blend, stencil, culling, scissor
- Follow with state configuration calls

### Pattern 3: Resource Creation Redundancy

```javascript
try {
    const tex1 = gl.createTexture();
    const tex2 = gl.createTexture();
    const tex3 = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex1);
    gl.bindTexture(gl.TEXTURE_2D, tex2);
} catch(e) { console.log(e); }
```

**Mutation Impact**: Repeating create → resource leaks → driver exhaustion

**Design Rules**:
- 2-3 redundant creates per block
- Apply to: textures, buffers, framebuffers, shaders
- Not all resources need to be used

### Pattern 4: FBO Attachment Swapping

```javascript
try {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex1, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo2);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex2, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
} catch(e) { console.log(e); }
```

**Mutation Impact**: Repeating attachment lines → wrong texture on wrong FBO → dangling references

**Design Rules**:
- 4-6 FBO binds with attachment changes
- Swap between 2-3 FBOs
- Reattach same attachment points multiple times

### Pattern 5: Deletion and Reuse

```javascript
try {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.deleteBuffer(buffer);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, 1024, gl.STATIC_DRAW);
} catch(e) { console.log(e); }
```

**Mutation Impact**: Repeating delete → double-free or use-after-free

**Design Rules**:
- Include deletion block near end of seed
- Delete resource, then attempt to use it
- Bind deleted resources before operations
- Line repetition of delete creates double-free potential

## Try-Catch Block Strategy

**Critical Design Decision**: Use try-catch blocks to maximize error path exploitation.

### Why Try-Catch?

**Target vulnerability pattern**:
1. Mutation creates invalid parameter (e.g., negative buffer size)
2. Driver begins operation and modifies internal state
3. Driver validation fails, throws error to JavaScript
4. Driver error path cleanup is buggy (incomplete/corrupted)
5. Next WebGL operation uses corrupted driver state → crash/UAF

**Without try-catch**: Test stops at step 3, never reaching step 5

**With try-catch**: Test continues to step 5, triggering driver memory corruption

### Development vs Production Mode

**Development Phase** (with console.log for debugging):
```javascript
try {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, bufferSize, gl.STATIC_DRAW);
} catch(e) { console.log(e); } // TEMP: Debug aid during validation
```

**Production Phase** (silent for radamsa fuzzing):
```javascript
try {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, bufferSize, gl.STATIC_DRAW);
} catch(e) {} // Silent - ready for radamsa
```

### Block Boundary Design

**One try-catch per logical operation group**:
- Block 1: Buffer operations
- Block 2: Texture operations
- Block 3: Shader compilation
- Block 4: Framebuffer setup
- Block 5: State configuration
- Block 6: Attribute setup
- Block 7: Draw calls
- Block 8: Resource cleanup

**Design Rules**:
- 6-10 try-catch blocks per seed
- Each block independent enough to run after previous errors
- Each block coupled enough that corrupted state affects it
- No nested try-catch blocks
- No try-catch around extension checking (must fail fast if unsupported)

### Signal Preservation

**Crashes still detected** (these are NOT masked by try-catch):
- Driver segfaults
- GPU process crashes
- Browser process crashes
- Infinite loops (timeout detection)

**JavaScript errors suppressed** (these ARE masked):
- Invalid enum values
- Null/undefined parameters
- Type mismatches
- WebGL validation errors

**This is intentional** - we want driver crashes, not JS errors.

## Development Workflow

### Step 1: Feature Selection

1. Check `UNSUPPORTED.md` for known browser/extension limitations
2. Identify target WebGL feature (e.g., "Multiple Render Targets + Float Textures")
3. List required extensions in `REQUIRED_EXTENSIONS` array
4. Review existing seeds for similar features (avoid duplication)

### Step 2: Seed Generation

**File creation**:
```bash
# Create new seed in agent_outputs/
touch agent_outputs/feature_<descriptive_name>.html
```

**Structure implementation**:
1. Copy standard boilerplate (canvas + extension checking)
2. Populate Declaration Zone:
   - 5-8 Tier 1 amplification variables
   - 4-6 Tier 3 enum constant variables
3. Create Setup Zone (4-8 try-catch blocks):
   - Buffer operations with bind ping-pong
   - Texture operations with creation redundancy
   - Shader compilation
   - Framebuffer/renderbuffer operations
   - Mix inline literals (Tier 2) and variable references
4. Create Execution Zone (2-4 try-catch blocks):
   - State configuration with enable/disable thrashing
   - Vertex attribute setup
   - Draw calls with FBO switching
   - Resource cleanup with deletion patterns
5. **Keep `console.log(e)` in all catch blocks**

**Code density targets**:
- Total lines: 150-300 (not counting shader source)
- Try-catch blocks: 6-10
- Inline numeric literals: 20-40
- Amplification variables: 5-8
- Redundant operations: 30-50

### Step 3: Initial Validation

```bash
./run_tests.sh --test-file agent_outputs/feature_<name>.html --browsers firefox
```

**Check JSON output** (`agent_outputs/feature_<name>.json`):
```json
{
  "passed": true/false,
  "console_logs": [...],  // Review caught errors here
  "javascript_errors": [...],
  "webgl_errors": [...],
  "errors": [...]
}
```

**Error classification**:

| Error Type | Action |
|------------|--------|
| Syntax errors (undefined variable) | Fix immediately |
| API errors (invalid enum) | Fix immediately |
| UNSUPPORTED_EXTENSIONS | Stop, document in UNSUPPORTED.md |
| Logic errors (wrong constant) | Fix immediately |

### Step 4: Iteration Loop

```
REPEAT:
  1. Review console_logs array in JSON
  2. Fix issues (syntax, undefined vars, wrong enums)
  3. Re-run: ./run_tests.sh --test-file agent_outputs/feature_<name>.html --browsers firefox
  4. Check JSON output
UNTIL: passed == true AND console_logs == []
```

**Common issues during iteration**:
- Undefined variables (fix: declare in appropriate zone)
- Wrong WebGL enum values (fix: use correct gl.CONSTANT)
- Shader compilation errors (fix: GLSL syntax)
- Variables referenced before declaration (fix: move to declaration zone)
- Extension not available (stop: document in UNSUPPORTED.md)

**Never assume fixes work** - always verify with test runner.

### Step 5: Production Preparation

**Strip console.log statements**:
```bash
# Manual: Replace catch(e) { console.log(e); } with catch(e) {}
# Or use sed:
sed -i 's/catch(e) { console.log(e); }/catch(e) {}/g' agent_outputs/feature_<name>.html
```

**Final validation**:
```bash
./run_tests.sh --test-file agent_outputs/feature_<name>.html --browsers firefox
```

**Success criteria**:
- `"passed": true`
- `"console_logs": []`
- `"javascript_errors": []`
- `"webgl_errors": []`
- Screenshot shows visual output (not blank)

### Step 6: Corpus Integration

```bash
# Option 1: Keep in agent_outputs/
# (If using separate corpus directory)

# Option 2: Move to samples-webgl/
mv agent_outputs/feature_<name>.html samples-webgl/

# Commit
git add samples-webgl/feature_<name>.html
git commit -m "Add mutation seed: <feature description>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

## Complete Template

```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgl-canvas" width="256" height="256"></canvas>
<script>
const REQUIRED_EXTENSIONS = [
    'EXT_color_buffer_float',
    'OES_texture_float_linear'
];

// ============ DECLARATION ZONE ============
// Tier 1: Amplification Variables
const texSize = 256;
const texPixels = texSize * texSize;
const bufferSize = texPixels * 4;
const vertexCount = 6;
const instanceCount = vertexCount * 2;

// Tier 3: Enum Constants
const bufferTarget = gl.ARRAY_BUFFER;
const bufferUsage = gl.STATIC_DRAW;
const textureTarget = gl.TEXTURE_2D;
const textureFormat = gl.RGBA;

async function main() {
    const canvas = document.getElementById('webgl-canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) throw new Error("WebGL2 not supported");

    const missingExtensions = REQUIRED_EXTENSIONS.filter(ext => !gl.getExtension(ext));
    if (missingExtensions.length > 0) {
        throw new Error(`UNSUPPORTED_EXTENSIONS: ${missingExtensions.join(', ')}`);
    }
    REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));

    // ============ SETUP ZONE ============

    // Block 1: Buffer creation with bind ping-pong
    try {
        const buffer1 = gl.createBuffer();
        const buffer2 = gl.createBuffer();
        gl.bindBuffer(bufferTarget, buffer1);
        gl.bindBuffer(bufferTarget, buffer2);
        gl.bindBuffer(bufferTarget, buffer1);
        gl.bufferData(bufferTarget, bufferSize, bufferUsage);
        gl.bufferSubData(bufferTarget, 0, new Float32Array(128));
    } catch(e) { console.log(e); }

    // Block 2: Texture setup
    try {
        const texture1 = gl.createTexture();
        const texture2 = gl.createTexture();
        gl.bindTexture(textureTarget, texture1);
        gl.texImage2D(textureTarget, 0, textureFormat, 512, 512, 0, textureFormat, gl.UNSIGNED_BYTE, null);
        gl.bindTexture(textureTarget, texture2);
        gl.texImage2D(textureTarget, 0, gl.RGBA32F, texSize, texSize, 0, gl.RGBA, gl.FLOAT, null);
        gl.texParameteri(textureTarget, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    } catch(e) { console.log(e); }

    // Block 3: Shader compilation
    try {
        const vs = gl.createShader(gl.VERTEX_SHADER);
        gl.shaderSource(vs, `#version 300 es
            in vec3 position;
            void main() { gl_Position = vec4(position, 1.0); }
        `);
        gl.compileShader(vs);

        const fs = gl.createShader(gl.FRAGMENT_SHADER);
        gl.shaderSource(fs, `#version 300 es
            precision highp float;
            out vec4 fragColor;
            void main() { fragColor = vec4(1.0); }
        `);
        gl.compileShader(fs);

        const program = gl.createProgram();
        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);
        gl.useProgram(program);
    } catch(e) { console.log(e); }

    // Block 4: FBO setup with attachment swapping
    try {
        const fbo1 = gl.createFramebuffer();
        const fbo2 = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, textureTarget, texture1, 0);
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo2);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, textureTarget, texture2, 0);
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
    } catch(e) { console.log(e); }

    // ============ EXECUTION ZONE ============

    // Block 5: State configuration with enable/disable thrashing
    try {
        gl.enable(gl.DEPTH_TEST);
        gl.disable(gl.DEPTH_TEST);
        gl.enable(gl.DEPTH_TEST);
        gl.depthFunc(gl.LEQUAL);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.disable(gl.BLEND);
    } catch(e) { console.log(e); }

    // Block 6: Draw calls with FBO switching
    try {
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
        gl.viewport(0, 0, texSize, texSize);
        gl.drawArrays(gl.TRIANGLES, 0, vertexCount);

        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, 256, 256);
        gl.drawArrays(gl.TRIANGLES, 0, 18);
    } catch(e) { console.log(e); }

    // Block 7: Resource cleanup with deletion patterns
    try {
        gl.bindBuffer(bufferTarget, buffer1);
        gl.deleteBuffer(buffer1);
        gl.bindBuffer(bufferTarget, buffer1);
    } catch(e) { console.log(e); }
}

main().catch(err => { throw err; });
</script>
</body>
</html>
```

## Anti-Patterns (Never Do This)

### ❌ Defensive Programming

```javascript
// WRONG - validation prevents interesting mutations
if (bufferSize > 0 && bufferSize < 1000000) {
    gl.bufferData(gl.ARRAY_BUFFER, bufferSize, gl.STATIC_DRAW);
}

// RIGHT - let mutations try anything
gl.bufferData(gl.ARRAY_BUFFER, bufferSize, gl.STATIC_DRAW);
```

### ❌ Error Checking

```javascript
// WRONG - checking compile status prevents error path bugs
gl.compileShader(shader);
if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    return; // Never do this
}

// RIGHT - assume success, let errors propagate
gl.compileShader(shader);
gl.attachShader(program, shader);
```

### ❌ Clean Abstractions

```javascript
// WRONG - functions hide mutation targets
function createBuffer(size) {
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, size, gl.STATIC_DRAW);
    return buf;
}

// RIGHT - inline everything, expose all operations
const buf = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buf);
gl.bufferData(gl.ARRAY_BUFFER, 1024, gl.STATIC_DRAW);
```

### ❌ Logical Variable Names Only

```javascript
// WRONG - all variables, no inline literals
const width = 256;
const height = 256;
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);

// RIGHT - mix both for diverse mutation surface
const texSize = 256;
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, texSize, texSize, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
gl.viewport(0, 0, 512, 512);  // Different value inline
```

### ❌ Minimal Code

```javascript
// WRONG - clean, minimal code with no redundancy
gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
gl.bufferData(gl.ARRAY_BUFFER, 1024, gl.STATIC_DRAW);

// RIGHT - redundant operations that become dangerous when repeated
gl.bindBuffer(gl.ARRAY_BUFFER, buffer1);
gl.bindBuffer(gl.ARRAY_BUFFER, buffer2);
gl.bindBuffer(gl.ARRAY_BUFFER, buffer1);
gl.bufferData(gl.ARRAY_BUFFER, 1024, gl.STATIC_DRAW);
```

### ❌ Nested Try-Catch

```javascript
// WRONG - nested try-catch complicates error paths
try {
    try {
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    } catch(e1) {}
    gl.bufferData(gl.ARRAY_BUFFER, 1024, gl.STATIC_DRAW);
} catch(e2) {}

// RIGHT - one try-catch per logical block
try {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, 1024, gl.STATIC_DRAW);
} catch(e) {}
```

## Key Principles Summary

1. **Code is a mutation target, not a program** - Every line is potential fuzzer input
2. **Redundancy is good** - "Spaghetti" code with repeated operations creates fragile state machines
3. **Inline some, parameterize others** - Balance between localized and cascading mutations
4. **Errors are features** - Try-catch allows error path bugs to corrupt driver state
5. **Crashes are success** - Driver segfaults are the goal, not test passes
6. **Never be defensive** - No validation, no checking, no error handling beyond try-catch
7. **Development != Production** - Use console.log during dev, strip for fuzzing
8. **Validate everything** - Never assume fixes work, always check JSON output
9. **Extensions are blockers** - Missing extensions = STOP, don't try to work around
10. **Machine-readable code** - Simple structure, no comments, no console output

## FAQ

**Q: Why not just generate random WebGL calls?**
A: Random generation creates mostly invalid code. These seeds are *valid* code that becomes *invalid* when mutated - much more effective for finding real bugs.

**Q: Why so much redundant code?**
A: Redundancy creates "state machine biomass" - more opportunities for line repetition to create subtle state corruption.

**Q: Won't try-catch hide bugs?**
A: No - we're hunting driver crashes, not JS errors. Driver segfaults kill the process regardless of try-catch.

**Q: Why mix inline literals and variables?**
A: Different mutation strategies need different targets. Inline literals create localized corruption, variables create cascading failures.

**Q: Why include deletion patterns?**
A: Use-after-delete is a common driver bug. Attempting operations on deleted resources exercises this path.

**Q: Should I make the code "realistic"?**
A: No - this isn't a demo or tutorial. Code should maximize mutation effectiveness, not human readability.

**Q: What if the test passes but renders nothing?**
A: Some operations (like FBO rendering without readback) won't show visual output. As long as no errors occur, it's valid.

**Q: How do I know if I have enough redundancy?**
A: 2-4 redundant bind operations per resource, 3-5 enable/disable toggles per state group, 4-6 FBO switches.

**Q: Can I simplify "ugly" code?**
A: No - "ugly" code is often the most effective for fuzzing. Resist the urge to clean it up.

**Q: Should I add comments explaining the patterns?**
A: Never add comments to seed files - they're machine input, not documentation.

## Validation Checklist

Before committing a seed to the corpus:

- [ ] File in `agent_outputs/` directory (or `samples-webgl/`)
- [ ] `REQUIRED_EXTENSIONS` array populated
- [ ] 5-8 Tier 1 amplification variables
- [ ] 4-6 Tier 3 enum constant variables
- [ ] 20-40 Tier 2 inline numeric literals
- [ ] 6-10 try-catch blocks
- [ ] All catch blocks use `catch(e) {}` (no console.log)
- [ ] Bind ping-pong patterns (2-4 per resource)
- [ ] Enable/disable thrashing (3-5 per state group)
- [ ] Resource creation redundancy (2-3 creates per block)
- [ ] FBO attachment swapping (if using FBOs)
- [ ] Deletion patterns (in cleanup block)
- [ ] Test passes: `./run_tests.sh --test-file <file> --browsers firefox`
- [ ] JSON shows: `"passed": true, "console_logs": []`
- [ ] Screenshot shows output (not blank)
- [ ] Total lines: 150-300
- [ ] No comments in code
- [ ] No console.log statements in final version

---

**End of Design Document**
