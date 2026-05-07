"""Tests for API surface method coverage helpers."""


def test_compute_method_coverage_basic():
    from feature_coverage import compute_method_coverage
    surface_methods = {"createBuffer", "bindBuffer", "bufferData", "deleteBuffer"}
    seen_methods = {"createBuffer", "bindBuffer"}
    result = compute_method_coverage(surface_methods, seen_methods)
    assert result["total"] == 4
    assert result["exercised"] == 2
    assert result["pct"] == 50
    assert "bufferData" in result["never_seen"]
    assert "deleteBuffer" in result["never_seen"]
    assert "createBuffer" not in result["never_seen"]


def test_compute_method_coverage_empty_corpus():
    from feature_coverage import compute_method_coverage
    result = compute_method_coverage({"m1", "m2"}, set())
    assert result["exercised"] == 0
    assert result["pct"] == 0
    assert set(result["never_seen"]) == {"m1", "m2"}


def test_compute_method_coverage_full():
    from feature_coverage import compute_method_coverage
    methods = {"a", "b", "c"}
    result = compute_method_coverage(methods, methods)
    assert result["pct"] == 100
    assert result["never_seen"] == []


def test_compute_method_coverage_empty_surface():
    from feature_coverage import compute_method_coverage
    result = compute_method_coverage(set(), {"orphan"})
    assert result["total"] == 0
    assert result["pct"] == 0
    assert result["never_seen"] == []


def test_analyze_file_returns_uncategorized_methods(api_surface, feature_categories, tmp_path):
    """Methods called in a seed but not tied to any feature category must
    still appear in the file's all_methods set, so the API surface coverage
    report can see them."""
    from feature_coverage import analyze_file
    seed = tmp_path / "uncategorized.html"
    seed.write_text("""<!DOCTYPE html><html><body>
    <canvas id="c"></canvas><script>
    const gl = document.getElementById('c').getContext('webgl2');
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);
    gl.cullFace(gl.BACK);
    gl.frontFace(gl.CCW);
    gl.lineWidth(1.0);
    gl.polygonOffset(0, 0);
    gl.getError();
    gl.getExtension('OES_texture_float');
    </script></body></html>""")
    fp = analyze_file(seed, api_surface, feature_categories)
    assert fp is not None
    assert "all_methods" in fp
    for m in ("enable", "disable", "cullFace", "frontFace", "lineWidth",
              "polygonOffset", "getError", "getExtension"):
        assert m in fp["all_methods"], f"{m} missing from all_methods"
