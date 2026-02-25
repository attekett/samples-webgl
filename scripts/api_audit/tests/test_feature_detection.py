"""Tests for feature_detection module."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from api_audit.feature_detection import is_category_match, detect_features


# ---------------------------------------------------------------------------
# Mock dataclasses (avoid importing real call_analysis which needs tree-sitter)
# ---------------------------------------------------------------------------

@dataclass
class MockCallRecord:
    constants: set = field(default_factory=set)
    constant_roles: dict = field(default_factory=dict)
    arity: int = 0
    overload_tag: str = None


@dataclass
class MockCallAnalysis:
    methods: dict = field(default_factory=dict)
    extension_methods: dict = field(default_factory=dict)
    return_constants: set = field(default_factory=set)


# ---------------------------------------------------------------------------
# Shared fixture: load the real feature_categories.json
# ---------------------------------------------------------------------------

CATEGORIES_PATH = Path(__file__).resolve().parents[3] / "docs" / "feature_categories.json"


@pytest.fixture
def categories():
    data = json.loads(CATEGORIES_PATH.read_text())
    return data["categories"]


@pytest.fixture
def full_config():
    return json.loads(CATEGORIES_PATH.read_text())


# ---------------------------------------------------------------------------
# is_category_match tests
# ---------------------------------------------------------------------------

class TestIsCategoryMatch:
    """Tests for the is_category_match gate function."""

    def test_basic_method_match(self, categories):
        """One matching method passes when min_methods_for_match=1."""
        cat = categories["buffer_ops"]
        matched, matched_methods, count = is_category_match(
            cat,
            methods_found={"createBuffer"},
            constants_found=set(),
            extensions_loaded=set(),
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is True
        assert "createBuffer" in matched_methods
        assert count == 1

    def test_method_count_below_threshold(self, categories):
        """shader_pipeline needs min 2 methods; 1 is not enough."""
        cat = categories["shader_pipeline"]
        matched, matched_methods, count = is_category_match(
            cat,
            methods_found={"createShader"},
            constants_found=set(),
            extensions_loaded=set(),
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is False
        assert count == 0

    def test_requires_any_constant_rejects_when_missing(self, categories):
        """texture_arrays requires TEXTURE_2D_ARRAY constant; none present."""
        cat = categories["texture_arrays"]
        matched, _, _ = is_category_match(
            cat,
            methods_found={"texImage3D", "texStorage3D"},
            constants_found={"TEXTURE_3D"},
            extensions_loaded=set(),
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is False

    def test_requires_any_constant_passes_when_present(self, categories):
        """texture_arrays matches when TEXTURE_2D_ARRAY is present."""
        cat = categories["texture_arrays"]
        matched, matched_methods, count = is_category_match(
            cat,
            methods_found={"texImage3D", "texStorage3D"},
            constants_found={"TEXTURE_2D_ARRAY"},
            extensions_loaded=set(),
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is True
        assert count >= 1

    def test_requires_any_extension_rejects_when_missing(self, categories):
        """ext_float_textures requires an extension; none loaded."""
        cat = categories["ext_float_textures"]
        matched, _, _ = is_category_match(
            cat,
            methods_found=set(),
            constants_found=set(),
            extensions_loaded=set(),
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is False

    def test_requires_any_extension_passes_when_loaded(self, categories):
        """ext_float_textures matches when OES_texture_float is loaded."""
        cat = categories["ext_float_textures"]
        matched, _, _ = is_category_match(
            cat,
            methods_found=set(),
            constants_found=set(),
            extensions_loaded={"OES_texture_float"},
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is True

    def test_glsl_gate(self, categories):
        """glsl_builtins category requires min_glsl_for_match >= 1."""
        cat = categories["glsl_builtins"]
        # No GLSL builtins -> should fail
        matched, _, _ = is_category_match(
            cat,
            methods_found=set(),
            constants_found=set(),
            extensions_loaded=set(),
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is False

        # One GLSL builtin -> should pass
        matched, _, _ = is_category_match(
            cat,
            methods_found=set(),
            constants_found=set(),
            extensions_loaded=set(),
            glsl_found={"smoothstep"},
            extension_methods_found=set(),
        )
        assert matched is True

    def test_min_constants_for_match(self, categories):
        """integer_textures requires min_constants_for_match >= 1."""
        cat = categories["integer_textures"]
        # No matching constants
        matched, _, _ = is_category_match(
            cat,
            methods_found=set(),
            constants_found=set(),
            extensions_loaded=set(),
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is False

        # With a matching integer texture constant
        matched, _, _ = is_category_match(
            cat,
            methods_found=set(),
            constants_found={"RGBA8I"},
            extensions_loaded=set(),
            glsl_found=set(),
            extension_methods_found=set(),
        )
        assert matched is True

    def test_extension_methods_count_toward_method_count(self, categories):
        """ext_draw_buffers_indexed extension methods count toward method_count."""
        cat = categories["ext_draw_buffers_indexed"]
        matched, matched_methods, count = is_category_match(
            cat,
            methods_found=set(),
            constants_found=set(),
            extensions_loaded={"OES_draw_buffers_indexed"},
            glsl_found=set(),
            extension_methods_found={"enableiOES", "blendFunciOES"},
        )
        assert matched is True
        assert count == 2
        assert "enableiOES" in matched_methods
        assert "blendFunciOES" in matched_methods


# ---------------------------------------------------------------------------
# detect_features tests
# ---------------------------------------------------------------------------

class TestDetectFeatures:
    """Tests for the detect_features function."""

    def test_buffer_only_seed(self, full_config):
        """A seed using only buffer methods should detect buffer_ops."""
        analysis = MockCallAnalysis(
            methods={
                "createBuffer": [MockCallRecord(constants={"ARRAY_BUFFER"})],
                "bindBuffer": [MockCallRecord(constants={"ARRAY_BUFFER"})],
                "bufferData": [MockCallRecord(constants={"ARRAY_BUFFER"})],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert "buffer_ops" in result["features"]

    def test_depth_present(self, full_config):
        """1 out of 9 buffer_ops methods = 0.11 ratio -> present."""
        analysis = MockCallAnalysis(
            methods={
                "createBuffer": [MockCallRecord()],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert "buffer_ops" in result["features"]
        assert result["feature_depth"]["buffer_ops"] == "present"
        assert result["depth_ratios"]["buffer_ops"] == pytest.approx(1 / 9, abs=0.01)

    def test_depth_meaningful(self, full_config):
        """4 out of 9 buffer_ops methods = 0.44 ratio -> meaningful."""
        analysis = MockCallAnalysis(
            methods={
                "createBuffer": [MockCallRecord()],
                "bindBuffer": [MockCallRecord()],
                "bufferData": [MockCallRecord()],
                "bufferSubData": [MockCallRecord()],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert "buffer_ops" in result["features"]
        assert result["feature_depth"]["buffer_ops"] == "meaningful"
        assert result["depth_ratios"]["buffer_ops"] == pytest.approx(4 / 9, abs=0.01)

    def test_depth_deep(self, full_config):
        """7 out of 9 buffer_ops methods = 0.78 ratio -> deep."""
        analysis = MockCallAnalysis(
            methods={
                "createBuffer": [MockCallRecord()],
                "bindBuffer": [MockCallRecord()],
                "bufferData": [MockCallRecord()],
                "bufferSubData": [MockCallRecord()],
                "copyBufferSubData": [MockCallRecord()],
                "getBufferSubData": [MockCallRecord()],
                "deleteBuffer": [MockCallRecord()],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert "buffer_ops" in result["features"]
        assert result["feature_depth"]["buffer_ops"] == "deep"
        assert result["depth_ratios"]["buffer_ops"] == pytest.approx(7 / 9, abs=0.01)

    def test_small_category_depth_mrt(self, full_config):
        """mrt has only 1 method (drawBuffers); 1/1 = deep."""
        analysis = MockCallAnalysis(
            methods={
                "drawBuffers": [MockCallRecord()],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert "mrt" in result["features"]
        assert result["feature_depth"]["mrt"] == "deep"
        assert result["depth_ratios"]["mrt"] == pytest.approx(1.0, abs=0.01)

    def test_texture_arrays_requires_constant(self, full_config):
        """texture_arrays should NOT match without TEXTURE_2D_ARRAY constant."""
        analysis = MockCallAnalysis(
            methods={
                "texImage3D": [MockCallRecord(constants={"TEXTURE_3D"})],
                "texStorage3D": [MockCallRecord(constants={"TEXTURE_3D"})],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert "texture_arrays" not in result["features"]

    def test_texture_arrays_matches_with_constant(self, full_config):
        """texture_arrays matches when TEXTURE_2D_ARRAY constant is present."""
        analysis = MockCallAnalysis(
            methods={
                "texImage3D": [MockCallRecord(constants={"TEXTURE_2D_ARRAY"})],
                "texStorage3D": [MockCallRecord(constants={"TEXTURE_2D_ARRAY"})],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert "texture_arrays" in result["features"]

    def test_methods_per_feature_correctness(self, full_config):
        """methods_per_feature should contain the correct sorted method names."""
        analysis = MockCallAnalysis(
            methods={
                "createBuffer": [MockCallRecord()],
                "bindBuffer": [MockCallRecord()],
                "deleteBuffer": [MockCallRecord()],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert "buffer_ops" in result["methods_per_feature"]
        expected = ["bindBuffer", "createBuffer", "deleteBuffer"]
        assert result["methods_per_feature"]["buffer_ops"] == expected

    def test_dict_input_format(self, full_config):
        """detect_features should accept dict input from analyze_file()."""
        result_dict = {
            "methods": {"createBuffer": 2, "bindBuffer": 1, "bufferData": 1},
            "constants": {"ARRAY_BUFFER": {"target": 3}},
            "extension_methods": {},
        }
        result = detect_features(result_dict, set(), full_config)
        assert "buffer_ops" in result["features"]
        assert result["method_counts"]["buffer_ops"] == 3

    def test_dict_input_with_gl_prefix_constants(self, full_config):
        """Constants with gl. prefix should be stripped properly for dict input."""
        result_dict = {
            "methods": {"texImage3D": 1, "texStorage3D": 1},
            "constants": {"gl.TEXTURE_2D_ARRAY": {"target": 1}},
            "extension_methods": {},
        }
        result = detect_features(result_dict, set(), full_config)
        assert "texture_arrays" in result["features"]

    def test_extension_only_category_depth(self, full_config):
        """Extension-only categories (0 methods defined) are always 'deep'."""
        result = detect_features(
            MockCallAnalysis(),
            set(),
            full_config,
            extensions={"OES_texture_float"},
        )
        assert "ext_float_textures" in result["features"]
        assert result["feature_depth"]["ext_float_textures"] == "deep"
        assert result["depth_ratios"]["ext_float_textures"] == 1.0

    def test_glsl_only_category(self, full_config):
        """glsl_builtins category matches on GLSL functions."""
        result = detect_features(
            MockCallAnalysis(),
            {"smoothstep", "texelFetch"},
            full_config,
        )
        assert "glsl_builtins" in result["features"]
        assert result["feature_depth"]["glsl_builtins"] == "deep"

    def test_features_are_sorted(self, full_config):
        """The features list should be alphabetically sorted."""
        analysis = MockCallAnalysis(
            methods={
                "createBuffer": [MockCallRecord()],
                "viewport": [MockCallRecord()],
                "createTexture": [MockCallRecord()],
            }
        )
        result = detect_features(analysis, set(), full_config)
        assert result["features"] == sorted(result["features"])

    def test_extension_methods_in_detect(self, full_config):
        """Extension methods should be detected via extension_methods parameter."""
        result = detect_features(
            MockCallAnalysis(),
            set(),
            full_config,
            extensions={"OES_draw_buffers_indexed"},
            extension_methods={"enableiOES", "blendFunciOES"},
        )
        assert "ext_draw_buffers_indexed" in result["features"]
        assert result["method_counts"]["ext_draw_buffers_indexed"] == 2
