# WebGL/WebGL2 Fuzzing Implementation Plan

## Overview

This document defines the implementation plan for the WebGL/WebGL2 **mutation-based fuzzing corpus**. The goal is to create **high-biomass, complex seed files** that provide rich surface area for mutation-based fuzzing through "spaghetti-like" valid resource usage patterns.

**CRITICAL DISTINCTION:** This is NOT a conformance suite. This is a fuzzing corpus designed specifically for mutation-based testing where the mutator can find crashes by twisting complex, valid WebGL state machines into invalid ones.

**Design Principles:**
1.  **Complexity over Isolation**: Seeds should combine multiple features ("spaghetti code") rather than testing features in isolation. A mutator acting on a "Unit Test" makes a "Broken Unit Test". A mutator acting on a "Complex Narrative" makes a "Security Vulnerability".
2.  **State Poisoning**: Every seed must include redundant state changes (binding/unbinding, enabling/disabling) to create fragile state machines that the mutator can break.
3.  **Variable Exposure**: Mix inline literals with parameterized variables to give the mutator easy targets for mutation while maintaining code readability.
4.  **Resource Lifecycle Stress**: Create, share, and delete resources in complex patterns to expose use-after-free and state corruption vulnerabilities.
5.  **Shader Biomass**: Use maximal shaders (many uniforms, attributes, unused functions) even for simple geometry to stress shader compilers.

**WebGL-Specific Goals:**
- **State Machine Stress**: Heavy interleaving of drawing, binding, and state changing operations to create fragile state machines.
- **Resource Coupling**: Share resources (buffers, textures) across multiple unrelated operations with complex lifetime patterns.
- **Extension Interactions**: Force interaction between disparate extensions (e.g., MRT + Float Textures + Instancing) in single seeds.
- **Mutation Surface Area**: Expose variables and inline constants that mutators can easily find and corrupt.

## Specification Coverage Analysis

Based on WebGL 1.0 and WebGL 2.0 specifications:

### WebGL 1.0 Core Features
- Context creation and management
- Shader compilation (vertex/fragment)
- Program linking and uniform binding
- Buffer objects (vertex, index, pixel)
- Texture objects (2D, cube maps)
- Framebuffer objects and renderbuffers
- Vertex arrays and attribute binding
- Drawing operations (arrays, elements)
- State management (blending, depth, stencil, scissor)
- Pixel operations (readPixels, pixelStore)

### WebGL 2.0 Exclusive Features
- 3D textures and texture arrays
- Multiple render targets (MRT)
- Uniform buffer objects (UBO)
- Transform feedback
- Vertex array objects (VAO) - core in WebGL2
- Sampler objects
- Query objects (occlusion, timer)
- Sync objects
- Instanced rendering - core in WebGL2
- Integer textures and attributes
- Advanced blend modes and equations

### Extension Coverage
- OES_texture_float, OES_texture_half_float
- WEBGL_draw_buffers, WEBGL_color_buffer_float
- OES_vertex_array_object (WebGL1), ANGLE_instanced_arrays
- EXT_shader_texture_lod, OES_standard_derivatives
- WEBGL_depth_texture, EXT_frag_depth

## Implementation Categories

The corpus is organized into categories based on WebGL capabilities and execution patterns. Categories are ordered by fuzzing priority, with integrated "kitchen sink" seeds first.

---

## Category 0: Integrated Pipelines (Kitchen Sink Seeds - HIGHEST PRIORITY)

### 0.1 The Ultimate Spaghetti Seeds

#### WEBGL-SEED-001: The Monolith
- **File:** `integrated/monolith_extreme.html`
- **Seed Logic:** Complete WebGL pipeline with maximum feature integration - MRT + Float Textures + Instancing + UBOs + Transform Feedback in single seed
- **Biomass:** Massive state machine with 50+ state changes, 10+ resource bindings, 5+ shader programs, heavy extension interactions
- **Variables to Expose:** textureSize, instanceCount, bufferSize, uniformBlockIndex, maxIterations
- **State Poisoning:** Bind/unbind all resources 3x each, enable/disable every capability randomly

#### WEBGL-SEED-002: Resource Lifecycle Nightmare
- **File:** `integrated/resource_zombie_farm.html`
- **Seed Logic:** Create 100 textures/buffers, delete evens, rebind odds, attempt operations on deleted handles, orphan buffers repeatedly
- **Biomass:** Resource manager stress with UAF patterns, handle validation logic, memory management edge cases
- **Variables to Expose:** resourceCount, deletePattern, rebindAttempts, orphanCycles
- **State Poisoning:** Bind deleted handles, mix valid/invalid operations, stress reference counting

