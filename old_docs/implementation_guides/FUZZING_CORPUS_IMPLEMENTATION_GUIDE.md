# WebGPU Fuzzing Corpus - Implementation Guide

This document provides detailed implementation specifications for each corpus test case. It is designed to be followed by an LLM to generate complete, working test cases.

## Implementation Template

All implementations must follow this structure:

```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgpu-canvas" width="256" height="256"></canvas>
<script>
async function main() {
    if (!navigator.gpu) throw new Error("WebGPU not supported");
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) throw new Error("No GPUAdapter found");
    const device = await adapter.requestDevice();
    const canvas = document.getElementById('webgpu-canvas');
    const context = canvas.getContext('webgpu');
    const format = navigator.gpu.getPreferredCanvasFormat();
    context.configure({ device, format });
    device.pushErrorScope('validation');
    
    // === IMPLEMENTATION HERE ===
    
    const error = await device.popErrorScope();
    if (error) throw new Error(`WebGPU Validation Error: ${error.message}`);
}
main();
</script>
</body>
</html>
```

---

# CATEGORY 2: Multi-Pass Execution Flows (HIGH PRIORITY)

## FLOW-CR-001: Compute Generates Vertex Data

**Purpose:** Compute shader generates vertex positions, which are then used for rendering.

**Resources:**
- Buffer A: STORAGE | VERTEX, size 1024 bytes (enough for ~20 vertices)

**Shaders:**
```wgsl
// Compute shader
@group(0) @binding(0) var<storage, read_write> vertices: array<vec4<f32>>;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let i = id.x;
    if (i < 6u) {
        let angle = f32(i) * 3.14159 / 3.0;
        vertices[i] = vec4<f32>(cos(angle) * 0.5, sin(angle) * 0.5, 0.0, 1.0);
    }
}

// Vertex shader
@vertex fn vs(@location(0) pos: vec4<f32>) -> @builtin(position) vec4<f32> {
    return pos;
}

// Fragment shader
@fragment fn fs() -> @location(0) vec4<f32> {
    return vec4<f32>(1.0, 0.5, 0.0, 1.0);
}
```

**Execution Flow:**
1. Create buffer with usage STORAGE | VERTEX | COPY_DST
2. Create compute pipeline
3. Create bind group with buffer as storage
4. Create render pipeline expecting vec4<f32> vertex input
5. Encode compute pass: setPipeline, setBindGroup, dispatchWorkgroups(1)
6. Encode render pass: setVertexBuffer, draw(6)
7. Finish, submit

---

## FLOW-CR-002: Compute Generates Instance Data

**Purpose:** Compute calculates per-instance transforms for instanced rendering.

**Resources:**
- Buffer A (vertex): VERTEX, 48 bytes (triangle)
- Buffer B (instances): STORAGE | VERTEX, 512 bytes (32 instances × 16 bytes each)

**Shaders:**
```wgsl
// Compute shader
struct Instance { offset: vec2<f32>, scale: f32, pad: f32 };
@group(0) @binding(0) var<storage, read_write> instances: array<Instance>;

@compute @workgroup_size(32)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let i = id.x;
    let row = i / 8u;
    let col = i % 8u;
    instances[i].offset = vec2<f32>(f32(col) * 0.2 - 0.7, f32(row) * 0.2 - 0.3);
    instances[i].scale = 0.08;
}

// Vertex shader
struct Instance { offset: vec2<f32>, scale: f32, pad: f32 };
@vertex fn vs(
    @location(0) pos: vec2<f32>,
    @location(1) inst_offset: vec2<f32>,
    @location(2) inst_scale: f32
) -> @builtin(position) vec4<f32> {
    return vec4<f32>(pos * inst_scale + inst_offset, 0.0, 1.0);
}

@fragment fn fs() -> @location(0) vec4<f32> {
    return vec4<f32>(0.2, 0.6, 1.0, 1.0);
}
```

