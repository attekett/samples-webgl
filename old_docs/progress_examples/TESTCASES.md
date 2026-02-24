# WebGPU Fuzzing Corpus: Test Cases

This document provides a comprehensive list of standalone, runnable test cases designed to exercise and fuzz the WebGPU API. Each test case is a self-contained HTML file with embedded JavaScript and WGSL, targeting a specific feature, limit, or behavior as outlined in the `TODO.md` file.

## 1) Platform and Initialization

### 1.1) `navigator.gpu` Presence Detection

**File:** `platform/navigator_gpu_presence.html`
**Covers:** `TODO.md #11`
**Description:** This test checks for the existence of `navigator.gpu`. If present, it logs a success message. If absent, it displays a clean fallback message to the user, ensuring graceful degradation.

### 1.2) `requestAdapter()` with Options

**File:** `platform/request_adapter_options.html`
**Covers:** `TODO.md #12`
**Description:** This test requests a `GPUAdapter` with different `powerPreference` options (`"high-performance"` and `"low-power"`) and with `forceFallbackAdapter=true`. It handles the case where the promise resolves to `null`, indicating no available adapter.

### 1.3) GPUAdapter Info

**File:** `platform/adapter_info.html`
**Covers:** `TODO.md #13`
**Description:** This test reads and logs all properties from the `GPUAdapter.info` object (vendor, architecture, device, description). It verifies that the values are strings and remain consistent across multiple accesses. It also covers privacy considerations where some values might be empty strings.

### 1.4) `getPreferredCanvasFormat()`

**File:** `platform/preferred_canvas_format.html`
**Covers:** `TODO.md #14`
**Description:** A simple test that gets the preferred canvas format via `navigator.gpu.getPreferredCanvasFormat()` and logs it. This format is then used in a `GPUCanvasContext.configure()` call to ensure compatibility.

### 1.5) `wgslLanguageFeatures` Set

**File:** `platform/wgsl_language_features.html`
**Covers:** `TODO.md #15`
**Description:** This test inspects the `navigator.gpu.wgslLanguageFeatures` `FrozenSet`. It iterates over the supported features, logging each one, and uses the `has()` method to check for the presence of a known feature (like `shader-f16` if available).

### 1.6) `requestDevice()` with Features and Limits

**File:** `platform/request_device_features_limits.html`
**Covers:** `TODO.md #16`
**Description:** This test requests a `GPUDevice` with a minimal set of required features and limits that are known to be supported by the adapter. It verifies that the device is successfully created.

### 1.7) `requestDevice()` with Unknown Feature

**File:** `platform/request_device_unknown_feature.html`
**Covers:** `TODO.md #17`
**Description:** This test attempts to call `requestDevice` with a completely fictional feature name (e.g., `"unknown-feature"`). It asserts that this throws an immediate `TypeError` before a promise is even returned, as per the spec.

### 1.8) `requestDevice()` with Unsupported Feature

**File:** `platform/request_device_unsupported_feature.html`
**Covers:** `TODO.md #18`
**Description:** This test attempts to request a device with a valid but unsupported feature (it skips if all standard features are supported). It asserts that the `requestDevice` promise rejects with an appropriate error.

### 1.9) `requestDevice()` Exceeding Limits

**File:** `platform/request_device_exceeding_limits.html`
**Covers:** `TODO.md #19`
**Description:** This test reads the adapter's limits, then attempts to `requestDevice` with a `requiredLimits` value that is slightly higher (e.g., `maxTextureDimension2D + 1`). It asserts that the promise rejects.

### 1.10) `requestAdapterInfo()`

**File:** `platform/request_adapter_info.html`
**Covers:** `TODO.md #1`
**Description:** This test calls `requestAdapterInfo()` with and without the `unmaskHintedRenderer` hint. It logs the returned `GPUAdapterInfo` to observe the privacy-protected and unmasked renderer information, if available.

## 2) Core Features Coverage (GPUFeatureName)

For each feature, a positive and negative test case is included. The positive case requests the feature and uses it. The negative case does not request the feature and asserts that attempting to use it generates a validation error.

### 2.1) `depth-clip-control`

**File:** `features/depth_clip_control.html`
**Covers:** `TODO.md #24`
**Description:** 
- **Positive:** Requests the `"depth-clip-control"` feature and creates a `GPURenderPipeline` with `depthClipControl: false`.
- **Negative:** Fails to create a pipeline with `depthClipControl: false` when the feature is not enabled, triggering a validation error.

### 2.2) `depth32float-stencil8`

**File:** `features/depth32float_stencil8.html`
**Covers:** `TODO.md #25`
**Description:** 
- **Positive:** Requests the feature and successfully creates a `GPUTexture` and a `GPURenderPipeline` using the `"depth32float-stencil8"` format.
- **Negative:** Fails to create a texture or pipeline with this format if the feature is not enabled.

### 2.3) `texture-compression-bc`

**File:** `features/texture_compression_bc.html`
**Covers:** `TODO.md #26`
**Description:** 
- **Positive:** Requests the feature, creates textures with various BC formats (e.g., `"bc7-rgba-unorm-srgb"`), and uses them for sampling.
- **Negative:** Fails to create a texture with a BC format when the feature is not enabled.

