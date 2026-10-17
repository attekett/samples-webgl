# WebGL corpus coverage report

Lane: `{"browser": "firefox", "browser_identity": {"browser_name": "firefox", "browser_version": "153.0", "context": {"ignore_https_errors": true, "permissions": []}, "event_cap": 20000, "executable": {"mtime_ns": 1787558585682244431, "path": "/home/attekett/.cache/ms-playwright/firefox-1538/firefox/firefox", "size": 576240}, "fingerprint": "bf7ea348b85a6b76f4270ecae9234035fa6268f98266ae8e3e34c4045d6e6ff6", "headless": true, "launch_flags": ["--new-instance", "--no-remote"], "outcome_cap": 2048, "preferences": {"dom.ipc.keepProcessesAlive.web": 1, "dom.ipc.processCount.web_isolated": 1, "gfx.webrender.all": true, "gfx.x11-egl.force-enabled": true, "gl.provider": "EGL", "layers.acceleration.force-enabled": true, "privacy.resistFingerprinting": false, "webgl.disable-extensions": false, "webgl.disable-fail-if-major-performance-caveat": true, "webgl.enable-draft-extensions": true, "webgl.enable-privileged-extensions": true, "webgl.enable-webgl2": true, "webgl.force-enabled": true, "webgl.min_capability_mode": false}, "profiler_version": "webgl-trace-2"}, "context_versions": [2], "contexts": [{"extensions": ["EXT_color_buffer_float", "EXT_depth_clamp", "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_texture_compression_bptc", "EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic", "EXT_texture_norm16", "MOZ_debug", "OES_draw_buffers_indexed", "OES_texture_float_linear", "WEBGL_compressed_texture_astc", "WEBGL_compressed_texture_etc", "WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info", "WEBGL_debug_shaders", "WEBGL_explicit_present", "WEBGL_lose_context"], "renderer": "Radeon R9 200 Series, or similar", "renderer_verified": false, "vendor": "Mozilla", "version": 2}], "outcome_cap": 2048, "profile_event_cap": 20000, "profiler_version": "webgl-trace-2", "reducer_version": "webgl-flow-3", "renderer": ["Radeon R9 200 Series, or similar"]}`

Measured baseline: 184 requirements; selection status: **provisional**.

Inventory: None sources; None clean controls, None failed controls, None unmeasured; 0 static requirements observed.

## Context capability scopes

| WebGL | Supported extensions | Covered | Missing | Unsupported | Unmeasured |
|---|---|---:|---:|---:|---:|
| 1 | unobserved | 0 | 0 | 0 | 483 |
| 2 | EXT_color_buffer_float, EXT_depth_clamp, EXT_disjoint_timer_query, EXT_float_blend, EXT_texture_compression_bptc, EXT_texture_compression_rgtc, EXT_texture_filter_anisotropic, EXT_texture_norm16, MOZ_debug, OES_draw_buffers_indexed, OES_texture_float_linear, WEBGL_compressed_texture_astc, WEBGL_compressed_texture_etc, WEBGL_compressed_texture_s3tc, WEBGL_compressed_texture_s3tc_srgb, WEBGL_debug_renderer_info, WEBGL_debug_shaders, WEBGL_explicit_present, WEBGL_lose_context | 139 | 460 | 75 | 0 |

## Equal-time campaign comparison

Common observed wall time: 300730.174 ms.

| Yield | Baseline | Current |
|---|---:|---:|
| Clean variants | 548 | 608 |
| Distinct flow changes | 264 | 286 |
| Distinct pixel images | 149 | 158 |

Baseline requirements preserved: **yes**.
Each yield preserved: **yes**.
Adoption eligible: **no**.

## Per-seed edit-site coverage

| Source | Candidate sites by family | Direct argument sites | Static gaps for observed methods (examples) |
|---|---|---:|---|
| `resource_typed_view_buffer_capture.html` | bounded_parameter:6, buffer_redefine_after_upload:1, compatible_buffer_switch:2, draw_mode:12, program_relink_duplicate:1, resource_storage:6, state_transition:5, storage_duplicate:3, sync_placement:4, typed_array_view_offset:1, vertex_attrib_offset:2, vertex_attrib_stride:2, viewport_dimension:2 | 15 | bufferSubData(data); bufferSubData(data) [wrapper only]; bindBuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program) |
| `shaders_structural_coupled_passes.html` | bounded_parameter:6, draw_mode:12, glsl_array_index:1, glsl_linked_varying_rename:1, glsl_loop_bound:1, glsl_matrix_scalar:1, program_relink_duplicate:1, state_transition:2, sync_placement:4, vertex_attrib_stride:1, viewport_dimension:2 | 9 | bufferData(data/size); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; bufferData(target); vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `texture_paired_update_offscreen_composite.html` | bounded_parameter:9, compatible_texture_update_switch:1, draw_mode:18, framebuffer_attachment_cycle:1, framebuffer_retire:1, glsl_linked_varying_rename:1, glsl_trig_function:1, program_relink_duplicate:1, state_transition:9, sync_placement:6, texture_allocation_update_dimensions:1, texture_retire:1, texture_storage_duplicate:1, texture_subimage_dimension:2, vertex_attrib_stride:1, viewport_dimension:6 | 19 | bufferData(data/size); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; bindFramebuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `valid_buffer_texture_paired_multipass.html` | bounded_parameter:6, compatible_buffer_switch:2, compatible_texture_update_switch:2, draw_mode:12, framebuffer_attachment_cycle:1, framebuffer_retire:1, glsl_linked_varying_rename:1, program_relink_duplicate:1, resource_storage:4, state_transition:12, storage_duplicate:2, sync_placement:4, texture_allocation_update_dimensions:1, texture_retire:1, texture_subimage_dimension:2, typed_array_view_offset:1, vertex_attrib_stride:2, viewport_dimension:4 | 20 | bufferSubData(data); bindBuffer(target) [wrapper only]; vertexAttribPointer(size); attachShader(program) |
| `rendering_ping_pong_texturing.html` | bounded_parameter:6, draw_mode:12, framebuffer_attachment_cycle:1, program_relink_duplicate:1, state_transition:7, sync_placement:2, texture_storage_duplicate:2, viewport_dimension:4 | 8 | bufferData(data/size); activeTexture(texture); bindBuffer(target) [wrapper only]; bindBuffer(buffer) [wrapper only]; vertexAttribPointer(size); attachShader(program); attachShader(shader) |
| `webgl2_instanced_rendering_core.html` | bounded_parameter:6, draw_mode:6, glsl_linked_varying_rename:1, program_relink_duplicate:1, state_transition:6, sync_placement:2, viewport_dimension:8 | 13 | bufferData(data/size); vertexAttribPointer(size) |
| `webgl2_vertex_arrays_state_isolation.html` | draw_mode:6, glsl_linked_varying_rename:3, glsl_trig_function:2, program_relink_duplicate:1, state_transition:1, viewport_dimension:8 | 11 | bufferData(data/size); bindBuffer(target); drawElements(count); uniformMatrix4fv(data/value); vertexAttribPointer(size) |

