"""Context-level markers: context attributes, multiple contexts, extension alias by assignment."""
import json
from pathlib import Path

from api_audit.context import detect_context
from api_audit.parse import parse_js
import feature_coverage

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