**Execution Flow:**
1. Create vertex buffer with triangle, create instance buffer with STORAGE | VERTEX
2. Create compute pipeline
3. Create render pipeline with vertex attributes:
   - location 0: vec2<f32> from buffer 0, stepMode vertex
   - location 1: vec2<f32> from buffer 1, stepMode instance
   - location 2: f32 from buffer 1, stepMode instance
4. Compute pass: generate instance data
5. Render pass: draw(3, 32) for 32 instances

---

## FLOW-CR-003: Compute Updates Uniforms

**Purpose:** Compute shader writes animation/simulation data that render shader reads as uniforms.

**Resources:**
- Buffer A: STORAGE | UNIFORM, 256 bytes

**Shaders:**
```wgsl
// Compute shader
struct Params { color: vec4<f32>, transform: mat4x4<f32> };
@group(0) @binding(0) var<storage, read_write> params: Params;

@compute @workgroup_size(1)
fn main() {
    params.color = vec4<f32>(0.8, 0.3, 0.1, 1.0);
    params.transform = mat4x4<f32>(
        vec4<f32>(0.8, 0.0, 0.0, 0.0),
        vec4<f32>(0.0, 0.8, 0.0, 0.0),
        vec4<f32>(0.0, 0.0, 1.0, 0.0),
        vec4<f32>(0.1, -0.1, 0.0, 1.0)
    );
}

// Vertex shader
struct Params { color: vec4<f32>, transform: mat4x4<f32> };
@group(0) @binding(0) var<uniform> params: Params;

@vertex fn vs(@location(0) pos: vec2<f32>) -> @builtin(position) vec4<f32> {
    return params.transform * vec4<f32>(pos, 0.0, 1.0);
}

@fragment fn fs() -> @location(0) vec4<f32> {
    return params.color;
}
```

**Key Detail:** Same buffer used as storage in compute, uniform in render. Different bind group layouts.

---

## FLOW-CR-004: Compute Generates Index Data

**Purpose:** Compute shader writes index buffer for dynamic mesh connectivity.

**Resources:**
- Buffer A (vertices): VERTEX, 64 bytes
- Buffer B (indices): STORAGE | INDEX, 48 bytes (12 indices × 4 bytes)

**Shaders:**
```wgsl
// Compute shader
@group(0) @binding(0) var<storage, read_write> indices: array<u32>;

@compute @workgroup_size(12)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    let i = id.x;
    // Generate indices for 4 triangles (quad grid)
    let quad_indices = array<u32, 12>(0u, 1u, 2u, 2u, 1u, 3u, 1u, 4u, 3u, 3u, 4u, 5u);
    if (i < 12u) { indices[i] = quad_indices[i]; }
}
```

**Execution Flow:**
1. Create vertex buffer with grid points
2. Create index buffer with STORAGE | INDEX
3. Compute pass fills indices
4. Render pass: setIndexBuffer, drawIndexed(12)

---

## FLOW-CR-005: Compute Indirect Parameters

**Purpose:** GPU-driven rendering where compute shader determines draw parameters.

**Resources:**
- Buffer A (indirect): STORAGE | INDIRECT, 16 bytes
- Buffer B (vertices): VERTEX, 64 bytes

**Shaders:**
```wgsl
// Compute shader writes draw indirect parameters
// struct { vertexCount: u32, instanceCount: u32, firstVertex: u32, firstInstance: u32 }
@group(0) @binding(0) var<storage, read_write> indirect: array<u32>;

@compute @workgroup_size(1)
fn main() {
    indirect[0] = 6u;  // vertexCount - draw a hexagon
    indirect[1] = 1u;  // instanceCount
    indirect[2] = 0u;  // firstVertex
    indirect[3] = 0u;  // firstInstance
}
```

**Execution Flow:**
1. Create indirect buffer with STORAGE | INDIRECT
2. Compute pass writes draw parameters
3. Render pass uses drawIndirect(indirectBuffer, 0)

---

## FLOW-MP-001: Compute → Render → Compute

**Purpose:** Demonstrates complex pipeline where compute generates vertices, render outputs to texture, second compute processes the rendered image.

