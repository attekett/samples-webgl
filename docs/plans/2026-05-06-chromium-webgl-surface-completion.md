# Chromium WebGL Surface Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `docs/webgl_api_surface.json` to parity with Chromium's WebGL IDL surface by adding the 28 extensions and 1 method (`makeXRCompatible`) currently missing from the project's surface but exposed by Chromium.

**Architecture:** Snapshot the 28 missing Chromium extension IDL files into `scripts/.idl_cache/extensions/` so the project owns reproducible source data. Add a parity test (`test_chromium_parity.py`) that parses each cached IDL and asserts the extension exists in `webgl_api_surface.json` with matching hex constants. Per-tier task adds entries to the `EXTENSIONS` block in `scripts/extract_webidl.js`, regenerates the surface JSON, and runs the test until it passes.

**Tech Stack:** Node.js (`webidl2` for the existing extractor), Python 3 (pytest for parity validation), regex-based IDL parsing in the validator (the IDL files are small and grammatically simple).

---

## Why this is needed

Validation against `~/git/chromium/src/third_party/blink/renderer/modules/webgl/*.idl` showed:

- **Methods**: 225/225 in project surface match Chromium. ✅ Plus 1 missing: `makeXRCompatible()` (gated `[RuntimeEnabled=WebXR]`, returns `Promise<undefined>`).
- **Extensions**: project has 28, Chromium ships 55. **27 extensions** present in Chromium are not tracked.

The pipeline correctly reports "225/225 methods covered" but the input surface JSON is incomplete — the audit pipeline can't generate seeds or report gaps for extensions it doesn't know exist.

This plan closes that gap by hand-transcribing 28 missing extensions from Chromium IDLs into `scripts/extract_webidl.js`'s `EXTENSIONS` block (currently 28 entries, growing to 56), then regenerating `webgl_api_surface.json`. Note: the count of 28 missing extensions reconciles vs the audit's 27-tier breakdown: `EXT_disjoint_timer_query` (WebGL1) is added as one entry, distinct from the existing `EXT_disjoint_timer_query_webgl2`.

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `scripts/.idl_cache/extensions/` | Create dir | Snapshot location for 28 Chromium extension IDLs |
| `scripts/.idl_cache/extensions/*.idl` | Create (28 files) | Frozen copies of `~/git/chromium/src/third_party/blink/renderer/modules/webgl/<name>.idl` for the 28 missing extensions |
| `scripts/api_audit/tests/test_chromium_parity.py` | Create | Parity test: assert each cached IDL's constants appear in `webgl_api_surface.json` with matching hex values |
| `scripts/extract_webidl.js` | Modify (lines 596-870, the `EXTENSIONS` block) | Add 28 new extension entries plus 1 method augmentation for `makeXRCompatible` |
| `docs/webgl_api_surface.json` | Regenerate (auto) | Output of `node scripts/extract_webidl.js`; not hand-edited |

No new top-level scripts. The existing extractor flow (`node scripts/extract_webidl.js`) is preserved — we extend its hardcoded data, not its logic.

---

## The 28 missing extensions

| Tier | Extension | Chromium IDL filename |
|---|---|---|
| **Tier 1** (7, high fuzzing value) | | |
| 1 | `ANGLE_instanced_arrays` | `angle_instanced_arrays.idl` |
| 2 | `EXT_disjoint_timer_query` | `ext_disjoint_timer_query.idl` |
| 3 | `EXT_frag_depth` | `ext_frag_depth.idl` |
| 4 | `EXT_blend_minmax` | `ext_blend_min_max.idl` |
| 5 | `WEBGL_compressed_texture_astc` | `webgl_compressed_texture_astc.idl` |
| 6 | `WEBGL_compressed_texture_etc1` | `webgl_compressed_texture_etc1.idl` |
| 7 | `WEBGL_compressed_texture_pvrtc` | `webgl_compressed_texture_pvrtc.idl` |
| **Tier 2 EXT-prefix** (8) | | |
| 8 | `EXT_clip_control` | `ext_clip_control.idl` |
| 9 | `EXT_depth_clamp` | `ext_depth_clamp.idl` |
| 10 | `EXT_polygon_offset_clamp` | `ext_polygon_offset_clamp.idl` |
| 11 | `EXT_render_snorm` | `ext_render_snorm.idl` |
| 12 | `EXT_texture_compression_bptc` | `ext_texture_compression_bptc.idl` |
| 13 | `EXT_texture_compression_rgtc` | `ext_texture_compression_rgtc.idl` |
| 14 | `EXT_texture_mirror_clamp_to_edge` | `ext_texture_mirror_clamp_to_edge.idl` |
| 15 | `EXT_conservative_depth` | `ext_conservative_depth.idl` |
| **Tier 2 WEBGL-prefix** (9) | | |
| 16 | `WEBGL_blend_func_extended` | `webgl_blend_func_extended.idl` |
| 17 | `WEBGL_clip_cull_distance` | `webgl_clip_cull_distance.idl` |
| 18 | `WEBGL_draw_instanced_base_vertex_base_instance` | `webgl_draw_instanced_base_vertex_base_instance.idl` |
| 19 | `WEBGL_multi_draw_instanced_base_vertex_base_instance` | `webgl_multi_draw_instanced_base_vertex_base_instance.idl` |
| 20 | `WEBGL_polygon_mode` | `webgl_polygon_mode.idl` |
| 21 | `WEBGL_provoking_vertex` | `webgl_provoking_vertex.idl` |
| 22 | `WEBGL_render_shared_exponent` | `webgl_render_shared_exponent.idl` |
| 23 | `WEBGL_shader_pixel_local_storage` | `webgl_shader_pixel_local_storage.idl` |
| 24 | `WEBGL_stencil_texturing` | `webgl_stencil_texturing.idl` |
| **Tier 3** (4, niche / vendor) | | |
| 25 | `OVR_multiview2` | `ovr_multiview_2.idl` |
| 26 | `OES_sample_variables` | `oes_sample_variables.idl` |
| 27 | `OES_shader_multisample_interpolation` | `oes_shader_multisample_interpolation.idl` |
| 28 | `NV_shader_noperspective_interpolation` | `nv_shader_noperspective_interpolation.idl` |

---

## EXTENSIONS schema reference

The `EXTENSIONS` block in `scripts/extract_webidl.js` is a hardcoded JS object literal. Each entry has this shape:

