# WebGL API Surface Extraction Design (v2)

## Problem

The fuzzing corpus has excellent **feature category** coverage (18 categories, all 2-way and 3-way gaps closed) but no measurement of **spec-level API surface** coverage. We don't know which of the ~183 WebGL/WebGL2 method names (~293 signatures including overloads), ~361 core constants (plus ~80-100 extension constants), or ~254 documented error conditions are actually exercised by the 367 seeds.

## Goal

Build a two-phase system:

1. **Phase 1 (this document):** Extract the WebGL API surface from WebIDL specs into a structured JSON file. Build an AST-based audit tool that analyzes the corpus against this file to produce a tiered gap report — which methods and constants are missing or underrepresented, ranked by detection confidence.

2. **Phase 2 (future, driven by Phase 1 results):** If Phase 1 reveals that method/constant coverage is already high and the remaining gaps are about parameter combination diversity, add LLM-assisted extraction of valid parameter combinations (format/type/internalformat triples) from spec prose, and extend the auditor to measure combinatorial coverage.

## Architecture

Two tools, one shared artifact:

```
┌─────────────────────┐         ┌──────────────────────────┐
│  extract_webidl.js  │         │  audit_api_surface.py    │
│  (Node.js, one-shot)│         │  (Python, runs often)    │
│                     │         │                          │
│  .idl_cache/ ───────┤         │  367 HTML seeds ──┐      │
│  (local/Khronos)    │         │                   │      │
│         │           │         │  tree-sitter AST ─┤      │
│         ▼           │         │  shader string ───┘      │
│  webgl_api_surface  │────────▶│  per-file cache (.cache/)│
│      .json          │         │         │                │
│  (committed)        │         │         ▼                │
└─────────────────────┘         │  gap report (tiered)     │
                                │  delta report (--file)   │
                                └──────────────────────────┘
```

**Extraction** (Node, `webidl2`): Checks `.idl_cache/` for IDLs; downloads from Khronos registry if missing. Parses with `webidl2`, produces `docs/webgl_api_surface.json`. Run once, output committed.

**Auditor** (Python, `tree-sitter-javascript`): Walks the corpus AST, tracks context aliases (e.g., `const ctx = gl`), resolves constants via two-pass propagation, extracts shader strings, produces tiered gap reports. Supports full-corpus and delta modes. Cache in `.cache/api_audit/` (gitignored).

**Shared artifact**: `webgl_api_surface.json` is the contract between the two tools and the source of truth for what "complete coverage" means.

## Why intermediate JSON, not direct spec parsing

1. **Separation of concerns.** Extraction (IDL -> JSON) and auditing (JSON + AST -> report) are independent tools in different languages.
2. **The specs are stable.** WebGL is a finished standard. The JSON is a version-controlled source of truth.
3. **AST precision.** Raw `grep` causes false positives (e.g., a constant existing in a file but not passed to the relevant method). AST analysis ensures the constant is an argument to the specific call.
4. **Agent consumption.** The JSON schema supports tiered confidence reporting, letting an agent act autonomously on high-confidence gaps and spend analysis time on ambiguous ones.

## Spec analysis

### Scale

| Metric | WebGL 1.0 | WebGL 2.0 (new only) | Combined Core |
|--------|-----------|---------------------|---------------|
| Unique method names | ~95 | ~88 | ~183 |
| Method signatures (with overloads) | ~146 | ~147 | ~293 |
| const GLenum definitions | ~159 | ~202 | ~361 |
| Regular interfaces | 12 | 6 | 18 |
| Interface mixins (latest IDL) | 2 | 2 | 4 |
| Extension files in registry | — | — | ~57 |

### IDL sources

IDL sources from Khronos registry. Use the **latest** (not versioned) URLs for modern `interface mixin` / `includes` syntax that `webidl2` handles natively:

- WebGL 1.0: `https://registry.khronos.org/webgl/specs/latest/1.0/webgl.idl` (pure IDL, direct parse)
- WebGL 2.0: `https://registry.khronos.org/webgl/specs/latest/2.0/webgl2.idl` (pure IDL, direct parse)
- Extensions: `https://registry.khronos.org/webgl/extensions/{NAME}/extension.xml` (XML with embedded `<idl>` tags — requires XML extraction before `webidl2` parse)

**WebGL2 inheritance model:** `WebGL2RenderingContext` uses mixin includes (not classical inheritance):
- `WebGLRenderingContextBase` — all WebGL1 methods + constants
- `WebGL2RenderingContextBase` — all new WebGL2 methods + constants
- `WebGL2RenderingContextOverloads` — extended overloads of WebGL1 methods

The auditor must understand this: a seed calling `gl.bindTexture()` on a WebGL2 context exercises a WebGL1-origin method.

