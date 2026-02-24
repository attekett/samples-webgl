# WebGPU Fuzzing Corpus Plan

## Overview

This document defines a comprehensive corpus structure for mutation-based fuzzing of WebGPU API implementations. The corpus is designed for tools like Radamsa that perform generic mutations on input files.

**Design Principles:**
1. Each test case represents a complete, valid WebGPU execution flow
2. Focus on API interaction complexity rather than parameter variations
3. Maximize "mutation surface" - expose raw API calls with literal values
4. Create diverse resource sharing and state dependency patterns
5. Cover all major execution paths through the API

## Corpus Categories

The corpus is organized into categories based on execution flow patterns:

---

## Category 1: Single-Pass Execution Flows

### 1.1 Compute-Only Flows

#### FLOW-C-001: Basic Compute Dispatch
- Create buffer with STORAGE usage
- Create compute shader module
- Create bind group layout with storage buffer binding
- Create compute pipeline
- Create bind group binding buffer
- Begin compute pass
- Set pipeline, set bind group
- Dispatch workgroups
- End pass, finish encoder, submit

#### FLOW-C-002: Multi-Buffer Compute
- Create 3 buffers: input1 (STORAGE), input2 (STORAGE), output (STORAGE | COPY_SRC)
- Shader reads from two inputs, writes to output
- Bind all three in single bind group
- Dispatch and verify output via map

#### FLOW-C-003: Compute with Uniform Buffer
- Create uniform buffer (UNIFORM | COPY_DST)
- Create storage buffer for output (STORAGE | COPY_SRC)
- Write uniform data via queue.writeBuffer
- Compute shader reads uniforms, writes storage
- Single dispatch

#### FLOW-C-004: Indirect Compute Dispatch
- Create indirect buffer (INDIRECT | COPY_DST)
- Write dispatch parameters to indirect buffer
- Create compute pipeline
- Use dispatchWorkgroupsIndirect

#### FLOW-C-005: Large Workgroup Compute
- Create compute shader with @workgroup_size(256, 1, 1)
- Use workgroup shared memory (var<workgroup>)
- Workgroup barrier synchronization
- Single dispatch with many workgroups

#### FLOW-C-006: 3D Workgroup Grid Compute
- Dispatch with (X, Y, Z) all > 1
- Use global_invocation_id to address 3D data
- Large output buffer representing 3D grid

#### FLOW-C-007: Pipeline Overridable Constants
- Define override constants in shader
- Pass constants dict when creating pipeline
- Different constant values affect output

#### FLOW-C-008: Compute with Read-Only Storage
- Create buffer with STORAGE usage
- Bind as read-only-storage in layout
- Shader reads via storage-read access mode

### 1.2 Render-Only Flows

#### FLOW-R-001: Minimal Triangle Render
- Create vertex buffer with triangle vertices
- Simple vertex/fragment shader
- Single color attachment render pass
- Draw 3 vertices

#### FLOW-R-002: Indexed Triangle Render  
- Create vertex buffer
- Create index buffer (INDEX)
- Set vertex buffer, set index buffer
- drawIndexed call

#### FLOW-R-003: Instanced Rendering
- Vertex buffer with per-vertex data
- Instance buffer with per-instance data
- Vertex shader uses instance_index
- draw with instanceCount > 1

#### FLOW-R-004: Multi-Attachment Render
- Create 4 render target textures
- Render pipeline with 4 color targets
- Fragment shader outputs to 4 locations
- Single render pass, multiple attachments

#### FLOW-R-005: Depth-Stencil Render
- Create depth-stencil texture (depth24plus-stencil8)
- Configure depthStencilAttachment
- Enable depth test and depth write
- Render overlapping geometry

#### FLOW-R-006: Multisampled Render
- Create multisampled texture (sampleCount: 4)
- Create resolve target texture
- Configure MSAA render pass
- Render and resolve

#### FLOW-R-007: Scissor and Viewport
- Begin render pass
- setScissorRect with partial coverage
- setViewport with modified depth range
- Draw primitives

#### FLOW-R-008: Dynamic Blend Constants
- Create pipeline with constant blend factors
- setBlendConstant during render pass
- Multiple draws with different blend constants

