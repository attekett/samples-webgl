# Coverage-model blind spots (2026-10-17)

The corpus coverage model has two parts. `docs/feature_categories.json` defines 33 categories and `docs/interaction_topology.json` defines 98 edges between them. This report lists the WebGL features that model cannot see. Before `WEBGL_multi_draw` had a category and edges, seeds that used it counted toward nothing; the features below are in the same position.

## Applied 2026-10-18

The JSON-only proposals are now in the model: 54 categories (was 33) and 252 edges (was 98).

- **New categories (21):** rows 1-6, 8-20 and the table under "Proposed new categories". `srgb` leaves out `SRGB_ALPHA`, which is not a WebGL2 constant.
- **Defects fixed (rows 26, 27, 29, 30):**
  - `transform_feedback` no longer lists `bindBufferBase`, `bindBufferRange` or `getIndexedParameter`, so it matches on TF methods only.
  - `ubo` and `texture_3d` now set `requires_any_constant`.
  - `ext_float_textures` drops the WebGL1 names.
  - `glsl_builtins` drops `textureGather` and `textureGatherOffset`.
  - `ext_disjoint_timer_query` gains the `*QueryEXT` methods.
- **Edges:** every group in both edge tables, except edges to categories that do not exist (`depth_textures`, `context_loss`, `multi_context`). `depth_stencil`–`ext_draw_buffers_indexed` was removed, as proposed.
- **Detector fix:** the new constant gates exposed a resolver blind spot. Numeric enums (`0x8C8E`, `35345`) and `WebGL2RenderingContext.X` were never resolved to constant names. They now resolve wherever the parameter is a `GLenum` and the value names exactly one constant. The `api_audit` per-file cache now carries an analyzer version, so a code change invalidates cached results.
- **Seed count changes:**
  - `ubo` 144 → 56 and `transform_feedback` 145 → 110; the seeds that dropped out were the shared-method false matches.
  - `texture_3d` 134 → 62. Six `mutation_b16_s7*` and `mutation_b28_s13*` "3dtex" seeds allocate `TEXTURE_2D_ARRAY` (35866) and sample it as `sampler3D`, so they are not 3D-texture seeds.
  - `texture_arrays` 75 → 95 and `integer_textures` 57 → 69, because numeric enums now resolve.
- **Result (`api_audit --combination-matrix`):**

  | | Covered | Gaps | Gaps involving a zero-seed category | Low diversity |
  |---|---|---|---|---|
  | 2-way | 231/252 | 21 | 15 | 18 |
  | 3-way | 1719/2440 | 721 | 280 | 64 |
  | 4-way | 11792/24178 | 12386 | 4047 | 318 |

  The zero-seed categories are `ext_multiview`, `ext_blend_func_extended`, `ext_renderable_formats` and `ext_debug_info`.

**Not applied:**

- `context_loss` (row 7): seeds may not call `loseContext`, so the category could never be matched.
- `depth_textures` (row 21): it needs a per-call constant gate.
- Rows 22-25 and 32-43, and row 28 (`enable(cap)` OR gate): these need detector changes.
- Row 31 (the two `UBIQUITOUS` sets): this is a code change.
- The surface edits in rows 8 and 30 (`gl_ClipDistance` and the other variables; removing `frexp`/`ldexp`).

## Summary

Six finder lanes (extensions, core API, a WebGL2 spec walk, WebGL1/context, GLSL and topology) reported 132 raw items. After merging duplicates and dropping items that are already mapped, the prioritised table has **46 rows**:

- **30 unmapped or under-mapped features**: rows 1-25 and 42-46.
- **8 model defects** that over-count or under-count existing categories: rows 26-33.
- **8 GLSL-construct rows**, which need a new detector gate before they can be counted: rows 34-41.

The edge sections propose 23 edge groups for the new categories and 20 between existing categories. **14 items** are deliberately left unmapped, each with its reason.

Among the unmapped features, **12 already have seeds that the model ignores**:

| Feature | Seeds |
|---|---|
| `RASTERIZER_DISCARD` | 86 |
| `EXT_clip_control` | 20 |
| `EXT_float_blend` | 18 |
| `TEXTURE_COMPARE_MODE` (shadow compare) | 11 |
| `TEXTURE_CUBE_MAP_POSITIVE_*` | 9 |
| `WEBGL_clip_cull_distance` | 8 |
| `EXT_conservative_depth` | 8 |
| `EXT_polygon_offset_clamp` | 6 |
| `WEBGL_stencil_texturing` | 6 |
| Framebuffer invalidation | 3 + 2 |
| sRGB formats | 2 |
| Four further Chrome-only extensions | 2 each |

**11 extensions have zero seeds even though a lane exposes them:**

- `EXT_depth_clamp`, `WEBGL_debug_shaders` and `WEBGL_debug_renderer_info`: exposed on both Firefox and Chrome.
- `EXT_texture_norm16`: exposed on Firefox 153 and Chrome.
- `OVR_multiview2`, `WEBGL_polygon_mode`, `WEBGL_blend_func_extended`, `EXT_render_snorm`, `WEBGL_render_shared_exponent` and `EXT_color_buffer_half_float`: exposed on Chrome ANGLE-Vulkan.
- `WEBGL_lose_context`: exposed on every lane. One seed requests it but never calls `loseContext`.

The model reports 100% 3-way and 4-way coverage (526/526 and 2947/2947 connected combos), and that figure is an artefact of these gaps. The topology lane applied 66 candidate edges together, and the result was 3 new zero-seed 3-way gaps and 242 new zero-seed 4-way gaps.

**Corrections to the finder reports, verified against the files:**

- Two lanes said no lane exposes `WEBGL_blend_func_extended`, `EXT_texture_norm16` and `OVR_multiview2`. That is wrong. All three are in the Chrome 155 ANGLE-Vulkan context list (`docs/snapshots/webgl-corpus-chrome-2026-10-16.md:3`). `EXT_texture_norm16` is also in the Firefox 153 list (`docs/snapshots/webgl-corpus-expanded-firefox-comparison-300s-2026-10-17.md:3`). `docs/browser_webgl_info.txt` is older than both snapshots.
- Firefox 153 exposes `EXT_disjoint_timer_query` (the WebGL1 name) inside a WebGL2 context, so that extension is not dead on every lane.
- The cheap fix "add `EXT_float_blend` to `ext_color_buffer_float`" changes nothing. All 18 `EXT_float_blend` seeds already load `EXT_color_buffer_float`, so they already match that category. `EXT_float_blend` needs its own category.

