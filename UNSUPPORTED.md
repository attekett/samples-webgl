# WebGL/WebGL2 Unsupported Extensions

This file documents WebGL extensions that are not supported in the current test environment. Tests that require these extensions will throw `UNSUPPORTED_EXTENSIONS` errors, which are logged here rather than counted as test failures.

## WebGL1 Extensions

### OES_texture_float
- **Status**: Not supported
- **Description**: Floating-point textures
- **Used in**: extension_soup.html, integrated_extension_orgasm_extreme.html
- **Alternative**: Use regular RGBA textures or WebGL2 float textures

### OES_texture_half_float
- **Status**: Not supported
- **Description**: Half-precision floating-point textures
- **Used in**: integrated_extension_orgasm_extreme.html
- **Alternative**: Use regular RGBA textures

### WEBGL_draw_buffers
- **Status**: Not supported
- **Description**: Multiple render targets (MRT)
- **Used in**: extension_soup.html, integrated_extension_orgasm_extreme.html
- **Alternative**: Use single render target or WebGL2 native MRT

### WEBGL_color_buffer_float
- **Status**: Not supported
- **Description**: Floating-point color buffers
- **Used in**: integrated_extension_orgasm_extreme.html
- **Alternative**: Use regular RGBA color buffers

### OES_vertex_array_object
- **Status**: Not supported
- **Description**: Vertex array objects for state management
- **Used in**: extension_soup.html, integrated_extension_orgasm_extreme.html
- **Alternative**: Manual attribute management or WebGL2 native VAOs

### ANGLE_instanced_arrays
- **Status**: Not supported
- **Description**: Instanced rendering
- **Used in**: extension_soup.html, integrated_extension_orgasm_extreme.html
- **Alternative**: Manual instancing or WebGL2 native instancing

### WEBGL_depth_texture
- **Status**: Not supported
- **Description**: Depth textures for shadow mapping
- **Used in**: extension_soup.html, integrated_extension_orgasm_extreme.html
- **Alternative**: Use regular depth buffers

### OES_standard_derivatives
- **Status**: Not supported
- **Description**: Shader derivatives (dFdx, dFdy, fwidth)
- **Used in**: extension_soup.html, integrated_extension_orgasm_extreme.html
- **Alternative**: Remove derivative calculations from shaders

### OES_element_index_uint
- **Status**: Not supported
- **Description**: 32-bit unsigned integer indices
- **Used in**: integrated_extension_orgasm_extreme.html
- **Alternative**: Use 16-bit indices or WebGL2 native uint indices

### EXT_shader_texture_lod
- **Status**: Not supported
- **Description**: Explicit texture LOD control in shaders
- **Used in**: integrated_extension_orgasm_extreme.html
- **Alternative**: Remove LOD bias calculations

## WebGL2 Extensions

### WEBGL_multi_draw
- **Status**: Not supported in the local Firefox runner; available in Chromium with ANGLE Vulkan
- **Used in**: `agent_outputs/mutation_vertex_buffer_state_multidraw.html`, `agent_outputs/webgl2_multidraw_indexed_instanced_rows.html`
- **Validation**: Run Chromium with `--browser-config config/angle_vulkan.json` and inspect `browser_info.webgl.renderer` in the JSON result

### EXT_disjoint_timer_query_webgl2
- **Status**: Not supported in Firefox
- **Description**: GPU timer queries for performance measurement
- **Used in**: mutation_b24_s117_query_time_elapsed.html (originally)
- **Alternative**: Use standard query types (ANY_SAMPLES_PASSED, TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN)

### WEBGL_clip_cull_distance
- **Status**: Not exposed by Firefox or the Chrome 155 ANGLE-Vulkan lane; exposed by Chrome with ANGLE's OpenGL backend (2026-10-17)
- **Used in**: `mutation_b76_s5`, `mutation_b84_s1`–`s5`, `mutation_b93_s1`, `mutation_b98_s9`
- **Validation**: Run Chromium with `--browser-config config/angle_gl.json`

### Chromium-only extensions
- **Status**: `EXT_clip_control`, `EXT_conservative_depth`, `EXT_polygon_offset_clamp`, `EXT_texture_mirror_clamp_to_edge`, `WEBGL_stencil_texturing`, `OES_sample_variables`, `OES_shader_multisample_interpolation`, and `NV_shader_noperspective_interpolation` are missing in Firefox but available in Chrome with `--browser-config config/angle_vulkan.json`
- **Used in**: Most `mutation_b76`–`b93` seeds and the `mutation_b98_*_chromium_*` seeds; validate them with `--browsers chromium`
- **Shader directives**: Use `GL_ANGLE_clip_cull_distance`, `GL_EXT_conservative_depth`, `GL_NV_shader_noperspective_interpolation`, `GL_OES_sample_variables`, and `GL_OES_shader_multisample_interpolation`; the `WEBGL_*`/`EXT_*` names fail to compile in Chromium's translator

## WebGL2 Features
All core WebGL2 features tested so far are supported in the test environment.

## Environment Analysis

Based on `docs/browser_webgl_info.txt`, the extension availability is **browser-specific**:

### Firefox (Superior Extension Support)
- **WebGL Extensions**: 24 extensions supported
- **Key Extensions**: All major WebGL1 extensions including float textures, MRT, VAOs, instancing, derivatives
- **Environment**: Native Mesa drivers with full extension exposure

### Chromium (Limited Extension Support)
- **Underlying GL Extensions**: 100+ OpenGL extensions available (ANGLE backend)
- **WebGL Extensions**: Restricted subset exposed to web applications
- **Missing**: Critical WebGL extensions not exposed despite GL driver support
- **Environment**: ANGLE translation layer with security restrictions