#### WEBGL-SEED-003: Shader Compiler Torture
- **File:** `integrated/shader_maximalist.html`
- **Seed Logic:** Mega-shader with 50 uniforms, 20 attributes, unused functions, nested loops, precision mixing, derivatives - applied to simple geometry
- **Biomass:** Compiler register pressure, optimization stress, precision boundary testing
- **Variables to Expose:** uniformCount, attributeCount, loopIterations, precisionMix
- **State Poisoning:** Multiple program switches, uniform updates between draws, shader recompilation

### 0.2 Multi-Pass Kitchen Sinks

#### WEBGL-SEED-004: Ping-Pong Pipeline
- **File:** `integrated/ping_pong_extreme.html`
- **Seed Logic:** 10-pass render-to-texture chain with MRT, blending, instancing, and feedback loops
- **Biomass:** Deep dependency chains, texture barrier logic, complex shader interactions across passes
- **Variables to Expose:** passCount, texturePingPong, blendMode, instanceMultiplier
- **State Poisoning:** FBO switching, texture unit cycling, blend equation changes between passes

#### WEBGL-SEED-005: Extension Orgasm
- **File:** `integrated/extension_combination.html`
- **Seed Logic:** Combine every available extension (Float + MRT + VAO + Instancing + Depth Texture) in single complex scene
- **Biomass:** Extension interoperability stress, capability interactions, fallback logic
- **Variables to Expose:** extensionCount, featureCombination, fallbackMode
- **State Poisoning:** Extension-dependent state changes, capability toggling based on extension availability

---


## Category 1: Rendering Complexities

### 1.1 Multi-Pass Feedback Loops

#### WEBGL-CPLX-001: Ping-Pong Texturing
- **File:** `complex/ping_pong_feedback.html`
- **Seed Logic:** Texture A->FBO1, Texture B->FBO2, draw to FBO1 reading TexB, draw to FBO2 reading TexA, swap and repeat 50x, add blending and state changes between passes.
- **Biomass:** Deep dependency chain, texture barrier logic, render state transitions.
- **Variables to Expose:** pingPongPasses, textureWidth, blendEquation, stateChangeCount.

#### WEBGL-CPLX-002: The G-Buffer (MRT + Instancing)
- **File:** `complex/gbuffer_mrt_instanced.html`
- **Seed Logic:** Setup MRT (4 targets: Color/Normal/Depth/ID), drawArraysInstanced 1000 spheres, shader writes to all targets with complex math, blit to screen, redundant MRT state changes.
- **Biomass:** High bandwidth, multiple output streams, instance data processing, MRT state management.
- **Variables to Expose:** instanceCount, mrtTargets, sphereRadius, shaderComplexity.

### 1.2 Shader Stress

#### WEBGL-SHADER-001: The "Megashader"
- **File:** `shaders/megashader_stress.html`
- **Seed Logic:** Generate vertex grid, fragment shader with 50 uniforms, deep if/else nesting, loops, gl_FragCoord dependencies, unused functions, precision mixing, multiple program switches.
- **Biomass:** Compiler register pressure, instruction cache usage, optimization prevention.
- **Variables to Expose:** uniformCount, nestDepth, loopCount, fragCoordUsage.

#### WEBGL-SHADER-002: Precision Torture
- **File:** `shaders/precision_torture.html`
- **Seed Logic:** Mix highp/mediump/lowp in calculations, math near zero/MAX_VALUE, use fract/pow/exp, precision conversions, boundary value stressing.
- **Biomass:** ALU logic, floating point behavior, precision boundary testing.
- **Variables to Expose:** precisionMix, boundaryValue, mathOperations, conversionCount.

---

## Category 2: Advanced WebGL Features

### 2.1 WebGL Extensions

#### WEBGL-EXT-001: Float Textures
- **File:** `extensions/float_textures.html`
- **Features:** `OES_texture_float`, `OES_texture_half_float`, floating-point textures
- **Seed Logic:** HDR rendering with float precision, tone mapping, combine with MRT and instancing, redundant texture format changes
- **Biomass:** Float precision handling, texture format validation, extension interaction
- **Variables to Expose:** floatFormat, precisionLevel, toneMapGamma, textureFiltering

#### WEBGL-EXT-002: Vertex Array Objects (WebGL1)
- **File:** `extensions/vertex_arrays_webgl1.html`
- **Features:** `OES_vertex_array_object`, VAO management, state capture
- **Seed Logic:** Complex geometry with multiple VAOs, state switching, redundant VAO creation/deletion, mix with instancing, state preservation stress
- **Biomass:** VAO state management, attribute binding complexity, extension state transitions
- **Variables to Expose:** vaoCount, attributeConfigs, stateSwitchCount, bindingPattern

