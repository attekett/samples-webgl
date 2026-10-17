# WebGL corpus coverage report

Lane: `{"browser": "chromium", "browser_identity": {"browser_name": "chromium", "browser_version": "155.0.8059.79", "context": {"ignore_https_errors": true, "permissions": ["camera", "microphone"]}, "event_cap": 20000, "executable": {"launched_path": "/opt/google/chrome/google-chrome", "mtime_ns": 1791849060000000000, "path": "/opt/google/chrome/chrome", "size": 298171720}, "fingerprint": "b1898765861690fdca4983af379bdac9397fa991caf7cc462c1683f50d062000", "headless": true, "launch_flags": ["--enable-features=Vulkan,UseSkiaRenderer", "--disable-vulkan-fallback-to-gl-for-testing", "--enable-dawn-features=allow_unsafe_apis", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu-sandbox", "--enable-gpu-rasterization", "--ignore-gpu-blocklist", "--enable-experimental-extension-apis", "--enable-experimental-web-platform-features", "--use-angle=vulkan"], "outcome_cap": 2048, "preferences": {}, "profiler_version": "webgl-trace-2"}, "context_versions": [2], "contexts": [{"extensions": ["EXT_clip_control", "EXT_color_buffer_float", "EXT_color_buffer_half_float", "EXT_conservative_depth", "EXT_depth_clamp", "EXT_disjoint_timer_query_webgl2", "EXT_float_blend", "EXT_polygon_offset_clamp", "EXT_render_snorm", "EXT_texture_compression_bptc", "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic", "EXT_texture_mirror_clamp_to_edge", "EXT_texture_norm16", "NV_shader_noperspective_interpolation", "OES_draw_buffers_indexed", "OES_sample_variables", "OES_shader_multisample_interpolation", "OES_texture_float_linear", "OVR_multiview2", "WEBGL_blend_func_extended", "WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info", "WEBGL_debug_shaders", "WEBGL_lose_context", "WEBGL_multi_draw", "WEBGL_polygon_mode", "WEBGL_render_shared_exponent", "WEBGL_stencil_texturing"], "renderer": "ANGLE (AMD, Vulkan 1.4.335 (Radeon 8060S Graphics (RADV STRIX_HALO) (0x00001586)), radv)", "renderer_verified": true, "vendor": "Google Inc. (AMD)", "version": 2}], "outcome_cap": 2048, "profile_event_cap": 20000, "profiler_version": "webgl-trace-2", "reducer_version": "webgl-flow-3", "renderer": ["ANGLE (AMD, Vulkan 1.4.335 (Radeon 8060S Graphics (RADV STRIX_HALO) (0x00001586)), radv)"]}`

Measured baseline: 276 requirements; selection status: **provisional**.

Inventory: 428 sources; 13 clean controls, 0 failed controls, 415 unmeasured; 546 static requirements observed.

## Context capability scopes

| WebGL | Supported extensions | Covered | Missing | Unsupported | Unmeasured |
|---|---|---:|---:|---:|---:|
| 1 | unobserved | 0 | 0 | 0 | 423 |
| 2 | EXT_clip_control, EXT_color_buffer_float, EXT_color_buffer_half_float, EXT_conservative_depth, EXT_depth_clamp, EXT_disjoint_timer_query_webgl2, EXT_float_blend, EXT_polygon_offset_clamp, EXT_render_snorm, EXT_texture_compression_bptc, EXT_texture_compression_rgtc, EXT_texture_filter_anisotropic, EXT_texture_mirror_clamp_to_edge, EXT_texture_norm16, NV_shader_noperspective_interpolation, OES_draw_buffers_indexed, OES_sample_variables, OES_shader_multisample_interpolation, OES_texture_float_linear, OVR_multiview2, WEBGL_blend_func_extended, WEBGL_compressed_texture_s3tc, WEBGL_compressed_texture_s3tc_srgb, WEBGL_debug_renderer_info, WEBGL_debug_shaders, WEBGL_lose_context, WEBGL_multi_draw, WEBGL_polygon_mode, WEBGL_render_shared_exponent, WEBGL_stencil_texturing | 209 | 389 | 19 | 0 |

## Equal-time campaign comparison

Common observed wall time: 12074.439 ms.

| Yield | Baseline | Current |
|---|---:|---:|
| Clean variants | 52 | 48 |
| Distinct flow changes | 32 | 32 |
| Distinct pixel images | 24 | 30 |

Baseline requirements preserved: **yes**.
Each yield preserved: **no**.
Adoption eligible: **no**.

## Per-seed edit-site coverage