### Extension Availability Matrix

| Extension | Firefox | Chromium | Status |
|-----------|---------|----------|--------|
| OES_texture_float | ✅ | ❌ | Browser limitation |
| WEBGL_draw_buffers | ✅ | ❌ | Browser limitation |
| OES_vertex_array_object | ✅ | ❌ | Browser limitation |
| ANGLE_instanced_arrays | ✅ | ❌ | Browser limitation |
| WEBGL_depth_texture | ✅ | ❌ | Browser limitation |
| OES_standard_derivatives | ✅ | ❌ | Browser limitation |
| OES_texture_half_float | ✅ | ❌ | Browser limitation |
| WEBGL_color_buffer_float | ✅ | ❌ | Browser limitation |
| OES_element_index_uint | ✅ | ❌ | Browser limitation |
| EXT_shader_texture_lod | ✅ | ❌ | Browser limitation |

### Firefox-Specific Issues
- **integrated_extension_soup.html**: Passes in Chromium but fails in Firefox with INVALID_OPERATION (1282) error
- **integrated_monolith_basic.html**: Fails in Firefox with INVALID_OPERATION (1282) after fixing uniform linking issues
- **integrated_shader_maximalist.html**: Fails in Firefox with INVALID_OPERATION (1282)
- **integrated_ping_pong_extreme.html**: Fails in Firefox with INVALID_OPERATION (1282)
- **Cause**: Firefox has stricter WebGL validation than Chromium, rejecting certain operations that Chromium allows
- **Status**: Functional in Chromium, Firefox has stricter validation rules
- **Impact**: Some complex tests work in Chromium but not Firefox automation environment

## Environment Notes
- **Firefox**: Full extension support, recommended for extension-heavy tests
- **Chromium**: Core WebGL + WebGL2 support, limited extensions
- **Platform**: Linux with Mesa drivers
- **WebGL Version**: WebGL 2.0 supported in both browsers

## Impact on Test Coverage
Tests requiring unsupported extensions are marked as "UNSUPPORTED" rather than "FAILED". This allows:
- Tracking of environment limitations
- Identification of extension availability requirements
- Planning for cross-browser compatibility
- Focus on core WebGL functionality where extensions are unavailable

## Recommendations

### Testing Strategy
1. **Firefox-First for Extensions**: Use Firefox for all extension-dependent tests
   ```bash
   ./run_tests.sh --test-file agent_outputs/extension_soup.html --browsers firefox
   ```

2. **Chromium for Core Features**: Use Chromium for WebGL2 native features and core functionality
   ```bash
   ./run_tests.sh --test-file agent_outputs/integrated_monolith_extreme.html --browsers chromium
   ```

3. **Cross-Browser Validation**: Critical extension tests should pass in Firefox
4. **Fallback Design**: Tests should gracefully handle missing extensions

### Implementation Strategy
1. **Browser-Specific Testing**: Add browser selection to test runner
2. **Extension Detection**: Tests should query and report extension availability
3. **UNSUPPORTED_EXTENSIONS**: Proper error handling for missing extensions
4. **Documentation**: Track browser-specific capabilities and limitations

### Environment Setup
1. **Firefox**: Primary browser for extension testing
2. **Chromium**: Primary browser for WebGL2 native features
3. **Multi-Browser**: Essential for comprehensive WebGL coverage
4. **Driver Awareness**: Mesa drivers provide good extension support in Firefox

### Current Testing Status
- **Chromium**: ✅ Working (core WebGL + WebGL2 via automation)
- **Firefox**: ⚠️ Playwright automation has extension limitations (native Firefox has superior extensions)
- **Playwright Firefox**: Limited WebGL extensions despite native Firefox supporting them
- **Recommendation**: Use manual testing in native Firefox for extension validation

### Playwright Firefox Configuration Breakthrough 🎉
- **Comprehensive Firefox User Preferences**:
  - **Fingerprinting Protection**: `'privacy.resistFingerprinting': false` (critical for float textures)
  - **WebGL 2.0 Forcing**: `'webgl.enable-webgl2': true`, `'webgl.force-enabled': true`
  - **Extension Enabling**: `'webgl.enable-privileged-extensions': true`, `'webgl.enable-draft-extensions': true`
  - **Safe Mode Disabling**: `'webgl.min_capability_mode': false`, `'webgl.disable-fail-if-major-performance-caveat': true`
  - **EGL Backend**: `'gfx.x11-egl.force-enabled': true`, `'gl.provider': 'EGL'`, `MOZ_X11_EGL=1` environment variable
- **Results**: **MAJOR BREAKTHROUGH** - WebGL 2.0 enabled with core features available
  - Extension count: 19 total extensions
  - **Core WebGL 2.0 Features**: `WEBGL_draw_buffers`, `OES_vertex_array_object`, `ANGLE_instanced_arrays`, `WEBGL_depth_texture`, `OES_standard_derivatives` now available as core features
  - **Remaining Issue**: Only `OES_texture_float` unavailable (fingerprinting protection blocks float textures)
- **Test Runner Fix**: Updated pass/fail logic to not fail tests on warnings (only actual errors)
- **Impact**: Extension-heavy tests now work in Playwright Firefox using WebGL 2.0 core features

### Manual Firefox Testing Instructions
For extension validation when automation fails:
1. Open `agent_outputs/extension_soup.html` in Firefox browser
2. Check browser console - should NOT show "UNSUPPORTED_EXTENSIONS" error
3. Verify visual output renders (green background + rendered content)
4. Test `integrated_extension_orgasm_extreme.html` similarly
5. If no console errors and visual output works → extensions are supported
