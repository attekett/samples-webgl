"""Tests for FileCache invalidation behaviour."""
import json
import tempfile
from pathlib import Path

import pytest

from api_audit.cache import FileCache


@pytest.fixture
def tmp_cache(tmp_path):
    return FileCache(tmp_path / "cache")


def test_store_and_lookup_same_config(tmp_cache):
    """Cache hit when both content and config hash are identical."""
    tmp_cache.store("f.html", "content", {"features": ["fbo"]}, config_hash="abc")
    result = tmp_cache.lookup("f.html", "content", config_hash="abc")
    assert result == {"features": ["fbo"]}


def test_different_config_hash_is_miss(tmp_cache):
    """Cache miss when config hash changes even if seed content is identical."""
    tmp_cache.store("f.html", "content", {"features": ["fbo"]}, config_hash="abc")
    result = tmp_cache.lookup("f.html", "content", config_hash="xyz")
    assert result is None


def test_different_content_is_miss(tmp_cache):
    """Cache miss when seed content changes."""
    tmp_cache.store("f.html", "contentA", {"features": ["fbo"]}, config_hash="abc")
    result = tmp_cache.lookup("f.html", "contentB", config_hash="abc")
    assert result is None


def test_no_config_hash_backward_compat(tmp_cache):
    """Empty config_hash (default) still works."""
    tmp_cache.store("f.html", "content", {"features": []})
    result = tmp_cache.lookup("f.html", "content")
    assert result == {"features": []}
