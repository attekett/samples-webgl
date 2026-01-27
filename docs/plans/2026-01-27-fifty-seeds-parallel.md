# 50 Mutation-Optimized WebGL Seeds - Parallel Implementation Plan

> **For Claude:** This plan uses parallel subagent execution. Each batch agent creates seeds WITHOUT testing to avoid browser conflicts. Testing happens after all creation is complete.

**Goal:** Create 50 diverse mutation-optimized WebGL2 seed files covering comprehensive feature combinations

**Architecture:** Split into 10 batches of 5 seeds each. Each batch handled by one subagent. Two-phase execution: (1) Parallel creation, (2) Sequential testing

**Coordination Strategy:**
- **Phase 1 (Parallel)**: All 10 agents create seeds simultaneously (no browser conflicts)
- **Phase 2 (Sequential)**: Single validation pass after all seeds created
- **File naming**: `mutation_batch{N}_seed{M}_*.html` to avoid conflicts

**Tech Stack:** WebGL2, GLSL ES 3.00, HTML5

---

## Feature Coverage Matrix (50 Seeds)

### Category 1: Rendering Pipeline (10 seeds)
1. MRT + Float Textures + Blending
2. MRT + Integer Textures + Layered Rendering
3. Depth Textures + Shadow Mapping + PCF
4. Stencil Operations + Two-Sided Stencil
5. Scissor Test + Viewport Arrays
6. Alpha-to-Coverage + Multisample
7. Sample Shading + Min Sample Shading
8. Color Masking + Draw Buffers
9. Framebuffer Blit + Multisample Resolve
10. Pixel Pack/Unpack + ReadPixels

### Category 2: Buffer Operations (10 seeds)
11. UBO + Multiple Binding Points
12. UBO + Dynamic Offsets + Range Binding
13. Transform Feedback + Interleaved Attribs
14. Transform Feedback + Separate Attribs + Pause/Resume
15. Copy Buffer + SubData Patterns
16. Buffer Orphaning + Map/Unmap
17. Vertex Array Objects + Multiple VAOs
18. Index Buffer + Primitive Restart
19. Indirect Drawing + Multi-Draw Indirect
20. Pixel Buffer Objects + Async Transfers

### Category 3: Texture Operations (10 seeds)
21. 3D Textures + Volume Rendering
22. 2D Texture Arrays + Layer Selection
23. Cubemap Arrays + Seamless Filtering
24. Texture Swizzling + Format Reinterpretation
25. Compressed Textures + Mipmap Generation
26. Texture Storage + Immutable Textures
27. Integer Textures + Atomic Operations
28. Sampler Objects + Comparison Mode
29. Texture Subimage + TexStorage3D
30. Texture Views + Base/Max Level

### Category 4: Shader Features (10 seeds)
31. Uniform Buffer Arrays + Dynamic Indexing
32. Texture Arrays + Dynamic Indexing
33. Integer Vertex Attributes + Normalization
34. Flat/Smooth Interpolation + Centroid
35. Derivative Functions + Explicit LOD
36. Bitfield Operations + Integer Math
37. Built-in Variables + gl_VertexID/InstanceID
38. Multiple Shader Stages + Complex Varyings
39. Precision Qualifiers + Mixed Precision
40. Preprocessor + Macro Expansion

### Category 5: Advanced Features (10 seeds)
41. Sync Objects + Client Wait
42. Sync Objects + Server Wait + Fences
43. Query Objects + Occlusion Queries
44. Query Objects + Transform Feedback Queries
45. Instanced Rendering + Divisors
46. Instanced Rendering + Base Instance
47. Primitive Restart + Index Ranges
48. Provoking Vertex + Flat Shading
49. Rasterizer Discard + TF Only
50. Context State + Multiple Contexts

---

## Batch Assignments

### Batch 1 (Seeds 1-5): MRT and Blending
- Agent creates 5 seeds from Category 1 (seeds 1-5)
- Focus: Multiple render targets, float/integer textures, depth operations

### Batch 2 (Seeds 6-10): Advanced Rendering
- Agent creates 5 seeds from Category 1 (seeds 6-10)
- Focus: Multisampling, pixel operations, framebuffer operations

### Batch 3 (Seeds 11-15): Buffer Management
- Agent creates 5 seeds from Category 2 (seeds 11-15)
- Focus: UBO operations, transform feedback