**Resources:**
- Buffer A (vertices): STORAGE | VERTEX, 256 bytes
- Texture A: RENDER_ATTACHMENT | STORAGE_BINDING, rgba8unorm, 64x64
- Buffer B (output): STORAGE | COPY_SRC, 64 bytes

**Execution Flow:**
1. Create buffer A with STORAGE | VERTEX
2. Create texture A with RENDER_ATTACHMENT | STORAGE_BINDING
3. Create buffer B for final output
4. **Pass 1 (Compute):** Generate vertex data to buffer A
5. **Pass 2 (Render):** Draw to texture A using buffer A as vertex buffer
6. **Pass 3 (Compute):** Read from texture A (as storage texture), compute statistics, write to buffer B

---

## FLOW-MP-002: Deferred Rendering

**Purpose:** Classic deferred shading with G-buffer render, lighting compute, final composite.

**Resources:**
- Texture G-Position: RENDER_ATTACHMENT | TEXTURE_BINDING, rgba16float
- Texture G-Normal: RENDER_ATTACHMENT | TEXTURE_BINDING, rgba16float
- Texture G-Albedo: RENDER_ATTACHMENT | TEXTURE_BINDING, rgba8unorm
- Texture Light: STORAGE_BINDING | TEXTURE_BINDING, rgba8unorm
- Buffer (lights): STORAGE, light data

**Execution Flow:**
1. **Pass 1 (Render):** Output to 3 G-buffer textures simultaneously
   - Fragment shader outputs @location(0) position, @location(1) normal, @location(2) albedo
2. **Pass 2 (Compute):** Sample all 3 G-buffer textures, compute lighting, write to storage texture
3. **Pass 3 (Render):** Full-screen quad sampling light texture for final output

---

## FLOW-MP-003: Shadow Mapping

**Purpose:** Two-pass shadow rendering with depth comparison.

**Resources:**
- Texture A (shadow map): depth24plus, RENDER_ATTACHMENT | TEXTURE_BINDING, 512x512
- Texture B (color output): RENDER_ATTACHMENT

**Execution Flow:**
1. **Pass 1:** Depth-only render from light perspective
   - fragment: { } // no color output
   - Only depth attachment, no color attachments
2. **Pass 2:** Render scene with shadow sampling
   - Sample shadow map with comparison sampler
   - `textureSampleCompare(shadowMap, shadowSampler, coords, depthRef)`

---

## FLOW-MP-004: Bloom Effect (5-Pass)

**Purpose:** Complex post-processing chain with horizontal/vertical blur separation.

**Resources:**
- Texture Scene: RENDER_ATTACHMENT | TEXTURE_BINDING
- Texture Bright: STORAGE_BINDING | TEXTURE_BINDING (bright pass output)
- Texture BlurH: STORAGE_BINDING | TEXTURE_BINDING (horizontal blur)
- Texture BlurV: STORAGE_BINDING | TEXTURE_BINDING (vertical blur)

**Execution Flow:**
1. **Pass 1 (Render):** Render scene to Texture Scene
2. **Pass 2 (Compute):** Threshold bright pixels from Scene → Bright
3. **Pass 3 (Compute):** Horizontal blur Bright → BlurH
4. **Pass 4 (Compute):** Vertical blur BlurH → BlurV
5. **Pass 5 (Render):** Composite Scene + BlurV to canvas

---

## FLOW-MP-005: GPU Particle System

**Purpose:** Particle simulation with compute update and point rendering.

**Resources:**
- Buffer Particles: STORAGE | VERTEX, 16384 bytes (1024 particles × 16 bytes)
  - struct: { position: vec2<f32>, velocity: vec2<f32> }
- Buffer Params: UNIFORM, 16 bytes (time, deltaTime)

**Execution Flow:**
1. **Each Frame:**
   - Update params buffer with time
   - Compute pass: Update particle positions/velocities
   - Render pass: Draw particles as points (topology: "point-list")
2. Single submit per frame

---

## FLOW-MP-007: Ping-Pong Buffer Pattern