#### WEBGL-EXT-003: Instanced Rendering (WebGL1)
- **File:** `extensions/instanced_rendering_webgl1.html`
- **Features:** `ANGLE_instanced_arrays`, `drawArraysInstancedANGLE()`, `drawElementsInstancedANGLE()`
- **Seed Logic:** Instanced geometry with particle systems, varying instance divisors, redundant attribute setup, combine with VAOs and textures
- **Biomass:** Instance data processing, divisor logic, attribute management
- **Variables to Expose:** instanceCount, divisorValue, attributeSetup, drawMode

#### WEBGL-EXT-004: Multiple Render Targets (WebGL1)
- **File:** `extensions/multiple_rendertargets_webgl1.html`
- **Features:** `WEBGL_draw_buffers`, `drawBuffersWEBGL()`, MRT extension
- **Seed Logic:** Deferred rendering with multiple color outputs, redundant draw buffer changes, blend mode combinations, MRT state switching
- **Biomass:** MRT state management, draw buffer validation, blend equation interactions
- **Variables to Expose:** mrtTargets, drawBuffers, blendMode, attachmentCount

#### WEBGL-EXT-005: Depth Textures
- **File:** `extensions/depth_textures.html`
- **Features:** `WEBGL_depth_texture`, depth texture formats, shadow mapping
- **Visual:** Shadow mapping with depth texture sampling
- **Fuzz Points:** Depth formats (DEPTH_COMPONENT, DEPTH_STENCIL), comparison modes

#### WEBGL-EXT-006: Shader Derivatives
- **File:** `extensions/shader_derivatives.html`
- **Features:** `OES_standard_derivatives`, `dFdx()`, `dFdy()`, `fwidth()`
- **Visual:** Edge detection and anti-aliasing using derivatives
- **Fuzz Points:** Derivative functions, LOD calculations, precision effects

#### WEBGL-EXT-007: Element Index Uint
- **File:** `extensions/element_index_uint.html`
- **Features:** `OES_element_index_uint`, 32-bit indices, large geometries
- **Visual:** High-polygon models using 32-bit indexing
- **Fuzz Points:** Uint32Array indices, large index ranges, primitive counts

### 2.2 WebGL2 Exclusive Features

#### WEBGL2-FEATURE-001: Uniform Buffer Objects
- **File:** `webgl2/uniform_buffers.html`
- **Features:** UBO binding, `uniformBlockBinding()`, `bindBufferBase()`, uniform blocks
- **Visual:** Complex shader with shared uniform data across programs
- **Fuzz Points:** Block bindings, uniform layouts, buffer offsets, block indices

#### WEBGL2-FEATURE-002: Transform Feedback
- **File:** `webgl2/transform_feedback.html`
- **Features:** `createTransformFeedback()`, `beginTransformFeedback()`, vertex capture, `transformFeedbackVaryings()`
- **Visual:** GPU-generated geometry streams and particle simulations
- **Fuzz Points:** Varying capture, buffer modes (INTERLEAVED_ATTRIBS, SEPARATE_ATTRIBS), primitive modes

#### WEBGL2-FEATURE-003: Vertex Array Objects (Core)
- **File:** `webgl2/vertex_arrays_core.html`
- **Features:** Native VAO support, `createVertexArray()`, `bindVertexArray()`
- **Visual:** Advanced geometry management with multiple VAO configurations
- **Fuzz Points:** VAO state isolation, attribute pointer management, binding stacks

#### WEBGL2-FEATURE-004: 3D Textures
- **File:** `webgl2/textures_3d.html`
- **Features:** `texImage3D()`, `TEXTURE_3D`, 3D texture sampling, `TEXTURE_WRAP_R`
- **Visual:** Volume rendering and 3D texture visualization
- **Fuzz Points:** 3D texture dimensions, depth coordinates, wrap modes

#### WEBGL2-FEATURE-005: Texture Arrays
- **File:** `webgl2/texture_arrays.html`
- **Features:** `TEXTURE_2D_ARRAY`, array textures, `texImage3D()` for arrays
- **Visual:** Multi-layer texture effects (terrain, animations)
- **Fuzz Points:** Array layers, layer indexing, array textures vs 3D textures

#### WEBGL2-FEATURE-006: Sampler Objects
- **File:** `webgl2/sampler_objects.html`
- **Features:** `createSampler()`, `bindSampler()`, `samplerParameteri()`, separate sampler state
- **Visual:** Texture parameter comparison with different samplers
- **Fuzz Points:** Sampler parameters, texture/sampler separation, parameter inheritance

