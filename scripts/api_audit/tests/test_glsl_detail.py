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
