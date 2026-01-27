# Mutation-Optimized WebGL Seeds Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create 5 new mutation-optimized WebGL seed files following the radamsa-focused design from docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md

**Architecture:** Each seed implements the three-zone architecture (Declaration/Setup/Execution) with line repetition patterns, variable tier system, and try-catch blocks for error path exploitation. Seeds target different WebGL2 feature combinations to maximize corpus diversity.

**Tech Stack:** WebGL2, GLSL ES 3.00, HTML5, Firefox for testing

---

## Seed Selection Strategy

Based on existing corpus analysis (66 seeds) and UNSUPPORTED.md, we'll create:

1. **Seed 1**: Multiple Render Targets + Float Textures (WebGL2 native)
2. **Seed 2**: Uniform Buffer Objects + Instanced Rendering
3. **Seed 3**: Transform Feedback + Vertex Array Objects
4. **Seed 4**: 3D Textures + Texture Arrays with Complex Sampling
5. **Seed 5**: Sync Objects + Query Objects with State Thrashing

All seeds use WebGL2 native features (avoiding unsupported WebGL1 extensions per UNSUPPORTED.md).

---

## Task 1: Create MRT + Float Textures Seed

**Files:**
- Create: `agent_outputs/integrated_mrt_float_textures_mutation.html`
- Test: Run `./run_tests.sh --test-file agent_outputs/integrated_mrt_float_textures_mutation.html --browsers firefox`

**Step 1: Write seed boilerplate with extensions**

Create file with standard structure:

```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgl-canvas" width="256" height="256"></canvas>
<script>
const REQUIRED_EXTENSIONS = [
    'EXT_color_buffer_float'
];

// ============ DECLARATION ZONE ============
const texSize = 256;
const texPixels = texSize * texSize;
const bufferSize = texPixels * 4;
const vertexCount = 6;
const mrtCount = 4;

const bufferTarget = gl.ARRAY_BUFFER;
const bufferUsage = gl.STATIC_DRAW;
const textureTarget = gl.TEXTURE_2D;

async function main() {
    const canvas = document.getElementById('webgl-canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) throw new Error("WebGL2 not supported");

    const missingExtensions = REQUIRED_EXTENSIONS.filter(ext => !gl.getExtension(ext));
    if (missingExtensions.length > 0) {
        throw new Error(`UNSUPPORTED_EXTENSIONS: ${missingExtensions.join(', ')}`);
    }
    REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));

    // Implementation continues in next steps
}

main().catch(err => { throw err; });
</script>
</body>
</html>
```

**Step 2: Add Setup Zone - Buffer operations with bind ping-pong**

Add after DECLARATION ZONE:

```javascript
// ============ SETUP ZONE ============

// Block 1: Vertex buffer with bind ping-pong
try {
    const positionData = new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]);
    const buffer1 = gl.createBuffer();
    const buffer2 = gl.createBuffer();
    gl.bindBuffer(bufferTarget, buffer1);
    gl.bindBuffer(bufferTarget, buffer2);
    gl.bindBuffer(bufferTarget, buffer1);
    gl.bufferData(bufferTarget, bufferSize, bufferUsage);
    gl.bufferSubData(bufferTarget, 0, positionData);
} catch(e) { console.log(e); }

// Block 2: Float texture creation with redundancy
try {
    const tex1 = gl.createTexture();
    const tex2 = gl.createTexture();
    const tex3 = gl.createTexture();
    const tex4 = gl.createTexture();
    gl.bindTexture(textureTarget, tex1);
    gl.texImage2D(textureTarget, 0, gl.RGBA32F, texSize, texSize, 0, gl.RGBA, gl.FLOAT, null);
    gl.bindTexture(textureTarget, tex2);
    gl.texImage2D(textureTarget, 0, gl.RGBA32F, 512, 512, 0, gl.RGBA, gl.FLOAT, null);
    gl.bindTexture(textureTarget, tex3);
    gl.texImage2D(textureTarget, 0, gl.RGBA16F, texSize, texSize, 0, gl.RGBA, gl.HALF_FLOAT, null);
    gl.bindTexture(textureTarget, tex4);
    gl.texImage2D(textureTarget, 0, gl.R32F, 256, 256, 0, gl.RED, gl.FLOAT, null);
} catch(e) { console.log(e); }
```