### 2.4) `texture-compression-etc2`

**File:** `features/texture_compression_etc2.html`
**Covers:** `TODO.md #28`
**Description:** 
- **Positive:** Requests the feature, creates textures with various ETC2 formats (e.g., `"etc2-rgb8unorm"`), and uses them.
- **Negative:** Fails to create a texture with an ETC2 format when the feature is not enabled.

### 2.5) `texture-compression-astc`

**File:** `features/texture_compression_astc.html`
**Covers:** `TODO.md #29`
**Description:** 
- **Positive:** Requests the feature, creates textures with various ASTC formats (e.g., `"astc-4x4-rgba-unorm"`), and uses them.
- **Negative:** Fails to create a texture with an ASTC format when the feature is not enabled.

### 2.6) `timestamp-query`

**File:** `features/timestamp_query.html`
**Covers:** `TODO.md #31`
**Description:** 
- **Positive:** Requests the feature, creates a `GPUQuerySet` with `type: "timestamp"`, and successfully calls `writeTimestamp()` in a command encoder.
- **Negative:** Fails to create a timestamp query set or use `writeTimestamp()` if the feature is not enabled.

### 2.7) `indirect-first-instance`

**File:** `features/indirect_first_instance.html`
**Covers:** `TODO.md #32`
**Description:** 
- **Positive:** Requests the feature and successfully uses `drawIndirect()` and `drawIndexedIndirect()` where the indirect buffer contains a non-zero value for `firstInstance`.
- **Negative:** A validation error is triggered if an indirect draw call uses a non-zero `firstInstance` and the feature is not enabled.

### 2.8) `shader-f16`

**File:** `features/shader_f16.html`
**Covers:** `TODO.md #33`
**Description:** 
- **Positive:** Requests the feature and compiles a WGSL shader that uses the `f16` data type for variables, arithmetic, and function arguments.
- **Negative:** Fails to compile a WGSL shader module containing `f16` types if the feature is not enabled.

### 2.9) `rg11b10ufloat-renderable`

**File:** `features/rg11b10ufloat_renderable.html`
**Covers:** `TODO.md #34`
**Description:** 
- **Positive:** Requests the feature and successfully uses a texture with the `"rg11b10ufloat"` format as a color attachment in a render pass.
- **Negative:** Fails to create a render pipeline with this attachment format if the feature is not enabled.

### 2.10) `bgra8unorm-storage`

**File:** `features/bgra8unorm_storage.html`
**Covers:** `TODO.md #35`
**Description:** 
- **Positive:** Requests the feature and successfully creates a `GPUBindGroupLayout` for a storage texture with the `"bgra8unorm"` format.
- **Negative:** Fails bind group layout creation for a `"bgra8unorm"` storage texture if the feature is not enabled.

### 2.11) `float32-filterable`

**File:** `features/float32_filterable.html`
**Covers:** `TODO.md #36`
**Description:** 
- **Positive:** Requests the feature and creates a `GPUSampler` with `type: "filtering"` to sample a `r32float`, `rg32float`, or `rgba32float` texture.
- **Negative:** Fails to create a filtering sampler for a 32-bit float texture if the feature is not enabled.

### 2.12) `clip-distances`

**File:** `features/clip_distances.html`
**Covers:** `TODO.md #38`
**Description:**
- **Positive:** Requests the feature, creates a pipeline with a vertex shader that writes to the `@builtin(clip_distance)` WGSL variable.
- **Negative:** Fails pipeline creation if the vertex shader writes to `@builtin(clip_distance)` but the feature is not enabled.

### 2.13) `dual-source-blending`

**File:** `features/dual_source_blending.html`
**Covers:** `TODO.md #39`
**Description:**
- **Positive:** Requests the feature, creates a render pipeline where the fragment shader outputs two color sources (`@location(0)` and `@location(1)`), and configures dual-source blending factors in the color target state.
- **Negative:** Fails pipeline creation if the blend state for a color target uses dual-source factors (e.g., `src-alpha1`) but the feature is not enabled.

## 3) Limits Coverage (GPUSupportedLimits)

For each limit, the test cases will query the adapter's supported limit and then attempt to create resources or pipelines that are at the limit, and one greater than the limit. The "exceeding" case should always generate a validation error.

### 3.1) `maxTextureDimension1D/2D/3D`

**File:** `limits/max_texture_dimensions.html`
**Covers:** `TODO.md #47-49`
**Description:**
- **Positive:** Creates 1D, 2D, and 3D textures with dimensions exactly matching the corresponding `maxTextureDimension` limits.
- **Negative:** Attempts to create 1D, 2D, and 3D textures with one dimension set to `maxTextureDimension + 1`, expecting a validation error.

### 3.2) `maxTextureArrayLayers`

**File:** `limits/max_texture_array_layers.html`
**Covers:** `TODO.md #50`
**Description:**
- **Positive:** Creates a 2D texture with `arrayLayerCount` equal to `maxTextureArrayLayers`.
- **Negative:** Fails to create a texture with `arrayLayerCount` set to `maxTextureArrayLayers + 1`.

