"""Tests for depth column formatting helpers."""
import pytest


def test_depth_summary_format():
    from feature_coverage import format_depth_summary
    result = format_depth_summary({"present": 3, "meaningful": 5, "deep": 2})
    assert result == "P:3 M:5 D:2"


def test_depth_summary_all_zero():
    from feature_coverage import format_depth_summary
    result = format_depth_summary({"present": 0, "meaningful": 0, "deep": 0})
    assert result == "P:0 M:0 D:0"


def test_depth_summary_only_deep():
    from feature_coverage import format_depth_summary
    result = format_depth_summary({"present": 0, "meaningful": 0, "deep": 10})
    assert result == "P:0 M:0 D:10"


def test_depth_summary_missing_keys():
    from feature_coverage import format_depth_summary
    result = format_depth_summary({})
    assert result == "P:0 M:0 D:0"