#### WEBGL2-FEATURE-007: Query Objects
- **File:** `webgl2/query_objects.html`
- **Features:** `createQuery()`, `beginQuery()`, `endQuery()`, occlusion queries, timer queries
- **Visual:** Query result visualization and performance monitoring
- **Fuzz Points:** Query targets (ANY_SAMPLES_PASSED, TIME_ELAPSED), result availability

#### WEBGL2-FEATURE-008: Sync Objects
- **File:** `webgl2/sync_objects.html`
- **Features:** `fenceSync()`, `clientWaitSync()`, `waitSync()`, synchronization primitives
- **Visual:** GPU-CPU synchronization visualization
- **Fuzz Points:** Sync conditions, wait timeouts, flush commands

#### WEBGL2-FEATURE-009: Instanced Rendering (Core)
- **File:** `webgl2/instanced_rendering_core.html`
- **Features:** Native `drawArraysInstanced()`, `drawElementsInstanced()`, `vertexAttribDivisor()`
- **Visual:** Advanced instanced rendering with divisor control
- **Fuzz Points:** Instance divisors, attribute indexing, instance counts

#### WEBGL2-FEATURE-010: Integer Textures and Attributes
- **File:** `webgl2/integer_textures_attributes.html`
- **Features:** Integer textures, integer vertex attributes, integer uniforms
- **Visual:** Data visualization using integer textures and attributes
- **Fuzz Points:** Integer formats (R32I, RG16UI), signed/unsigned variants, precision handling

---

## Category 3: Complex Multi-Pass Scenarios

### 3.1 Render-to-Texture Pipelines

#### WEBGL-MULTIPASS-001: Post-Processing Chain
- **File:** `multipass/post_processing.html`
- **Features:** Multiple FBOs, shader chaining, render-to-texture pipeline
- **Visual:** Scene → blur → bloom → tone mapping → final composite
- **Fuzz Points:** Render target switching, shader combinations, texture sampling chains

#### WEBGL-MULTIPASS-002: Shadow Mapping
- **File:** `multipass/shadow_mapping.html`
- **Features:** Depth textures, projective texturing, shadow comparison, `TEXTURE_COMPARE_MODE`
- **Visual:** 3D scene with dynamic shadows from multiple light sources
- **Fuzz Points:** Light matrices, depth comparison modes, shadow bias, PCF filtering

#### WEBGL-MULTIPASS-003: Deferred Rendering
- **File:** `multipass/deferred_rendering.html`
- **Features:** G-buffer (position, normal, albedo), lighting passes, MRT
- **Visual:** Complex lighting with multiple light sources and materials
- **Fuzz Points:** G-buffer layouts, lighting equations, accumulation blending

#### WEBGL-MULTIPASS-004: Screen Space Effects
- **File:** `multipass/screen_space_effects.html`
- **Features:** SSAO, SSR, screen space ambient occlusion and reflections
- **Visual:** Realistic lighting with screen space effects
- **Fuzz Points:** Depth buffer sampling, normal reconstruction, effect parameters

#### WEBGL-MULTIPASS-005: Multi-Resolution Rendering
- **File:** `multipass/multi_resolution.html`
- **Features:** Mipmapped render targets, downsampling/upsampling
- **Visual:** Level-of-detail rendering with resolution switching
- **Fuzz Points:** Mipmap level rendering, texture LOD control, resolution ratios

### 4.2 Transform Feedback and Compute-like Operations

#### WEBGL-COMPUTE-001: Particle Systems via Transform Feedback
- **File:** `compute/particle_systems_tf.html`
- **Features:** Transform feedback for particle updates, ping-pong buffers
- **Visual:** Complex particle effects with physics simulation
- **Fuzz Points:** Feedback varyings, buffer configurations, iteration counts

#### WEBGL-COMPUTE-002: Procedural Geometry Generation
- **File:** `compute/procedural_geometry.html`
- **Features:** Transform feedback for geometry amplification, tessellation-like effects
- **Visual:** Dynamic geometry creation and modification
- **Fuzz Points:** Varying capture modes, geometry expansion, buffer management

#### WEBGL-COMPUTE-003: GPU Data Processing Pipelines
- **File:** `compute/data_processing_pipeline.html`
- **Features:** Multi-stage transform feedback, data transformation chains
- **Visual:** Visual data processing (sorting, filtering, analysis)
- **Fuzz Points:** Multi-stage feedback, data dependencies, processing accuracy

### 4.3 Advanced Texture Techniques

#### WEBGL-TEXTURE-TECH-001: Dynamic Texture Synthesis
- **File:** `texture_tech/dynamic_synthesis.html`
- **Features:** Render-to-texture with feedback, procedural textures
- **Visual:** Self-modifying textures, reaction-diffusion systems
- **Fuzz Points:** Feedback loops, texture sampling precision, iteration stability