## Proposed manifest

- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/valid_buffer_texture_paired_multipass.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/samples-webgl/webgl2/webgl2_vertex_arrays_state_isolation.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/samples-webgl/rendering/rendering_ping_pong_texturing.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/samples-webgl/webgl2/webgl2_instanced_rendering_core.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/shaders_structural_coupled_passes.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/resource_typed_view_buffer_capture.html`
- `/home/attekett/orca/workspaces/samples-webgl/albacore/agent_outputs/texture_paired_update_offscreen_composite.html`

Unmet baseline requirements: 0.
Unmet full-universe requirements: 512.

## Mutation yield

| Family | Sites | Generated | Clean | Flow changes | Image changes | Browser ms | Median ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| bounded_parameter | 39 | 6 | 6 | 4 | 6 | 2075.0735119800083 | 332.9712244885741 |
| buffer_redefine_after_upload | 1 | 1 | 1 | 1 | 1 | 267.3251380037982 | 267.3251380037982 |
| compatible_buffer_switch | 4 | 2 | 2 | 2 | 2 | 626.5350290050264 | 313.2675145025132 |
| compatible_texture_update_switch | 3 | 2 | 2 | 2 | 2 | 609.5808839891106 | 304.7904419945553 |
| draw_mode | 78 | 7 | 7 | 7 | 6 | 2244.702631025575 | 302.768544992432 |
| framebuffer_attachment_cycle | 3 | 3 | 3 | 3 | 0 | 931.0475320089608 | 302.9223240155261 |
| framebuffer_retire | 2 | 2 | 2 | 0 | 0 | 588.2865750172641 | 294.14328750863206 |
| glsl_array_index | 1 | 1 | 1 | 0 | 1 | 277.6326120074373 | 277.6326120074373 |
| glsl_linked_varying_rename | 7 | 5 | 5 | 0 | 0 | 1777.4172889476176 | 318.34163700114004 |
| glsl_loop_bound | 1 | 1 | 1 | 0 | 1 | 274.4223100016825 | 274.4223100016825 |
| glsl_matrix_scalar | 1 | 1 | 1 | 0 | 1 | 283.882766001625 | 283.882766001625 |
| glsl_trig_function | 3 | 2 | 2 | 0 | 1 | 631.6669349907897 | 315.83346749539487 |
| mixed | 0 | 537 | 529 | 268 | 150 | 271918.5180323111 | 369.1527080081869 |
| program_relink_duplicate | 7 | 7 | 7 | 7 | 0 | 2395.0854710128624 | 315.2287580014672 |
| resource_storage | 10 | 2 | 2 | 1 | 0 | 587.3224660172127 | 293.66123300860636 |
| state_transition | 42 | 7 | 7 | 7 | 0 | 2191.3290280208457 | 309.95284000528045 |
| storage_duplicate | 5 | 2 | 2 | 2 | 0 | 578.7416069942992 | 289.3708034971496 |
| sync_placement | 22 | 6 | 6 | 0 | 0 | 1790.7795939827338 | 300.2387899905443 |
| texture_allocation_update_dimensions | 2 | 2 | 2 | 0 | 2 | 609.6598820295185 | 304.82994101475924 |
| texture_retire | 2 | 2 | 2 | 2 | 0 | 595.4283100145403 | 297.71415500727016 |
| texture_storage_duplicate | 3 | 2 | 2 | 2 | 0 | 656.8682120123412 | 328.4341060061706 |
| texture_subimage_dimension | 4 | 2 | 2 | 0 | 1 | 650.3157769620884 | 325.1578884810442 |
| typed_array_view_offset | 2 | 2 | 2 | 0 | 2 | 937.413684965577 | 468.7068424827885 |
| vertex_attrib_offset | 2 | 1 | 1 | 1 | 1 | 329.9147169745993 | 329.9147169745993 |
| vertex_attrib_stride | 6 | 4 | 4 | 4 | 0 | 1180.7839670218527 | 295.78953600139357 |
| viewport_dimension | 34 | 7 | 7 | 0 | 6 | 2292.773976980243 | 321.99075698736124 |