### 3.3) `maxBindGroups`

**File:** `limits/max_bind_groups.html`
**Covers:** `TODO.md #51`
**Description:**
- **Positive:** Creates a `GPUPipelineLayout` with a number of `GPUBindGroupLayout`s equal to `maxBindGroups`.
- **Negative:** Fails to create a pipeline layout with `maxBindGroups + 1` bind group layouts.

### 3.4) `maxDynamicUniformBuffersPerPipelineLayout`

**File:** `limits/max_dynamic_uniform_buffers.html`
**Covers:** `TODO.md #54`
**Description:**
- **Positive:** Creates a pipeline layout with `maxDynamicUniformBuffersPerPipelineLayout` dynamic uniform buffer bindings spread across its bind group layouts.
- **Negative:** Fails to create a pipeline layout with one more than the maximum number of dynamic uniform buffer bindings.

### 3.5) `maxSampledTexturesPerShaderStage`

**File:** `limits/max_sampled_textures_per_stage.html`
**Covers:** `TODO.md #56`
**Description:**
- **Positive:** Creates a pipeline whose vertex or fragment shader declares `maxSampledTexturesPerShaderStage` sampled textures.
- **Negative:** Fails to create a pipeline if a shader stage declares `maxSampledTexturesPerShaderStage + 1` textures.

### 3.6) `maxStorageBuffersPerShaderStage`

**File:** `limits/max_storage_buffers_per_stage.html`
**Covers:** `TODO.md #58`
**Description:**
- **Positive:** Creates a compute pipeline where the shader declares `maxStorageBuffersPerShaderStage` storage buffers.
- **Negative:** Fails to create a pipeline if the shader declares `maxStorageBuffersPerShaderStage + 1` storage buffers.

### 3.7) `maxUniformBufferBindingSize`

**File:** `limits/max_uniform_buffer_binding_size.html`
**Covers:** `TODO.md #61`
**Description:**
- **Positive:** Creates a `GPUBuffer` with `usage: GPUBufferUsage.UNIFORM` and `size: maxUniformBufferBindingSize` and binds it successfully.
- **Negative:** Attempts to bind a uniform buffer with a size or offset that exceeds `maxUniformBufferBindingSize`, expecting an error.

### 3.8) `maxVertexBuffers`

**File:** `limits/max_vertex_buffers.html`
**Covers:** `TODO.md #65`
**Description:**
- **Positive:** Creates a `GPURenderPipeline` with a vertex state that defines `maxVertexBuffers` buffer layouts. `setVertexBuffer` is then called for each slot.
- **Negative:** Fails to create a pipeline with `maxVertexBuffers + 1` vertex buffer layouts. Also tests calling `setVertexBuffer` on a slot greater than or equal to `maxVertexBuffers`.

### 3.9) `maxColorAttachments`

**File:** `limits/max_color_attachments.html`
**Covers:** `TODO.md #70`
**Description:**
- **Positive:** Creates a `GPURenderPipeline` with `maxColorAttachments` color target states.
- **Negative:** Fails to create a pipeline with `maxColorAttachments + 1` color target states.

### 3.10) `maxComputeInvocationsPerWorkgroup`

**File:** `limits/max_compute_invocations.html`
**Covers:** `TODO.md #73`
**Description:**
- **Positive:** Creates a compute pipeline with a workgroup size (e.g., `(X, Y, Z)`) such that `X * Y * Z` equals `maxComputeInvocationsPerWorkgroup`.
- **Negative:** Fails to create a pipeline where the product of the workgroup size dimensions exceeds the limit.

## 4) Buffers (GPUBuffer)

### 4.1) `createBuffer` Size Variants

**File:** `buffers/create_buffer_sizes.html`
**Covers:** `TODO.md #78`
**Description:** This test creates buffers with various sizes: 0, 1, a size that is not a multiple of 4, a large size near `maxBufferSize`, and a size exactly equal to `maxBufferSize`. It also tests that creating a buffer larger than `maxBufferSize` throws an error.

### 4.2) `createBuffer` Usage Flags

**File:** `buffers/create_buffer_usage.html`
**Covers:** `TODO.md #79`
**Description:** Creates buffers with all valid single `GPUBufferUsage` flags and all valid combinations of flags. It asserts that disallowed combinations (e.g., `MAP_WRITE | COPY_DST`) trigger an error.

### 4.3) `mappedAtCreation`

**File:** `buffers/mapped_at_creation.html`
**Covers:** `TODO.md #80`
**Description:**
- **Positive:** Creates a buffer with `mappedAtCreation: true`, gets the mapped range via `getMappedRange()`, writes data to it, and then unmaps it.
- **Negative:** Tests calling `getMappedRange` with out-of-bounds ranges. Asserts that you cannot call `mapAsync` on a buffer created as mapped until it is unmapped.

### 4.4) `mapAsync`

**File:** `buffers/map_async.html`
**Covers:** `TODO.md #81`
**Description:** This test covers the `mapAsync` lifecycle. It maps a buffer for `GPUMapMode.WRITE`, writes data, unmaps it, then maps it for `GPUMapMode.READ`, and verifies the contents. It includes negative tests for mapping a buffer that is already mapped or currently in use by the GPU.

