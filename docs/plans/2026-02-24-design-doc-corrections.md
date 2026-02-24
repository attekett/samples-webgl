# WebGL API Surface Extraction Design — Corrections Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update `docs/plans/2026-02-24-webgl-api-surface-extraction-design.md` with verified ground truth from real Khronos IDL files, fixing three categories of inaccuracies: (1) extraction pipeline obstacles, (2) GLSL analysis scope, (3) constant role enumeration.

**Architecture:** This is a design document revision, not code. Each task edits specific sections of the design doc to replace assumptions with verified data.

**Tech Stack:** Markdown editing only. All data comes from research already completed.

---

## Research Summary (input to all tasks)

### Verified Counts

| Metric | WebGL 1.0 | WebGL 2.0 (new) | Combined Core | Extensions (~57) |
|--------|-----------|-----------------|---------------|------------------|
| Unique method names | ~95 | ~88 | ~183 | varies |
| Method signatures (with overloads) | ~146 | ~147 | ~293 | varies |
| const GLenum definitions | ~159 | ~202 | ~361 | ~80-100 |
| Interfaces | 12 | 6 new | 18 | varies |
| Interface mixins (latest IDL) | 2 | 2 | 4 | 0 |

The design doc's intro claims "~192 methods, ~819 constants" — both wrong. The spec table claims "115/99/297/522" — also wrong. Real numbers above.

### Extension File Format

Extension specs are **XML files** (`extension.xml`), not pure IDL. Structure:

```xml
<ratified href="OES_vertex_array_object/">
  <name>OES_vertex_array_object</name>
  <idl xml:space="preserve">
    interface OES_vertex_array_object {
        const GLenum VERTEX_ARRAY_BINDING_OES = 0x85B5;
        WebGLVertexArrayObjectOES createVertexArrayOES();
        ...
    };
  </idl>
</ratified>
```

Root element varies: `<ratified>` vs `<extension>` depending on status. IDL is extractable from `<idl>` tags. `webidl2` can parse the extracted text.

### IDL Version Choice

Two versions of each core IDL exist:
- **Versioned** (`/specs/1.0.2/`, `/specs/2.0.0/`): Older syntax, everything on interfaces directly.
- **Latest** (`/specs/latest/1.0/`, `/specs/latest/2.0/`): Modern `interface mixin` + `includes` syntax.

Use **latest** for `webidl2` compatibility. The inheritance chain is mixin-based:

```
WebGL2RenderingContext includes WebGLRenderingContextBase;      // WebGL1 methods+constants
WebGL2RenderingContext includes WebGL2RenderingContextBase;     // WebGL2 new methods+constants
WebGL2RenderingContext includes WebGL2RenderingContextOverloads; // Extended overloads
```

### GLSL Built-in Functions

ESSL 3.00 has **89 distinct built-in function names** across 9 categories. Of these:
- **~40 have distinctive GLSL-only names** (low false-positive risk for regex): all texture functions, derivatives, bit reinterpretation, pack/unpack, `smoothstep`, `inversesqrt`, `matrixCompMult`, `outerProduct`, etc.
- **~30+ collide with common JS identifiers** (`abs`, `min`, `max`, `length`, `distance`, `dot`, `log`, `sign`, `mix`, `step`, `floor`, `ceil`, `round`, `normalize`, `reflect`, `pow`, `sqrt`, `sin`, `cos`, `tan`, `not`, `all`, `any`, `equal`, `inverse`, `transpose`, `texture`).

The security-relevant functions (texture sampling, derivatives, bit reinterpretation, pack/unpack) are **almost entirely** in the distinctive-name set.

### Constant Role Analysis

57 semantic groups identified. Key findings:
- **Only ~29% of constants** (162 of 552) can be correctly classified from IDL parameter names alone.
- The parameter name `target` appears 73 times across unrelated methods (buffer, texture, framebuffer, renderbuffer, query, etc.).
- The parameter name `type` appears 32 times with different valid values per method.
- The parameter name `pname` appears 21 times across different getter methods.
- **~25% of constants** are return values or value-side enums with no IDL parameter trace.
- **Multi-membership is the norm**: `FLOAT` belongs to 4+ roles, `NONE` to 3+.
- **True orphans: <5 constants.**

---