### Batch 4 (Seeds 16-20): Buffer Advanced
- Agent creates 5 seeds from Category 2 (seeds 16-20)
- Focus: Buffer mapping, VAO operations, indirect drawing

### Batch 5 (Seeds 21-25): Texture Types
- Agent creates 5 seeds from Category 3 (seeds 21-25)
- Focus: 3D textures, arrays, cubemaps, compression

### Batch 6 (Seeds 26-30): Texture Operations
- Agent creates 5 seeds from Category 3 (seeds 26-30)
- Focus: Storage, samplers, views, integer textures

### Batch 7 (Seeds 31-35): Shader Variables
- Agent creates 5 seeds from Category 4 (seeds 31-35)
- Focus: Dynamic indexing, interpolation, derivatives

### Batch 8 (Seeds 36-40): Shader Advanced
- Agent creates 5 seeds from Category 4 (seeds 36-40)
- Focus: Integer math, built-ins, precision

### Batch 9 (Seeds 41-45): Synchronization
- Agent creates 5 seeds from Category 5 (seeds 41-45)
- Focus: Sync objects, queries, instancing

### Batch 10 (Seeds 46-50): Advanced Pipeline
- Agent creates 5 seeds from Category 5 (seeds 46-50)
- Focus: Instancing, primitive restart, rasterizer control

---

## Detailed Seed Specifications

### Batch 1: Seeds 1-5

**Seed 1: MRT + Float Textures + Blending**
- File: `agent_outputs/mutation_b1_s1_mrt_float_blend.html`
- Extensions: `['EXT_color_buffer_float']`
- Amplification vars: `texSize`, `mrtCount`, `bufferSize`, `vertexCount`, `blendFactors`
- Enum vars: `textureTarget`, `textureFormat`, `bufferTarget`, `blendMode`
- Patterns: FBO attachment swapping (4 MRTs), float texture creation redundancy, blend mode thrashing
- Blocks: 8 (buffer, 4 float textures, shader, FBO+MRT, blend state, draw calls)

**Seed 2: MRT + Integer Textures + Layered Rendering**
- File: `agent_outputs/mutation_b1_s2_mrt_integer_layered.html`
- Extensions: `[]`
- Amplification vars: `texSize`, `layerCount`, `mrtCount`, `bufferSize`, `vertexCount`
- Enum vars: `textureTarget`, `intFormat`, `bufferTarget`
- Patterns: Integer texture creation redundancy, layer selection in shader, MRT with mixed formats
- Blocks: 9 (buffer, integer textures, shader with flat varyings, FBO+layers, draw to layers)

**Seed 3: Depth Textures + Shadow Mapping + PCF**
- File: `agent_outputs/mutation_b1_s3_depth_shadow_pcf.html`
- Extensions: `[]`
- Amplification vars: `shadowSize`, `texSize`, `kernelSize`, `vertexCount`, `pcfSamples`
- Enum vars: `depthFormat`, `compareMode`, `textureTarget`, `bufferTarget`
- Patterns: Depth texture bind ping-pong, comparison mode thrashing, multi-pass shadow
- Blocks: 10 (geometry buffer, depth texture, shadow texture, shadow shader, main shader, 2 FBOs, shadow pass, main pass, cleanup)

**Seed 4: Stencil Operations + Two-Sided Stencil**
- File: `agent_outputs/mutation_b1_s4_stencil_twosided.html`
- Extensions: `[]`
- Amplification vars: `stencilRef`, `stencilMask`, `vertexCount`, `passCount`
- Enum vars: `stencilOp`, `stencilFunc`, `bufferTarget`, `cullMode`
- Patterns: Stencil op thrashing, front/back face switching, stencil mask mutations
- Blocks: 8 (buffer, shader, stencil state thrashing, cull mode switching, multi-pass stencil, draw calls)

**Seed 5: Scissor Test + Viewport Arrays**
- File: `agent_outputs/mutation_b1_s5_scissor_viewport.html`
- Extensions: `[]`
- Amplification vars: `viewportCount`, `scissorSize`, `tileSize`, `vertexCount`
- Enum vars: `bufferTarget`, `bufferUsage`
- Patterns: Scissor rect mutations, viewport switching, tiled rendering
- Blocks: 7 (buffer, shader, viewport state thrashing, scissor mutations, multi-pass tiled, draw calls)

### Batch 2: Seeds 6-10

