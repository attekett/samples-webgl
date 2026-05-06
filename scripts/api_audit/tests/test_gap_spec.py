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


from api_audit.gap_spec import split_required_bonus_methods


class TestSplitMethods:
    def test_short_list_all_required(self):
        cat_def = {"methods": ["createA", "bindA", "deleteA"]}
        required, bonus = split_required_bonus_methods(cat_def)
        assert required == ["createA", "bindA", "deleteA"]
        assert bonus == []

    def test_long_list_split_at_five(self):
        cat_def = {
            "methods": ["m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8"]
        }
        required, bonus = split_required_bonus_methods(cat_def)
        assert required == ["m1", "m2", "m3", "m4", "m5"]
        assert bonus == ["m6", "m7", "m8"]

    def test_extension_methods_added_to_required(self):
        cat_def = {
            "methods": ["getExtension"],
            "extension_methods": ["drawArraysInstancedANGLE"],
        }
        required, bonus = split_required_bonus_methods(cat_def)
        assert "drawArraysInstancedANGLE" in required
        assert "getExtension" in required

    def test_glsl_functions_added_to_required(self):
        cat_def = {
            "methods": [],
            "glsl_functions": ["texture", "textureLod"],
        }
        required, bonus = split_required_bonus_methods(cat_def)
        assert "texture" in required
        assert "textureLod" in required

    def test_missing_methods_key_returns_empty(self):
        required, bonus = split_required_bonus_methods({})
        assert required == []
        assert bonus == []


from api_audit.gap_spec import build_recipe


class TestBuildRecipe:
    def _categories(self):
        return {
            "categories": {
                "fbo": {
                    "methods": ["createFramebuffer", "bindFramebuffer",
                                "framebufferTexture2D", "checkFramebufferStatus",
                                "blitFramebuffer", "readBuffer",
                                "deleteFramebuffer"],
                },
                "sampler": {
                    "methods": ["createSampler", "bindSampler",
                                "samplerParameteri", "deleteSampler",
                                "samplerParameterf"],
                },
                "ext_float_textures": {
                    "methods": ["getExtension"],
                    "extensions": ["OES_texture_float", "EXT_color_buffer_float"],
                },
            }
        }

    def _topology(self):
        return {
            "edges": [
                {"pair": ["fbo", "sampler"],
                 "relationship": "Sampler bound to texture read from FBO"},
                {"pair": ["ext_float_textures", "fbo"],
                 "relationship": "Float texture as FBO color attachment"},
            ]
        }

    def test_recipe_has_required_keys(self):
        gap = {"combo": ["fbo", "sampler", "ext_float_textures"],
               "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features={}, recipe_id="gap_001"
        )
        assert recipe["recipe_id"] == "gap_001"
        assert recipe["priority"] == "high"
        assert recipe["target_features"] == ["ext_float_textures", "fbo", "sampler"]
        assert recipe["topology_connected"] is True
        assert "reason" in recipe
        assert "required_methods" in recipe
        assert "bonus_methods" in recipe
        assert "topology_edges" in recipe
        assert "seed_constraints" in recipe
        assert "reference_seeds" in recipe

    def test_recipe_required_methods_per_feature(self):
        gap = {"combo": ["fbo", "sampler"], "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features={}, recipe_id="gap_002"
        )
        # fbo has 7 methods, top 5 are required
        assert recipe["required_methods"]["fbo"][:5] == [
            "createFramebuffer", "bindFramebuffer",
            "framebufferTexture2D", "checkFramebufferStatus",
            "blitFramebuffer",
        ]
        assert recipe["bonus_methods"]["fbo"] == [
            "readBuffer", "deleteFramebuffer"
        ]

    def test_recipe_topology_edges_filtered_to_combo(self):
        gap = {"combo": ["fbo", "sampler"], "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features={}, recipe_id="gap_003"
        )
        # Only the fbo<->sampler edge involves both target features
        assert len(recipe["topology_edges"]) == 1
        assert sorted(recipe["topology_edges"][0]["pair"]) == ["fbo", "sampler"]

    def test_recipe_includes_reference_seeds(self):
        corpus = {
            "agent_outputs/seedA.html": {
                "features": ["fbo", "sampler"],
                "depth_ratios": {"fbo": 0.8, "sampler": 0.8},
            },
        }
        gap = {"combo": ["fbo", "sampler"], "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features=corpus, recipe_id="gap_004"
        )
        assert recipe["reference_seeds"] == ["agent_outputs/seedA.html"]

    def test_recipe_seed_constraints_are_static(self):
        gap = {"combo": ["fbo", "sampler"], "priority": "high", "seed_count": 0}
        recipe = build_recipe(
            gap, self._categories(), self._topology(),
            corpus_features={}, recipe_id="gap_005"
        )
        c = recipe["seed_constraints"]
        assert c["tier1_vars"] == {"min": 5, "max": 8}
        assert c["tier3_enums"] == {"min": 4, "max": 6}
        assert c["try_catch_blocks"] == {"min": 6, "max": 10}
        assert c["line_repetition_patterns"] == {"min": 3}
        assert c["total_lines"] == {"min": 150, "max": 300}