**Step 3: Add Setup Zone - Shader program**

```javascript
// Block 3: Shader compilation
try {
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, `#version 300 es
        in vec2 position;
        out vec2 vTexCoord;
        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
            vTexCoord = position * 0.5 + 0.5;
        }
    `);
    gl.compileShader(vs);

    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, `#version 300 es
        precision highp float;
        in vec2 vTexCoord;
        layout(location = 0) out vec4 color0;
        layout(location = 1) out vec4 color1;
        layout(location = 2) out vec4 color2;
        layout(location = 3) out vec4 color3;
        void main() {
            float val = vTexCoord.x * vTexCoord.y;
            color0 = vec4(val, 0.0, 0.0, 1.0);
            color1 = vec4(0.0, val, 0.0, 1.0);
            color2 = vec4(0.0, 0.0, val, 1.0);
            color3 = vec4(val);
        }
    `);
    gl.compileShader(fs);

    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    gl.useProgram(program);
} catch(e) { console.log(e); }
```

**Step 4: Add Setup Zone - FBO with MRT attachment swapping**

```javascript
// Block 4: FBO setup with MRT attachment swapping
try {
    const fbo1 = gl.createFramebuffer();
    const fbo2 = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, textureTarget, tex1, 0);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT1, textureTarget, tex2, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo2);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, textureTarget, tex3, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT2, textureTarget, tex3, 0);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT3, textureTarget, tex4, 0);
    gl.drawBuffers([gl.COLOR_ATTACHMENT0, gl.COLOR_ATTACHMENT1, gl.COLOR_ATTACHMENT2, gl.COLOR_ATTACHMENT3]);
} catch(e) { console.log(e); }
```

**Step 5: Add Execution Zone - State configuration and draw calls**

```javascript
// ============ EXECUTION ZONE ============

// Block 5: State configuration with enable/disable thrashing
try {
    gl.enable(gl.BLEND);
    gl.disable(gl.BLEND);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.DEPTH_TEST);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
} catch(e) { console.log(e); }

// Block 6: Vertex attribute setup
try {
    const posLoc = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 8, 0);
} catch(e) { console.log(e); }

// Block 7: Multi-pass rendering with FBO switching
try {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo1);
    gl.viewport(0, 0, texSize, texSize);
    gl.drawArrays(gl.TRIANGLES, 0, vertexCount);

    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo2);
    gl.viewport(0, 0, 512, 512);
    gl.drawArrays(gl.TRIANGLES, 0, 6);

    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, 256, 256);
    gl.drawArrays(gl.TRIANGLES, 0, vertexCount);
} catch(e) { console.log(e); }

// Block 8: Resource cleanup with deletion patterns
try {
    gl.bindBuffer(bufferTarget, buffer1);
    gl.deleteBuffer(buffer1);
    gl.bindBuffer(bufferTarget, buffer1);
    gl.deleteTexture(tex1);
    gl.bindTexture(textureTarget, tex1);
} catch(e) { console.log(e); }
```

**Step 6: Run test with console.log (development mode)**

```bash
./run_tests.sh --test-file agent_outputs/integrated_mrt_float_textures_mutation.html --browsers firefox
```

Expected: Test runs, check JSON output for any errors in console_logs

**Step 7: Fix any errors reported in JSON**

Review `agent_outputs/integrated_mrt_float_textures_mutation.json`, fix:
- Undefined variables
- Wrong WebGL constants
- Shader compilation errors

Re-run test after each fix.

