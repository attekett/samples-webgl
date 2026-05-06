# Coverage Analysis Upgrade: Multi-Layer Analysis + Recipe-Guided Seed Generation

**Date**: 2026-02-24 (revised 2026-02-25)
**Status**: Design (pending implementation)
**Phases**: 3 (Foundation → Depth [optional] → Generation)

## Problem Statement

The current coverage analysis has two limitations:

1. **Shallow coverage metrics**: The `api_audit` tool tracks method/constant presence, and `feature_matrix.sh` uses grep-based counting. Neither answers: "Do features meaningfully interact within seeds?" or "Which security-relevant call sequence patterns are exercised?"

2. **Manual seed creation**: The `expand-webgl-coverage` skill guides a human through audit → select → write → validate → verify. Each seed requires reading gap reports, making targeting decisions, writing code, and iterating on validation.

## Goal

Build a multi-layer analysis pipeline that understands coverage **depth** (not just breadth), feeding structured gap specifications into recipe-guided seed generation with automated validation.

**Important framing**: Phase 3 is *recipe-guided generation*, not fully automated generation. The pipeline produces structured recipes; an LLM (Claude) writes each seed from the recipe context in a human-supervised conversation. The automation covers analysis, gap prioritization, recipe creation, and validation - not the code writing itself.