#### FLOW-R-009: Stencil Operations
- Create depth-stencil texture
- First pass: write stencil values
- Second pass: test stencil, conditional render
- Use different stencil ops (increment, replace, etc.)

#### FLOW-R-010: Indirect Draw
- Create indirect buffer with draw parameters
- drawIndirect call
- Both regular and indexed variants

#### FLOW-R-011: Point and Line Primitives
- Render with topology: "point-list"
- Render with topology: "line-list"
- Render with topology: "line-strip"

#### FLOW-R-012: Strip Topologies with Restart
- triangle-strip with primitive restart index
- line-strip with primitive restart index
- stripIndexFormat in pipeline

#### FLOW-R-013: Alpha-to-Coverage
- Multisampled render pass
- alphaToCoverageEnabled: true in pipeline
- Fragment outputs alpha values

#### FLOW-R-014: Cull Mode and Front Face
- pipeline with cullMode: "back"
- pipeline with cullMode: "front"
- frontFace: "cw" vs "ccw"

#### FLOW-R-015: Depth Bias
- depthBias, depthBiasSlopeScale, depthBiasClamp
- Render coplanar geometry
- Prevent z-fighting

---

## Category 2: Multi-Pass Execution Flows

### 2.1 Compute → Render Chains

#### FLOW-CR-001: Compute Generates Vertex Data
- Compute pass writes vertex positions to buffer (STORAGE | VERTEX)
- Render pass uses same buffer as vertex buffer
- Dynamic geometry generation

#### FLOW-CR-002: Compute Generates Instance Data
- Compute pass calculates instance transforms
- Buffer: STORAGE | VERTEX
- Render pass instanced draw with computed data

#### FLOW-CR-003: Compute Updates Uniforms
- Compute pass writes to buffer (STORAGE | UNIFORM)
- Render pass binds same buffer as uniform
- Animation/simulation pattern

#### FLOW-CR-004: Compute Generates Index Data
- Compute pass writes indices to buffer (STORAGE | INDEX)
- Render pass uses computed index buffer
- Dynamic mesh connectivity

#### FLOW-CR-005: Compute Indirect Parameters
- Compute pass writes to buffer (STORAGE | INDIRECT)
- Render pass uses drawIndirect
- GPU-driven rendering

### 2.2 Render → Copy Chains

#### FLOW-RC-001: Render then Readback
- Render to texture (RENDER_ATTACHMENT | COPY_SRC)
- copyTextureToBuffer to staging buffer
- mapAsync and verify pixels

#### FLOW-RC-002: Render to Texture then Sample
- Render to texture A (RENDER_ATTACHMENT | TEXTURE_BINDING)
- Second render pass samples texture A
- Offscreen rendering pattern

#### FLOW-RC-003: Mipmap Generation
- Render to mip level 0
- Blit/render to subsequent mip levels
- Create texture views per mip level

#### FLOW-RC-004: Render then Copy Texture-to-Texture
- Render to texture A
- copyTextureToTexture to texture B
- Use texture B in subsequent pass

### 2.3 Compute → Copy Chains

#### FLOW-CC-001: Compute Output Readback
- Compute writes to storage buffer (STORAGE | COPY_SRC)
- copyBufferToBuffer to mapped staging buffer
- mapAsync to read results

#### FLOW-CC-002: Compute Writes Storage Texture
- Create storage texture (STORAGE_BINDING | COPY_SRC)
- Compute shader writes via textureStore
- Copy texture to buffer for verification

#### FLOW-CC-003: Multi-Stage Compute
- Compute pass A writes buffer
- Compute pass B reads buffer, writes different buffer
- Chain of compute operations

### 2.4 Complex Multi-Pass

#### FLOW-MP-001: Compute → Render → Compute
- Compute generates vertices
- Render to texture
- Second compute reads from rendered texture (via storage texture)

#### FLOW-MP-002: Deferred Rendering
- Pass 1: Render G-buffer (position, normal, albedo)
- Pass 2: Lighting compute using G-buffer textures
- Pass 3: Final composite render

