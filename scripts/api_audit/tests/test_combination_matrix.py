import pytest
from api_audit.combination_matrix import (
    compute_matrix, identify_gaps, compute_priority_key,
    priority_label, is_topology_connected,
    merge_seed_into_matrix, generate_matrix_report,
)


class TestIsTopologyConnected:
    def _topology(self, edges):
        return {"edges": [{"pair": e} for e in edges]}

    def test_2way_direct_edge(self):
        t = self._topology([["A", "B"]])
        assert is_topology_connected(["A", "B"], t) is True

    def test_2way_no_edge(self):
        t = self._topology([["A", "C"]])
        assert is_topology_connected(["A", "B"], t) is False

    def test_3way_all_connected(self):
        t = self._topology([["A", "B"], ["B", "C"]])
        assert is_topology_connected(["A", "B", "C"], t) is True

    def test_3way_disconnected(self):
        t = self._topology([["A", "B"]])
        assert is_topology_connected(["A", "B", "C"], t) is False

    def test_single_feature(self):
        t = self._topology([])
        assert is_topology_connected(["A"], t) is True


class TestComputeMatrix:
    def test_basic_2way(self):
        corpus = {
            "seed1": {"features": ["A", "B"], "methods_per_feature": {"A": ["m1"], "B": ["m2"]}},
            "seed2": {"features": ["A"], "methods_per_feature": {"A": ["m1"]}},
            "seed3": {"features": ["B", "C"], "methods_per_feature": {"B": ["m2"], "C": ["m3"]}},
        }
        matrix = compute_matrix(corpus, n=2)
        assert matrix[("A", "B")]["seed_count"] == 1
        assert matrix[("A", "C")]["seed_count"] == 0
        assert matrix[("B", "C")]["seed_count"] == 1

    def test_distinct_fingerprints(self):
        corpus = {
            "seed1": {"features": ["A", "B"],
                       "methods_per_feature": {"A": ["m1"], "B": ["m2"]}},
            "seed2": {"features": ["A", "B"],
                       "methods_per_feature": {"A": ["m1", "m3"], "B": ["m2"]}},
        }
        matrix = compute_matrix(corpus, n=2)
        assert matrix[("A", "B")]["distinct_fingerprints"] == 2

    def test_topology_filtering(self):
        corpus = {
            "seed1": {"features": ["A", "B", "C"],
                       "methods_per_feature": {"A": ["m1"], "B": ["m2"], "C": ["m3"]}},
        }
        topology = {"edges": [{"pair": ["A", "B"]}]}
        matrix = compute_matrix(corpus, n=2, interaction_topology=topology)
        assert matrix[("A", "B")]["topology_connected"] is True
        assert matrix[("A", "C")]["topology_connected"] is False
        assert matrix[("A", "C")]["seed_count"] == 0  # disconnected = 0 seeds


class TestIdentifyGaps:
    def test_finds_zero_seed_gaps(self):
        matrix = {
            ("A", "B"): {"seed_count": 3, "topology_connected": True},
            ("A", "C"): {"seed_count": 0, "topology_connected": True},
        }
        gaps = identify_gaps(matrix, min_seeds=1)
        assert ("A", "C") in gaps
        assert ("A", "B") not in gaps


