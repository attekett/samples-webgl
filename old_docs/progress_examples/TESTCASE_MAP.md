# WebGPU Progressive Test Case Map

This document outlines a progressive, layered approach to the WebGPU fuzzing corpus. Each test case is a standalone, runnable HTML file that builds upon the concepts of the previous one, resulting in a clear visual output and testing a specific combination of interacting API features. All tests are "positive," meaning they are expected to run without validation errors.

## Mutation-Based Fuzzing Variations

To support effective mutation-based fuzzing, test cases include explicit variations of enumerated values that the fuzzer can mutate but cannot invent. This includes:

- **Texture Dimensions**: `"1d"`, `"2d"`, `"3d"` variants
- **Texture Formats**: Common formats like `"rgba8unorm"`, `"bgra8unorm"`, `"depth24plus"`, etc.
- **Primitive Topologies**: `"point-list"`, `"line-list"`, `"line-strip"`, `"triangle-list"`, `"triangle-strip"`
- **Compare Functions**: `"never"`, `"less"`, `"equal"`, `"less-equal"`, `"greater"`, `"not-equal"`, `"greater-equal"`, `"always"`
- **Buffer Usage Flags**: `VERTEX`, `INDEX`, `UNIFORM`, `STORAGE`, `INDIRECT`, `QUERY_RESOLVE`
- **Texture Usage Flags**: `COPY_SRC`, `COPY_DST`, `TEXTURE_BINDING`, `STORAGE_BINDING`, `RENDER_ATTACHMENT`
- **Address Modes**: `"clamp-to-edge"`, `"repeat"`, `"mirror-repeat"`
- **Filter Modes**: `"nearest"`, `"linear"`

---

### **1. `01_basic_triangle.html`**
*   **Goal:** The "hello world" of WebGPU. Establishes the minimum boilerplate for rendering.
*   **Visual:** A single, solid-colored triangle.
*   **Features Covered:**
    *   **Initialization:** `navigator.gpu`, `requestAdapter`, `requestDevice`.
    *   **Canvas:** Get context, `getPreferredCanvasFormat`, `configure`.
    *   **Shaders:** A minimal WGSL vertex and fragment shader.
    *   **Buffers:** `createBuffer` for a single, hardcoded vertex buffer.
    *   **Pipelines:** `createShaderModule`, `createRenderPipeline` with a basic vertex layout.
    *   **Commands:** `createCommandEncoder`, `beginRenderPass`, `setPipeline`, `setVertexBuffer`, `draw`, `finish`.
    *   **Queue:** `submit` a single command buffer.
    *   **Presentation:** `getCurrentTexture` and rendering to its view.

---

### **2. `02_textured_cube.html`**
*   **Goal:** Introduce textures, samplers, uniform buffers for transformations, and index buffers.
*   **Visual:** A 3D cube rotating, with an image texture applied to its faces.
*   **Builds On:** `01_basic_triangle.html`
*   **New Features Covered:**
    *   **Buffers:**
        *   Adds an **index buffer** (`GPUBufferUsage.INDEX`).
        *   Adds a **uniform buffer** (`GPUBufferUsage.UNIFORM`) for a model-view-projection matrix.
        *   Uses `queue.writeBuffer` to update the uniform buffer each frame.
    *   **Textures & Samplers:**
        *   `createTexture` for a 2D texture with `dimension: "2d"`.
        *   `queue.writeTexture` or `copyExternalImageToTexture` to upload image data.
        *   `createSampler` for basic texture sampling (`magFilter: "linear"`, `minFilter: "linear"`).
    *   **Binding:**
        *   `createBindGroupLayout` defining a uniform buffer, texture, and sampler.
        *   `createBindGroup` to bind the created resources.
        *   `createPipelineLayout` using the bind group layout.
    *   **Commands:** `setIndexBuffer`, `setBindGroup`.
    *   **Drawing:** `drawIndexed`.

### **2a. `02a_texture_dimensions.html`**
*   **Goal:** Provide texture dimension variations for mutation fuzzing.
*   **Visual:** Multiple objects demonstrating different texture dimensions.
*   **Builds On:** `02_textured_cube.html`
*   **Fuzzing Variations:**
    *   **1D Texture:** `dimension: "1d"` with gradient data
    *   **2D Texture:** `dimension: "2d"` with standard image data  
    *   **3D Texture:** `dimension: "3d"` with volumetric data
    *   **Format Variants:** `"rgba8unorm"`, `"bgra8unorm"`, `"r8unorm"`, `"rg8unorm"`
    *   **Usage Combinations:** `TEXTURE_BINDING`, `TEXTURE_BINDING | COPY_DST`, `STORAGE_BINDING`