**Purpose:** Alternating read/write pattern for iterative simulation.

**Resources:**
- Buffer A: STORAGE, 4096 bytes
- Buffer B: STORAGE, 4096 bytes

**Execution Flow (single submit):**
1. Initialize buffer A with data
2. **Pass 1 (Compute):** Read A, write B
3. **Pass 2 (Compute):** Read B, write A
4. **Pass 3 (Compute):** Read A, write B
5. Result in buffer B

**Key:** Different bind groups for each pass, same pipeline.

---

## FLOW-MP-008: Multiple Command Buffers

**Purpose:** Multiple command buffers in single submit.

**Resources:**
- Various buffers and textures

**Execution Flow:**
1. Create encoder1, record compute pass, finish() → cmdBuf1
2. Create encoder2, record render pass, finish() → cmdBuf2
3. Create encoder3, record copy operations, finish() → cmdBuf3
4. `device.queue.submit([cmdBuf1, cmdBuf2, cmdBuf3])`

---

# CATEGORY 3: Resource Interaction Patterns (HIGH PRIORITY)

## FLOW-BU-001: Buffer as Multiple Roles

**Purpose:** Single buffer used as VERTEX and UNIFORM in different contexts.

**Resources:**
- Buffer A: VERTEX | UNIFORM, 256 bytes

**Execution:**
- Pass 1: setVertexBuffer(0, bufferA)
- Pass 2 (different render pass): setBindGroup with bufferA as uniform binding

**Note:** Cannot use same buffer as both in same pass.

---

## FLOW-BU-002: Dynamic Uniform Buffers

**Purpose:** Single buffer, multiple parameter sets via dynamic offsets.

**Resources:**
- Buffer A: UNIFORM, 1024 bytes (4 × 256-byte aligned regions)

**Bind Group Layout:**
```javascript
{ binding: 0, visibility: FRAGMENT, buffer: { type: "uniform", hasDynamicOffset: true } }
```

**Execution:**
```javascript
setBindGroup(0, bindGroup, [0]);    // offset 0
draw(3);
setBindGroup(0, bindGroup, [256]);  // offset 256
draw(3);
setBindGroup(0, bindGroup, [512]);  // offset 512
draw(3);
```

---

## FLOW-BU-003: Dynamic Storage Buffers

**Purpose:** Similar to BU-002 but for storage buffers.

**Bind Group Layout:**
```javascript
{ binding: 0, visibility: COMPUTE, buffer: { type: "storage", hasDynamicOffset: true } }
```

---

## FLOW-TU-001: Texture Render then Sample

**Purpose:** Same texture as render target, then sampled.

**Resources:**
- Texture A: RENDER_ATTACHMENT | TEXTURE_BINDING

**Execution:**
1. Pass 1: Render to texture A (color attachment)
2. Pass 2: Sample texture A in fragment shader

---

## FLOW-TU-002: Multiple Texture Views

**Purpose:** Different views of same texture for different purposes.

**Resources:**
- Texture A: 256x256, mipLevelCount: 5, depthOrArrayLayers: 4

**Views:**
```javascript
view1 = texture.createView({ baseMipLevel: 0, mipLevelCount: 1 });  // Full res
view2 = texture.createView({ baseMipLevel: 2, mipLevelCount: 1 });  // 64x64
view3 = texture.createView({ baseArrayLayer: 0, arrayLayerCount: 1 }); // Layer 0
view4 = texture.createView({ baseArrayLayer: 2, arrayLayerCount: 2 }); // Layers 2-3
```

---

## FLOW-BG-001: Four Bind Groups

**Purpose:** All 4 bind group slots active simultaneously.

**Shader:**
```wgsl
@group(0) @binding(0) var<uniform> params0: vec4<f32>;
@group(1) @binding(0) var<uniform> params1: vec4<f32>;
@group(2) @binding(0) var tex: texture_2d<f32>;
@group(2) @binding(1) var samp: sampler;
@group(3) @binding(0) var<storage, read_write> output: array<f32>;
```