```javascript
'EXTENSION_NAME_AS_USED_IN_getExtension()': {
    methods: {
        'extensionMethodName': {
            overloads: [
                { arity: N, params: [
                    { name: 'paramName', type: 'GLenum' },
                    // ...
                ] }
            ]
        }
    },
    constants: {
        'CONSTANT_NAME_AS_DEFINED': {
            value: '0xHEX',
            kind: 'enum',
            roles: ['role_tag']  // see role glossary below
        }
    }
}
```

**Existing example** — `OES_vertex_array_object` from `extract_webidl.js:597-606`:

```javascript
'OES_vertex_array_object': {
    methods: {
      'createVertexArrayOES': { overloads: [{ arity: 0, params: [] }] },
      'deleteVertexArrayOES': { overloads: [{ arity: 1, params: [{ name: 'arrayObject', type: 'WebGLVertexArrayObjectOES?' }] }] },
      'isVertexArrayOES': { overloads: [{ arity: 1, params: [{ name: 'arrayObject', type: 'WebGLVertexArrayObjectOES?' }] }] },
      'bindVertexArrayOES': { overloads: [{ arity: 1, params: [{ name: 'arrayObject', type: 'WebGLVertexArrayObjectOES?' }] }] }
    },
    constants: {
      'VERTEX_ARRAY_BINDING_OES': { value: '0x85B5', kind: 'enum', roles: ['get_parameter'] }
    }
}
```

### Role tag glossary (project conventions)

Pulled from existing entries in `extract_webidl.js`. Pick the closest match per constant:

| Role | Use for | Example constants |
|---|---|---|
| `get_parameter` | Argument to `gl.getParameter()` | `VERTEX_ARRAY_BINDING_OES`, `MAX_DRAW_BUFFERS` |
| `pixel_type` | Pixel type argument to `texImage2D` etc. | `HALF_FLOAT_OES`, `UNSIGNED_INT_24_8_WEBGL` |
| `compressed_format` | Compressed-texture internal format | `COMPRESSED_RGBA_S3TC_DXT5_EXT` |
| `sized_internalformat` | Sized internal texture format | `R16_EXT`, `RGBA16_EXT` |
| `color_attachment` | FBO color-attachment enum | `COLOR_ATTACHMENT0_WEBGL`..`15_WEBGL` |
| `texture_filter` | Texture min/mag filter values | `TEXTURE_MAX_ANISOTROPY_EXT` |
| `texture_parameter` | `texParameter` pname | `TEXTURE_BASE_LEVEL_OES` |
| `texture_target` | `bindTexture` target enum | `TEXTURE_2D_ARRAY_EXT` |
| `blend_equation` | `blendEquation` value | `MIN_EXT`, `MAX_EXT` |
| `blend_factor` | `blendFunc` factor | `SRC1_COLOR_WEBGL` |
| `hint_target` | `gl.hint()` target | `FRAGMENT_SHADER_DERIVATIVE_HINT_OES` |
| `hint_mode` | `gl.hint()` mode | `FASTEST`, `NICEST` |
| `capability` | `gl.enable/disable` capability | `DEPTH_CLAMP_EXT`, `POLYGON_OFFSET_LINE_NV` |
| `shader_parameter` | `gl.getProgramParameter` pname | `COMPLETION_STATUS_KHR` |
| `query_target` | `gl.beginQuery` target | `TIME_ELAPSED_EXT`, `TIMESTAMP_EXT` |
| `query_object_parameter` | `gl.getQueryObjectParameter` pname | `QUERY_RESULT_AVAILABLE_EXT` |
| `polygon_mode` | `gl.polygonMode` value | `LINE_WEBGL`, `FILL_WEBGL` |
| `provoking_vertex_mode` | `gl.provokingVertex` value | `FIRST_VERTEX_CONVENTION_WEBGL` |
| `webgl_specific` | None of the above; WebGL-only enum without obvious role | (last-resort fallback) |

