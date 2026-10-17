# WebGL corpus coverage report

Lane: `{"browser": "firefox", "browser_identity": {"browser_name": "firefox", "browser_version": "153.0", "context": {"ignore_https_errors": true, "permissions": []}, "event_cap": 20000, "executable": {"mtime_ns": 1787558585682244431, "path": "/home/attekett/.cache/ms-playwright/firefox-1538/firefox/firefox", "size": 576240}, "fingerprint": "bf7ea348b85a6b76f4270ecae9234035fa6268f98266ae8e3e34c4045d6e6ff6", "headless": true, "launch_flags": ["--new-instance", "--no-remote"], "outcome_cap": 2048, "preferences": {"dom.ipc.keepProcessesAlive.web": 1, "dom.ipc.processCount.web_isolated": 1, "gfx.webrender.all": true, "gfx.x11-egl.force-enabled": true, "gl.provider": "EGL", "layers.acceleration.force-enabled": true, "privacy.resistFingerprinting": false, "webgl.disable-extensions": false, "webgl.disable-fail-if-major-performance-caveat": true, "webgl.enable-draft-extensions": true, "webgl.enable-privileged-extensions": true, "webgl.enable-webgl2": true, "webgl.force-enabled": true, "webgl.min_capability_mode": false}, "profiler_version": "webgl-trace-2"}, "context_versions": [2], "contexts": [{"extensions": ["EXT_color_buffer_float", "EXT_depth_clamp", "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_texture_compression_bptc", "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic", "EXT_texture_norm16", "MOZ_debug", "OES_draw_buffers_indexed", "OES_texture_float_linear", "WEBGL_compressed_texture_astc", "WEBGL_compressed_texture_etc", "WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info", "WEBGL_debug_shaders", "WEBGL_explicit_present", "WEBGL_lose_context"], "renderer": "Radeon R9 200 Series, or similar", "renderer_verified": false, "vendor": "Mozilla", "version": 2}], "outcome_cap": 2048, "profile_event_cap": 20000, "profiler_version": "webgl-trace-2", "reducer_version": "webgl-flow-3", "renderer": ["Radeon R9 200 Series, or similar"]}`

Measured baseline: 257 requirements; selection status: **selected**.

Inventory: 428 sources; 12 clean controls, 0 failed controls, 416 unmeasured; 547 static requirements observed.

## Context capability scopes

| WebGL | Supported extensions | Covered | Missing | Unsupported | Unmeasured |
|---|---|---:|---:|---:|---:|
| 1 | unobserved | 0 | 0 | 0 | 483 |
| 2 | EXT_color_buffer_float, EXT_depth_clamp, EXT_disjoint_timer_query, EXT_float_blend, EXT_texture_compression_bptc, EXT_texture_compression_rgtc, EXT_texture_filter_anisotropic, EXT_texture_norm16, MOZ_debug, OES_draw_buffers_indexed, OES_texture_float_linear, WEBGL_compressed_texture_astc, WEBGL_compressed_texture_etc, WEBGL_compressed_texture_s3tc, WEBGL_compressed_texture_s3tc_srgb, WEBGL_debug_renderer_info, WEBGL_debug_shaders, WEBGL_explicit_present, WEBGL_lose_context | 192 | 407 | 75 | 0 |

## Equal-time campaign comparison

Common observed wall time: 300916.58 ms.

| Yield | Baseline | Current |
|---|---:|---:|
| Clean variants | 548 | 540 |
| Distinct flow changes | 264 | 289 |
| Distinct pixel images | 149 | 188 |

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

- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/webgl2_buffer_rebind_value_grid.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/webgl2_occlusion_query_visibility_panels.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/webgl2_transform_feedback_wave_particles.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/texture_paired_update_offscreen_composite.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/samples-webgl/webgl2/webgl2_vertex_arrays_state_isolation.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/webgl2_uniform_buffer_palette_tiles.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/webgl2_sampler_objects_split_filter.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/resource_typed_view_buffer_capture.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/samples-webgl/rendering/rendering_ping_pong_texturing.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/shaders_structural_coupled_passes.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/samples-webgl/webgl2/webgl2_instanced_rendering_core.html`

Unmet baseline requirements: 0.
Unmet full-universe requirements: 441.

## Mutation yield

| Family | Sites | Generated | Clean | Flow changes | Image changes | Browser ms | Median ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| bounded_parameter | 80 | 10 | 9 | 5 | 9 | 4261.391899985028 | 426.0365835070843 |
| buffer_redefine_after_upload | 1 | 1 | 1 | 1 | 1 | 450.2064039988909 | 450.2064039988909 |
| compatible_buffer_switch | 4 | 2 | 2 | 2 | 2 | 748.33853598102 | 374.16926799051 |
| compatible_texture_update_switch | 3 | 2 | 2 | 2 | 2 | 726.0450700414367 | 363.02253502071835 |
| draw_mode | 168 | 11 | 11 | 11 | 8 | 4444.713375036372 | 417.01557001215406 |
| framebuffer_attachment_cycle | 3 | 3 | 3 | 3 | 0 | 1363.7387760390993 | 353.8175300054718 |
| framebuffer_retire | 2 | 2 | 2 | 0 | 0 | 762.6113519945648 | 381.3056759972824 |
| glsl_array_index | 1 | 1 | 1 | 0 | 1 | 364.0913429844659 | 364.0913429844659 |
| glsl_linked_varying_rename | 7 | 5 | 5 | 0 | 0 | 2471.3705250178464 | 476.57789100776426 |
| glsl_loop_bound | 1 | 1 | 1 | 0 | 1 | 346.54440902522765 | 346.54440902522765 |
| glsl_matrix_scalar | 1 | 1 | 1 | 0 | 1 | 366.1449619976338 | 366.1449619976338 |
| glsl_trig_function | 8 | 5 | 5 | 0 | 4 | 2098.1424499477725 | 400.42990597430617 |
| mixed | 0 | 441 | 435 | 254 | 168 | 249869.7315546451 | 405.3357880038675 |
| program_relink_duplicate | 7 | 7 | 7 | 7 | 0 | 3175.5106329801492 | 401.8745979992673 |
| resource_storage | 10 | 2 | 2 | 1 | 0 | 724.6790859790053 | 362.33954298950266 |
| state_transition | 75 | 12 | 12 | 12 | 0 | 5076.729684049496 | 404.67033949971665 |
| storage_duplicate | 5 | 2 | 2 | 2 | 0 | 932.737028982956 | 466.368514491478 |
| sync_placement | 54 | 10 | 10 | 0 | 0 | 4032.3463100066874 | 369.15153049631044 |
| texture_allocation_update_dimensions | 2 | 2 | 2 | 0 | 2 | 747.8114820260089 | 373.90574101300444 |
| texture_retire | 2 | 2 | 2 | 2 | 0 | 791.5574490034487 | 395.77872450172435 |
| texture_storage_duplicate | 3 | 2 | 2 | 2 | 0 | 823.6340549774468 | 411.8170274887234 |
| texture_subimage_dimension | 4 | 2 | 2 | 0 | 1 | 813.8194560015108 | 406.9097280007554 |
| typed_array_view_offset | 2 | 2 | 2 | 0 | 2 | 722.5629209715407 | 361.28146048577037 |
| vertex_attrib_offset | 3 | 2 | 2 | 2 | 2 | 1172.6091130112763 | 586.3045565056382 |
| vertex_attrib_stride | 8 | 5 | 5 | 5 | 1 | 2002.7650030096993 | 405.12277698144317 |
| viewport_dimension | 52 | 12 | 12 | 0 | 11 | 4880.963898031041 | 375.76546949276235 |
