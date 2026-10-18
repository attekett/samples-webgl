"""Context-level markers: context attributes, multiple contexts, extension alias by assignment."""
import json
from pathlib import Path

from api_audit.context import detect_context
from api_audit.parse import parse_js
import feature_coverage
from api_audit.feature_detection import detect_features
from api_audit.usage_summary import summarize_usage

ROOT = Path(__file__).resolve().parents[3]
SURFACE = json.loads((ROOT / "docs/webgl_api_surface.json").read_text())
CATS = json.loads((ROOT / "docs/feature_categories.json").read_text())


def ctx(src):
    return detect_context(parse_js(src), {})


def test_literal_attributes_skip_defaults_and_antialias():
    c = ctx("const g = c.getContext('webgl2', {stencil: true, antialias: false, alpha: true});")
    assert c.markers == {'ctxattr:stencil=true'}


def test_attributes_through_identifier():
    c = ctx("const opts = {preserveDrawingBuffer: true}; const g = c.getContext('webgl2', opts);")
    assert 'ctxattr:preserveDrawingBuffer=true' in c.markers


def test_2d_context_is_not_a_gl_receiver():
    c = ctx("const g = c.getContext('2d');")
    assert 'g' not in c.context_vars


def test_multiple_contexts():
    assert 'ctx:multiple' in ctx(
        "const a = canvasA.getContext('webgl2'); const b = canvasB.getContext('webgl2');").markers
    assert 'ctx:multiple' not in ctx(
        "const g = c.getContext('webgl2') || c.getContext('webgl');").markers
    assert 'ctx:multiple' not in ctx(
        "let g = c.getContext('webgl2'); if (!g) g = c.getContext('webgl');").markers


def test_offscreen():
    assert 'ctx:offscreen' in ctx("const g = new OffscreenCanvas(4,4).getContext('webgl2');").markers
    assert 'ctx:offscreen' in ctx(
        "const o = new OffscreenCanvas(4,4); const g = o.getContext('webgl2');").markers
    assert 'ctx:offscreen' not in ctx("const g = c.getContext('webgl2');").markers


def test_extension_alias_by_assignment(tmp_path):
    f = tmp_path / "seed.html"
    f.write_text("""<html><body><canvas id="c"></canvas><script>
const gl = document.getElementById('c').getContext('webgl2');
let ext; ext = gl.getExtension('WEBGL_multi_draw');
ext.multiDrawArraysWEBGL(gl.TRIANGLES, [0], 0, [3], 0, 1);
</script></body></html>""")
    r = feature_coverage.analyze_file(f, SURFACE, CATS)
    assert 'WEBGL_multi_draw' in r['requested_extensions']
    assert 'multiDrawArraysWEBGL' in r['extension_methods']['WEBGL_multi_draw']
    assert 'WEBGL_multi_draw' in r['features']


def test_marker_category_matches(tmp_path):
    f = tmp_path / "seed.html"
    f.write_text("""<html><body><canvas id="c"></canvas><script>
const gl = document.getElementById('c').getContext('webgl2', {stencil: true});
</script></body></html>""")
    r = feature_coverage.analyze_file(f, SURFACE, CATS)
    assert 'context_attributes' in r['features']
    assert 'multi_context' not in r['features']


def features(tmp_path, body):
    f = tmp_path / "seed.html"
    f.write_text(f"""<html><body><canvas id="c"></canvas><script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
{body}
</script></body></html>""")
    return feature_coverage.analyze_file(f, SURFACE, CATS)


def test_drawing_buffer_markers(tmp_path):
    for body in ("canvas.width = 64;", "gl.canvas.height = 8;", "requestAnimationFrame(f);",
                 "window.requestAnimationFrame(f);", "gl.drawingBufferStorage(gl.RGBA8, 4, 4);",
                 "canvas.toDataURL();", "ctx2d.drawImage(canvas, 0, 0);"):
        assert 'drawing_buffer' in features(tmp_path, body)['features'], body
    assert 'drawing_buffer' not in features(tmp_path, "other.width = 4;")['features']