### **2b. `02b_sampler_variations.html`**
*   **Goal:** Provide sampler configuration variations for mutation fuzzing.
*   **Visual:** Grid showing different sampling modes applied to the same texture.
*   **Builds On:** `02_textured_cube.html`
*   **Fuzzing Variations:**
    *   **Address Modes:** `"clamp-to-edge"`, `"repeat"`, `"mirror-repeat"`
    *   **Filter Modes:** `"nearest"`, `"linear"`
    *   **Mipmap Modes:** `"nearest"`, `"linear"`
    *   **Compare Functions:** `"never"`, `"less"`, `"equal"`, `"less-equal"`, `"greater"`, `"not-equal"`, `"greater-equal"`, `"always"`

---

### **3. `03_instancing.html`**
*   **Goal:** Demonstrate high-efficiency drawing of many similar objects using instancing.
*   **Visual:** Thousands of cubes, each with a different color and position, drawn with a single command.
*   **Builds On:** `02_textured_cube.html`
*   **New Features Covered:**
    *   **Buffers:**
        *   Adds a **storage buffer** (`GPUBufferUsage.STORAGE`) to hold per-instance data (e.g., position, color).
    *   **Pipelines:**
        *   Modifies the vertex buffer layout in `createRenderPipeline` to include an instance-stepped buffer.
    *   **WGSL:**
        *   Vertex shader reads per-instance attributes from the storage buffer using `@builtin(instance_index)`.
    *   **Binding:**
        *   Adds the storage buffer to the `GPUBindGroupLayout` and `GPUBindGroup`.
    *   **Drawing:** `drawIndexed` with the `instanceCount` parameter set to a large number.

### **3a. `03a_primitive_topologies.html`**
*   **Goal:** Provide primitive topology variations for mutation fuzzing.
*   **Visual:** Different sections showing various primitive types.
*   **Builds On:** `03_instancing.html`
*   **Fuzzing Variations:**
    *   **Point Rendering:** `topology: "point-list"` with large point sprites
    *   **Line Rendering:** `topology: "line-list"` connecting instance positions
    *   **Line Strip:** `topology: "line-strip"` creating continuous paths
    *   **Triangle List:** `topology: "triangle-list"` (default cube rendering)
    *   **Triangle Strip:** `topology: "triangle-strip"` for efficient triangle fans

### **3b. `03b_buffer_usage_combinations.html`**
*   **Goal:** Provide buffer usage flag combinations for mutation fuzzing.
*   **Visual:** Instance data rendered with different buffer configurations.
*   **Builds On:** `03_instancing.html`
*   **Fuzzing Variations:**
    *   **Vertex Buffer:** `GPUBufferUsage.VERTEX`
    *   **Index Buffer:** `GPUBufferUsage.INDEX`
    *   **Uniform Buffer:** `GPUBufferUsage.UNIFORM`
    *   **Storage Buffer:** `GPUBufferUsage.STORAGE`
    *   **Combined Usage:** `GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST`
    *   **Indirect Buffer:** `GPUBufferUsage.INDIRECT | GPUBufferUsage.COPY_DST`

---

### **4. `04_compute_particles.html`**
*   **Goal:** Showcase a compute-to-render workflow, using a compute shader for simulation.
*   **Visual:** A dynamic field of thousands of particles moving according to a simulation.
*   **Builds On:** Concepts from `03_instancing.html`.
*   **New Features Covered:**
    *   **Pipelines:**
        *   `createComputePipeline` for the particle simulation.
    *   **Buffers:**
        *   Uses two storage buffers to read particle positions from one and write updated positions to the other (ping-pong technique).
    *   **WGSL:**
        *   A `@compute` shader that updates particle positions based on velocity and time.
        *   A vertex shader that reads particle positions for rendering (`point-list` topology).
    *   **Binding:**
        *   Separate bind groups for the compute and render passes.
    *   **Commands:**
        *   `beginComputePass`, `setPipeline` (compute), `dispatchWorkgroups`.
    *   **Synchronization:** Demonstrates the implicit barrier between a compute pass and a subsequent render pass in the same command buffer.

---

### **5. `05_depth_and_msaa.html`**
*   **Goal:** Implement correct 3D scene rendering with occlusion and anti-aliasing.
*   **Visual:** Several overlapping 3D objects, correctly sorted by depth, with smooth edges.
*   **Builds On:** `02_textured_cube.html`
*   **New Features Covered:**
    *   **Textures:**
        *   `createTexture` for a depth texture (`format: "depth24plus"`).
        *   `createTexture` for a multisampled color texture (`sampleCount: 4`).
    *   **Pipelines:**
        *   `createRenderPipeline` with a `depthStencil` state (enabling `depthWriteEnabled: true` and `depthCompare: "less"`).
        *   `createRenderPipeline` with a `multisample` state.
    *   **Commands:**
        *   `beginRenderPass` with `depthStencilAttachment` and a `resolveTarget`.

