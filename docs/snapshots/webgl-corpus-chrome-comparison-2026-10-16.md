# WebGL corpus coverage report

Lane: `{"browser": "chromium", "browser_identity": {"browser_name": "chromium", "browser_version": "155.0.8059.79", "context": {"ignore_https_errors": true, "permissions": ["camera", "microphone"]}, "event_cap": 20000, "executable": {"launched_path": "/opt/google/chrome/google-chrome", "mtime_ns": 1791849060000000000, "path": "/opt/google/chrome/chrome", "size": 298171720}, "fingerprint": "b1898765861690fdca4983af379bdac9397fa991caf7cc462c1683f50d062000", "headless": true, "launch_flags": ["--enable-features=Vulkan,UseSkiaRenderer", "--disable-vulkan-fallback-to-gl-for-testing", "--enable-dawn-features=allow_unsafe_apis", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu-sandbox", "--enable-gpu-rasterization", "--ignore-gpu-blocklist", "--enable-experimental-extension-apis", "--enable-experimental-web-platform-features", "--use-angle=vulkan"], "outcome_cap": 2048, "preferences": {}, "profiler_version": "webgl-trace-2"}, "context_versions": [2], "contexts": [{"extensions": ["EXT_clip_control", "EXT_color_buffer_float", "EXT_color_buffer_half_float", "EXT_conservative_depth", "EXT_depth_clamp", "EXT_disjoint_timer_query_webgl2", "EXT_float_blend", "EXT_polygon_offset_clamp", "EXT_render_snorm", "EXT_texture_compression_bptc", "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic", "EXT_texture_mirror_clamp_to_edge", "EXT_texture_norm16", "NV_shader_noperspective_interpolation", "OES_draw_buffers_indexed", "OES_sample_variables", "OES_shader_multisample_interpolation", "OES_texture_float_linear", "OVR_multiview2", "WEBGL_blend_func_extended", "WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info", "WEBGL_debug_shaders", "WEBGL_lose_context", "WEBGL_multi_draw", "WEBGL_polygon_mode", "WEBGL_render_shared_exponent", "WEBGL_stencil_texturing"], "renderer": "ANGLE (AMD, Vulkan 1.4.335 (Radeon 8060S Graphics (RADV STRIX_HALO) (0x00001586)), radv)", "renderer_verified": true, "vendor": "Google Inc. (AMD)", "version": 2}], "outcome_cap": 2048, "profile_event_cap": 20000, "profiler_version": "webgl-trace-2", "reducer_version": "webgl-flow-3", "renderer": ["ANGLE (AMD, Vulkan 1.4.335 (Radeon 8060S Graphics (RADV STRIX_HALO) (0x00001586)), radv)"]}`

Measured baseline: 208 requirements; selection status: **selected**.

Inventory: 422 sources; 7 clean controls, 0 failed controls, 415 unmeasured; 543 static requirements observed.

## Context capability scopes

| WebGL | Supported extensions | Covered | Missing | Unsupported | Unmeasured |
|---|---|---:|---:|---:|---:|
| 1 | unobserved | 0 | 0 | 0 | 423 |
| 2 | EXT_clip_control, EXT_color_buffer_float, EXT_color_buffer_half_float, EXT_conservative_depth, EXT_depth_clamp, EXT_disjoint_timer_query_webgl2, EXT_float_blend, EXT_polygon_offset_clamp, EXT_render_snorm, EXT_texture_compression_bptc, EXT_texture_compression_rgtc, EXT_texture_filter_anisotropic, EXT_texture_mirror_clamp_to_edge, EXT_texture_norm16, NV_shader_noperspective_interpolation, OES_draw_buffers_indexed, OES_sample_variables, OES_shader_multisample_interpolation, OES_texture_float_linear, OVR_multiview2, WEBGL_blend_func_extended, WEBGL_compressed_texture_s3tc, WEBGL_compressed_texture_s3tc_srgb, WEBGL_debug_renderer_info, WEBGL_debug_shaders, WEBGL_lose_context, WEBGL_multi_draw, WEBGL_polygon_mode, WEBGL_render_shared_exponent, WEBGL_stencil_texturing | 155 | 443 | 19 | 0 |

## Equal-time campaign comparison

Common observed wall time: 12077.701 ms.