**Where the numbers come from:**

- Corpus counts are seed-file counts from `grep`, deduplicated by realpath over `samples-webgl/` and `agent_outputs/` (572 unique seeds). The counts cited above were re-checked for this report.
- Gap deltas ("+N 3-way") were measured by the webgl2-spec and topology lanes, using in-memory overlays on the real `detect_features`/`compute_matrix`. I did not re-run them. Each delta was measured alone, so deltas do not add up across proposals.

## Prioritised table

Priority levels:

- **High**: seeds already use the feature, or a lane exposes it, and the fix is a JSON change to the categories or topology.
- **Medium**: as High, but the fix needs a detector or engine change. Model defects that skew existing counts are also Medium.
- **Low**: no lane exposes the feature, or the measured effect on gaps is zero.

Lane abbreviations: FF is Firefox 153, CV is Chrome 155 ANGLE-Vulkan, CG is Chrome ANGLE-GL (no extension list has been recorded for CG).

| # | Feature | Kind | Why it is invisible | Corpus usage | Lanes | Recommended mapping change | Pri |
|---|---|---|---|---|---|---|---|
| 1 | `RASTERIZER_DISCARD` | constant | It is in no category. `enable`/`disable` resolve only to `pipeline_state`, which matches every seed. | 86 seeds (82 with TF) | all | New `rasterizer_discard` category gated on the constant. Edges to TF, query, draw_calls, fbo, depth_stencil. | High |
| 2 | `EXT_clip_control` | extension | No category. | 20 seeds | CV | New `ext_clip_control` category. | High |
| 3 | `EXT_float_blend` | extension | No category. Folding it into `ext_color_buffer_float` adds nothing (all 18 seeds already match that category). | 18 seeds | FF, CV | New `ext_float_blend` category with edges blending, ext_color_buffer_float, mrt, ext_draw_buffers_indexed. | High |
| 4 | Framebuffer invalidation (`invalidateFramebuffer`, `invalidateSubFramebuffer`) | method | Folded into `fbo`, which matches 59% of seeds. | 3 / 2 seeds | all | New `fbo_invalidate` category. Measured +1 2-way, +29 3-way, +334 4-way gaps, the largest single blind spot. | High |
| 5 | sRGB formats (`SRGB8`, `SRGB8_ALPHA8`, `FRAMEBUFFER_ATTACHMENT_COLOR_ENCODING`) | constant | Format constants gate nothing. | 2 seeds | all | New `srgb` category gated on the constants. Measured +26 3-way, +259 4-way. | High |
| 6 | Shadow compare (`TEXTURE_COMPARE_MODE`/`FUNC`, `COMPARE_REF_TO_TEXTURE`) | constant | `sampler` has `constants: []`. `texture_ops` matches on methods only. | 11 seeds | all | New `shadow_compare` category. Measured +9 3-way, +129 4-way. | High |
| 7 | `WEBGL_lose_context` / context loss and restore | extension | No category. `isContextLost` sits in `pipeline_state` (100% match). | 1 seed requests it; 0 calls to `loseContext`/`restoreContext`; 0 event listeners | all (probe: lose and restore both work) | New `context_loss` category. This is the clearest UAF-style lifecycle surface. | High |
| 8 | `WEBGL_clip_cull_distance` | extension | No category. `gl_ClipDistance`/`gl_CullDistance` are missing from the surface's GLSL variables. | 8 seeds; `gl_CullDistance` 0; 3 of 11 constants used | CG only | New `ext_clip_cull_distance` category, plus the surface variables. | High |
| 9 | `EXT_conservative_depth`, `OES_sample_variables`, `OES_shader_multisample_interpolation`, `NV_shader_noperspective_interpolation` | extension | No category. Shader-only extensions with no JS methods. | 8 / 2 / 2 / 2 seeds | CV | Two categories: `ext_conservative_depth` and `ext_sample_shading` (with noperspective folded into the latter or its own). | High |
| 10 | `EXT_polygon_offset_clamp`, `WEBGL_stencil_texturing`, `EXT_texture_mirror_clamp_to_edge` | extension | No category. | 6 / 6 / 2 seeds | CV | `ext_rasterizer_ext` (polygon_offset_clamp with depth_clamp and polygon_mode) and `ext_texture_params` (stencil_texturing with mirror_clamp). | High |
| 11 | `EXT_depth_clamp` | extension | No category. | 0 seeds | FF, CV | Fold into `ext_rasterizer_ext`, then seed it. It runs on Firefox too. | High |
| 12 | `OVR_multiview2`, `WEBGL_polygon_mode`, `WEBGL_blend_func_extended` | extension | No category. | 0 seeds | CV | New `ext_multiview` and `ext_blend_func_extended` categories; `WEBGL_polygon_mode` goes into `ext_rasterizer_ext`. Seed first. | High |
| 13 | `EXT_texture_norm16`, `EXT_render_snorm`, `WEBGL_render_shared_exponent`, `EXT_color_buffer_half_float` | extension | No category for the first three. The half-float extension is listed in `ext_color_buffer_float` but has no seed. | 0 seeds each | norm16: FF, CV; others: CV | New `ext_renderable_formats` category (norm16, snorm, shared_exponent). Write one half-float seed. | High |
| 14 | `WEBGL_debug_shaders` (`getTranslatedShaderSource`), `WEBGL_debug_renderer_info` | extension | No category. | 0 seeds | FF, CV | New `ext_debug_info` category. `getTranslatedShaderSource` drives ANGLE translator output. | High |
| 15 | Cube maps (`TEXTURE_CUBE_MAP_POSITIVE_X`..`NEGATIVE_Z`, `samplerCube`) | constant | `TEXTURE_CUBE_MAP` is a non-gating `texture_ops` constant, so cube maps cannot be told apart from 2D. | 9 seeds | all | New `texture_cube` category. | High |
| 16 | Mip/LOD range (`TEXTURE_BASE_LEVEL`, `TEXTURE_MAX_LEVEL`, `TEXTURE_MIN_LOD`, `TEXTURE_MAX_LOD`) | constant | Constants do not gate. | 42 seeds | all | New `texture_lod_range` category. Measured +16 4-way. | High |
| 17 | Integer vertex attributes (`vertexAttribIPointer`, `vertexAttribI4*`) | method | Inside `attributes`, which is ubiquitous and skipped. | 23 seeds | all | New `integer_attributes` category. Measured +2 3-way, +45 4-way. | High |
| 18 | Buffer copy and readback (`copyBufferSubData`, `getBufferSubData`) | method | Inside `buffer_ops`, which matches 97% of seeds and is skipped. | 66 seeds | all | New `buffer_copy_readback` category. Measured +2 3-way, +22 4-way. | High |
| 19 | Multisample renderbuffers (`renderbufferStorageMultisample`) | method | Any `createRenderbuffer` call already matches `renderbuffer`. | 28 seeds | all | New `multisample_rb` category. Measured +44 4-way. | High |
| 20 | Pixel buffer objects (`PIXEL_PACK_BUFFER`, `PIXEL_UNPACK_BUFFER`) | constant | Listed in `buffer_ops` but they gate nothing. | 38 pack / 6 unpack seeds | all | New `pbo` category. Measured +7 4-way. The unpack path has only 4-6 seeds. | High |
| 21 | Depth textures (`DEPTH_COMPONENT*`, `DEPTH24_STENCIL8`, `DEPTH32F_STENCIL8` in `tex*` calls) | constant | `depth_stencil` covers test state only, not depth-format textures. | 29 seeds in `tex*` calls, 72 in `renderbufferStorage` | all | New `depth_textures` category. This needs per-call constant gating, because `constants_found` is file-wide. | Medium |
| 22 | Context creation attributes (`alpha`, `premultipliedAlpha`, `preserveDrawingBuffer`, `stencil`, `desynchronized`, `powerPreference`, `failIfMajorPerformanceCaveat`) | spec-area | `call_analysis.py` skips `getContext`, and `context.py` reads only the context-type string, never the attribute dictionary. | 174 seeds pass a dictionary, but apart from `antialias:false` (the boilerplate) almost nothing else is set: no seed sets `alpha:false`, `premultipliedAlpha:false` or `preserveDrawingBuffer:true` | all (probed) | New `context_attributes` category from `ctxattr:` pseudo-constants. Relevant crbugs: 40050541, 40053883. | Medium |
| 23 | Drawing buffer: `drawingBufferStorage`, canvas resize, `drawingBufferColorSpace`/`unpackColorSpace`, `drawingBufferFormat` | spec-area | `drawingBufferStorage` is misfiled under `fbo`. The surface JSON has no IDL attributes, and property assignments are not calls, so the detector sees none of the rest. | 1 seed each for `drawingBufferStorage` and canvas resize; 0 for the colour-space attributes | `drawingBufferStorage`: Chrome lanes only; the rest: all | Move `drawingBufferStorage` out of `fbo` into a new `drawing_buffer` category that also detects canvas resize and the attribute writes. | Medium |
| 24 | Texture uploads from DOM sources (`ImageData`, canvas, `ImageBitmap`, `OffscreenCanvas`, `VideoFrame`) and the `UNPACK_*_WEBGL` pixel-store parameters | spec-area | `texture_ops` matches on the method name whatever the source argument. `pixel_ops` omits the `*_WEBGL` constants. | 0 DOM-source uploads; the `UNPACK_*_WEBGL` constants appear in 2 seeds | all (probed: all seven source kinds return NO_ERROR) | New `dom_texture_sources` category (classify the source argument) and new `unpack_webgl_params` category. | Medium |
| 25 | Multiple contexts and OffscreenCanvas contexts | spec-area | `context.py` merges every `getContext` result into one context set. | 2 multi-context seeds; 0 OffscreenCanvas | all | New `multi_context` category (`ctx:multiple`, `ctx:offscreen`). | Medium |
| 26 | Overlap between `ubo` and `transform_feedback` on `bindBufferBase`, `bindBufferRange`, `getIndexedParameter` | defect | Both categories list the three methods with `min_methods_for_match:1`. | 86 of 141 indexed-binding seeds have no UBO-specific call (verified); 32 have no TF call | n/a | Drop the shared methods from both categories, or gate each on `UNIFORM_BUFFER` / `TRANSFORM_FEEDBACK_BUFFER`. `ubo` counts are inflated about 2.7x. Measured +2 hidden 4-way. | Medium |
| 27 | `texture_3d` matches 2D-array-only seeds | defect | Shares `texImage3D` and `texStorage3D` with `texture_arrays`, and has no constant gate. | 74 of 132 `*3D` seeds never mention `TEXTURE_3D` (verified) | n/a | Set `requires_any_constant: true` on `texture_3d`. Measured +3 hidden 4-way. | Medium |
| 28 | Capability constants used only through `enable(cap)` | defect | `depth_stencil`, `blending` and `rasterizer_state` list constants without a gate, so `enable(DEPTH_TEST)` alone does not match them (`feature_detection.py:110-122`). | 54 seeds use `DEPTH_TEST` without matching `depth_stencil`; 47 `CULL_FACE`; 24 `BLEND` | all | Add an OR gate (`match_if_any_constant`). This under-counts rather than hides gaps. | Medium |
| 29 | `ext_float_textures` counts WebGL1-only names | defect | `OES_texture_float` and `OES_texture_half_float` return null in WebGL2 on every lane, but `requires_any_extension` counts the bare `getExtension` call. | 26 of 28 matches come only via `OES_texture_float_linear` | n/a | Drop the WebGL1 names from the category, or report coverage with `--passed-only` per lane. | Medium |
| 30 | GLSL names that are ESSL 3.10, not 3.00 | defect | `glsl_builtins` lists `textureGather` and `textureGatherOffset`; the surface lists `frexp` and `ldexp`. None of them compile in WebGL2. | 1 seed for `textureGather`; the `frexp`/`ldexp` hits are user-defined functions | none | Remove all four. Stop `_match_builtins` from counting function definitions as uses. | Medium |
| 31 | Two different `UBIQUITOUS` sets | defect | `feature_coverage.py:69` and `combination_matrix.py:14-15` disagree: `pixel_ops` is in one set only; `buffer_ops` and `pipeline_state` are in the other only. | n/a | n/a | Reconcile the two sets. `pipeline_state`, a 572/572 match, currently inflates combos through its edge to `query`. | Medium |
| 32 | Shader-source extraction misses some shaders | defect | `glsl.py` drops `${}` substitutions. `context.py` misses closure helpers and ternary initialisers. | 40 seeds yield no GLSL; 46 lose a `#version 300 es` shader | n/a | Fall back to scanning string literals for `void main` / `#version`. This is a prerequisite for rows 34-41. | Medium |
| 33 | Extension alias by assignment (`ext = gl.getExtension(...)`) | defect | `context.py` Pattern 1 handles only `const x = gl.getExtension(...)`. | `extensions_instanced_rendering_webgl1.html` gets `extension_methods={}` | n/a | Also handle the assignment form. | Medium |
| 34 | GLSL constructs in general (qualifiers, statements, directives, built-in variables) | spec-area | `is_category_match` gates on GLSL function names only. `extract_glsl_variables` output never reaches any category. | 563 seeds have shaders | n/a | Add `glsl_patterns` / `min_glsl_patterns_for_match` and a `glsl_variables` gate. This is a prerequisite for rows 35-41. | Medium |
| 35 | Preprocessor (`#define`, `#if`, `#undef`, `#error`, `#line`, `#pragma`, `defined`, `__LINE__`) | glsl | No GLSL gate. | 1 seed | all | New `glsl_preprocessor` category. | Medium |
| 36 | Control flow (`switch`, `while`, `do-while`, `inout`) | glsl | No GLSL gate. | `switch` 0, `do-while` 0, `inout` 2 | all | New `glsl_control_flow` category. | Medium |
| 37 | Interpolation and invariance qualifiers (`flat`, `smooth`, `centroid`, `invariant`, `#pragma STDGL invariant`) | glsl | No GLSL gate. | `flat` 58; `centroid` 2; `invariant` 0 | all | New `glsl_interpolation` category. | Medium |
| 38 | Uniform block layout (`row_major`, `column_major`, block arrays, default layout statement, `shared`/`packed` negative probes) | glsl | `ubo` matches JS calls only. | `row_major` 0; block arrays 0 | all | New `glsl_ubo_layout` category. | Medium |
| 39 | `discard` and `gl_FragDepth` | glsl | No GLSL gate. | 4 / 13 seeds | all | New `glsl_fragment_kill_depth` category. | Medium |
| 40 | Integer and bitwise operators, `uint` types | glsl | No GLSL gate. | 26 / 46 seeds | all | New `glsl_integer_ops` category. | Medium |
| 41 | Aggregates (`struct`, arrays, `.length()`) and the WebGL must-fail rules (reserved `webgl_` prefix, 1024-character token limit, struct nesting depth) | glsl | No GLSL gate. | `struct` 2; must-fail probes 0 | all | New `glsl_aggregates` category, plus compile-only negative probes. | Medium |
| 42 | Presentation and readback (`toDataURL`, `drawImage` of the WebGL canvas, the `requestAnimationFrame` frame boundary) | spec-area | Receivers other than `gl` are ignored. | rAF 13 seeds; `toDataURL`/`drawImage` 0 | all | Add these as pseudo-methods in `drawing_buffer`. Restrict `context_vars` to the WebGL context strings. | Medium |
| 43 | Primitive restart and cross-frame result polling | spec-area | These are value-level and structural behaviours that no method or constant marks. | 3 restart seeds; most query/sync seeds poll within one frame | all | Optional detectors in `value_classes.py`. Otherwise leave a lint note. | Low |
| 44 | `clearBuffer*` family | method | Inside the ubiquitous `draw_calls`. | 64 seeds | all | Optional `clear_buffer` category. Measured 0 gaps at 2, 3 and 4 way, so for display only. | Low |
| 45 | Packed and snorm formats (`RGB10_A2`, `RGB565`, `RGB5_A1`, `RGBA4`, `*_SNORM`, `RGB9_E5`, `R11F_G11F_B10F`) | constant | No category gates on them. | 1-16 seeds | all | Optional `packed_formats` category. Not measured. | Low |
| 46 | Extension constants that are mapped only by extension name (timer query, compressed formats, half float) | constant | The categories list extension names but `constants: []`. | 25 of 28 ASTC constants and 8 of 10 ETC constants are unused | ASTC/ETC: FF only | Add the constants for diagnostics only. The real gap is the missing ETC and ASTC seeds. | Low |