#### WEBGL-TEXTURE-TECH-002: Texture Atlasing and Packing
- **File:** `texture_tech/texture_atlasing.html`
- **Features:** Multiple textures in single atlas, coordinate transformations
- **Visual:** Texture atlas visualization with coordinate mapping
- **Fuzz Points:** Atlas layouts, coordinate precision, packing efficiency

#### WEBGL-TEXTURE-TECH-003: Advanced Filtering Techniques
- **File:** `texture_tech/advanced_filtering.html`
- **Features:** Custom filtering via shaders, anisotropic filtering, texture LOD
- **Visual:** Comparison of different filtering approaches
- **Fuzz Points:** Filter kernels, anisotropy values, LOD calculations

---

## Category 5: Error Conditions and Edge Cases

### 5.1 Error Handling and Validation

#### WEBGL-ERROR-001: Shader Compilation Errors
- **File:** `errors/shader_compilation.html`
- **Features:** `getShaderInfoLog()`, `COMPILE_STATUS`, compilation error detection
- **Visual:** Visual feedback for compilation status (green=success, red=error)
- **Fuzz Points:** Invalid GLSL syntax, type mismatches, undefined functions, preprocessor errors

#### WEBGL-ERROR-002: Program Linking Errors
- **File:** `errors/program_linking.html`
- **Features:** `getProgramInfoLog()`, `LINK_STATUS`, linking validation, `validateProgram()`
- **Visual:** Visual indicators for link status and validation results
- **Fuzz Points:** Attribute mismatches, uniform conflicts, shader compatibility, precision mismatches

#### WEBGL-ERROR-003: Runtime WebGL Errors
- **File:** `errors/runtime_errors.html`
- **Features:** `getError()`, error state management, error codes (INVALID_ENUM, INVALID_VALUE, etc.)
- **Visual:** Error state visualization through color-coded rendering
- **Fuzz Points:** Invalid operations, out-of-bounds access, state combinations, context loss

#### WEBGL-ERROR-004: Framebuffer Completeness Errors
- **File:** `errors/framebuffer_errors.html`
- **Features:** `checkFramebufferStatus()`, completeness validation, INVALID_FRAMEBUFFER_OPERATION
- **Visual:** Visual feedback for different framebuffer status codes
- **Fuzz Points:** Incomplete attachments, mismatched formats, size mismatches, missing attachments

#### WEBGL-ERROR-005: Texture Validation Errors
- **File:** `errors/texture_validation.html`
- **Features:** Texture completeness, mipmap consistency, format validation
- **Visual:** Texture status visualization with error indicators
- **Fuzz Points:** Incomplete textures, format mismatches, size constraints

### 5.2 Resource Limits and Boundaries

#### WEBGL-LIMITS-001: Texture Size Limits
- **File:** `limits/max_texture_size.html`
- **Features:** `MAX_TEXTURE_SIZE`, `MAX_CUBE_MAP_TEXTURE_SIZE`, limit testing
- **Visual:** Textures at maximum supported size with visual boundary indicators
- **Fuzz Points:** Size boundaries, format combinations, cube map limits

#### WEBGL-LIMITS-002: Vertex Attributes and Uniforms
- **File:** `limits/vertex_uniform_limits.html`
- **Features:** `MAX_VERTEX_ATTRIBS`, `MAX_VERTEX_UNIFORM_VECTORS`, `MAX_FRAGMENT_UNIFORM_VECTORS`
- **Visual:** Complex vertex data with maximum attribute counts
- **Fuzz Points:** Attribute counts, uniform vector limits, data type combinations

#### WEBGL-LIMITS-003: Renderbuffer and Framebuffer Limits
- **File:** `limits/renderbuffer_limits.html`
- **Features:** `MAX_RENDERBUFFER_SIZE`, attachment limits, multisample limits
- **Visual:** Large off-screen buffers pushing limits
- **Fuzz Points:** Size constraints, format compatibility, multisample support

#### WEBGL-LIMITS-004: Shader and Program Limits (WebGL2)
- **File:** `limits/shader_program_limits_webgl2.html`
- **Features:** `MAX_VERTEX_UNIFORM_COMPONENTS`, `MAX_VARYING_COMPONENTS`, block limits
- **Visual:** Complex shaders approaching limits with visual feedback
- **Fuzz Points:** Component limits, varying counts, uniform block sizes

### 5.3 Edge Cases and Boundary Conditions

#### WEBGL-EDGE-001: Precision and Numerical Limits
- **File:** `edge_cases/numerical_limits.html`
- **Features:** Floating-point precision, integer overflow, NaN handling, `lineWidth()` NaN
- **Visual:** Visual representation of precision artifacts and numerical boundaries
- **Fuzz Points:** Near-zero values, large numbers, precision-dependent calculations

