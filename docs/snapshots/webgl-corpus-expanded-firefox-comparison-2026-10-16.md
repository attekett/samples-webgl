# WebGL corpus coverage report

Lane: `{"browser": "firefox", "browser_identity": {"browser_name": "firefox", "browser_version": "153.0", "context": {"ignore_https_errors": true, "permissions": []}, "event_cap": 20000, "executable": {"mtime_ns": 1787558585682244431, "path": "/home/attekett/.cache/ms-playwright/firefox-1538/firefox/firefox", "size": 576240}, "fingerprint": "bf7ea348b85a6b76f4270ecae9234035fa6268f98266ae8e3e34c4045d6e6ff6", "headless": true, "launch_flags": ["--new-instance", "--no-remote"], "outcome_cap": 2048, "preferences": {"dom.ipc.keepProcessesAlive.web": 1, "dom.ipc.processCount.web_isolated": 1, "gfx.webrender.all": true, "gfx.x11-egl.force-enabled": true, "gl.provider": "EGL", "layers.acceleration.force-enabled": true, "privacy.resistFingerprinting": false, "webgl.disable-extensions": false, "webgl.disable-fail-if-major-performance-caveat": true, "webgl.enable-draft-extensions": true, "webgl.enable-privileged-extensions": true, "webgl.enable-webgl2": true, "webgl.force-enabled": true, "webgl.min_capability_mode": false}, "profiler_version": "webgl-trace-2"}, "context_versions": [2], "contexts": [{"extensions": ["EXT_color_buffer_float", "EXT_depth_clamp", "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_texture_compression_bptc", "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic", "EXT_texture_norm16", "MOZ_debug", "OES_draw_buffers_indexed", "OES_texture_float_linear", "WEBGL_compressed_texture_astc", "WEBGL_compressed_texture_etc", "WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info", "WEBGL_debug_shaders", "WEBGL_explicit_present", "WEBGL_lose_context"], "renderer": "Radeon R9 200 Series, or similar", "renderer_verified": false, "vendor": "Mozilla", "version": 2}], "outcome_cap": 2048, "profile_event_cap": 20000, "profiler_version": "webgl-trace-2", "reducer_version": "webgl-flow-3", "renderer": ["Radeon R9 200 Series, or similar"]}`

Measured baseline: 241 requirements; selection status: **provisional**.

Inventory: 428 sources; 11 clean controls, 0 failed controls, 417 unmeasured; 546 static requirements observed.

## Context capability scopes

| WebGL | Supported extensions | Covered | Missing | Unsupported | Unmeasured |
|---|---|---:|---:|---:|---:|
| 1 | unobserved | 0 | 0 | 0 | 423 |
| 2 | EXT_color_buffer_float, EXT_depth_clamp, EXT_disjoint_timer_query, EXT_float_blend, EXT_texture_compression_bptc, EXT_texture_compression_rgtc, EXT_texture_filter_anisotropic, EXT_texture_norm16, MOZ_debug, OES_draw_buffers_indexed, OES_texture_float_linear, WEBGL_compressed_texture_astc, WEBGL_compressed_texture_etc, WEBGL_compressed_texture_s3tc, WEBGL_compressed_texture_s3tc_srgb, WEBGL_debug_renderer_info, WEBGL_debug_shaders, WEBGL_explicit_present, WEBGL_lose_context | 188 | 400 | 31 | 0 |

## Equal-time campaign comparison

Common observed wall time: 12328.089 ms.

| Yield | Baseline | Current |
|---|---:|---:|
| Clean variants | 25 | 18 |
| Distinct flow changes | 18 | 13 |
| Distinct pixel images | 18 | 15 |

Baseline requirements preserved: **yes**.
Each yield preserved: **no**.
Adoption eligible: **no**.

## Per-seed edit-site coverage