## Proposed new categories

All entries use the existing schema in `docs/feature_categories.json`. Extension names, methods and constants were checked against `docs/webgl_api_surface.json`.

### Extension categories (JSON-only)

| Category | `extensions` | `extension_methods` | `constants` | Gate |
|---|---|---|---|---|
| `ext_clip_control` | `EXT_clip_control` | `clipControlEXT` | `LOWER_LEFT_EXT`, `UPPER_LEFT_EXT`, `NEGATIVE_ONE_TO_ONE_EXT`, `ZERO_TO_ONE_EXT`, `CLIP_ORIGIN_EXT`, `CLIP_DEPTH_MODE_EXT` | `requires_any_extension`, `min_methods_for_match: 0` |
| `ext_float_blend` | `EXT_float_blend` | — | — | `requires_any_extension` |
| `ext_rasterizer_ext` | `EXT_polygon_offset_clamp`, `EXT_depth_clamp`, `WEBGL_polygon_mode` | `polygonOffsetClampEXT`, `polygonModeWEBGL` | `POLYGON_OFFSET_CLAMP_EXT`, `DEPTH_CLAMP_EXT`, `POLYGON_MODE_WEBGL`, `POLYGON_OFFSET_LINE_WEBGL`, `LINE_WEBGL`, `FILL_WEBGL` | `requires_any_extension` (it cannot go in `rasterizer_state`, which has no extension gate) |
| `ext_texture_params` | `WEBGL_stencil_texturing`, `EXT_texture_mirror_clamp_to_edge` | — | `DEPTH_STENCIL_TEXTURE_MODE_WEBGL`, `STENCIL_INDEX_WEBGL`, `MIRROR_CLAMP_TO_EDGE_EXT` | `requires_any_extension` |
| `ext_clip_cull_distance` | `WEBGL_clip_cull_distance` | — | `MAX_CLIP_DISTANCES_WEBGL`, `MAX_CULL_DISTANCES_WEBGL`, `MAX_COMBINED_CLIP_AND_CULL_DISTANCES_WEBGL`, `CLIP_DISTANCE0_WEBGL` … `CLIP_DISTANCE7_WEBGL` | `requires_any_extension`. Also add `gl_ClipDistance`, `gl_CullDistance`, `gl_MaxClipDistances` and `gl_MaxCullDistances` to the surface `glsl_builtin_variables`. |
| `ext_conservative_depth` | `EXT_conservative_depth` | — | — | `requires_any_extension`; later also the `glsl_patterns` gate `layout\s*\(\s*depth_(any\|greater\|less\|unchanged)` |
| `ext_sample_shading` | `OES_sample_variables`, `OES_shader_multisample_interpolation`, `NV_shader_noperspective_interpolation` | — | `MIN_FRAGMENT_INTERPOLATION_OFFSET_OES`, `MAX_FRAGMENT_INTERPOLATION_OFFSET_OES`, `FRAGMENT_INTERPOLATION_OFFSET_BITS_OES` | `requires_any_extension`; `glsl_functions`: `interpolateAtCentroid`, `interpolateAtSample`, `interpolateAtOffset`. Also add `gl_SampleID`, `gl_SamplePosition`, `gl_SampleMaskIn`, `gl_SampleMask` and `gl_NumSamples` to the surface variables. |
| `ext_blend_func_extended` | `WEBGL_blend_func_extended` | — | `SRC1_COLOR_WEBGL`, `SRC1_ALPHA_WEBGL`, `ONE_MINUS_SRC1_COLOR_WEBGL`, `ONE_MINUS_SRC1_ALPHA_WEBGL`, `MAX_DUAL_SOURCE_DRAW_BUFFERS_WEBGL` | `requires_any_extension` |
| `ext_renderable_formats` | `EXT_texture_norm16`, `EXT_render_snorm`, `WEBGL_render_shared_exponent` | — | `R16_EXT`, `RG16_EXT`, `RGB16_EXT`, `RGBA16_EXT`, `R16_SNORM_EXT`, `RG16_SNORM_EXT`, `RGB16_SNORM_EXT`, `RGBA16_SNORM_EXT` | `requires_any_extension`. `render_snorm` and `render_shared_exponent` have no API fingerprint, so only the `getExtension` call can detect them. |
| `ext_multiview` | `OVR_multiview2` | `framebufferTextureMultiviewOVR` | `FRAMEBUFFER_ATTACHMENT_TEXTURE_NUM_VIEWS_OVR`, `FRAMEBUFFER_ATTACHMENT_TEXTURE_BASE_VIEW_INDEX_OVR`, `MAX_VIEWS_OVR`, `FRAMEBUFFER_INCOMPLETE_VIEW_TARGETS_OVR` | `requires_any_extension` |
| `ext_debug_info` | `WEBGL_debug_shaders`, `WEBGL_debug_renderer_info` | `getTranslatedShaderSource` | `UNMASKED_VENDOR_WEBGL`, `UNMASKED_RENDERER_WEBGL` | `requires_any_extension` |
| `context_loss` | `WEBGL_lose_context` | `loseContext`, `restoreContext` | `CONTEXT_LOST_WEBGL` | `requires_any_extension`, `min_methods_for_match: 1` (so a bare `isContextLost` call does not match) |