When in doubt, pick the role used by an analogous constant in an existing entry (e.g., `OES_texture_half_float`'s `HALF_FLOAT_OES` uses `pixel_type` → other half-float pixel-type constants should also use `pixel_type`).

---

## Test command

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/ -v
```

Targeted parity test (added in Task 2):

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/test_chromium_parity.py -v
```

Regenerate the surface after editing `extract_webidl.js`:

```bash
cd /home/attekett/git/samples-webgl/scripts && node extract_webidl.js
```

---

## Task 1: Snapshot the 28 Chromium extension IDLs into `.idl_cache/extensions/`

**Files:**
- Create: `scripts/.idl_cache/extensions/` (directory)
- Create: 28 IDL files copied verbatim from Chromium

- [ ] **Step 1: Create the snapshot directory and copy the IDLs**

```bash
set -e   # abort on any cp failure — partial commit would silently break Task 2
cd /home/attekett/git/samples-webgl
mkdir -p scripts/.idl_cache/extensions

CHROMIUM_DIR="$HOME/git/chromium/src/third_party/blink/renderer/modules/webgl"
for f in \
  angle_instanced_arrays \
  ext_disjoint_timer_query \
  ext_frag_depth \
  ext_blend_min_max \
  webgl_compressed_texture_astc \
  webgl_compressed_texture_etc1 \
  webgl_compressed_texture_pvrtc \
  ext_clip_control \
  ext_depth_clamp \
  ext_polygon_offset_clamp \
  ext_render_snorm \
  ext_texture_compression_bptc \
  ext_texture_compression_rgtc \
  ext_texture_mirror_clamp_to_edge \
  ext_conservative_depth \
  webgl_blend_func_extended \
  webgl_clip_cull_distance \
  webgl_draw_instanced_base_vertex_base_instance \
  webgl_multi_draw_instanced_base_vertex_base_instance \
  webgl_polygon_mode \
  webgl_provoking_vertex \
  webgl_render_shared_exponent \
  webgl_shader_pixel_local_storage \
  webgl_stencil_texturing \
  ovr_multiview_2 \
  oes_sample_variables \
  oes_shader_multisample_interpolation \
  nv_shader_noperspective_interpolation; do
  cp "$CHROMIUM_DIR/$f.idl" "scripts/.idl_cache/extensions/$f.idl"
done

ls scripts/.idl_cache/extensions/ | wc -l   # Expected: 28
```

- [ ] **Step 2: Verify all 28 files copied successfully**

```bash
ls /home/attekett/git/samples-webgl/scripts/.idl_cache/extensions/*.idl | wc -l
```

Expected output: `28`

- [ ] **Step 3: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/.idl_cache/extensions/
git commit -m "chore: snapshot 28 missing Chromium WebGL extension IDLs"
```

---

## Task 2: Add the parity test (initially all 28 should fail)

**Files:**
- Create: `scripts/api_audit/tests/test_chromium_parity.py`

The test parses each cached extension IDL with regex (the files are simple) to extract `interface` name, `const` declarations, and method signatures, then asserts that each appears in `docs/webgl_api_surface.json`.

- [ ] **Step 1: Write the test file**

Create `scripts/api_audit/tests/test_chromium_parity.py`:

```python
"""Parity test: webgl_api_surface.json must match the snapshotted Chromium IDLs.

For each .idl in scripts/.idl_cache/extensions/, extracts the interface name,
constants (with hex values), and methods, then asserts the project's surface
JSON has a matching extension entry.
"""
import json
import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXTENSIONS_DIR = PROJECT_ROOT / "scripts" / ".idl_cache" / "extensions"
SURFACE_PATH = PROJECT_ROOT / "docs" / "webgl_api_surface.json"


# Map IDL filename → expected getExtension() name (the surface key).
# This is hand-curated because IDL filenames don't always match getExtension
# names (e.g. ext_blend_min_max.idl → EXT_blend_minmax).
IDL_TO_EXT_NAME = {
    "angle_instanced_arrays": "ANGLE_instanced_arrays",
    "ext_disjoint_timer_query": "EXT_disjoint_timer_query",
    "ext_frag_depth": "EXT_frag_depth",
    "ext_blend_min_max": "EXT_blend_minmax",
    "webgl_compressed_texture_astc": "WEBGL_compressed_texture_astc",
    "webgl_compressed_texture_etc1": "WEBGL_compressed_texture_etc1",
    "webgl_compressed_texture_pvrtc": "WEBGL_compressed_texture_pvrtc",
    "ext_clip_control": "EXT_clip_control",
    "ext_depth_clamp": "EXT_depth_clamp",
    "ext_polygon_offset_clamp": "EXT_polygon_offset_clamp",
    "ext_render_snorm": "EXT_render_snorm",
    "ext_texture_compression_bptc": "EXT_texture_compression_bptc",
    "ext_texture_compression_rgtc": "EXT_texture_compression_rgtc",
    "ext_texture_mirror_clamp_to_edge": "EXT_texture_mirror_clamp_to_edge",
    "ext_conservative_depth": "EXT_conservative_depth",
    "webgl_blend_func_extended": "WEBGL_blend_func_extended",
    "webgl_clip_cull_distance": "WEBGL_clip_cull_distance",
    "webgl_draw_instanced_base_vertex_base_instance": "WEBGL_draw_instanced_base_vertex_base_instance",
    "webgl_multi_draw_instanced_base_vertex_base_instance": "WEBGL_multi_draw_instanced_base_vertex_base_instance",
    "webgl_polygon_mode": "WEBGL_polygon_mode",
    "webgl_provoking_vertex": "WEBGL_provoking_vertex",
    "webgl_render_shared_exponent": "WEBGL_render_shared_exponent",
    "webgl_shader_pixel_local_storage": "WEBGL_shader_pixel_local_storage",
    "webgl_stencil_texturing": "WEBGL_stencil_texturing",
    "ovr_multiview_2": "OVR_multiview2",
    "oes_sample_variables": "OES_sample_variables",
    "oes_shader_multisample_interpolation": "OES_shader_multisample_interpolation",
    "nv_shader_noperspective_interpolation": "NV_shader_noperspective_interpolation",
}


CONST_RE = re.compile(
    r'const\s+(?:unsigned\s+)?\w+\s+(\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*;'
)
# Broad type-token match: handles `const long`, `const unsigned long`,
# `const GLenum`, `const GLbitfield`, `const GLuint`, etc. Without this,
# Chromium IDLs that use `const GLenum NAME = 0xHEX;` (e.g.
# ext_disjoint_timer_query.idl, ovr_multiview_2.idl) would yield zero
# constants and the parity test would silently pass.
# Match method declarations: optional [extattr] return-type name(...)
METHOD_RE = re.compile(
    r'^\s*(?:\[[^\]]+\]\s+)?'        # optional [ext-attr]
    r'(?:[\w<>\?]+\s+)+?'             # return type
    r'(\w+)\s*\(',                    # method name + '('
    re.MULTILINE,
)


def parse_idl(idl_path):
    """Extract constants and method names from an extension IDL file."""
    text = idl_path.read_text()
    # Strip block + line comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//.*', '', text)

    constants = {}
    for m in CONST_RE.finditer(text):
        name, value = m.group(1), m.group(2)
        constants[name] = value.lower()

    methods = set()
    for m in METHOD_RE.finditer(text):
        name = m.group(1)
        # Filter out IDL keywords that look like method names
        if name in {"interface", "typedef", "dictionary", "enum",
                    "DOMString", "void", "undefined", "boolean", "long", "any",
                    "Promise", "sequence", "object", "Element",
                    "GLenum", "GLbitfield", "GLuint", "GLint", "GLfloat",
                    "GLboolean", "GLsizei", "GLintptr", "GLsizeiptr"}:
            continue
        methods.add(name)
    return constants, methods


@pytest.fixture(scope="module")
def surface():
    return json.loads(SURFACE_PATH.read_text())


@pytest.mark.parametrize("idl_stem,ext_name", sorted(IDL_TO_EXT_NAME.items()))
def test_extension_present(surface, idl_stem, ext_name):
    """Every snapshotted extension IDL must have a matching entry in surface JSON."""
    assert ext_name in surface["extensions"], (
        f"Extension {ext_name} (from {idl_stem}.idl) not found in webgl_api_surface.json"
    )


@pytest.mark.parametrize("idl_stem,ext_name", sorted(IDL_TO_EXT_NAME.items()))
def test_extension_constants_match(surface, idl_stem, ext_name):
    """Extension's constants must match the IDL exactly (name + hex value)."""
    if ext_name not in surface["extensions"]:
        pytest.skip(f"Extension {ext_name} not yet added — see test_extension_present")

    idl_path = EXTENSIONS_DIR / f"{idl_stem}.idl"
    chromium_consts, _ = parse_idl(idl_path)
    project_consts = surface["extensions"][ext_name].get("constants", {})

    for const_name, expected_hex in chromium_consts.items():
        assert const_name in project_consts, (
            f"{ext_name}: constant {const_name} missing"
        )
        actual = project_consts[const_name]["value"].lower()
        assert actual == expected_hex, (
            f"{ext_name}.{const_name}: expected {expected_hex}, got {actual}"
        )


@pytest.mark.parametrize("idl_stem,ext_name", sorted(IDL_TO_EXT_NAME.items()))
def test_extension_methods_present(surface, idl_stem, ext_name):
    """Extension's methods must all appear (signatures not strictly checked)."""
    if ext_name not in surface["extensions"]:
        pytest.skip(f"Extension {ext_name} not yet added")

    idl_path = EXTENSIONS_DIR / f"{idl_stem}.idl"
    _, chromium_methods = parse_idl(idl_path)
    project_methods = set(
        surface["extensions"][ext_name].get("methods", {}).keys()
    )

    for method_name in chromium_methods:
        assert method_name in project_methods, (
            f"{ext_name}: method {method_name} missing from surface"
        )
```

- [ ] **Step 2: Run the test — expect 28 failures (one per missing extension)**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/test_chromium_parity.py -v 2>&1 | tail -40
```

Expected: 28 `test_extension_present` failures (one parameterized test per IDL). The other two tests skip because of the `pytest.skip` guard.

- [ ] **Step 3: Commit the failing tests**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/api_audit/tests/test_chromium_parity.py
git commit -m "test: add Chromium WebGL extension parity tests (28 currently failing)"
```

---

## Task 3: Add Tier 1 extensions (7) — high fuzzing value

**Files:**
- Modify: `scripts/extract_webidl.js` (the `EXTENSIONS` block, lines 596-870)
- Regenerate: `docs/webgl_api_surface.json` (auto via `node extract_webidl.js`)

### Tier 1 extensions to add

For each, read the IDL at `scripts/.idl_cache/extensions/<filename>` and transcribe into the `EXTENSIONS` block. Place new entries in alphabetical order within the existing block, OR append at the end before the closing `};` — either is fine; downstream consumers don't care about ordering.

| getExtension name | IDL filename |
|---|---|
| `ANGLE_instanced_arrays` | `angle_instanced_arrays.idl` |
| `EXT_disjoint_timer_query` | `ext_disjoint_timer_query.idl` |
| `EXT_frag_depth` | `ext_frag_depth.idl` |
| `EXT_blend_minmax` | `ext_blend_min_max.idl` |
| `WEBGL_compressed_texture_astc` | `webgl_compressed_texture_astc.idl` |
| `WEBGL_compressed_texture_etc1` | `webgl_compressed_texture_etc1.idl` |
| `WEBGL_compressed_texture_pvrtc` | `webgl_compressed_texture_pvrtc.idl` |

### Worked example: `ANGLE_instanced_arrays`

`scripts/.idl_cache/extensions/angle_instanced_arrays.idl` content (simplified):

```idl
[ LegacyNoInterfaceObject ] interface ANGLEInstancedArrays {
    const unsigned long VERTEX_ATTRIB_ARRAY_DIVISOR_ANGLE = 0x88FE;

    void drawArraysInstancedANGLE(unsigned long mode, long first, long count, long primcount);
    void drawElementsInstancedANGLE(unsigned long mode, long count, unsigned long type, long long offset, long primcount);
    void vertexAttribDivisorANGLE(unsigned long index, long divisor);
};
```

Add this entry to `EXTENSIONS` in `scripts/extract_webidl.js`:

```javascript
'ANGLE_instanced_arrays': {
    methods: {
      'drawArraysInstancedANGLE': { overloads: [{ arity: 4, params: [
        { name: 'mode', type: 'GLenum' },
        { name: 'first', type: 'GLint' },
        { name: 'count', type: 'GLsizei' },
        { name: 'primcount', type: 'GLsizei' }
      ] }] },
      'drawElementsInstancedANGLE': { overloads: [{ arity: 5, params: [
        { name: 'mode', type: 'GLenum' },
        { name: 'count', type: 'GLsizei' },
        { name: 'type', type: 'GLenum' },
        { name: 'offset', type: 'GLintptr' },
        { name: 'primcount', type: 'GLsizei' }
      ] }] },
      'vertexAttribDivisorANGLE': { overloads: [{ arity: 2, params: [
        { name: 'index', type: 'GLuint' },
        { name: 'divisor', type: 'GLuint' }
      ] }] }
    },
    constants: {
      'VERTEX_ATTRIB_ARRAY_DIVISOR_ANGLE': { value: '0x88FE', kind: 'enum', roles: ['get_parameter'] }
    }
}
```

Type mapping: `unsigned long` → `GLenum` (when target/mode-like) or `GLuint` (when count-like); `long` → `GLint`; `long long` → `GLintptr` for byte offsets; `boolean` → `GLboolean`; etc. Match the convention used by existing entries.

### Steps

- [ ] **Step 1: Read each Tier 1 IDL file**

```bash
cd /home/attekett/git/samples-webgl
for f in angle_instanced_arrays ext_disjoint_timer_query ext_frag_depth ext_blend_min_max webgl_compressed_texture_astc webgl_compressed_texture_etc1 webgl_compressed_texture_pvrtc; do
  echo "=== $f.idl ==="
  cat scripts/.idl_cache/extensions/$f.idl