#### FLOW-MP-003: Shadow Mapping
- Pass 1: Render depth-only from light view
- Pass 2: Render scene sampling depth texture
- Depth comparison sampling

#### FLOW-MP-004: Bloom Effect
- Pass 1: Render scene
- Pass 2: Compute bright pass threshold
- Pass 3: Compute horizontal blur
- Pass 4: Compute vertical blur
- Pass 5: Composite render

#### FLOW-MP-005: GPU Particle System
- Compute: Update particle positions
- Compute: Sort/bin particles (optional)
- Render: Draw particles as points/quads

#### FLOW-MP-006: Procedural Terrain
- Compute: Generate heightmap
- Compute: Generate normal map
- Render: Draw terrain mesh sampling both

#### FLOW-MP-007: Ping-Pong Buffer Pattern
- Two storage buffers A and B
- Alternating: Compute reads A → writes B, then reads B → writes A
- Multi-frame simulation pattern

#### FLOW-MP-008: Command Buffer Sequence
- Create multiple command buffers
- Each contains different passes
- Submit all in single submit() call

---

## Category 3: Resource Interaction Patterns

### 3.1 Buffer Usage Combinations

#### FLOW-BU-001: Buffer as Multiple Roles
- Single buffer with VERTEX | UNIFORM usage
- Use as vertex buffer in one pass
- Use as uniform buffer in different bind group (different pass)

#### FLOW-BU-002: Dynamic Uniform Buffers
- Buffer with hasDynamicOffset: true
- Single bind group, multiple setBindGroup calls with different offsets
- Efficient parameter variation

#### FLOW-BU-003: Dynamic Storage Buffers
- Storage buffer with hasDynamicOffset: true
- Multiple dispatches accessing different regions

#### FLOW-BU-004: Buffer Mapping Lifecycle
- Create buffer with MAP_READ
- Use in GPU operation (COPY_DST | MAP_READ)
- copyBufferToBuffer to it
- mapAsync after GPU operation completes

#### FLOW-BU-005: Write-Map-Write Pattern
- Create mapped buffer (mappedAtCreation: true)
- Write initial data
- Unmap
- GPU operations
- writeBuffer to update

### 3.2 Texture Usage Combinations

#### FLOW-TU-001: Texture as Render Target then Sample
- Single texture with RENDER_ATTACHMENT | TEXTURE_BINDING
- Render pass uses as color attachment
- Next render pass samples texture

#### FLOW-TU-002: Texture with Multiple Views
- Create texture
- Create multiple GPUTextureViews with different:
  - baseMipLevel
  - mipLevelCount
  - baseArrayLayer
  - arrayLayerCount
- Use different views in different passes

#### FLOW-TU-003: Storage Texture Write then Sample
- Texture with STORAGE_BINDING | TEXTURE_BINDING
- Compute pass writes via textureStore
- Render pass samples via textureSample

#### FLOW-TU-004: Texture Copy Operations
- Texture with COPY_SRC | COPY_DST
- copyTextureToTexture between textures
- copyBufferToTexture / copyTextureToBuffer

#### FLOW-TU-005: Mip Level Access Patterns
- Create texture with mipLevelCount > 1
- Views targeting specific mip levels
- Render to mip 0, sample from mip 0 for mip 1, etc.

#### FLOW-TU-006: Array Layer Access Patterns
- 2D array texture (dimension: "2d", depthOrArrayLayers > 1)
- Views of individual layers
- Cube map pattern (6 array layers)

#### FLOW-TU-007: 3D Texture Operations
- dimension: "3d" texture
- Compute writes to 3D storage texture
- Render samples 3D texture

#### FLOW-TU-008: Depth Texture Sampling
- depth24plus texture used as depth attachment
- Create texture view for sampling
- Fragment shader samples depth for effects

### 3.3 Bind Group Patterns

#### FLOW-BG-001: Multiple Bind Groups
- 4 bind groups (groups 0-3)
- Different resource types per group
- All bound during single dispatch/draw

#### FLOW-BG-002: Bind Group Update Mid-Pass
- Single render pass
- Draw with bind group A
- setBindGroup to bind group B
- Draw again with different resources

