"""Tests for the passed-only seed filter."""
import json
from pathlib import Path
import pytest


def write_seed_pair(directory: Path, name: str, passed: bool) -> Path:
    """Write an HTML seed and its sibling JSON result file."""
    html = directory / f"{name}.html"
    js_result = directory / f"{name}.json"
    html.write_text("<html><body><script>const gl = null;</script></body></html>")
    js_result.write_text(json.dumps({"passed": passed, "console_logs": []}))
    return html


def test_is_passed_true(tmp_path):
    from feature_coverage import is_passed
    html = write_seed_pair(tmp_path, "seed_pass", passed=True)
    assert is_passed(html) is True


def test_is_passed_false(tmp_path):
    from feature_coverage import is_passed
    html = write_seed_pair(tmp_path, "seed_fail", passed=False)
    assert is_passed(html) is False


def test_is_passed_no_json(tmp_path):
    from feature_coverage import is_passed
    html = tmp_path / "seed_no_result.html"
    html.write_text("<html></html>")
    assert is_passed(html) is False


def test_is_passed_malformed_json(tmp_path):
    from feature_coverage import is_passed
    html = tmp_path / "seed.html"
    html.write_text("<html></html>")
    (tmp_path / "seed.json").write_text("not json {{{")
    assert is_passed(html) is False