**Seed 6: Alpha-to-Coverage + Multisample**
- File: `agent_outputs/mutation_b2_s6_alpha_coverage_ms.html`
- Extensions: `[]`
- Amplification vars: `sampleCount`, `texSize`, `vertexCount`, `alphaThreshold`
- Enum vars: `msTarget`, `resolveMode`, `bufferTarget`
- Patterns: Multisample FBO switching, resolve operations, alpha coverage enable/disable thrashing
- Blocks: 9 (buffer, MS texture, resolve texture, shader with alpha, MS FBO, resolve FBO, render MS, resolve, draw)

**Seed 7: Sample Shading + Min Sample Shading**
- File: `agent_outputs/mutation_b2_s7_sample_shading_min.html`
- Extensions: `['OES_sample_variables']` (check availability)
- Amplification vars: `sampleCount`, `minSampleFraction`, `texSize`, `vertexCount`
- Enum vars: `bufferTarget`, `textureTarget`
- Patterns: Sample shading enable/disable, min sample shading mutations
- Blocks: 8 (buffer, MS texture, shader with sample shading, FBO, sample state, draw calls)

**Seed 8: Color Masking + Draw Buffers**
- File: `agent_outputs/mutation_b2_s8_colormask_drawbuffers.html`
- Extensions: `[]`
- Amplification vars: `mrtCount`, `texSize`, `vertexCount`, `maskPattern`
- Enum vars: `bufferTarget`, `textureFormat`
- Patterns: Color mask thrashing per draw buffer, draw buffer selection mutations
- Blocks: 9 (buffer, 4 textures, shader with MRT, FBO, color mask per buffer, draw buffer switching, draw calls)

**Seed 9: Framebuffer Blit + Multisample Resolve**
- File: `agent_outputs/mutation_b2_s9_fbo_blit_resolve.html`
- Extensions: `[]`
- Amplification vars: `srcSize`, `dstSize`, `sampleCount`, `blitRegion`
- Enum vars: `blitFilter`, `bufferTarget`, `textureTarget`
- Patterns: Blit operation redundancy, filter mode mutations, MS resolve with blit
- Blocks: 10 (buffer, MS texture, resolve texture, src FBO, dst FBO, render to MS, blit operations, resolve, read back)

**Seed 10: Pixel Pack/Unpack + ReadPixels**
- File: `agent_outputs/mutation_b2_s10_pixel_pack_read.html`
- Extensions: `[]`
- Amplification vars: `texSize`, `packAlignment`, `rowLength`, `skipPixels`
- Enum vars: `packFormat`, `packType`, `bufferTarget`
- Patterns: Pack/unpack parameter mutations, PBO bind ping-pong, async readpixels
- Blocks: 9 (render target, PBO creation, render, pack parameter mutations, readpixels to PBO, unpack mutations, bind thrashing)

### Batch 3: Seeds 11-15

**Seed 11: UBO + Multiple Binding Points**
- File: `agent_outputs/mutation_b3_s11_ubo_multipoint.html`
- Extensions: `[]`
- Amplification vars: `uboCount`, `bindingPoints`, `uboSize`, `vertexCount`
- Enum vars: `uboTarget`, `bufferUsage`, `bufferTarget`
- Patterns: UBO binding point thrashing, multiple UBOs per shader, binding redundancy
- Blocks: 10 (3 UBOs, shader with multiple blocks, binding point mutations, buffer updates, draw calls)

**Seed 12: UBO + Dynamic Offsets + Range Binding**
- File: `agent_outputs/mutation_b3_s12_ubo_offsets_range.html`
- Extensions: `[]`
- Amplification vars: `offsetCount`, `rangeSize`, `uboSize`, `alignment`
- Enum vars: `uboTarget`, `bufferUsage`
- Patterns: Offset mutations, range binding with overlaps, alignment violations
- Blocks: 9 (large UBO, shader, offset array mutations, range binding patterns, draw calls with different offsets)

**Seed 13: Transform Feedback + Interleaved Attribs**
- File: `agent_outputs/mutation_b3_s13_tf_interleaved.html`
- Extensions: `[]`
- Amplification vars: `vertexCount`, `tfBufferSize`, `varyingCount`, `primitiveCount`
- Enum vars: `tfTarget`, `tfMode`, `bufferTarget`, `bufferUsage`
- Patterns: TF buffer bind ping-pong, begin/end thrashing, interleaved layout mutations
- Blocks: 10 (input buffer, TF buffer, shader with varyings, TF object, begin/end patterns, draw with TF, pause/resume, read TF results)