#### FLOW-BG-003: Shared Bind Group Layout
- Create explicit GPUBindGroupLayout
- Create multiple GPUBindGroups with same layout
- Swap bind groups during execution

#### FLOW-BG-004: Auto Layout Pipeline
- Create pipeline with layout: "auto"
- Use getBindGroupLayout() to get derived layouts
- Create bind groups from auto layouts

#### FLOW-BG-005: Mixed Binding Types
- Single bind group containing:
  - Uniform buffer
  - Storage buffer
  - Sampled texture
  - Storage texture
  - Sampler

### 3.4 Sampler Patterns

#### FLOW-SP-001: All Filter Modes
- Samplers with different magFilter, minFilter, mipmapFilter combinations
- nearest, linear for each
- Compare visual output

#### FLOW-SP-002: Address Modes
- Samplers with different addressModeU/V/W
- clamp-to-edge, repeat, mirror-repeat
- Texture coordinates outside [0,1]

#### FLOW-SP-003: Comparison Sampler
- Sampler with compare function
- Shadow mapping pattern
- textureSampleCompare in shader

#### FLOW-SP-004: Anisotropic Filtering
- maxAnisotropy > 1
- Grazing angle texture sampling

#### FLOW-SP-005: LOD Control
- lodMinClamp, lodMaxClamp
- Force specific mip level usage

---

## Category 4: State and Configuration Variations

### 4.1 Pipeline State Variations

#### FLOW-PS-001: Primitive Topologies
- triangle-list (default)
- triangle-strip
- line-list
- line-strip
- point-list

#### FLOW-PS-002: Blend Modes Matrix
- Pipelines with different blend configurations
- All blend factors: zero, one, src, dst, etc.
- All blend operations: add, subtract, min, max

#### FLOW-PS-003: Depth Compare Functions
- All GPUCompareFunction values:
- never, less, equal, less-equal, greater, not-equal, greater-equal, always

#### FLOW-PS-004: Stencil State Matrix
- All stencil operations: keep, zero, replace, invert, increment-*, decrement-*
- Different front/back stencil states
- stencilReadMask, stencilWriteMask variations

#### FLOW-PS-005: Color Write Masks
- writeMask with different combinations
- Selective channel writes (RED | GREEN but not BLUE | ALPHA)

#### FLOW-PS-006: Vertex Attribute Formats
- All GPUVertexFormat values in vertex buffers
- uint8x2, uint8x4, sint8x2, sint8x4
- uint16x2, uint16x4, sint16x2, sint16x4
- unorm8x2, unorm8x4, snorm8x2, snorm8x4
- float16x2, float16x4
- float32, float32x2, float32x3, float32x4
- uint32, uint32x2, uint32x3, uint32x4
- sint32, sint32x2, sint32x3, sint32x4
- unorm10-10-10-2

### 4.2 Render Pass Configurations

#### FLOW-RP-001: Load/Store Operations
- loadOp: "clear" vs "load"
- storeOp: "store" vs "discard"
- Different combinations per attachment

#### FLOW-RP-002: Clear Values
- Different clearValue colors
- Different depthClearValue
- Different stencilClearValue

#### FLOW-RP-003: Read-Only Depth/Stencil
- depthReadOnly: true
- stencilReadOnly: true
- Sample depth while using for depth test

#### FLOW-RP-004: Resolve Targets
- Multisampled render with resolveTarget
- Different resolve target formats

#### FLOW-RP-005: Depth Slice Rendering
- Render to specific slice of 3D texture
- depthSlice in color attachment

### 4.3 Texture Format Coverage

#### FLOW-TF-001: Color Formats
- All plain color formats as render targets
- r8unorm, rg8unorm, rgba8unorm, etc.
- 16-bit and 32-bit formats

#### FLOW-TF-002: sRGB Formats
- rgba8unorm-srgb, bgra8unorm-srgb
- Correct gamma handling

#### FLOW-TF-003: Float Formats
- r16float, rg16float, rgba16float
- r32float, rg32float, rgba32float
- HDR rendering patterns

#### FLOW-TF-004: Integer Formats
- r8uint, rg8uint, rgba8uint
- r16uint, rg16uint, rgba16uint
- r32uint, rg32uint, rgba32uint
- Corresponding sint variants