**Step 8: Strip console.log statements**

Replace all `catch(e) { console.log(e); }` with `catch(e) {}`

**Step 9: Final validation**

```bash
./run_tests.sh --test-file agent_outputs/integrated_mrt_float_textures_mutation.html --browsers firefox
```

Expected: `"passed": true`, `"console_logs": []`, `"javascript_errors": []`

**Step 10: Commit**

```bash
git add agent_outputs/integrated_mrt_float_textures_mutation.html
git commit -m "Add mutation seed: MRT + Float Textures

Mutation-optimized seed following radamsa design:
- 6 amplification variables
- 5 enum constants
- 8 try-catch blocks with line repetition patterns
- Bind ping-pong, FBO swapping, deletion patterns
- Targets driver memory corruption via error paths

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Create UBO + Instanced Rendering Seed

**Files:**
- Create: `agent_outputs/integrated_ubo_instancing_mutation.html`
- Test: Run `./run_tests.sh --test-file agent_outputs/integrated_ubo_instancing_mutation.html --browsers firefox`

**Step 1: Write seed boilerplate**

```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgl-canvas" width="256" height="256"></canvas>
<script>
const REQUIRED_EXTENSIONS = [];

// ============ DECLARATION ZONE ============
const instanceCount = 32;
const vertexCount = 6;
const uboSize = 256;
const matrixSize = 16;
const bufferStride = 64;

const bufferTarget = gl.ARRAY_BUFFER;
const uboTarget = gl.UNIFORM_BUFFER;
const bufferUsage = gl.STATIC_DRAW;

async function main() {
    const canvas = document.getElementById('webgl-canvas');
    const gl = canvas.getContext('webgl2');
    if (!gl) throw new Error("WebGL2 not supported");

    // No extensions required for WebGL2 native features
}

main().catch(err => { throw err; });
</script>
</body>
</html>
```

**Step 2: Add Setup Zone - Buffer and UBO operations**

```javascript
// ============ SETUP ZONE ============

// Block 1: Vertex buffer with bind ping-pong
try {
    const vertices = new Float32Array([-0.1, -0.1, 0.1, -0.1, -0.1, 0.1, -0.1, 0.1, 0.1, -0.1, 0.1, 0.1]);
    const vbo1 = gl.createBuffer();
    const vbo2 = gl.createBuffer();
    gl.bindBuffer(bufferTarget, vbo1);
    gl.bindBuffer(bufferTarget, vbo2);
    gl.bindBuffer(bufferTarget, vbo1);
    gl.bufferData(bufferTarget, vertices, bufferUsage);
} catch(e) { console.log(e); }

// Block 2: Instance data buffer
try {
    const instanceData = new Float32Array(instanceCount * 4);
    for (let i = 0; i < instanceCount; i++) {
        instanceData[i * 4] = (i % 8) * 0.25 - 1.0;
        instanceData[i * 4 + 1] = Math.floor(i / 8) * 0.25 - 1.0;
        instanceData[i * 4 + 2] = i / instanceCount;
        instanceData[i * 4 + 3] = 1.0;
    }
    const instanceBuffer = gl.createBuffer();
    gl.bindBuffer(bufferTarget, instanceBuffer);
    gl.bufferData(bufferTarget, instanceData, bufferUsage);
} catch(e) { console.log(e); }

