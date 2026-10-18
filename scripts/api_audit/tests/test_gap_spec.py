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


from api_audit.gap_spec import plan_batches


class TestPlanBatches:
    def _recipe(self, rid, features, priority="high"):
        return {
            "recipe_id": rid,
            "priority": priority,
            "target_features": features,
        }

    def test_high_priority_packed_first(self):
        recipes = [
            self._recipe("a", ["fbo"], priority="medium"),
            self._recipe("b", ["sampler"], priority="high"),
            self._recipe("c", ["renderbuffer"], priority="high"),
        ]
        batches = plan_batches(recipes, max_batches=1, max_per_batch=2)
        assert len(batches) == 1
        ids = [r["recipe_id"] for r in batches[0]["recipes"]]
        # Both high-priority recipes go in batch 1
        assert "b" in ids and "c" in ids
        assert "a" not in ids

    def test_feature_concentration_cap(self):
        # 4 recipes all targeting fbo — only 3 fit per batch
        recipes = [
            self._recipe(f"r{i}", ["fbo", f"other{i}"]) for i in range(4)
        ]
        batches = plan_batches(recipes, max_batches=2, max_per_batch=5)
        first_ids = [r["recipe_id"] for r in batches[0]["recipes"]]
        second_ids = [r["recipe_id"] for r in batches[1]["recipes"]]
        assert len(first_ids) == 3
        assert len(second_ids) == 1

    def test_max_per_batch_respected(self):
        recipes = [
            self._recipe(f"r{i}", [f"feat{i}"]) for i in range(10)
        ]
        batches = plan_batches(recipes, max_batches=2, max_per_batch=3)
        assert len(batches[0]["recipes"]) == 3
        assert len(batches[1]["recipes"]) == 3

    def test_max_batches_respected(self):
        recipes = [
            self._recipe(f"r{i}", [f"feat{i}"]) for i in range(20)
        ]
        batches = plan_batches(recipes, max_batches=2, max_per_batch=3)
        assert len(batches) == 2

    def test_empty_recipes_returns_empty(self):
        assert plan_batches([], max_batches=4, max_per_batch=5) == []

    def test_batch_id_starts_at_1(self):
        recipes = [self._recipe("r1", ["fbo"])]
        batches = plan_batches(recipes, max_batches=4, max_per_batch=5)
        assert batches[0]["batch_id"] == 1


from api_audit.gap_spec import generate_recipes


