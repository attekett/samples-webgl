"""Tests for gap_spec module — recipe generation from combination gaps."""
import pytest

from api_audit.gap_spec import is_relevant, derive_extension_categories


EXT_CATS = {"ext_float_textures", "ext_color_buffer_float",
            "ext_draw_buffers_indexed", "ext_texture_filter_anisotropic",
            "ext_compressed_textures", "ext_disjoint_timer_query"}


class TestDeriveExtensionCategories:
    def test_picks_categories_with_non_empty_extensions(self):
        cfg = {"categories": {
            "fbo": {"methods": ["createFramebuffer"]},
            "ext_float_textures": {"methods": ["getExtension"],
                                   "extensions": ["OES_texture_float"]},
            "ext_empty_list": {"extensions": []},
            "ext_anisotropic": {"extensions": ["EXT_texture_filter_anisotropic"]},
        }}
        assert derive_extension_categories(cfg) == {
            "ext_float_textures", "ext_anisotropic",
        }

    def test_accepts_flat_dict(self):
        flat = {"ext_float_textures": {"extensions": ["OES_texture_float"]}}
        assert derive_extension_categories(flat) == {"ext_float_textures"}


class TestIsRelevant:
    def test_all_ubiquitous_combo_skipped(self):
        assert is_relevant(
            ["shader_pipeline", "draw_calls", "uniforms"], EXT_CATS) is False

    def test_combo_with_one_non_ubiquitous_kept(self):
        assert is_relevant(
            ["shader_pipeline", "draw_calls", "fbo"], EXT_CATS) is True

    def test_extension_only_combo_without_security_skipped(self):
        assert is_relevant(["ext_float_textures",
                            "ext_texture_filter_anisotropic",
                            "ext_compressed_textures"], EXT_CATS) is False

    def test_extension_only_combo_with_security_kept(self):
        assert is_relevant(["ext_color_buffer_float",
                            "ext_float_textures",
                            "ext_compressed_textures"], EXT_CATS) is True

    def test_normal_mixed_combo_kept(self):
        assert is_relevant(["fbo", "sampler", "texture_ops"], EXT_CATS) is True


from api_audit.gap_spec import select_references


class TestSelectReferences:
    def test_picks_seed_with_most_overlap(self):
        corpus = {
            "seedA": {"features": ["fbo"], "depth_ratios": {"fbo": 0.5}},
            "seedB": {"features": ["fbo", "sampler"],
                      "depth_ratios": {"fbo": 0.5, "sampler": 0.5}},
            "seedC": {"features": ["fbo", "sampler", "ext_float_textures"],
                      "depth_ratios": {"fbo": 1.0, "sampler": 1.0, "ext_float_textures": 1.0}},
        }
        target = ["fbo", "sampler", "ext_float_textures"]
        refs = select_references(target, corpus, max_refs=1)
        assert refs == ["seedC"]

    def test_skips_seeds_with_no_overlap(self):
        corpus = {
            "seedX": {"features": ["draw_calls"], "depth_ratios": {"draw_calls": 1.0}},
        }
        refs = select_references(["fbo", "sampler"], corpus, max_refs=3)
        assert refs == []

    def test_breaks_ties_by_depth_score(self):
        corpus = {
            "shallow": {"features": ["fbo", "sampler"],
                        "depth_ratios": {"fbo": 0.1, "sampler": 0.1}},
            "deep": {"features": ["fbo", "sampler"],
                     "depth_ratios": {"fbo": 0.9, "sampler": 0.9}},
        }
        refs = select_references(["fbo", "sampler"], corpus, max_refs=1)
        assert refs == ["deep"]

    def test_caps_at_max_refs(self):
        corpus = {
            f"seed{i}": {"features": ["fbo"], "depth_ratios": {"fbo": 0.5}}
            for i in range(10)
        }
        refs = select_references(["fbo"], corpus, max_refs=3)
        assert len(refs) == 3