// Block 3: UBO creation with redundancy
try {
    const ubo1 = gl.createBuffer();
    const ubo2 = gl.createBuffer();
    const ubo3 = gl.createBuffer();
    gl.bindBuffer(uboTarget, ubo1);
    gl.bufferData(uboTarget, uboSize, bufferUsage);
    gl.bindBuffer(uboTarget, ubo2);
    gl.bufferData(uboTarget, 512, gl.DYNAMIC_DRAW);
    gl.bindBuffer(uboTarget, ubo3);
    gl.bufferData(uboTarget, uboSize, bufferUsage);

    const matrixData = new Float32Array(matrixSize);
    for (let i = 0; i < 16; i++) matrixData[i] = i === 0 || i === 5 || i === 10 || i === 15 ? 1.0 : 0.0;
    gl.bindBuffer(uboTarget, ubo1);
    gl.bufferSubData(uboTarget, 0, matrixData);
} catch(e) { console.log(e); }
```

**Step 3: Add Setup Zone - Shader with UBO**

```javascript
// Block 4: Shader compilation with UBO
try {
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, `#version 300 es
        layout(std140) uniform Matrices {
            mat4 projection;
            mat4 view;
        };
        in vec2 position;
        in vec4 instanceOffset;
        out vec4 vColor;
        void main() {
            vec2 pos = position + instanceOffset.xy;
            gl_Position = projection * view * vec4(pos, 0.0, 1.0);
            vColor = vec4(instanceOffset.z, 1.0 - instanceOffset.z, 0.5, 1.0);
        }
    `);
    gl.compileShader(vs);

    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, `#version 300 es
        precision highp float;
        in vec4 vColor;
        out vec4 fragColor;
        void main() {
            fragColor = vColor;
        }
    `);
    gl.compileShader(fs);

    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    gl.useProgram(program);
} catch(e) { console.log(e); }

// Block 5: UBO binding with redundancy
try {
    const uboIndex = gl.getUniformBlockIndex(program, 'Matrices');
    gl.uniformBlockBinding(program, uboIndex, 0);
    gl.bindBufferBase(uboTarget, 0, ubo1);
    gl.bindBufferBase(uboTarget, 1, ubo2);
    gl.bindBufferBase(uboTarget, 0, ubo1);
} catch(e) { console.log(e); }
```

**Step 4: Add Execution Zone**

```javascript
// ============ EXECUTION ZONE ============

// Block 6: State configuration with enable/disable thrashing
try {
    gl.enable(gl.BLEND);
    gl.disable(gl.BLEND);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE);
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.DEPTH_TEST);
    gl.enable(gl.DEPTH_TEST);
} catch(e) { console.log(e); }

// Block 7: Vertex attribute setup for instancing
try {
    const posLoc = gl.getAttribLocation(program, 'position');
    const instanceLoc = gl.getAttribLocation(program, 'instanceOffset');

    gl.bindBuffer(bufferTarget, vbo1);
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 8, 0);

    gl.bindBuffer(bufferTarget, instanceBuffer);
    gl.enableVertexAttribArray(instanceLoc);
    gl.vertexAttribPointer(instanceLoc, 4, gl.FLOAT, false, 16, 0);
    gl.vertexAttribDivisor(instanceLoc, 1);
} catch(e) { console.log(e); }

// Block 8: Instanced draw calls
try {
    gl.viewport(0, 0, 256, 256);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArraysInstanced(gl.TRIANGLES, 0, vertexCount, instanceCount);
    gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, 16);
    gl.drawArraysInstanced(gl.TRIANGLES, 0, vertexCount, instanceCount);
} catch(e) { console.log(e); }

// Block 9: Resource cleanup with deletion patterns
try {
    gl.bindBuffer(uboTarget, ubo1);
    gl.deleteBuffer(ubo1);
    gl.bindBuffer(uboTarget, ubo1);
    gl.bindBufferBase(uboTarget, 0, ubo1);
} catch(e) { console.log(e); }
```

**Step 5-9: Test, fix, strip console.log, validate, commit**

Same process as Task 1.

Commit message:
```
Add mutation seed: UBO + Instanced Rendering

Mutation-optimized seed with:
- 6 amplification variables
- 3 enum constants
- 9 try-catch blocks
- UBO binding redundancy, instancing patterns
- Targets driver state corruption in uniform buffer handling

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Task 3: Create Transform Feedback + VAO Seed