| Source | Candidate sites by family | Direct argument sites | Static gaps for observed methods (examples) |
|---|---|---:|---|
| `mutation_vertex_buffer_state_multidraw.html` | bounded_parameter:12, draw_mode:24, state_transition:11, sync_placement:2, vertex_attrib_stride:3, viewport_dimension:2 | 13 | WEBGL_multi_draw.multiDrawArraysWEBGL(firstsList); WEBGL_multi_draw.multiDrawArraysWEBGL(countsList); bufferData(data/size); vertexAttribPointer(size); attachShader(program) |
| `resource_typed_view_buffer_capture.html` | bounded_parameter:6, buffer_redefine_after_upload:1, compatible_buffer_switch:2, draw_mode:12, program_relink_duplicate:1, resource_storage:6, state_transition:5, storage_duplicate:3, sync_placement:4, typed_array_view_offset:1, vertex_attrib_offset:2, vertex_attrib_stride:2, viewport_dimension:2 | 15 | bufferSubData(data); bufferSubData(data) [wrapper only]; bindBuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program) |
| `shaders_structural_coupled_passes.html` | bounded_parameter:6, draw_mode:12, glsl_array_index:1, glsl_linked_varying_rename:1, glsl_loop_bound:1, glsl_matrix_scalar:1, program_relink_duplicate:1, state_transition:2, sync_placement:4, vertex_attrib_stride:1, viewport_dimension:2 | 9 | bufferData(data/size); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; bufferData(target); vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `texture_paired_update_offscreen_composite.html` | bounded_parameter:9, compatible_texture_update_switch:1, draw_mode:18, framebuffer_attachment_cycle:1, framebuffer_retire:1, glsl_linked_varying_rename:1, glsl_trig_function:1, program_relink_duplicate:1, state_transition:9, sync_placement:6, texture_allocation_update_dimensions:1, texture_retire:1, texture_storage_duplicate:1, texture_subimage_dimension:2, vertex_attrib_stride:1, viewport_dimension:6 | 19 | bufferData(data/size); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; bindFramebuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `valid_buffer_texture_paired_multipass.html` | bounded_parameter:6, compatible_buffer_switch:2, compatible_texture_update_switch:2, draw_mode:12, framebuffer_attachment_cycle:1, framebuffer_retire:1, glsl_linked_varying_rename:1, program_relink_duplicate:1, resource_storage:4, state_transition:12, storage_duplicate:2, sync_placement:4, texture_allocation_update_dimensions:1, texture_retire:1, texture_subimage_dimension:2, typed_array_view_offset:1, vertex_attrib_stride:2, viewport_dimension:4 | 20 | bufferSubData(data); bindBuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program) |
| `webgl2_buffer_rebind_value_grid.html` | bounded_parameter:14, draw_mode:36, glsl_trig_function:1, state_transition:11, sync_placement:12, vertex_attrib_offset:1, vertex_attrib_stride:2, viewport_dimension:2 | 18 | bufferData(data/size); drawArraysInstanced(instanceCount) [wrapper only]; drawElements(count) [wrapper only]; vertexAttribPointer(size) |
| `webgl2_multidraw_indexed_instanced_rows.html` | state_transition:10, vertex_attrib_offset:1, vertex_attrib_stride:2, viewport_dimension:2 | 5 | WEBGL_multi_draw.multiDrawArraysInstancedWEBGL(firstsList); WEBGL_multi_draw.multiDrawArraysInstancedWEBGL(countsList); WEBGL_multi_draw.multiDrawArraysInstancedWEBGL(countsOffset); WEBGL_multi_draw.multiDrawArraysInstancedWEBGL(instanceCountsList); bufferData(data/size); bindBuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program) |
| `webgl2_occlusion_query_visibility_panels.html` | bounded_parameter:15, draw_mode:30, state_transition:2, sync_placement:10, viewport_dimension:8 | 18 | bufferData(data/size); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; bufferData(target); vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `webgl2_sampler_objects_split_filter.html` | bounded_parameter:9, draw_mode:18, state_transition:5, sync_placement:6, viewport_dimension:4 | 10 | bufferData(data/size); activeTexture(texture); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `webgl2_transform_feedback_wave_particles.html` | glsl_trig_function:2, state_transition:9, sync_placement:4, viewport_dimension:2 | 3 | bufferData(data/size); bindBuffer(target) [wrapper only]; drawArrays(count) [wrapper only]; vertexAttribPointer(size) |
| `webgl2_uniform_buffer_palette_tiles.html` | bounded_parameter:3, draw_mode:6, glsl_trig_function:2, state_transition:6, viewport_dimension:2 | 5 | bindBufferRange(size); bufferData(data/size); bufferSubData(data); vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `rendering_ping_pong_texturing.html` | bounded_parameter:6, draw_mode:12, framebuffer_attachment_cycle:1, program_relink_duplicate:1, state_transition:7, sync_placement:2, texture_storage_duplicate:2, viewport_dimension:4 | 8 | bufferData(data/size); activeTexture(texture); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `webgl2_instanced_rendering_core.html` | bounded_parameter:6, draw_mode:6, glsl_linked_varying_rename:1, program_relink_duplicate:1, state_transition:6, sync_placement:2, viewport_dimension:8 | 13 | bufferData(data/size); vertexAttribPointer(size) |
| `webgl2_vertex_arrays_state_isolation.html` | draw_mode:6, glsl_linked_varying_rename:3, glsl_trig_function:2, program_relink_duplicate:1, state_transition:1, viewport_dimension:8 | 11 | bufferData(data/size); bindBuffer(target); drawElements(count); uniformMatrix4fv(data/value); vertexAttribPointer(size) |