Also add `queryCounterEXT`'s siblings (`createQueryEXT`, `deleteQueryEXT`, `isQueryEXT`, `beginQueryEXT`, `endQueryEXT`, `getQueryEXT`, `getQueryObjectEXT`) to `ext_disjoint_timer_query.extension_methods`. Firefox 153 exposes `EXT_disjoint_timer_query` in WebGL2.

### Core categories (JSON-only)

| Category | `methods` | `constants` | Gate |
|---|---|---|---|
| `rasterizer_discard` | — | `RASTERIZER_DISCARD` | `min_methods_for_match: 0`, `min_constants_for_match: 1` |
| `fbo_invalidate` | `invalidateFramebuffer`, `invalidateSubFramebuffer` | — | `min_methods_for_match: 1` |
| `srgb` | `texImage2D`, `texImage3D`, `texStorage2D`, `texStorage3D`, `renderbufferStorage`, `renderbufferStorageMultisample`, `compressedTexImage2D` | `SRGB8`, `SRGB8_ALPHA8`, `SRGB`, `SRGB_ALPHA`, `FRAMEBUFFER_ATTACHMENT_COLOR_ENCODING` | `requires_any_constant` |
| `shadow_compare` | `texParameteri`, `texParameterf`, `samplerParameteri`, `samplerParameterf` | `TEXTURE_COMPARE_MODE`, `TEXTURE_COMPARE_FUNC`, `COMPARE_REF_TO_TEXTURE` | `requires_any_constant` |
| `texture_lod_range` | `texParameteri`, `texParameterf`, `samplerParameteri`, `samplerParameterf` | `TEXTURE_BASE_LEVEL`, `TEXTURE_MAX_LEVEL`, `TEXTURE_MIN_LOD`, `TEXTURE_MAX_LOD` | `requires_any_constant` |
| `texture_cube` | `texImage2D`, `texStorage2D`, `texSubImage2D`, `framebufferTexture2D`, `generateMipmap` | `TEXTURE_CUBE_MAP_POSITIVE_X`, `TEXTURE_CUBE_MAP_NEGATIVE_X`, `TEXTURE_CUBE_MAP_POSITIVE_Y`, `TEXTURE_CUBE_MAP_NEGATIVE_Y`, `TEXTURE_CUBE_MAP_POSITIVE_Z`, `TEXTURE_CUBE_MAP_NEGATIVE_Z`, `TEXTURE_BINDING_CUBE_MAP` | `requires_any_constant` |
| `integer_attributes` | `vertexAttribIPointer`, `vertexAttribI4i`, `vertexAttribI4iv`, `vertexAttribI4ui`, `vertexAttribI4uiv` | — | `min_methods_for_match: 1` |
| `buffer_copy_readback` | `copyBufferSubData`, `getBufferSubData` | — | `min_methods_for_match: 1` |
| `multisample_rb` | `renderbufferStorageMultisample` | — | `min_methods_for_match: 1` |
| `pbo` | `readPixels`, `texImage2D`, `texSubImage2D`, `texImage3D`, `texSubImage3D`, `compressedTexImage2D`, `compressedTexSubImage2D` | `PIXEL_PACK_BUFFER`, `PIXEL_UNPACK_BUFFER` | `requires_any_constant`. Optionally split the unpack path into `pbo_unpack`. |
| `depth_textures` | `texImage2D`, `texImage3D`, `texStorage2D`, `texStorage3D` | `DEPTH_COMPONENT16`, `DEPTH_COMPONENT24`, `DEPTH_COMPONENT32F`, `DEPTH24_STENCIL8`, `DEPTH32F_STENCIL8` | `requires_any_constant`. Needs a per-call (method, constant) gate; with today's file-wide gate, renderbuffer-only seeds match falsely. |

