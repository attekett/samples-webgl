"""Helper-function parameters that receive a context at a call site."""
import json
from pathlib import Path

import feature_coverage
from api_audit.__main__ import analyze_file as audit_analyze

ROOT = Path(__file__).resolve().parents[3]
SURFACE = json.loads((ROOT / "docs/webgl_api_surface.json").read_text())
CATS = json.loads((ROOT / "docs/feature_categories.json").read_text())


def run(tmp_path, body, gl="const gl = document.getElementById('c').getContext('webgl2');"):
    f = tmp_path / "seed.html"
    f.write_text(f"<html><body><canvas id='c'></canvas><script>\n{gl}\n{body}\n</script></body></html>")
    return feature_coverage.analyze_file(f, SURFACE, CATS)


def test_differently_named_helper_param(tmp_path):
    r = run(tmp_path, """
function makeSetup(gl) { gl.createBuffer(); gl.uniform4f(null, 1, 2, 3, 4); }
makeSetup(glA); makeSetup(glB);""",
            gl="const glA = c1.getContext('webgl2'); const glB = c2.getContext('webgl2');")
    assert {'createBuffer', 'uniform4f'} <= r['all_methods']
    assert 'buffer_ops' in r['features'] and 'uniforms' in r['features']
    a = audit_analyze(tmp_path / "seed.html", SURFACE)
    assert {'createBuffer', 'uniform4f'} <= set(a['methods'])


def test_renamed_param_records_constants(tmp_path):
    r = run(tmp_path, "function f(ctx) { ctx.drawArrays(ctx.TRIANGLES, 0, 3); } f(gl);")
    assert 'TRIANGLES' in r['method_constants']['drawArrays']


def test_shadowing_and_unbound_names(tmp_path):
    r = run(tmp_path, """
function f(ctx) { ctx.flush(); } f(gl);
function h(ctx) { ctx.clear(0); }
h(document.createElement('canvas').getContext('2d'));
ctx.finish();""")
    assert 'flush' in r['all_methods']
    assert not {'clear', 'finish'} & r['all_methods']


def test_shadowed_param_not_called_with_context(tmp_path):
    r = run(tmp_path, "function h(ctx) { ctx.clear(0); } h(42);")
    assert 'clear' not in r['all_methods']


def test_arrow_function(tmp_path):
    r = run(tmp_path, "const draw = (c) => c.drawElements(c.TRIANGLES, 3, c.UNSIGNED_SHORT, 0); draw(gl);")
    assert 'drawElements' in r['all_methods']


def test_two_levels(tmp_path):
    r = run(tmp_path, """
function outer(a) { inner(a); }
function inner(b) { b.enable(b.BLEND); }
outer(gl);""")
    assert 'blending' in r['features']


def test_non_context_argument(tmp_path):
    r = run(tmp_path, "function f2(x) { x.flush(); } f2(42);")
    assert 'flush' not in r['all_methods']


def test_nested_class_method_shadows_param(tmp_path):
    r = run(tmp_path, "function f(c){ class K { m(c){ c.flush(); } } } f(gl);")
    assert 'flush' not in r['all_methods']


def test_generator_function_param(tmp_path):
    r = run(tmp_path, "function* g(c){ c.flush(); } g(gl);")
    assert 'flush' in r['all_methods']


def test_destructured_param_shadows(tmp_path):
    r = run(tmp_path, "function f(c){ const k = ({c}) => c.flush(); } f(gl);")
    assert 'flush' not in r['all_methods']


def test_default_value_does_not_shadow(tmp_path):
    r = run(tmp_path, "function f(c, x = c){ c.flush(); } f(gl);")
    assert 'flush' in r['all_methods']