done
```

For each: extract the `interface` block, identify `const ... = 0x...;` lines (constants) and method declarations.

- [ ] **Step 2: Insert 7 new entries into `EXTENSIONS` in `scripts/extract_webidl.js`**

Append entries at the end of the `EXTENSIONS = { ... }` block (just before the closing `};` at approximately line 870). Use the pattern shown above. Ensure correct hex values, method names, and parameter types.

For role-tag picks:
- `VERTEX_ATTRIB_ARRAY_DIVISOR_ANGLE` → `get_parameter`
- `EXT_disjoint_timer_query` constants like `QUERY_COUNTER_BITS_EXT`, `CURRENT_QUERY_EXT` → `get_parameter`; `QUERY_RESULT_EXT`, `QUERY_RESULT_AVAILABLE_EXT` → `query_object_parameter`; `TIME_ELAPSED_EXT`, `TIMESTAMP_EXT` → `query_target`; `GPU_DISJOINT_EXT` → `get_parameter`
- `EXT_frag_depth` has no constants — methods only (well actually it has no methods either; it's a flag-only extension that enables `gl_FragDepth` in shaders. Use `methods: {}, constants: {}`)
- `EXT_blend_minmax` constants `MIN_EXT`, `MAX_EXT` → `blend_equation`
- ASTC compressed format constants → `compressed_format`
- ETC1 `COMPRESSED_RGB_ETC1_WEBGL` → `compressed_format`
- PVRTC compressed formats → `compressed_format`

- [ ] **Step 3: Regenerate the surface JSON**

```bash
cd /home/attekett/git/samples-webgl/scripts && node extract_webidl.js 2>&1 | tail -20
```

Expected: completes without errors. Output mentions `Extensions: 35` (28 existing + 7 new).

- [ ] **Step 4: Run the parity test for Tier 1**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/test_chromium_parity.py -v 2>&1 | tail -30
```