### **5a. `05a_depth_formats.html`**
*   **Goal:** Provide depth texture format variations for mutation fuzzing.
*   **Visual:** Same scene rendered with different depth formats.
*   **Builds On:** `05_depth_and_msaa.html`
*   **Fuzzing Variations:**
    *   **Depth Formats:** `"depth16unorm"`, `"depth24plus"`, `"depth32float"`
    *   **Depth-Stencil Formats:** `"depth24plus-stencil8"`, `"depth32float-stencil8"`
    *   **Compare Functions:** `"never"`, `"less"`, `"equal"`, `"less-equal"`, `"greater"`, `"not-equal"`, `"greater-equal"`, `"always"`
    *   **Depth Write:** `depthWriteEnabled: true`, `depthWriteEnabled: false`

### **5b. `05b_multisample_variations.html`**
*   **Goal:** Provide multisampling variations for mutation fuzzing.
*   **Visual:** Same scene with different MSAA settings.
*   **Builds On:** `05_depth_and_msaa.html`
*   **Fuzzing Variations:**
    *   **Sample Counts:** `sampleCount: 1`, `sampleCount: 2`, `sampleCount: 4`, `sampleCount: 8`
    *   **Alpha to Coverage:** `alphaToCoverageEnabled: true`, `alphaToCoverageEnabled: false`
    *   **Sample Masks:** `0xFFFFFFFF`, `0x0F0F0F0F`, `0x33333333`

---

### **6. `06_render_to_texture.html`**
*   **Goal:** Demonstrate rendering to an offscreen texture (framebuffer object).
*   **Visual:** A main 3D scene that includes a cube, where the faces of the cube display a different, animated scene that was rendered separately.
*   **Builds On:** `02_textured_cube.html`, `05_depth_and_msaa.html`
*   **New Features Covered:**
    *   **Resources:**
        *   Creates a renderable color texture (`GPUTextureUsage.RENDER_ATTACHMENT`) and a corresponding depth texture.
    *   **Binding:**
        *   Uses the offscreen color texture as a sampled `texture` in a bind group for the main scene.
    *   **Commands:**
        *   **Pass 1:** A `GPURenderPassEncoder` that renders the secondary scene into the offscreen texture.
        *   **Pass 2:** A `GPURenderPassEncoder` that renders the main scene to the canvas, sampling from the texture created in Pass 1.

---

### **7. `07_worker_rendering.html`**
*   **Goal:** Move all GPU operations to a Web Worker to avoid blocking the main thread.
*   **Visual:** Any of the previous scenes (e.g., the textured cube), but with all rendering logic handled by a worker.
*   **Builds On:** `02_textured_cube.html`
*   **New Features Covered:**
    *   **Workers:**
        *   Main thread creates a `Worker`.
        *   Main thread gets an `OffscreenCanvas` from the main canvas and transfers it to the worker.
    *   **Worker Logic:**
        *   The worker script initializes the `GPUDevice`, creates all resources, and runs the render loop, presenting directly to the `OffscreenCanvas`.

---

### **8. `08_video_texture.html`**
*   **Goal:** Showcase real-time video processing by importing video frames as textures.
*   **Visual:** A 3D object in the scene that has a playing video mapped onto its surface.
*   **Builds On:** `02_textured_cube.html`
*   **New Features Covered:**
    *   **External Textures:**
        *   Uses an HTML `<video>` element.
        *   In the render loop, calls `importExternalTexture` with the video element.
    *   **Binding:**
        *   The `GPUExternalTexture` is used in a `GPUBindGroup`.
    *   **WGSL:**
        *   The fragment shader samples from the external texture.

---

## Fuzzing Variation Strategy

The enhanced test corpus provides explicit enumerated value variations that are critical for mutation-based fuzzing effectiveness. Each "variation" test case focuses on providing multiple instances of WebGPU enums and flags that a mutational fuzzer can modify but cannot invent.

### Key Variation Test Cases Added:

1. **`01a_primitive_variations.html`** - All primitive topologies in one test
2. **`01b_texture_format_variations.html`** - Multiple texture formats demonstrated
3. **`01c_texture_dimension_variations.html`** - 1D, 2D, and 3D texture examples
4. **`02a_texture_dimensions.html`** - Advanced texture dimension patterns
5. **`02b_sampler_variations.html`** - Comprehensive sampler configurations
6. **`03a_primitive_topologies.html`** - Primitive types with instancing
7. **`03b_buffer_usage_combinations.html`** - Buffer usage flag combinations
8. **`05a_depth_formats.html`** - Depth texture format variations
9. **`05b_multisample_variations.html`** - MSAA configuration options

### Fuzzing Benefits:

- **Enum Coverage:** Each variation provides multiple values for WebGPU enums like `GPUPrimitiveTopology`, `GPUTextureFormat`, `GPUTextureDimension`
- **Flag Combinations:** Tests include various usage flag combinations for buffers and textures
- **Parameter Variations:** Different sampler configurations, compare functions, and filter modes
- **Format Compatibility:** Tests demonstrate which formats work with which features
- **Dimension Constraints:** Shows proper usage patterns for 1D, 2D, and 3D textures

This approach ensures that mutation-based fuzzers have rich source material to modify, leading to better API coverage and edge case discovery.
