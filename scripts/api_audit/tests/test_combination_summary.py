"""Tests for combination coverage summary helpers."""
import pytest


def test_combination_summary_counts():
    from feature_coverage import summarize_combinations
    matrix = {
        ("fbo", "sync"): {"seed_count": 3, "topology_connected": True},
        ("fbo", "query"): {"seed_count": 0, "topology_connected": True},
        ("sync", "query"): {"seed_count": 1, "topology_connected": True},
        ("fbo", "vao"): {"seed_count": 0, "topology_connected": False},
    }
    result = summarize_combinations(matrix)
    assert result["total"] == 4
    assert result["connected"] == 3
    assert result["covered"] == 2      # fbo+sync, sync+query (fbo+query is connected but 0 seeds)
    assert result["gap_count"] == 1    # fbo+query only (fbo+vao is disconnected)


def test_combination_summary_full_coverage():
    from feature_coverage import summarize_combinations
    matrix = {
        ("a", "b"): {"seed_count": 5, "topology_connected": True},
    }
    result = summarize_combinations(matrix)
    assert result["gap_count"] == 0
    assert result["pct"] == 100


def test_combination_summary_empty():
    from feature_coverage import summarize_combinations
    result = summarize_combinations({})
    assert result["total"] == 0
    assert result["covered"] == 0
    assert result["gap_count"] == 0
    assert result["pct"] == 0