#### WEBGL-EDGE-002: Context Loss and Recovery
- **File:** `edge_cases/context_loss.html`
- **Features:** Context lost events, resource restoration, `isContextLost()`, `WEBGL_lose_context`
- **Visual:** Context loss simulation with recovery visualization
- **Fuzz Points:** Context loss timing, resource cleanup, restoration accuracy

#### WEBGL-EDGE-003: Memory Management
- **File:** `edge_cases/memory_management.html`
- **Features:** Buffer/texture deletion, reference counting, garbage collection, resource cleanup
- **Visual:** Memory usage visualization with allocation/deallocation patterns
- **Fuzz Points:** Resource lifecycle, deletion timing, memory leaks

#### WEBGL-EDGE-004: Asynchronous Operations
- **File:** `edge_cases/async_operations.html`
- **Features:** Buffer mapping, query result availability, sync object timing (WebGL2)
- **Visual:** Timing-dependent visual effects with async operation feedback
- **Fuzz Points:** Operation timing, result availability, synchronization primitives

---
## Category 6: Creative Anomalies & Experimental Features

### 6.1 Visual & Temporal Stress

#### WEBGL-CREATIVE-008: The Time Warp
- **File:** `creative/time_warp_slitscan.html`
- **Features:** `TEXTURE_2D_ARRAY` ring buffer, temporal sampling, `copyTexSubImage3D`
- **Visual:** Slit-scan "time travel" effect using 64-frame history buffer
- **Biomass:** Heavy texture bandwidth, modulo arithmetic, temporal state management
- **Fuzz Points:** History depth, warp functions, copy methods

#### WEBGL-CREATIVE-009: The Voxellated World
- **File:** `creative/voxellated_world.html`
- **Features:** 3D Texture FBO attachment, volumetric slicing, Raymarching
- **Visual:** Real-time voxelization of mesh into 3D texture, then raymarched
- **Biomass:** FBO attachment churn (layer switching), 3D texture sampling, orthographic slicing
- **Fuzz Points:** Grid resolution, slicing axis, raysteps

#### WEBGL-CREATIVE-010: The Stencil Spray-Paint
- **File:** `creative/stencil_spray_paint.html`
- **Features:** Stencil logic ops (`INCR_WRAP`, `INVERT`), complex stencil masks
- **Visual:** "Graffiti" logic where shapes add/subtract stencil values to reveal patterns
- **Biomass:** Stencil state machine stress, integer overflow logic, multipass masking
- **Fuzz Points:** Op codes, mask bits, shape density

#### WEBGL-CREATIVE-011: The Feedback Turing Machine
- **File:** `creative/feedback_low_level_turing.html`
- **Features:** Transform Feedback, RASTERIZER_DISCARD, gl_VertexID logic
- **Visual:** GPGPU computation visualization, point cloud from computed state
- **Biomass:** Pure vertex processing, buffer ping-ponging, feedback loops
- **Fuzz Points:** Tape length, iterations, logic rules

#### WEBGL-CREATIVE-012: The Mipmap Cascade
- **File:** `creative/mipmap_cascade_feedback.html`
- **Features:** Intra-texture feedback, TEXTURE_BASE/MAX_LEVEL, manual mipmap generation
- **Visual:** Recursive rendering into mip levels, downsampling effects
- **Biomass:** Texture state validation, level consistency, feedback loop avoidance
- **Fuzz Points:** Level count, cascade shader logic, barrier usage

#### WEBGL-CREATIVE-013: The Anti-Aliased Blit Krieg
- **File:** `creative/multisample_blit_krieg.html`
- **Features:** MSAA Renderbuffers, blitFramebuffer, scaling blits
- **Visual:** MSAA resolve verification, scaling artifacts, scissor blitting
- **Biomass:** Multisample resolve pipeline, blit rectangle calculations
- **Fuzz Points:** Sample count, scale factors, scissor rects

---

## Implementation Guidelines

### File Structure
```
webgl_fuzzing_corpus/
├── context/          # Context creation and initialization
├── shaders/          # Shader compilation and programs
├── buffers/          # Buffer management and updates
├── textures/         # Texture creation and sampling
├── rendering/        # Basic rendering operations
├── framebuffer/      # FBO and render-to-texture
├── extensions/       # WebGL extension testing
├── webgl2/          # WebGL2 exclusive features
├── multipass/       # Complex multi-pass scenarios
├── errors/          # Error conditions and handling
├── limits/          # Resource limits and boundaries
├── edge_cases/      # Boundary conditions and edge cases
├── creative/        # Creative anomalies and experimental features
└── agent_outputs/   # Generated test files
```