**Files:**
- Create: `agent_outputs/integrated_transform_feedback_vao_mutation.html`

**Step 1: Write seed with Transform Feedback setup**

Follow same structure with:
- Declaration Zone: `feedbackBufferSize`, `vertexCount`, `tfVaryingCount`
- Setup Zone: VAO creation redundancy, TF buffer bind ping-pong, shader with varyings
- Execution Zone: TF activation/deactivation thrashing, multi-pass with pause/resume

**Step 2-9: Implement, test, validate, commit**

Commit message:
```
Add mutation seed: Transform Feedback + VAO

Mutation-optimized seed with:
- Transform feedback buffer management
- VAO state isolation patterns
- Pause/resume thrashing
- Targets driver bugs in TF state machines

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Task 4: Create 3D Textures + Texture Arrays Seed

**Files:**
- Create: `agent_outputs/integrated_3d_textures_arrays_mutation.html`

**Step 1: Write seed with 3D texture operations**

Follow structure with:
- Declaration Zone: `texDepth`, `texLayers`, `texSize3D`
- Setup Zone: 3D texture creation redundancy, texture array setup, complex sampling
- Execution Zone: Layer-by-layer rendering, 3D texture slicing

**Step 2-9: Implement, test, validate, commit**

Commit message:
```
Add mutation seed: 3D Textures + Texture Arrays

Mutation-optimized seed with:
- 3D texture dimension mutations
- Texture array layer management
- Complex sampling patterns
- Targets driver bugs in 3D texture addressing

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Task 5: Create Sync Objects + Query Objects Seed

**Files:**
- Create: `agent_outputs/integrated_sync_query_mutation.html`

**Step 1: Write seed with sync/query operations**

Follow structure with:
- Declaration Zone: `queryCount`, `syncTimeout`, `fenceCount`
- Setup Zone: Query object creation redundancy, fence sync creation patterns
- Execution Zone: Query begin/end thrashing, sync wait patterns, deletion after wait

**Step 2-9: Implement, test, validate, commit**

Commit message:
```
Add mutation seed: Sync Objects + Query Objects

Mutation-optimized seed with:
- Fence sync creation/deletion patterns
- Query object state thrashing
- Wait timeout mutations
- Targets driver synchronization bugs

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Validation Checklist (Apply to Each Seed)

Before committing each seed, verify:

- [ ] 5-8 Tier 1 amplification variables in Declaration Zone
- [ ] 4-6 Tier 3 enum constant variables in Declaration Zone
- [ ] 20-40 Tier 2 inline numeric literals throughout
- [ ] 6-10 try-catch blocks total
- [ ] All `catch(e)` blocks use `catch(e) {}` (no console.log)
- [ ] Bind ping-pong patterns (2-4 per resource type)
- [ ] Enable/disable thrashing (3-5 toggles per state group)
- [ ] FBO/resource swapping patterns where applicable
- [ ] Deletion + reuse patterns in final blocks
- [ ] Test passes: `"passed": true`
- [ ] No console output: `"console_logs": []`
- [ ] No JavaScript errors: `"javascript_errors": []`
- [ ] Screenshot shows visual output
- [ ] File size: 150-300 lines (excluding shader strings)

---

## Success Criteria

All 5 seeds:
1. Follow three-zone architecture exactly
2. Implement variable tier system correctly
3. Use line repetition patterns throughout
4. Include try-catch blocks without console.log
5. Pass validation with Firefox
6. Generate visual output
7. Committed with descriptive messages

**Estimated Time:** 2-3 hours for all 5 seeds (25-35 minutes per seed including testing)

---

## Notes

- Use Firefox for all testing (superior WebGL2 support)
- All seeds use WebGL2 native features (no extensions needed except EXT_color_buffer_float for Seed 1)
- Focus on mutation effectiveness over visual complexity
- Redundancy is intentional - do not "clean up" code
- Each seed targets different driver subsystems for corpus diversity