Expected: 7 of 28 `test_extension_present` tests now pass (the Tier 1 ones), plus their `test_extension_constants_match` and `test_extension_methods_present` parameterized variants.

- [ ] **Step 5: Run the full audit suite — confirm no regression**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/ -q 2>&1 | tail -5
```

Expected: all prior 150 tests pass + the parity-test deltas. Some `test_chromium_parity` tests still fail (Tiers 2/3), which is expected.

- [ ] **Step 6: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/extract_webidl.js docs/webgl_api_surface.json
git commit -m "feat(surface): add Tier 1 missing Chromium WebGL extensions

Adds ANGLE_instanced_arrays, EXT_disjoint_timer_query, EXT_frag_depth,
EXT_blend_minmax, and three compressed-texture extensions (ASTC, ETC1,
PVRTC). Brings extension count from 28 to 35."
```

---

## Task 4: Add Tier 2 EXT-prefix extensions (8)

**Files:**
- Modify: `scripts/extract_webidl.js` (`EXTENSIONS` block)
- Regenerate: `docs/webgl_api_surface.json`

### Tier 2 EXT extensions to add

| getExtension name | IDL filename |
|---|---|
| `EXT_clip_control` | `ext_clip_control.idl` |
| `EXT_depth_clamp` | `ext_depth_clamp.idl` |
| `EXT_polygon_offset_clamp` | `ext_polygon_offset_clamp.idl` |
| `EXT_render_snorm` | `ext_render_snorm.idl` |
| `EXT_texture_compression_bptc` | `ext_texture_compression_bptc.idl` |
| `EXT_texture_compression_rgtc` | `ext_texture_compression_rgtc.idl` |
| `EXT_texture_mirror_clamp_to_edge` | `ext_texture_mirror_clamp_to_edge.idl` |
| `EXT_conservative_depth` | `ext_conservative_depth.idl` |

### Steps

- [ ] **Step 1: Read each IDL file**

```bash
cd /home/attekett/git/samples-webgl
for f in ext_clip_control ext_depth_clamp ext_polygon_offset_clamp ext_render_snorm ext_texture_compression_bptc ext_texture_compression_rgtc ext_texture_mirror_clamp_to_edge ext_conservative_depth; do
  echo "=== $f.idl ==="
  cat scripts/.idl_cache/extensions/$f.idl
done
```

- [ ] **Step 2: Insert 8 new entries into `EXTENSIONS` in `scripts/extract_webidl.js`**

Role-tag guidance for these extensions:
- `EXT_clip_control` constants `LOWER_LEFT_EXT`, `UPPER_LEFT_EXT`, `NEGATIVE_ONE_TO_ONE_EXT`, `ZERO_TO_ONE_EXT`, `CLIP_ORIGIN_EXT`, `CLIP_DEPTH_MODE_EXT` → `get_parameter`. Method `clipControlEXT` takes `(GLenum origin, GLenum depth)`.
- `EXT_depth_clamp` constant `DEPTH_CLAMP_EXT` → `capability` (used with enable/disable)
- `EXT_polygon_offset_clamp` constants `POLYGON_OFFSET_CLAMP_EXT` → `get_parameter`; method `polygonOffsetClampEXT` takes `(GLfloat factor, GLfloat units, GLfloat clamp)`.
- `EXT_render_snorm` — Chromium IDL `ext_render_snorm.idl` exposes no constants and no methods. Use `methods: {}, constants: {}`. (The extension is a flag that enables signed-normalized formats already defined in WebGL2 base; the format constants live in webgl2.idl, not in this extension.)
- `EXT_texture_compression_bptc` constants like `COMPRESSED_RGBA_BPTC_UNORM_EXT` → `compressed_format`
- `EXT_texture_compression_rgtc` constants like `COMPRESSED_RED_RGTC1_EXT` → `compressed_format`
- `EXT_texture_mirror_clamp_to_edge` constant `MIRROR_CLAMP_TO_EDGE_EXT` → `texture_parameter` (used with TEXTURE_WRAP_*)
- `EXT_conservative_depth` has no constants or methods — it's a shader-extension flag. Use `methods: {}, constants: {}`.

- [ ] **Step 3: Regenerate**

```bash
cd /home/attekett/git/samples-webgl/scripts && node extract_webidl.js 2>&1 | tail -5
```

Expected: `Extensions: 43`.

- [ ] **Step 4: Run parity tests**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/test_chromium_parity.py -v 2>&1 | tail -20
```

Expected: 15 of 28 extensions now passing (7 Tier 1 + 8 Tier 2 EXT).

- [ ] **Step 5: Run full suite**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/ -q 2>&1 | tail -3
```

Expected: no regression.

- [ ] **Step 6: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/extract_webidl.js docs/webgl_api_surface.json
git commit -m "feat(surface): add Tier 2 EXT-prefix Chromium WebGL extensions

Adds clip_control, depth_clamp, polygon_offset_clamp, render_snorm,
texture_compression_bptc/rgtc, texture_mirror_clamp_to_edge, and
conservative_depth. Extension count 35 → 43."
```

---

## Task 5: Add Tier 2 WEBGL-prefix extensions (9)

**Files:**
- Modify: `scripts/extract_webidl.js` (`EXTENSIONS` block)
- Regenerate: `docs/webgl_api_surface.json`

### Tier 2 WEBGL extensions to add

| getExtension name | IDL filename |
|---|---|
| `WEBGL_blend_func_extended` | `webgl_blend_func_extended.idl` |
| `WEBGL_clip_cull_distance` | `webgl_clip_cull_distance.idl` |
| `WEBGL_draw_instanced_base_vertex_base_instance` | `webgl_draw_instanced_base_vertex_base_instance.idl` |
| `WEBGL_multi_draw_instanced_base_vertex_base_instance` | `webgl_multi_draw_instanced_base_vertex_base_instance.idl` |
| `WEBGL_polygon_mode` | `webgl_polygon_mode.idl` |
| `WEBGL_provoking_vertex` | `webgl_provoking_vertex.idl` |
| `WEBGL_render_shared_exponent` | `webgl_render_shared_exponent.idl` |
| `WEBGL_shader_pixel_local_storage` | `webgl_shader_pixel_local_storage.idl` |
| `WEBGL_stencil_texturing` | `webgl_stencil_texturing.idl` |

### Steps

- [ ] **Step 1: Read each IDL file**

```bash
cd /home/attekett/git/samples-webgl
for f in webgl_blend_func_extended webgl_clip_cull_distance webgl_draw_instanced_base_vertex_base_instance webgl_multi_draw_instanced_base_vertex_base_instance webgl_polygon_mode webgl_provoking_vertex webgl_render_shared_exponent webgl_shader_pixel_local_storage webgl_stencil_texturing; do
  echo "=== $f.idl ==="
  cat scripts/.idl_cache/extensions/$f.idl
