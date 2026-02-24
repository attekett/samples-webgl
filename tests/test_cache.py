import pytest
import json
from api_audit.cache import FileCache


class TestFileCache:
    def test_cache_hit(self, tmp_path):
        """Same content → cache hit, returns stored data."""
        cache = FileCache(tmp_path / 'cache')
        data = {'methods': {'drawArrays': 1}}
        cache.store('file.html', 'content_abc', data)
        result = cache.lookup('file.html', 'content_abc')
        assert result == data

    def test_cache_miss_different_content(self, tmp_path):
        """Modified content → cache miss."""
        cache = FileCache(tmp_path / 'cache')
        cache.store('file.html', 'content_v1', {'methods': {}})
        result = cache.lookup('file.html', 'content_v2')
        assert result is None

    def test_cache_dir_created(self, tmp_path):
        """Cache directory created automatically."""
        cache_dir = tmp_path / 'nonexistent' / 'cache'
        cache = FileCache(cache_dir)
        cache.store('f.html', 'content', {})
        assert cache_dir.exists()

    def test_layer2_hit(self, tmp_path):
        """Same surface + same aggregated data → Layer 2 hit."""
        cache = FileCache(tmp_path / 'cache')
        surface_hash = 'surface_abc'
        agg_hash = 'agg_xyz'
        report = {'tier1': ['method1']}
        cache.store_evaluation(surface_hash, agg_hash, report)
        result = cache.lookup_evaluation(surface_hash, agg_hash)
        assert result == report

    def test_layer2_miss_surface_change(self, tmp_path):
        """Changed surface JSON → Layer 2 miss."""
        cache = FileCache(tmp_path / 'cache')
        cache.store_evaluation('surface_v1', 'agg_xyz', {'tier1': []})
        result = cache.lookup_evaluation('surface_v2', 'agg_xyz')
        assert result is None