### 4.5) `queue.writeBuffer`

**File:** `buffers/queue_write_buffer.html`
**Covers:** `TODO.md #82`
**Description:** Exercises `queue.writeBuffer` with various offsets and sizes, including full, partial, and zero-sized writes. It includes negative tests for writes that would go out of the buffer's bounds.

### 4.6) `copyBufferToBuffer`

**File:** `buffers/copy_buffer_to_buffer.html`
**Covers:** `TODO.md #83`
**Description:** Performs copies between buffers of various sizes and alignments. Includes tests for zero-sized copies and overlapping regions to ensure correct behavior and validation.

### 4.7) `destroy()`

**File:** `buffers/destroy.html`
**Covers:** `TODO.md #84`
**Description:** Creates a buffer, destroys it, and then attempts to use it in various ways (map, write, copy, bind), asserting that all subsequent operations are invalid and generate errors.

## 5) Textures and Texture Views (GPUTexture, GPUTextureView)

### 5.1) `createTexture` Variants

**File:** `textures/create_texture_variants.html`
**Covers:** `TODO.md #88`
**Description:** Creates textures with different dimensions (`1d`, `2d`, `3d`), mip level counts, and sample counts (1 and 4). Verifies that creating textures with invalid configurations (e.g., `sampleCount > 1` for a 3D texture) throws an error.

### 5.2) `createView`

**File:** `textures/create_view.html`
**Covers:** `TODO.md #91`
**Description:** Creates a base texture and then creates multiple views into it with different `baseMipLevel`, `mipLevelCount`, `baseArrayLayer`, `arrayLayerCount`, and `aspect` settings. Includes negative tests for view descriptors that are out of bounds of the source texture.

### 5.3) `queue.writeTexture`

**File:** `textures/queue_write_texture.html`
**Covers:** `TODO.md #92`
**Description:** Uses `queue.writeTexture` to upload data to 2D and 3D textures. Tests various `bytesPerRow` and `rowsPerImage` alignments, including tightly packed and loosely packed data. Includes negative tests for out-of-bounds writes.

### 5.4) Texture Copies

**File:** `textures/texture_copies.html`
**Covers:** `TODO.md #93`
**Description:**
- `copyTextureToBuffer`: Copies data from a texture subregion to a GPU buffer and reads it back to verify correctness.
- `copyBufferToTexture`: Copies data from a buffer to a texture subregion.
- `copyTextureToTexture`: Copies between different regions of two textures, including tests for overlapping regions.

### 5.5) Compressed Textures

**File:** `textures/compressed_textures.html`
**Covers:** `TODO.md #95`
**Description:** If a compressed format feature is available (e.g., `"texture-compression-bc"`), this test creates a texture with that format, uploads data with `writeTexture`, and samples from it. It includes negative tests for creating compressed textures with dimensions that are not a multiple of the block size.

### 5.6) `destroy()`

**File:** `textures/destroy.html`
**Covers:** `TODO.md #97`
**Description:** Creates a texture and a view from it. Destroys the texture. Asserts that any subsequent use of the texture or its view (e.g., in a bind group or as a render attachment) is invalid.

## 6) Samplers (GPUSampler)

### 6.1) Sampler Address Modes

**File:** `samplers/address_modes.html`
**Covers:** `TODO.md #100`
**Description:** Creates three samplers, one for each address mode: `clamp-to-edge`, `repeat`, and `mirror-repeat`. A shader then samples a texture with UV coordinates outside the `[0, 1]` range to verify that each mode behaves as expected.

### 6.2) Sampler Filtering

**File:** `samplers/filtering.html`
**Covers:** `TODO.md #101`
**Description:** Creates samplers with `magFilter` and `minFilter` set to `nearest` and `linear`. Samples a texture at coordinates between pixels to verify that the correct filtering is applied.

### 6.3) `compare` Sampler

**File:** `samplers/compare.html`
**Covers:** `TODO.md #101`
**Description:** Creates a `compare` sampler and a `depth` texture view. Uses the `textureSampleCompareLevel` function in WGSL to perform percentage-closer filtering, a common technique for shadow mapping.

### 6.4) Invalid Sampler-Texture Combination

**File:** `samplers/invalid_combination.html`
**Covers:** `TODO.md #103`
**Description:** This test attempts to create a bind group where a `compare` sampler is paired with a non-depth texture format (e.g., `rgba8unorm`). It asserts that this is a validation error.

## 7) Shader Modules (GPUShaderModule)

### 7.1) Valid WGSL Module

**File:** `shaders/valid_module.html`
**Covers:** `TODO.md #106`
**Description:** Creates a valid WGSL shader module with multiple entry points (`@vertex`, `@fragment`, `@compute`) and successfully creates pipelines from it.

### 7.2) Invalid WGSL Module

**File:** `shaders/invalid_module.html`
**Covers:** `TODO.md #108`
**Description:** Attempts to create a shader module from WGSL source that contains a syntax error. It checks `getCompilationInfo()` and asserts that the promise rejects or the returned info object contains error messages.