#### FLOW-TF-005: Depth/Stencil Formats
- depth16unorm
- depth24plus
- depth24plus-stencil8
- depth32float
- depth32float-stencil8 (if supported)
- stencil8

#### FLOW-TF-006: View Format Compatibility
- Create texture with viewFormats array
- Create views with compatible formats
- srgb/non-srgb pairs

---

## Category 5: Render Bundle Patterns

#### FLOW-RB-001: Basic Render Bundle
- Create GPURenderBundleEncoder
- Encode draw commands
- finish() to get GPURenderBundle
- executeBundles() in render pass

#### FLOW-RB-002: Bundle with Bind Groups
- Encode setBindGroup in bundle
- Use bundle with bound resources

#### FLOW-RB-003: Multiple Bundle Execution
- Create multiple render bundles
- Execute all bundles in single render pass
- executeBundles([bundle1, bundle2, bundle3])

#### FLOW-RB-004: Bundle Interleaved with Direct
- Render pass with:
  - Direct draw commands
  - executeBundles()
  - More direct draw commands

#### FLOW-RB-005: Bundle Reuse
- Single render bundle
- Execute in multiple different render passes
- Reuse optimization pattern

#### FLOW-RB-006: Read-Only Depth Bundle
- Bundle created with depthReadOnly: true
- Execute in render pass with read-only depth

---

## Category 6: Query Operations

#### FLOW-QO-001: Occlusion Query
- Create QuerySet with type: "occlusion"
- beginOcclusionQuery / endOcclusionQuery
- resolveQuerySet to buffer
- Read occlusion results

#### FLOW-QO-002: Timestamp Query (Feature-Gated)
- Requires "timestamp-query" feature
- timestampWrites in pass descriptor
- beginningOfPassWriteIndex, endOfPassWriteIndex
- Measure pass execution time

#### FLOW-QO-003: Multiple Queries
- QuerySet with count > 1
- Multiple occlusion query sections
- Resolve all queries

---

## Category 7: Copy Operations

#### FLOW-CO-001: Buffer to Buffer Copy
- copyBufferToBuffer
- Full buffer copy
- Partial copy with offsets

#### FLOW-CO-002: Buffer to Texture Copy
- copyBufferToTexture
- Proper bytesPerRow, rowsPerImage alignment
- Multiple mip levels

#### FLOW-CO-003: Texture to Buffer Copy
- copyTextureToBuffer
- Read back rendered content
- Specific mip level copy

#### FLOW-CO-004: Texture to Texture Copy
- copyTextureToTexture
- Same format textures
- Different mip levels

#### FLOW-CO-005: Clear Buffer
- clearBuffer
- Full clear
- Partial clear with offset/size

#### FLOW-CO-006: External Image Copy
- copyExternalImageToTexture
- From ImageBitmap source
- From canvas source

---

## Category 8: Canvas and Presentation

#### FLOW-CV-001: Basic Canvas Present
- Configure canvas context
- Render to getCurrentTexture()
- Automatic presentation

#### FLOW-CV-002: Canvas Resize Handling
- Change canvas width/height
- Reconfigure or recreate context
- Handle texture size changes

#### FLOW-CV-003: Canvas Alpha Modes
- alphaMode: "opaque"
- alphaMode: "premultiplied"
- Different compositing behavior

#### FLOW-CV-004: Canvas View Formats
- Configure with viewFormats for sRGB views
- Create sRGB view of canvas texture

#### FLOW-CV-005: Multi-Canvas
- Multiple canvas elements
- Different device configurations
- Concurrent rendering

---

## Category 9: Error and Edge Case Patterns

### 9.1 Resource Lifecycle Patterns

#### FLOW-LC-001: Buffer Destroy Mid-Frame
- Create buffer
- Use in command
- Destroy buffer
- Finish and submit (should error)

#### FLOW-LC-002: Texture Destroy and Recreate
- Create and use texture
- Destroy texture
- Create new texture with same parameters
- Use new texture

#### FLOW-LC-003: Device Destroy Handling
- Normal operation sequence
- device.destroy() call
- Subsequent operations should fail