## Proposed manifest

- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_uniform_buffer_palette_tiles.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/webgl2/webgl2_vertex_arrays_state_isolation.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/mutation_vertex_buffer_state_multidraw.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/rendering/rendering_ping_pong_texturing.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_transform_feedback_wave_particles.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_occlusion_query_visibility_panels.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_buffer_rebind_value_grid.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_multidraw_indexed_instanced_rows.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/valid_buffer_texture_paired_multipass.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_sampler_objects_split_filter.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/webgl2/webgl2_instanced_rendering_core.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/shaders_structural_coupled_passes.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/resource_typed_view_buffer_capture.html`

Unmet baseline requirements: 0.
Unmet full-universe requirements: 421.

## Mutation yield

| Family | Sites | Generated | Clean | Flow changes | Image changes | Browser ms | Median ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| bounded_parameter | 92 | 11 | 10 | 5 | 9 | 2008.9954659924842 | 180.35332899307832 |
| buffer_redefine_after_upload | 1 | 1 | 1 | 1 | 1 | 201.6181999933906 | 201.6181999933906 |
| compatible_buffer_switch | 4 | 2 | 2 | 2 | 2 | 358.7752290040953 | 179.38761450204765 |
| compatible_texture_update_switch | 3 | 2 | 2 | 2 | 2 | 349.23601399350446 | 174.61800699675223 |
| draw_mode | 192 | 12 | 12 | 12 | 9 | 2228.3410109957913 | 182.81749549350934 |
| framebuffer_attachment_cycle | 3 | 2 | 2 | 2 | 0 | 402.9629360011313 | 201.48146800056566 |
| framebuffer_retire | 2 | 0 | 0 | 0 | 0 | 0 | None |
| glsl_array_index | 1 | 1 | 1 | 0 | 1 | 165.26497399900109 | 165.26497399900109 |
| glsl_linked_varying_rename | 7 | 3 | 3 | 0 | 0 | 550.2924660104327 | 176.6197410033783 |
| glsl_loop_bound | 1 | 0 | 0 | 0 | 0 | 0 | None |
| glsl_matrix_scalar | 1 | 0 | 0 | 0 | 0 | 0 | None |
| glsl_trig_function | 8 | 4 | 4 | 0 | 3 | 728.3493869763333 | 167.13470399554353 |
| program_relink_duplicate | 7 | 0 | 0 | 0 | 0 | 0 | None |
| resource_storage | 10 | 0 | 0 | 0 | 0 | 0 | None |
| state_transition | 96 | 6 | 6 | 6 | 0 | 1031.3523889926728 | 172.76879599376116 |
| storage_duplicate | 5 | 0 | 0 | 0 | 0 | 0 | None |
| sync_placement | 56 | 3 | 2 | 0 | 0 | 656.5951910088188 | 177.02704900875688 |
| texture_allocation_update_dimensions | 2 | 0 | 0 | 0 | 0 | 0 | None |
| texture_retire | 2 | 0 | 0 | 0 | 0 | 0 | None |
| texture_storage_duplicate | 3 | 0 | 0 | 0 | 0 | 0 | None |
| texture_subimage_dimension | 4 | 0 | 0 | 0 | 0 | 0 | None |
| typed_array_view_offset | 2 | 0 | 0 | 0 | 0 | 0 | None |
| vertex_attrib_offset | 4 | 1 | 1 | 1 | 1 | 168.73833199497312 | 168.73833199497312 |
| vertex_attrib_stride | 13 | 1 | 1 | 1 | 1 | 178.81462899094913 | 178.81462899094913 |
| viewport_dimension | 56 | 1 | 1 | 0 | 1 | 179.0712829970289 | 179.0712829970289 |
