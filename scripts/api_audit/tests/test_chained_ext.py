"""Tests for chained extension method call detection."""
import pytest
from api_audit.parse import parse_js
from api_audit.const_propagation import resolve_constants
from api_audit.context import detect_context
from api_audit.call_analysis import analyze_calls


SURFACE = {
    "methods": {"viewport": {"overloads": [{"arity": 4, "params": []}]}},
    "extensions": {
        "OES_draw_buffers_indexed": {
            "methods": {
                "enableiOES": {"overloads": [{"arity": 2, "params": []}]},
                "blendFunciOES": {"overloads": [{"arity": 4, "params": []}]},
            }
        }
    }
}


def _analyze(js_source: str):
    root = parse_js(js_source)
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    return analyze_calls(root, ctx, consts, SURFACE)


def test_chained_extension_method_detected():
    """gl.getExtension('ext').method() should be tracked."""
    js = """
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2');
    gl.getExtension('OES_draw_buffers_indexed').enableiOES(0, gl.BLEND);
    """
    result = _analyze(js)
    assert "OES_draw_buffers_indexed" in result.extension_methods
    assert "enableiOES" in result.extension_methods["OES_draw_buffers_indexed"]


def test_chained_unknown_extension_ignored():
    """Chained call on unknown extension is silently dropped."""
    js = """
    const gl = document.createElement('canvas').getContext('webgl2');
    gl.getExtension('UNKNOWN_EXT').someMethod(0);
    """
    result = _analyze(js)
    assert result.extension_methods == {}
