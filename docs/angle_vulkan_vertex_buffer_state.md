# ANGLE Vulkan vertex-buffer state coverage

`agent_outputs/mutation_vertex_buffer_state_multidraw.html` exercises a shared vertex buffer through two VAOs, two programs with different active attribute slots, zero and nonzero `WEBGL_multi_draw` counts, attribute enable/disable changes, and repeated small/large `bufferData` replacements. It draws two colored triangles as a visual check. The seed is aimed at stale vertex-buffer binding and invalidation paths, not at reproducing one specific UAF sequence.

Run with:

```bash
./run_tests.sh --test-file agent_outputs/mutation_vertex_buffer_state_multidraw.html --browsers chromium --chromium-path /usr/bin/google-chrome --browser-config config/angle_vulkan.json
```

Require `passed: true`, empty console and error arrays, a nonblank screenshot, `WEBGL_multi_draw` in `browser_info.webgl.extensions`, and `Vulkan` in `browser_info.webgl.renderer`. Firefox in the local runner does not expose this extension. A clean local run validates the seed and backend; detecting a driver memory error still requires a sanitizer-equipped campaign browser and driver.