### What's parseable from WebIDL (Phase 1 scope)

WebIDL provides the "Hard Schema":
- Complete method signatures with parameter names and types.
- All `const GLenum` definitions with hex values.
- Extension-specific methods and constants.
- Method-to-extension mapping (which interface defines which method).
- Overload signatures with arity, enabling ambiguity detection.

### What requires LLM/Manual extraction (Phase 2 scope)

Deferred until Phase 1 results show these are the bottleneck:
1. **Valid parameter combinations.** The `internalformat/format/type` triples (27+ tables in spec prose).
2. **Error conditions.** Natural language triggers for `INVALID_*` errors.
3. **State dependencies.** Preconditions (e.g., "Transform feedback must be active").

## Phase 1 JSON schema

This is **schema version 3.0** (as recorded in the `meta.schema_version` field). The schema evolved during design: v1 used a single `category` string per constant; v2 replaced it with a `roles` list; v3 (current) adds `ambiguous_arity` flags, GLSL built-ins, optional per-overload `webgl_version`, and `kind` classification heuristic. See "Schema notes" below the example for details.

```json
{
  "meta": {
    "sources": [
      {"name": "WebGL 1.0", "url": "...", "sha256": "..."},
      {"name": "WebGL 2.0", "url": "...", "sha256": "..."}
    ],
    "schema_version": "3.0",
    "extracted_at": "2026-02-24T..."
  },

  "constants": {
    "COLOR_BUFFER_BIT": {
      "value": "0x00004000",
      "kind": "bitmask",
      "roles": ["buffer_bit"],
      "webgl_version": 1
    },
    "RGBA": {
      "value": "0x1908",
      "kind": "enum",
      "roles": ["format", "internalformat"],
      "webgl_version": 1
    },
    "UNSIGNED_BYTE": {
      "value": "0x1401",
      "kind": "enum",
      "roles": ["pixel_type", "index_type"],
      "webgl_version": 1
    }
  },

  "methods": {
    "texImage2D": {
      "webgl_version": 1,
      "overloads": [
        {
          "arity": 6,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "level", "type": "GLint"},
            {"name": "internalformat", "type": "GLint"},
            {"name": "format", "type": "GLenum"},
            {"name": "type", "type": "GLenum"},
            {"name": "source", "type": "TexImageSource"}
          ]
        },
        {
          "arity": 9,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "level", "type": "GLint"},
            {"name": "internalformat", "type": "GLint"},
            {"name": "width", "type": "GLsizei"},
            {"name": "height", "type": "GLsizei"},
            {"name": "border", "type": "GLint"},
            {"name": "format", "type": "GLenum"},
            {"name": "type", "type": "GLenum"},
            {"name": "pixels", "type": "ArrayBufferView?"}
          ]
        }
      ]
    },
    "bufferData": {
      "webgl_version": 1,
      "ambiguous_arity": true,
      "overloads": [
        {
          "arity": 3,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "size", "type": "GLsizeiptr"},
            {"name": "usage", "type": "GLenum"}
          ]
        },
        {
          "arity": 3,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "srcData", "type": "AllowSharedBufferSource?"},
            {"name": "usage", "type": "GLenum"}
          ]
        }
      ]
    }
  },

  "extensions": {
    "EXT_color_buffer_float": {
      "methods": {},
      "constants": {}
    },
    "OES_vertex_array_object": {
      "methods": {
        "createVertexArrayOES": {
          "overloads": [{"arity": 0, "params": []}]
        },
        "deleteVertexArrayOES": {
          "overloads": [{"arity": 1, "params": [{"name": "arrayObject", "type": "WebGLVertexArrayObjectOES?"}]}]
        },
        "isVertexArrayOES": {
          "overloads": [{"arity": 1, "params": [{"name": "arrayObject", "type": "WebGLVertexArrayObjectOES?"}]}]
        },
        "bindVertexArrayOES": {
          "overloads": [{"arity": 1, "params": [{"name": "arrayObject", "type": "WebGLVertexArrayObjectOES?"}]}]
        }
      },
      "constants": {
        "VERTEX_ARRAY_BINDING_OES": {"value": "0x85B5", "kind": "enum", "roles": ["get_parameter"]}
      }
    }
  },

  "glsl_builtins": {
    "texture_sampling": [
      "textureSize", "texture", "textureProj", "textureLod", "textureOffset",
      "texelFetch", "texelFetchOffset", "textureProjOffset", "textureLodOffset",
      "textureProjLod", "textureProjLodOffset", "textureGrad", "textureGradOffset",
      "textureProjGrad", "textureProjGradOffset"
    ],
    "fragment_processing": ["dFdx", "dFdy", "fwidth"],
    "bit_reinterpretation": ["floatBitsToInt", "floatBitsToUint", "intBitsToFloat", "uintBitsToFloat"],
    "pack_unpack": [
      "packSnorm2x16", "unpackSnorm2x16", "packUnorm2x16", "unpackUnorm2x16",
      "packHalf2x16", "unpackHalf2x16"
    ],
    "matrix": ["outerProduct", "transpose", "determinant", "inverse"],
    "distinctive_math": [
      "smoothstep", "inversesqrt", "faceforward", "matrixCompMult",
      "roundEven", "isnan", "isinf", "modf", "fract", "trunc",
      "radians", "degrees", "refract",
      "lessThan", "lessThanEqual", "greaterThan", "greaterThanEqual",
      "notEqual", "sinh", "cosh", "tanh", "asinh", "acosh", "atanh"
    ]
  }
}
```