### Categories that need a detector change

- **Context attributes and the drawing buffer:**
  - `context_attributes`: in `context.py`, record each property of the second `getContext` argument as `ctxattr:<name>=<value>`. Match only non-default values (`alpha=false`, `premultipliedAlpha=false`, `preserveDrawingBuffer=true`, `stencil=true`, `depth=false`, `desynchronized=true`, a non-default `powerPreference`, `failIfMajorPerformanceCaveat=true`). Exclude `antialias=false`: it is boilerplate. Move `getContextAttributes` into this category.
  - `drawing_buffer`: methods `drawingBufferStorage` (removed from `fbo`) plus pseudo-methods `canvas_resize`, `attr:drawingBufferColorSpace=`, `attr:unpackColorSpace=`, `canvas_readback` and `frame_boundary`. This needs an `attributes` section in `webgl_api_surface.json`, extracted from the same IDL.
- **Texture sources:**
  - `dom_texture_sources`: methods `texImage2D`, `texSubImage2D`, `texImage3D` and `texSubImage3D`, with `requires_any_constant` over `src:ImageData`, `src:canvas`, `src:ImageBitmap`, `src:OffscreenCanvas`, `src:VideoFrame`, `src:webgl_canvas` and `src:image`. The source kind comes from classifying the last argument.
  - `unpack_webgl_params`: method `pixelStorei`; constants `UNPACK_FLIP_Y_WEBGL`, `UNPACK_PREMULTIPLY_ALPHA_WEBGL`, `UNPACK_COLORSPACE_CONVERSION_WEBGL`, `BROWSER_DEFAULT_WEBGL`; gated with `requires_any_constant`. This one is JSON-only, but it is useful only together with `dom_texture_sources` and `pbo`.
