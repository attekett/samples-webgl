"""Tests for GLSL built-in variable extraction (gl_VertexID, gl_Position, etc.)."""


def test_aggregate_glsl_variables_basic():
    from feature_coverage import aggregate_glsl_variables
    fingerprints = [
        {"glsl_variables": {"gl_Position", "gl_VertexID"}},
        {"glsl_variables": {"gl_Position", "gl_FragCoord"}},
        {"glsl_variables": set()},
    ]
    result = aggregate_glsl_variables(fingerprints)
    assert result["gl_Position"] == 2
    assert result["gl_VertexID"] == 1
    assert result["gl_FragCoord"] == 1


def test_aggregate_glsl_variables_skips_none():
    from feature_coverage import aggregate_glsl_variables
    result = aggregate_glsl_variables([None, {"glsl_variables": {"gl_Position"}}])
    assert result == {"gl_Position": 1}


def test_extract_finds_vertex_and_fragment_vars(api_surface, feature_categories, tmp_path):
    """Built-in variables in shader sources are detected without confusing
    them with same-named function calls."""
    from feature_coverage import analyze_file
    seed = tmp_path / "vars.html"
    seed.write_text("""<!DOCTYPE html><html><body>
    <canvas id="c"></canvas><script>
    const gl = document.getElementById('c').getContext('webgl2');
    const vs = `#version 300 es
    in vec3 pos;
    void main() {
        gl_Position = vec4(pos, 1.0);
        gl_PointSize = float(gl_VertexID + gl_InstanceID);
    }`;
    const fs = `#version 300 es
    precision highp float;
    out vec4 o;
    void main() {
        if (gl_FrontFacing) {
            o = vec4(gl_FragCoord.xy / 256.0, gl_PointCoord, 1.0);
        } else {
            o = vec4(0.0);
        }
        gl_FragDepth = gl_FragCoord.z;
    }`;
    const v = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(v, vs);
    const f = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(f, fs);
    </script></body></html>""")
    fp = analyze_file(seed, api_surface, feature_categories)
    assert fp is not None
    found = fp["glsl_variables"]
    for name in ("gl_Position", "gl_PointSize", "gl_VertexID", "gl_InstanceID",
                 "gl_FragCoord", "gl_FrontFacing", "gl_PointCoord", "gl_FragDepth"):
        assert name in found, f"{name} missing from glsl_variables"


def test_match_variables_skips_function_call_collision():
    """Variable matcher must not match `gl_X(` (function-call form)."""
    from api_audit.glsl import _match_variables
    src = "void main() { gl_Position = vec4(0); /* and a fake gl_Position(1) */ }"
    found = _match_variables(src, ["gl_Position"])
    # Variable still found because the bare `gl_Position = ...` is a real
    # use; the regex requires at least one bare occurrence to count.
    assert "gl_Position" in found


def test_match_variables_only_function_call_form_excluded():
    """When `gl_Position` only appears as `gl_Position(...)`, don't count it."""
    from api_audit.glsl import _match_variables
    src = "float gl_Position(float x) { return x; }"  # contrived collision
    found = _match_variables(src, ["gl_Position"])
    assert found == set()