class TestPriorityKey:
    def test_non_ubiquitous_beats_ubiquitous(self):
        """Non-ubiquitous combo ranks above all-ubiquitous."""
        non_ubiq = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        all_ubiq = compute_priority_key(
            ("shader_pipeline", "draw_calls"), seed_count=0, depth_levels=[])
        assert non_ubiq > all_ubiq

    def test_connected_beats_disconnected(self):
        topology = {"edges": [{"pair": ["fbo", "texture_ops"]}]}
        connected = compute_priority_key(
            ("fbo", "texture_ops"), seed_count=0, depth_levels=[],
            interaction_topology=topology)
        disconnected = compute_priority_key(
            ("fbo", "sync"), seed_count=0, depth_levels=[],
            interaction_topology=topology)
        assert connected > disconnected

    def test_zero_seed_beats_thin(self):
        zero = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        thin = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=2, depth_levels=["present", "present"])
        assert zero > thin

    def test_more_security_beats_less(self):
        more = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        less = compute_priority_key(
            ("fbo", "sampler"), seed_count=0, depth_levels=[])
        assert more >= less  # fbo+buffer_ops has 2 security, fbo+sampler has 1

    def test_2way_beats_3way(self):
        two = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        three = compute_priority_key(
            ("fbo", "buffer_ops", "sampler"), seed_count=0, depth_levels=[])
        # 2-way has n_way_pref=-2, 3-way has -3; same security_count=2
        assert two > three

    def test_priority_label_skip_for_ubiquitous(self):
        key = compute_priority_key(
            ("shader_pipeline", "draw_calls"), seed_count=0, depth_levels=[])
        assert priority_label(key) == "skip"

    def test_priority_label_high_for_security_zero_seed(self):
        key = compute_priority_key(
            ("fbo", "buffer_ops"), seed_count=0, depth_levels=[])
        assert priority_label(key) == "high"

    def test_priority_label_medium_for_zero_seed_no_security(self):
        key = compute_priority_key(
            ("vao", "sampler"), seed_count=0, depth_levels=[])
        assert priority_label(key) == "medium"


class TestIncrementalMerge:
    def test_merge_updates_seed_count(self):
        baseline = {
            ("A", "B"): {"seed_count": 1, "seeds": ["s1"],
                          "distinct_fingerprints": 1,
                          "topology_connected": True},
        }
        new_fp = {"features": ["A", "B"], "file": "s2",
                  "methods_per_feature": {"A": ["m1"], "B": ["m2"]}}
        merge_seed_into_matrix(baseline, new_fp, n_way=2)
        assert baseline[("A", "B")]["seed_count"] == 2
        assert "s2" in baseline[("A", "B")]["seeds"]

    def test_merge_creates_new_combo(self):
        baseline = {}
        new_fp = {"features": ["X", "Y"], "file": "s1",
                  "methods_per_feature": {"X": ["mx"], "Y": ["my"]}}
        merge_seed_into_matrix(baseline, new_fp, n_way=2)
        assert ("X", "Y") in baseline
        assert baseline[("X", "Y")]["seed_count"] == 1

    def test_merge_tracks_distinct_fingerprints(self):
        baseline = {
            ("A", "B"): {"seed_count": 1, "seeds": ["s1"],
                          "distinct_fingerprints": 1,
                          "_fingerprint_set": {(("m1",), ("m2",))},
                          "topology_connected": True},
        }
        # Different methods = new fingerprint
        new_fp = {"features": ["A", "B"], "file": "s2",
                  "methods_per_feature": {"A": ["m1", "m3"], "B": ["m2"]}}
        merge_seed_into_matrix(baseline, new_fp, n_way=2)
        assert baseline[("A", "B")]["distinct_fingerprints"] == 2

    def test_merge_same_fingerprint_no_duplicate(self):
        baseline = {
            ("A", "B"): {"seed_count": 1, "seeds": ["s1"],
                          "distinct_fingerprints": 1,
                          "_fingerprint_set": {(("m1",), ("m2",))},
                          "topology_connected": True},
        }
        # Same methods = same fingerprint
        new_fp = {"features": ["A", "B"], "file": "s2",
                  "methods_per_feature": {"A": ["m1"], "B": ["m2"]}}
        merge_seed_into_matrix(baseline, new_fp, n_way=2)
        assert baseline[("A", "B")]["distinct_fingerprints"] == 1
        assert baseline[("A", "B")]["seed_count"] == 2


class TestGenerateReport:
    def test_report_structure(self):
        corpus = {
            "s1": {"features": ["A", "B"],
                    "methods_per_feature": {"A": ["m1"], "B": ["m2"]},
                    "feature_depth": {"A": "deep", "B": "present"}},
        }
        matrix = compute_matrix(corpus, n=2)
        report = generate_matrix_report(matrix, corpus)
        assert "total" in report
        assert "covered" in report
        assert "gaps" in report
        assert report["phase2_enriched"] is False