### 7.3) `shader-f16` Gated WGSL

**File:** `shaders/shader_f16_gated.html`
**Covers:** `TODO.md #107`
**Description:** If the `"shader-f16"` feature is supported and enabled, this test successfully creates a shader module using `f16` types. It also includes a negative test asserting that module creation fails if the feature is supported but *not* enabled on the device.

## 8) Pipeline Layouts and Bind Groups

### 8.1) Bind Group Layout with Buffer Types

**File:** `bind_groups/bgl_buffer_types.html`
**Covers:** `TODO.md #112`
**Description:** Creates a `GPUBindGroupLayout` with entries for `uniform`, `storage`, and `read-only-storage` buffer types, including dynamic offsets and `minBindingSize`.

### 8.2) Bind Group Layout with Texture Types

**File:** `bind_groups/bgl_texture_types.html`
**Covers:** `TODO.md #113`
**Description:** Creates a `GPUBindGroupLayout` with entries for various texture `sampleType`s (`float`, `unfilterable-float`, `depth`, `sint`, `uint`) and `viewDimension`s.

### 8.3) Bind Group Layout with Storage Texture

**File:** `bind_groups/bgl_storage_texture.html`
**Covers:** `TODO.md #114`
**Description:** Creates a `GPUBindGroupLayout` for a `storage` texture with `access: "write-only"` and a compatible format. Includes a negative test for an incompatible format.

### 8.4) Pipeline Layout

**File:** `bind_groups/pipeline_layout.html`
**Covers:** `TODO.md #116`
**Description:** Creates a `GPUPipelineLayout` from multiple `GPUBindGroupLayout`s.

### 8.5) Bind Group Creation

**File:** `bind_groups/bind_group_creation.html`
**Covers:** `TODO.md #117`
**Description:**
- **Positive:** Creates a `GPUBindGroup` that perfectly matches its corresponding `GPUBindGroupLayout`.
- **Negative:** Attempts to create a bind group with various mismatches: wrong resource type (e.g., a sampler where a texture is expected), missing entries, extra entries, or a buffer that is too small for the layout's `minBindingSize`. Each case should trigger a validation error.

## 9) Render Pipelines (GPURenderPipeline)

### 9.1) Vertex State

**File:** `pipelines/render_pipeline_vertex_state.html`
**Covers:** `TODO.md #120`
**Description:** Creates a render pipeline with a complex `vertex` state, including multiple `vertexBuffers` with different `arrayStride`s, `stepMode`s, and `attributes` covering various formats and shader locations.

### 9.2) Primitive State and Topology

**File:** `pipelines/render_pipeline_primitive_state.html`
**Covers:** `TODO.md #121`
**Description:** Creates and uses render pipelines for each primitive `topology`: `point-list`, `line-list`, `line-strip`, `triangle-list`, and `triangle-strip`. For strip topologies, it tests the `stripIndexFormat` (`uint16` vs. `uint32`).

### 9.3) Depth/Stencil State

**File:** `pipelines/render_pipeline_depth_stencil.html`
**Covers:** `TODO.md #123`
**Description:** Creates a render pipeline with a `depthStencil` state, enabling depth testing (`depthCompare: 'less'`), depth writes (`depthWriteEnabled: true`), and stencil operations.

### 9.4) Multisample State

**File:** `pipelines/render_pipeline_multisample.html`
**Covers:** `TODO.md #124`
**Description:** Creates a render pipeline with `multisample.count > 1` and renders to a multisampled color attachment. The multisampled texture is then resolved to a standard texture for verification.

### 9.5) Color Target State and Blending

**File:** `pipelines/render_pipeline_blending.html`
**Covers:** `TODO.md #125`
**Description:** Creates a render pipeline with a `colorTargetState` that enables alpha blending by setting the `blend` property. The test renders semi-transparent objects to verify the blend factors are applied correctly.

### 9.6) Async Pipeline Creation

**File:** `pipelines/render_pipeline_async.html`
**Covers:** `TODO.md #126`
**Description:** Uses `createRenderPipelineAsync` to create a pipeline. It checks that a `GPUPipeline` object is returned and that the promise resolves successfully. Includes a negative test with an invalid descriptor, asserting that the promise rejects.

## 10) Compute Pipelines (GPUComputePipeline)

### 10.1) Basic Compute Pipeline

**File:** `pipelines/compute_pipeline_basic.html`
**Covers:** `TODO.md #129`
**Description:** Creates a simple compute pipeline that reads from one storage buffer and writes a result to another. It dispatches the compute shader and reads the data back to verify the result.

### 10.2) `dispatchWorkgroupsIndirect`

**File:** `pipelines/compute_pipeline_indirect.html`
**Covers:** `TODO.md #130`
**Description:** Uses a compute shader to write dispatch parameters (`x`, `y`, `z`) to an indirect buffer. Then uses `dispatchWorkgroupsIndirect` with that buffer to launch a second compute pass.

## 11) Command Encoding and Passes

### 11.1) Render Pass Load/Store Operations