**Seed 14: Transform Feedback + Separate Attribs + Pause/Resume**
- File: `agent_outputs/mutation_b3_s14_tf_separate_pause.html`
- Extensions: `[]`
- Amplification vars: `varyingCount`, `bufferCount`, `vertexCount`, `pausePoints`
- Enum vars: `tfMode`, `bufferTarget`, `bufferUsage`
- Patterns: Separate buffer creation redundancy, pause/resume at varying points, buffer switching
- Blocks: 12 (input, 3 TF buffers, shader, TF setup, draw with pause, resume, multiple passes, read results)

**Seed 15: Copy Buffer + SubData Patterns**
- File: `agent_outputs/mutation_b3_s15_copy_buffer_subdata.html`
- Extensions: `[]`
- Amplification vars: `bufferSize`, `copySize`, `copyOffset`, `subDataCount`
- Enum vars: `srcTarget`, `dstTarget`, `bufferUsage`
- Patterns: Copy buffer with overlapping regions, subData redundancy, target rebinding
- Blocks: 9 (2 source buffers, 2 dest buffers, copy operations, subData patterns, bind thrashing, draw using copied data)

### Batch 4: Seeds 16-20

**Seed 16: Buffer Orphaning + Map/Unmap**
- File: `agent_outputs/mutation_b4_s16_orphan_map.html`
- Extensions: `[]`
- Amplification vars: `bufferSize`, `mapSize`, `orphanCount`, `vertexCount`
- Enum vars: `mapAccess`, `mapFlags`, `bufferTarget`, `bufferUsage`
- Patterns: Orphaning via bufferData(null), map/unmap thrashing, access flag mutations
- Blocks: 10 (buffer creation, orphan patterns, map operations, write to mapped, unmap, rebind, draw, remap)

**Seed 17: Vertex Array Objects + Multiple VAOs**
- File: `agent_outputs/mutation_b4_s17_vao_multiple.html`
- Extensions: `[]`
- Amplification vars: `vaoCount`, `attributeCount`, `bufferCount`, `vertexCount`
- Enum vars: `bufferTarget`, `bufferUsage`
- Patterns: VAO bind ping-pong, attribute setup redundancy, VAO state isolation
- Blocks: 11 (3 VAOs, multiple buffers, shader, per-VAO attribute setup, VAO switching, draw calls per VAO)

**Seed 18: Index Buffer + Primitive Restart**
- File: `agent_outputs/mutation_b4_s18_index_primrestart.html`
- Extensions: `[]`
- Amplification vars: `indexCount`, `restartIndex`, `vertexCount`, `primitiveCount`
- Enum vars: `indexType`, `bufferTarget`, `bufferUsage`
- Patterns: Primitive restart enable/disable, restart index mutations, index buffer rebinding
- Blocks: 9 (vertex buffer, index buffer with restart indices, shader, restart state thrashing, draw elements, index mutations)

**Seed 19: Indirect Drawing + Multi-Draw Indirect**
- File: `agent_outputs/mutation_b4_s19_indirect_multidraw.html`
- Extensions: `[]`
- Amplification vars: `drawCount`, `indirectStride`, `vertexCount`, `instanceCount`
- Enum vars: `indirectTarget`, `bufferUsage`, `bufferTarget`
- Patterns: Indirect buffer mutations, multi-draw with varying params, stride violations
- Blocks: 10 (vertex buffer, indirect command buffer, shader, command buffer mutations, multi-draw indirect calls, stride changes)

**Seed 20: Pixel Buffer Objects + Async Transfers**
- File: `agent_outputs/mutation_b4_s20_pbo_async.html`
- Extensions: `[]`
- Amplification vars: `texSize`, `pboCount`, `transferSize`
- Enum vars: `pboTarget`, `textureTarget`, `bufferUsage`
- Patterns: PBO bind ping-pong, async texture upload, readpixels to PBO, buffer chain
- Blocks: 11 (texture, 2 PBOs, render to texture, readpixels to PBO1, upload from PBO2, bind thrashing, async chain)

### Batch 5: Seeds 21-25

**Seed 21: 3D Textures + Volume Rendering**
- File: `agent_outputs/mutation_b5_s21_3dtex_volume.html`
- Extensions: `[]`
- Amplification vars: `texDepth`, `texSize`, `sliceCount`, `vertexCount`
- Enum vars: `tex3DTarget`, `textureFormat`, `wrapMode`
- Patterns: 3D texture dimension mutations, slice-by-slice rendering, depth coordinate variations
- Blocks: 9 (3D texture creation, slice textures, shader with 3D sampling, FBOs per slice, volume render loop)

