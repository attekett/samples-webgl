"""Tests for GLSL per-builtin detail helpers."""


def test_aggregate_glsl_builtins_basic():
    from feature_coverage import aggregate_glsl_builtins
    fingerprints = [
        {"glsl_builtins": {"smoothstep", "texelFetch"}},
        {"glsl_builtins": {"smoothstep", "inverse"}},
        {"glsl_builtins": set()},
    ]
    result = aggregate_glsl_builtins(fingerprints)
    assert result["smoothstep"] == 2
    assert result["texelFetch"] == 1
    assert result["inverse"] == 1


def test_aggregate_glsl_builtins_empty():
    from feature_coverage import aggregate_glsl_builtins
    result = aggregate_glsl_builtins([])
    assert result == {}


def test_aggregate_glsl_builtins_missing_key():
    from feature_coverage import aggregate_glsl_builtins
    # fingerprint without glsl_builtins key is handled gracefully
    result = aggregate_glsl_builtins([{"features": ["fbo"]}])
    assert result == {}


def test_aggregate_glsl_builtins_none_entry():
    from feature_coverage import aggregate_glsl_builtins
    # None entries in the list are skipped gracefully
    result = aggregate_glsl_builtins([None, {"glsl_builtins": {"smoothstep"}}])
    assert result == {"smoothstep": 1}


def test_extract_scans_category_only_builtins(api_surface, feature_categories, tmp_path):
    """Builtins defined only in feature_categories.json (not in the api
    surface glsl_builtins map) must still be extracted from shader source."""
    from feature_coverage import analyze_file
    seed = tmp_path / "smoothstep.html"
    seed.write_text("""<!DOCTYPE html><html><body>
    <canvas id="c"></canvas><script>
    const gl = document.getElementById('c').getContext('webgl2');
    const fs = `#version 300 es
    precision highp float;
    out vec4 o;
    void main() {
        float a = smoothstep(0.0, 1.0, 0.5);
        vec3 r = reflect(vec3(1.0), vec3(0.0,1.0,0.0));
        float i = inversesqrt(2.0);
        o = vec4(r * a * i, 1.0);
    }`;
    const s = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(s, fs);
    </script></body></html>""")
    fp = analyze_file(seed, api_surface, feature_categories)
    assert fp is not None
    assert "smoothstep" in fp["glsl_builtins"]
    assert "reflect" in fp["glsl_builtins"]
    assert "inversesqrt" in fp["glsl_builtins"]