- **Multiple contexts:**
  - `multi_context`: pseudo-methods `ctx:multiple`, `ctx:cross_object` and `ctx:offscreen`.
- **GLSL categories:** `glsl_preprocessor`, `glsl_control_flow`, `glsl_interpolation`, `glsl_ubo_layout`, `glsl_fragment_kill_depth`, `glsl_integer_ops` and `glsl_aggregates`. Each needs a new `glsl_patterns` key: regexes run over comment-stripped shader sources, with a `min_glsl_patterns_for_match` threshold. `glsl_fragment_kill_depth` also needs a `glsl_variables` gate fed by `extract_glsl_variables`. The regexes are listed in the GLSL lane output. Fix the shader-source extraction first (table row 32), or every new GLSL category inherits its ~7% miss rate.

## Proposed new topology edges

The spec references are to `docs/WebGL 2.0 Specification.md` (WebGL2) and `docs/WebGL Specification.md` (WebGL1), unless they cite an extension spec or the OpenGL ES 3.0.6 specification. Neither of those is in `docs/`; those rules are cited from memory.

### Edges for the new categories

| Edge | Spec rule |
|---|---|
| `rasterizer_discard`–`transform_feedback`, –`query`, –`draw_calls`, –`fbo`, –`depth_stencil` | WebGL2:3655 and ES 3.0.6 §3.1: discard drops every fragment after TF capture, so TF still works while occlusion queries, depth/stencil, blending and FBO writes see nothing |
| `ext_clip_control`–`viewport_scissor`, –`rasterizer_state`, –`depth_stencil`, –`fbo`, –`draw_calls` | clip origin and depth mode change the window transform and the depth range |
| `ext_float_blend`–`blending`, –`ext_color_buffer_float`, –`mrt`, –`ext_draw_buffers_indexed` | without the extension, drawing with BLEND enabled to a 32-bit float attachment gives INVALID_OPERATION (this also covers per-buffer BLEND) |
| `ext_rasterizer_ext`–`rasterizer_state`, –`depth_stencil`, –`viewport_scissor`, –`draw_calls` | the offset clamp, depth clamp and polygon mode all modify rasterisation and the depth test |
| `ext_texture_params`–`depth_stencil`, –`texture_ops`, –`sampler`, –`fbo`, –`depth_textures` | the stencil-texture mode selects which component of a depth-stencil texture is sampled |
| `ext_clip_cull_distance`–`shader_pipeline`, –`draw_calls`, –`rasterizer_state`, –`transform_feedback`, –`fbo` | `enable(CLIP_DISTANCEi_WEBGL)` together with `gl_ClipDistance` writes clips primitives |
| `ext_conservative_depth`–`depth_stencil`, –`shader_pipeline`, –`fbo`, –`renderbuffer` | the `layout(depth_*)` qualifier on `gl_FragDepth` |
| `ext_sample_shading`–`renderbuffer`, –`fbo`, –`rasterizer_state`, –`blending`, –`shader_pipeline` | sample variables need a multisample target, and `gl_SampleMask` interacts with coverage |
| `ext_blend_func_extended`–`blending`, –`mrt`, –`shader_pipeline`, –`draw_calls` | dual-source factors with `layout(index=1)`; `MAX_DUAL_SOURCE_DRAW_BUFFERS_WEBGL` caps the draw buffers |
| `ext_renderable_formats`–`fbo`, –`renderbuffer`, –`texture_ops`, –`pixel_ops`, –`ext_color_buffer_float` | the extensions make formats colour-renderable |
| `ext_multiview`–`fbo`, –`texture_arrays`, –`shader_pipeline`, –`draw_calls`, –`instancing` | multiview attaches a layer range of an array texture; `gl_ViewID_OVR` |
| `ext_debug_info`–`shader_pipeline` | `getTranslatedShaderSource` returns the translator output |
| `context_loss`–`buffer_ops`, –`texture_ops`, –`fbo`, –`renderbuffer`, –`vao`, –`shader_pipeline`, –`sync`, –`query`, –`transform_feedback`, –`draw_calls`, –`multi_context` | WebGL1:2046-2215: every object is invalidated on loss; calls on stale handles after restore |
| `fbo_invalidate`–`fbo`, –`renderbuffer`, –`depth_stencil`, –`mrt`, –`viewport_scissor`, –`texture_ops`, –`draw_calls` | WebGL2:4080: framebuffer contents after invalidation |
| `srgb`–`texture_ops`, –`fbo`, –`blending`, –`renderbuffer`, –`ext_compressed_textures` | sRGB encode and decode on attachment and blend |
| `shadow_compare`–`texture_ops`, –`sampler`, –`fbo`, –`shader_pipeline`, –`texture_arrays`, –`depth_stencil`, –`depth_textures` | WebGL2:3996: the sampler type must match the texture's compare mode and format |
| `texture_lod_range`–`texture_ops`, –`sampler`, –`fbo`, –`texture_3d`, –`texture_arrays`, –`shader_pipeline` | rendering to a mip level outside the base/max range, and feedback-loop rules |
| `texture_cube`–`texture_ops`, –`fbo`, –`sampler`, –`pixel_ops`, –`shader_pipeline`, –`ext_compressed_textures` | face targets and cube completeness |
| `integer_attributes`–`attributes`, –`vao`, –`shader_pipeline`, –`instancing`, –`buffer_ops`, –`transform_feedback`, –`draw_calls`, –`WEBGL_multi_draw` | WebGL2:4101: the VertexAttrib function must match the shader attribute type |
| `buffer_copy_readback`–`buffer_ops`, –`sync`, –`transform_feedback`, –`ubo`, –`vao`, –`query`, –`draw_calls`, –`attributes` | WebGL2:1726-1792 (`getBufferSubData`, fence advice) and WebGL2:3740 (copying buffers) |
| `multisample_rb`–`renderbuffer`, –`fbo`, –`rasterizer_state`, –`depth_stencil`, –`integer_textures`, –`ext_color_buffer_float`, –`mrt`, –`fbo_invalidate` | resolve blits; integer formats with samples>0 give INVALID_OPERATION; coverage needs `SAMPLE_BUFFERS=1` |
| `pbo`–`buffer_ops`, –`pixel_ops`, –`texture_ops`, –`texture_3d`, –`texture_arrays`, –`fbo`, –`sync`, –`integer_textures`, –`ext_compressed_textures`, –`transform_feedback` | WebGL2:2820 and 2200-2204: the offset overloads; WebGL2:3750-3757: double binding with TF |
| `depth_textures`–`texture_ops`, –`fbo`, –`sampler`, –`shader_pipeline`, –`depth_stencil`, –`texture_arrays`, –`pixel_ops` | WebGL2:4091: `FLOAT_32_UNSIGNED_INT_24_8_REV` upload rules |