**Seed 22: 2D Texture Arrays + Layer Selection**
- File: `agent_outputs/mutation_b5_s22_texarray_layers.html`
- Extensions: `[]`
- Amplification vars: `layerCount`, `texSize`, `vertexCount`, `mipLevels`
- Enum vars: `arrayTarget`, `textureFormat`
- Patterns: Layer selection mutations, array texture creation redundancy, layered FBO attachment
- Blocks: 10 (array texture, per-layer data, shader with layer selection, layered FBO, render to layers, sample from layers)

**Seed 23: Cubemap Arrays + Seamless Filtering**
- File: `agent_outputs/mutation_b5_s23_cubemap_array_seamless.html`
- Extensions: `[]`
- Amplification vars: `cubeCount`, `faceSize`, `vertexCount`
- Enum vars: `cubemapTarget`, `textureFormat`, `filterMode`
- Patterns: Cubemap face mutations, array index selection, seamless enable/disable
- Blocks: 11 (cubemap array, per-face/cube data, shader with cube sampling, FBO per face, render all faces, seamless thrashing)

**Seed 24: Texture Swizzling + Format Reinterpretation**
- File: `agent_outputs/mutation_b5_s24_swizzle_reinterpret.html`
- Extensions: `[]`
- Amplification vars: `texSize`, `channelCount`, `vertexCount`
- Enum vars: `textureTarget`, `swizzleR`, `swizzleG`, `swizzleB`, `swizzleA`
- Patterns: Swizzle mask mutations, format reinterpretation, channel mapping variations
- Blocks: 9 (texture, swizzle parameter thrashing, shader sampling all channels, draw with different swizzles)

**Seed 25: Compressed Textures + Mipmap Generation**
- File: `agent_outputs/mutation_b5_s25_compressed_mipmaps.html`
- Extensions: `['WEBGL_compressed_texture_s3tc']` (check availability, may need fallback)
- Amplification vars: `texSize`, `mipLevels`, `vertexCount`
- Enum vars: `compressedFormat`, `textureTarget`
- Patterns: Mipmap generation redundancy, level mutations, compressed format variations
- Blocks: 9 (compressed texture, mipmap generation, level selection, shader with LOD, draw at different LODs)

### Batch 6: Seeds 26-30

**Seed 26: Texture Storage + Immutable Textures**
- File: `agent_outputs/mutation_b6_s26_texstorage_immutable.html`
- Extensions: `[]`
- Amplification vars: `texSize`, `mipLevels`, `vertexCount`
- Enum vars: `storageFormat`, `textureTarget`
- Patterns: TexStorage vs TexImage, immutability violations, storage mutation attempts
- Blocks: 8 (immutable texture via texStorage, attempt mutations, shader, draw, try to modify immutable)

**Seed 27: Integer Textures + Atomic Operations**
- File: `agent_outputs/mutation_b6_s27_integer_atomic.html`
- Extensions: `[]`
- Amplification vars: `texSize`, `atomicCount`, `vertexCount`
- Enum vars: `intFormat`, `atomicOp`
- Patterns: Integer texture creation, shader atomics, image load/store, counter mutations
- Blocks: 10 (integer texture, atomic counter buffer, shader with imageAtomicAdd, image binding, atomic ops, readback)

**Seed 28: Sampler Objects + Comparison Mode**
- File: `agent_outputs/mutation_b6_s28_sampler_compare.html`
- Extensions: `[]`
- Amplification vars: `samplerCount`, `texSize`, `vertexCount`
- Enum vars: `compareMode`, `compareFunc`, `filterMode`
- Patterns: Sampler bind ping-pong, comparison mode thrashing, filter mutations
- Blocks: 10 (depth texture, 3 samplers, sampler parameter mutations, shader with shadow sampling, sampler switching)

**Seed 29: Texture Subimage + TexStorage3D**
- File: `agent_outputs/mutation_b6_s29_subimage_storage3d.html`
- Extensions: `[]`
- Amplification vars: `texDepth`, `texSize`, `updateCount`, `subRegionSize`
- Enum vars: `tex3DTarget`, `storageFormat`
- Patterns: SubImage3D with varying regions, storage3D mutations, partial update patterns
- Blocks: 9 (3D texture via storage, subimage updates, overlapping regions, shader sampling, draw)