> **GLSL built-in filtering rationale:** Only GLSL ES 3.0 built-ins that are (a) unambiguously GLSL-specific (no overlap with common JS/variable names) and (b) exercise distinct driver code paths. Common math like abs, min, max, clamp, mix, step, pow, floor, ceil, dot, cross, normalize, length, distance, reflect are excluded because they map to trivial hardware instructions and their names collide with user-defined functions. The 56 functions above target texture sampling pipelines, data reinterpretation, packing, and ES 3.0-specific math that stresses less-tested shader compiler paths.

### Schema notes

- **Overload versioning:** Overloads originating from `WebGL2RenderingContextOverloads` carry an optional `"webgl_version": 2` field on the overload entry itself. If absent, the overload inherits `webgl_version` from the parent method. This lets the auditor distinguish "WebGL2-specific overload of `texImage2D` never exercised" from "original WebGL1 overload unused."
- **`kind` classification:** The IDL does not distinguish bitmask from enum constants — all are `const GLenum`. The extractor applies a heuristic: constants with a `_BIT` suffix whose hex value is a power of two are classified as `"bitmask"`; all others default to `"enum"`.

### Constant role mapping — hybrid approach

Constants are assigned to roles via a three-tier strategy applied **sequentially** — each tier processes only the constants not yet classified by earlier tiers. Estimated counts are based on prototype testing against 361 core constants and should be treated as approximations, not commitments.

**Critical asymmetry:** The WebGL 1.0 IDL is exhaustively annotated with `/* GroupName */` block comments before each constant group (e.g., `/* BeginMode */`, `/* BlendingFactorDest */`, `/* TextureTarget */`). The WebGL 2.0 IDL has essentially **zero** such fine-grained annotations — only coarse section headers like `/* Buffer objects */` that span dozens of unrelated constants. This means Tier A covers ~100% of WebGL1 constants but ~0% of WebGL2 constants. Tier C (structural heuristics) catches another ~50 WebGL2 constants. The remaining ~200 WebGL2 constants require manual classification in Tier B.

**Tier A — Stateful IDL Block Scraping (~159 WebGL1 constants, ~44% of total, fully automatic):**
The extraction script uses a stateful parser that tracks `/* GroupName */` comment blocks in the IDL. Constants following a block comment inherit its group name as their role (e.g., `TextureUnit`, `GetPName`, `Framebuffer Object`). **Scope:** Effectively WebGL1-only — the WebGL2 IDL lacks the fine-grained comment annotations this tier depends on. **Caveat:** This depends on the specific comment formatting convention in the Khronos WebGL1 IDL (`/* GroupName */` on a line by itself preceding a block of `const GLenum` definitions). If Khronos reformats the IDL, Tier A yields will drop. The "latest" IDL URLs may be updated at any time — pin downloaded IDLs by SHA256 (already in `meta.sources`) and re-validate tier distribution on each re-extraction.

**Tier B — Manual Mapping Table (~150 constants, ~42% of total, version-controlled):**
A manually authored lookup table in the extraction script maps WebGL2 constants to their semantic roles. This table is organized by role group for maintainability:

| Role Group | Example Constants | Approx Count |
|-----------|------------------|-------------|
| `sized_internalformat` | `RGBA32F`, `RGB16F`, `R8I`, `RG32UI`, `SRGB8_ALPHA8` | ~56 |
| `buffer_usage` | `STREAM_READ`, `STATIC_READ`, `DYNAMIC_COPY` | ~6 |
| `buffer_target` | `COPY_READ_BUFFER`, `PIXEL_PACK_BUFFER`, `UNIFORM_BUFFER` | ~6 |
| `texture_target` | `TEXTURE_3D`, `TEXTURE_2D_ARRAY`, `TEXTURE_WRAP_R` | ~8 |
| `get_parameter` / `pname` | `MAX_DRAW_BUFFERS`, `MAX_SAMPLES`, `VERTEX_ARRAY_BINDING` | ~35 |
| `transform_feedback` | `INTERLEAVED_ATTRIBS`, `SEPARATE_ATTRIBS`, `RASTERIZER_DISCARD` | ~8 |
| `sync` | `SYNC_CONDITION`, `SIGNALED`, `ALREADY_SIGNALED`, `WAIT_FAILED` | ~10 |
| `query` | `QUERY_RESULT`, `ANY_SAMPLES_PASSED`, `CURRENT_QUERY` | ~8 |
| `uniform_buffer` | `UNIFORM_BLOCK_DATA_SIZE`, `UNIFORM_ARRAY_STRIDE` | ~15 |
| Other | `DRAW_BUFFER0`–`DRAW_BUFFER15`, `COLOR_ATTACHMENT1`–`15`, etc. | ~remaining |

**Scope acknowledgment:** Tier B is the largest single effort in Phase 1 extraction, requiring ~150 manual lookups. Budget accordingly.

**Creation methodology:** Build the table incrementally. For each constant, record the WebGL 2.0 spec section and/or MDN page that determines its role. Table entries should include a provenance comment (e.g., `// texImage2D spec table 3.2`, `// MDN WebGL2 getParameter`). This creates an auditable trail from each classification back to its authoritative source. The manual table should be re-reviewed against the spec whenever the IDL is re-fetched, not only on initial creation.

**Why not automated cross-referencing?** Prototype testing of name-based matching between constant names and method parameter names achieved only 3.9% true positive rate on WebGL2 orphans (10 correct out of 254). The core problem: WebGL2 method signatures use generic parameter names (`pname`, `target`, `type`, `mode`) that carry no semantic information about which of the hundreds of constants belong to each slot. The 40 distinct `GLenum` parameter names in the IDL are too coarse to distinguish `TEXTURE_MIN_LOD` (a `texParameteri` pname) from `QUERY_RESULT` (a `getQueryParameter` pname) from `UNIFORM_BLOCK_DATA_SIZE` (a `getActiveUniformBlockParameter` pname) — all three get passed to a parameter named `pname`.

**Guardrail:** The manual table is version-controlled and validated at extraction time: every WebGL2 constant not covered by Tier A or Tier C must have an entry. Missing entries cause the extraction script to fail with a list of unclassified constants, preventing silent gaps.

**Cross-validation:** For constants that appear in both Tier A (IDL block scraping) and Tier B (manual table), the extraction script checks that the roles are consistent. Mismatches (e.g., Tier A says `BlendingFactorDest` but Tier B says `stencil_op`) cause extraction to fail, listing the conflicting constant and both claimed roles. **Rationale:** A mismatch means either the IDL comment parser is wrong or the manual table is wrong — both need investigation before the surface JSON can be trusted. Warnings are too easy to ignore for a bug that silently corrupts coverage measurement.

**Tier C — Prefix/suffix heuristics (~52 constants, ~14% of total, automatic):**
Constants from both WebGL versions are caught by structural patterns:
- `_BIT` suffix + power-of-two value → `buffer_bit` role, `"kind": "bitmask"`
- Sized format suffixes (`_SNORM`, `8UI`, `32F`, `16I`, etc.) → `sized_internalformat`
- `INVALID_` prefix → `error_code`
- `UNPACK_`/`PACK_` prefix → `pixel_store`

This tier also handles `kind` classification for **all** constants (including those already role-tagged by Tiers A/B), since `kind` is orthogonal to role assignment. All other constants default to `"kind": "enum"`.

## Extraction process

### Step 1: WebIDL fetching & parsing

The script `scripts/extract_webidl.js` manages local IDL files:

1. **Cache Check:** Checks `scripts/.idl_cache/` for previously downloaded files.
2. **Download Core IDLs:** If missing, downloads from Khronos registry (`latest/1.0/webgl.idl`, `latest/2.0/webgl2.idl`) and saves locally. These are pure IDL — parse directly with `webidl2`.
3. **Download Extension XMLs:** For each extension in the registry index, downloads `extension.xml`. Extracts IDL text from `<idl xml:space="preserve">` tags using an XML parser (Node's built-in or `fast-xml-parser`). Feeds extracted IDL to `webidl2`.
4. **Handle empty extensions:** Some extensions (e.g., `EXT_color_buffer_float`) define empty interfaces with no methods or constants — they exist purely as feature-detection markers. Record these in the JSON with `"methods": {}, "constants": {}` so the auditor knows to check for `gl.getExtension('EXT_color_buffer_float')` calls.
5. **Handle parser failures:** If `webidl2` fails on an extension IDL fragment (e.g., non-standard attributes like `[AllowShared]` inside union types), log a warning and skip that extension. Do not abort the entire extraction. The canary check below catches catastrophic failures.
6. **Produce JSON:** Merge all parsed IDLs into `docs/webgl_api_surface.json` following the schema below.

**Validation:**
- **Canary Check:** Script must fail if resulting JSON has <150 unique method names or <300 constants.
- **Role Assignment:** Every constant must have at least one entry in the `roles` array (see constant role mapping section above).
- **Extension count:** Script must warn if fewer than 20 extensions were successfully parsed.
- **Tier A yield:** Warn if Tier A produces <100 constants (expected ~159). This detects IDL comment format changes.
- **Tier B coverage:** Fail if any WebGL2 constant is unclassified after all tiers (already specified — keep).
- **Tier C yield:** Warn if Tier C produces <30 constants (expected ~52). This detects pattern drift.

## Audit tool design

The audit tool (`scripts/audit_api_surface.py`) uses `tree-sitter-javascript` to parse the corpus. It recursively scans `samples-webgl/` for HTML files across all subdirectories (`mutations/`, `seeds/`, `creative/`, `webgl2/`, `extensions/`, `integrated/`, `multipass/`, `errors/`, `rendering/`, `limits/`, `edge_cases/`, `texture_tech/`, `compute/`, `shaders/`, `resource/`).

### AST analysis pipeline

For each HTML file:

1. **HTML extraction:** Extract `<script>` content.
2. **tree-sitter parse:** Parse JS into AST.
3. **Context & Alias Detection:**
   - Find `canvas.getContext('webgl2')` or `canvas.getContext('webgl')`. Record the API version per seed. 22 seeds use `getContext('webgl2') || getContext('webgl')` fallback (all inline `||`) — these are tagged as WebGL1-capable and their coverage counts toward WebGL1 methods. The remaining 345 seeds use pure WebGL2 context creation.
   - **Global Alias Tracker:** Track context aliases across function boundaries. If a function parameter is named `gl` or `ctx` and the call site passes a known context, treat it as a context within that function. Corpus analysis shows 18 files define helper functions with `gl` as a parameter (e.g., `createShader(gl, type, source)`) — these must be tracked. Corpus analysis (2026-02-24) confirms all 18 files use **single-level** helper functions — `main()` calls `createShader(gl, ...)` which uses `gl` directly. No two-level indirection (e.g., `a(gl)` calling `b(gl)`) exists in the corpus. The single-level tracking design is therefore sufficient. If future seeds introduce deeper indirection, the auditor will silently miss those calls — this is acceptable given the known-limitations section already documents "deep dataflow" as out of scope.
   - **Extension detection — three patterns (a single seed may use multiple):**
     - **Array pattern (dominant, 340 seeds):** `const REQUIRED_EXTENSIONS = ['EXT_color_buffer_float', ...]; REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext))`. Resolve the `REQUIRED_EXTENSIONS` array literal to extract string values, then map those to extension names. The `ext` parameter in the `.forEach` callback receives each extension name string from the array and passes it to `getExtension`; the return value (the extension object) is discarded, so no extension object alias is created by this pattern. **Implication for extension method tracking:** Extension-specific methods (e.g., `createVertexArrayOES()`) can only be tracked when a seed uses the direct assignment pattern (`const ext = gl.getExtension('...')`). Seeds that enable extensions only via the array forEach pattern enable the extension's constants and capabilities on the `gl` context but do not create an alias for extension-specific method calls. Corpus analysis confirms no seed stores extension objects in collections or arrays — all extension method calls use simple variable aliases. Note: 278 of these 340 seeds have an empty `REQUIRED_EXTENSIONS = []` array — the forEach runs but calls `getExtension` zero times. Only 62 seeds declare non-empty extension arrays via this pattern.
     - **Direct assignment (27 seeds, 25 overlap with array pattern):** `const ext = gl.getExtension('OES_vertex_array_object')`. Track the assigned variable as an extension alias for method calls like `ext.createVertexArrayOES()`. Most of these seeds also use `REQUIRED_EXTENSIONS` for non-aliased extensions — the auditor must handle both patterns in the same file.
     - **Exclusive direct (3 seeds):** Seeds that use only direct `gl.getExtension()` with no `REQUIRED_EXTENSIONS` array at all. Two assign the result to a variable (`extensions_element_index_uint.html`, `seed_query_conditional_mrt_stencil_blend_ubos.html`); one discards it as a bare enable call (`extensions_shader_derivatives.html` — `gl.getExtension('OES_standard_derivatives')` with no assignment). The auditor must detect all three sub-patterns: `const x = gl.getExtension(...)`, `gl.getExtension(...)` as an expression statement, and the array forEach pattern.
     - **No extensions (24 seeds):** Seeds that never call `gl.getExtension()` and have no `REQUIRED_EXTENSIONS` array at all. Concentrated in `seeds/` (20) and `creative/` (3) plus one in `multipass/`. These exercise only core WebGL2 API surface.
4. **Const propagation** (two-pass):
   - **Pass 1 (collection):** Walk all `const`/`let` declarations and record each identifier's initializer expression without resolving references. This builds the complete declaration map before any lookups.
   - **Pass 2 (resolution):** Resolve references using the declaration map. Map `identifier -> gl.CONSTANT` (e.g., `const RGBA = gl.RGBA`). Two passes ensure forward references (declarations appearing after their first use) are handled correctly. While the three-zone architecture makes forward references unlikely, two-pass resolution is trivially more robust with no performance cost.
   - **Template literal propagation:** Map `identifier -> template literal content` for shader source variables (e.g., `` const vsSource = `#version 300 es ...` ``). This is required because `shaderSource()` always receives an identifier, never an inline string. The propagation resolves `vsSource` to its initializer. **Corpus convention:** All seeds in the current corpus use single template literals for shader source. No shader string concatenation (`vsSource = header + body`) exists. The auditor does not resolve `BinaryExpression` concatenation for shader strings. If future seeds use concatenation, the GLSL built-ins within those shaders will be invisible to the auditor. This is documented as a known limitation, not a design gap — the corpus convention is template literals.
   - **Array literal resolution:** Map `identifier -> array of string literals` for extension arrays (e.g., `const REQUIRED_EXTENSIONS = ['EXT_color_buffer_float', ...]`). Each string element is extracted as an extension name.
5. **Call analysis & Disambiguation:**
   - Resolve receiver to a known context or extension alias.
   - **Role-aware constant tracking:** For each resolved `gl.method(arg0, arg1, ...)` call, look up the method's signature in `webgl_api_surface.json` to determine which parameter position each argument occupies. If `arg1` resolves to `gl.FLOAT` and the method signature says parameter 1 is `type: GLenum`, record "FLOAT used in `type` role for this method." This is what enables the gap report to distinguish "FLOAT as pixel_type: 0 seeds" from "FLOAT as internalformat: 12 seeds." For methods with multiple overloads of different arity, select the overload matching the call's argument count. For ambiguous-arity overloads (same arity, different types), fall back to recording the constant against the union of possible roles.
   - **Constructor-Based Overload Resolution:** To distinguish overloads like `bufferData(target, size, usage)` vs `bufferData(target, data, usage)`:
     - `NewExpression` (e.g., `new Float32Array`) -> `data`
     - `Literal` or `BinaryExpression` (e.g., `1024 * 4`) -> `size`
     - Unresolvable identifiers -> Tier 3.
   - **Corpus impact of ambiguous-arity fallback:** The primary ambiguous-arity method is `bufferData` (3-arg form used in 320 of 367 seeds). However, constructor-based disambiguation resolves most cases — seeds predominantly use `new Float32Array(...)` (data overload) or numeric literals/expressions (size overload). The remaining ambiguous calls (unresolvable identifiers) are estimated at <10% of `bufferData` calls. Other potentially ambiguous methods (`texImage2D:6`, `bufferSubData:4`) have zero occurrences in the current corpus, so arity alone resolves all their overloads.
   - Walk each argument, resolving `member_expression`, `identifier`, and bitwise `|`.
   - **Return-value tracking:** Detect `=== gl.CONSTANT` and `!== gl.CONSTANT` comparison expressions where the left side is a `gl` method call or a variable assigned from one. Record the constant as "used in return-value comparison for [method]." This is low-frequency (5 seeds currently) but captures constants that never appear as arguments — notably `FRAMEBUFFER_COMPLETE`, `ALREADY_SIGNALED`, `NO_ERROR`, and similar status/result constants. This is additive — it does not change existing argument tracking.
6. **Shader extraction:** The second argument to `shaderSource(shader, source)` is always an identifier in this corpus (e.g., `vsSource`), never an inline string. Resolve the identifier to its template literal initializer via const propagation (step 4). For seeds that use helper functions like `createShader(gl, type, source)`, trace the `source` parameter back to the call site's argument. Within extracted shader source text, regex-match `\b(functionName)\s*\(` against `glsl_builtins`. Strip GLSL comments (`//`, `/* */`) and string literals before matching to avoid false positives.

### Confidence tiers

| Tier | What it catches | Accuracy | Agent action |
|------|----------------|----------|--------------|
| **1 - Certain** | Method never called in any seed. | 100% | Generate seed immediately. |
| **2 - High** | Constant never passed to any GL call OR specific method overload never used (after disambiguation). | ~95% | Generate seed, low risk of redundancy. |
| **3 - Needs analysis** | Ambiguous overload (remaining after disambiguation) or distinctive GLSL built-in missing from all shader sources. | ~75% | Agent reads relevant seeds before deciding. |

### Known limitations (by design)

- **Deep Dataflow:** Does not track context objects passed through multiple functions.
- **Computed Properties:** `gl[methodName](...)` is not tracked.
- **Array-indexed constants:** `const modes = [gl.TRIANGLES]; gl.drawArrays(modes[0], ...)` is missed.
- **Destructuring:** `const { TRIANGLES } = gl` is not tracked. (No occurrences in the current corpus; listed for completeness.)
- **AST vs. runtime coverage:** Every seed wraps operations in `try-catch(e) {}`. A call present in the AST may always throw at runtime (wrong state, invalid enum) and never reach driver processing. The auditor reports AST-level coverage, not runtime coverage. For mutation-based fuzzing this is correct — the call exists for Radamsa to mutate, and a mutated version may succeed where the original throws. But the gap report should not be interpreted as "the driver processes this call in N seeds."

### Convention lint

The auditor runs a lightweight convention check on each file before AST analysis. It flags (not fails) seeds that use patterns the auditor cannot track:

- `gl[` — computed property access on the WebGL context
- `const {` followed by `} = gl` — destructuring of context object
- String concatenation in `shaderSource()` arguments — non-template-literal shader source (detected via `BinaryExpression` node as the second argument to `shaderSource`)
- Helper functions calling other helper functions that receive `gl` — multi-level indirection (detected via call graph depth > 1 among functions with a `gl` parameter)

Flagged seeds are still analyzed, but the report marks their coverage contribution as "partial — convention violation detected." This prevents invisible coverage holes when new seeds break assumptions the auditor relies on.

### Report modes

**Full corpus** (`python scripts/audit_api_surface.py`):
- Analyzes all seeds, uses two-layer caching in `.cache/api_audit/`:
  - **Layer 1 — Per-file parse cache:** Keyed by `SHA256(file_content)`. Stores extracted call data: method names with argument lists, constants used, shader strings, extension aliases. This cache survives surface JSON changes because parsed call data is independent of the surface definition.
  - **Layer 2 — Coverage evaluation:** Compares aggregated call data against `webgl_api_surface.json`. Keyed by `SHA256(surface_json) + SHA256(aggregated_call_data)`. When the surface JSON changes (new constants, fixed roles), only this layer is invalidated — the expensive per-file AST parsing is reused. Note: Layer 2 invalidation is all-or-nothing — adding or modifying any single seed invalidates the entire Layer 2 cache, since `SHA256(aggregated_call_data)` changes. For the current 367-seed corpus this is acceptable (full re-evaluation is cheap once Layer 1 is populated). If the corpus grows past ~2000 seeds, consider switching to incremental Layer 2 updates keyed by per-file contribution deltas.
- Produces `docs/api_coverage_report.md` with per-role constant coverage and tiered gaps.

**Example gap report output:**

```
=== Tier 1 — Missing Methods (Certain) ===
  getFragDataLocation     (WebGL2, 0 seeds)
  waitSync                (WebGL2, 0 seeds)
  fenceSync               (WebGL2, 0 seeds)

=== Tier 2 — Missing Constants/Overloads (High Confidence) ===
  FLOAT as pixel_type:          0 seeds (constant appears in 47 seeds in other roles)
  texImage2D arity-10:          0 seeds (arity-6 and arity-9 covered)
  RASTERIZER_DISCARD as enable: 2 seeds (below 3-seed threshold)

=== Tier 3 — Needs Analysis ===
  bufferData arity-3:           ambiguous in 12 seeds (size vs data indistinguishable)
  texelFetchOffset (GLSL):      0 shader matches (texelFetch found in 8 seeds)
```

**Delta mode** (`python scripts/audit_api_surface.py --file path/to/seed.html`):
- Requires a prior full-corpus run (loads cached per-file call data from `.cache/api_audit/`).
- Parses the specified seed, extracts its call data, then computes: which methods/constants/overloads does this seed exercise that are currently at 0 coverage (new coverage) or below the 3-seed threshold (incremental coverage)?
- Output: a compact list of "this seed adds coverage for: [methods], [constants], [overloads]" plus "this seed is redundant for: [everything else it exercises]."
- If no prior full-corpus cache exists, prints a warning and falls back to full-corpus mode. To avoid a cold-start penalty during seed development, commit the Layer 1 cache directory or ship a `make audit-cache` target that runs a full-corpus parse.

## Relationship to existing tooling

This system **supplements** `scripts/feature_matrix.sh` for coverage measurement. The feature matrix provides a lightweight grep-based sanity check across 16 hand-picked categories (runs in <1 second, useful during rapid seed iteration). The API surface auditor provides spec-complete, AST-verified coverage with per-method and per-constant granularity. Both tools answer useful but different questions: the feature matrix says "45 seeds use Transform Feedback" (development sanity check); the auditor says "`beginTransformFeedback` is called in 45 seeds, but `pauseTransformFeedback` is called in only 3" (spec coverage detail). Keep `feature_matrix.sh` as the quick dev tool; use `audit_api_surface.py` as the authoritative coverage measurement.

## Interaction with UNSUPPORTED.md

Seeds that require unsupported extensions (listed in `UNSUPPORTED.md`) are still analyzed by the auditor — their AST contains valid `gl.getExtension()` calls and extension method calls that contribute to coverage counts. The auditor does **not** cross-reference test results or runtime success. This is intentional: for mutation fuzzing, a seed that throws `UNSUPPORTED_EXTENSIONS` in one browser may work in another (Firefox has superior extension support). The gap report should note which extension methods are exercised exclusively by seeds requiring potentially-unsupported extensions, so that the operator can assess whether coverage claims depend on browser choice. The `--file` delta mode output should flag if a seed's extension requirements overlap with `UNSUPPORTED.md` entries.

## Dependencies

- **Node:** `webidl2`
- **Python:** `tree-sitter`, `tree-sitter-javascript` (added to `requirements.txt`). Both packages ship prebuilt binary wheels for common platforms (Linux x86_64, macOS ARM/x86_64, Windows) — no C compiler required for installation.

## Development milestones

| Milestone | Scope | Validation |
|-----------|-------|------------|
| **M1** | IDL extraction: `extract_webidl.js` runs, produces valid JSON, passes canary checks (>150 methods, >300 constants, >20 extensions). | JSON committed, schema validated. |
| **M2** | Basic auditor: parses 5 seeds, correctly detects method calls, produces Tier 1 gap report (missing methods) with no false positives. | Manual spot-check against known seed content. |
| **M3** | Const propagation + extension detection: auditor handles `REQUIRED_EXTENSIONS` array pattern (340 seeds, 62 non-empty), direct `gl.getExtension()` assignment (27 seeds, 25 overlapping with array pattern), `gl.CONSTANT` aliasing, and template literal shader sources. Tier 2 reporting operational. | Run on full corpus, verify extension counts match both detection patterns. Spot-check 5 seeds that use both patterns in the same file. |
| **M4** | Overload disambiguation + GLSL extraction: constructor-based overload resolution, shader string analysis. Tier 3 reporting operational. | Compare auditor output against manual inspection of 10 seeds. |
| **M5** | Caching + delta mode: SHA256-based per-file caching, `--file` delta mode. First run (cold cache, 367 files) completes in <5 minutes. Second full-corpus run completes in <30 seconds. | Time two consecutive runs; time a cold run after clearing `.cache/api_audit/`. |

## Phase 2 trigger criteria

Proceed to Phase 2 when Phase 1 gaps are predominantly combinatorial (Phase 2's focus), not missing API surface. Specific thresholds:

- **Tier 1 gaps** (missing methods) < 5% (~9 or fewer of ~183 method names uncovered).
- **Tier 2 gaps** (missing constants) < 15% per role (across role groups with >5 constants; smaller groups may have higher variance).
- **GLSL built-in coverage** > 50% of the 56 distinctive functions.
- All thresholds are subject to revision after the first full-corpus audit run — they are informed estimates, not empirically calibrated.

**Phase 1 GLSL remediation:** After the first full-corpus audit, run a dedicated GLSL coverage round targeting the 56 distinctive built-ins. Priority targets: all bit-reinterpretation functions (4), all pack/unpack functions (6), under-covered texture sampling variants, and derivative functions. This round runs in parallel with any remaining API method/constant gap closure and does not block Phase 2. The 50% threshold gates Phase 2 entry; the remediation round is the mechanism to get there.

**Current GLSL baseline** (pre-auditor, grep-estimated): Coverage is heavily skewed toward texture sampling (`texture` in 149 seeds, `textureLod` in 12, `texelFetch` in 6). Most non-sampling builtins have 0 seeds (all bit-reinterpretation, all pack/unpack, all matrix except `inverse`). An earlier draft of this design used an 80% threshold, which was unrealistic given the corpus was built for WebGL API coverage, not GLSL built-in diversity. The revised 50% threshold accounts for this while still requiring meaningful improvement before declaring Phase 1 complete.

**Remediation workflow (out of scope for this design):** The gap report is consumed by a human or agent who creates seeds targeting specific gaps. The auditor's `--file` delta mode validates each new seed's contribution before committing. A future design may specify a template-based seed generator that reads the gap report directly.