### Task 1: Fix method/constant counts and IDL source URLs

**Files:**
- Modify: `docs/plans/2026-02-24-webgl-api-surface-extraction-design.md` (lines 5, 53-57, 61-65)

**Step 1: Fix intro paragraph (line 5)**

Replace:
```
We don't know which of the ~192 WebGL/WebGL2 methods, ~819 constants, or ~254 documented error conditions are actually exercised by the 367 seeds.
```

With:
```
We don't know which of the ~183 WebGL/WebGL2 method names (~293 signatures including overloads), ~361 core constants (plus ~80-100 extension constants), or ~254 documented error conditions are actually exercised by the 367 seeds.
```

**Step 2: Fix spec scale table (lines 53-57)**

Replace the entire table with:

```markdown
| Metric | WebGL 1.0 | WebGL 2.0 (new only) | Combined Core |
|--------|-----------|---------------------|---------------|
| Unique method names | ~95 | ~88 | ~183 |
| Method signatures (with overloads) | ~146 | ~147 | ~293 |
| const GLenum definitions | ~159 | ~202 | ~361 |
| Regular interfaces | 12 | 6 | 18 |
| Interface mixins (latest IDL) | 2 | 2 | 4 |
| Extension files in registry | — | — | ~57 |
```

**Step 3: Fix IDL source URLs (lines 60-65)**

Replace:
```markdown
Raw IDL files from Khronos registry (no HTML parsing needed):

- WebGL 1.0: `https://registry.khronos.org/webgl/specs/1.0.2/webgl.idl`
- WebGL 2.0: `https://registry.khronos.org/webgl/specs/2.0.0/webgl2.idl`
- Extensions: individual IDL/XML files from `https://registry.khronos.org/webgl/extensions/`
```

With:
```markdown
IDL sources from Khronos registry. Use the **latest** (not versioned) URLs for modern `interface mixin` / `includes` syntax that `webidl2` handles natively:

- WebGL 1.0: `https://registry.khronos.org/webgl/specs/latest/1.0/webgl.idl` (pure IDL, direct parse)
- WebGL 2.0: `https://registry.khronos.org/webgl/specs/latest/2.0/webgl2.idl` (pure IDL, direct parse)
- Extensions: `https://registry.khronos.org/webgl/extensions/{NAME}/extension.xml` (XML with embedded `<idl>` tags — requires XML extraction before `webidl2` parse)

**WebGL2 inheritance model:** `WebGL2RenderingContext` uses mixin includes (not classical inheritance):
- `WebGLRenderingContextBase` — all WebGL1 methods + constants
- `WebGL2RenderingContextBase` — all new WebGL2 methods + constants
- `WebGL2RenderingContextOverloads` — extended overloads of WebGL1 methods

The auditor must understand this: a seed calling `gl.bindTexture()` on a WebGL2 context exercises a WebGL1-origin method.
```

**Step 4: Run diff to verify changes**

Run: `git diff docs/plans/2026-02-24-webgl-api-surface-extraction-design.md`
Expected: Three hunks matching the edits above.

**Step 5: Commit**

```bash
git add docs/plans/2026-02-24-webgl-api-surface-extraction-design.md
git commit -m "fix: correct method/constant counts and IDL URLs from real spec data"
```

---

### Task 2: Fix extraction pipeline — XML parsing for extensions + extension methods in schema

**Files:**
- Modify: `docs/plans/2026-02-24-webgl-api-surface-extraction-design.md` (extraction process section ~lines 178-189, extensions section of JSON schema ~lines 151-157)

**Step 1: Add XML extraction step to the extraction process**

Replace the extraction process section:
```markdown
### Step 1: WebIDL fetching & parsing

The script `scripts/extract_webidl.js` manages local IDL files:
1. **Cache Check:** Checks `scripts/.idl_cache/*.idl`.
2. **Download:** If missing, downloads from Khronos registry (pinned versions) and saves locally.
3. **Parse:** Uses `webidl2` to transform IDLs into the structured JSON.