**Seed 30: Texture Views + Base/Max Level**
- File: `agent_outputs/mutation_b6_s30_texview_levels.html`
- Extensions: `[]`
- Amplification vars: `mipLevels`, `baseLevel`, `maxLevel`, `texSize`
- Enum vars: `textureTarget`, `viewFormat`
- Patterns: Base/max level mutations, view level range, incomplete texture states
- Blocks: 9 (texture with mipmaps, base/max level thrashing, shader sampling at levels, draw with different ranges)

### Batch 7: Seeds 31-35

**Seed 31: Uniform Buffer Arrays + Dynamic Indexing**
- File: `agent_outputs/mutation_b7_s31_ubo_array_dynamic.html`
- Extensions: `[]`
- Amplification vars: `uboArraySize`, `indexRange`, `vertexCount`
- Enum vars: `uboTarget`, `bufferUsage`
- Patterns: UBO array indexing, dynamic index mutations in shader, array out-of-bounds
- Blocks: 10 (UBO array, shader with dynamic indexing, per-element data, index mutations, draw calls)

**Seed 32: Texture Arrays + Dynamic Indexing**
- File: `agent_outputs/mutation_b7_s32_texarray_dynamic.html`
- Extensions: `[]`
- Amplification vars: `arraySize`, `texSize`, `indexRange`, `vertexCount`
- Enum vars: `arrayTarget`, `textureFormat`
- Patterns: Dynamic texture array indexing, index out-of-bounds, array size mutations
- Blocks: 9 (texture array, per-layer data, shader with dynamic index, index mutations, draw)

**Seed 33: Integer Vertex Attributes + Normalization**
- File: `agent_outputs/mutation_b7_s33_int_vertex_norm.html`
- Extensions: `[]`
- Amplification vars: `vertexCount`, `attributeCount`, `intRange`
- Enum vars: `intType`, `normalizeFlag`, `bufferTarget`
- Patterns: Integer attribute types, normalized vs non-normalized, attribute format mutations
- Blocks: 9 (int vertex buffer, shader with integer inputs, normalize flag thrashing, attribute format mutations, draw)

**Seed 34: Flat/Smooth Interpolation + Centroid**
- File: `agent_outputs/mutation_b7_s34_interp_flat_smooth.html`
- Extensions: `[]`
- Amplification vars: `varyingCount`, `vertexCount`, `interpolationModes`
- Enum vars: `bufferTarget`
- Patterns: Flat vs smooth interpolation, centroid sampling, interpolation qualifier mutations
- Blocks: 8 (buffer, shader with mixed interpolation qualifiers, varying data, draw large triangles)

**Seed 35: Derivative Functions + Explicit LOD**
- File: `agent_outputs/mutation_b7_s35_derivatives_lod.html`
- Extensions: `[]`
- Amplification vars: `texSize`, `lodBias`, `vertexCount`
- Enum vars: `textureTarget`, `filterMode`
- Patterns: dFdx/dFdy/fwidth usage, textureLod with mutations, derivative discontinuities
- Blocks: 9 (texture with mipmaps, shader with derivatives and explicit LOD, LOD mutations, draw)

### Batch 8: Seeds 36-40

**Seed 36: Bitfield Operations + Integer Math**
- File: `agent_outputs/mutation_b8_s36_bitfield_intmath.html`
- Extensions: `[]`
- Amplification vars: `intRange`, `bitCount`, `vertexCount`
- Enum vars: `bufferTarget`
- Patterns: Bitwise operations, integer overflow, bit extraction/insertion
- Blocks: 8 (buffer with integer data, shader with bitfield ops, integer math patterns, draw)

**Seed 37: Built-in Variables + gl_VertexID/InstanceID**
- File: `agent_outputs/mutation_b8_s37_builtins_ids.html`
- Extensions: `[]`
- Amplification vars: `vertexCount`, `instanceCount`, `idRange`
- Enum vars: `bufferTarget`
- Patterns: gl_VertexID/gl_InstanceID usage, gl_FragCoord patterns, built-in mutations
- Blocks: 8 (minimal buffers, shader using built-ins, instanced draws, ID-based patterns)

**Seed 38: Multiple Shader Stages + Complex Varyings**
- File: `agent_outputs/mutation_b8_s38_stages_varyings.html`
- Extensions: `[]`
- Amplification vars: `varyingCount`, `matrixSize`, `vertexCount`
- Enum vars: `bufferTarget`
- Patterns: Many varyings, complex types (matrices, arrays), varying packing
- Blocks: 9 (buffer, shader with many varyings, large varying structs, draw)