**File:** `encoding/render_pass_load_store.html`
**Covers:** `TODO.md #135`
**Description:** This test demonstrates the behavior of different `loadOp` (`"clear"`, `"load"`) and `storeOp` (`"store"`, `"discard"`) values for color and depth/stencil attachments in a `GPURenderPassDescriptor`.

### 11.2) Render Pass with Resolve Target

**File:** `encoding/render_pass_resolve.html`
**Covers:** `TODO.md #136`
**Description:** Renders a primitive to a multisampled color attachment (`sampleCount: 4`) and sets a non-multisampled `resolveTarget`. After the pass, the content of the resolve target is verified.

### 11.3) `executeBundles`

**File:** `encoding/execute_bundles.html`
**Covers:** `TODO.md #138`
**Description:** Creates a `GPURenderBundle` containing a draw call. Then, in a `GPURenderPassEncoder`, it calls `executeBundles` with the created bundle to perform the drawing commands.

### 11.4) `clearBuffer`

**File:** `encoding/clear_buffer.html`
**Covers:** `TODO.md #11`
**Description:** Uses `clearBuffer` on a `GPUCommandEncoder` to zero-out a region of a `GPUBuffer`. It verifies the cleared region and also tests that the regions outside the clear range are unaffected.

## 12) Queue (GPUQueue)

### 12.1) `submit` with multiple Command Buffers

**File:** `queue/submit_multiple.html`
**Covers:** `TODO.md #142`
**Description:** Creates two separate command buffers. The first copies data to a buffer, and the second copies it to a different buffer. Both are submitted in a single `submit` call. The test verifies that the operations were executed in order.

### 12.2) `onSubmittedWorkDone`

**File:** `queue/on_submitted_work_done.html`
**Covers:** `TODO.md #143`
**Description:** Submits a command buffer and uses the `onSubmittedWorkDone()` promise to signal when the GPU has finished. This is used to accurately measure GPU execution time and to synchronize with `buffer.mapAsync`.

### 12.3) `copyExternalImageToTexture`

**File:** `queue/copy_external_image.html`
**Covers:** `TODO.md #146-149`
**Description:** Creates an `ImageBitmap` from a data URL. It then uses `copyExternalImageToTexture` to upload the bitmap data into a `GPUTexture`. The texture is then rendered to the canvas to verify the copy.

## 13) Queries (GPUQuerySet)

### 13.1) Occlusion Query

**File:** `queries/occlusion_query.html`
**Covers:** `TODO.md #152`
**Description:** Creates an `occlusion` query set. In a render pass, it calls `beginOcclusionQuery` and `endOcclusionQuery` around a draw call. The query results are then resolved into a buffer and read back to see how many samples passed the depth test.

### 13.2) Timestamp Query

**File:** `queries/timestamp_query.html`
**Covers:** `TODO.md #153`
**Description:** If the `"timestamp-query"` feature is enabled, this test writes timestamps at the beginning and end of a pass. The results are resolved to a buffer and read back to calculate the GPU execution time for the pass.

## 14) Canvas and Presentation (GPUCanvasContext)

### 14.1) Basic Canvas Presentation

**File:** `canvas/basic_present.html`
**Covers:** `TODO.md #157-160`
**Description:** A minimal test that gets a `'webgpu'` context from an HTML canvas, configures it, gets the `getCurrentTexture()`, renders a clear color to it, and implicitly submits it for presentation.

### 14.2) Canvas Resizing

**File:** `canvas/resize.html`
**Covers:** `TODO.md #159`
**Description:** This test renders a frame, then changes the canvas's client width and height. It then re-configures the context and renders another frame, demonstrating how to handle canvas resizing.

### 14.3) `alphaMode`

**File:** `canvas/alpha_mode.html`
**Covers:** `TODO.md #163`
**Description:** Configures the canvas context with `alphaMode: 'premultiplied'` and `alphaMode: 'opaque'`. It renders a semi-transparent object against the page's HTML background to show how the modes affect final compositing.

## 15) External Textures (GPUExternalTexture)

### 15.1) `importExternalTexture` from Video

**File:** `external_texture/import_video.html`
**Covers:** `TODO.md #168`
**Description:** This test uses a `<video>` element as a source. In a `requestAnimationFrame` loop, it calls `importExternalTexture` with the video element and samples from the resulting `GPUExternalTexture` in a shader to render the video to the canvas.

## 16) Errors & Debugging

### 16.1) `pushErrorScope` / `popErrorScope`

**File:** `errors/error_scope.html`
**Covers:** `TODO.md #174, #178`
**Description:** This test intentionally triggers a validation error (e.g., creating a buffer with invalid usage flags) inside an error scope (`pushErrorScope('validation')`). It then calls `popErrorScope()` and asserts that the promise resolves with a `GPUValidationError` object.

### 16.2) `uncapturederror` Event

**File:** `errors/uncaptured_error.html`
**Covers:** `TODO.md #175`
**Description:** An event listener is added to the `GPUDevice` for the `uncapturederror` event. The test then triggers a validation error *without* an error scope, and asserts that the event listener fires with a `GPUUncapturedErrorEvent`.

### 16.3) Device Loss