**Validation:**
- **Canary Check:** Script must fail if resulting JSON has <150 methods.
- **Role Assignment:** Every constant must have at least one entry in the `roles` array.
```

With:
```markdown
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
- **Role Assignment:** Every constant must have at least one entry in the `roles` array (see constant role mapping below).
- **Extension count:** Script must warn if fewer than 20 extensions were successfully parsed.
```

**Step 2: Add extension methods to the JSON schema**

Replace the extensions section in the JSON example:
```json
  "extensions": {
    "EXT_color_buffer_float": {
      "constants": {
        "R11F_G11F_B10F": {"value": "0x8C3A", "kind": "enum", "roles": ["format"]}
      }
    }
  },
```

With:
```json
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
```

**Step 3: Commit**

```bash
git add docs/plans/2026-02-24-webgl-api-surface-extraction-design.md
git commit -m "fix: add XML extraction for extensions and extension methods in schema"
```

---

### Task 3: Replace heuristic role detection with hybrid mapping approach

**Files:**
- Modify: `docs/plans/2026-02-24-webgl-api-surface-extraction-design.md` (constant role rules section ~lines 163-177)

**Step 1: Replace the constant role rules section**

Replace everything from `### Constant role rules` through the role table (lines 163-177) with:

```markdown
### Constant role mapping — hybrid approach

Constants are assigned to roles via a three-tier strategy. The extraction script applies these in order:

**Tier A — IDL parameter name derivation (~29% of constants, fully automatic):**

These parameter names are unique across the entire WebGL API and unambiguously identify the role:

| Parameter name(s) | Role | Example constants | Count |
|-------------------|------|-------------------|-------|
| `cap` | `capability` | `BLEND`, `DEPTH_TEST`, `SCISSOR_TEST` | 10 |
| `usage` | `buffer_usage` | `STATIC_DRAW`, `DYNAMIC_COPY` | 9 |
| `func` | `comparison_func` | `LESS`, `GEQUAL`, `ALWAYS` | 8 |
| `face` | `face_mode` | `FRONT`, `BACK`, `FRONT_AND_BACK` | 3 |
| `fail`, `zfail`, `zpass` | `stencil_op` | `KEEP`, `REPLACE`, `INCR_WRAP` | 8 |
| `sfactor`, `dfactor`, `srcRGB`, `dstRGB`, `srcAlpha`, `dstAlpha` | `blend_factor` | `SRC_ALPHA`, `ONE_MINUS_SRC_ALPHA` | 15 |
| `modeRGB`, `modeAlpha` | `blend_equation` | `FUNC_ADD`, `FUNC_SUBTRACT`, `MIN` | 5 |
| `attachment`, `attachments` | `framebuffer_attachment` | `COLOR_ATTACHMENT0`, `DEPTH_ATTACHMENT` | 19 |
| `internalformat`, `sizedFormat` | `internalformat` | `RGBA8`, `R32F`, `DEPTH24_STENCIL8` | ~55 |
| `format` | `format` | `RGBA`, `RED_INTEGER`, `DEPTH_STENCIL` | 13 |
| `filter` | `blit_filter` | `NEAREST`, `LINEAR` | 2 |
| `bufferMode` | `tf_mode` | `INTERLEAVED_ATTRIBS`, `SEPARATE_ATTRIBS` | 2 |
| `condition` | `sync_condition` | `SYNC_GPU_COMMANDS_COMPLETE` | 1 |
| `precisiontype` | `shader_precision_type` | `HIGH_FLOAT`, `MEDIUM_INT` | 6 |

**Tier B — Prefix/suffix heuristics (~6% of constants, automatic with validation):**

| Pattern | Role | Count |
|---------|------|-------|
| `_BIT` suffix + power-of-two value | `clear_buffer_bit` | 4 |
| `FRAMEBUFFER_ATTACHMENT_` prefix | `fb_attachment_parameter` | 13 |
| `RENDERBUFFER_` prefix | `renderbuffer_parameter` | 10 |
| `UNIFORM_BLOCK_` or `UNIFORM_` prefix (in UBO context) | `uniform_block_parameter` | 13 |
| `VERTEX_ATTRIB_` prefix | `vertex_attrib_parameter` | 10 |
| `COMPRESSED_` prefix | `compressed_format` | ~22 |
| `_EXT`, `_OES`, `_WEBGL`, `_ANGLE` suffix | `extension_specific` | ~18 |
| `INVALID_` prefix or `NO_ERROR` | `error_code` | 7 |

**Tier C — Hardcoded mapping table (~65% of constants, committed JSON file):**

The remaining constants require a mapping table because:
- The parameter name `target` appears 73 times across unrelated methods (buffer, texture, framebuffer, renderbuffer, query, etc.)
- The parameter name `type` appears 32 times with different valid values per method
- The parameter name `pname` appears 21 times across different getter methods
- ~25% of constants are return values (error codes, framebuffer status, sync status, uniform types) with no parameter trace
- ~5% are value-side enums (filter values, wrap modes, compare modes) passed as generic `param` arguments

The mapping table is maintained as a section of `webgl_api_surface.json` and covers roles including: `draw_mode`, `buffer_target`, `texture_target`, `texture_parameter_name`, `texture_filter_value`, `texture_wrap_value`, `pixel_type`, `data_type`, `index_type`, `shader_type`, `front_face_direction`, `hint_target`, `hint_mode`, `framebuffer_target`, `framebuffer_status`, `renderbuffer_target`, `pixel_store_parameter`, `query_target`, `tf_target`, `uniform_type`, `program_parameter`, `shader_parameter`, `sync_status`, `sync_parameter`, `get_parameter`, `buffer_clear_target`, `draw_buffer_index`, `texture_unit`, `buffer_parameter`, `query_object_parameter`, `component_type`, `texture_compare_mode_value`, `fb_attachment_object_type`, `color_encoding_value`.

The initial table is generated from IDL comments (e.g., `/* BeginMode */`, `/* BlendingFactorDest */`) cross-referenced with MDN documentation, then committed and maintained manually. Constants can belong to multiple roles (e.g., `FLOAT` is in `pixel_type`, `data_type`, `uniform_type`, and `component_type`).

**Orphan policy:** After all three tiers, fewer than 5 constants should remain unassigned. Any unassigned constant is logged as a warning during extraction.
```