**Seed 39: Precision Qualifiers + Mixed Precision**
- File: `agent_outputs/mutation_b8_s39_precision_mixed.html`
- Extensions: `[]`
- Amplification vars: `precisionLevels`, `vertexCount`, `computeIntensity`
- Enum vars: `bufferTarget`
- Patterns: lowp/mediump/highp mixing, precision mismatches, implicit conversions
- Blocks: 8 (buffer, shader with mixed precision, precision-sensitive math, draw)

**Seed 40: Preprocessor + Macro Expansion**
- File: `agent_outputs/mutation_b8_s40_preprocessor_macro.html`
- Extensions: `[]`
- Amplification vars: `macroCount`, `defineValue`, `vertexCount`
- Enum vars: `bufferTarget`
- Patterns: Complex #define, conditional compilation, macro recursion
- Blocks: 7 (buffer, shader with heavy preprocessing, macro-driven variants, draw)

### Batch 9: Seeds 41-45

**Seed 41: Sync Objects + Client Wait**
- File: `agent_outputs/mutation_b9_s41_sync_clientwait.html`
- Extensions: `[]`
- Amplification vars: `syncCount`, `waitTimeout`, `drawCount`
- Enum vars: `syncCondition`, `waitFlags`
- Patterns: Fence sync creation redundancy, clientWaitSync with timeout mutations, deletion after wait
- Blocks: 10 (render operations, sync creation, wait patterns, timeout mutations, draw+sync chains)

**Seed 42: Sync Objects + Server Wait + Fences**
- File: `agent_outputs/mutation_b9_s42_sync_serverwait.html`
- Extensions: `[]`
- Amplification vars: `fenceCount`, `drawCount`, `waitTimeout`
- Enum vars: `syncCondition`, `bufferTarget`
- Patterns: waitSync (server-side), fence creation/deletion, sync status queries
- Blocks: 10 (render, fence sync, waitSync, query sync status, multiple fences, interleaved draws)

**Seed 43: Query Objects + Occlusion Queries**
- File: `agent_outputs/mutation_b9_s43_query_occlusion.html`
- Extensions: `[]`
- Amplification vars: `queryCount`, `drawCount`, `primitiveCount`
- Enum vars: `queryTarget`, `bufferTarget`
- Patterns: Query begin/end thrashing, nested query attempts, multiple query objects
- Blocks: 10 (geometry, query creation, begin/end patterns, occlusion draws, query results)

**Seed 44: Query Objects + Transform Feedback Queries**
- File: `agent_outputs/mutation_b9_s44_query_tf.html`
- Extensions: `[]`
- Amplification vars: `queryCount`, `tfPrimitives`, `vertexCount`
- Enum vars: `queryTarget`, `tfMode`, `bufferTarget`
- Patterns: TF primitives written query, query begin/end with TF, multiple queries
- Blocks: 11 (TF setup, query objects, TF+query begin, draw with TF, end patterns, query results)

**Seed 45: Instanced Rendering + Divisors**
- File: `agent_outputs/mutation_b9_s45_instancing_divisors.html`
- Extensions: `[]`
- Amplification vars: `instanceCount`, `divisorValue`, `attributeCount`, `vertexCount`
- Enum vars: `bufferTarget`, `bufferUsage`
- Patterns: vertexAttribDivisor mutations, per-instance attributes, divisor value variations
- Blocks: 9 (vertex buffer, instance buffers, shader, divisor mutations per attribute, instanced draws)

### Batch 10: Seeds 46-50

**Seed 46: Instanced Rendering + Base Instance**
- File: `agent_outputs/mutation_b10_s46_instancing_base.html`
- Extensions: `[]`
- Amplification vars: `instanceCount`, `baseInstance`, `vertexCount`
- Enum vars: `bufferTarget`
- Patterns: drawArraysInstancedBaseInstance, base instance mutations, gl_InstanceID offset
- Blocks: 9 (buffers, shader using gl_InstanceID, base instance mutations, multiple instanced draws)

**Seed 47: Primitive Restart + Index Ranges**
- File: `agent_outputs/mutation_b10_s47_primrestart_ranges.html`
- Extensions: `[]`
- Amplification vars: `restartIndex`, `indexCount`, `rangeCount`
- Enum vars: `indexType`, `primitiveMode`, `bufferTarget`
- Patterns: Restart index mutations, drawRangeElements, restart enable/disable
- Blocks: 9 (vertex buffer, index buffer with restarts, shader, restart thrashing, range draws)