**File:** `errors/device_loss.html`
**Covers:** `TODO.md #177`
**Description:** The test checks the `device.lost` promise. While a real device loss is hard to trigger, the test sets up the promise handler to log a message if the device is lost for any reason. A follow-up test could use a browser-specific extension to force a device loss for more thorough testing.

## 17) Robustness/Security-Oriented Cases

### 17.1) Zero-Initialization of Resources

**File:** `robustness/zero_initialization.html`
**Covers:** `TODO.md #181`
**Description:** This test creates a new buffer and a new texture. Without writing any data to them, it immediately copies their contents to a readable buffer and verifies that the data is all zeros.

### 17.2) Out-of-Bounds Protection

**File:** `robustness/oob_protection.html`
**Covers:** `TODO.md #182`
**Description:** A collection of negative tests that attempt to violate bounds checks. This includes `copyBufferToBuffer` with an out-of-bounds source/destination offset, `setVertexBuffer` with an out-of-bounds offset, and `getMappedRange` with an out-of-bounds offset. All are expected to generate validation errors.

### 17.3) Long-Running Shader

**File:** `robustness/long_running_shader.html`
**Covers:** `TODO.md #185`
**Description:** This test runs a compute shader with a massive dispatch size and a loop that performs a high number of calculations. The goal is to test the driver's timeout detection and recovery (TDR). The expected outcome is a device loss.

## 18) WGSL Language Features & Builtins

### 18.1) Subgroups Feature

**File:** `wgsl/subgroups.html`
**Covers:** `TODO.md #190`
**Description:** If the `"subgroups"` feature is enabled, this test runs a compute shader that uses subgroup built-ins like `@builtin(subgroup_invocation_id)` and `@builtin(subgroup_size)`. It performs a subgroup-wide reduction (e.g., sum) and verifies the result.

### 18.2) Math Builtins Edge Cases

**File:** `wgsl/math_builtins.html`
**Covers:** `TODO.md #32`
**Description:** This compute shader test feeds edge-case values (NaN, Infinity, 0.0, subnormals) into various WGSL math built-in functions (`sqrt`, `log`, `atan2`, etc.) and reads back the results to check for spec-compliant behavior.

## 19) Texture Format Coverage (GPUTextureFormat)

### 19.1) All Formats as Sampled Texture

**File:** `formats/sampling.html`
**Covers:** `TODO.md #195`
**Description:** This test iterates through a list of all non-depth/stencil `GPUTextureFormat`s. For each format, it creates a texture, uploads some data, and then samples it in a simple fragment shader to ensure it can be read from.

### 19.2) All Formats as Renderable Attachment

**File:** `formats/rendering.html`
**Covers:** `TODO.md #195`
**Description:** Iterates through all color `GPUTextureFormat`s that have the `"render-attachment"` capability. For each, it creates a texture and uses it as a `colorAttachment` in a `GPURenderPassDescriptor`, rendering a simple triangle to it.

## 20) Copy/Blit Edge Cases

### 20.1) `bytesPerRow` Alignment

**File:** `copies/bytes_per_row.html`
**Covers:** `TODO.md #206`
**Description:** This test uses `writeTexture` with `bytesPerRow` values that are not the tightly-packed minimum. It creates a source `ArrayBuffer` with padding between rows and verifies that the data is correctly unpacked and uploaded to the destination texture. Includes negative tests for `bytesPerRow` not aligned to 256.

### 20.2) Compressed Texture Copies

**File:** `copies/compressed_copies.html`
**Covers:** `TODO.md #207`
**Description:** If a compressed texture format is available, this test performs a `copyTextureToTexture` operation. It includes a negative test where the copy `width` or `height` is not a multiple of the compression block size, which should trigger a validation error.

## 21) Draw/Dispatch Variants

### 21.1) All Draw Call Variants

**File:** `draw/all_draws.html`
**Covers:** `TODO.md #213`
**Description:** This test demonstrates all four basic drawing commands: `draw`, `drawIndexed`, `drawIndirect`, and `drawIndexedIndirect`.

### 21.2) `setVertexBuffer` Null to Unset

**File:** `draw/set_vertex_buffer_null.html`
**Covers:** `TODO.md #217`
**Description:** This test first sets a valid vertex buffer on slot 0 and draws. It then calls `setVertexBuffer(0, null)` to clear the binding and attempts to draw again, which should fail validation if the pipeline requires that buffer.

### 21.3) Dynamic State

**File:** `draw/dynamic_state.html`
**Covers:** `TODO.md #218`
**Description:** Inside a single `GPURenderPassEncoder`, this test changes dynamic state between draw calls. It calls `setViewport`, `setScissorRect`, `setBlendConstant`, and `setStencilReference` multiple times to draw primitives with different state properties.

## 22) Cross-Object State and Lifetime

### 22.1) Contagious Invalidity

**File:** `lifetime/contagious_invalidity.html`
**Covers:** `TODO.md #221`
**Description:** This test creates an invalid `GPUBindGroupLayout`. It then attempts to create a `GPUPipelineLayout` and a `GPUBindGroup` from it. It asserts that both of these subsequent creations also fail, demonstrating that invalidity propagates.

### 22.2) Using Destroyed Resources