### Edges between existing categories

Measured alone, unless the row says otherwise:

| Edge | Spec rule | Measured delta |
|---|---|---|
| `WEBGL_multi_draw`–`ext_disjoint_timer_query` | `TIME_ELAPSED_EXT` brackets a batched draw | +8 zero-seed 4-way. Combined with the integer and MRT edges below, it exposes 2 zero-seed 3-way gaps that only CV can close. |
| `WEBGL_multi_draw`–`transform_feedback` | WebGL2:3750-3768 and ES 3.0.6 §2.15.2: element-draw variants are rejected while TF is active; array variants consume capture space | +3 3-way |
| `WEBGL_multi_draw`–`query` | WebGL2:2940-2953: occlusion and TF-primitive queries count every sub-draw | +7 3-way, +1 zero-seed 4-way |
| `WEBGL_multi_draw`–`fbo`, –`mrt` | WebGL1:2622 (feedback loops); WebGL2:3774-3810 (shader output must be compatible with the draw buffers) | +16 / +8 3-way |
| `WEBGL_multi_draw`–`texture_ops`, –`integer_textures` | WebGL2:3996: the sampler type is checked against the format at draw time | +10 / +4 zero-seed 4-way |
| `WEBGL_multi_draw`–`instancing`, –`ubo`, –`uniforms` | instance-count lists; WebGL2:3834 (UBO backing size); `gl_DrawID` indexing | small |
| `transform_feedback`–`pixel_ops`, –`texture_ops` | WebGL2:3750-3757: a buffer bound to TF and also used as a PBO gives INVALID_OPERATION | +3 / +7 zero-seed 4-way |
| `transform_feedback`–`ubo`, –`attributes`, –`instancing` | the same double-binding rule; capture space counts instances | 0 (adds pair visibility) |
| `ubo`–`draw_calls` | WebGL2:3834-3845: an active uniform block not backed by a large enough buffer gives INVALID_OPERATION at draw time | +11 3-way |
| `query`–`depth_stencil`, –`fbo` (and optionally –`rasterizer_state`) | ES 3.0.6 §4.1.6: occlusion counts samples that pass the depth/stencil tests | +10 / +17 3-way |
| `integer_textures`–`sampler` | ES 3.0.6 §3.8.13: an integer texture with LINEAR filtering is incomplete, and a sampler object overrides the texture's filter; WebGL2:3878 | +7 3-way |
| `integer_textures`–`draw_calls` | WebGL2:3983-3994: fragment output type must match the buffer; WebGL2:3860: invalid clears | +14 3-way |
| `integer_textures`–`pixel_ops`, –`blending`, –`ext_draw_buffers_indexed`, –`renderbuffer` | `RGBA_INTEGER` readback; blending skips integer buffers (ES 3.0.6 §4.1.7); multisample integer storage gives INVALID_OPERATION | +2 zero-seed 4-way (from `ext_draw_buffers_indexed`) |
| `mrt`–`viewport_scissor`, `ext_draw_buffers_indexed`–`viewport_scissor`, `ext_draw_buffers_indexed`–`shader_pipeline` | WebGL2:3790-3810: the shader-output-compatibility check runs only when `colorMask`/`colorMaski` enables a channel | +13 3-way (`ext_draw_buffers_indexed`–`shader_pipeline`) |
| `mrt`–`ext_color_buffer_float`, –`renderbuffer` | WebGL2:4120-4127: every attachment must have the same size | — |
| `ext_color_buffer_float`–`pixel_ops`, –`texture_ops` | float readback; in WebGL2 the core RGBA16F/32F formats are what this extension makes renderable | — |
| `ext_compressed_textures`–`buffer_ops`, –`fbo` | WebGL2:2500-2515: compressed upload from `PIXEL_UNPACK_BUFFER`; ES 3.0.6 §4.4.4: a compressed attachment makes the framebuffer incomplete | +10 / +4 zero-seed 4-way |
| `ext_texture_filter_anisotropic`–`texture_3d`, –`texture_arrays` | `TEXTURE_MAX_ANISOTROPY_EXT` is valid on every texture target | +1 zero-seed 4-way each |
| `rasterizer_state`–`draw_calls`, –`shader_pipeline`, –`renderbuffer` | ES 3.0.6 §3.6.1: cull applies to polygon draws; `gl_FrontFacing` depends on `frontFace`; coverage needs a multisample target | +12 to +15 3-way |
| `glsl_builtins`–`texture_ops`, –`sampler` | GLSL ES 3.00 §8.8: `texelFetch` ignores sampler state; WebGL2:3866 (invalid texture offsets) | small |