**Step 2: Commit**

```bash
git add docs/plans/2026-02-24-webgl-api-surface-extraction-design.md
git commit -m "fix: replace heuristic role detection with hybrid mapping approach"
```

---

### Task 4: Scope GLSL analysis to distinctive names only

**Files:**
- Modify: `docs/plans/2026-02-24-webgl-api-surface-extraction-design.md` (glsl_builtins in JSON schema ~line 159, shader extraction in audit pipeline ~line 216, Tier 3 description ~line 224)

**Step 1: Replace glsl_builtins in JSON schema**

Replace:
```json
  "glsl_builtins": ["texture", "texelFetch", "dFdx", "mix"]
```

With:
```json
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
```

**Note:** This is ~52 functions (of 89 total in ESSL 3.00). The ~37 omitted functions (`abs`, `min`, `max`, `length`, `distance`, `dot`, `log`, `sign`, `mix`, `step`, `floor`, `ceil`, `round`, `normalize`, `reflect`, `pow`, `sqrt`, `sin`, `cos`, `tan`, `exp`, `exp2`, `log2`, `cross`, `clamp`, `mod`, `not`, `all`, `any`, `equal`, etc.) are excluded because their names collide with common JS identifiers, making regex matching unreliable. The omitted functions are predominantly math primitives — if a shader uses `texelFetch` or `dFdx`, it almost certainly also uses `sin`/`cos`/`mix`, so coverage of the distinctive set is a reliable proxy for overall shader complexity.

**Step 2: Update shader extraction description in audit pipeline**

Replace line 216:
```markdown
6. **Shader extraction:** Find string arguments to `shaderSource()`, regex-match against `glsl_builtins`.
```

