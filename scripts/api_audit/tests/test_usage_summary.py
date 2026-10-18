import json
from pathlib import Path

from api_audit.__main__ import analyze_file as audit_analyze
from api_audit.feature_detection import detect_features
from api_audit.parse import parse_js
from api_audit.usage_summary import summarize_usage
import feature_coverage

ROOT = Path(__file__).resolve().parents[3]
SURFACE = json.loads((ROOT / "docs/webgl_api_surface.json").read_text())
CATS = json.loads((ROOT / "docs/feature_categories.json").read_text())

SEED = """<!DOCTYPE html><html><body><canvas id="c" width="256" height="256"></canvas>
<script>
const gl = document.getElementById('c').getContext('webgl2');
const buf = gl.createBuffer();
gl.bindBuffer(gl.UNIFORM_BUFFER, buf);
gl.bufferData(gl.UNIFORM_BUFFER, 64, gl.DYNAMIC_DRAW);
const tex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_3D, tex);
gl.texStorage3D(gl.TEXTURE_3D, 1, gl.RGBA8, 4, 4, 4);
gl.enable(gl.DEPTH_TEST);
const fs = `#version 300 es
precision highp float;
out vec4 o;
void main() { o = texture(s, gl_FragCoord.xy) * smoothstep(0., 1., o.x); }`;
gl.shaderSource(gl.createShader(gl.FRAGMENT_SHADER), fs);
</script></body></html>"""


def test_wrappers_agree(tmp_path):
    f = tmp_path / "seed.html"
    f.write_text(SEED)
    extra = [g for c in CATS["categories"].values() for g in c.get("glsl_functions", [])]
    a = audit_analyze(f, SURFACE, extra_glsl_builtins=extra)
    b = feature_coverage.analyze_file(f, SURFACE, CATS)
    assert a["methods"] == b["methods"]
    assert a["constants"] == b["constants"]
    assert a["extension_methods"] == b["extension_methods"]
    assert a["glsl_variables"] == sorted(b["glsl_variables"])
    assert set(a["glsl_builtins"]) == b["glsl_builtins"]
    assert "smoothstep" in a["glsl_builtins"]
    fa = detect_features(a, set(a["glsl_builtins"]), CATS, extensions=set(a["extensions"]))
    assert fa["features"] == b["features"]


def test_method_constants():
    root = parse_js("""const gl = document.getElementById('c').getContext('webgl2');
gl.enable(gl.DEPTH_TEST);
gl.texImage2D(gl.TEXTURE_2D, 0, gl.DEPTH_COMPONENT24, 4, 4, 0, gl.DEPTH_COMPONENT, gl.UNSIGNED_INT, null);""")
    summary, _ = summarize_usage(root, SURFACE)
    mc = summary["method_constants"]
    assert mc["enable"] == ["DEPTH_TEST"]
    assert {"TEXTURE_2D", "DEPTH_COMPONENT24", "DEPTH_COMPONENT", "UNSIGNED_INT"} <= set(mc["texImage2D"])


def test_audit_result_has_glsl_variables(tmp_path):
    f = tmp_path / "seed.html"
    f.write_text(SEED)
    assert "gl_FragCoord" in audit_analyze(f, SURFACE)["glsl_variables"]