**Replace** the edge `depth_stencil`–`ext_draw_buffers_indexed` ("per-buffer depth/stencil interaction"). `OES_draw_buffers_indexed` indexes only blend state and `colorMask`, so this edge has no spec basis. Use `ext_draw_buffers_indexed`–`viewport_scissor` in its place.

Do **not** add `rasterizer_state`–`transform_feedback`. TF captures vertices before culling, so cull state does not interact with it. The real coupling is `RASTERIZER_DISCARD`, which `rasterizer_discard` covers.

Every edge enlarges the denominator of the coverage percentage. Save a baseline with `--snapshot` before applying them.

## Left unmapped on purpose

| Item | Reason |
|---|---|
| `WEBGL_draw_instanced_base_vertex_base_instance` and `WEBGL_multi_draw_instanced_base_vertex_base_instance` | Absent from the FF and CV context lists. First record a `getSupportedExtensions` capture for `config/angle_gl.json`. |
| `WEBGL_provoking_vertex`, `WEBGL_shader_pixel_local_storage`, `KHR_parallel_shader_compile` | Absent from the FF and CV lists. CG is unrecorded, so capture it before deciding. |
| `makeXRCompatible` and the `xrCompatible` attribute | Probe 2026-10-17: `undefined` on every headless lane. Mark it unexposed in the method-coverage denominator rather than counting it as a gap. |
| WebGL1-only extensions (`OES_vertex_array_object`, `ANGLE_instanced_arrays`, `WEBGL_draw_buffers`, `OES_standard_derivatives` and the rest) and a `webgl1_context` category | `CLAUDE.md` requires WebGL2 contexts, and these return null in WebGL2. The probe shows WebGL1 contexts expose them on every lane, so `UNSUPPORTED.md`'s "Not supported" entries are stale and worth correcting. Allowing WebGL1 contexts would be a policy decision. |
| `WEBGL_compressed_texture_pvrtc` | No lane exposes it. |
| `gl_DrawID` | All 5 seeds that use it already match `WEBGL_multi_draw`. Add it to the surface `glsl_builtin_variables` for the per-variable report only. |
| Core float formats (`RGBA16F`/`32F` etc.) as a category | A category for them adds 0 gaps at 3 and 4 way, because existing gates already match 99 of 109 seeds. |
| Precision qualifiers | Present in 563/563 seeds, so a category would carry no signal. |
| Non-square uniform matrices and uniform-type constants | Method-level depth, already reported by `--api-surface-coverage`. |
| Transform feedback buffer modes (`SEPARATE` vs `INTERLEAVED`) | Not a category. Add the buffer-mode constant to the `distinct_fingerprints` key in `combination_matrix.py:104-110` instead. |
| `drawRangeElements` / `MAX_ELEMENT_INDEX` | Thin usage (5 seeds) but no distinct interaction. Write a seed or two; no category. |
| Broad `sync` edges (to `query`, `texture_ops`, …) | A fence covers every prior command, so edges to every producer add noise without a coupling-specific rule. |
| More `pipeline_state` edges | It matches 572/572 seeds, so more edges cannot reveal a gap. Fix the `UBIQUITOUS` mismatch instead (table row 31). |
| `WEBGL_explicit_present`, `MOZ_debug` | Exposed by Firefox but absent from `webgl_api_surface.json`. Extend the surface first if they are wanted. |

## Open data gaps

- No `getSupportedExtensions` list is recorded for the ANGLE-GL lane. Only `WEBGL_clip_cull_distance` is documented there.
- `docs/browser_webgl_info.txt` is older than the 2026-10-16 and 2026-10-17 snapshots, and its "Chromium" section is not tagged with a lane.
- `UNSUPPORTED.md:74-78` (timer queries are not supported in Firefox) holds only for the `_webgl2` name. Firefox 153 exposes `EXT_disjoint_timer_query`.
- `CLAUDE.md` gives 405 seeds; the tool sees 572.