class TestGenerateRecipes:
    def _matrix_report(self):
        return {
            "total": 100,
            "covered": 50,
            "uncovered": 50,
            "gaps": [
                {"combo": ["fbo", "sampler", "ext_float_textures"],
                 "priority": "high", "seed_count": 0,
                 "topology_connected": True},
                {"combo": ["shader_pipeline", "draw_calls", "uniforms"],
                 "priority": "low", "seed_count": 0,
                 "topology_connected": True},
                {"combo": ["fbo", "renderbuffer"],
                 "priority": "high", "seed_count": 0,
                 "topology_connected": True},
            ],
        }

    def _categories(self):
        return {
            "categories": {
                "fbo": {"methods": ["createFramebuffer", "bindFramebuffer"]},
                "sampler": {"methods": ["createSampler", "bindSampler"]},
                "ext_float_textures": {"methods": ["getExtension"]},
                "renderbuffer": {"methods": ["createRenderbuffer"]},
                "shader_pipeline": {"methods": ["createProgram"]},
                "draw_calls": {"methods": ["drawArrays"]},
                "uniforms": {"methods": ["uniform1f"]},
            }
        }

    def _topology(self):
        return {"edges": [
            {"pair": ["fbo", "sampler"], "relationship": "fbo binds sampler"},
            {"pair": ["fbo", "renderbuffer"], "relationship": "fbo holds renderbuffer"},
            {"pair": ["ext_float_textures", "fbo"], "relationship": "float fbo"},
        ]}

    def test_emits_recipes_and_batches(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
            max_recipes=20, max_batches=4, max_per_batch=5,
        )
        assert "recipes" in out
        assert "batches" in out
        assert "n_way" in out
        assert out["n_way"] == 3
        assert "total_gaps_considered" in out
        assert "missing_categories" in out
        assert isinstance(out["recipes"], list)
        assert isinstance(out["batches"], list)

    def test_filters_irrelevant_gaps(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        # All-ubiquitous combo {shader_pipeline, draw_calls, uniforms} dropped
        ids = [r["target_features"] for r in out["recipes"]]
        assert ["draw_calls", "shader_pipeline", "uniforms"] not in ids
        assert sorted(["fbo", "sampler", "ext_float_textures"]) in ids

    def test_assigns_sequential_recipe_ids(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        ids = [r["recipe_id"] for r in out["recipes"]]
        assert ids == sorted(ids)
        assert ids[0].startswith("gap_")

    def test_high_priority_recipes_emitted_before_low(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        priorities = [r["priority"] for r in out["recipes"]]
        # Both relevant gaps in this fixture are "high" — confirm none are low
        assert "low" not in priorities

    def test_max_recipes_caps_output(self):
        # Build a matrix with 10 relevant gaps
        gaps = [
            {"combo": ["fbo", f"feat{i}"], "priority": "high", "seed_count": 0,
             "topology_connected": True}
            for i in range(10)
        ]
        cats = {"categories": {"fbo": {"methods": ["createFramebuffer"]}}}
        for i in range(10):
            cats["categories"][f"feat{i}"] = {"methods": [f"createF{i}"]}
        topo = {"edges": [
            {"pair": ["fbo", f"feat{i}"], "relationship": ""}
            for i in range(10)
        ]}
        out = generate_recipes(
            {"gaps": gaps}, corpus_features={},
            categories_config=cats,
            interaction_topology=topo,
            n_way=2,
            max_recipes=3,
        )
        assert len(out["recipes"]) == 3

    def test_total_gaps_considered_counts_input(self):
        out = generate_recipes(
            self._matrix_report(), corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        assert out["total_gaps_considered"] == 3

    def test_missing_categories_surfaced(self):
        # Gap targets a feature with no category definition
        gaps = [{"combo": ["fbo", "nonexistent_feature"],
                 "priority": "high", "seed_count": 0,
                 "topology_connected": True}]
        cats = {"categories": {"fbo": {"methods": ["createFramebuffer"]}}}
        topo = {"edges": [{"pair": ["fbo", "nonexistent_feature"],
                           "relationship": "synthetic"}]}
        out = generate_recipes(
            {"gaps": gaps}, corpus_features={},
            categories_config=cats,
            interaction_topology=topo, n_way=2,
        )
        assert "nonexistent_feature" in out["missing_categories"]

    def test_empty_gaps_returns_empty_recipes(self):
        out = generate_recipes(
            {"gaps": []}, corpus_features={},
            categories_config=self._categories(),
            interaction_topology=self._topology(),
            n_way=3,
        )
        assert out["recipes"] == []
        assert out["batches"] == []
        assert out["total_gaps_considered"] == 0
        assert out["n_way"] == 3


import json
import sys
from pathlib import Path


class TestCLIIntegration:
    def test_main_writes_recipes_json(self, tmp_path, monkeypatch):
        # Tiny synthetic corpus
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        (corpus / "seed1.html").write_text(
            "<html><body><script>"
            "const gl = canvas.getContext('webgl2');"
            "const fb = gl.createFramebuffer();"
            "gl.bindFramebuffer(gl.FRAMEBUFFER, fb);"
            "const s = gl.createSampler();"
            "gl.bindSampler(0, s);"
            "</script></body></html>"
        )

        # Tiny categories config — two real categories so a 2-way matrix exists
        cats = {"categories": {
            "fbo": {"methods": ["createFramebuffer", "bindFramebuffer"],
                    "min_methods_for_match": 1},
            "sampler": {"methods": ["createSampler", "bindSampler"],
                        "min_methods_for_match": 1},
        }}
        cats_path = tmp_path / "cats.json"
        cats_path.write_text(json.dumps(cats))

        topo = {"edges": [{"pair": ["fbo", "sampler"],
                           "relationship": "synthetic"}]}
        topo_path = tmp_path / "topo.json"
        topo_path.write_text(json.dumps(topo))

        # Minimal API surface: only the methods our seed calls
        surface = {"meta": {}, "constants": {},
                   "methods": {"createFramebuffer": {}, "bindFramebuffer": {},
                               "createSampler": {}, "bindSampler": {}},
                   "extensions": {}, "glsl_builtins": {}}
        surface_path = tmp_path / "surface.json"
        surface_path.write_text(json.dumps(surface))

        matrix_path = tmp_path / "matrix.json"
        recipes_path = tmp_path / "recipes.json"

        monkeypatch.setattr(sys, "argv", [
            "api_audit",
            "--surface", str(surface_path),
            "--corpus-dirs", str(corpus),
            "--feature-categories", str(cats_path),
            "--interaction-topology", str(topo_path),
            "--combination-matrix", str(matrix_path),
            "--gap-recipes", str(recipes_path),
            "--cache-dir", str(tmp_path / "cache"),
            "--n-way", "2",
            "--max-recipes", "5",
        ])

        from api_audit.__main__ import main
        main()

        assert recipes_path.exists()
        data = json.loads(recipes_path.read_text())
        assert "recipes" in data
        assert "batches" in data
        assert "n_way" in data
        assert data["n_way"] == 2
        assert "missing_categories" in data
        assert "generated_from_matrix" in data
        assert len(data["recipes"]) <= 5


class TestGateKeyRecipes:
    @pytest.fixture
    def cats(self, feature_categories):
        return feature_categories["categories"]

    def test_depth_textures_call_constant(self, cats):
        req, _ = split_required_bonus_methods(cats["depth_textures"])
        assert req[0] == "texImage2D(DEPTH_COMPONENT16)"
        assert "texImage2D" not in req

    def test_pbo_bind_buffer(self, cats):
        req, _ = split_required_bonus_methods(cats["pbo"])
        assert "bindBuffer(PIXEL_PACK_BUFFER)" in req

    def test_or_gate_is_bonus(self, cats):
        req, bon = split_required_bonus_methods(cats["depth_stencil"])
        assert "enable(DEPTH_TEST)" in bon and "enable(DEPTH_TEST)" not in req

    def test_glsl_patterns(self, cats):
        req, bon = split_required_bonus_methods(cats["glsl_fragment_kill_depth"])
        assert req == ["glsl:discard"]
        assert "glsl:gl_FragDepth" in bon

    def test_extension_before_glsl(self, cats):
        req, _ = split_required_bonus_methods(cats["ext_conservative_depth"])
        assert req == ["getExtension('EXT_conservative_depth')",
                       "glsl:depth_layout"]

    def test_marker_only(self, cats):
        req, _ = split_required_bonus_methods(cats["dom_texture_sources"])
        assert req == ["src:ImageData"]

    def test_constant_only(self, cats):
        req, _ = split_required_bonus_methods(cats["rasterizer_discard"])
        assert req == ["gl.RASTERIZER_DISCARD"]

    def test_every_category_has_required(self, cats):
        empty = [n for n, d in cats.items()
                 if not split_required_bonus_methods(d)[0]]
        assert empty == []

    def test_lane_restricted_method_is_bonus(self, cats):
        req, bon = split_required_bonus_methods(cats["drawing_buffer"])
        assert req == ["canvas:resize"]
        assert "drawingBufferStorage" in bon

    def test_no_missing_categories(self, cats):
        missing = set()
        gap = {"combo": ["glsl_ubo_layout", "fbo"], "priority": "high"}
        build_recipe(gap, cats, {}, {}, "gap_001", missing)
        assert missing == set()