---

## FLOW-BG-002: Bind Group Swap Mid-Pass

**Purpose:** Change bind group between draws in single pass.

**Execution:**
```javascript
renderPass.setBindGroup(0, bindGroupA);
renderPass.draw(3);
renderPass.setBindGroup(0, bindGroupB);  // Same slot, different group
renderPass.draw(3);
```

---

## FLOW-BG-004: Auto Layout with getBindGroupLayout

**Purpose:** Use pipeline's automatically generated layout.

**Execution:**
```javascript
const pipeline = device.createComputePipeline({
    layout: "auto",
    compute: { module, entryPoint: "main" }
});

const layout = pipeline.getBindGroupLayout(0);  // Get auto-generated layout

const bindGroup = device.createBindGroup({
    layout: layout,
    entries: [...]
});
```

---

## FLOW-BG-005: Mixed Binding Types

**Purpose:** Single bind group with all binding types.

**Layout:**
```javascript
{
    entries: [
        { binding: 0, visibility: FRAGMENT, buffer: { type: "uniform" } },
        { binding: 1, visibility: FRAGMENT, buffer: { type: "storage" } },
        { binding: 2, visibility: FRAGMENT, texture: { sampleType: "float" } },
        { binding: 3, visibility: FRAGMENT, storageTexture: { access: "write-only", format: "rgba8unorm" } },
        { binding: 4, visibility: FRAGMENT, sampler: { type: "filtering" } }
    ]
}
```

---

## FLOW-SP-001: All Filter Mode Combinations

**Purpose:** Samplers with all filter combinations.

**Samplers:**
```javascript
const samplers = [
    { magFilter: "nearest", minFilter: "nearest", mipmapFilter: "nearest" },
    { magFilter: "nearest", minFilter: "nearest", mipmapFilter: "linear" },
    { magFilter: "nearest", minFilter: "linear", mipmapFilter: "nearest" },
    { magFilter: "nearest", minFilter: "linear", mipmapFilter: "linear" },
    { magFilter: "linear", minFilter: "nearest", mipmapFilter: "nearest" },
    { magFilter: "linear", minFilter: "nearest", mipmapFilter: "linear" },
    { magFilter: "linear", minFilter: "linear", mipmapFilter: "nearest" },
    { magFilter: "linear", minFilter: "linear", mipmapFilter: "linear" }  // Trilinear
];
```

---

## FLOW-SP-003: Comparison Sampler

**Purpose:** Shadow map comparison sampling.

**Sampler:**
```javascript
{
    compare: "less",
    magFilter: "linear",
    minFilter: "linear"
}
```

**Shader:**
```wgsl
@group(0) @binding(0) var shadowMap: texture_depth_2d;
@group(0) @binding(1) var shadowSampler: sampler_comparison;

// Usage:
let shadow = textureSampleCompare(shadowMap, shadowSampler, uv, referenceDepth);
```

---

# CATEGORY 5: Render Bundle Patterns

## FLOW-RB-001: Basic Render Bundle

**Execution:**
```javascript
const bundleEncoder = device.createRenderBundleEncoder({
    colorFormats: [format],
    depthStencilFormat: "depth24plus"
});

bundleEncoder.setPipeline(pipeline);
bundleEncoder.setBindGroup(0, bindGroup);
bundleEncoder.setVertexBuffer(0, vertexBuffer);
bundleEncoder.draw(36);

const bundle = bundleEncoder.finish();

// In render pass:
renderPass.executeBundles([bundle]);
```

---

## FLOW-RB-003: Multiple Bundle Execution

**Execution:**
```javascript
// Create three bundles with different content
const bundle1 = createBundle(pipeline1, bindGroup1);
const bundle2 = createBundle(pipeline2, bindGroup2);
const bundle3 = createBundle(pipeline3, bindGroup3);

renderPass.executeBundles([bundle1, bundle2, bundle3]);
```

---

## FLOW-RB-004: Bundle Interleaved with Direct Commands

