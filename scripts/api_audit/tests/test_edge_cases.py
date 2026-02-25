"""Edge case tests for Phase 1 pipeline."""
import pytest
from api_audit.feature_detection import detect_features, is_category_match
from api_audit.combination_matrix import (
    compute_matrix, compute_priority_key, is_topology_connected,
)


class TestEdgeCases:
    def test_empty_seed_produces_empty_fingerprint(self):
        """Seed with no methods produces empty feature list."""
        result = detect_features(
            {"methods": {}, "constants": {}, "extension_methods": {}},
            set(),
            {"categories": {"buffer_ops": {
                "methods": ["createBuffer"],
                "constants": [],
                "min_methods_for_match": 1}}})
        assert result["features"] == []

    def test_empty_corpus_matrix(self):
        """Empty corpus produces empty matrix."""
        matrix = compute_matrix({}, n=2)
        assert matrix == {}

    def test_single_feature_corpus(self):
        """Corpus with only 1 feature produces no 2-way combos."""
        corpus = {
            "s1": {"features": ["A"], "methods_per_feature": {"A": ["m1"]}},
        }
        matrix = compute_matrix(corpus, n=2)
        assert len(matrix) == 0

    def test_priority_key_with_empty_depth(self):
        """Priority key handles empty depth_levels (zero-seed gap)."""
        key = compute_priority_key(("fbo", "buffer_ops"), 0, [])
        assert key[5] == 1.0  # depth_deficit = 1.0 for no seeds

    def test_priority_key_all_deep(self):
        """All deep coverage = minimum depth deficit."""
        key = compute_priority_key(
            ("fbo", "buffer_ops"), 5, ["deep", "deep"])
        assert key[5] == 0.0

    def test_category_match_empty_everything_min_zero(self):
        """Category with min_methods 0 and no gates always matches."""
        cat = {"methods": [], "constants": [], "min_methods_for_match": 0}
        match, _, _ = is_category_match(
            cat, set(), set(), set(), set(), set())
        assert match is True

    def test_very_large_combo_nway_pref(self):
        """4-way combo priority key has correct n_way_pref."""
        key = compute_priority_key(
            ("fbo", "buffer_ops", "sync", "transform_feedback"),
            0, [])
        assert key[4] == -4  # n_way_pref

    def test_topology_empty_edges(self):
        """Topology with no edges: all 2-way combos disconnected."""
        t = {"edges": []}
        assert is_topology_connected(["A", "B"], t) is False

    def test_topology_single_feature_always_connected(self):
        """Single-feature combo is always connected."""
        t = {"edges": []}
        assert is_topology_connected(["A"], t) is True

    def test_many_features_same_seed(self):
        """Corpus with one seed having many features produces many combos."""
        corpus = {
            "s1": {"features": ["A", "B", "C", "D"],
                    "methods_per_feature": {
                        "A": ["m1"], "B": ["m2"],
                        "C": ["m3"], "D": ["m4"]}},
        }
        matrix = compute_matrix(corpus, n=2)
        # C(4,2) = 6 combos
        assert len(matrix) == 6
        # All should have seed_count = 1
        assert all(d["seed_count"] == 1 for d in matrix.values())

    def test_priority_key_deterministic(self):
        """Same inputs always produce same priority key."""
        key1 = compute_priority_key(("fbo", "buffer_ops"), 0, ["present"])
        key2 = compute_priority_key(("fbo", "buffer_ops"), 0, ["present"])
        assert key1 == key2

    def test_detect_features_with_no_categories(self):
        """Empty categories config produces empty features."""
        result = detect_features(
            {"methods": {"createBuffer": 1}, "constants": {},
             "extension_methods": {}},
            set(),
            {"categories": {}})
        assert result["features"] == []

    def test_matrix_n3_with_two_features(self):
        """3-way matrix with only 2 distinct features produces empty matrix."""
        corpus = {
            "s1": {"features": ["A", "B"],
                    "methods_per_feature": {"A": ["m1"], "B": ["m2"]}},
        }
        matrix = compute_matrix(corpus, n=3)
        assert len(matrix) == 0