With:
```markdown
6. **Shader extraction:** Extract string content passed to `shaderSource()` calls (including template literals and string concatenation where one operand is a string literal). Within extracted shader source only (not surrounding JS), regex-match `\b(functionName)\s*\(` against the `glsl_builtins` lists. Only the ~56 distinctive GLSL names are checked — common math names (`abs`, `min`, `max`, `length`, `dot`, `log`, etc.) are excluded due to collision with JS identifiers. This covers all security-relevant shader functions (texture sampling, derivatives, bit reinterpretation, pack/unpack).
```

**Step 3: Update Tier 3 description**

Replace the Tier 3 row in the confidence tiers table:
```markdown
| **3 - Needs analysis** | Ambiguous overload (remaining) or GLSL built-in missing. | ~75% | Agent reads relevant seeds before deciding. |
```

With:
```markdown
| **3 - Needs analysis** | Ambiguous overload (remaining after disambiguation) or distinctive GLSL built-in missing from all shader sources. | ~75% | Agent reads relevant seeds before deciding. |
```

**Step 4: Commit**

```bash
git add docs/plans/2026-02-24-webgl-api-surface-extraction-design.md
git commit -m "fix: scope GLSL analysis to 56 distinctive names, exclude JS-colliding names"
```

---

### Task 5: Fix texImage2D overload example in JSON schema

**Files:**
- Modify: `docs/plans/2026-02-24-webgl-api-surface-extraction-design.md` (JSON schema example, lines 119-149)

**Step 1: Replace the texImage2D example with a realistic one**

The current example shows two 6-arity overloads, which doesn't match the real spec. Replace the `methods` section of the JSON example:

```json
  "methods": {
    "texImage2D": {
      "webgl_version": 1,
      "overloads": [
        {
          "arity": 6,
          "ambiguous_arity": true,
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
          "arity": 6,
          "ambiguous_arity": true,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "level", "type": "GLint"},
            {"name": "internalformat", "type": "GLenum"},
            {"name": "width", "type": "GLsizei"},
            {"name": "height", "type": "GLsizei"},
            {"name": "source", "type": "TexImageSource"}
          ]
        }
      ]
    }
  },
```

With a more representative example showing real arity differences:

```json
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
```

Also move `ambiguous_arity` to the method level (not per-overload), since it describes the relationship between overloads.

**Step 2: Update the overload disambiguation description**

Replace lines 211-214:
```markdown
   - **Overload resolution:** For `ambiguous_arity` methods (like `texImage2D:6`), inspect argument types:
     - If argument 5 is a `Literal (Number)`, resolve to the `width/height` signature.
     - If argument 5 is an `Identifier` (e.g., `img`), resolve to the `TexImageSource` signature.
     - Moves these gaps from Tier 3 (Ambiguous) to Tier 2 (High confidence).
```

With:
```markdown
   - **Overload resolution:** Most methods have overloads with different arities — these are trivially distinguished by argument count. For `ambiguous_arity` methods (same arity, different parameter types, e.g., `bufferData:3` with size vs. srcData), inspect argument AST node types:
     - `Literal (Number)` or `BinaryExpression` → numeric parameter (e.g., `size`)
     - `Identifier` resolving to a known typed variable → typed parameter (e.g., `srcData`)
     - Unresolvable → remains Tier 3.
     - This moves some gaps from Tier 3 (Ambiguous) to Tier 2 (High confidence), but deep dataflow cases stay in Tier 3.
```

**Step 3: Commit**

```bash
git add docs/plans/2026-02-24-webgl-api-surface-extraction-design.md
git commit -m "fix: realistic overload examples and method-level ambiguous_arity flag"
```

---

### Task 6: Update canary thresholds and Phase 2 trigger criteria

**Files:**
- Modify: `docs/plans/2026-02-24-webgl-api-surface-extraction-design.md` (validation section, Phase 2 criteria)

**Step 1: Update canary check (already done in Task 2, verify)**

Ensure the canary check says `<150 unique method names or <300 constants` (matching the real counts of ~183 methods and ~361 constants).

**Step 2: Update Phase 2 trigger criteria**

Replace:
```markdown
## Phase 2 trigger criteria

Proceed to Phase 2 when:
- Tier 1 gaps (missing methods) < 5%.
- Tier 2 gaps (missing constants) < 15% per role.
- Remaining gaps are predominantly combinatorial (Phase 2's focus).
```

With:
```markdown
## Phase 2 trigger criteria

Proceed to Phase 2 when:
- Tier 1 gaps (missing methods) < 5% (~9 or fewer of ~183 method names uncovered).
- Tier 2 gaps (missing constants) < 15% per role (across all 57 role groups).
- GLSL built-in coverage > 80% of the 56 distinctive functions.
- Remaining gaps are predominantly combinatorial (Phase 2's focus).
```

**Step 3: Commit**

```bash
git add docs/plans/2026-02-24-webgl-api-surface-extraction-design.md
git commit -m "fix: update thresholds with verified counts"
```