**Execution:**
```javascript
renderPass.setPipeline(directPipeline);
renderPass.draw(3);  // Direct draw

renderPass.executeBundles([bundle]);  // Bundle execution

renderPass.setPipeline(directPipeline2);
renderPass.draw(6);  // More direct draws
```

---

# CATEGORY 6: Query Operations

## FLOW-QO-001: Occlusion Query

**Execution:**
```javascript
const querySet = device.createQuerySet({
    type: "occlusion",
    count: 4
});

const resolveBuffer = device.createBuffer({
    size: 32,  // 4 queries × 8 bytes each
    usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC
});

// In render pass:
renderPass.beginOcclusionQuery(0);
renderPass.draw(3);
renderPass.endOcclusionQuery();

renderPass.beginOcclusionQuery(1);
renderPass.draw(6);
renderPass.endOcclusionQuery();

// After pass:
encoder.resolveQuerySet(querySet, 0, 4, resolveBuffer, 0);
```

---

# CATEGORY 7: Copy Operations

## FLOW-CO-001: Buffer to Buffer Copy

**Execution:**
```javascript
encoder.copyBufferToBuffer(
    srcBuffer,    // source
    64,           // sourceOffset
    dstBuffer,    // destination  
    128,          // destinationOffset
    256           // size (optional - copies whole buffer if omitted)
);
```

---

## FLOW-CO-002: Buffer to Texture Copy

**Execution:**
```javascript
encoder.copyBufferToTexture(
    {
        buffer: srcBuffer,
        offset: 0,
        bytesPerRow: 256 * 4,  // Must be multiple of 256
        rowsPerImage: 256
    },
    {
        texture: dstTexture,
        mipLevel: 0,
        origin: { x: 0, y: 0, z: 0 },
        aspect: "all"
    },
    { width: 256, height: 256, depthOrArrayLayers: 1 }
);
```

---

## FLOW-CO-003: Texture to Buffer Copy

**Execution:**
```javascript
encoder.copyTextureToBuffer(
    {
        texture: srcTexture,
        mipLevel: 0,
        origin: { x: 0, y: 0, z: 0 }
    },
    {
        buffer: dstBuffer,
        offset: 0,
        bytesPerRow: 256 * 4,
        rowsPerImage: 256
    },
    { width: 256, height: 256, depthOrArrayLayers: 1 }
);
```

---

## FLOW-CO-004: Texture to Texture Copy

**Execution:**
```javascript
encoder.copyTextureToTexture(
    {
        texture: srcTexture,
        mipLevel: 0,
        origin: { x: 0, y: 0, z: 0 }
    },
    {
        texture: dstTexture,
        mipLevel: 0,
        origin: { x: 64, y: 64, z: 0 }
    },
    { width: 128, height: 128, depthOrArrayLayers: 1 }
);
```

---

## FLOW-CO-005: Clear Buffer

**Execution:**
```javascript
encoder.clearBuffer(buffer);  // Clear entire buffer
encoder.clearBuffer(buffer, 128);  // Clear from offset 128 to end
encoder.clearBuffer(buffer, 128, 256);  // Clear 256 bytes starting at offset 128
```

---

# Implementation Checklist

For each flow implementation:

- [ ] All resources created with correct usage flags
- [ ] Bind group layouts match shader bindings exactly
- [ ] Pipeline layouts match bind group layouts
- [ ] Texture formats support required usages
- [ ] Buffer sizes are properly aligned
- [ ] No comments in final output
- [ ] All numbers are literals (not constants)
- [ ] Entry point names vary between tests
- [ ] Labels vary between tests
- [ ] Test passes with `./run_tests.sh`

---

# Next Steps

1. Start with FLOW-CR-001 through FLOW-CR-005 (Compute→Render chains)
2. Implement FLOW-MP-002 (Deferred Rendering) as complex multi-pass example
3. Implement FLOW-BG-001 through FLOW-BG-005 (Bind Group patterns)
4. Continue with remaining categories

Each implementation should be saved to `agent_outputs/` and tested before moving to category directories.




