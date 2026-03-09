"""Tests for coverage snapshot diff helpers."""
import pytest


def test_diff_coverage_added():
    from feature_coverage import diff_coverage_snapshots
    prev = {"fbo": {"seeds": 10, "pct": 5.0}, "sync": {"seeds": 3, "pct": 2.0}}
    curr = {"fbo": {"seeds": 15, "pct": 7.0}, "sync": {"seeds": 3, "pct": 2.0},
            "query": {"seeds": 2, "pct": 1.0}}
    result = diff_coverage_snapshots(prev, curr)
    assert result["changed"]["fbo"]["delta_seeds"] == 5
    assert result["changed"]["fbo"]["delta_pct"] == pytest.approx(2.0)
    assert "sync" not in result["changed"]
    assert "query" in result["new_features"]


def test_diff_coverage_removed():
    from feature_coverage import diff_coverage_snapshots
    prev = {"fbo": {"seeds": 5, "pct": 3.0}, "ubo": {"seeds": 2, "pct": 1.0}}
    curr = {"fbo": {"seeds": 5, "pct": 3.0}}
    result = diff_coverage_snapshots(prev, curr)
    assert "ubo" in result["removed_features"]


def test_diff_coverage_no_change():
    from feature_coverage import diff_coverage_snapshots
    snap = {"fbo": {"seeds": 5, "pct": 3.0}}
    result = diff_coverage_snapshots(snap, snap)
    assert result["changed"] == {}
    assert result["new_features"] == []
    assert result["removed_features"] == []


def test_diff_coverage_empty_prev():
    from feature_coverage import diff_coverage_snapshots
    curr = {"fbo": {"seeds": 5, "pct": 3.0}}
    result = diff_coverage_snapshots({}, curr)
    assert result["new_features"] == ["fbo"]
    assert result["changed"] == {}
    assert result["removed_features"] == []
