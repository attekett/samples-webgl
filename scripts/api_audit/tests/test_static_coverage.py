import json
from pathlib import Path

from api_audit.cache import FileCache
from api_audit.value_classes import classify_static_value, resolve_static_overload
from feature_coverage import requirement_universe, static_fingerprint
from api_audit.parse import parse_js


ROOT = Path(__file__).resolve().parents[3]


def load_surface():
    return json.loads((ROOT / "docs/webgl_api_surface.json").read_text())


def test_multidraw_surface_arities_match_parameters():
    methods = load_surface()["extensions"]["WEBGL_multi_draw"]["methods"]
    assert {name: overload["arity"] for name, info in methods.items()
            for overload in info["overloads"]} == {
        "multiDrawArraysWEBGL": 6,
        "multiDrawElementsWEBGL": 7,
        "multiDrawArraysInstancedWEBGL": 8,
        "multiDrawElementsInstancedWEBGL": 9,
    }
    assert all(overload["arity"] == len(overload["params"])
               for info in methods.values() for overload in info["overloads"])


def test_webgl1_universe_filters_webgl2_method_and_overload():
    surface = load_surface()
    universe = requirement_universe(surface, {"categories": {}}, {"edges": []}, 1,
                                    {"WEBGL_multi_draw"})
    assert "core:createVertexArray" not in universe["core_methods"]
    assert "core:drawArraysInstanced" not in universe["core_methods"]
    assert "overload:bufferData:GLenum,ArrayBufferView,GLenum,unsigned long long,GLuint?" not in universe["core_overloads"]
    assert "extension:WEBGL_multi_draw:multiDrawArraysWEBGL" in universe["extension_methods"]
    assert "WEBGL_multi_draw" not in universe["unsupported_extensions"]
    assert "WEBGL_multi_draw" not in universe["unmeasured_extensions"]
    assert universe["unsupported_extensions"]


def test_extension_pairs_distinguish_unsupported_and_unmeasured():
    surface = load_surface()
    categories = json.loads((ROOT / "docs/feature_categories.json").read_text())
    topology = json.loads((ROOT / "docs/interaction_topology.json").read_text())
    pair = "pair:draw_calls+WEBGL_multi_draw"

    unavailable = requirement_universe(surface, categories, topology, 1, [])
    assert pair in unavailable["unsupported_category_pairs"]
    assert pair not in unavailable["requirements"]["category_pairs"]
    assert "pair:draw_calls+shader_pipeline" in unavailable["requirements"]["category_pairs"]

    unobserved = requirement_universe(surface, categories, topology, 1, None)
    assert pair in unobserved["unmeasured_category_pairs"]
    assert "WEBGL_multi_draw" in unobserved["unmeasured_extensions"]


def test_missing_context_version_is_unmeasured():
    universe = requirement_universe(load_surface(), {"categories": {}}, {"edges": []}, None, [])
    assert universe["context_version"] is None
    assert not universe["requirements"]["core_methods"]
    assert universe["unmeasured_core_methods"]


def test_bufferdata_variable_stays_unknown_but_literal_types_resolve():
    surface = load_surface()
    source = "const gl = canvas.getContext('webgl2'); const bytes = new Uint8Array(8); gl.bufferData(gl.ARRAY_BUFFER, bytes, gl.STATIC_DRAW);"
    root = parse_js(source)
    calls = [node for node in _walk(root) if node.type == "call_expression"]
    buffer_call = next(node for node in calls if "bufferData" in node.text.decode())
    args = [child for child in buffer_call.child_by_field_name("arguments").children
            if child.type not in ("(", ")", ",")]
    assert resolve_static_overload("bufferData", args, surface) is None

    numeric = parse_js("gl.bufferData(gl.ARRAY_BUFFER, 16, gl.STATIC_DRAW)")
    numeric_call = next(node for node in _walk(numeric) if node.type == "call_expression")
    numeric_args = [child for child in numeric_call.child_by_field_name("arguments").children
                    if child.type not in ("(", ")", ",")]
    assert resolve_static_overload("bufferData", numeric_args, surface) == \
        "overload:bufferData:GLenum,GLsizeiptr,GLenum"