| Source | Candidate sites by family | Direct argument sites | Static gaps for observed methods (examples) |
|---|---|---:|---|
| `resource_typed_view_buffer_capture.html` | bounded_parameter:6, buffer_redefine_after_upload:1, compatible_buffer_switch:2, draw_mode:12, program_relink_duplicate:1, resource_storage:6, state_transition:5, storage_duplicate:3, sync_placement:4, typed_array_view_offset:1, vertex_attrib_offset:2, vertex_attrib_stride:2, viewport_dimension:2 | 15 | bufferSubData(data); bufferSubData(data) [wrapper only]; bindBuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program) |
| `shaders_structural_coupled_passes.html` | bounded_parameter:6, draw_mode:12, glsl_array_index:1, glsl_linked_varying_rename:1, glsl_loop_bound:1, glsl_matrix_scalar:1, program_relink_duplicate:1, state_transition:2, sync_placement:4, vertex_attrib_stride:1, viewport_dimension:2 | 9 | bufferData(data/size); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; bufferData(target); vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `texture_paired_update_offscreen_composite.html` | bounded_parameter:9, compatible_texture_update_switch:1, draw_mode:18, framebuffer_attachment_cycle:1, framebuffer_retire:1, glsl_linked_varying_rename:1, glsl_trig_function:1, program_relink_duplicate:1, state_transition:9, sync_placement:6, texture_allocation_update_dimensions:1, texture_retire:1, texture_storage_duplicate:1, texture_subimage_dimension:2, vertex_attrib_stride:1, viewport_dimension:6 | 19 | bufferData(data/size); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; bindFramebuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `valid_buffer_texture_paired_multipass.html` | bounded_parameter:6, compatible_buffer_switch:2, compatible_texture_update_switch:2, draw_mode:12, framebuffer_attachment_cycle:1, framebuffer_retire:1, glsl_linked_varying_rename:1, program_relink_duplicate:1, resource_storage:4, state_transition:12, storage_duplicate:2, sync_placement:4, texture_allocation_update_dimensions:1, texture_retire:1, texture_subimage_dimension:2, typed_array_view_offset:1, vertex_attrib_stride:2, viewport_dimension:4 | 20 | bufferSubData(data); bindBuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program) |
| `webgl2_buffer_rebind_value_grid.html` | bounded_parameter:14, draw_mode:36, glsl_trig_function:1, state_transition:11, sync_placement:12, vertex_attrib_offset:1, vertex_attrib_stride:2, viewport_dimension:2 | 18 | bufferData(data/size); drawArraysInstanced(instanceCount) [wrapper only]; drawElements(count) [wrapper only]; vertexAttribPointer(size) |
| `webgl2_occlusion_query_visibility_panels.html` | bounded_parameter:15, draw_mode:30, state_transition:2, sync_placement:10, viewport_dimension:8 | 18 | bufferData(data/size); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; bufferData(target); vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `webgl2_sampler_objects_split_filter.html` | bounded_parameter:9, draw_mode:18, state_transition:5, sync_placement:6, viewport_dimension:4 | 10 | bufferData(data/size); activeTexture(texture); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `webgl2_transform_feedback_wave_particles.html` | glsl_trig_function:2, state_transition:9, sync_placement:4, viewport_dimension:2 | 3 | bufferData(data/size); bindBuffer(target) [wrapper only]; drawArrays(count) [wrapper only]; vertexAttribPointer(size) |
| `webgl2_uniform_buffer_palette_tiles.html` | bounded_parameter:3, draw_mode:6, glsl_trig_function:2, state_transition:6, viewport_dimension:2 | 5 | bindBufferRange(size); bufferData(data/size); bufferSubData(data); vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `rendering_ping_pong_texturing.html` | bounded_parameter:6, draw_mode:12, framebuffer_attachment_cycle:1, program_relink_duplicate:1, state_transition:7, sync_placement:2, texture_storage_duplicate:2, viewport_dimension:4 | 8 | bufferData(data/size); activeTexture(texture); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `webgl2_instanced_rendering_core.html` | bounded_parameter:6, draw_mode:6, glsl_linked_varying_rename:1, program_relink_duplicate:1, state_transition:6, sync_placement:2, viewport_dimension:8 | 13 | bufferData(data/size); vertexAttribPointer(size) |
| `webgl2_vertex_arrays_state_isolation.html` | draw_mode:6, glsl_linked_varying_rename:3, glsl_trig_function:2, program_relink_duplicate:1, state_transition:1, viewport_dimension:8 | 11 | bufferData(data/size); bindBuffer(target); drawElements(count); uniformMatrix4fv(data/value); vertexAttribPointer(size) |