def test_drawing_buffer_storage_not_fbo(tmp_path):
    f = features(tmp_path, "gl.drawingBufferStorage(gl.RGBA8, 4, 4);")['features']
    assert 'drawing_buffer' in f and 'fbo' not in f


def test_colour_space_attribute_marker(tmp_path):
    r = features(tmp_path, "gl.drawingBufferColorSpace = 'display-p3';")
    assert 'attr:drawingBufferColorSpace=' in r['methods_per_feature']['drawing_buffer']


def test_dom_texture_sources(tmp_path):
    up = "gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, %s);"
    r = features(tmp_path, up % "new ImageData(2, 2)")
    assert 'src:ImageData' in r['methods_per_feature']['dom_texture_sources']
    r = features(tmp_path, "const im = document.createElement('img');" + up % "im")
    assert 'src:image' in r['methods_per_feature']['dom_texture_sources']
    r = features(tmp_path, up % "await createImageBitmap(x)")
    assert 'src:ImageBitmap' in r['methods_per_feature']['dom_texture_sources']
    r = features(tmp_path, up % "canvas")
    assert 'src:webgl_canvas' in r['methods_per_feature']['dom_texture_sources']
    r = features(tmp_path, "gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 2, 2, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(16));")
    assert 'dom_texture_sources' not in r['features']


def test_unpack_webgl_params(tmp_path):
    assert 'unpack_webgl_params' in features(tmp_path, "gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);")['features']
    assert 'unpack_webgl_params' not in features(tmp_path, "gl.getParameter(gl.UNPACK_FLIP_Y_WEBGL);")['features']
    assert 'unpack_webgl_params' not in features(tmp_path, "gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);")['features']


def test_identical_call_receivers_are_one_context():
    both = "document.getElementById('c').getContext('{}')"
    src = f"const g = {both.format('webgl2')} || {both.format('webgl')};"
    assert 'ctx:multiple' not in ctx(src).markers
    assert 'ctx:multiple' in ctx(
        "const a = document.getElementById('a').getContext('webgl2');"
        "const b = document.getElementById('b').getContext('webgl2');").markers


def test_numeric_attributes_normalise_to_booleans():
    assert ctx("const g = c.getContext('webgl2', {stencil: 0, alpha: 1});").markers == set()
    assert ctx("const g = c.getContext('webgl2', {stencil: 1});").markers == {'ctxattr:stencil=true'}
    assert ctx("const g = c.getContext('webgl2', {alpha: 0});").markers == {'ctxattr:alpha=false'}


def test_markers_count_toward_depth():
    cat = {"markers": ["a", "b"]}
    r = detect_features({"markers": ["a"]}, set(), {"c": cat})
    assert r["depth_ratios"]["c"] == 0.5
    assert r["methods_per_feature"]["c"] == ["a"]


def usage_markers(body):
    src = f"const canvas = document.getElementById('c'); const gl = canvas.getContext('webgl2'); {body}"
    return summarize_usage(parse_js(src), SURFACE)[0]['markers']


UP2 = "gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, %s);"


def test_canvas_readback_via_create_image_bitmap():
    assert 'canvas:readback' in usage_markers("createImageBitmap(canvas);")
    assert 'canvas:readback' not in usage_markers("createImageBitmap(other);")


def test_unpack_colour_space_marker():
    assert 'attr:unpackColorSpace=' in usage_markers("gl.unpackColorSpace = 'display-p3';")


def test_texture_source_markers():
    for arg, marker in [("new OffscreenCanvas(2, 2)", 'src:OffscreenCanvas'),
                        ("new VideoFrame(x)", 'src:VideoFrame'),
                        ("document.createElement('video')", 'src:video'),
                        ("document.createElement('canvas')", 'src:canvas')]:
        assert marker in usage_markers(UP2 % arg), marker


def test_texture_3d_upload_source_marker():
    for m in ('texImage3D', 'texSubImage3D'):
        body = f"gl.{m}(gl.TEXTURE_3D, 0, 0, 0, 0, 2, 2, 2, gl.RGBA, gl.UNSIGNED_BYTE, new ImageData(2, 2));"
        assert 'src:ImageData' in usage_markers(body), m