### 9.2 Validation Boundary Patterns

#### FLOW-VB-001: Zero-Size Operations
- Draw with vertexCount: 0
- Dispatch with (0, 1, 1)
- Copy with size 0

#### FLOW-VB-002: Maximum Limits
- Buffers at maxBufferSize
- Textures at maxTextureDimension2D
- Workgroup counts at maxComputeWorkgroupsPerDimension

#### FLOW-VB-003: Alignment Boundaries
- Buffer offsets at alignment boundaries
- Texture copy alignments

---

## Category 10: Async Pipeline Creation

#### FLOW-AP-001: createComputePipelineAsync
- Use async version
- Await result before use
- No race conditions

#### FLOW-AP-002: createRenderPipelineAsync
- Async render pipeline
- Proper sequencing with render commands

#### FLOW-AP-003: Concurrent Pipeline Creation
- Multiple async pipeline creations
- Promise.all pattern
- Verify all complete

---

## Category 11: Debug and Diagnostic

#### FLOW-DB-001: Debug Groups
- pushDebugGroup / popDebugGroup
- Nested debug groups
- Debug markers

#### FLOW-DB-002: Error Scopes
- pushErrorScope("validation")
- pushErrorScope("out-of-memory")
- popErrorScope and check errors

#### FLOW-DB-003: Object Labels
- Set label on buffers, textures, pipelines
- Labels in error messages

---

## Category 12: Advanced Shader Patterns

### 12.1 WGSL Feature Coverage

#### FLOW-WS-001: All Built-in Types
- Scalars: f32, i32, u32, bool
- Vectors: vec2/3/4<T>
- Matrices: mat2x2, mat3x3, mat4x4, non-square
- Arrays, structs

#### FLOW-WS-002: Texture Sampling Functions
- textureSample, textureSampleBias
- textureSampleLevel, textureSampleGrad
- textureSampleCompare, textureSampleCompareLevel
- textureLoad, textureStore
- textureGather, textureGatherCompare

#### FLOW-WS-003: Storage Buffer Access Patterns
- arrayLength() for runtime-sized arrays
- Atomic operations: atomicLoad, atomicStore, atomicAdd, etc.

#### FLOW-WS-004: Derivative Functions (Fragment)
- dpdx, dpdy, dpdxCoarse, dpdyCoarse
- dpdxFine, dpdyFine
- fwidth

#### FLOW-WS-005: Control Flow Variations
- if/else branching
- switch statements
- for/while loops
- break, continue, return

---

## Implementation Notes for LLM

### File Structure
Each test case should be a single HTML file following the boilerplate in `NEW_LLM_INSTRUCTIONS.md`.

### Naming Convention
```
category_subcategory_flowid.html
```
Example: `compute_basic_c001.html`, `multipass_deferred_mp002.html`

### Mutation Optimization
- Use literal numbers instead of variables where possible
- Avoid helper functions - inline all API calls
- Include varied numeric constants (different sizes, offsets, counts)
- Vary string values (labels, entry point names)

### Required Elements
- No comments in final output
- No error checking/try-catch (let crashes happen)
- All features should work without optional feature flags unless specified
- 256x256 canvas unless specific test needs otherwise

### Priority Order for Implementation
1. Category 2 (Multi-Pass) - highest API interaction
2. Category 3 (Resource Interaction) - complex resource patterns
3. Category 1.2 (Render Flows) - comprehensive render coverage
4. Category 1.1 (Compute Flows) - comprehensive compute coverage
5. Category 5 (Render Bundles) - important for reuse patterns
6. Categories 4, 6, 7 - state/configuration coverage
7. Remaining categories

---

## Continuation Notes

This document defines the structure. Implementation should proceed by:

1. Selecting flows from priority categories
2. Implementing each as standalone HTML file
3. Testing with `run_tests.sh`
4. Moving working tests to appropriate category directories
5. Tracking completed flows in a separate progress document

For maximum fuzzing value, prioritize flows that:
- Combine multiple pipeline types (compute + render)
- Share resources across passes
- Use diverse bind group configurations
- Exercise different command encoder methods
- Include varied numeric parameters for mutation




