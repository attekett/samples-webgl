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