| Yield | Baseline | Current |
|---|---:|---:|
| Clean variants | 52 | 48 |
| Distinct flow changes | 32 | 29 |
| Distinct pixel images | 24 | 21 |

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
| `rendering_ping_pong_texturing.html` | bounded_parameter:6, draw_mode:12, framebuffer_attachment_cycle:1, program_relink_duplicate:1, state_transition:7, sync_placement:2, texture_storage_duplicate:2, viewport_dimension:4 | 8 | bufferData(data/size); activeTexture(texture); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `webgl2_instanced_rendering_core.html` | bounded_parameter:6, draw_mode:6, glsl_linked_varying_rename:1, program_relink_duplicate:1, state_transition:6, sync_placement:2, viewport_dimension:8 | 13 | bufferData(data/size); vertexAttribPointer(size) |
| `webgl2_vertex_arrays_state_isolation.html` | draw_mode:6, glsl_linked_varying_rename:3, glsl_trig_function:2, program_relink_duplicate:1, state_transition:1, viewport_dimension:8 | 11 | bufferData(data/size); bindBuffer(target); drawElements(count); uniformMatrix4fv(data/value); vertexAttribPointer(size) |

## Proposed manifest

- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/mutation_vertex_buffer_state_multidraw.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/rendering/rendering_ping_pong_texturing.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/shaders_structural_coupled_passes.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/webgl2/webgl2_instanced_rendering_core.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/webgl2/webgl2_vertex_arrays_state_isolation.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/resource_typed_view_buffer_capture.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/texture_paired_update_offscreen_composite.html`

Unmet baseline requirements: 0.
Unmet full-universe requirements: 487.

## Mutation yield

| Family | Sites | Generated | Clean | Flow changes | Image changes | Browser ms | Median ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| bounded_parameter | 45 | 6 | 6 | 4 | 5 | 1218.6575200030347 | 190.48811849643243 |
| buffer_redefine_after_upload | 1 | 1 | 1 | 1 | 1 | 168.60794300737325 | 168.60794300737325 |
| compatible_buffer_switch | 2 | 1 | 1 | 1 | 1 | 191.56200799625367 | 191.56200799625367 |
| compatible_texture_update_switch | 1 | 1 | 1 | 1 | 1 | 172.9747560020769 | 172.9747560020769 |
| draw_mode | 90 | 7 | 7 | 7 | 6 | 1485.3616220061667 | 208.62757100258023 |
| framebuffer_attachment_cycle | 2 | 2 | 2 | 2 | 0 | 468.60822799499147 | 234.30411399749573 |
| framebuffer_retire | 1 | 1 | 1 | 0 | 0 | 175.1557379902806 | 175.1557379902806 |
| glsl_array_index | 1 | 1 | 1 | 0 | 1 | 213.3901900087949 | 213.3901900087949 |
| glsl_linked_varying_rename | 6 | 4 | 4 | 0 | 0 | 889.1508169908775 | 223.6797884979751 |
| glsl_loop_bound | 1 | 1 | 1 | 0 | 1 | 184.0116530074738 | 184.0116530074738 |
| glsl_matrix_scalar | 1 | 1 | 1 | 0 | 1 | 167.59183799149469 | 167.59183799149469 |
| glsl_trig_function | 3 | 2 | 2 | 0 | 1 | 393.44627600803506 | 196.72313800401753 |
| mixed | 0 | 2 | 1 | 0 | 1 | 383.1456489933771 | 191.57282449668855 |
| program_relink_duplicate | 6 | 5 | 5 | 5 | 0 | 1087.268174989731 | 204.56384999852162 |
| resource_storage | 6 | 1 | 1 | 1 | 0 | 185.79727900214493 | 185.79727900214493 |
| state_transition | 41 | 5 | 5 | 5 | 0 | 1083.4122050291626 | 196.7613910092041 |
| storage_duplicate | 3 | 0 | 0 | 0 | 0 | 0 | None |
| sync_placement | 20 | 3 | 3 | 0 | 0 | 602.6579879981 | 202.97832100186497 |
| texture_allocation_update_dimensions | 1 | 0 | 0 | 0 | 0 | 0 | None |
| texture_retire | 1 | 0 | 0 | 0 | 0 | 0 | None |
| texture_storage_duplicate | 3 | 1 | 1 | 1 | 0 | 239.8259390029125 | 239.8259390029125 |
| texture_subimage_dimension | 2 | 0 | 0 | 0 | 0 | 0 | None |
| typed_array_view_offset | 1 | 0 | 0 | 0 | 0 | 0 | None |
| vertex_attrib_offset | 2 | 0 | 0 | 0 | 0 | 0 | None |
| vertex_attrib_stride | 7 | 1 | 1 | 1 | 0 | 218.52402899821755 | 218.52402899821755 |
| viewport_dimension | 32 | 3 | 3 | 0 | 2 | 642.7545619953889 | 215.87530500255525 |