**Seed 48: Provoking Vertex + Flat Shading**
- File: `agent_outputs/mutation_b10_s48_provoking_flat.html`
- Extensions: `[]`
- Amplification vars: `vertexCount`, `primitiveCount`, `colorIndex`
- Enum vars: `provokingMode`, `bufferTarget`
- Patterns: Provoking vertex mode (first/last), flat shading, vertex order sensitivity
- Blocks: 8 (vertex buffer, shader with flat color, provoking mode mutations, draw primitives)

**Seed 49: Rasterizer Discard + TF Only**
- File: `agent_outputs/mutation_b10_s49_rasterizer_discard_tf.html`
- Extensions: `[]`
- Amplification vars: `vertexCount`, `tfBufferSize`, `passCount`
- Enum vars: `tfMode`, `bufferTarget`
- Patterns: Rasterizer discard enable/disable, TF without fragment shader, discard thrashing
- Blocks: 10 (input buffer, TF buffers, shader, rasterizer discard state, TF passes, discard toggle, read TF)

**Seed 50: Context State + Multiple Contexts** (Note: Tricky in single-canvas setup)
- File: `agent_outputs/mutation_b10_s50_context_state.html`
- Extensions: `[]`
- Amplification vars: `stateCount`, `drawCount`, `contextSwitches`
- Enum vars: `bufferTarget`, `textureTarget`
- Patterns: Heavy state changes, state query redundancy, context attribute mutations
- Blocks: 8 (comprehensive state setup, state thrashing across all categories, state queries, draws with state changes)

---

## Implementation Strategy

### Phase 1: Parallel Seed Creation (10 agents)

Each agent receives:
1. Batch number (1-10)
2. Seed specifications for their 5 seeds
3. Instruction: CREATE seeds without testing
4. Output: 5 HTML files in agent_outputs/

**Agent Task Template:**

```
Create 5 mutation-optimized WebGL2 seeds for Batch N:

For each seed in your batch:
1. Read seed specification above
2. Create HTML file with exact filename
3. Implement three-zone architecture:
   - Declaration Zone: Listed amplification and enum variables
   - Setup Zone: Listed patterns and blocks
   - Execution Zone: State thrashing, draw calls, cleanup
4. Include try-catch blocks with console.log(e)
5. Follow all line repetition patterns
6. DO NOT run tests (avoid browser conflicts)
7. Verify file is created in agent_outputs/

Each seed must have:
- 5-8 amplification variables
- 4-6 enum constants
- 20-40 inline literals
- 6-10 try-catch blocks
- Proper three-zone structure
```

### Phase 2: Batch Testing (Sequential)

After all agents complete, run single test pass:

```bash
# Test all 50 seeds
./run_tests.sh --test-dir agent_outputs --browsers firefox

# Review results
find agent_outputs -name "*.json" -exec grep -l '"passed": false' {} \;
```

### Phase 3: Fix and Finalize

1. Identify failed seeds from JSON output
2. Fix errors (undefined vars, wrong constants, shader errors)
3. Strip all console.log statements
4. Re-run validation
5. Commit in batches

---

## Coordination Safety

**Why parallel creation is safe:**
- No browser instances launched during creation
- Each agent writes different files (batch number in filename)
- No shared state between agents
- Testing happens AFTER all creation completes

**Why sequential testing is necessary:**
- run_tests.sh spawns browser instance
- Multiple simultaneous browsers can conflict
- Firefox/Playwright has single-instance limitations

---

## Success Criteria

- 50 HTML files created in agent_outputs/
- All follow mutation-fuzzing-seed-structure design
- Each seed unique feature combination
- All pass validation after fixing
- Console.log stripped from production versions
- Visual output for all seeds
- Comprehensive corpus covering WebGL2 feature space

---

## Estimated Time

- Phase 1 (Parallel creation): 30-45 minutes (all agents working simultaneously)
- Phase 2 (Testing): 15-20 minutes (sequential browser runs)
- Phase 3 (Fixing): 30-60 minutes (depends on error count)
- **Total: 75-125 minutes for 50 seeds**

Compare to sequential: ~250 minutes (5 min/seed × 50)
**Speedup: ~2-3x faster with parallelization**
