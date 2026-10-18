"""Shader-source extraction: literal fallback, ${} substitutions, escapes, user-defined builtins."""

HEAD = "<!DOCTYPE html><html><body><canvas id='c'></canvas><script>\n"
TAIL = "\n</script></body></html>"


def _fp(tmp_path, api_surface, feature_categories, body):
    from feature_coverage import analyze_file
    seed = tmp_path / "s.html"
    seed.write_text(HEAD + body + TAIL)
    fp = analyze_file(seed, api_surface, feature_categories)
    assert fp is not None
    return fp


def test_concatenated_template_shader(tmp_path, api_surface, feature_categories):
    fp = _fp(tmp_path, api_surface, feature_categories, """
    const gl = document.getElementById('c').getContext('webgl2');
    const off = 1.5;
    const vs = `#version 300 es
    void main() { gl_PointSize = a + ` + off.toFixed(1) + `; gl_Position = vec4(0); }`;
    gl.shaderSource(gl.createShader(gl.VERTEX_SHADER), vs);""")
    assert {"gl_PointSize", "gl_Position"} <= fp["glsl_variables"]


def test_two_level_helper(tmp_path, api_surface, feature_categories):
    fp = _fp(tmp_path, api_surface, feature_categories, """
    const gl = document.getElementById('c').getContext('webgl2');
    function createShader(gl, type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); return s; }
    function createProgram(gl, vs, fs) { createShader(gl, gl.VERTEX_SHADER, vs); createShader(gl, gl.FRAGMENT_SHADER, fs); }
    const vs = `#version 300 es
    void main() { gl_Position = vec4(0); }`;
    const fs = `#version 300 es
    precision highp float; uniform sampler2D t; out vec4 o;
    void main() { o = texture(t, gl_FragCoord.xy); }`;
    createProgram(gl, vs, fs);""")
    assert "texture" in fp["glsl_builtins"]
    assert "gl_FragCoord" in fp["glsl_variables"]


def test_helper_with_differently_named_contexts(tmp_path, api_surface, feature_categories):
    fp = _fp(tmp_path, api_surface, feature_categories, """
    const glA = document.getElementById('c').getContext('webgl2');
    const glB = document.createElement('canvas').getContext('webgl2');
    function makeSetup(gl) {
      const s = gl.createShader(gl.FRAGMENT_SHADER);
      gl.shaderSource(s, `#version 300 es
      precision highp float; out vec4 o;
      void main() { o = vec4(smoothstep(0.0, 1.0, gl_FragCoord.x)); }`);
    }
    makeSetup(glA); makeSetup(glB);""")
    assert "smoothstep" in fp["glsl_builtins"]


def test_ternary_shader_both_branches(tmp_path, api_surface, feature_categories):
    fp = _fp(tmp_path, api_surface, feature_categories, """
    const gl = document.getElementById('c').getContext('webgl2');
    const flag = Math.random() > 0.5;
    const fs = flag ? `#version 300 es
    precision highp float; out vec4 o;
    void main() { o = vec4(reflect(vec3(1.0), vec3(0.0, 1.0, 0.0)), 1.0); }` : `#version 300 es
    precision highp float; out vec4 o;
    void main() { o = vec4(smoothstep(0.0, 1.0, 0.5)); }`;
    gl.shaderSource(gl.createShader(gl.FRAGMENT_SHADER), fs);""")
    assert {"reflect", "smoothstep"} <= fp["glsl_builtins"]


def _literals(js):
    from api_audit.parse import parse_js
    from api_audit.const_propagation import resolve_constants
    from api_audit.glsl import collect_literal_shader_sources
    root = parse_js(js)
    return collect_literal_shader_sources(root, resolve_constants(root))


def test_single_quoted_escapes_decoded():
    out = _literals(r"""const s = '#version 300 es\nprecision highp float;\nvoid main(){ gl_FragColor; }';""")
    assert out == ["#version 300 es\nprecision highp float;\nvoid main(){ gl_FragColor; }"]


def test_template_substitution_of_const():
    out = _literals("const N = 4; const s = `#version 300 es\nconst int n = ${N};\nvoid main(){}`;")
    assert "const int n = 4;" in out[0]


def test_user_defined_builtin_name_not_reported(tmp_path, api_surface, feature_categories):
    def body(shader):
        return f"""
        const gl = document.getElementById('c').getContext('webgl2');
        gl.shaderSource(gl.createShader(gl.FRAGMENT_SHADER), `#version 300 es
        precision highp float; out vec4 o;
        {shader}`);"""
    user = _fp(tmp_path, api_surface, feature_categories, body(
        "float sinh(float x) { return x; } void main() { o = vec4(sinh(1.0)); }"))
    builtin = _fp(tmp_path, api_surface, feature_categories, body(
        "void main() { o = vec4(sinh(1.0)); }"))
    assert "sinh" not in user["glsl_builtins"]
    assert "sinh" in builtin["glsl_builtins"]


def test_shader_source_identifier_without_glsl_marker(tmp_path, api_surface, feature_categories):
    # No '#version' / 'void main(' so only the shaderSource(s, ident) path can find it.
    fp = _fp(tmp_path, api_surface, feature_categories, """
    const gl = document.getElementById('c').getContext('webgl2');
    const frag = 'precision mediump float; vec4 f() { return gl_FragCoord; }';
    gl.shaderSource(gl.createShader(gl.FRAGMENT_SHADER), frag);""")
    assert "gl_FragCoord" in fp["glsl_variables"]


def test_collect_shader_sources_runs_once_per_file(monkeypatch, api_surface):
    from api_audit import usage_summary
    from api_audit.parse import parse_js
    calls = []
    real = usage_summary.collect_shader_sources
    monkeypatch.setattr(usage_summary, "collect_shader_sources",
                        lambda *a: calls.append(1) or real(*a))
    import api_audit.glsl as glsl
    monkeypatch.setattr(glsl, "collect_shader_sources",
                        lambda *a: calls.append(1) or real(*a))
    usage_summary.summarize_usage(parse_js("const gl = c.getContext('webgl2');"), api_surface)
    assert len(calls) == 1