### Naming Convention
- **Files:** `category_feature_description.html`
- **Variables:** Descriptive names, mix of inline values and variables
- **Shaders:** Embedded as template literals, no external files

### State Poisoning and Resource Lifecycle Requirements

**MANDATORY for all seeds:** Every test case must include state poisoning to create fragile state machines for mutation.

#### State Poisoning Requirements
- **Capability Churn:** Enable/disable every WebGL capability (BLEND, CULL_FACE, DEPTH_TEST, etc.) multiple times in varying patterns
- **Resource Binding Chaos:** Bind/unbind textures, buffers, and framebuffers redundantly between operations
- **Parameter Twisting:** Change blend functions, equations, and other state parameters repeatedly
- **Extension State Mixing:** Toggle extension-dependent features on/off based on availability

#### Resource Lifecycle Stress
- **Zombie Operations:** Create resources, delete some, attempt operations on deleted handles (UAF patterns)
- **Buffer Orphaning:** Repeatedly call bufferData() to orphan existing allocations
- **Texture Reallocation:** Change texture parameters and reallocate with different formats
- **Handle Exhaustion:** Create maximum allowed resources, then stress deletion/recreation patterns

#### Variable Exposure Pattern (REQUIRED)
- **Inline Literals + Variables:** Mix hardcoded values with parameterized variables for easy mutation targeting
- **Magic Number Elimination:** Replace magic numbers with named constants that mutators can find
- **Configuration Objects:** Expose all tweakable parameters as variables at the top of the file

### Boilerplate Template

**CRITICAL:** Use the exact boilerplate from `AGENTS.md`. Do NOT create custom variations. The boilerplate includes proper `UNSUPPORTED_EXTENSIONS` handling required by the test runner.

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
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!gl) throw new Error("WebGL not supported");

    // 1. EXTENSION GATING
    const missingExtensions = REQUIRED_EXTENSIONS.filter(ext => !gl.getExtension(ext));
    if (missingExtensions.length > 0) {
        // Signal to the Test Runner that this is an environment limit, not a code bug
        throw new Error(`UNSUPPORTED_EXTENSIONS: ${missingExtensions.join(', ')}`);
    }

    // 2. ENABLE REQUIRED EXTENSIONS
    REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));

    // ==========================================
    // COMPLEX IMPLEMENTATION STARTS HERE
    // ==========================================

    // [Insert Multi-pass, Multi-resource logic here]
    // [Avoid abstractions. Use raw WebGL API calls.]
    // [Focus on extension interactions and complex shader usage]

    // ==========================================
    // COMPLEX IMPLEMENTATION ENDS HERE
    // ==========================================

    // 3. ERROR CHECKING
    const error = gl.getError();
    if (error !== gl.NO_ERROR) {
       throw new Error(`WebGL Error: ${error}`);
    }
} 