**File:** `lifetime/use_destroyed.html`
**Covers:** `TODO.md #222`
**Description:** A collection of negative tests. It creates various resources (buffer, texture, bind group), destroys them, and then attempts to use them in an encoder (`setBindGroup`, `setVertexBuffer`, etc.). All uses after destroy should generate validation errors.

## 23) Ordering and Synchronization

### 23.1) `mapAsync` vs `onSubmittedWorkDone`

**File:** `sync/map_vs_work_done.html`
**Covers:** `TODO.md #227`
**Description:** This test submits work that writes to a buffer, then immediately calls `mapAsync` on the buffer *without* waiting for `onSubmittedWorkDone`. It verifies that the `mapAsync` promise does not resolve until after the `onSubmittedWorkDone` promise, demonstrating the implicit synchronization.

## 24) Labels and Debug Info

### 24.1) Object Labels

**File:** `debug/labels.html`
**Covers:** `TODO.md #232`
**Description:** This test creates one of each major GPU object type (GPUBuffer, GPUTexture, GPURenderPipeline, etc.) and assigns a unique `label` to it. While not directly verifiable, these labels are invaluable for debugging and should appear in browser devtools and error messages.

## 25) Debug Markers & Groups (GPUDebugCommandsMixin)

### 25.1) Debug Groups and Markers

**File:** `debug/markers_and_groups.html`
**Covers:** `TODO.md #236-237`
**Description:** In a command encoder, this test uses `pushDebugGroup` and `popDebugGroup` to create a hierarchy of debug regions. Inside these groups, it uses `insertDebugMarker` to label specific points in the command stream. This is primarily for use with external graphics debuggers.

## 26) Render Bundles (GPURenderBundleEncoder)

### 26.1) Basic Render Bundle

**File:** `bundles/basic_bundle.html`
**Covers:** `TODO.md #27`
**Description:** Creates a `GPURenderBundleEncoder`, records a few draw commands into it (e.g., set pipeline, set bind groups, draw), and calls `finish()` to get a `GPURenderBundle`. This bundle is then executed in a render pass.

### 26.2) Disallowed Commands in Bundle

**File:** `bundles/disallowed_commands.html`
**Covers:** `TODO.md #27`
**Description:** This negative test attempts to call a command that is not allowed inside a render bundle, such as `setViewport`. It asserts that this generates an immediate validation error.

## 27) Pipeline-overridable Constants

### 27.1) Using Overridable Constants

**File:** `pipelines/overridable_constants.html`
**Covers:** `TODO.md #28`
**Description:** Defines a shader with an overridable constant (`override my_id: f32;`). It then creates a pipeline, providing a value for `my_id` in the `constants` dictionary. The shader uses this constant, and the test verifies the output.

### 27.2) Invalid Constant Override

**File:** `pipelines/invalid_constant_override.html`
**Covers:** `TODO.md #28`
**Description:** This negative test attempts to create a pipeline but provides a value for a constant identifier that does not exist in the shader code. It asserts that pipeline creation fails.

## 28) Multi-threading and Worker Support

### 28.1) OffscreenCanvas in Worker

**File:** `workers/offscreen_canvas.html`
**Covers:** `TODO.md #29`
**Description:** The main thread creates a worker and transfers an `OffscreenCanvas` to it. The worker then performs all WebGPU initialization, rendering, and presentation to the offscreen canvas, demonstrating end-to-end rendering off the main thread.

### 28.2) Encoding in Worker, Submit on Main

**File:** `workers/encode_in_worker.html`
**Covers:** `TODO.md #29`
**Description:** The main thread creates the `GPUDevice` and shares it with a worker. The worker creates a `GPUCommandEncoder`, records commands, and calls `finish()`. The resulting `GPUCommandBuffer` is transferred back to the main thread to be submitted to the queue.

## 29) WGSL Atomics and Synchronization

### 29.1) Atomic Add on Storage Buffer

**File:** `wgsl/atomics.html`
**Covers:** `TODO.md #30`
**Description:** A compute shader is dispatched with many workgroups that all use `atomicAdd` to increment a counter in a storage buffer. After the dispatch, the final value of the atomic counter is read back and verified to be the total number of invocations.

### 29.2) `workgroupBarrier`

**File:** `wgsl/workgroup_barrier.html`
**Covers:** `TODO.md #30`
**Description:** This test uses `workgroupBarrier()` to synchronize invocations within a workgroup. Invocations write data to `workgroup` memory, call the barrier, and then read data written by *other* invocations in the same workgroup to verify that the writes were visible.

## 30) Implicit Pipeline Layouts

### 30.1) `auto` Layout

**File:** `pipelines/auto_layout.html`
**Covers:** `TODO.md #31`
**Description:** Creates a render pipeline with `layout: 'auto'`. After creation, it inspects the pipeline's `getBindGroupLayout(0)` to retrieve the implicitly generated layout, which is then used to create a compatible `GPUBindGroup`.

## 31) Finalizing Document

This completes the generation of the `TESTCASES.md` file. It now contains a comprehensive list of test cases covering the entire WebGPU API surface as detailed in the `TODO.md` file.