def test_unproven_constructor_and_unary_expression_stay_unknown():
    assert classify_static_value(_single_expression("new Foo(8)")) == "unknown"
    assert classify_static_value(_single_expression("-COUNT")) == "unknown"
    assert classify_static_value(_single_expression("-3")) == "negative"
    surface = load_surface()
    root = parse_js("gl.bufferData(gl.ARRAY_BUFFER, new Foo(8), gl.STATIC_DRAW)")
    call = next(node for node in _walk(root) if node.type == "call_expression")
    args = [child for child in call.child_by_field_name("arguments").children
            if child.type not in ("(", ")", ",")]
    assert resolve_static_overload("bufferData", args, surface) is None


def test_static_fingerprint_records_multidraw_and_unknown_overload(tmp_path):
    surface = load_surface()
    categories = json.loads((ROOT / "docs/feature_categories.json").read_text())
    html = tmp_path / "seed.html"
    html.write_text("""<canvas></canvas><script>
const gl = canvas.getContext('webgl2');
const ext = gl.getExtension('WEBGL_multi_draw');
const firsts = new Int32Array([0]);
const counts = new Int32Array([3]);
ext.multiDrawArraysWEBGL(gl.TRIANGLES, firsts, 0, counts, 0, 1);
const data = new Uint8Array(8);
gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
</script>""")
    fp = static_fingerprint(html, surface, categories, FileCache(tmp_path / "cache"))
    assert Path(fp["source_path"]) == html.resolve()
    assert fp["source_sha256"]
    assert "WEBGL_multi_draw" in fp["requested_extensions"]
    assert fp["extension_methods"]["WEBGL_multi_draw"]["multiDrawArraysWEBGL"] == 1
    assert "WEBGL_multi_draw" in fp["features"]
    assert "extension:WEBGL_multi_draw:multiDrawArraysWEBGL" in fp["static_requirements"]
    buffer_data = next(call for call in fp["overload_calls"]
                       if call["method"] == "bufferData")
    assert buffer_data["overload"] == "unknown"


def test_static_fingerprint_hashes_original_crlf_bytes(tmp_path):
    html = tmp_path / "crlf.html"
    source = b"<canvas></canvas>\r\n<script>\r\nconst gl = canvas.getContext('webgl2');\r\ngl.drawArrays(gl.TRIANGLES, 0, 3);\r\n</script>\r\n"
    html.write_bytes(source)
    fp = static_fingerprint(html, load_surface(), {"categories": {}})
    import hashlib
    assert fp["source_sha256"] == hashlib.sha256(source).hexdigest()


def test_cache_invalidates_for_surface_or_categories(tmp_path):
    html = tmp_path / "seed.html"
    html.write_text("<canvas></canvas><script>const gl = canvas.getContext('webgl'); gl.drawArrays(gl.TRIANGLES, 0, 3);</script>")
    surface = {"methods": {"drawArrays": {"webgl_version": 1, "overloads": []}},
               "extensions": {}, "constants": {}}
    cats = {"categories": {}}
    cache = FileCache(tmp_path / "cache")
    static_fingerprint(html, surface, cats, cache)
    assert len(list((tmp_path / "cache/files").glob("*.json"))) == 1
    changed_surface = json.loads(json.dumps(surface))
    changed_surface["methods"]["drawArrays"]["overloads"].append(
        {"arity": 3, "webgl_version": 1,
         "params": [{"name": "mode", "type": "GLenum"},
                    {"name": "first", "type": "GLint"},
                    {"name": "count", "type": "GLsizei"}]})
    static_fingerprint(html, changed_surface, cats, cache)
    static_fingerprint(html, changed_surface, {"categories": {"new": {}}}, cache)
    assert len(list((tmp_path / "cache/files").glob("*.json"))) == 3


def _walk(node):
    yield node
    for child in node.children:
        yield from _walk(child)


def _single_expression(source):
    root = parse_js(source)
    nodes = [node for node in _walk(root) if node.type in ("new_expression", "unary_expression")]
    return nodes[0] if nodes else next(
        node for node in _walk(root) if node.type == "call_expression")