## Proposed manifest

- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/rendering/rendering_ping_pong_texturing.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_transform_feedback_wave_particles.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_buffer_rebind_value_grid.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_occlusion_query_visibility_panels.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_uniform_buffer_palette_tiles.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/webgl2/webgl2_vertex_arrays_state_isolation.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/valid_buffer_texture_paired_multipass.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/samples-webgl/webgl2/webgl2_instanced_rendering_core.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/resource_typed_view_buffer_capture.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/webgl2_sampler_objects_split_filter.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/shaders_structural_coupled_passes.html`
- `/home/attekett/orca/workspaces/samples-webgl/periwinkle/agent_outputs/texture_paired_update_offscreen_composite.html`

Unmet baseline requirements: 0.
Unmet full-universe requirements: 446.

## Mutation yield

| Family | Sites | Generated | Clean | Flow changes | Image changes | Browser ms | Median ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| bounded_parameter | 80 | 10 | 9 | 5 | 9 | 3381.973289011512 | 326.07917150016874 |
| buffer_redefine_after_upload | 1 | 1 | 1 | 1 | 1 | 309.4385139993392 | 309.4385139993392 |
| compatible_buffer_switch | 4 | 1 | 1 | 1 | 1 | 314.86546600353904 | 314.86546600353904 |
| compatible_texture_update_switch | 3 | 1 | 1 | 1 | 1 | 352.3816149972845 | 352.3816149972845 |
| draw_mode | 168 | 5 | 5 | 5 | 2 | 2385.8731139844167 | 322.0895849954104 |
| framebuffer_attachment_cycle | 3 | 0 | 0 | 0 | 0 | 0 | None |
| framebuffer_retire | 2 | 0 | 0 | 0 | 0 | 0 | None |
| glsl_array_index | 1 | 0 | 0 | 0 | 0 | 0 | None |
| glsl_linked_varying_rename | 7 | 0 | 0 | 0 | 0 | 0 | None |
| glsl_loop_bound | 1 | 0 | 0 | 0 | 0 | 0 | None |
| glsl_matrix_scalar | 1 | 0 | 0 | 0 | 0 | 0 | None |
| glsl_trig_function | 8 | 1 | 1 | 0 | 1 | 333.46328799962066 | 333.46328799962066 |
| program_relink_duplicate | 7 | 0 | 0 | 0 | 0 | 0 | None |
| resource_storage | 10 | 0 | 0 | 0 | 0 | 0 | None |
| state_transition | 75 | 0 | 0 | 0 | 0 | 0 | None |
| storage_duplicate | 5 | 0 | 0 | 0 | 0 | 0 | None |
| sync_placement | 54 | 0 | 0 | 0 | 0 | 0 | None |
| texture_allocation_update_dimensions | 2 | 0 | 0 | 0 | 0 | 0 | None |
| texture_retire | 2 | 0 | 0 | 0 | 0 | 0 | None |
| texture_storage_duplicate | 3 | 0 | 0 | 0 | 0 | 0 | None |
| texture_subimage_dimension | 4 | 0 | 0 | 0 | 0 | 0 | None |
| typed_array_view_offset | 2 | 0 | 0 | 0 | 0 | 0 | None |
| vertex_attrib_offset | 3 | 0 | 0 | 0 | 0 | 0 | None |
| vertex_attrib_stride | 8 | 0 | 0 | 0 | 0 | 0 | None |
| viewport_dimension | 52 | 0 | 0 | 0 | 0 | 0 | None |