done
```

- [ ] **Step 2: Insert 9 new entries into `EXTENSIONS` in `scripts/extract_webidl.js`**

Role-tag guidance:
- `WEBGL_blend_func_extended` constants like `SRC1_COLOR_WEBGL`, `SRC1_ALPHA_WEBGL`, `ONE_MINUS_SRC1_*` → `blend_factor`; `MAX_DUAL_SOURCE_DRAW_BUFFERS_WEBGL` → `get_parameter`
- `WEBGL_clip_cull_distance` constants like `MAX_CLIP_DISTANCES_WEBGL`, `CLIP_DISTANCE0_WEBGL`..`7_WEBGL` → `get_parameter` (or `capability` for the enum'd `CLIP_DISTANCE0_WEBGL`..`CLIP_DISTANCE7_WEBGL` since they're used with `gl.enable`)
- `WEBGL_draw_instanced_base_vertex_base_instance`: methods `drawArraysInstancedBaseInstanceWEBGL`, `drawElementsInstancedBaseVertexBaseInstanceWEBGL`. No constants.
- `WEBGL_multi_draw_instanced_base_vertex_base_instance`: methods `multiDrawArraysInstancedBaseInstanceWEBGL`, `multiDrawElementsInstancedBaseVertexBaseInstanceWEBGL`. No constants.
- `WEBGL_polygon_mode` constants `POLYGON_MODE_WEBGL`, `POLYGON_OFFSET_LINE_WEBGL`, `LINE_WEBGL`, `FILL_WEBGL` → `polygon_mode`. Method `polygonModeWEBGL(GLenum face, GLenum mode)`.
- `WEBGL_provoking_vertex` constants `FIRST_VERTEX_CONVENTION_WEBGL`, `LAST_VERTEX_CONVENTION_WEBGL`, `PROVOKING_VERTEX_WEBGL` → `provoking_vertex_mode`. Method `provokingVertexWEBGL(GLenum provokeMode)`.
- `WEBGL_render_shared_exponent` — Chromium IDL `webgl_render_shared_exponent.idl` exposes no constants and no methods. Use `methods: {}, constants: {}`. (The `RGB9_E5` format constant lives in webgl2.idl already; this extension is a flag enabling it as a render target.)
- `WEBGL_shader_pixel_local_storage` is the largest — read its IDL carefully. Methods include `framebufferTexturePixelLocalStorageWEBGL`, `framebufferPixelLocalClearValuefvWEBGL`, etc. Constants like `MAX_PIXEL_LOCAL_STORAGE_PLANES_WEBGL` → `get_parameter`; `LOAD_OP_*_WEBGL` and `STORE_OP_*_WEBGL` → `webgl_specific`.
- `WEBGL_stencil_texturing` constant `DEPTH_STENCIL_TEXTURE_MODE_WEBGL` → `texture_parameter`; `STENCIL_INDEX_WEBGL` → `texture_parameter` (it's a value for `DEPTH_STENCIL_TEXTURE_MODE_WEBGL`)

- [ ] **Step 3: Regenerate**

```bash
cd /home/attekett/git/samples-webgl/scripts && node extract_webidl.js 2>&1 | tail -5
```

Expected: `Extensions: 52`.

- [ ] **Step 4: Run parity tests**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/test_chromium_parity.py -v 2>&1 | tail -20
```

Expected: 24 of 28 extensions now passing.

- [ ] **Step 5: Run full suite**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/ -q 2>&1 | tail -3
```

- [ ] **Step 6: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/extract_webidl.js docs/webgl_api_surface.json
git commit -m "feat(surface): add Tier 2 WEBGL-prefix Chromium WebGL extensions

Adds blend_func_extended, clip_cull_distance, draw_instanced_base_vertex_base_instance,
multi_draw_instanced_base_vertex_base_instance, polygon_mode, provoking_vertex,
render_shared_exponent, shader_pixel_local_storage, and stencil_texturing.
Extension count 43 → 52."
```

---

## Task 6: Add Tier 3 extensions (4) — niche / vendor-specific

**Files:**
- Modify: `scripts/extract_webidl.js`
- Regenerate: `docs/webgl_api_surface.json`

### Tier 3 extensions to add

| getExtension name | IDL filename |
|---|---|
| `OVR_multiview2` | `ovr_multiview_2.idl` |
| `OES_sample_variables` | `oes_sample_variables.idl` |
| `OES_shader_multisample_interpolation` | `oes_shader_multisample_interpolation.idl` |
| `NV_shader_noperspective_interpolation` | `nv_shader_noperspective_interpolation.idl` |

### Steps

- [ ] **Step 1: Read each IDL file**

```bash
cd /home/attekett/git/samples-webgl
for f in ovr_multiview_2 oes_sample_variables oes_shader_multisample_interpolation nv_shader_noperspective_interpolation; do
  echo "=== $f.idl ==="
  cat scripts/.idl_cache/extensions/$f.idl
done
```

- [ ] **Step 2: Insert 4 new entries**

Role-tag guidance:
- `OVR_multiview2` constants `FRAMEBUFFER_ATTACHMENT_TEXTURE_NUM_VIEWS_OVR`, `FRAMEBUFFER_ATTACHMENT_TEXTURE_BASE_VIEW_INDEX_OVR`, `MAX_VIEWS_OVR`, `FRAMEBUFFER_INCOMPLETE_VIEW_TARGETS_OVR` → `get_parameter`. Method `framebufferTextureMultiviewOVR(target, attachment, texture, level, baseViewIndex, numViews)`.
- `OES_sample_variables` is shader-only flag (no methods, no constants)
- `OES_shader_multisample_interpolation` constants `MIN_FRAGMENT_INTERPOLATION_OFFSET_OES`, `MAX_FRAGMENT_INTERPOLATION_OFFSET_OES`, `FRAGMENT_INTERPOLATION_OFFSET_BITS_OES` → `get_parameter`
- `NV_shader_noperspective_interpolation` is shader-only flag (no methods, no constants)

