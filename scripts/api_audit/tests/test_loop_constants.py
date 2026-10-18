"""Constants reached through gl-constant arrays, loop variables and subscripts."""

from feature_coverage import analyze_file


def _analyze(tmp_path, api_surface, feature_categories, body):
    seed = tmp_path / "seed.html"
    seed.write_text(f"""<!DOCTYPE html><html><body><canvas id="c"></canvas><script>
    const gl = document.getElementById('c').getContext('webgl2');
    let i = 0;
    {body}
    </script></body></html>""")
    return analyze_file(seed, api_surface, feature_categories)


def test_for_of_over_constant_array(tmp_path, api_surface, feature_categories):
    r = _analyze(tmp_path, api_surface, feature_categories,
                 "for (const t of [gl.TEXTURE_2D, gl.TEXTURE_3D]) gl.texStorage3D(t, 1, gl.RGBA8, 4, 4, 4);")
    assert "texture_3d" in r["features"]
    assert "TEXTURE_3D" in r["method_constants"]["texStorage3D"]


def test_foreach_callback(tmp_path, api_surface, feature_categories):
    r = _analyze(tmp_path, api_surface, feature_categories,
                 "const caps = [gl.DEPTH_TEST, gl.BLEND]; caps.forEach(c => gl.enable(c));")
    assert {"depth_stencil", "blending"} <= set(r["features"])


def test_subscript_of_constant_array(tmp_path, api_surface, feature_categories):
    r = _analyze(tmp_path, api_surface, feature_categories,
                 "const views = [gl.TEXTURE_2D_ARRAY]; const v = views[i % 1]; gl.texStorage3D(v, 1, gl.RGBA8, 4, 4, 4);")
    assert "texture_arrays" in r["features"]


def test_inner_parameter_shadows_loop_variable(tmp_path, api_surface, feature_categories):
    r = _analyze(tmp_path, api_surface, feature_categories,
                 """for (const t of [gl.TEXTURE_3D]) {
                      function f(t) { gl.texStorage3D(t, 1, gl.RGBA8, 4, 4, 4); }
                    }""")
    assert "TEXTURE_3D" not in r["method_constants"].get("texStorage3D", [])
    assert "texture_3d" not in r["features"]


def test_string_array_still_loads_extension(tmp_path, api_surface, feature_categories):
    r = _analyze(tmp_path, api_surface, feature_categories,
                 "const REQUIRED_EXTENSIONS = ['EXT_color_buffer_float']; REQUIRED_EXTENSIONS.forEach(e => gl.getExtension(e));")
    assert "EXT_color_buffer_float" in r["requested_extensions"]


def test_direct_subscript_argument(tmp_path, api_surface, feature_categories):
    r = _analyze(tmp_path, api_surface, feature_categories,
                 "const views = [gl.TEXTURE_2D_ARRAY]; gl.texStorage3D(views[i], 1, gl.RGBA8, 4, 4, 4);"
                 "gl.texStorage3D([gl.TEXTURE_3D][i], 1, gl.RGBA8, 4, 4, 4);")
    assert {"TEXTURE_2D_ARRAY", "TEXTURE_3D"} <= set(r["method_constants"]["texStorage3D"])


def test_identifier_elements_of_inline_array(tmp_path, api_surface, feature_categories):
    r = _analyze(tmp_path, api_surface, feature_categories,
                 "const A = gl.TEXTURE_3D; for (const t of [A, gl.TEXTURE_2D_ARRAY]) "
                 "gl.texStorage3D(t, 1, gl.RGBA8, 4, 4, 4);")
    assert {"TEXTURE_3D", "TEXTURE_2D_ARRAY"} <= set(r["method_constants"]["texStorage3D"])


def test_comment_inside_constant_array(tmp_path, api_surface, feature_categories):
    r = _analyze(tmp_path, api_surface, feature_categories,
                 "for (const t of [gl.TEXTURE_2D, /* x */ gl.TEXTURE_3D]) gl.texStorage3D(t, 1, gl.RGBA8, 4, 4, 4);")
    assert "TEXTURE_3D" in r["method_constants"]["texStorage3D"]