main();
</script>
</body>
</html>
```

**Variable Exposure Pattern (REQUIRED):**
```javascript
// GOOD SEED STYLE - Mix inline literals with variables for mutation
const TEX_WIDTH = 256;
const TEX_FORMAT = gl.RGBA;
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, TEX_WIDTH, TEX_HEIGHT, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
gl.texImage2D(gl.TEXTURE_2D, 0, TEX_FORMAT, 512, 512, 0, TEX_FORMAT, gl.UNSIGNED_BYTE, null); // Inline literal + variable mix
```

### Testing and Validation
- **Automated Testing:** `./run_tests.sh --test-file <test-file>.html`
- **Success Criteria:** `"passed": true`, output `<test-file>.json` empty error arrays, no warnings pointing to WebGL failure.
- **Visual Validation:** Deterministic, meaningful output
- **Fuzzer-Friendly:** Inline literals with parameterized variables

---

## Progress Tracking Template

### Status Legend
- 🔲 Not started
- 🚧 In progress
- ✅ Complete and tested
- ⏸️ Blocked/Waiting
- ❌ Skipped (unsupported)

### Progress Table Template

| Flow ID | Description | Status | File | Notes |
|---------|-------------|--------|------|-------|
| WEBGL-INIT-001 | Basic WebGL Context Creation | 🔲 |  |  |

### Coverage Metrics
- **Total Test Cases:** 0/65 (0%)
- **Core Functionality:** 0/20 (0%) - Context, shaders, buffers
- **Rendering Pipeline:** 0/17 (0%) - Basic rendering, textures, framebuffers
- **Advanced Features:** 0/22 (0%) - Extensions + WebGL2 features
- **Multi-pass Scenarios:** 0/11 (0%) - Complex pipelines and techniques
- **Error Conditions:** 0/13 (0%) - Error handling, limits, edge cases
- **Creative Anomalies:** 0/3 (0%) - Visual & temporal stress

### Implementation Priority (Fuzzing-Focused)
1. **HIGHEST Priority:** Category 0 - Integrated Pipelines (Kitchen Sink Seeds) - Maximum biomass, spaghetti code
2. **High Priority:** Category 6 - Creative Anomalies - New experimental mega-shaders
3. **High Priority:** Category 4 - Complex Multi-Pass Scenarios - Render-to-texture chains, advanced pipelines
4. **Medium Priority:** Category 3 - Advanced WebGL Features - Extensions + WebGL2 features combined
5. **Low Priority:** Category 1 - Core Pipeline Components - Basic isolated features (deprioritize these)
6. **Lowest Priority:** Category 2 - Rendering Complexities - Individual complex features without integration

---

## Extension Coverage Matrix

| Extension | Test Case | Status | Priority | WebGL Version |
|-----------|-----------|--------|----------|----------------|
| OES_texture_float | WEBGL-EXT-001 | ❌ Blocked | High | WebGL1 |
| OES_texture_half_float | WEBGL-EXT-001 | 🔲 | High | WebGL1 |
| WEBGL_draw_buffers | WEBGL-EXT-004 | 🔲 | High | WebGL1 |
| OES_vertex_array_object | WEBGL-EXT-002 | 🔲 | Medium | WebGL1 |
| ANGLE_instanced_arrays | WEBGL-EXT-003 | 🔲 | Medium | WebGL1 |
| WEBGL_depth_texture | WEBGL-EXT-005 | 🔲 | Medium | WebGL1 |
| OES_standard_derivatives | WEBGL-EXT-006 | 🔲 | Medium | WebGL1 |
| OES_element_index_uint | WEBGL-EXT-007 | 🔲 | Low | WebGL1 |
| EXT_shader_texture_lod | WEBGL-TEXTURE-006 | 🔲 | Low | WebGL1 |
| EXT_frag_depth | WEBGL-RENDER-003 | 🔲 | Low | WebGL1 |
| WEBGL_color_buffer_float | WEBGL-FBO-002 | 🔲 | Medium | WebGL1 |
| Vertex Array Objects (Core) | WEBGL2-FEATURE-003 | 🔲 | High | WebGL2 |
| Multiple Render Targets (Core) | WEBGL2-FEATURE-003 | 🔲 | High | WebGL2 |
| Uniform Buffer Objects | WEBGL2-FEATURE-001 | 🔲 | High | WebGL2 |
| Transform Feedback | WEBGL2-FEATURE-002 | 🔲 | High | WebGL2 |
| 3D Textures | WEBGL2-FEATURE-004 | 🔲 | High | WebGL2 |
| Texture Arrays | WEBGL2-FEATURE-005 | 🔲 | Medium | WebGL2 |
| Sampler Objects | WEBGL2-FEATURE-006 | 🔲 | Medium | WebGL2 |
| Query Objects | WEBGL2-FEATURE-007 | 🔲 | Medium | WebGL2 |
| Sync Objects | WEBGL2-FEATURE-008 | 🔲 | Low | WebGL2 |
| Instanced Rendering (Core) | WEBGL2-FEATURE-009 | 🔲 | Medium | WebGL2 |
| Integer Textures | WEBGL2-FEATURE-010 | 🔲 | Medium | WebGL2 |

### Extension Blocking Notes

#### OES_texture_float - Blocked by Fingerprinting Protection
- **Status:** Permanently blocked in Playwright Firefox automation
- **Cause:** Firefox's `privacy.resistFingerprinting` setting blocks floating-point textures to prevent hardware identification
- **Impact:** Cannot test HDR rendering, float precision effects, or advanced texture techniques in automated Playwright environment
- **Workaround:** Test manually in native Firefox browser or use alternative texture formats
- **WebGL2 Alternative:** Use WebGL2 core float textures (EXT_color_buffer_float) where available

---

## Success Metrics (Fuzzing-Focused)

- **Mutation Biomass:** High density of state changes, resource operations, and extension interactions
- **Variable Exposure:** Mix of inline literals and parameterized variables for easy mutation targeting
- **State Fragility:** Complex state machines that become invalid with small mutations
- **Resource Coupling:** Shared resources across multiple operations with complex lifecycles
- **Extension Stress:** Forced interaction between disparate WebGL extensions
- **Crash Surface Area:** Code patterns that expose driver bugs when mutated
- **Valid but Hostile:** Complex valid sequences that stress implementation boundaries

This implementation plan provides a systematic approach to comprehensively cover the WebGL/WebGL2 API surface while creating visually compelling and fuzzer-friendly test cases.