- [ ] **Step 3: Regenerate**

```bash
cd /home/attekett/git/samples-webgl/scripts && node extract_webidl.js 2>&1 | tail -5
```

Expected: `Extensions: 56`.

- [ ] **Step 4: Run parity tests — all 28 should pass now**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/test_chromium_parity.py -v 2>&1 | tail -10
```

Expected: 84 tests pass (28 × 3 parameterized tests). 0 failures.

- [ ] **Step 5: Run full suite**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/ -q 2>&1 | tail -3
```

Expected: 150 prior + 84 new = **234 passing**.

- [ ] **Step 6: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/extract_webidl.js docs/webgl_api_surface.json
git commit -m "feat(surface): add Tier 3 niche/vendor Chromium WebGL extensions

Adds OVR_multiview2, OES_sample_variables, OES_shader_multisample_interpolation,
and NV_shader_noperspective_interpolation. Extension count 52 → 56.
Brings project surface to full parity with Chromium WebGL extension set."
```

---

## Task 7: Add `makeXRCompatible` method to the surface

**Files:**
- Modify: `scripts/extract_webidl.js` (the IDL parsing pipeline OR add a manual augmentation step)
- Regenerate: `docs/webgl_api_surface.json`
- Update: `scripts/api_audit/tests/test_chromium_parity.py` (add a method test)

`makeXRCompatible()` is a context method (lives on `WebGLRenderingContextBase`), not in an extension. Chromium gates it `[RuntimeEnabled=WebXR, SecureContext, CallWith=ScriptState, RaisesException, MeasureAs=WebGLRenderingContextMakeXRCompatible] Promise<undefined> makeXRCompatible();`.

The current cached `.idl_cache/webgl1.idl` is from Khronos `latest/` and does NOT include this method (Khronos IDL doesn't bundle WebXR integration). The simplest path: add a manual augmentation in `extract_webidl.js` that injects `makeXRCompatible` into the methods dict during extraction.

- [ ] **Step 1: Locate the methods-dict assembly in `extract_webidl.js`**

The method dict at the assembly point (where the output JSON is built) is named **`allMethods`**, NOT `methods`. The local `methods` variable on line 524 is scoped to the inner extraction function and is out of scope at file-end. Verify:

```bash
grep -nE "const allMethods|allMethods\[|methods: allMethods" /home/attekett/git/samples-webgl/scripts/extract_webidl.js
```

Expected output includes:
```
986:  const allMethods = {};
1019:    methods: allMethods,
1030:  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2) + '\n');
```

The augmentation must mutate `allMethods` AFTER it is fully populated (after line ~1006) and BEFORE the `const output = {` object literal at line 1009.

- [ ] **Step 2: Add a manual augmentation block**

Insert the following block in `scripts/extract_webidl.js` immediately before the `const output = {` block (line 1009):

```javascript
  // Manual augmentation: methods exposed by Chromium but absent from the
  // Khronos-latest cached IDL files. Source: Chromium
  // third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.idl.
  allMethods['makeXRCompatible'] = {
    webgl_version: 'webgl1',
    overloads: [{
      arity: 0,
      params: [],
      returnType: 'Promise<undefined>'
    }]
  };
```

The variable name is **`allMethods`** — using `methods` would throw `ReferenceError: methods is not defined`. Indentation: 2 spaces (matches surrounding lines in the `run()` function).

- [ ] **Step 3: Regenerate**

```bash
cd /home/attekett/git/samples-webgl/scripts && node extract_webidl.js 2>&1 | tail -5
```

Expected: completes; method count goes from 225 → 226.

- [ ] **Step 4: Verify makeXRCompatible appears in the surface**

```bash
cd /home/attekett/git/samples-webgl
./venv/bin/python -c "
import json
s = json.load(open('docs/webgl_api_surface.json'))
print('Method count:', len(s['methods']))
print('makeXRCompatible present:', 'makeXRCompatible' in s['methods'])
print('Entry:', json.dumps(s['methods'].get('makeXRCompatible'), indent=2))
"
```

Expected:
```
Method count: 226
makeXRCompatible present: True
Entry: {...}
```

- [ ] **Step 5: Add a method test**

Append to `scripts/api_audit/tests/test_chromium_parity.py`:

```python
def test_make_xr_compatible_present(surface):
    """makeXRCompatible is exposed by Chromium but missing from Khronos IDL.

    Validated via the manual augmentation block in extract_webidl.js.
    """
    assert "makeXRCompatible" in surface["methods"], (
        "makeXRCompatible should be in surface.methods after extract_webidl.js runs"
    )
```

- [ ] **Step 6: Run the test**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/test_chromium_parity.py::test_make_xr_compatible_present -v
```

Expected: 1 passed.

- [ ] **Step 7: Run full suite**

```bash
cd /home/attekett/git/samples-webgl/scripts && ../venv/bin/python -m pytest api_audit/tests/ -q 2>&1 | tail -3
```

Expected: **235 passing** (234 from Task 6 + 1 new XR test).

- [ ] **Step 8: Commit**

```bash
cd /home/attekett/git/samples-webgl
git add scripts/extract_webidl.js docs/webgl_api_surface.json scripts/api_audit/tests/test_chromium_parity.py
git commit -m "feat(surface): add makeXRCompatible to method surface

WebXR integration method exposed by Chromium but absent from Khronos
latest IDL. Added via manual augmentation in extract_webidl.js. Method
count 225 → 226."
```

---

## Task 8: Run the full audit pipeline + update CLAUDE.md

**Files:**
- Verify: `docs/webgl_api_surface.json` (no changes — verification only)
- Update: `CLAUDE.md` (Coverage Analysis section if needed)

- [ ] **Step 1: Run the full audit pipeline against the real corpus**

```bash
cd /home/attekett/git/samples-webgl
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix_post.json \
  --gap-recipes /tmp/recipes_post.json \
  --n-way 3 2>&1 | tail -10
```

Expected: completes cleanly. Report shows updated method count (226 not 225) and updated extension count (56 not 28). The number of "uncovered" 3-way combos may have changed because the surface has more features.

- [ ] **Step 2: Inspect the new surface stats**

```bash
./venv/bin/python -c "
import json
s = json.load(open('docs/webgl_api_surface.json'))
print(f\"Methods: {len(s['methods'])}\")
print(f\"Constants: {len(s['constants'])}\")
print(f\"Extensions: {len(s['extensions'])}\")
print(f\"GLSL builtins: {len(s['glsl_builtins'])}\")
print(f\"Schema version: {s['meta']['schema_version']}\")
print(f\"Extracted at: {s['meta']['extracted_at']}\")
print()
print('All extensions:')
for ext in sorted(s['extensions'].keys()):
    print(f'  {ext}')
"
```

Expected: 226 methods, 56 extensions. All 28 newly-added extensions present.

- [ ] **Step 3: Re-run validation against Chromium (full diff)**

```bash
./venv/bin/python << 'EOF'
"""Final cross-check: project surface vs Chromium IDLs."""
import json
import re
from pathlib import Path

CHROMIUM_DIR = Path.home() / "git/chromium/src/third_party/blink/renderer/modules/webgl"

# Get every extension class name from Chromium IDLs
SKIP = {
    "webgl_object", "webgl_context_event", "webgl_context_event_init",
    "webgl_uniform_location", "webgl_active_info",
    "webgl_shader_precision_format", "webgl_buffer", "webgl_framebuffer",
    "webgl_program", "webgl_renderbuffer", "webgl_shader", "webgl_texture",
    "webgl_query", "webgl_sampler", "webgl_sync", "webgl_transform_feedback",
    "webgl_vertex_array_object", "webgl_context_attributes",
    "webgl_rendering_context", "webgl_rendering_context_base",
    "webgl_rendering_context_webgpu", "webgl2_rendering_context",
    "webgl2_rendering_context_base", "webgl2_rendering_context_webgpu",
    "webgl_timer_query_ext", "webgl_vertex_array_object_oes",
}

iface_re = re.compile(r'interface\s+(\w+)\s*[:{]')
chromium_classes = set()
for idl_file in sorted(CHROMIUM_DIR.glob("*.idl")):
    if idl_file.stem in SKIP:
        continue
    text = idl_file.read_text()
    for m in iface_re.finditer(text):
        chromium_classes.add(m.group(1))

surface = json.load(open("docs/webgl_api_surface.json"))
project_extensions = set(surface["extensions"].keys())

print(f"Chromium extension interface classes: {len(chromium_classes)}")
print(f"Project extensions: {len(project_extensions)}")
print()
print(f"Chromium extension classes (for reference):")
for c in sorted(chromium_classes):
    print(f"  {c}")
EOF
```

Expected: Chromium has ~55-56 extension classes; project has 56. The remaining handful (if any) should be those previously identified as object types (e.g., the WebGLTimerQueryEXT object class for `EXT_disjoint_timer_query`, which is registered as the *object* not the *extension* itself).

- [ ] **Step 4: Update CLAUDE.md if surface counts are quoted there**

```bash
grep -n "225\|225/225\|extensions" /home/attekett/git/samples-webgl/CLAUDE.md
```

If any line quotes "225 methods" or "28 extensions", update to "226 methods" / "56 extensions". If no such lines exist, skip this step.

- [ ] **Step 5: Commit any CLAUDE.md updates**

```bash
cd /home/attekett/git/samples-webgl
git diff CLAUDE.md   # confirm what changed
git add CLAUDE.md
git commit -m "docs: update surface counts in CLAUDE.md for Chromium parity"
```

If nothing changed, no commit needed.

---

## Self-Review Checklist

| Spec requirement | Where in plan |
|---|---|
| Snapshot 28 Chromium extension IDLs | Task 1 |
| Parity test catches missing extensions | Task 2 |
| Add Tier 1 extensions (7) | Task 3 |
| Add Tier 2 EXT extensions (8) | Task 4 |
| Add Tier 2 WEBGL extensions (9) | Task 5 |
| Add Tier 3 extensions (4) | Task 6 |
| Add `makeXRCompatible` method | Task 7 |
| Final pipeline run + docs | Task 8 |
| Total: 28 extensions + 1 method | All tasks |

**Type/name consistency**:
- Extension surface key matches `getExtension()` argument (e.g., `EXT_blend_minmax`, not `EXT_blend_min_max` from filename). The `IDL_TO_EXT_NAME` map in Task 2 documents this mapping.
- Constant hex values in extract_webidl.js entries must match IDL **exactly**. Case is normalized by the parity test (`.lower()` comparison), but **leading zeros and width are NOT normalized** — copy the hex literal verbatim from the IDL (`'0x88FE'` not `'0x088FE'`; `'0x1'` not `'0x00000001'`). The parity test does string equality after `.lower()`; any padding/stripping breaks it.
- Role tags from the glossary (Section "Role tag glossary") only — no novel tags.
- `EXTENSIONS` block schema matches existing entries: `{ methods: {...}, constants: {...} }` with method overload arity matching param count.

**Out of scope (explicitly deferred)**:
- Categorizing the 28 newly-added extensions in `feature_categories.json` (separate hand-curation plan).
- Updating `interaction_topology.json` to add edges involving new extensions (separate plan).
- Generating mutation seeds for the new extensions (the `expand-webgl-coverage` skill consumes the surface; once it's complete, those flows can target the new extensions).
- Refreshing the cached `.idl_cache/webgl1.idl` and `webgl2.idl` from upstream Khronos (different concern).

**Risks and mitigations**:

| Risk | Mitigation |
|---|---|
| Hex constant typos | Parity test in Task 2 compares each constant value byte-for-byte against the cached IDL |
| Wrong extension name (filename vs getExtension) | `IDL_TO_EXT_NAME` map in Task 2 is the single source of truth |
| Wrong role tag | Glossary in Section "Role tag glossary" + role conventions in existing entries |
| Method signature errors (param types) | Less critical for fuzzing — names matter more than types. Parity test verifies method names; signature drift won't break the audit pipeline. |
| `node extract_webidl.js` fails on bad JS syntax | TDD discipline: regenerate after every tier; if it fails, the test won't even run |
| Tests for unrelated functionality break | Step 5 of each tier task runs the full pytest suite |
| `makeXRCompatible` augmentation breaks other methods | Task 7 isolates the augmentation to a single key insertion; full suite verifies |

**Effort estimate**: 8 tasks. Tier transcription tasks (3-6) are mechanical: read IDL → add entry → regenerate → test. Each ~10-20 minutes per tier (7-9 entries). Total: ~3 hours of focused work for the implementer, longer if subagent-driven with reviews between each.