**Phase independence**: Phase 1 + Phase 3 form a **complete, self-sufficient pipeline**. Phase 2 is an optional enrichment layer that improves the quality of gap prioritization and recipe guidance when available, but Phase 3 generates fully functional recipes from Phase 1 data alone. This is deliberate: Phase 1 captures ~80% of the value (feature detection + combination coverage + gap identification). Phase 2 adds interaction quality and security pattern signals, but its inherent limitations (cannot detect state-based, shader-mediated, or ordering-dependent interactions — see decision #26) mean the additional signal is a lower bound with significant blind spots. The pipeline must not depend on partial signals that may mislead as often as they inform.

```
Phase 1 (required):
  Audit → Feature detect → Combination matrix → Prioritize gaps → Generate recipes

Phase 2 (optional enrichment):
  Resource tracking → Interaction graph → Sequence analyzer
  → Enriches: combination matrix quality metrics, recipe interaction guidance

Recipe-guided generation (Phase 3, works with Phase 1 alone):
  For each recipe:
      Claude writes seed from recipe context (human-supervised)
      → Validate → Fix → Re-validate
      → Delta audit → Verify gap closure
  → Final full audit → Report improvement
```

## Architecture Overview

All new modules live inside `scripts/api_audit/` alongside existing modules. The existing 8-pass pipeline is untouched; new passes consume its output.

### Existing Pipeline (unchanged)

```
html_extract → parse → context → const_propagation → call_analysis → glsl → lint → report
```

### New Analysis Passes

```
Phase 1 (required):
                    ┌─────────────────────┐
                    │  feature_detection   │ ← reads: call_analysis + glsl output, feature_categories.json
                    │  (Layer 1)           │ → produces: feature fingerprint per seed (with depth levels)
                    └─────────┬───────────┘
                              │
                    ┌─────────────────────┐
                    │ combination_matrix   │ ← reads: feature fingerprints, interaction_topology.json
                    │  (Layer 2)           │ → produces: N-way coverage, gaps, priority ranking
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │     gap_spec        │ ← reads: matrix gaps + (optionally) Phase 2 enrichment
                    │  (Layer 3)          │ → produces: prioritized recipes
                    └─────────────────────┘

Phase 2 (optional enrichment — improves quality of Layer 2 + Layer 3 output):
                    ┌─────────────────────┐
                    │  resource_tracking   │ ← reads: parsed AST, call_analysis, const_propagation
                    │                      │ → produces: resource map (variable → type → feature)
                    └─────────┬───────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────┐           ┌───────────────────┐
│ interaction_graph   │           │ sequence_analyzer  │
│ (shared resources)  │           │ (call sequences)   │
└────────┬────────────┘           └────────┬──────────┘
         │                                 │
         └────────────┬────────────────────┘
                      ▼
         Enriches combination_matrix with:
         - avg_interaction_score per combo
         - state_path coverage per combo
         - depth_confidence from miss rates
```

### New Config Files

```
Phase 1 (required):
docs/feature_categories.json     ← Data-driven feature category definitions (categories + matching rules)
docs/interaction_topology.json   ← Static feature interaction graph (which categories CAN meaningfully interact)

Phase 2 (optional):
docs/resource_types.json         ← Resource type → feature category mapping (used by resource_tracking)
docs/state_paths.json            ← State path catalog + state point definitions (used by sequence_analyzer + interaction_graph)
```

### Updated Skill

```
.claude/skills/expand-webgl-coverage/SKILL.md   ← Rewritten for automated pipeline
```

---

## Phase 1: Foundation

### Module: `feature_detection.py`

**Purpose**: AST-based feature categorization per seed. Replaces grep-based `feature_matrix.sh`.

**Input**:
- Call analysis results from `call_analysis.py` (methods + constants)
- GLSL builtin set from `glsl.py` (needed for `glsl_builtins` category)
- `docs/feature_categories.json` (new config file)

**Config file format** (`docs/feature_categories.json`):

```json
{
  "version": 1,
  "categories": {
    "buffer_ops": {
      "description": "Buffer creation, binding, data upload, and readback",
      "methods": [
        "createBuffer", "bindBuffer", "bufferData", "bufferSubData",
        "copyBufferSubData", "getBufferSubData", "deleteBuffer",
        "getBufferParameter", "isBuffer"
      ],
      "constants": [
        "ARRAY_BUFFER", "ELEMENT_ARRAY_BUFFER", "COPY_READ_BUFFER",
        "COPY_WRITE_BUFFER", "PIXEL_PACK_BUFFER", "PIXEL_UNPACK_BUFFER"
      ],
      "min_methods_for_match": 1
    },
    "transform_feedback": {
      "description": "Transform feedback capture and buffer binding",
      "methods": [
        "beginTransformFeedback", "endTransformFeedback",
        "transformFeedbackVaryings", "createTransformFeedback",
        "bindTransformFeedback", "deleteTransformFeedback",
        "pauseTransformFeedback", "resumeTransformFeedback",
        "getTransformFeedbackVarying"
      ],
      "constants": [
        "TRANSFORM_FEEDBACK", "TRANSFORM_FEEDBACK_BUFFER",
        "TRANSFORM_FEEDBACK_BINDING"
      ],
      "min_methods_for_match": 1
    },
    "fbo": {
      "description": "Framebuffer creation, attachment, and render targets",
      "methods": [
        "createFramebuffer", "bindFramebuffer", "deleteFramebuffer",
        "framebufferTexture2D", "framebufferTextureLayer",
        "framebufferRenderbuffer", "checkFramebufferStatus",
        "blitFramebuffer", "readBuffer", "invalidateFramebuffer",
        "invalidateSubFramebuffer", "isFramebuffer"
      ],
      "constants": [
        "FRAMEBUFFER", "DRAW_FRAMEBUFFER", "READ_FRAMEBUFFER"
      ],
      "min_methods_for_match": 1
    },
    "texture_ops": {
      "description": "Texture creation, data upload, and parameter configuration",
      "methods": [
        "createTexture", "bindTexture", "deleteTexture",
        "texImage2D", "texSubImage2D", "texStorage2D",
        "texParameteri", "texParameterf",
        "generateMipmap", "compressedTexImage2D", "compressedTexSubImage2D",
        "copyTexImage2D", "copyTexSubImage2D", "isTexture",
        "getTexParameter"
      ],
      "constants": [
        "TEXTURE_2D", "TEXTURE_CUBE_MAP"
      ],
      "min_methods_for_match": 1
    },
    "texture_3d": {
      "description": "3D texture operations",
      "methods": [
        "texImage3D", "texSubImage3D", "texStorage3D",
        "compressedTexImage3D", "compressedTexSubImage3D",
        "copyTexSubImage3D"
      ],
      "constants": ["TEXTURE_3D"],
      "min_methods_for_match": 1
    },
    "texture_arrays": {
      "description": "2D array texture operations",
      "methods": [
        "texImage3D", "texSubImage3D", "texStorage3D",
        "framebufferTextureLayer"
      ],
      "constants": ["TEXTURE_2D_ARRAY"],
      "min_methods_for_match": 1,
      "requires_any_constant": true
    },
    "sampler": {
      "description": "Sampler object creation and configuration",
      "methods": [
        "createSampler", "bindSampler", "deleteSampler",
        "samplerParameteri", "samplerParameterf",
        "getSamplerParameter", "isSampler"
      ],
      "constants": [],
      "min_methods_for_match": 1
    },
    "sync": {
      "description": "Sync object creation and wait operations",
      "methods": [
        "fenceSync", "clientWaitSync", "waitSync",
        "deleteSync", "getSyncParameter", "isSync"
      ],
      "constants": [
        "SYNC_GPU_COMMANDS_COMPLETE", "SYNC_FENCE"
      ],
      "min_methods_for_match": 1
    },
    "query": {
      "description": "Query object operations",
      "methods": [
        "createQuery", "deleteQuery", "beginQuery", "endQuery",
        "getQuery", "getQueryParameter", "isQuery"
      ],
      "constants": [
        "ANY_SAMPLES_PASSED", "ANY_SAMPLES_PASSED_CONSERVATIVE",
        "TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN"
      ],
      "min_methods_for_match": 1
    },
    "vao": {
      "description": "Vertex Array Object operations",
      "methods": [
        "createVertexArray", "bindVertexArray", "deleteVertexArray",
        "isVertexArray"
      ],
      "constants": [],
      "min_methods_for_match": 1
    },
    "instancing": {
      "description": "Instanced rendering",
      "methods": [
        "drawArraysInstanced", "drawElementsInstanced",
        "vertexAttribDivisor"
      ],
      "constants": [],
      "min_methods_for_match": 1
    },
    "mrt": {
      "description": "Multiple Render Targets",
      "methods": ["drawBuffers"],
      "constants": [
        "COLOR_ATTACHMENT1", "COLOR_ATTACHMENT2", "COLOR_ATTACHMENT3",
        "COLOR_ATTACHMENT4", "COLOR_ATTACHMENT5", "COLOR_ATTACHMENT6",
        "COLOR_ATTACHMENT7"
      ],
      "min_methods_for_match": 1
    },
    "ubo": {
      "description": "Uniform Buffer Objects",
      "methods": [
        "getUniformBlockIndex", "uniformBlockBinding",
        "getActiveUniformBlockParameter", "getActiveUniformBlockName",
        "getUniformIndices", "getActiveUniforms"
      ],
      "constants": [
        "UNIFORM_BUFFER", "UNIFORM_BUFFER_BINDING"
      ],
      "min_methods_for_match": 1
    },
    "integer_textures": {
      "description": "Integer-format texture operations",
      "methods": ["clearBufferiv", "clearBufferuiv"],
      "constants": [
        "R8I", "R16I", "R32I", "RG8I", "RG16I", "RG32I",
        "RGB8I", "RGB16I", "RGB32I", "RGBA8I", "RGBA16I", "RGBA32I",
        "R8UI", "R16UI", "R32UI", "RG8UI", "RG16UI", "RG32UI",
        "RGB8UI", "RGB16UI", "RGB32UI", "RGBA8UI", "RGBA16UI", "RGBA32UI"
      ],
      "min_methods_for_match": 0,
      "min_constants_for_match": 1
    },
    "depth_stencil": {
      "description": "Depth and stencil test operations",
      "methods": [
        "depthFunc", "depthMask", "depthRange",
        "stencilFunc", "stencilFuncSeparate",
        "stencilMask", "stencilMaskSeparate",
        "stencilOp", "stencilOpSeparate",
        "clearDepth", "clearStencil"
      ],
      "constants": [
        "DEPTH_TEST", "STENCIL_TEST"
      ],
      "min_methods_for_match": 1
    },
    "blending": {
      "description": "Blending operations",
      "methods": [
        "blendColor", "blendEquation", "blendEquationSeparate",
        "blendFunc", "blendFuncSeparate"
      ],
      "constants": ["BLEND"],
      "min_methods_for_match": 1
    },
    "pixel_ops": {
      "description": "Pixel read/write operations",
      "methods": [
        "readPixels", "pixelStorei"
      ],
      "constants": [
        "PACK_ROW_LENGTH", "PACK_SKIP_PIXELS", "PACK_SKIP_ROWS",
        "UNPACK_ROW_LENGTH", "UNPACK_IMAGE_HEIGHT", "UNPACK_SKIP_PIXELS",
        "UNPACK_SKIP_ROWS", "UNPACK_SKIP_IMAGES"
      ],
      "min_methods_for_match": 1
    },
    "renderbuffer": {
      "description": "Renderbuffer operations",
      "methods": [
        "createRenderbuffer", "bindRenderbuffer", "deleteRenderbuffer",
        "renderbufferStorage", "renderbufferStorageMultisample",
        "getRenderbufferParameter", "isRenderbuffer"
      ],
      "constants": ["RENDERBUFFER"],
      "min_methods_for_match": 1
    },
    "shader_pipeline": {
      "description": "Shader compilation, program linking, and program management",
      "methods": [
        "createShader", "shaderSource", "compileShader", "deleteShader",
        "getShaderParameter", "getShaderInfoLog", "getShaderSource", "isShader",
        "createProgram", "attachShader", "detachShader", "linkProgram",
        "useProgram", "deleteProgram", "validateProgram",
        "getProgramParameter", "getProgramInfoLog", "isProgram",
        "getAttachedShaders"
      ],
      "constants": [
        "VERTEX_SHADER", "FRAGMENT_SHADER", "COMPILE_STATUS", "LINK_STATUS"
      ],
      "min_methods_for_match": 2
    },
    "uniforms": {
      "description": "Uniform variable operations (non-UBO)",
      "methods": [
        "getUniformLocation", "getActiveUniform",
        "uniform1f", "uniform2f", "uniform3f", "uniform4f",
        "uniform1i", "uniform2i", "uniform3i", "uniform4i",
        "uniform1ui", "uniform2ui", "uniform3ui", "uniform4ui",
        "uniform1fv", "uniform2fv", "uniform3fv", "uniform4fv",
        "uniform1iv", "uniform2iv", "uniform3iv", "uniform4iv",
        "uniform1uiv", "uniform2uiv", "uniform3uiv", "uniform4uiv",
        "uniformMatrix2fv", "uniformMatrix3fv", "uniformMatrix4fv",
        "uniformMatrix2x3fv", "uniformMatrix3x2fv",
        "uniformMatrix2x4fv", "uniformMatrix4x2fv",
        "uniformMatrix3x4fv", "uniformMatrix4x3fv",
        "getUniform"
      ],
      "constants": [],
      "min_methods_for_match": 1
    },
    "attributes": {
      "description": "Vertex attribute configuration",
      "methods": [
        "getAttribLocation", "getActiveAttrib",
        "vertexAttribPointer", "vertexAttribIPointer",
        "enableVertexAttribArray", "disableVertexAttribArray",
        "vertexAttrib1f", "vertexAttrib2f", "vertexAttrib3f", "vertexAttrib4f",
        "vertexAttrib1fv", "vertexAttrib2fv", "vertexAttrib3fv", "vertexAttrib4fv",
        "vertexAttribI4i", "vertexAttribI4iv", "vertexAttribI4ui", "vertexAttribI4uiv",
        "getVertexAttrib", "getVertexAttribOffset"
      ],
      "constants": [],
      "min_methods_for_match": 1
    },
    "draw_calls": {
      "description": "Drawing and clearing operations",
      "methods": [
        "drawArrays", "drawElements", "drawRangeElements",
        "drawArraysInstanced", "drawElementsInstanced",
        "clear", "clearColor", "clearBufferfv", "clearBufferfi",
        "clearBufferiv", "clearBufferuiv"
      ],
      "constants": [
        "TRIANGLES", "TRIANGLE_STRIP", "TRIANGLE_FAN",
        "LINES", "LINE_STRIP", "LINE_LOOP", "POINTS",
        "COLOR_BUFFER_BIT", "DEPTH_BUFFER_BIT", "STENCIL_BUFFER_BIT"
      ],
      "min_methods_for_match": 1
    },
    "viewport_scissor": {
      "description": "Viewport and scissor rectangle configuration",
      "methods": [
        "viewport", "scissor", "colorMask"
      ],
      "constants": ["SCISSOR_TEST"],
      "min_methods_for_match": 1
    },
    "ext_float_textures": {
      "description": "Floating-point texture extensions",
      "methods": [],
      "constants": [],
      "extensions": ["OES_texture_float", "OES_texture_half_float", "OES_texture_float_linear", "OES_texture_half_float_linear"],
      "min_methods_for_match": 0,
      "requires_any_extension": true
    },
    "ext_color_buffer_float": {
      "description": "Float color buffer extension for rendering to float textures",
      "methods": [],
      "constants": [],
      "extensions": ["EXT_color_buffer_float", "EXT_color_buffer_half_float"],
      "min_methods_for_match": 0,
      "requires_any_extension": true
    },
    "ext_draw_buffers_indexed": {
      "description": "Per-draw-buffer blend and color mask control",
      "methods": [],
      "constants": [],
      "extensions": ["OES_draw_buffers_indexed"],
      "extension_methods": ["enableiOES", "disableiOES", "blendEquationiOES", "blendEquationSeparateiOES", "blendFunciOES", "blendFuncSeparateiOES", "colorMaskiOES"],
      "min_methods_for_match": 0,
      "requires_any_extension": true
    },
    "ext_texture_filter_anisotropic": {
      "description": "Anisotropic texture filtering",
      "methods": [],
      "constants": ["TEXTURE_MAX_ANISOTROPY_EXT", "MAX_TEXTURE_MAX_ANISOTROPY_EXT"],
      "extensions": ["EXT_texture_filter_anisotropic"],
      "min_methods_for_match": 0,
      "requires_any_extension": true
    },
    "ext_compressed_textures": {
      "description": "Compressed texture format extensions",
      "methods": [],
      "constants": [],
      "extensions": [
        "WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb",
        "WEBGL_compressed_texture_etc", "WEBGL_compressed_texture_astc",
        "WEBGL_compressed_texture_pvrtc", "EXT_texture_compression_bptc",
        "EXT_texture_compression_rgtc"
      ],
      "min_methods_for_match": 0,
      "requires_any_extension": true
    },
    "ext_disjoint_timer_query": {
      "description": "GPU timer query extension",
      "methods": [],
      "constants": [],
      "extensions": ["EXT_disjoint_timer_query_webgl2", "EXT_disjoint_timer_query"],
      "extension_methods": ["queryCounterEXT"],
      "min_methods_for_match": 0,
      "requires_any_extension": true
    },
    "glsl_builtins": {
      "description": "GLSL built-in function usage in shaders",
      "methods": [],
      "constants": [],
      "glsl_functions": [
        "smoothstep", "refract", "reflect", "faceforward",
        "matrixCompMult", "outerProduct", "transpose", "determinant",
        "inverse", "inversesqrt", "textureSize", "textureLod",
        "textureGrad", "textureOffset", "textureProjLod",
        "textureProjGrad", "texelFetch", "texelFetchOffset",
        "textureGather", "textureGatherOffset",
        "dFdx", "dFdy", "fwidth",
        "intBitsToFloat", "uintBitsToFloat", "floatBitsToInt",
        "floatBitsToUint", "packSnorm2x16", "unpackSnorm2x16",
        "packUnorm2x16", "unpackUnorm2x16", "packHalf2x16",
        "unpackHalf2x16"
      ],
      "min_glsl_for_match": 1
    }
  }
}
```

**Feature categories design notes**:
- Categories are data-driven: adding/removing/modifying categories requires only JSON edits
- `min_methods_for_match` controls sensitivity (some categories need just 1 method, others need constants too). **Known trade-off**: With `min_methods_for_match: 1`, boilerplate calls like `pixelStorei` (in `pixel_ops`) or `viewport` (in `viewport_scissor`) tag seeds with categories they don't meaningfully exercise. This is mitigated by two mechanisms: (1) the ratio-based depth level — a seed with 1/2 `pixel_ops` methods registers as "meaningful" (50%), but the combination matrix relies on depth-weighted coverage, not raw seed counts, to assess coverage quality; (2) the UBIQUITOUS set in priority scoring deprioritizes combos involving near-ubiquitous categories (`pixel_ops`, `viewport_scissor`). The trade-off is accepted: false negatives from raising `min_methods_for_match` would be worse than the noise from boilerplate tagging, since missing a genuine gap is harder to detect than deprioritizing a low-value one
- **Disambiguation mechanism**: Multiple flags control when a category matches (see matching algorithm below)
- `glsl_functions` field for shader-level coverage (uses GLSL extraction output from `glsl.py`)
- `extensions` field for extension-based categories (uses extension detection from `context.py`)
- `extension_methods` field for methods exposed by extension objects (uses `extension_methods` from `call_analysis.py`)
- Categories can overlap (a seed can match both `texture_ops` and `texture_3d`, or both `draw_calls` and `instancing`)
- **Ubiquitous categories** (`shader_pipeline`, `draw_calls`, `attributes`, `uniforms`) will match most seeds - this is expected. They're included so the matrix can detect seeds that are missing a functioning pipeline, and so recipes can explicitly require them.

**Category matching algorithm** (the canonical specification — all matching logic derives from this function):

```python
def is_category_match(category_def, methods_found, constants_found,
                      extensions_loaded, glsl_found, extension_methods_found):
    """Determine if a seed matches a feature category.

    All inputs use resolved constant NAMES (e.g., "TEXTURE_2D_ARRAY"), not GL enum
    numeric values. const_propagation.py resolves gl.TEXTURE_2D_ARRAY to the string
    "gl.TEXTURE_2D_ARRAY" — strip the "gl." prefix before matching against category
    constant lists.

    Args:
        category_def: Category entry from feature_categories.json
        methods_found: set of method names called in the seed (from call_analysis)
        constants_found: set of constant names used in the seed (from call_analysis,
                         with "gl." prefix stripped)
        extensions_loaded: set of extension names loaded (from context.py)
        glsl_found: set of GLSL builtin names matched (from glsl.py)
        extension_methods_found: dict {ext_name: set(method_names)} (from call_analysis)
    """
    cat = category_def

    # --- Method count check ---
    cat_methods = set(cat.get("methods", []))
    matched_methods = methods_found & cat_methods
    method_count = len(matched_methods)

    # Extension methods contribute to method count
    cat_ext_methods = set(cat.get("extension_methods", []))
    all_ext_methods = set()
    for ext_methods in extension_methods_found.values():
        all_ext_methods |= ext_methods
    matched_ext_methods = all_ext_methods & cat_ext_methods
    method_count += len(matched_ext_methods)

    # GLSL-only categories should set min_methods_for_match: 0
    min_methods = cat.get("min_methods_for_match", 1)
    if min_methods > 0 and method_count < min_methods:
        return False, set(), 0

    # --- Constant gate (AND — required if flag is set) ---
    if cat.get("requires_any_constant", False):
        cat_constants = set(cat.get("constants", []))
        if not (constants_found & cat_constants):
            return False, set(), 0

    # --- Constant count gate (AND — required if set) ---
    min_constants = cat.get("min_constants_for_match", 0)
    if min_constants > 0:
        cat_constants = set(cat.get("constants", []))
        if len(constants_found & cat_constants) < min_constants:
            return False, set(), 0

    # --- Extension gate (AND — required if flag is set) ---
    if cat.get("requires_any_extension", False):
        cat_extensions = set(cat.get("extensions", []))
        if not (extensions_loaded & cat_extensions):
            return False, set(), 0

    # --- GLSL gate (for glsl_builtins category) ---
    min_glsl = cat.get("min_glsl_for_match", 0)
    if min_glsl > 0:
        cat_glsl = set(cat.get("glsl_functions", []))
        matched_glsl = glsl_found & cat_glsl
        if len(matched_glsl) < min_glsl:
            return False, set(), 0

    # --- All gates passed → category matches ---
    all_matched = matched_methods | matched_ext_methods
    return True, all_matched, method_count
```

**Gate composition**: All gates are **AND**-composed. A category matches only if:
1. Method count ≥ `min_methods_for_match` (or category is GLSL-only), AND
2. If `requires_any_constant`: at least one listed constant is present, AND
3. If `min_constants_for_match > 0`: at least N listed constants are present, AND
4. If `requires_any_extension`: at least one listed extension is loaded, AND
5. If `min_glsl_for_match > 0`: at least N listed GLSL builtins are present

**Constant name resolution**: `const_propagation.py` resolves `gl.TEXTURE_2D_ARRAY` to the string `"gl.TEXTURE_2D_ARRAY"`. Before matching, the `"gl."` prefix is stripped, so the constant set contains `"TEXTURE_2D_ARRAY"` — matching the names in `feature_categories.json`. This is handled once at the call site in `detect_features()`, not inside `is_category_match()`.

**Disambiguation example** (`texture_arrays` vs `texture_3d`): Both share methods `texImage3D`, `texSubImage3D`, `texStorage3D`. A seed using `texImage3D` with constant `TEXTURE_3D` matches `texture_3d` (no constant gate) but NOT `texture_arrays` (requires `TEXTURE_2D_ARRAY` constant). A seed using `texImage3D` with constant `TEXTURE_2D_ARRAY` matches BOTH categories (overlap is intentional).

**Overlap noise acknowledgment**: When categories share methods, the combination matrix inherits tautological coverage. The concrete tautological pairs caused by shared methods are:

- **`draw_calls` + `instancing`**: `drawArraysInstanced` and `drawElementsInstanced` appear in both categories. Any seed using instanced drawing automatically covers this pair.
- **`integer_textures` + `draw_calls`**: `clearBufferiv` and `clearBufferuiv` appear in both categories. Seeds using integer clear operations automatically cover this pair.
- **`fbo` + `texture_arrays`**: `framebufferTextureLayer` appears in both categories. Seeds using layered FBO attachment automatically cover this pair.
- **`texture_3d` + `texture_arrays`**: `texImage3D`, `texSubImage3D`, `texStorage3D` appear in both (disambiguation via constant gate prevents false positives, but the method overlap means they often co-occur).

These tautological pairs inflate coverage counts slightly but do not distort gap detection — they simply won't appear as gaps. The gap report should **annotate and deprioritize** known tautological pairs: mark them with `"tautological": true` and exclude them from gap counts and coverage percentages. This prevents inflated coverage metrics and focuses attention on genuine gaps.

Beyond method-overlap tautologies, **pipeline tautologies** arise from near-ubiquitous category co-occurrence. Any working seed with a functioning render pipeline necessarily covers `shader_pipeline` + `draw_calls` + `attributes` + `uniforms` + `buffer_ops` — producing C(5,2) = 10 pairs that are always "covered." These inflate the raw covered count without reflecting genuine coverage diversity. The combination matrix should report both raw covered count and an **adjusted covered count** that excludes pairs where both features are in the UBIQUITOUS set (`shader_pipeline`, `draw_calls`, `attributes`, `uniforms`, `viewport_scissor`, `pixel_ops`). The adjusted count gives a more accurate picture of how many non-trivial combinations the corpus exercises.

To support this, category definitions may include an optional `overlaps_with` field listing categories that share methods:
```json
{
  "instancing": {
    "overlaps_with": ["draw_calls"],
    ...
  }
}
```
The combination matrix uses `overlaps_with` to identify tautological pairs and annotate them in the output. The `overlaps_with` field is symmetric — listing it on one side is sufficient (the matrix builder checks both directions).

**Constant propagation failure**: When const_propagation fails to resolve a constant argument (e.g., a variable holding `TEXTURE_2D_ARRAY` is assigned dynamically), the seed may fail the `requires_any_constant` gate and miss the `texture_arrays` category even though it genuinely uses array textures. This is a false negative from the conservative design — the seed will still match `texture_3d` (no constant gate), so it won't be invisible to the matrix, just miscategorized. The miss is acceptable; false positives (claiming array texture coverage when there is none) would be worse.

**Feature detection false positives**: The doc's false negative analysis above is conservative-correct, but the opposite problem — false positives — also affects coverage quality. With `min_methods_for_match: 1`, boilerplate calls create spurious category matches:

- `pixelStorei` (called by most texture-uploading seeds) → matches `pixel_ops`, even though the seed doesn't perform pixel read/write operations
- `viewport` (called by nearly every seed) → matches `viewport_scissor`, even though the seed isn't exercising viewport/scissor behavior
- `clearBufferiv` (used for general buffer clearing) → matches `integer_textures`, even though the seed may not use integer texture formats

The UBIQUITOUS set in priority scoring (`pixel_ops`, `viewport_scissor` included) partially mitigates this by deprioritizing combos involving these categories. However, the combination matrix's "covered" count is still inflated — a pair like `(pixel_ops, sampler)` registers as covered in any seed that calls both `pixelStorei` and `createSampler`, even if the seed never reads pixels or configures pixel storage for sampler output.

**Mitigation**: Category definitions may include an optional `false_positive_prone` flag:
```json
{
  "pixel_ops": {
    "false_positive_prone": true,
    "false_positive_methods": ["pixelStorei"],
    ...
  },
  "viewport_scissor": {
    "false_positive_prone": true,
    "false_positive_methods": ["viewport"],
    ...
  }
}
```

When `false_positive_prone` is set, the combination matrix annotates coverage entries where a category matched only via methods listed in `false_positive_methods` as `"low_confidence_match": true`. The gap report can then report both raw covered count and adjusted covered count (excluding low-confidence matches). This does not change the matching algorithm — the category still matches — but downstream consumers can distinguish confident matches from boilerplate noise.

This is not fully solved: some false positives come from methods that are legitimately in the category (e.g., `clearBufferiv` IS an integer texture operation when used with integer formats, but is a general clear operation otherwise). Context-dependent disambiguation would require analyzing the constant arguments, which is deferred to future work.

**Output per seed**:

```json
{
  "file": "agent_outputs/mutation_b12_s45_fbo_texture.html",
  "features": ["buffer_ops", "texture_ops", "fbo", "vao", "depth_stencil"],
  "feature_depth": {
    "buffer_ops": "meaningful",
    "texture_ops": "meaningful",
    "fbo": "present",
    "vao": "meaningful",
    "depth_stencil": "present"
  },
  "depth_ratios": {
    "buffer_ops": 0.44,
    "texture_ops": 0.40,
    "fbo": 0.25,
    "vao": 0.50,
    "depth_stencil": 0.18
  },
  "method_counts": {
    "buffer_ops": 4,
    "texture_ops": 6,
    "fbo": 3,
    "vao": 2,
    "depth_stencil": 2
  },
  "methods_per_feature": {
    "buffer_ops": ["createBuffer", "bindBuffer", "bufferData", "deleteBuffer"],
    "texture_ops": ["createTexture", "bindTexture", "texImage2D", "texStorage2D", "texParameteri", "deleteTexture"],
    "fbo": ["createFramebuffer", "bindFramebuffer", "framebufferTexture2D"],
    "vao": ["createVertexArray", "bindVertexArray"],
    "depth_stencil": ["depthFunc", "depthMask"]
  }
}
```

**Depth levels**: Each detected feature is classified by how substantially the seed exercises it. Depth is a **ratio-based heuristic** in Phase 1 — it measures what fraction of a category's API surface the seed uses, not interaction quality. Phase 2's interaction graph and sequence analysis provide the actual quality signal (shared resources, state paths, security patterns).

Depth uses the ratio `methods_used / methods_available`, where `methods_available` is the number of methods defined in the category's `methods` list in `feature_categories.json`. This normalizes depth across categories of different sizes — a seed using 1/1 `mrt` methods (100%) is "deep", while a seed using 1/9 `buffer_ops` methods (11%) is "present".

| Level | Criteria | Example (buffer_ops, 9 methods) | Example (mrt, 1 method) |
|-------|----------|--------------------------------|------------------------|
| `"present"` | ratio < 0.33 | 1-2 of 9 methods (11-22%) | — (impossible: 1/1 = 100%) |
| `"meaningful"` | 0.33 ≤ ratio < 0.66 | 3-5 of 9 methods (33-55%) | — (impossible: 1/1 = 100%) |
| `"deep"` | ratio ≥ 0.66 | 6+ of 9 methods (67%+) | 1 of 1 methods (100%) |

For categories with very few methods (`mrt`: 1, `instancing`: 3, `vao`: 4), using any methods at all tends to produce "meaningful" or "deep" coverage. This is intentional — these categories have small API surfaces, so any usage IS substantial coverage. For large categories like `uniforms` (40+ methods), routine usage of 2-3 methods correctly registers as "present" rather than inflating to "meaningful".

The depth level is a coarse signal. A seed at 67% of buffer methods is "deep" but may just be calling them independently. A seed at 44% of buffer methods but with a use-after-delete pattern is "meaningful" by ratio but more interesting for fuzzing. Depth helps filter the obviously-thin coverage (low ratio = barely touched), but should not be over-relied-upon. Phase 2's interaction scores and state path coverage are the authoritative quality metrics.

Depth levels allow Phase 1 to distinguish "this combination exists" from "this combination uses a non-trivial amount of the API surface" **without** requiring the full interaction graph from Phase 2. The combination matrix uses depth to weight coverage quantity: "present" < "meaningful" < "deep".

**API**:

```python
from api_audit.feature_detection import detect_features

# Single file - accepts call_analysis AND glsl output
fingerprint = detect_features(call_analysis_result, glsl_builtins, categories_config)

# With extension info (for extension-based categories)
fingerprint = detect_features(call_analysis_result, glsl_builtins, categories_config,
                               extensions=context_info.extensions,
                               extension_methods=call_analysis_result.extension_methods)

# Corpus
corpus_features = {f: detect_features(r.calls, r.glsl, config, extensions=r.extensions)
                   for f, r in corpus_results.items()}
```

**Blind spot: shader complexity is invisible**: Feature detection categorizes GL API calls and GLSL builtin usage, but it does not analyze shader *structure*. Two seeds calling identical GL methods but with radically different shaders (trivial passthrough vs. complex multi-texture PBR with branching, loops, and many uniform lookups) produce identical feature fingerprints. For fuzzing, shader complexity is a significant attack surface — complex shaders stress the compiler, optimizer, and register allocator in ways simple shaders don't. The `glsl_builtins` category captures *which* GLSL functions are used but not shader depth (number of uniforms, texture lookups, branching complexity, loop nesting). This is acknowledged as a design limitation — shader structure analysis would require a GLSL parser beyond the current regex-based builtin matching in `glsl.py`.

---

### Config: `docs/interaction_topology.json`

**Purpose**: A static, manually-curated graph defining which feature categories can meaningfully interact. This is a **whitelist** — only connected pairs represent combinations worth targeting. An N-way combo is "topology-connected" if every pair within it is connected (directly or transitively) in the graph.

**Why a whitelist, not a blacklist**: The previous design used `low_interaction_with` on category definitions to blacklist known-orthogonal pairs. This is backwards — the interaction topology of WebGL is relatively sparse (~50-80 meaningful edges among 30 nodes), while the space of orthogonal pairs is large (C(30,2) - 80 ≈ 355 pairs). Whitelisting meaningful interactions is more maintainable, more complete, and less error-prone than blacklisting all non-interactions.

**Config file format** (`docs/interaction_topology.json`):

```json
{
  "version": 1,
  "description": "Static feature interaction graph. Edges represent feature pairs that CAN meaningfully interact in a WebGL seed. An N-way combo is topology-connected if all pairs are connected (directly or via shared neighbor).",
  "edges": [
    {"pair": ["buffer_ops", "vao"], "relationship": "buffers feed vertex attributes"},
    {"pair": ["buffer_ops", "transform_feedback"], "relationship": "TF captures to buffers"},
    {"pair": ["buffer_ops", "ubo"], "relationship": "uniform buffers are buffer objects"},
    {"pair": ["buffer_ops", "pixel_ops"], "relationship": "PBO readback to buffer"},
    {"pair": ["texture_ops", "fbo"], "relationship": "textures as FBO attachments"},
    {"pair": ["texture_ops", "sampler"], "relationship": "samplers configure texture filtering"},
    {"pair": ["texture_ops", "pixel_ops"], "relationship": "pixel unpack for texture upload, readPixels from texture"},
    {"pair": ["texture_ops", "shader_pipeline"], "relationship": "shaders sample textures via uniforms"},
    {"pair": ["texture_3d", "fbo"], "relationship": "3D texture layers as FBO attachment"},
    {"pair": ["texture_3d", "texture_ops"], "relationship": "3D is a texture variant"},
    {"pair": ["texture_arrays", "fbo"], "relationship": "array layers as FBO attachment"},
    {"pair": ["texture_arrays", "texture_ops"], "relationship": "arrays are a texture variant"},
    {"pair": ["fbo", "renderbuffer"], "relationship": "renderbuffers as FBO attachments"},
    {"pair": ["fbo", "mrt"], "relationship": "MRT requires FBO with multiple attachments"},
    {"pair": ["fbo", "depth_stencil"], "relationship": "FBO depth/stencil attachments"},
    {"pair": ["fbo", "blending"], "relationship": "blending affects FBO draw output"},
    {"pair": ["fbo", "pixel_ops"], "relationship": "readPixels from FBO"},
    {"pair": ["renderbuffer", "depth_stencil"], "relationship": "depth/stencil renderbuffer storage"},
    {"pair": ["vao", "attributes"], "relationship": "VAO stores attribute state"},
    {"pair": ["vao", "instancing"], "relationship": "instanced attributes via VAO"},
    {"pair": ["shader_pipeline", "uniforms"], "relationship": "programs contain uniform locations"},
    {"pair": ["shader_pipeline", "attributes"], "relationship": "programs define attribute inputs"},
    {"pair": ["shader_pipeline", "ubo"], "relationship": "programs reference uniform blocks"},
    {"pair": ["shader_pipeline", "transform_feedback"], "relationship": "TF varyings declared on program"},
    {"pair": ["shader_pipeline", "glsl_builtins"], "relationship": "GLSL builtins are shader features"},
    {"pair": ["uniforms", "texture_ops"], "relationship": "sampler uniforms bind textures"},
    {"pair": ["draw_calls", "vao"], "relationship": "draw uses bound VAO"},
    {"pair": ["draw_calls", "fbo"], "relationship": "draw targets bound FBO"},
    {"pair": ["draw_calls", "depth_stencil"], "relationship": "depth/stencil test affects draw"},
    {"pair": ["draw_calls", "blending"], "relationship": "blending affects draw output"},
    {"pair": ["draw_calls", "viewport_scissor"], "relationship": "viewport/scissor clips draw"},
    {"pair": ["draw_calls", "instancing"], "relationship": "instanced draw variants"},
    {"pair": ["draw_calls", "transform_feedback"], "relationship": "draw during TF capture"},
    {"pair": ["instancing", "attributes"], "relationship": "vertexAttribDivisor for instancing"},
    {"pair": ["sync", "transform_feedback"], "relationship": "fence after TF for readback"},
    {"pair": ["sync", "pixel_ops"], "relationship": "fence before readPixels"},
    {"pair": ["sync", "buffer_ops"], "relationship": "fence before getBufferSubData"},
    {"pair": ["query", "draw_calls"], "relationship": "occlusion query wraps draw"},
    {"pair": ["query", "transform_feedback"], "relationship": "TF primitives written query"},
    {"pair": ["integer_textures", "texture_ops"], "relationship": "integer formats are texture formats"},
    {"pair": ["integer_textures", "fbo"], "relationship": "integer textures as FBO attachments"},
    {"pair": ["integer_textures", "shader_pipeline"], "relationship": "integer samplers in shaders"},
    {"pair": ["ext_float_textures", "texture_ops"], "relationship": "float formats extend textures"},
    {"pair": ["ext_float_textures", "fbo"], "relationship": "float textures as FBO attachments"},
    {"pair": ["ext_color_buffer_float", "fbo"], "relationship": "enables float render targets"},
    {"pair": ["ext_color_buffer_float", "ext_float_textures"], "relationship": "float render to float textures"},
    {"pair": ["ext_draw_buffers_indexed", "mrt"], "relationship": "per-buffer blend/mask on MRT"},
    {"pair": ["ext_draw_buffers_indexed", "fbo"], "relationship": "per-attachment control on FBO"},
    {"pair": ["ext_draw_buffers_indexed", "blending"], "relationship": "per-buffer blend equations"},
    {"pair": ["ext_texture_filter_anisotropic", "texture_ops"], "relationship": "anisotropic filtering on textures"},
    {"pair": ["ext_texture_filter_anisotropic", "sampler"], "relationship": "anisotropic filter via sampler"},
    {"pair": ["ext_compressed_textures", "texture_ops"], "relationship": "compressed formats extend textures"},
    {"pair": ["ext_disjoint_timer_query", "query"], "relationship": "timer query extends query objects"},
    {"pair": ["ext_disjoint_timer_query", "draw_calls"], "relationship": "GPU timing of draw calls"},
    {"pair": ["mrt", "blending"], "relationship": "per-target blending with MRT"},
    {"pair": ["depth_stencil", "renderbuffer"], "relationship": "depth/stencil in renderbuffer storage"}
  ]
}
```

**Topology connectivity algorithm**:

```python
def is_topology_connected(combo, topology):
    """Check if all features in an N-way combo are connected in the topology graph.

    For N=2: the pair must be a direct edge in the topology.
    For N≥3: all features must be in the same connected component of the
    subgraph induced by the combo's features. This allows transitive
    connectivity: [A, B, C] is connected if A↔B and B↔C exist, even
    without a direct A↔C edge. This captures cases like
    [buffer_ops, vao, instancing] where buffer_ops↔vao and vao↔instancing
    connect all three features through VAO.
    """
    if len(combo) < 2:
        return True

    # Build adjacency set from topology edges
    edges = set()
    for edge in topology["edges"]:
        pair = tuple(sorted(edge["pair"]))
        edges.add(pair)

    # For 2-way: direct edge check
    if len(combo) == 2:
        return tuple(sorted(combo)) in edges

    # For N≥3: check connected component via BFS on induced subgraph
    combo_set = set(combo)
    adjacency = {f: set() for f in combo_set}
    for edge in topology["edges"]:
        a, b = edge["pair"]
        if a in combo_set and b in combo_set:
            adjacency[a].add(b)
            adjacency[b].add(a)

    # BFS from first feature
    visited = set()
    queue = [combo[0]]
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        queue.extend(adjacency[node] - visited)

    return visited == combo_set
```

**Maintenance**: The topology is a one-time annotation (~55 edges for 30 categories). It changes only when feature categories are added/removed. The config validation tests (`test_config_validation.py`) verify that all topology edge endpoints reference categories that exist in `feature_categories.json`, and warn about categories with zero topology edges (potentially missing connections).

**Design note**: The topology encodes "CAN interact," not "SHOULD interact." A connected combo is eligible for recipe generation; a disconnected combo is deprioritized. The topology does not attempt to quantify interaction strength — that's Phase 2's job when available.

---

### Module: `combination_matrix.py`

**Purpose**: Compute N-way feature combination coverage across the corpus.

**Input**:
- Feature fingerprints from `feature_detection.py` for all seeds
- Optionally: interaction scores from `interaction_graph.py` (Phase 2)
- Optionally: state path data from `sequence_analyzer.py` (Phase 2)

**Algorithm**:

```python
from itertools import combinations

def compute_matrix(corpus_features, n=2, interaction_topology=None):
    """Compute n-way feature combination coverage.

    Works with Phase 1 data alone. Phase 2 enrichment is applied
    separately via enrich_matrix() when available.
    """
    all_features = sorted(set(f for fp in corpus_features.values() for f in fp["features"]))

    matrix = {}
    for combo in combinations(all_features, n):
        combo_key = tuple(sorted(combo))

        # Skip combos that are not topology-connected (if topology available)
        if interaction_topology and not is_topology_connected(combo_key, interaction_topology):
            # Still record for completeness, but mark as disconnected
            matrix[combo_key] = {
                "seed_count": 0, "distinct_fingerprints": 0, "seeds": [],
                "topology_connected": False,
            }
            continue

        seeds_with_combo = [
            f for f, fp in corpus_features.items()
            if all(c in fp["features"] for c in combo)
        ]

        # Distinct fingerprints: count unique method-set combinations
        # across covering seeds. Measures API diversity (Phase 1).
        # Phase 2 can enrich this with path signatures via enrich_matrix().
        fingerprints = set()
        for f in seeds_with_combo:
            fp = corpus_features[f]
            fp_key = tuple(
                tuple(sorted(fp.get("methods_per_feature", {}).get(c, [])))
                for c in combo_key
            )
            fingerprints.add(fp_key)

        matrix[combo_key] = {
            "seed_count": len(seeds_with_combo),
            "distinct_fingerprints": len(fingerprints),
            "seeds": seeds_with_combo,
            "topology_connected": True,
        }

    return matrix

def enrich_matrix(matrix, corpus_features, corpus_interactions, corpus_sequences):
    """Phase 2 enrichment: add interaction scores, state paths, and
    path-signature-enriched fingerprints to an existing matrix.

    Called only when Phase 2 data is available. The matrix is fully
    functional without this enrichment.
    """
    for combo_key, entry in matrix.items():
        if not entry.get("topology_connected", True):
            continue

        seeds = entry["seeds"]

        # Enrich fingerprints with path signatures for behavioral diversity
        fingerprints = set()
        for f in seeds:
            fp = corpus_features[f]
            fp_key = tuple(
                tuple(sorted(fp.get("methods_per_feature", {}).get(c, [])))
                for c in combo_key
            )
            path_sigs = tuple(sorted(fp.get("path_signatures", [])))
            fp_key = fp_key + (path_sigs,)
            fingerprints.add(fp_key)
        entry["distinct_fingerprints"] = len(fingerprints)

        # Interaction scores
        scores = []
        for seed in seeds:
            if seed in corpus_interactions:
                for interaction in corpus_interactions[seed].get("interactions", []):
                    if set(interaction["features"]) <= set(combo_key):
                        scores.append(interaction["score"])
        entry["avg_interaction_score"] = (
            sum(scores) / len(scores) if scores else 0.0
        )

        # State path coverage
        paths = set()
        for seed in seeds:
            if seed in corpus_sequences:
                paths.update(corpus_sequences[seed].get("path_signatures", []))
        entry["state_paths_covered"] = sorted(paths) if paths else []

    return matrix
```

**Gap identification**:

```python
def identify_gaps(matrix, min_seeds=1):
    """Find combinations below minimum seed threshold."""
    gaps = {}
    for combo, data in matrix.items():
        if data["seed_count"] < min_seeds:
            gaps[combo] = {
                "seed_count": data["seed_count"],
                "priority": compute_priority(combo, data),
            }
    return gaps
```

**Priority scoring** (lexicographic ordering):

Previous iterations of this design used an additive formula with 7 hardcoded constants that combined ordinal scales, boolean features, and continuous metrics into a single number. The crossover points between dimensions (e.g., "should a 3-way security gap outrank a 2-way non-security gap?") were calibration artifacts with no principled basis. Changing any constant shifted all crossover points unpredictably.

The replacement is **lexicographic ordering**: gaps are sorted by a tuple of dimensions, each resolved before considering the next. This is transparent, has no tuning constants, and produces stable rankings.

```python
SECURITY_RELEVANT = {"fbo", "buffer_ops", "transform_feedback",
                     "renderbuffer", "sync", "ext_color_buffer_float"}

UBIQUITOUS = {"shader_pipeline", "draw_calls", "attributes", "uniforms",
              "viewport_scissor", "pixel_ops"}

def compute_priority_key(combo, seed_count, depth_levels,
                         interaction_topology=None):
    """Returns a tuple for lexicographic sorting. Higher = more important gap.

    Sorting order (most significant first):
      1. ubiquitous_penalty: all-ubiquitous combos sort to the bottom (0 or 1)
      2. topology_connected: combos with known interaction paths rank higher (0 or 1)
      3. seed_count_bucket: fewer seeds = higher priority (2=zero, 1=thin, 0=covered)
      4. security_count: more security-relevant features = higher priority
      5. n_way_preference: lower n = higher priority (2-way > 3-way > 4-way)
      6. depth_deficit: shallower coverage = higher priority (tiebreaker)

    No magic numbers, no calibration needed. The ordering is:
      non-ubiquitous > ubiquitous-only
      connected > disconnected (within same ubiquity tier)
      zero-seed > thin > covered (within same connectivity tier)
      more-security > less-security (within same seed bucket)
      2-way > 3-way > 4-way (within same security count)
      shallow > deep (tiebreaker within same n-way level)
    """
    # Dimension 1: ubiquitous penalty (0=all-ubiquitous, 1=has non-ubiquitous)
    ubiq = 0 if all(f in UBIQUITOUS for f in combo) else 1

    # Dimension 2: topology connectivity (1=connected, 0=disconnected/unknown)
    if interaction_topology:
        connected = 1 if is_topology_connected(combo, interaction_topology) else 0
    else:
        connected = 1  # Without topology data, assume connected (permissive)

    # Dimension 3: seed count bucket (2=zero, 1=thin ≤2, 0=covered)
    if seed_count == 0:
        seed_bucket = 2
    elif seed_count <= 2:
        seed_bucket = 1
    else:
        seed_bucket = 0

    # Dimension 4: security relevance count
    security_count = sum(1 for f in combo if f in SECURITY_RELEVANT)

    # Dimension 5: n-way preference (invert so 2-way > 3-way > 4-way)
    n_way_pref = -len(combo)  # -2 > -3 > -4

    # Dimension 6: depth deficit (higher = shallower coverage = more important)
    DEPTH_WEIGHT = {"present": 0.0, "meaningful": 0.5, "deep": 1.0}
    if depth_levels:
        avg_depth = sum(DEPTH_WEIGHT.get(d, 0) for d in depth_levels) / len(depth_levels)
        depth_deficit = 1.0 - avg_depth
    else:
        depth_deficit = 1.0  # No seeds = maximum deficit

    return (ubiq, connected, seed_bucket, security_count, n_way_pref, depth_deficit)

def priority_label(key):
    """Map priority key to display tier."""
    ubiq, connected, seed_bucket, security_count, n_way_pref, _ = key
    if ubiq == 0:
        return "skip"  # All-ubiquitous
    if connected == 0:
        return "low"   # Not topology-connected
    if seed_bucket == 2 and security_count >= 1:
        return "high"  # Zero-seed gap with security relevance
    if seed_bucket == 2:
        return "medium"  # Zero-seed gap without security relevance
    if seed_bucket == 1:
        return "low"   # Thin coverage
    return "skip"      # Covered
```

**Design rationale**: Lexicographic ordering eliminates all calibration constants. Each dimension is independently meaningful and can be reasoned about in isolation. The ordering is transparent: "Is it ubiquitous-only? If not, is it topology-connected? If so, does it have zero seeds?" There are no accidental crossover points where changing a constant causes a 3-way security gap to flip above or below a 2-way non-security gap. The dimensions are ordered by decreasing significance: ubiquity filtering > topology connectivity > gap severity > security relevance > n-way level > depth.

**Note on `pixel_ops`**: `pixel_ops` is in `UBIQUITOUS` but NOT in `SECURITY_RELEVANT`. While pixel readback operations can be security-relevant, the `pixel_ops` category is dominated by false-positive matches from boilerplate `pixelStorei` calls (see false positive analysis in feature_detection section). Its presence in `UBIQUITOUS` reflects the empirical fact that most seeds match it, not a judgment about pixel operation security. Genuine pixel readback security concerns are better captured by the `fbo` + `pixel_ops` combination, where `fbo` provides the security relevance signal.

**Priority scoring** (Phase 2 enrichment — optional, applied when Phase 2 data is available):

When Phase 2 data is available, the priority key gains two additional tiebreaker dimensions appended after `depth_deficit`:

```python
def compute_priority_key_enriched(combo, seed_count, depth_levels,
                                   interaction_topology=None,
                                   avg_interaction_score=None,
                                   missing_security_paths=None,
                                   miss_rates=None):
    """Extended priority key with Phase 2 enrichment dimensions.

    Appends to the base key:
      7. missing_security_paths_count: more missing paths = higher priority
      8. interaction_deficit: lower interaction = higher priority
         (only if miss_rates indicate reliable tracking)
    """
    base_key = compute_priority_key(combo, seed_count, depth_levels,
                                     interaction_topology)

    # Dimension 7: missing security-relevant state paths
    security_paths = missing_security_paths or []
    missing_path_count = len(security_paths)

    # Dimension 8: interaction deficit (only reliable if miss_rate < 0.5)
    if avg_interaction_score is not None and miss_rates:
        reliable_miss_rates = [r for r in miss_rates if r < 0.5]
        if len(reliable_miss_rates) > len(miss_rates) * 0.5:
            interaction_deficit = 1.0 - avg_interaction_score
        else:
            interaction_deficit = 0.5  # Uncertain — neutral position
    else:
        interaction_deficit = 0.5  # No Phase 2 data — neutral

    return base_key + (missing_path_count, interaction_deficit)
```

Phase 2 dimensions are tiebreakers only — they never override the base ordering. A gap with zero seeds always outranks a gap with thin coverage regardless of interaction quality. This ensures Phase 2 data improves discrimination within tiers without creating surprising rank inversions.

**Output** (JSON report — Phase 1, no Phase 2 enrichment):

```json
{
  "corpus_size": 367,
  "feature_count": 30,
  "phase2_enriched": false,
  "2way_combinations": {
    "total": 171,
    "covered": 165,
    "covered_adjusted": 155,
    "uncovered": 6,
    "tautological_pairs": 4,
    "ubiquitous_only_pairs": 10,
    "topology_disconnected": 12,
    "gaps": [
      {"combo": ["sync", "integer_textures"], "seed_count": 0, "priority": "high", "topology_connected": true},
      {"combo": ["query", "pixel_ops"], "seed_count": 0, "priority": "medium", "topology_connected": true}
    ]
  },
  "3way_combinations": {
    "total": 969,
    "covered": 812,
    "covered_adjusted": 780,
    "uncovered": 157,
    "topology_disconnected": 340,
    "gaps": [
      {"combo": ["transform_feedback", "sampler", "integer_textures"], "seed_count": 0, "priority": "medium", "topology_connected": true}
    ]
  },
  "uncategorized_methods": ["newMethodFromSpec"],
  "low_diversity": [
    {"combo": ["buffer_ops", "vao"], "seed_count": 15, "distinct_fingerprints": 2, "note": "high seed count but near-duplicate coverage — fewer distinct approaches than seed_count suggests"}
  ]
}
```

**Output** (with Phase 2 enrichment):

```json
{
  "phase2_enriched": true,
  "2way_combinations": {
    "gaps": [
      {"combo": ["sync", "integer_textures"], "seed_count": 0, "priority": "high",
       "topology_connected": true, "missing_state_paths": ["use_after_delete"]}
    ]
  },
  "weak_coverage": [
    {"combo": ["fbo", "texture_ops"], "seed_count": 12, "distinct_fingerprints": 3,
     "avg_interaction_score": 0.3, "note": "many seeds but low diversity and interaction"}
  ]
}
```

Note: `weak_coverage` entries are only meaningful with Phase 2 data (they require interaction scores). Without Phase 2, only `low_diversity` is reported (based on distinct method-set fingerprints from Phase 1).
```

**CLI integration**: New `--combination-matrix` flag on the audit CLI:

```bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --combination-matrix /tmp/matrix_report.json \
  --n-way 3
```

---

## Phase 2: Depth

### Module: `resource_tracking.py`

**Purpose**: Track WebGL resource variables through the AST. Maps `create*()` return values to resource types and tracks which variables refer to which resources. This module is the foundation for both `interaction_graph.py` and `sequence_analyzer.py`.

**Why this is needed**: The existing `const_propagation.py` resolves `const` declarations to `gl.*` constants, string literals, and arrays. It explicitly **cannot** track `call_expression` return values - `const buf1 = gl.createBuffer()` produces no entry in the constants dict because `gl.createBuffer()` is a call expression, not a resolvable literal. Both interaction detection and sequence analysis need to know "this variable holds a buffer resource" which is outside const_propagation's scope.

**Input**:
- Parsed AST from `parse.py`
- Call analysis results from `call_analysis.py`
- Resolved constants from `const_propagation.py`

**Algorithm**:

1. **Collect resource creation sites**: Walk **all** `variable_declarator` nodes where the initializer is a `call_expression` matching a `gl.create*()` or `gl.fenceSync()` pattern, **regardless of declaration kind** (`const`, `let`, or `var`) **and regardless of scope** (top-level, inside try-catch blocks, inside if-blocks, inside functions):
   ```
   const buf1 = gl.createBuffer()      → resource "buf1", type "buffer"
   let tex1 = gl.createTexture()       → resource "tex1", type "texture"
   var fbo1 = gl.createFramebuffer()   → resource "fbo1", type "framebuffer"
   const rb1  = gl.createRenderbuffer() → resource "rb1", type "renderbuffer"
   const vao1 = gl.createVertexArray() → resource "vao1", type "vertex_array"
   const tf1  = gl.createTransformFeedback() → resource "tf1", type "transform_feedback"
   const q1   = gl.createQuery()       → resource "q1", type "query"
   const s1   = gl.createSampler()     → resource "s1", type "sampler"
   const sync1 = gl.fenceSync(...)     → resource "sync1", type "sync"
   const prog1 = gl.createProgram()    → resource "prog1", type "program"
   const sh1  = gl.createShader(...)   → resource "sh1", type "shader"
   ```

   **Scope handling**: In the corpus, most resource creation happens inside try-catch blocks (the three-zone architecture places all setup in try-catch). The tree-sitter AST walk visits `variable_declarator` nodes inside `try_statement` → `statement_block` → `lexical_declaration`/`variable_declaration` nodes. The walker does not filter by scope — it collects all `variable_declarator` nodes from the entire AST, consistent with the linear-walk-assuming-all-try-blocks-succeed design of `sequence_analyzer.py`.

   **Multiple declarators**: A single statement like `const a = gl.createBuffer(), b = gl.createTexture()` produces two `variable_declarator` nodes in the AST. Each is processed independently.

2. **Map resource types to feature categories** (using `docs/resource_types.json`):

   **Config file format** (`docs/resource_types.json`):
   ```json
   {
     "version": 1,
     "resource_type_map": {
       "buffer": "buffer_ops",
       "texture": "texture_ops",
       "framebuffer": "fbo",
       "renderbuffer": "renderbuffer",
       "vertex_array": "vao",
       "transform_feedback": "transform_feedback",
       "query": "query",
       "sampler": "sampler",
       "sync": "sync",
       "program": "shader_pipeline",
       "shader": "shader_pipeline"
     },
     "create_method_map": {
       "createBuffer": "buffer",
       "createTexture": "texture",
       "createFramebuffer": "framebuffer",
       "createRenderbuffer": "renderbuffer",
       "createVertexArray": "vertex_array",
       "createTransformFeedback": "transform_feedback",
       "createQuery": "query",
       "createSampler": "sampler",
       "fenceSync": "sync",
       "createProgram": "program",
       "createShader": "shader"
     }
   }
   ```

3. **Track variable usage**: For each `gl.*` call in the AST, check if any argument is an identifier in the resource map. Record which resource is used where.

**Scope and limitations** (explicit design choices):

- **All declaration kinds tracked**: `const`, `let`, and `var` declarations are all handled. For `let`/`var` where the variable is reassigned (`let buf = gl.createBuffer(); buf = gl.createBuffer()`), the second assignment overwrites the first in the resource map.
- **All scopes walked**: Declarations inside try-catch blocks, if-blocks, and nested functions are all collected. This is consistent with the linear-walk design used by `sequence_analyzer.py`.
- **Simple variable names only**: Tracks `const buf1 = gl.createBuffer()` but NOT:
  - Array storage: `buffers[i] = gl.createBuffer()` - skipped (not a `variable_declarator`)
  - Object properties: `state.buffer = gl.createBuffer()` - skipped (not a `variable_declarator`)
  - Helper function returns: `function makeBuf() { return gl.createBuffer(); }` - skipped (return value not captured as a named variable at the call site)
  - Bare calls: `gl.createBuffer()` without assignment - skipped (no variable to map)
- **Name-based heuristic matching**: Argument matching uses the variable name as the identifier. If the AST shows `gl.bindBuffer(gl.ARRAY_BUFFER, buf1)` and `buf1` is in the resource map, that's a match. This works well for the corpus's coding conventions (simple variable names, no aliasing).
- **No cross-function tracking**: Resources created in one function and used in another are only tracked if the variable name appears at both sites. This is name-based, not scope-aware — if a helper creates `const buf` and the caller also has `const buf`, they collide in the resource map. In practice this is rare in the corpus.
- **This is intentionally conservative**: False negatives (missed interactions) are acceptable; false positives (phantom interactions) are not. The interaction graph will undercount rather than overcount.

**Miss rate reduction patterns** (mandatory Phase 2 improvement, integrated into `resource_tracking.py`):

The ~40% corpus miss rate is dominated by three trackable patterns. Implementing these should reduce the corpus miss rate to <20%:

1. **Separated assignments**: `let buf; ... buf = gl.createBuffer()` — Track `assignment_expression` nodes where the left-hand side is an identifier already in scope (from a prior `let`/`var` declaration) and the right-hand side matches a `gl.create*()` call. Add the identifier to the resource map at the assignment site. If the identifier was already in the resource map (from a prior assignment or declaration), overwrite it (same as current `let`/`var` reassignment behavior).

2. **Array push patterns**: `resources.push(gl.createBuffer())` — Track `call_expression` nodes where the callee is `<identifier>.push()` and the argument matches a `gl.create*()` call. Map the array variable as a "collection" resource with type derived from the `create*` method. When the array variable appears as an argument to a subsequent `gl.*` call (e.g., `gl.bindBuffer(target, resources[i])`), record a usage site for the collection. This is approximate — individual array elements are not tracked, but the resource type association is captured.

3. **Scope-shadowed variables**: When the same variable name is declared with `const` or `let` in different try-catch blocks (e.g., `const buf` in block 3 and `const buf` in block 5), treat each as a distinct resource by appending a scope-disambiguating suffix (`buf#1`, `buf#2`). The suffix is derived from a monotonically increasing counter per variable name. This prevents phantom use-after-delete detection in `sequence_analyzer.py` — without disambiguation, `delete(buf)` in block 3 and `bind(buf)` in block 5 appears as a use-after-delete even though they refer to different resources.

   **`var` declarations are excluded from disambiguation**: JavaScript's `var` is function-scoped, not block-scoped. A `var buf` declared in try-block 3 IS the same variable as `var buf` referenced in try-block 5 — they share function scope. Disambiguating `var` declarations across blocks would be incorrect: `var buf = gl.createBuffer()` in block 3, `gl.deleteBuffer(buf)` in block 3, and `gl.bindBuffer(target, buf)` in block 5 is a genuine use-after-delete because `buf` persists across blocks. Only `const` and `let` (which are block-scoped and create genuinely distinct variables per block) should be disambiguated. In practice, the corpus overwhelmingly uses `const`, so this distinction rarely matters — but the implementation must check the declaration kind before applying the suffix.

**Miss rate targets** (integrated into Implementation Order):
- Phase 2, step 3: Implement these three patterns as explicit sub-tasks of `resource_tracking.py`
- Phase 2, step 4: After running against full corpus, evaluate miss rate. Target: corpus_avg_miss_rate < 0.20. This is a noted checkpoint, not a blocking gate — if the target isn't met, document which patterns remain untracked and proceed.

**Miss rate instrumentation** (required, not optional):

The corpus contains two distinct seed populations: mutation seeds (`mutation_b*`) which use simple variable names and conform well to resource tracking assumptions, and creative/multipass/high-biomass seeds which frequently use arrays (`const textures = []`), helper functions (`function createProgram() { return gl.createProgram(); }`), and inline variable declarations. Empirically, ~40% of the corpus uses patterns that resource tracking will miss.

Resource tracking **must** report its miss rate per seed:

```python
@dataclass
class ResourceTrackingResult:
    resource_map: ResourceMap
    miss_report: MissReport

@dataclass
class MissReport:
    total_create_calls: int       # All gl.create*() / gl.fenceSync() calls found in AST
    tracked_creates: int          # Subset that were simple variable_declarator assignments
    untracked_creates: int        # total - tracked (array storage, helpers, bare calls, etc.)
    miss_rate: float              # untracked / total (0.0 = perfect, 1.0 = total miss)
    untracked_reasons: list[str]  # e.g. ["array_storage: textures[i] = gl.createTexture()",
                                  #        "helper_return: createProgram() wraps gl.createProgram()"]
```

The miss report is computed during the AST walk by counting **all** `call_expression` nodes matching `gl.create*` or `gl.fenceSync` patterns, regardless of whether the return value is captured in a trackable variable. Any create call that doesn't produce a resource map entry increments `untracked_creates` with a reason tag.

**Corpus-level miss rate reporting**: The CLI outputs aggregate miss statistics:
```json
{
  "resource_tracking_coverage": {
    "total_seeds": 367,
    "seeds_with_zero_miss": 245,
    "seeds_with_partial_miss": 80,
    "seeds_with_total_miss": 42,
    "corpus_avg_miss_rate": 0.18,
    "worst_miss_seeds": ["creative_fractal_nebula_forge.html", "multipass_screen_space_effects.html"]
  }
}
```

**How downstream modules use miss rate**: The interaction graph and sequence analyzer already undercount by design. The miss rate makes this undercounting *visible* and *quantified*:
- Seeds with miss_rate > 0.5 are flagged as "low-confidence" in interaction and sequence analyzer outputs
- The combination matrix marks combinations where all contributing seeds have miss_rate > 0.5 as "unreliable depth data"
- Gap recipes include a `depth_confidence` field derived from miss rates of seeds covering similar features

**Output**:

```python
@dataclass
class ResourceMap:
    resources: dict[str, ResourceInfo]   # variable_name → ResourceInfo

@dataclass
class ResourceInfo:
    var_name: str          # "buf1" or "resources" (for collections)
    resource_type: str     # "buffer"
    feature_category: str  # "buffer_ops"
    create_method: str     # "createBuffer"
    is_collection: bool    # True for array push patterns (approximate tracking)
    usage_sites: list[UsageSite]  # Where this resource appears as an argument

@dataclass
class UsageSite:
    method: str            # "bindBuffer", "framebufferTexture2D"
    feature_category: str  # Feature category of the method (from feature_detection)
    arg_position: int      # Which argument position (0-indexed)
```

---

### Module: `interaction_graph.py`

**Purpose**: Detect whether features within a seed actually interact (shared resources, state dependencies) or just co-exist independently.

**Input**:
- Resource map from `resource_tracking.py`
- Call analysis results from `call_analysis.py`
- Feature fingerprint from `feature_detection.py`

**Algorithm**:

1. **Resource map consumption**: Use the resource map from `resource_tracking.py` which provides variable-name → resource-type → feature-category mappings. No redundant AST walking needed.

2. **Cross-feature reference detection**: For each WebGL call, check if its arguments reference resources from a different feature category (using resource map usage sites):
   ```
   gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex1, 0)
   → fbo method using texture resource → interaction: fbo ↔ texture_ops

   gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, buf1)
   → transform_feedback method using buffer resource → interaction: transform_feedback ↔ buffer_ops
   ```

3. **Shared binding point detection**: Identify when features bind resources to the same GL binding point. This uses a static mapping of methods to binding points (no runtime state simulation):
   ```python
   # Defined in docs/state_paths.json under "binding_points"
   BINDING_POINTS = {
       "ARRAY_BUFFER": ["buffer_ops"],
       "ELEMENT_ARRAY_BUFFER": ["buffer_ops"],
       "TRANSFORM_FEEDBACK_BUFFER": ["transform_feedback", "buffer_ops"],
       "UNIFORM_BUFFER": ["ubo", "buffer_ops"],
       "FRAMEBUFFER": ["fbo"],
       "DRAW_FRAMEBUFFER": ["fbo"],
       "READ_FRAMEBUFFER": ["fbo"],
       "RENDERBUFFER": ["renderbuffer"],
       "TEXTURE_2D": ["texture_ops"],
       "TEXTURE_3D": ["texture_3d"],
       "TEXTURE_2D_ARRAY": ["texture_arrays"],
       "TEXTURE_CUBE_MAP": ["texture_ops"],
   }
   ```
   When two different feature categories both have methods that target the same binding point in a seed, that's a shared binding point interaction. Example: `bindBufferBase(TRANSFORM_FEEDBACK_BUFFER, 0, buf1)` targets `TRANSFORM_FEEDBACK_BUFFER` which maps to `["transform_feedback", "buffer_ops"]` — interaction detected.

   **Explicit non-goal**: Texture unit tracking (which requires simulating `activeTexture` state to know which unit `bindTexture`/`bindSampler` affects) is **out of scope**. Texture-sampler interactions are detected via resource-based cross-references (sampler and texture both appear as arguments to calls in the same seed), not via texture unit state simulation. This is consistent with the feedback loop detection scope.

4. **Interaction scoring**: Count the number of cross-feature references and shared binding points:
   - Each cross-feature resource reference: +1
   - Each shared binding point: +1
   - Each resource lifecycle dependency (e.g., buffer must be created before transform feedback can bind it): +1

**Output per seed**:

```json
{
  "interactions": [
    {
      "features": ["fbo", "texture_ops"],
      "score": 3,
      "evidence": [
        "framebufferTexture2D references tex1",
        "framebufferTexture2D references tex2",
        "both modify FRAMEBUFFER binding state"
      ]
    },
    {
      "features": ["buffer_ops", "transform_feedback"],
      "score": 2,
      "evidence": [
        "bindBufferBase(TRANSFORM_FEEDBACK_BUFFER) references buf1",
        "lifecycle dependency: buffer created before TF bind"
      ]
    }
  ],
  "isolated_features": ["blending"],
  "total_interaction_score": 5,
  "interaction_density": 0.71
}
```

**Interaction density** = interacting_pair_count / max_possible_pairs. A seed with 5 features has C(5,2) = 10 possible pairs. If 7 pairs have score > 0, density = 0.7. Note: this counts *pairs with any interaction*, not the sum of scores — using the score sum would allow density > 1.0 (a pair with score 3 would contribute 3 to the numerator), making the metric counterintuitive.

**Corpus-level aggregation**: For each feature pair, aggregate interaction scores across all seeds that contain both features. Identify pairs with many seeds but consistently low interaction (weak coverage).

**Implementation notes**:
- Resource tracking is delegated to `resource_tracking.py` (see module description above). The interaction graph consumes the `ResourceMap` output and iterates over `usage_sites` to find cross-feature references.
- Cross-feature detection: for each usage site where a resource's `feature_category` differs from the method's `feature_category`, record an interaction edge.
- Shared binding point detection uses the `binding_points` map from `docs/state_paths.json`. For each `gl.bind*()` call in the seed, resolve the binding target constant (via `const_propagation`) and look up which feature categories use that binding point. If two categories share a binding point within the same seed, record a shared binding point interaction.
- **Texture unit interactions** are NOT detected via state simulation. Instead, texture-sampler interactions are caught when the same seed contains both `bindTexture` and `bindSampler` calls (detected via feature co-occurrence) and, if resource tracking captures the sampler/texture variables, via cross-feature resource references.
- **Inherited limitations from resource_tracking**: interactions involving array-stored resources, helper-function-passed resources, or reassigned variables will be missed. This undercounting is acceptable - the metric identifies *confirmed* interactions, not exhaustive ones.

**What interaction scoring does NOT capture** (explicit scope boundaries):

The interaction graph detects resource-level and binding-point-level interactions. It cannot detect:

- **State-based interactions**: `enable(DEPTH_TEST)` affects `drawArrays` behavior, but there's no shared resource — the interaction is through implicit GL state. These are real interactions that matter for fuzzing (enabling/disabling capabilities changes how draw calls behave), but detecting them would require a GL state simulator.
- **Shader-mediated interactions**: A shader reads a texture that was written via FBO. The interaction exists semantically but requires understanding shader source → uniform/sampler bindings → texture units → FBO attachments. This crosses the boundary between GL call analysis and shader analysis.
- **Ordering-dependent interactions**: The *interesting* fuzzing targets are cases where reordering calls produces different behavior (bind before upload matters). The interaction graph records that both calls exist, not that their ordering creates a dependency. `sequence_analyzer.py` partially captures this via lifecycle patterns, but it operates independently of the interaction graph — they don't compose.

These limitations mean the interaction score is a **lower bound** on actual interaction. A score of 0 does NOT mean features don't interact — it means we couldn't confirm interaction via resource tracking. A score of 3 vs. 5 indicates more resource-sharing evidence but says nothing about the fuzzing potential of those interactions. The score is most useful for detecting the *absence* of any detectable interaction (score = 0), not for ranking interaction quality between non-zero scores.

---

### Module: `sequence_analyzer.py`

**Purpose**: Extract WebGL call sequences from each seed and match them against a catalog of security-relevant patterns. This is a **linear sequence extractor with pattern matching**, not a GL state simulator — it does not model runtime GL state (current bindings, enabled flags). It detects *potential* patterns in source order that Radamsa mutations could activate.

**Naming rationale**: Named `sequence_analyzer` rather than `state_machine` because it extracts and pattern-matches call sequences without simulating actual GL state transitions. A true state machine would track what's bound to each target and which capabilities are enabled — that level of simulation is out of scope.

**Input**:
- Parsed AST from `parse.py` (execution-order walk)
- Resource map from `resource_tracking.py` (for lifecycle tracking)
- Call analysis results from `call_analysis.py`
- Resolved constants from `const_propagation.py` (for enum value resolution)

**Call sequence categories**:

| Category | Operations tracked | Example sequence |
|----------|--------------------------|--------------|
| Binding | `bindBuffer`, `bindTexture`, `bindFramebuffer`, `bindRenderbuffer`, `bindVertexArray`, `bindSampler`, `bindTransformFeedback` | `bind(buf1) → bind(buf2) → bind(null) → bind(buf1)` |
| Enable/Disable | `enable`, `disable` | `enable(DEPTH_TEST) → disable(DEPTH_TEST) → enable(DEPTH_TEST)` |
| Active state | `activeTexture`, `useProgram` | `activeTexture(TEXTURE0) → activeTexture(TEXTURE1)` |
| Resource lifecycle | `create*`, `bind*`, `*Data`/`*Image*`/`*Storage*`, `draw*`, `delete*` | `create → bind → upload → use → delete` |
| Begin/End blocks | `beginQuery`/`endQuery`, `beginTransformFeedback`/`endTransformFeedback` | `begin → draw → end → begin → draw → end` |

**Algorithm**:

1. **Walk AST in execution order**: Extract all `gl.*` calls in sequential order, treating the entire seed as a **linear sequence**.

   **Explicit assumption (try-catch handling)**: All try blocks are assumed to execute successfully. The seed is treated as if every statement runs in source order. This is a deliberate simplification:
   - **Why not branch tracking**: Seeds have 6-10 independent try-catch blocks. Tracking both paths per block produces 2^N combinatorial paths (64-1024), which is impractical for pattern matching.
   - **Why this is acceptable**: The purpose is to detect *potential* state patterns that Radamsa mutations could trigger. If the source code has `delete(buf)` in block 3 and `bind(buf)` in block 5, the use-after-delete pattern exists regardless of whether block 3 actually succeeds at runtime. The mutator can corrupt the seed to make any execution path reachable.
   - **Known limitation**: Patterns detected may not occur in un-mutated execution. This is fine - we're analyzing mutation *potential*, not runtime behavior.

2. **Classify each call**: Map to a state transition category and extract the state key:
   ```
   gl.bindBuffer(gl.ARRAY_BUFFER, buf1)
   → category: "binding", state_key: "ARRAY_BUFFER", value: "buf1"

   gl.enable(gl.DEPTH_TEST)
   → category: "enable_disable", state_key: "DEPTH_TEST", value: true

   gl.deleteBuffer(buf1)
   → category: "lifecycle", resource: "buf1", stage: "delete"
   ```

3. **Build transition sequences**: Group by state key, record value changes:
   ```
   binding/ARRAY_BUFFER: [buf1, buf2, null, buf1]
   enable_disable/DEPTH_TEST: [true, false, true]
   lifecycle/buf1: [create, bind, bufferData, bindBuffer, draw, delete, bind]
   ```

4. **Extract path signatures**: Normalize sequences into canonical patterns:
   - `bind_rebind`: `[A, B, A]` or `[A, null, A]`
   - `enable_thrash`: `[true, false, true]` or longer toggles
   - `use_after_delete`: lifecycle contains `[..., delete, ..., bind/use]`
   - `create_without_delete`: lifecycle ends without `delete`
   - `double_delete`: lifecycle contains `[..., delete, ..., delete]`
   - `begin_end_cycle`: `[begin, ..., end, begin, ..., end]`
   - `nested_binding`: binding changes while a begin/end block is active

**Scope-shadowed variable handling**: The sequence analyzer uses scope-disambiguated resource names from `resource_tracking.py` (e.g., `buf#1`, `buf#2`) to avoid phantom lifecycle patterns. Disambiguation applies only to `const`/`let` declarations (which are block-scoped); `var` declarations are NOT disambiguated because `var` is function-scoped and the same variable genuinely persists across try-catch blocks. Without disambiguation, a seed with `const buf = gl.createBuffer(); gl.deleteBuffer(buf);` in try-block 3 and `const buf = gl.createBuffer(); gl.bindBuffer(target, buf);` in try-block 5 produces a false `use_after_delete` because the flat walk treats both `buf` as the same resource. With scope disambiguation, these become `buf#1` (created, deleted in block 3) and `buf#2` (created, bound in block 5) — two independent lifecycles with no cross-contamination.

**Known limitation**: `let` reassignment within the same scope still causes collisions. If a single try-block contains `let buf = gl.createBuffer(); gl.deleteBuffer(buf); buf = gl.createBuffer(); gl.bindBuffer(target, buf);`, the second `buf` overwrites the first in the resource map (same scope, same name), so the lifecycle shows `create → delete → create → bind` which is correct. The problematic case is only cross-scope name shadowing of `const`/`let`, which the suffix mechanism handles.

**Config file format** (`docs/state_paths.json`):

```json
{
  "version": 1,
  "binding_points": {
    "ARRAY_BUFFER": ["buffer_ops"],
    "ELEMENT_ARRAY_BUFFER": ["buffer_ops"],
    "COPY_READ_BUFFER": ["buffer_ops"],
    "COPY_WRITE_BUFFER": ["buffer_ops"],
    "PIXEL_PACK_BUFFER": ["buffer_ops", "pixel_ops"],
    "PIXEL_UNPACK_BUFFER": ["buffer_ops", "pixel_ops"],
    "TRANSFORM_FEEDBACK_BUFFER": ["transform_feedback", "buffer_ops"],
    "UNIFORM_BUFFER": ["ubo", "buffer_ops"],
    "FRAMEBUFFER": ["fbo"],
    "DRAW_FRAMEBUFFER": ["fbo"],
    "READ_FRAMEBUFFER": ["fbo"],
    "RENDERBUFFER": ["renderbuffer"],
    "TEXTURE_2D": ["texture_ops"],
    "TEXTURE_3D": ["texture_3d"],
    "TEXTURE_2D_ARRAY": ["texture_arrays"],
    "TEXTURE_CUBE_MAP": ["texture_ops"],
    "TRANSFORM_FEEDBACK": ["transform_feedback"]
  },
  "path_catalog": {
    "use_after_delete": {
      "description": "Resource used after deletion - UAF potential",
      "security_relevance": "high",
      "pattern": "lifecycle contains delete followed by bind or use"
    },
    "double_delete": {
      "description": "Resource deleted twice - double-free potential",
      "security_relevance": "high",
      "pattern": "lifecycle contains two delete operations"
    },
    "bind_rebind": {
      "description": "Same binding point rebound multiple times",
      "security_relevance": "medium",
      "pattern": "binding sequence has repeated values"
    },
    "enable_thrash": {
      "description": "State toggled on/off/on rapidly",
      "security_relevance": "medium",
      "pattern": "enable_disable sequence has 3+ alternations"
    },
    "orphan_resource": {
      "description": "Resource created but never properly deleted",
      "security_relevance": "low",
      "pattern": "lifecycle has create but no delete"
    },
    "bind_during_block": {
      "description": "Binding changes during begin/end block",
      "security_relevance": "high",
      "pattern": "binding change between begin and end calls"
    },
    "cross_fbo_draw": {
      "description": "Draw calls across different FBO bindings",
      "security_relevance": "medium",
      "pattern": "draw occurs, then FBO rebind, then draw"
    },
    "feedback_loop": {
      "description": "Same texture used as both FBO attachment and sampler input (DEFERRED — see design rationale)",
      "security_relevance": "high",
      "detection_level": "deferred",
      "pattern": "DEFERRED: Feedback loops are a specific driver bug class better addressed by intentionally constructing 2-3 dedicated seeds rather than corpus-wide heuristic detection. The detection algorithm (name-based matching with FBO-switch suppression) requires disproportionate implementation complexity relative to its utility — it's the most complex piece of the sequence analyzer but targets a single vulnerability pattern. If feedback loop coverage is desired, write dedicated seeds that explicitly create feedback loops (attach texture to FBO, bind same texture to sampler, draw). This is cheaper and more reliable than heuristic detection with known false positive/negative rates."
    }
  }
}
```

Note: `binding_points` maps GL binding target constants to the feature categories that use them. When two categories share a binding point in the same seed, `interaction_graph.py` records a shared binding point interaction. The `path_catalog` defines security-relevant state patterns that `sequence_analyzer.py` checks for.

**Output per seed**:

```json
{
  "transitions": [
    {"category": "binding", "state_key": "ARRAY_BUFFER", "sequence": ["buf1", "buf2", "null", "buf1"], "length": 4},
    {"category": "enable_disable", "state_key": "DEPTH_TEST", "sequence": [true, false, true], "length": 3},
    {"category": "lifecycle", "resource": "tex1", "stages": ["create", "bind", "texImage2D", "delete", "bind"], "length": 5}
  ],
  "path_signatures": ["bind_rebind", "enable_thrash", "use_after_delete"],
  "missing_catalog_paths": ["double_delete", "bind_during_block"],
  "unique_transition_count": 7,
  "max_sequence_length": 5
}
```

**Corpus-level aggregation**:

```json
{
  "catalog_coverage": {
    "use_after_delete": {"seed_count": 45, "coverage": "good"},
    "double_delete": {"seed_count": 3, "coverage": "thin"},
    "bind_rebind": {"seed_count": 180, "coverage": "saturated"},
    "feedback_loop": {"seed_count": 0, "coverage": "deferred"}
  },
  "total_unique_paths": 23,
  "avg_paths_per_seed": 3.2
}
```

**Implementation notes**:
- Try-catch blocks are traversed linearly (see assumption above). Catch block bodies are ignored (they contain `{}` in production seeds anyway).
- Enum value resolution uses `const_propagation.py` to resolve `enable`/`disable` arguments to `gl.*` constants.
- Resource lifecycle tracking uses `resource_tracking.py` to map variable names to resource types. Lifecycle stages are derived from the method name: `createBuffer` → "create", `bindBuffer` with resource arg → "bind", `deleteBuffer` → "delete", etc.
- The path catalog is stored in `docs/state_paths.json` under a `path_catalog` key.
- Feedback loop detection is **deferred** (see catalog entry). If feedback loop coverage is needed, write dedicated seeds rather than attempting corpus-wide heuristic detection.

---

### Phase 2 integration with combination matrix (optional enrichment)

When Phase 2 data is available, the combination matrix gains two enrichment dimensions via `enrich_matrix()`:

1. **Interaction quality**: For each covered combination, report the average interaction score from `interaction_graph.py`. A combination with many seeds but low interaction is "weak coverage." (Only meaningful with Phase 2; without it, the matrix reports seed counts and method-set diversity only.)

2. **State path coverage**: For each covered combination, report which sequence patterns from the catalog are exercised. A combination might be "covered" but missing critical security-relevant paths.

**Without Phase 2**, the gap report contains:
```json
{"combo": ["fbo", "texture_ops"], "seed_count": 12, "priority": "low",
 "distinct_fingerprints": 3, "topology_connected": true}
```

**With Phase 2 enrichment**, the same gap gains quality dimensions:
```json
{
  "combo": ["fbo", "texture_ops"],
  "seed_count": 12,
  "distinct_fingerprints": 5,
  "avg_interaction_score": 0.3,
  "missing_state_paths": ["cross_fbo_draw"],
  "priority": "medium",
  "note": "12 seeds but low interaction quality and missing security-relevant paths"
}
```

Phase 3's `gap_spec.py` consumes either format — it generates recipes from whatever data is available (see Phase 3 section).

---

## Phase 3: Generation

### Module: `gap_spec.py`

**Purpose**: Consume analysis outputs and produce structured "seed recipes" — machine-readable specifications for what each new seed should contain. Works with Phase 1 data alone; Phase 2 data enriches recipes when available.

**Input** (required — Phase 1):
- Combination matrix gap report (from `combination_matrix.py`)
- Feature fingerprints (from `feature_detection.py`)
- Interaction topology (from `docs/interaction_topology.json`)
- API audit method/constant coverage (from existing `report.py`)

**Input** (optional — Phase 2 enrichment):
- Interaction patterns (from `interaction_graph.py`) — adds `interaction_requirements` to recipes
- State path catalog coverage (from `sequence_analyzer.py`) — adds `required_state_paths` to recipes
- When Phase 2 data is absent, recipes omit interaction and state path fields. The seed-writing LLM receives method/feature targeting only — which is the primary signal anyway.

**Recipe generation algorithm**:

1. **Filter gaps for relevance** before ranking. With 30 categories, 3-way produces C(30,3) = 4,060 combinations, most with 0 seeds. Unfiltered recipe generation produces hundreds of low-value recipes targeting unrelated niche feature combos. The relevance filter is applied *before* priority scoring to prune the universe:

   ```python
   SECURITY_RELEVANT = {"fbo", "buffer_ops", "transform_feedback",
                        "renderbuffer", "sync", "ext_color_buffer_float"}
   UBIQUITOUS = {"shader_pipeline", "draw_calls", "attributes", "uniforms",
                  "viewport_scissor", "pixel_ops"}
   EXTENSION_CATEGORIES = {"ext_float_textures", "ext_color_buffer_float",
                           "ext_draw_buffers_indexed", "ext_texture_filter_anisotropic",
                           "ext_compressed_textures", "ext_disjoint_timer_query"}

   def is_relevant_gap(combo):
       """Filter out gaps that aren't worth generating recipes for.

       A gap is relevant if it meets ANY of:
       1. Contains at least one security-relevant feature
       2. Contains at least one non-ubiquitous, non-extension core feature
       3. Is a 2-way gap (all 2-way gaps are relevant due to small universe)

       A gap is EXCLUDED if:
       - All features are ubiquitous (shader_pipeline + draw_calls + uniforms = boring)
       - All features are extension categories (ext_float + ext_compressed + ext_timer = unlikely to interact)
       - It contains more than 1 extension category AND no security-relevant feature
         (extension combos rarely produce meaningful interactions — but security-relevant
         features like fbo justify multi-extension combos, e.g., float texture rendering)
       """
       n = len(combo)

       # All 2-way gaps pass (C(30,2) = 435, manageable)
       if n == 2:
           return True

       # Reject all-ubiquitous
       if all(f in UBIQUITOUS for f in combo):
           return False

       # Reject all-extension
       if all(f in EXTENSION_CATEGORIES for f in combo):
           return False

       # Must contain at least one security-relevant OR one non-ubiquitous core feature
       core_non_ubiquitous = [f for f in combo
                              if f not in UBIQUITOUS and f not in EXTENSION_CATEGORIES]
       has_security = any(f in SECURITY_RELEVANT for f in combo)

       # Reject combos with 2+ extension categories UNLESS a security-relevant feature
       # is present (e.g., [fbo, ext_float_textures, ext_color_buffer_float] is valid
       # because fbo is security-relevant — float texture rendering to FBO is a real
       # attack surface)
       ext_count = sum(1 for f in combo if f in EXTENSION_CATEGORIES)
       if ext_count > 1 and not has_security:
           return False

       return has_security or len(core_non_ubiquitous) >= 1
   ```

   **Semantic orthogonality**: The structural filter above catches syntactic irrelevance (all-ubiquitous, all-extension) but cannot detect *semantic* orthogonality. A combo like `[sync, integer_textures, ext_texture_filter_anisotropic]` passes the filter (has non-ubiquitous core features) but these three features have no meaningful interaction surface.

   This is solved by the **feature interaction topology** (`docs/interaction_topology.json`) — a static, manually-curated graph of which feature categories can meaningfully interact. See the "Feature Interaction Topology" section below for the full specification. The `is_topology_connected()` function checks whether all features in a combo are connected via the topology graph. Disconnected combos are deprioritized in the lexicographic ordering (dimension 2: `topology_connected`).

   **Expected pruning effect**: The structural filter reduces 3-way combinations from ~4,060 to ~800-1,200 relevant gaps. The topology connectivity check further reduces this to ~200-400 connected, relevant gaps — eliminating the ~60% of structurally-relevant-but-semantically-orthogonal combinations that would otherwise require human review to skip. The remaining recipes should have <10% semantically weak combinations (down from 30-40% without topology filtering).

   The filter is deliberately permissive (most non-trivial combos pass). It eliminates the clearly useless tail — combos like `[ext_compressed_textures, ext_disjoint_timer_query, glsl_builtins]` or `[shader_pipeline, draw_calls, attributes]` — without risking false exclusion of interesting gaps.

2. **Rank filtered gaps** by lexicographic priority using `compute_priority_key()` (or `compute_priority_key_enriched()` when Phase 2 data is available). Gaps with `priority_label == "skip"` are excluded from recipe generation.

3. **Generate recipe per gap**:

```json
{
  "recipe_id": "gap_001",
  "priority": "high",
  "target_features": ["transform_feedback", "sampler", "integer_textures"],
  "topology_connected": true,
  "reason": "Uncovered 3-way combination with security-relevant features",

  "required_methods": {
    "transform_feedback": ["beginTransformFeedback", "endTransformFeedback", "transformFeedbackVaryings"],
    "sampler": ["createSampler", "bindSampler", "samplerParameteri"],
    "integer_textures": ["clearBufferiv"]
  },
  "bonus_methods": ["getTransformFeedbackVarying", "getSamplerParameter"],

  "topology_edges": [
    {"pair": ["transform_feedback", "buffer_ops"], "relationship": "TF captures buffer output"},
    {"pair": ["sampler", "texture_ops"], "relationship": "sampler configures texture filtering"}
  ],

  "required_state_paths": ["bind_rebind", "use_after_delete"],
  "bonus_state_paths": ["enable_thrash", "begin_end_cycle"],

  "interaction_requirements": [
    {
      "features": ["transform_feedback", "sampler"],
      "suggested_interaction": "sampler bound to texture unit receiving TF output"
    },
    {
      "features": ["sampler", "integer_textures"],
      "suggested_interaction": "sampler configured for integer texture format"
    }
  ],

  "seed_constraints": {
    "tier1_vars": {"min": 5, "max": 8},
    "tier3_enums": {
      "min": 4, "max": 6,
      "derived_from_categories": ["TRANSFORM_FEEDBACK_BUFFER", "TEXTURE_2D", "R32I", "NEAREST"]
    },
    "try_catch_blocks": {"min": 6, "max": 10, "setup": {"min": 4, "max": 8}, "execution": {"min": 2, "max": 4}},
    "line_repetition_patterns": {"min": 3},
    "inline_literals": {"min": 20, "max": 40},
    "total_lines": {"min": 150, "max": 300}
  },

  "reference_seeds": [
    "agent_outputs/mutation_b34_s190_tf_sampler.html",
    "agent_outputs/mutation_b22_s112_integer_tex.html"
  ]
}
```

**Phase 2 field availability**: The `required_state_paths`, `bonus_state_paths`, and `interaction_requirements` fields are populated only when Phase 2 data is available. Without Phase 2, recipes contain `required_methods`, `bonus_methods`, `topology_edges`, `seed_constraints`, and `reference_seeds` — which is sufficient context for the seed-writing LLM. The `topology_edges` field (derived from the static interaction topology, not Phase 2 runtime analysis) provides lightweight interaction guidance even without Phase 2.

4. **Seed constraint derivation algorithm**:

   Recipe constraints are derived mechanically from the category definitions and reference seeds — no hand-coded domain knowledge:

   ```python
   def derive_constraints(target_features, categories_config, reference_seeds_data):
       """Derive seed_constraints from category definitions and reference seeds."""

       # tier3_enums: union of all constants from target feature categories
       tier3_candidates = []
       for feature in target_features:
           cat = categories_config["categories"][feature]
           tier3_candidates.extend(cat.get("constants", []))
       # Deduplicate, take first 6 (sorted for determinism)
       tier3_enums = sorted(set(tier3_candidates))[:6]

       # tier1_vars and line_repetition_patterns: NOT specified in recipe.
       # These are generic structural requirements (counts only, no suggestions).
       # The seed-writing LLM infers appropriate variable names from:
       #   (a) the required_methods (which imply resource types and sizes), and
       #   (b) the reference seeds (which demonstrate naming conventions).
       # Providing suggestions here would require WebGL domain knowledge that
       # the gap analyzer doesn't have, and would likely be worse than what
       # the LLM infers from context.

       return {
           "tier1_vars": {"min": 5, "max": 8},
           "tier3_enums": {"min": 4, "max": 6, "derived_from_categories": tier3_enums},
           "try_catch_blocks": {"min": 6, "max": 10,
                                "setup": {"min": 4, "max": 8},
                                "execution": {"min": 2, "max": 4}},
           "line_repetition_patterns": {"min": 3},
           "inline_literals": {"min": 20, "max": 40},
           "total_lines": {"min": 150, "max": 300},
       }
   ```

   **Design rationale**: Only `tier3_enums` gets concrete suggestions because constants are directly derivable from category definitions. Variable names (`tier1_vars`) and repetition patterns (`line_repetition_patterns`) are structural requirements — the recipe specifies *how many*, and the seed-writing LLM determines *which ones* based on the required methods and reference seeds. This avoids generating low-quality suggestions that the LLM would ignore anyway.

5. **Reference seed selection algorithm**:

   For each recipe, select 2-3 reference seeds using a tiered fallback:
   ```python
   def select_references(target_features, corpus_features, max_refs=3,
                          validated_seeds=None):
       """Select reference seeds by decreasing feature overlap.

       Args:
           validated_seeds: optional set of seed filenames known to pass validation.
               If provided, only validated seeds are eligible as references.
               A high-overlap seed that fails validation is a worse reference
               than a lower-overlap seed that works correctly.
       """
       candidates = []
       for seed, fp in corpus_features.items():
           # Skip seeds that fail validation if we have validation data
           if validated_seeds is not None and seed not in validated_seeds:
               continue
           overlap = len(set(target_features) & set(fp["features"]))
           total_methods = sum(fp["method_counts"].values())
           if overlap > 0:
               candidates.append((overlap, total_methods, seed))

       # Sort by: overlap (desc), then total method count (desc, prefer complex seeds)
       candidates.sort(key=lambda x: (-x[0], -x[1]))

       # Take top candidates, preferring diversity (no two refs with identical feature sets)
       selected = []
       seen_feature_sets = set()
       for overlap, _, seed in candidates:
           feature_key = tuple(sorted(corpus_features[seed]["features"]))
           if feature_key not in seen_feature_sets:
               selected.append(seed)
               seen_feature_sets.add(feature_key)
           if len(selected) >= max_refs:
               break

       # Fallback: if no seeds share ANY target feature, select highest-complexity seeds
       if not selected:
           all_seeds = sorted(corpus_features.items(),
                              key=lambda x: -sum(x[1].get("method_counts", {}).values()))
           selected = [s[0] for s in all_seeds[:max_refs]]

       return selected
   ```

6. **Batch planning** (sort-by-priority with deduplication):

   ```python
   def plan_batches(recipes, batch_size=5, max_batches=4, max_feature_concentration=3):
       """Group recipes into batches by priority with deduplication and feature spread.

       At max 20 recipes across max 4 batches, greedy weighted set cover
       provides negligible optimization over simple sorting. This simplified
       algorithm produces the same practical outcome: highest-priority
       recipes first, no duplicate target feature combinations.

       Feature spread: within each batch, no single feature category appears in
       more than max_feature_concentration recipes. This prevents a batch from
       being dominated by one feature (e.g., 5 FBO-heavy seeds in one batch),
       which would reduce corpus diversity. Recipes that would exceed the
       concentration limit are deferred to the next batch.
       """
       sorted_recipes = sorted(recipes, key=lambda r: -r["priority_score"])

       batches = []
       planned_combos = set()
       deferred = []

       def _start_new_batch():
           return [], {}  # recipes list, feature_counts dict

       current_batch, feature_counts = _start_new_batch()

       for recipe in sorted_recipes:
           combo = tuple(sorted(recipe["target_features"]))
           if combo in planned_combos:
               continue

           # Check feature concentration
           would_exceed = any(
               feature_counts.get(f, 0) >= max_feature_concentration
               for f in recipe["target_features"]
           )
           if would_exceed:
               deferred.append(recipe)
               continue

           planned_combos.add(combo)
           current_batch.append(recipe)
           for f in recipe["target_features"]:
               feature_counts[f] = feature_counts.get(f, 0) + 1

           if len(current_batch) >= batch_size:
               batches.append(current_batch)
               current_batch, feature_counts = _start_new_batch()
               # Re-add deferred recipes to the candidate pool
               sorted_recipes = deferred + [r for r in sorted_recipes
                                             if tuple(sorted(r["target_features"])) not in planned_combos]
               deferred = []
               if len(batches) >= max_batches:
                   break

       if current_batch and len(batches) < max_batches:
           batches.append(current_batch)
       return batches
   ```

**Optimistic coverage caveat**: The batch planner assumes each seed will exercise all its target features with meaningful interaction. In practice, a seed targeting `[A, B, C]` may achieve strong `A ↔ B` interaction but have `C` at shallow depth with no cross-feature references. The planner marks `(A,C)` and `(B,C)` as "planned" and deprioritizes them in future batches, when they may still be genuine gaps after the seed is written.

This is inherent to planning-before-writing. The post-batch full re-analysis (Step 4 in the skill workflow) is the **source of truth** — it reconciles planned coverage against actual achieved coverage. If the re-analysis reveals that sub-combos are still gaps, they re-enter the priority queue in the next planning cycle. The batch planner's optimism is acceptable because the re-analysis loop corrects it within one cycle.

7. **Weak coverage recipe generation** (Phase 3):

   The recipe generation algorithm above only targets *missing* combinations (seed_count < min_seeds). Combinations with many seeds but poor interaction quality are observed by the combination matrix (reported in `weak_coverage`) but not acted upon. The `generate_weak_coverage_recipes()` function closes this gap:

   ```python
   def generate_weak_coverage_recipes(weak_coverage_entries, corpus_features,
                                       corpus_interactions, categories_config):
       """Generate recipes for combinations with high seed count but poor quality.

       Strengthen recipes differ from gap recipes by analyzing WHAT existing seeds
       already do and specifying what's MISSING. Generic "pass resource from one
       feature to another" guidance is not actionable — the recipe must identify
       which specific interaction patterns the existing seeds use and which they
       don't, so the LLM can write a genuinely different seed.

       Args:
           weak_coverage_entries: List from combination matrix's weak_coverage output.
           corpus_features: Full corpus feature fingerprints.
           corpus_interactions: Per-seed interaction graph outputs (Phase 2).
           categories_config: Feature categories config.

       Returns:
           List of recipes with recipe_type="strengthen".
       """
       recipes = []
       for entry in weak_coverage_entries:
           combo = entry["combo"]
           seeds = entry.get("seeds", [])

           # Analyze what existing seeds already do for this combo
           existing_interactions = _collect_existing_interactions(
               combo, seeds, corpus_interactions)
           existing_path_sigs = _collect_existing_path_signatures(
               combo, seeds, corpus_features)

           # Identify what's missing vs. what's saturated
           missing_interactions = _identify_missing_interactions(
               combo, existing_interactions, categories_config)

           recipe = {
               "recipe_id": f"strengthen_{len(recipes)+1:03d}",
               "recipe_type": "strengthen",
               "priority": compute_priority_label(entry.get("priority_score", 30)),
               "priority_score": entry.get("priority_score", 30),
               "target_features": list(combo),
               "reason": f"Weak coverage: {entry['seed_count']} seeds but "
                         f"avg_interaction_score={entry.get('avg_interaction_score', 'N/A')}, "
                         f"distinct_fingerprints={entry.get('distinct_fingerprints', 'N/A')}",

               # What existing seeds already cover (so the LLM avoids duplicating)
               "existing_coverage_summary": {
                   "interaction_patterns_present": existing_interactions,
                   "path_signatures_present": list(existing_path_sigs),
                   "seed_count": len(seeds),
               },

               # What the new seed should do differently
               "interaction_requirements": missing_interactions,
               "avoid_patterns": list(existing_path_sigs),  # Don't repeat what exists
               "required_state_paths": [
                   p for p in ["use_after_delete", "bind_during_block"]
                   if p not in existing_path_sigs
               ] or ["bind_rebind"],  # Fallback if all security paths already present

               "seed_constraints": derive_constraints(combo, categories_config, {}),
               "reference_seeds": select_references(combo, corpus_features),
           }
           recipes.append(recipe)
       return recipes

   def _collect_existing_interactions(combo, seeds, corpus_interactions):
       """Collect interaction evidence strings from existing seeds for this combo."""
       interactions = []
       for seed in seeds:
           if seed in corpus_interactions:
               for interaction in corpus_interactions[seed].get("interactions", []):
                   if set(interaction["features"]) <= set(combo):
                       interactions.extend(interaction.get("evidence", []))
       return list(set(interactions))

   def _collect_existing_path_signatures(combo, seeds, corpus_features):
       """Collect path signatures from existing seeds covering this combo."""
       sigs = set()
       for seed in seeds:
           if seed in corpus_features:
               sigs.update(corpus_features[seed].get("path_signatures", []))
       return sigs

   def _identify_missing_interactions(combo, existing_interactions, categories_config):
       """Identify interaction patterns not yet present in existing seeds."""
       # Build all possible pairwise interaction descriptions from category methods
       missing = []
       for i in range(len(combo)):
           for j in range(i + 1, len(combo)):
               pair_evidence = [e for e in existing_interactions
                               if combo[i] in e or combo[j] in e]
               if not pair_evidence:
                   # No existing interaction between this pair — suggest one
                   missing.append({
                       "features": [combo[i], combo[j]],
                       "suggested_interaction": (
                           f"Create a resource in {combo[i]} and pass it to "
                           f"{combo[j]} (no existing seeds do this)"
                       ),
                       "existing_evidence": "none",
                   })
               else:
                   # Interaction exists but may be shallow — suggest deeper variant
                   missing.append({
                       "features": [combo[i], combo[j]],
                       "suggested_interaction": (
                           f"Existing seeds use: {pair_evidence[0]}. "
                           f"Write a different interaction pattern."
                       ),
                       "existing_evidence": pair_evidence[0],
                   })
       return missing
   ```

   Recipes carry a `recipe_type` field: `"gap"` for standard gap-filling recipes, `"strengthen"` for weak coverage recipes. The key improvement over simple "pass resource from one feature to another" guidance: strengthen recipes include an `existing_coverage_summary` showing what existing seeds already do, an `avoid_patterns` list to prevent duplication, and `interaction_requirements` that reference specific evidence from existing seeds. This makes the recipe actionable — the LLM knows what not to repeat.

**Output**: Ordered list of recipes with batch assignments.

---

### Skill rewrite: `expand-webgl-coverage`

The skill becomes an orchestrator for the recipe-guided pipeline:

```markdown
## Workflow (Recipe-Guided Pipeline)

### Step 1: Analysis
Run analysis appropriate to the available pipeline phase:

Phase 1 only (sufficient for full pipeline):
\`\`\`bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix_report.json \
  --gap-recipes /tmp/gap_recipes.json \
  --n-way 3
\`\`\`

Phase 2 enriched (optional, adds interaction quality + state paths):
\`\`\`bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --resource-types docs/resource_types.json \
  --state-paths docs/state_paths.json \
  --combination-matrix /tmp/matrix_report.json \
  --gap-recipes /tmp/gap_recipes.json \
  --interaction-graph \
  --sequence-analyzer \
  --n-way 3
\`\`\`

### Step 1.5: Include Weak Coverage (Phase 2 only, optional)
If `--include-weak-coverage` was passed in Step 1 AND Phase 2 data is available, the recipe output includes strengthen recipes (`recipe_type: "strengthen"`) alongside gap recipes. Strengthen recipes require interaction scores and are not generated from Phase 1 data alone.

### Step 2: Review Priorities
Read `/tmp/gap_recipes.json`. Present the top-priority batch to the user:
- What combinations are targeted
- Whether they are topology-connected
- What methods need coverage
- What topology edges suggest how features should interact
- (Phase 2) What state paths should be exercised, what interaction patterns to target
- How many seeds in this batch

Ask: "Ready to generate this batch?"

### Step 3: Generate Seeds (per recipe)
For each recipe in the batch:

1. Read the recipe from `/tmp/gap_recipes.json`
2. Read the reference seeds listed in the recipe
3. Read the design doc (three-zone architecture)
4. Write the seed following the recipe's requirements (methods, topology edges, constraints)
5. Validate: `./run_tests.sh --test-file <file> --browsers firefox`
6. If errors: read JSON, fix, re-validate (max 3 retries)
7. Strip console.log, final validation
8. Delta audit to verify gap closure
9. (Phase 2 only) **Interaction quality check**: Run `interaction_graph` on the new seed. If any pair from `interaction_requirements` has score 0, flag as advisory "weak interaction." Max 1 revision attempt per seed.

### Step 4: Batch Verification
After all seeds in the batch are complete:
- Run full analysis again (Step 1)
- Compare before/after metrics
- Report: combinations closed, distinct fingerprints added
- (Phase 2) Report interaction scores, state paths added

### Step 5: Iterate
If gaps remain, return to Step 2 with the next batch.
```

**Key changes from current skill**:
- Analysis is feature-combination-based, not just method coverage
- Topology graph prunes semantically orthogonal combinations before recipe generation
- Gap selection is recipe-driven, not manual reading of audit reports
- Validation loop is explicitly structured with retry limits
- Batch-level verification replaces per-seed final audit
- Recipe provides structured context for seed writing (methods, topology edges, constraints)
- Phase 2 enrichment is additive — the pipeline works end-to-end with Phase 1 alone
- **Not automated code generation**: Claude still writes each seed in a human-supervised conversation. The automation covers analysis → prioritization → recipe creation → validation. The skill orchestrates this loop, not a script.

---

## CLI Interface Design

The audit CLI gains new flags. All are additive to existing functionality:

```
Usage: python -m api_audit [existing flags] [new flags]

Phase 1 flags:
  --feature-categories FILE      Path to feature_categories.json config
  --interaction-topology FILE    Path to interaction_topology.json config
  --combination-matrix FILE      Output combination matrix report to FILE
  --gap-recipes FILE             Output gap recipe specs to FILE
  --n-way N                      Compute N-way combinations (default: 2, max: 4)
  --min-seeds N                  Minimum seeds per combination (default: 1)
  --max-recipes N                Maximum recipes to generate (default: 20)
  --baseline FILE                Baseline matrix to merge incrementally (see Incremental Analysis)

Phase 2 flags (optional enrichment):
  --resource-types FILE          Path to resource_types.json config
  --state-paths FILE             Path to state_paths.json config
  --interaction-graph            Include interaction analysis
  --sequence-analyzer            Include sequence pattern analysis
  --include-weak-coverage        Include strengthen recipes for weak coverage combos (requires Phase 2)
```

**Phase 1 usage** (complete pipeline, no Phase 2):
```bash
# Analysis + recipe generation (fully functional without Phase 2)
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix.json \
  --gap-recipes /tmp/recipes.json \
  --n-way 3 \
  --max-recipes 10
```

**Phase 2 enriched** (adds interaction quality + state paths):
```bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --resource-types docs/resource_types.json \
  --state-paths docs/state_paths.json \
  --combination-matrix /tmp/matrix.json \
  --gap-recipes /tmp/recipes.json \
  --interaction-graph \
  --sequence-analyzer \
  --n-way 3 \
  --max-recipes 10
```

---

## Incremental Analysis

During the recipe-guided workflow (write seed → validate → delta audit → write next seed), re-running full corpus analysis after every seed is wasteful. The pipeline supports incremental updates:

**Per-file caching** (existing mechanism, extended):
- The existing `cache.py` caches per-file parse results keyed by content hash. New analysis passes (feature_detection, resource_tracking, interaction_graph, sequence_analyzer) store their per-file results in the same cache. Unchanged files are not re-analyzed.

**Combination matrix incremental merge**:
- The `--baseline` flag loads a previously-computed matrix report and merges a new seed's fingerprint into it without recomputing from scratch:

```python
def merge_seed_into_matrix(baseline_matrix, new_seed_fingerprint,
                           new_seed_interaction=None, new_seed_sequences=None):
    """Incrementally update a combination matrix with one new seed.

    For each N-way combination present in the new seed's feature set,
    increment the seed count and update depth/interaction metadata.
    This is O(C(k, n)) where k = features in new seed, n = n-way level.
    For a typical seed with 5 features and n=3, this is C(5,3) = 10 updates.

    Quality metrics are preserved from the baseline with a stale flag rather
    than nulled out. Stale metrics are better than no metrics for relative
    ranking within a batch — nulling would reduce within-batch recipe ordering
    to Phase 1 data (seed_count + depth only), wasting Phase 2 analysis costs.
    """
    features = new_seed_fingerprint["features"]
    for n in range(2, min(len(features), baseline_matrix["n_way"]) + 1):
        for combo in combinations(sorted(features), n):
            key = tuple(combo)
            if key in baseline_matrix["combinations"]:
                entry = baseline_matrix["combinations"][key]
                entry["seed_count"] += 1
                entry["seeds"].append(new_seed_fingerprint["file"])

                # Update distinct_fingerprints incrementally: compute the
                # new seed's method-set fingerprint for this combo and check
                # if it's already in the fingerprint set.
                fp_key = tuple(
                    tuple(sorted(new_seed_fingerprint.get("methods_per_feature", {}).get(c, [])))
                    for c in key
                )
                existing_fps = entry.setdefault("_fingerprint_set", set())
                existing_fps.add(fp_key)
                entry["distinct_fingerprints"] = len(existing_fps)

                # Mark quality metrics as stale rather than nulling them.
                # The old values are still useful for relative ranking —
                # they reflect the corpus before this seed was added.
                # Full re-analysis (batch Step 4) replaces stale values
                # with authoritative ones.
                entry["stale"] = True
            else:
                baseline_matrix["combinations"][key] = {
                    "seed_count": 1,
                    "seeds": [new_seed_fingerprint["file"]],
                    "avg_interaction_score": None,
                    "state_paths_covered": None,
                    "stale": True,
                }
    return baseline_matrix
```

**Workflow integration**: During batch seed generation (Step 3 in the skill), the delta audit uses `--baseline` to update the matrix incrementally after each seed. The full re-analysis (Step 4) runs only once per batch completion to produce authoritative numbers.

```bash
# After writing a single new seed (fast, incremental):
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --file agent_outputs/new_seed.html \
  --feature-categories docs/feature_categories.json \
  --baseline /tmp/matrix_report.json \
  --combination-matrix /tmp/matrix_report.json

# After completing a full batch (authoritative, full recompute):
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --combination-matrix /tmp/matrix_report.json \
  --n-way 3
```

**Performance note**: No hard performance budget. Correctness and completeness take priority over speed. Incremental single-seed updates (via `--baseline`) should be fast relative to full corpus analysis since they process one file and merge into existing data.

---

## Testing Strategy

**Test infrastructure**: All tests use `pytest` and live in `scripts/api_audit/tests/`. Tests requiring real corpus seeds on disk use a shared fixture that provides paths to 5-10 curated test seeds (stored in the test directory or referenced from the real corpus). The benchmark test uses `pytest-benchmark` or manual `time.time()` instrumentation — no hard assertions on timing, only recording for regression tracking.

```
scripts/api_audit/tests/
├── conftest.py                     ← Shared fixtures (test seeds, category config, mock corpus)
├── test_feature_detection.py       ← Phase 1 unit tests
├── test_combination_matrix.py      ← Phase 1 unit tests
├── test_config_validation.py       ← Config schema + cross-reference validation
├── test_phase1_integration.py      ← Integration + migration validation
├── test_edge_cases.py              ← Adversarial inputs
├── test_benchmark.py               ← Performance regression tracking
├── test_resource_tracking.py       ← Phase 2 unit tests
├── test_interaction_graph.py       ← Phase 2 unit tests
├── test_sequence_analyzer.py       ← Phase 2 unit tests
├── test_gap_spec.py                ← Phase 3 unit tests
├── test_e2e_pipeline.py            ← End-to-end pipeline test
└── fixtures/                       ← Test seed HTML files + expected outputs
    ├── seed_buffer_only.html
    ├── seed_fbo_texture.html
    ├── seed_transform_feedback.html
    └── ...
```

Each phase includes tests that validate the new modules:

### Phase 1 Tests

**Unit tests** (`test_feature_detection.py`):
- Seed with only buffer operations → `["buffer_ops"]` at depth `"present"`
- Seed with FBO + textures → `["fbo", "texture_ops"]` (not just one)
- Seed with 4/9 buffer methods → depth `"meaningful"` (ratio 0.44), seed with 1/9 → depth `"present"` (ratio 0.11), seed with 7/9 → depth `"deep"` (ratio 0.78)
- Seed with 1/1 mrt methods → depth `"deep"` (ratio 1.0) — small categories normalize correctly
- Seed with integer texture constants but no integer methods → `["integer_textures"]`
- Seed with extension loaded → matches extension category
- GLSL builtins detected via glsl_builtins input (not call_analysis)
- Config changes propagate correctly (add/remove category)
- `is_category_match` gate composition: category with `requires_any_constant=true` rejects seed missing required constant even if methods match
- `is_category_match` gate composition: category with `requires_any_extension=true` rejects seed without extension even if methods match
- Constant name resolution: `gl.TEXTURE_2D_ARRAY` resolved by const_propagation → strips `gl.` prefix → matches `TEXTURE_2D_ARRAY` in category constants

**Unit tests** (`test_combination_matrix.py`):
- 3 seeds covering A, B, AB → 2-way matrix shows AB covered
- Gap identification with min_seeds threshold
- Lexicographic priority key produces correct dimension ordering
- Topology connectivity: connected combo ranks above disconnected combo (dimension 2)
- Seed count buckets: zero-seed > thin > covered (dimension 3)
- Security relevance: more security features = higher rank within same seed bucket (dimension 4)
- n-way preference: 2-way > 3-way within same security count (dimension 5)
- False positive annotation: combination matrix reports adjusted covered count excluding pairs where both features are UBIQUITOUS
- Topology-disconnected combos marked with `topology_connected: false` in output

**Config validation tests** (`test_config_validation.py`):
- `feature_categories.json` schema: every category has `methods` (list of strings), `constants` (list of strings), `min_methods_for_match` (int ≥ 0)
- All method names in `feature_categories.json` exist in `webgl_api_surface.json` methods or extension methods (catch typos)
- All constant names in `feature_categories.json` exist in `webgl_api_surface.json` constants (catch typos)
- `interaction_topology.json` schema: every edge `pair` references categories that exist in `feature_categories.json`
- `interaction_topology.json` coverage: warn about categories with zero topology edges (potentially missing connections)
- `interaction_topology.json` symmetry: edges are unordered pairs, no duplicates
- `resource_types.json` schema (Phase 2): `resource_type_map` values reference categories that exist in `feature_categories.json`
- `resource_types.json` (Phase 2): `create_method_map` values reference types that exist in `resource_type_map`
- `state_paths.json` schema (Phase 2): `binding_points` values reference categories that exist in `feature_categories.json`
- `state_paths.json` (Phase 2): `path_catalog` entries have required fields (`description`, `security_relevance`, `pattern`)
- **Completeness check**: Every method in `webgl_api_surface.json` appears in at least one category's `methods` list in `feature_categories.json`. Uncategorized methods produce a warning (not a failure — some methods may intentionally be uncategorized, but omissions should be visible). This catches the case where a new method is added to the API surface but nobody remembers to categorize it.
- **Semantic drift mitigation**: Config validation catches structural inconsistencies (missing references, invalid schemas) but NOT semantic drift (a method assigned to the wrong category, a topology edge missing between features that should interact). To mitigate semantic drift: (1) the completeness check surfaces uncategorized methods, (2) the topology coverage warning surfaces disconnected categories, and (3) the migration validation test (integration test) compares new-system output against hand-verified ground truth for 10 seeds. These three mechanisms together make semantic errors visible, even if they can't prevent them automatically.

**Integration test** (`test_phase1_integration.py`):
- Run full pipeline on 5-10 real corpus seeds with known feature profiles
- Verify feature detection matches expected categories
- Verify combination matrix output is consistent
- **Migration validation**: For 10 known seeds, manually determine their features (ground truth). Run both `feature_matrix.sh` (grep-based) and `combination_matrix.py` (AST-based) on these seeds. Both should agree on feature presence for these seeds. Where they disagree, verify the new system is more precise (e.g., grep might false-positive on a method name in a comment). Document discrepancies.

**Benchmark test** (`test_benchmark.py`):
- Run full Phase 1 pipeline (feature detection + combination matrix) on entire corpus (367 files)
- Record wall clock timing (no hard assertion — correctness over speed)
- Run incremental merge (single seed into existing matrix) and record timing
- Store timing results for regression tracking across Phase 2 additions

**Edge case tests** (`test_edge_cases.py`):
- Seed with zero GL calls (empty script body) → produces empty feature fingerprint, no crash
- Seed with `gl[dynamicMethod]()` computed property access → method not detected (known limitation, no crash)
- Seed with `eval("gl.createBuffer()")` → method not detected (known limitation, no crash)
- Seed with multiple `<canvas>` elements and multiple GL contexts → only methods on detected context variables are tracked
- Seed with no `getContext` call (broken seed) → `context.py` returns `api_version: "unknown"`, pipeline still produces output
- Extremely large seed (1000+ GL calls) → pipeline completes without excessive memory or time
- Seed with only comments containing GL method names → methods not detected (AST-based, not grep-based)
- Seed with destructuring `const { createBuffer } = gl` → method not tracked via lint.py warning, no false positive in feature detection

### Phase 2 Tests

**Unit tests** (`test_resource_tracking.py`):
- `const buf = gl.createBuffer()` → resource map contains `buf` as type `"buffer"`
- `gl.createBuffer()` without assignment → not tracked (no variable to map)
- Array storage `bufs[0] = gl.createBuffer()` → not tracked (explicit limitation)
- Resource used in `gl.bindBuffer(target, buf)` → usage site recorded
- Miss rate: seed with 3 simple creates → miss_rate = 0.0
- Miss rate: seed with 2 simple + 1 array create → miss_rate = 0.33, untracked_reasons contains "array_storage"
- Miss rate: seed with helper `createProgram()` wrapping `gl.createProgram()` → miss_rate includes helper miss
- Miss rate: seed with 0 create calls → total_create_calls = 0, miss_rate = 0.0 (not NaN)
- Separated assignment: `let buf; buf = gl.createBuffer()` → resource map contains `buf` as type `"buffer"`
- Array push: `resources.push(gl.createBuffer())` → resource map contains `resources` as collection type `"buffer"`
- Scope-shadowed variables: `const buf` in two different try-catch blocks → resource map contains `buf#1` and `buf#2` as distinct resources

**Unit tests** (`test_interaction_graph.py`):
- Seed with FBO using texture → interaction detected via resource map
- Seed with buffer and texture that don't interact → isolated
- Shared binding point detection: `bindBufferBase(TRANSFORM_FEEDBACK_BUFFER, ...)` → transform_feedback ↔ buffer_ops interaction
- Interaction scoring produces expected values

**Unit tests** (`test_sequence_analyzer.py`):
- Known bind-rebind sequence detected
- Use-after-delete lifecycle detected (resource map resolves variable across blocks)
- Enable-thrash pattern detected
- Catalog path matching
- Linear walk through try-catch produces correct sequence (no branching)
- Feedback loop detection: deferred (not implemented — see design rationale in state_paths.json catalog)
- Scope-shadowed variables: `const buf` in try-block 3 (created, deleted) and `const buf` in try-block 5 (created, bound) → NO `use_after_delete` detected (disambiguated as `buf#1` and `buf#2`)

### Phase 3 Tests

**Unit tests** (`test_gap_spec.py`):
- Relevance filter: `[shader_pipeline, draw_calls, attributes]` (all ubiquitous) → excluded
- Relevance filter: `[ext_float_textures, ext_compressed_textures, ext_disjoint_timer_query]` (all extension) → excluded
- Relevance filter: `[fbo, ext_float_textures, ext_compressed_textures]` (2 extension categories, but `fbo` is security-relevant) → included
- Relevance filter: `[vao, ext_float_textures, ext_compressed_textures]` (2 extension categories, no security-relevant feature) → excluded
- Relevance filter: `[fbo, buffer_ops, texture_ops]` (has security-relevant) → included
- Relevance filter: `[sampler, query]` (2-way, any content) → included
- Relevance filter: `[vao, instancing, sampler]` (non-ubiquitous core) → included
- Uncovered combination produces recipe with correct methods
- Priority scoring accounts for security relevance
- Batch planning: sorted recipes produce non-redundant batches (deduplication removes duplicate target combos)
- Batch planning: max_batches limit respected
- Batch planning feature spread: 5 recipes all containing `fbo` → max 3 in batch 1, remaining deferred to batch 2
- Batch planning deferred recipes: deferred recipes appear in subsequent batches (not dropped)
- Reference seed selection: tiered fallback works (overlap → complexity → fallback)
- Reference seed selection: 0-overlap gap still produces references (fallback path)
- Weak coverage recipe generation: combo with 12 seeds but avg_interaction_score=0.3 → generates strengthen recipe
- Weak coverage recipe generation: strengthen recipe has `recipe_type: "strengthen"` and includes `existing_coverage_summary` + `avoid_patterns`
- Weak coverage recipe generation: strengthen recipe's `interaction_requirements` reference specific evidence from existing seeds (not generic "pass resource" text)
- False positive annotation: seed matching `pixel_ops` only via `pixelStorei` → combination matrix entry annotated `"low_confidence_match": true`

**End-to-end test** (`test_e2e_pipeline.py`):
- Run full analysis on real corpus → generate recipes → verify recipes are valid JSON with all required fields
- Verify top-priority recipe targets a known gap from the corpus
- Verify reference seeds in recipes actually exist on disk

**Pilot test quality criteria** (for Phase 3, Step 5 pilot):
- Each recipe-generated seed should achieve `interaction_score > 0` for at least one pair of its target features (validates that features interact, not just co-exist)
- At least 50% of recipe-generated seeds should achieve `interaction_density > 0.3` (validates that interactions are non-trivial — multiple shared resources or binding points, not a single incidental connection)
- Compare interaction scores of recipe-guided seeds vs. manually-written seeds covering similar features. Recipe-guided seeds should achieve comparable or higher interaction scores, validating that the recipe's `interaction_requirements` field produces meaningful guidance

---

## File Inventory

### New files (Phase 1)
- `scripts/api_audit/feature_detection.py` - Feature categorization module (with depth levels + matching algorithm)
- `scripts/api_audit/combination_matrix.py` - N-way combination analysis (with incremental merge + topology filtering)
- `docs/feature_categories.json` - Configurable feature category definitions (categories + matching rules only)
- `docs/interaction_topology.json` - Static feature interaction graph (~55 edges, which categories CAN interact)
- `scripts/api_audit/tests/conftest.py` - Shared test fixtures (test seeds, mock configs, corpus data)
- `scripts/api_audit/tests/test_feature_detection.py`
- `scripts/api_audit/tests/test_combination_matrix.py`
- `scripts/api_audit/tests/test_phase1_integration.py` - Integration + migration validation
- `scripts/api_audit/tests/test_config_validation.py` - Config schema validation + completeness check + topology validation
- `scripts/api_audit/tests/test_edge_cases.py` - Adversarial and edge case inputs

### New files (Phase 2)
- `docs/resource_types.json` - Resource type → feature category mapping + create method mapping
- `docs/state_paths.json` - State path catalog + binding point definitions
- `scripts/api_audit/resource_tracking.py` - WebGL resource variable tracking (create* return values)
- `scripts/api_audit/interaction_graph.py` - Cross-feature interaction detection (resource refs + binding points)
- `scripts/api_audit/sequence_analyzer.py` - Call sequence extraction + pattern catalog matching (feedback loop deferred)
- `scripts/api_audit/tests/test_resource_tracking.py`
- `scripts/api_audit/tests/test_interaction_graph.py`
- `scripts/api_audit/tests/test_sequence_analyzer.py`

### New files (Phase 3)
- `scripts/api_audit/gap_spec.py` - Recipe generation from gap analysis (with constraint derivation algorithm)
- `scripts/api_audit/tests/test_gap_spec.py`
- `scripts/api_audit/tests/test_e2e_pipeline.py` - End-to-end pipeline test
- `scripts/api_audit/tests/test_benchmark.py` - Performance regression test

### Modified files
- `scripts/api_audit/__main__.py` - New CLI flags for combination matrix, recipes, etc.
- `.claude/skills/expand-webgl-coverage/SKILL.md` - Rewritten for recipe-guided pipeline

### Deprecated
- `scripts/feature_matrix.sh` - Replaced by `combination_matrix.py` (keep for reference, add deprecation header comment)
- **Migration plan**: After Phase 1 integration test validates parity with `feature_matrix.sh`, add a deprecation notice to the script header and update CLAUDE.md to reference the new tool. Do not delete until Phase 1 has been used in at least one full coverage expansion cycle.

---

## Implementation Order

### Phase 1: Foundation
1. Create `docs/feature_categories.json` with initial category definitions (core + extension categories)
2. Create `docs/interaction_topology.json` with feature interaction graph (~55 edges)
3. Implement config schema validation tests (`test_config_validation.py`) — validate all method/constant names against API surface, validate topology edge endpoints reference valid categories, warn about categories with zero topology edges
4. Implement `feature_detection.py` with `is_category_match()` algorithm, ratio-based depth levels, + unit tests
5. Implement `combination_matrix.py` with lexicographic priority ordering + topology connectivity filtering + incremental merge + unit tests
6. Add `--feature-categories`, `--interaction-topology`, `--combination-matrix`, `--n-way`, `--baseline` flags to CLI
7. Run against full corpus, validate output against known coverage metrics
8. **Benchmark**: Run full pipeline on entire corpus, record timing baseline
9. **Migration validation**: Run integration test comparing `feature_matrix.sh` output against `combination_matrix.py` output on 10 ground-truth seeds. Document discrepancies, resolve any where the new system is wrong.

### Recipe Validation Experiment (gate before Phase 3 implementation)

Before building the Phase 3 recipe pipeline, validate the core hypothesis: **does structured recipe context produce meaningfully better seeds than ad-hoc instructions?**

1. After Phase 1 step 7, manually create 3-5 recipe-like JSON specs by hand (not programmatically). Each should target a known gap from the Phase 1 matrix output.
2. For each recipe, write a seed in two ways:
   - **Recipe-guided**: Present the recipe JSON to Claude as context alongside the design doc and reference seeds. Let Claude write the seed from the recipe.
   - **Ad-hoc**: Present only the gap description ("write a seed combining transform_feedback, sampler, and integer_textures") and the design doc. Let Claude write the seed without the recipe.
3. Validate both seeds. Compare:
   - Do recipe-guided seeds use more of the `required_methods`?
   - Do recipe-guided seeds have higher distinct fingerprints (more diverse method combinations)?
   - Subjectively: are recipe-guided seeds better structured for mutation?
4. **Decision gate**: If recipe-guided seeds are measurably better on at least 2 of 3 criteria, proceed with Phase 3. If they're roughly equivalent, the recipe pipeline is overhead — consider simplifying Phase 3 to a gap report + manual targeting workflow (skip `gap_spec.py`, keep the combination matrix).

**Cost**: ~2 hours of manual work. **Risk mitigated**: Building an elaborate recipe generation pipeline that doesn't improve seed quality.

### Phase 2: Depth (optional — implement only after Phase 1 has been used in ≥1 coverage expansion cycle)

**Prerequisite**: Phase 1 must have been used for at least one full coverage expansion cycle (Steps 1-5 of the skill workflow). This provides empirical evidence of whether Phase 1 alone is sufficient or whether interaction quality data would materially change targeting decisions.

1. Create `docs/resource_types.json` and `docs/state_paths.json` config files. Add schema validation tests.
2. **Miss rate pattern survey** (prerequisite before committing to full Phase 2): Run a lightweight AST scan over the full corpus counting all `gl.create*()` / `gl.fenceSync()` calls and classifying each by its context:
   - Simple `variable_declarator` assignment (trackable now)
   - Separated `assignment_expression` (trackable with pattern 2a)
   - Array `.push()` (trackable with pattern 2b, approximate)
   - Array subscript assignment `arr[i] = gl.create*()` (untrackable)
   - Helper function return (untrackable)
   - Bare call without assignment (untrackable)
   - Object property assignment `obj.prop = gl.create*()` (untrackable)

   **Purpose**: Determine whether the three proposed miss-rate reduction patterns will actually reduce the miss rate to <20%. If helper functions and array indexing dominate the 40%, the three patterns won't help. This survey is cheap (one AST pass, no full pipeline) and answers a critical question before investing in the full Phase 2 implementation.

   **Decision gate**: If the survey shows that the three proposed patterns cover >50% of currently-untracked creates (i.e., the projected miss rate after implementing them is <20%), proceed with Phase 2. If not, reassess whether Phase 2's interaction graph and sequence analyzer provide enough value with the higher miss rate, or whether additional tracking patterns are needed first.
3. **Implement `resource_tracking.py` with miss rate instrumentation + tests** (this is the foundation - must come first). Include the three miss rate reduction patterns as explicit sub-tasks:
   - 3a. Separated assignment tracking (`let buf; ... buf = gl.createBuffer()`)
   - 3b. Array push tracking (`resources.push(gl.createBuffer())`)
   - 3c. Scope-shadowed variable disambiguation (`buf#1`, `buf#2` — for `const`/`let` only, see design note below)
4. **Run resource tracking on full corpus, review miss rate report.** Document the corpus_avg_miss_rate and the distribution of per-seed miss rates. **Target: corpus_avg_miss_rate < 0.20.** Compare against the step 2 survey projections. This is a noted evaluation checkpoint, not a blocking gate — proceed to step 5 regardless. The miss rate is propagated as confidence metadata into downstream modules (interaction graph marks low-confidence seeds, combination matrix flags unreliable depth data). If the target isn't met, document which patterns remain untracked for potential future improvement, but do not block Phase 2 progress — the conservative undercounting is the designed behavior.
5. Implement `interaction_graph.py` (consumes resource map, uses binding_points from state_paths.json, propagates miss rate confidence) + tests
6. Implement `sequence_analyzer.py` with path catalog (from state_paths.json), excluding feedback loop detection (deferred — see design rationale in state_paths.json catalog) + tests
7. Integrate interaction scores, sequence patterns, and depth confidence into combination matrix via `enrich_matrix()` + tests
8. Add `--resource-types`, `--state-paths`, `--interaction-graph` and `--sequence-analyzer` flags to CLI
9. **Benchmark**: Re-run full pipeline with Phase 2 passes, record timing for regression tracking
10. Run against full corpus, identify new insights not visible in Phase 1. Compare gap rankings with and without Phase 2 enrichment — document cases where Phase 2 data materially changed a gap's priority.

### Phase 3: Generation (proceed only after recipe validation experiment passes)
1. Implement `gap_spec.py` with reference seed selection + batch planning algorithms + tests. **Must work with Phase 1 data alone** — Phase 2 enrichment fields are optional in recipe output.
2. Implement `generate_weak_coverage_recipes()` in `gap_spec.py` + tests (requires Phase 2 data — skip if Phase 2 not implemented)
3. Add `--gap-recipes`, `--max-recipes`, and `--include-weak-coverage` flags to CLI
4. Rewrite `expand-webgl-coverage` skill for recipe-guided pipeline
5. End-to-end test: run analysis → generate recipes → verify recipe validity
6. Pilot: use recipes to write 1 batch of seeds, compare quality against manually-written seeds and against the recipe validation experiment results

---

## Resolved Design Decisions

1. **Category overlap handling**: Yes, overlapping categories count separately. The disambiguation mechanism uses AND-composed gates (`requires_any_constant`, `requires_any_extension`, `min_constants_for_match`). The canonical matching algorithm is `is_category_match()` — see feature_detection.py section. New overlap cases should add the appropriate gate flag rather than ad-hoc workarounds.

2. **Category matching algorithm**: Fully specified in the `is_category_match()` function. Gates compose with AND logic. Constant matching uses resolved names (strip `gl.` prefix from const_propagation output). See feature_detection.py section for complete specification and disambiguation examples.

3. **Depth levels**: Three levels, **ratio-based** — `"present"` (ratio < 0.33), `"meaningful"` (0.33 ≤ ratio < 0.66), `"deep"` (ratio ≥ 0.66), where ratio = `methods_used / methods_available` (category's `methods` list size is the denominator). This normalizes depth across categories of different sizes: small categories like `mrt` (1 method) reach "deep" from any usage, while large categories like `uniforms` (40+ methods) require substantial API breadth. Depth is a breadth heuristic, not a quality metric. Phase 2's interaction graph and sequence analyzer provide the quality signal. Priority scoring uses weighted average: present=0.0, meaningful=0.5, deep=1.0.

4. **Sequence analyzer scope (renamed from "state machine")**: Named `sequence_analyzer.py` rather than `state_machine.py` because it extracts call sequences and pattern-matches against a catalog without simulating actual GL state. Linear walk through entire seed, assuming all try blocks succeed. No per-block branching. Rationale: we're analyzing mutation potential, not runtime behavior. A true state machine would model what's bound to each target and which capabilities are enabled — that level of simulation is out of scope. See sequence_analyzer.py assumptions section.

5. **Recipe reference seeds**: 2-3 per recipe, selected by tiered fallback (feature overlap → total method count → fallback to highest-complexity seeds). Algorithm specified in gap_spec.py section.

6. **Recipe constraint derivation**: `tier3_enums` suggestions are derived mechanically from category constant lists. `tier1_vars` and `line_repetition_patterns` specify counts only — the seed-writing LLM infers concrete names from required methods and reference seeds. See `derive_constraints()` algorithm in gap_spec.py section.

7. **Validation retry strategy**: Pause and report after 3 retries. Persistent failures likely indicate unsupported features or deeper issues requiring human judgment.

8. **`detect_features` API**: Accepts both `call_analysis_result` AND `glsl_builtins` output, plus optional `extensions` and `extension_methods` for extension-based categories.

9. **Try-catch handling in state analysis**: All try blocks assumed to execute successfully. Linear sequence. See explicit assumption in sequence_analyzer.py section.

10. **N-way relevance filtering**: Recipe generation applies an `is_relevant_gap()` filter before priority scoring. Excluded: all-ubiquitous combos, all-extension combos, combos with 2+ extension categories **unless a security-relevant feature is present**. Included: anything with a security-relevant feature or a non-ubiquitous core feature, plus all 2-way gaps unconditionally. Example: `[fbo, ext_float_textures, ext_color_buffer_float]` passes despite 2 extension categories because `fbo` is security-relevant. See gap_spec.py recipe generation algorithm step 1.

11. **Feedback loop detection scope**: **Deferred**. Feedback loops are a specific driver bug class better addressed by intentionally constructing 2-3 dedicated seeds rather than corpus-wide heuristic detection. The detection algorithm (name-based matching with FBO-switch suppression) required disproportionate implementation complexity relative to its utility. If feedback loop coverage is desired, write dedicated seeds. See `state_paths.json` catalog entry for rationale.

12. **Resource tracking miss rate instrumentation**: `resource_tracking.py` reports a `MissReport` per seed quantifying how many `gl.create*()` calls were not captured (due to array storage, helper functions, bare calls, etc.). Corpus-level aggregation surfaces seeds and feature combinations with unreliable depth data. The miss rate threshold is an **evaluation step, not a blocking gate** — Phase 2 proceeds regardless.

13. **Shared state detection scope**: Interaction graph detects shared **binding points** (via static mapping in `state_paths.json`), NOT texture unit state. Texture unit tracking would require runtime state simulation (tracking `activeTexture` state), which is explicitly out of scope. Texture-sampler interactions are detected via resource-based cross-feature references instead.

14. **Config file organization**: Phase 1 configuration uses two files: `feature_categories.json` (category definitions + matching rules) and `interaction_topology.json` (static feature interaction graph). Phase 2 adds two more: `resource_types.json` (resource type → feature category mapping) and `state_paths.json` (binding points + state path catalog). Splitting by concern prevents a single god config from coupling unrelated modules. **Semantic drift risk**: Config validation catches structural inconsistencies but not semantic errors (wrong categorization, missing topology edges). Three mitigation mechanisms: completeness checks surface uncategorized methods, topology coverage warnings surface disconnected categories, and migration validation tests compare against hand-verified ground truth. See test_config_validation.py section.

15. **Batch planning**: Sort-by-priority with deduplication and **feature spread**. Within each batch, no single feature category appears in more than `max_feature_concentration` recipes (default: 3). This prevents batches from being dominated by one feature (e.g., 5 FBO-heavy seeds), which reduces corpus diversity. Recipes exceeding the concentration limit are deferred to the next batch. Duplicate target feature combinations are skipped.

16. **Incremental analysis**: Single-seed updates merge into a baseline combination matrix via `merge_seed_into_matrix()`. Merge marks touched combos as `stale: true` rather than nulling out quality metrics. Stale metrics are better than no metrics for within-batch recipe ranking — nulling would reduce subsequent recipes to Phase 1 data (seed_count + depth only), wasting Phase 2 analysis costs. `gap_spec.py` uses stale metrics for relative ranking but annotates them as `"stale": true` in recipe output. Full re-analysis runs once per batch completion to replace stale values with authoritative ones. Per-file caching (existing mechanism) is extended to new analysis passes.

17. **Performance**: No hard performance budget. Correctness and completeness take priority. Benchmark tests record timing for regression tracking but do not assert hard limits. Incremental single-seed updates should be fast relative to full corpus analysis. The batch planner simplification (sort vs. greedy set cover) is one example of preferring simplicity over negligible optimization.

18. **Miss rate guard on interaction discount**: Phase 2 enriched priority key only uses interaction scores as a tiebreaker dimension when miss_rates indicate reliable tracking (>50% of covering seeds have miss_rate < 0.5). Seeds with high miss rates get a neutral interaction_deficit value (0.5) rather than their possibly-misleading actual scores. This prevents unreliable data from overriding the base ordering.

19. **Batch planner optimistic assumptions**: The batch planner assumes each seed will exercise all target features with meaningful interaction. Post-batch full re-analysis (Step 4) is the source of truth. Sub-combos that remain gaps after a batch re-enter the priority queue in the next planning cycle.

20. **Near-ubiquitous categories**: `pixel_ops` and `viewport_scissor` are treated as ubiquitous in priority scoring and relevance filtering. `pixelStorei` appears in most texture-uploading seeds; `viewport` appears in nearly every seed. Without this classification, their combinations dominate the gap report with low-value noise.

21. **Config maintenance burden**: Three JSON configs (`feature_categories.json`, `resource_types.json`, `state_paths.json`) must stay synchronized with the WebGL API surface and with each other. Adding a new WebGL method requires updating `feature_categories.json` (category membership) and potentially `resource_types.json` (if it's a `create*` method) and `webgl_api_surface.json` (API surface). The config validation tests (`test_config_validation.py`) are the primary mitigation — they cross-reference all method/constant names against the API surface and verify inter-config consistency (e.g., `resource_types.json` references categories that exist in `feature_categories.json`). Additionally, `resource_types.json` could potentially be derived from `feature_categories.json` + `webgl_api_surface.json` in a future improvement (the `create_method_map` is a simple pattern match, and `resource_type_map` is a direct inversion), but explicit config is preferred for now for clarity and auditability.

22. **Feature detection false positives**: Acknowledged as a real concern — `min_methods_for_match: 1` causes boilerplate calls like `pixelStorei` and `viewport` to create spurious category matches. Mitigated by two mechanisms: (1) the UBIQUITOUS set in priority scoring deprioritizes combos involving near-ubiquitous categories, and (2) the optional `false_positive_prone` flag on category definitions lets the combination matrix annotate low-confidence matches. Not fully solved — context-dependent disambiguation (analyzing constant arguments to determine if a method call genuinely exercises the category) is deferred to future work.

23. **Scope-shadowed variables**: Resource tracking disambiguates same-name `const`/`let` variables in different try-catch blocks via a monotonic suffix (`buf#1`, `buf#2`). This prevents phantom sequence patterns (false `use_after_delete`) from cross-scope name collisions. **`var` declarations are NOT disambiguated** because `var` is function-scoped in JavaScript — a `var buf` in try-block 3 and `var buf` in try-block 5 are the same variable, so cross-block lifecycle patterns (create in block 3, use in block 5) are genuine, not phantom. `let`/`var` reassignment within the same scope is handled by overwriting in the resource map (existing behavior). See resource_tracking.py miss rate reduction patterns and sequence_analyzer.py scope-shadowed variable handling sections.

24. **Weak coverage recipes**: Phase 3 generates both gap-filling recipes (`recipe_type: "gap"`, targeting missing combinations) and strengthening recipes (`recipe_type: "strengthen"`, targeting combinations with many seeds but poor interaction quality or low fingerprint diversity). Strengthen recipes include an `existing_coverage_summary` (what existing seeds already do), `avoid_patterns` (what not to repeat), and specific `interaction_requirements` that reference evidence from existing seeds. This makes recipes actionable — the LLM knows what existing seeds cover and what to do differently. Enabled via `--include-weak-coverage` CLI flag.

25. **Priority scoring**: Uses **lexicographic ordering** instead of an additive formula. Gaps are sorted by a tuple: (ubiquitous_penalty, topology_connected, seed_count_bucket, security_count, n_way_preference, depth_deficit). Each dimension is independently meaningful; no tuning constants, no calibration needed, no accidental crossover points. Phase 2 enrichment appends tiebreaker dimensions (missing_security_paths_count, interaction_deficit) that never override the base ordering. Replaces the previous 7-constant additive formula which combined ordinal, boolean, and continuous signals into a single number with unpredictable crossover behavior.

26. **Interaction graph scope**: The interaction graph detects resource-level and binding-point-level interactions only. It cannot detect state-based interactions (enable/disable affecting draw behavior), shader-mediated interactions (shader reads texture written via FBO), or ordering-dependent interactions (the mutation targets). The interaction score is a lower bound — score=0 means "no confirmed interaction via resource tracking," not "features don't interact." Scores are most useful for detecting absence of detectable interaction, not for ranking quality between non-zero scores.

27. **Distinct fingerprints**: Phase 1 fingerprints use method-set combinations per feature. Phase 2's `enrich_matrix()` upgrades fingerprints to include path signatures for behavioral diversity — two seeds using identical methods but with different patterns (one UAF, one normal lifecycle) produce distinct fingerprints. Without Phase 2, diversity is method-breadth only. Incremental merge (`merge_seed_into_matrix`) tracks fingerprint sets to keep `distinct_fingerprints` accurate during incremental updates.

28. **Miss rate pattern survey**: Phase 2 includes a mandatory prerequisite survey (step 2) that classifies all `gl.create*()` calls in the corpus by their syntactic context before implementing tracking patterns. This validates that the three proposed miss-rate reduction patterns will actually reduce the miss rate to <20% before investing in the full Phase 2 implementation. If they can't, the decision gate triggers reassessment.

29. **Config completeness validation**: `test_config_validation.py` includes a completeness check ensuring every method in `webgl_api_surface.json` appears in at least one category in `feature_categories.json`. This catches omissions (new methods added to the surface but not categorized), which cross-reference tests cannot detect. Uncategorized methods produce warnings, not failures.

30. **Semantic orthogonality**: Solved by the **feature interaction topology** (`docs/interaction_topology.json`) — a static whitelist graph of ~55 edges defining which feature categories can meaningfully interact. N-way combos are checked for topology connectivity (all pairs connected directly or transitively). Disconnected combos are deprioritized in the lexicographic ordering (dimension 2). This replaces the previous `low_interaction_with` blacklist approach, which was backwards — the interaction topology is sparse (~55 edges among C(30,2)=435 possible pairs), so whitelisting meaningful interactions is more complete and maintainable than blacklisting all non-interactions. Expected noise reduction from 30-40% to <10% of generated recipes targeting semantically weak combinations.

31. **Shader complexity blind spot**: Feature detection does not analyze shader structure (branching, loops, uniform count, texture lookups). Two seeds with identical GL methods but radically different shaders produce identical feature fingerprints. This is acknowledged as a design limitation — shader structure analysis would require a GLSL parser beyond the current regex-based builtin matching.

32. **Phase independence**: Phase 1 + Phase 3 form a complete, self-sufficient pipeline. Phase 2 is an optional enrichment layer. This is deliberate: Phase 1 captures ~80% of the value (feature detection + combination coverage + gap identification + topology-filtered recipes). Phase 2 adds interaction quality and security pattern signals, but its inherent limitations (decision #26) mean the additional signal is a lower bound with significant blind spots. Phase 3 recipes contain Phase 2 fields only when Phase 2 data is available; without it, recipes use method targeting, topology edges, and seed constraints — which is sufficient context for the seed-writing LLM. Phase 2 should only be implemented after Phase 1 has proven its value in at least one full coverage expansion cycle.

33. **Recipe validation experiment**: A mandatory zero-cost experiment before building Phase 3: manually create 3-5 recipe-like specs, write seeds both with and without recipe context, and compare quality. Validates the core hypothesis that structured recipes produce meaningfully better seeds than ad-hoc instructions. If recipes don't help, Phase 3 simplifies to a gap report + manual targeting workflow (skip `gap_spec.py`, keep the combination matrix). Cost: ~2 hours. Risk mitigated: building an elaborate pipeline that doesn't improve seed quality.

34. **`pixel_ops` classification**: `pixel_ops` is in `UBIQUITOUS` but NOT in `SECURITY_RELEVANT`. While pixel readback operations can be security-relevant, the category is dominated by false-positive matches from boilerplate `pixelStorei` calls. Its presence in `UBIQUITOUS` reflects empirical frequency, not a security judgment. Genuine pixel readback security concerns are captured by the `fbo + pixel_ops` combination, where `fbo` provides the security relevance signal.

35. **Reference seed quality filtering**: `select_references()` accepts an optional `validated_seeds` parameter (set of seeds known to pass validation). When provided, only validated seeds are eligible as references. A high-overlap seed that fails validation is a worse reference than a lower-overlap seed that works correctly.

## Open Questions

1. **Extension category granularity**: The current design groups related extensions (e.g., all compressed texture extensions into one category). Should each extension be its own category for finer-grained gap detection? Tradeoff: more categories = more combinations = more noise in the matrix.

2. **Phase 2 ROI**: Phase 2 is now optional (decision #32) and gated behind Phase 1 proving its value in at least one coverage expansion cycle. The miss rate pattern survey (Phase 2 step 2) provides concrete data before committing. The fundamental question remains: does the interaction graph provide enough additional value over Phase 1's combination matrix + topology to justify its implementation complexity? Phase 1 captures ~80% of the value. The interaction graph's inherent limitations (decision #26: state-based interactions invisible, score=0 doesn't mean no interaction) limit the remaining 20%. The topology graph (Phase 1) provides lightweight interaction guidance that partially substitutes for Phase 2's runtime interaction detection. This question should be revisited after Phase 1 has been used in practice — if the topology-filtered gap report produces good seeds without interaction scoring, Phase 2 may not be worth implementing.

3. **Fuzzing feedback loop**: The design has no mechanism for feeding fuzzing results (crash reports, coverage data from actual Radamsa runs) back into priority scoring. If certain feature combinations produce more crashes in practice, that should influence which gaps are prioritized. Currently, the security relevance boost is a static heuristic. A future improvement could ingest crash logs and adjust priority scoring based on empirical crash rates per feature combination.

4. **Category granularity mismatch**: `shader_pipeline` has 20+ methods while `mrt` has 1 method. The combination matrix treats these as equals, but a "gap" involving two tiny categories is qualitatively different from a gap between two massive categories. Should the priority scoring account for category size disparity? E.g., deprioritize gaps where all categories are very small (combined method count < 5)?

5. **Shader structure analysis**: Should the GLSL analysis be extended beyond builtin function matching to capture shader complexity metrics (uniform count, texture lookup count, branching depth, loop nesting)? This would address the shader complexity blind spot (decision #31) but requires a proper GLSL parser. Could be a Phase 4 addition if Phase 1-3 prove their value.
