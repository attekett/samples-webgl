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
