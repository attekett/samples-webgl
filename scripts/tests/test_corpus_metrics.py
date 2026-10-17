import json

import pytest

import corpus_metrics as metrics
import webgl_mutator


def _candidate(name, digest, req, cost=60000, flows=()):
    return {"id": name, "source_path": f"/{name}.html", "source_sha256": digest, "clean": True,
            "campaign_cost_ms": cost, "browser_ms": cost,
            "reduced": {"methods": [], "flow_patterns": list(flows), "value_classes": []}}


def test_selection_respects_caps_and_two_distinct_flow_carriers():
    flow = "flow:vao_switch_draw"
    a = _candidate("a", "a" * 64, {flow}, flows=["vao_switch_draw"])
    b = _candidate("b", "b" * 64, {flow}, flows=["vao_switch_draw"])
    single = metrics.select_manifest([a, b], {flow}, max_seeds=1, min_carriers=2)
    assert single["status"] == "infeasible"
    assert single["unmet_redundancy"] == [flow]
    two = metrics.select_manifest([a, b], {flow}, max_seeds=2, min_carriers=2)
    assert two["status"] == "selected"
    assert len(set(two["selected_hashes"])) == 2
    over_time = metrics.select_manifest([a, b], {flow}, budget_minutes=1, min_carriers=2)
    assert over_time["status"] == "infeasible"


def test_source_hash_dedup_and_missing_baseline_is_infeasible():
    duplicate = _candidate("same", "a" * 64, set())
    other_path = _candidate("copy", "a" * 64, set())
    result = metrics.select_manifest([duplicate, other_path], {"core:drawArrays"})
    assert result["status"] == "infeasible"
    assert result["selected"] == []
    assert result["unmet_baseline"] == ["core:drawArrays"]


def test_candidate_family_exposure_preserves_existing_replay():
    source = '<canvas></canvas><script>const gl = canvas.getContext("webgl2"); gl.drawArrays(gl.TRIANGLES, 0, 3);</script>'
    groups = webgl_mutator.candidate_families(source)
    candidates = [edit for group in groups.values() for edit in group]
    assert candidates
    edit = candidates[0]
    changed = webgl_mutator.apply_candidate(source, edit)
    assert changed != source
    assert webgl_mutator.replay(source.encode("utf-8"), {"edits": [edit]}) == changed.encode("utf-8")


def test_explicit_manifest_paths_and_hashes_are_checked(tmp_path):
    source = tmp_path / "seed.html"
    source.write_text("<script>gl.drawArrays(gl.TRIANGLES, 0, 3)</script>")
    manifest = tmp_path / "manifest.json"
    digest = metrics._hash(source.read_bytes())
    manifest.write_text(json.dumps({"seeds": [{"source_path": str(source), "source_sha256": digest}]}))
    assert metrics._manifest_paths(manifest) == [source.resolve()]
    manifest.write_text(json.dumps({"seeds": [{"source_path": str(source), "source_sha256": "0" * 64}]}))
    with pytest.raises(ValueError, match="manifest source hash mismatch"):
        metrics._manifest_paths(manifest)
    manifest.write_text(json.dumps({"seeds": [str(tmp_path / "missing.html")]}))
    with pytest.raises(ValueError, match="manifest source is missing"):
        metrics._manifest_paths(manifest)


def test_identical_source_copies_share_one_profile_representative(tmp_path):
    first_dir, second_dir = tmp_path / "a", tmp_path / "b"
    first_dir.mkdir()
    second_dir.mkdir()
    first, second = first_dir / "seed.html", second_dir / "copy.html"
    first.write_bytes(b"<canvas></canvas>")
    second.write_bytes(first.read_bytes())
    representatives, aliases = metrics._unique_sources_by_hash([second, first])
    assert representatives == [first.resolve()]
    assert aliases[str(first.resolve())] == [str(second.resolve())]


def _row(identifier, edit, *, signature=None, image=None, clean=True, browser_ms=100, flow_novel=False,
         image_novel=False):
    return {"id": identifier, "source_path": f"/{identifier}.html", "source_sha256": identifier * 64,
            "control_source_sha256": "s" * 64 if edit else None,
            "control_id": "control" if edit else None, "edits": edit,
            "clean": clean, "productive": flow_novel or image_novel,
            "flow_novel": flow_novel, "image_novel": image_novel, "browser_ms": browser_ms,
            "calibrated_browser_ms": browser_ms,
            "browser": {}, "profile": {"image_sha256": image, "image_hash_kind": "rgba_pixels"},
            "reduced": {"flow_signature": signature, "flow_patterns": [], "methods": [], "value_classes": [],
                        "extension_methods": {}, "overloads": [], "positive_draws": 1, "unresolved": [],
                        "reducer_version": metrics.REDUCER_VERSION}}


def test_report_deduplicates_signatures_pixels_and_groups_mixed_edits():
    control = _row("control", [], browser_ms=100)
    control["id"] = "control"
    control["source_sha256"] = "s" * 64
    variants = [
        _row("a", [{"operator": "numeric_boundary"}], signature="same", image="px", flow_novel=True, image_novel=True),
        _row("b", [{"operator": "numeric_boundary"}], signature="same", image="px", flow_novel=True, image_novel=True),
        _row("c", [{"operator": "numeric_boundary"}, {"operator": "array_shrink"}], signature="mixed", image="px2", flow_novel=True, image_novel=True),
        _row("d", [{"operator": "numeric_boundary"}], clean=False, browser_ms=900),
    ]
    for row in variants:
        row["control_id"] = "control"
    ledger = {"records": [control, *variants], "seed_families": {"/seed": {"families": {"numeric_boundary": 4}}},
              "lane": {}, "calibration": {"status": "calibrated"}}
    report = metrics.make_report(ledger, max_seeds=1)
    yields = report["mutation_yield"]
    assert yields["numeric_boundary"]["generated"] == 3
    assert yields["numeric_boundary"]["flow_distinct"] == 1
    assert yields["numeric_boundary"]["image_distinct"] == 1
    assert yields["numeric_boundary"]["browser_ms"] == 1100
    assert yields["mixed"]["generated"] == 1
    assert report["campaign_time"]["browser_ms"] == 1300
    assert report["campaign_time"]["includes_controls_variants_failures_and_recovery"] is True


def test_report_controls_only_ledger_keeps_unsampled_families_as_gaps():
    control = _row("control", [], browser_ms=100)
    control.update({"id": "control", "source_sha256": "s" * 64})
    ledger = {"records": [control], "seed_families": {"/seed": {"families": {"numeric_boundary": 3}}},
              "lane": {}, "calibration": {"status": "uncalibrated"}}
    report = metrics.make_report(ledger)
    item = report["mutation_yield"]["numeric_boundary"]
    assert item["eligible_sites"] == 3
    assert item["generated"] == 0
    assert item["flow_per_campaign_minute"] is None


def test_report_reconciles_inventory_measurement_counts_with_control_path_and_hash():
    control = _row("clean", [])
    control.update({"id": "clean", "source_path": "/corpus/clean.html", "source_sha256": "a" * 64})
    failed = _row("failed", [], clean=False)
    failed.update({"id": "failed", "source_path": "/corpus/failed.html", "source_sha256": "b" * 64})
    inventory = {"seed_count": 3, "unmeasured_count": 3, "seeds": [
        {"source_path": "/corpus/clean.html", "source_sha256": "a" * 64, "static_requirements": []},
        {"source_path": "/corpus/failed.html", "source_sha256": "b" * 64, "static_requirements": []},
        {"source_path": "/corpus/unmeasured.html", "source_sha256": "c" * 64, "static_requirements": []},
    ]}
    report = metrics.make_report({"records": [control, failed], "lane": {},
                                  "calibration": {"status": "uncalibrated"}}, inventory_data=inventory)
    assert report["inventory"]["measured_clean_count"] == 1
    assert report["inventory"]["measured_failed_count"] == 1
    assert report["inventory"]["unmeasured_count"] == 1


def test_calibration_requires_exact_lane_and_paired_output_hashes(tmp_path):
    output = "x" * 64
    lane = {"browser": "chromium", "browser_identity": {"fingerprint": "abc"}, "renderer": ["ANGLE"],
            "contexts": [], "profiler_version": "p1", "reducer_version": metrics.REDUCER_VERSION,
            "profile_event_cap": 20000, "outcome_cap": 2048}
    path = tmp_path / "calibration.json"
    records = [{"output_sha256": output, "profile": {"timing": {"navigation_to_completion_ms": 100}}}]
    path.write_text(json.dumps({"lane": lane, "records": [{"output_sha256": output, "duration_s": 0.2}]}))
    assert metrics._calibration(path, records, lane)["status"] == "calibrated"
    path.write_text(json.dumps({"lane": {**lane, "renderer": ["other"]}, "records": []}))
    with pytest.raises(ValueError, match="calibration lane identity"):
        metrics._calibration(path, records, lane)


def test_report_can_attach_new_exact_lane_calibration_without_reprofiling(tmp_path):
    output = "a" * 64
    lane = {"browser": "chromium", "browser_identity": {"fingerprint": "abc"}, "renderer": ["ANGLE"],
            "contexts": [], "profiler_version": "trace2", "reducer_version": metrics.REDUCER_VERSION,
            "profile_event_cap": 20000, "outcome_cap": 2048}
    calibration_file = tmp_path / "calibration.json"
    calibration_file.write_text(json.dumps({"lane": lane, "lane_verified": True,
        "records": [{"output_sha256": output, "duration_s": 0.4}]}))
    row = {"output_sha256": output, "browser_ms": 200,
           "profile": {"timing": {"navigation_to_completion_ms": 100}}}
    ledger = {"lane": lane, "records": [row], "total_browser_ms": 250}
    attached = metrics._apply_calibration(ledger, calibration_file)
    assert attached["calibration"]["status"] == "calibrated"
    assert row["calibrated_browser_ms"] == 800
    assert attached["total_calibrated_browser_ms"] == 1000
    calibration_file.write_text(json.dumps({"lane": lane, "lane_verified": False,
        "records": [{"output_sha256": output, "duration_s": 0.4}]}))
    with pytest.raises(ValueError, match="marked unverified"):
        metrics._apply_calibration(ledger, calibration_file)


def test_report_cli_validates_current_reduced_evidence_before_calibration(tmp_path):
    source = tmp_path / "control.html"
    source.write_text("<canvas></canvas>")
    identity = {"fingerprint": "current-lane", "event_cap": 20000, "outcome_cap": 2048}
    profile = {"profiler_version": "webgl-trace-2", "identity": identity,
               "contexts": [{"id": "c0", "version": 2, "extensions": [], "renderer": "ANGLE",
                             "vendor": "AMD", "renderer_verified": True}],
               "events": [{"seq": 1, "context": "c0", "method": "drawArrays", "args": [4, 0, 3]}],
               "outcomes": [], "truncated": False,
               "timing": {"navigation_to_completion_ms": 50}}
    profile_path = tmp_path / "control.profile.json"
    profile_path.write_text(json.dumps(profile))
    reduced = metrics.reduce_trace(profile, metrics._json(metrics.ROOT / "docs/webgl_api_surface.json", {}))
    row = {"id": "control", "source_path": str(source), "output_path": str(source),
           "source_sha256": metrics._hash(source.read_bytes()), "output_sha256": metrics._hash(source.read_bytes()),
           "edits": [], "control_id": None, "control_source_sha256": None,
           "result": {"completed": True, "passed": True, "errors": [], "warnings": [],
                      "console_logs": [], "javascript_errors": [], "webgl_errors": []},
           "profile": profile, "profile_path": str(profile_path), "reduced": reduced, "clean": True,
           "browser": identity, "browser_ms": 100, "context_versions": [2], "renderer": ["ANGLE"],
           "supported_extensions": []}
    lane = {"browser": "chromium", "browser_identity": identity, "renderer": ["ANGLE"],
            "contexts": metrics._lane_contexts([row]), "profiler_version": "webgl-trace-2",
            "reducer_version": metrics.REDUCER_VERSION, "profile_event_cap": 20000, "outcome_cap": 2048}
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps({"records": [row], "lane": lane,
        "settings": {"profile_event_cap": 20000, "outcome_cap": 2048,
                     "profiler_version": "webgl-trace-2", "reducer_version": metrics.REDUCER_VERSION},
        "calibration": {"status": "uncalibrated"}, "total_browser_ms": 100}))
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text(json.dumps({"lane": {key: lane[key] for key in (
        "browser", "browser_identity", "renderer", "contexts", "profiler_version", "reducer_version",
        "profile_event_cap", "outcome_cap")}, "lane_verified": True,
        "records": [{"output_sha256": row["output_sha256"], "duration_s": 0.1}]}))
    output = tmp_path / "report.json"
    assert metrics.main(["report", "--ledger", str(ledger_path), "--calibration", str(calibration_path),
                         "--output", str(output)]) == 0
    assert json.loads(output.read_text())["calibration"]["status"] == "calibrated"
    row["reduced"] = {**reduced, "flow_patterns": ["resource_delete_after_use"]}
    ledger_path.write_text(json.dumps({"records": [row], "lane": lane,
        "settings": {"profile_event_cap": 20000, "outcome_cap": 2048,
                     "profiler_version": "webgl-trace-2", "reducer_version": metrics.REDUCER_VERSION},
        "calibration": {"status": "uncalibrated"}, "total_browser_ms": 100}))
    with pytest.raises(ValueError, match="reduced profile evidence mismatch"):
        metrics.main(["report", "--ledger", str(ledger_path), "--calibration", str(calibration_path),
                      "--output", str(tmp_path / "invalid.json")])


def test_ledger_validation_rejects_source_hash_and_replay_sidecar_mismatch(tmp_path):
    source, output = tmp_path / "source.html", tmp_path / "variant.html"
    source.write_text("<canvas></canvas><script>const x = 1;</script>")
    output.write_text(source.read_text())
    identity = {"fingerprint": "id", "event_cap": 10}
    row = {"id": "test", "source_path": str(source), "output_path": str(source),
           "source_sha256": "bad", "output_sha256": metrics._hash(source.read_bytes()),
           "browser": identity, "profile": {"identity": identity, "events": [], "contexts": []},
           "context_versions": [], "renderer": [], "supported_extensions": [],
           "reduced": {"reducer_version": metrics.REDUCER_VERSION}}
    ledger = {"records": [row], "lane": {"browser_identity": identity}, "settings": {"profile_event_cap": 10,
              "reducer_version": metrics.REDUCER_VERSION}}
    with pytest.raises(ValueError, match="source_path hash mismatch"):
        metrics._validate_ledger(ledger)


def test_ledger_recomputes_reducer_and_rejects_forged_control_linkage(tmp_path):
    source = tmp_path / "seed.html"
    source.write_text("<canvas></canvas>")
    identity = {"fingerprint": "lane", "event_cap": 20000, "outcome_cap": 2048}
    profile = {"profiler_version": "webgl-trace-2", "identity": identity,
               "contexts": [{"id": "c0", "version": 2, "extensions": [], "renderer": "ANGLE",
                             "vendor": "AMD", "renderer_verified": True}],
               "events": [{"seq": 1, "context": "c0", "method": "drawArrays", "args": [4, 0, 3]}],
               "outcomes": [], "truncated": False}
    reduced = metrics.reduce_trace(profile, metrics._json(metrics.ROOT / "docs/webgl_api_surface.json", {}))
    result = {"completed": True, "passed": True, "errors": [], "warnings": [], "console_logs": [],
              "javascript_errors": [], "webgl_errors": []}
    control = {"id": "control", "source_path": str(source), "output_path": str(source),
               "source_sha256": metrics._hash(source.read_bytes()), "output_sha256": metrics._hash(source.read_bytes()),
               "edits": [], "control_id": None, "control_source_sha256": None, "result": result,
               "profile": profile, "reduced": reduced, "clean": True, "browser": identity,
               "context_versions": [2], "renderer": ["ANGLE"], "supported_extensions": []}
    lane = {"browser_identity": identity, "contexts": metrics._lane_contexts([control])}
    ledger = {"records": [control], "lane": lane,
              "settings": {"profile_event_cap": 20000, "outcome_cap": 2048,
                           "profiler_version": "webgl-trace-2", "reducer_version": metrics.REDUCER_VERSION}}
    metrics._validate_ledger(ledger, check_files=False)
    forged = {**control, "reduced": {**reduced, "flow_patterns": ["resource_delete_after_use"]}}
    with pytest.raises(ValueError, match="reduced profile evidence mismatch"):
        metrics._validate_ledger({**ledger, "records": [forged]}, check_files=False)
    variant = {**control, "id": "variant", "edits": [{"operator": "numeric_boundary"}],
               "control_id": "missing", "control_source_sha256": control["source_sha256"],
               "flow_novel": True, "image_novel": False, "productive": True}
    with pytest.raises(ValueError, match="variant control linkage mismatch"):
        metrics._validate_ledger({**ledger, "records": [control, variant]}, check_files=False)


def test_equal_time_comparison_rejects_lane_and_settings_mismatch():
    ledger = {"lane": {"browser": "chromium"}, "settings": {"rng_seed": 1}, "records": []}
    with pytest.raises(ValueError, match="different browser lanes"):
        metrics.compare_campaigns(ledger, {**ledger, "lane": {"browser": "firefox"}})
    with pytest.raises(ValueError, match="settings differ"):
        metrics.compare_campaigns(ledger, {**ledger, "settings": {"rng_seed": 2}})


def test_bounded_comparison_allows_different_manifests_and_uses_observed_prefix():
    lane = {"browser": "chromium", "browser_identity": {"fingerprint": "same"}}
    settings = {"rng_seed": 4, "samples_per_family": 1, "mixed_samples": 3, "max_edits": 3,
                "timeout_ms": 30000, "headless": True, "profile_event_cap": 20000,
                "outcome_cap": 2048, "campaign_seconds": 10}
    def control(identifier, digest):
        row = _row(identifier, [], browser_ms=100)
        row.update({"id": identifier, "source_sha256": digest, "campaign_end_ms": 100,
                    "reduced": {**row["reduced"], "methods": ["drawArrays"]}})
        return row
    def variant(identifier, control_id, digest, signature, end):
        row = _row(identifier, [{"operator": "numeric_boundary"}], signature=signature,
                    flow_novel=True, browser_ms=100)
        row.update({"id": identifier, "source_sha256": digest, "control_id": control_id,
                    "campaign_end_ms": end})
        return row
    baseline = {"lane": lane, "settings": settings, "campaign": {"mode": "bounded", "actual_wall_ms": 300},
                "calibration": {"status": "calibrated"},
                "records": [control("base-control", "a" * 64),
                            variant("base-v1", "base-control", "x" * 64, "flow-a", 200),
                            variant("base-v2", "base-control", "y" * 64, "flow-b", 250)]}
    current = {"lane": lane, "settings": settings, "campaign": {"mode": "bounded", "actual_wall_ms": 300},
               "calibration": {"status": "calibrated"},
               "records": [control("new-control", "b" * 64),
                           variant("new-v1", "new-control", "z" * 64, "flow-a", 200),
                           variant("new-v2", "new-control", "w" * 64, "flow-a", 250)]}
    comparison = metrics.compare_campaigns(current, baseline)
    assert comparison["preserves_baseline_requirements"]
    assert comparison["preserves_each_yield"] is False
    assert comparison["current"]["flow_distinct"] == 1
    assert comparison["baseline"]["flow_distinct"] == 2
    assert comparison["adoption_eligible"] is False


def test_equal_time_comparison_rejects_exhausted_campaigns_and_ignores_seed_context_union():
    lane = {"browser": "chromium", "browser_identity": {"fingerprint": "same"},
            "renderer": ["ANGLE"], "profiler_version": "trace2", "reducer_version": metrics.REDUCER_VERSION,
            "profile_event_cap": 20000, "outcome_cap": 2048, "contexts": [{"version": 2}]}
    settings = {"rng_seed": 0, "samples_per_family": 1, "mixed_samples": 2, "max_edits": 3,
                "timeout_ms": 30000, "headless": True, "profile_event_cap": 20000,
                "outcome_cap": 2048, "campaign_seconds": 5}
    base = {"lane": lane, "settings": settings, "campaign": {"mode": "bounded", "actual_wall_ms": 5000},
            "records": []}
    other_contexts = {**base, "lane": {**lane, "contexts": [{"version": 1}]}}
    assert metrics.compare_campaigns(base, other_contexts)["common_actual_wall_ms"] == 5000
    with pytest.raises(ValueError, match="full time budget"):
        metrics.compare_campaigns({**base, "campaign": {**base["campaign"], "exhausted": True}}, base)


def test_report_records_hashes_and_small_replay_metadata(tmp_path):
    output = tmp_path / "variant.html"
    output.write_text("<script></script>")
    profile = tmp_path / "variant.profile.json"
    profile.write_text("{}\n")
    sidecar = output.with_suffix(".mutation.json")
    sidecar.write_text('{"edits":[]}\n')
    row = _row("variant", [{"operator": "numeric_boundary"}], signature="f", flow_novel=True)
    row.update({"output_path": str(output), "output_sha256": metrics._hash(output.read_bytes()),
                "profile_path": str(profile), "campaign_end_ms": 50})
    summary = metrics._report_record(row)
    assert summary["output_sha256"] == metrics._hash(output.read_bytes())
    assert summary["profile_sha256"] == metrics._hash(profile.read_bytes())
    assert summary["mutation_sidecar_sha256"] == metrics._hash(sidecar.read_bytes())
    assert summary["edits"] == row["edits"]


def test_report_keeps_static_site_execution_unresolved_for_observed_methods():
    control = _row("control", [])
    control.update({"id": "control", "source_path": "/seed.html", "source_sha256": "s" * 64,
                   "reduced": {**control["reduced"], "extension_methods": {"WEBGL_multi_draw": ["multiDrawArraysWEBGL"]}}})
    call = {"method": "multiDrawArraysWEBGL", "kind": "extension", "extension": "WEBGL_multi_draw",
            "args": [{"index": 3, "status": "no_direct_edits", "eligible_edits": 0,
                      "direct_candidate_count": 0, "parameter_names": ["countsList"],
                      "wrapper_only_families": ["statement_wrapper"]}]}
    unexecuted_same_method_site = {**call, "start": 100, "end": 150,
                                   "args": [{**call["args"][0], "start": 130, "end": 136}]}
    call["start"], call["end"] = 10, 50
    call["args"][0].update({"start": 30, "end": 36})
    ledger = {"records": [control], "lane": {}, "calibration": {"status": "uncalibrated"},
              "seed_families": {"/seed.html": {"source_sha256": "s" * 64,
                  "families": {"state_toggle": 3}, "candidate_site_count": 3,
                  "argument_sites": [call, unexecuted_same_method_site]}}}
    report = metrics.make_report(ledger)
    seed = report["seed_candidate_sites"][0]
    assert seed["candidate_site_count"] == 3
    assert seed["method_observed_call_count"] == 2
    assert all(site["site_execution"] == "unresolved" for site in seed["argument_sites"])
    assert len(seed["static_gaps_for_observed_methods"]) == 2
    assert seed["static_gaps_for_observed_methods"][0]["parameter_names"] == ["countsList"]
    assert seed["static_gaps_for_observed_methods"][0]["wrapper_only_families"] == ["statement_wrapper"]


def test_markdown_gap_examples_prioritize_extension_then_resource_arguments():
    control = _row("control", [])
    control.update({"id": "control", "source_path": "/extension-seed.html", "source_sha256": "e" * 64,
                   "reduced": {**control["reduced"], "extension_methods": {"WEBGL_multi_draw": ["multiDrawArraysWEBGL"]},
                               "methods": ["bufferData", "drawArrays"]}})
    def call(method, kind, extension, parameter):
        return {"method": method, "kind": kind, "extension": extension,
                "args": [{"index": 1, "status": "no_direct_edits", "eligible_edits": 0,
                          "direct_candidate_count": 0, "parameter_names": [parameter]}]}
    ledger = {"records": [control], "lane": {}, "calibration": {"status": "uncalibrated"},
              "seed_families": {"/extension-seed.html": {"source_sha256": "e" * 64,
                  "families": {"state_toggle": 2}, "argument_sites": [
                      call("drawArrays", "core", None, "count"),
                      call("bufferData", "core", None, "size"),
                      call("multiDrawArraysWEBGL", "extension", "WEBGL_multi_draw", "countsList")]}}}
    markdown = metrics._markdown(metrics.make_report(ledger))
    assert markdown.index("WEBGL_multi_draw.multiDrawArraysWEBGL(countsList)") < markdown.index("bufferData(size)")
    assert "drawArrays(count)" in markdown


def test_markdown_shows_equal_time_campaign_yield_and_adoption_decision():
    comparison = {"common_actual_wall_ms": 12000,
                  "baseline": {"clean": 8, "flow_distinct": 3, "image_distinct": 2},
                  "current": {"clean": 9, "flow_distinct": 4, "image_distinct": 2},
                  "preserves_baseline_requirements": True, "preserves_each_yield": True,
                  "adoption_eligible": True}
    report = metrics.make_report({"records": [], "lane": {}}, comparison=comparison)
    report["campaign_comparison"]["adoption_eligible"] = True
    markdown = metrics._markdown(report)
    assert "## Equal-time campaign comparison" in markdown
    assert "Common observed wall time: 12000 ms." in markdown
    assert "| Clean variants | 8 | 9 |" in markdown
    assert "| Distinct flow changes | 3 | 4 |" in markdown
    assert "| Distinct pixel images | 2 | 2 |" in markdown
    assert "Baseline requirements preserved: **yes**." in markdown
    assert "Each yield preserved: **yes**." in markdown
    assert "Adoption eligible: **yes**." in markdown


def test_generic_value_denominator_exists_before_any_value_is_observed():
    requirements, _, _ = metrics._applicable_universe({"records": []}, {}, {}, {})
    for key in ("value:buffer_replacement:shrink", "value:buffer_replacement:grow",
                "value:buffer_replacement:same", "value:buffer_subdata_offset:end",
                "value:buffer_subdata_offset:out_of_bounds", "value:draw_mode:TRIANGLES",
                "value:buffer_usage:STATIC_DRAW", "value:buffer_target:COPY_WRITE_BUFFER"):
        assert key in requirements


def test_all_failed_contextless_profiles_keep_core_api_universe_unmeasured():
    failed = {"id": "failed", "edits": [], "clean": False,
              "profile": {"contexts": [], "events": [], "outcomes": [], "truncated": True},
              "reduced": {"methods": [], "value_classes": [], "flow_patterns": [], "unresolved": []}}
    report = metrics.make_report({"records": [failed]}, surface=metrics._json(
        metrics.ROOT / "docs/webgl_api_surface.json", {}),
        categories=metrics._json(metrics.ROOT / "docs/feature_categories.json", {}),
        topology=metrics._json(metrics.ROOT / "docs/interaction_topology.json", {}))
    statuses = report["requirement_status"]
    assert statuses["core:drawArrays"] == "unmeasured"
    assert statuses["core:createVertexArray"] == "unmeasured"
    overloads = [status for key, status in statuses.items() if key.startswith("overload:bufferData:")]
    assert overloads and set(overloads) == {"unmeasured"}
    assert "core:drawArrays" not in report["full_universe_gaps"]


def test_extension_eligibility_is_partitioned_by_context_version():
    surface = {"methods": {"drawArrays": {"webgl_version": 1, "overloads": []},
                           "createVertexArray": {"webgl_version": 2, "overloads": []}},
               "extensions": {"EXT_demo": {"methods": {"drawEXT": {}}}}}
    categories = {"categories": {"draw_calls": {"methods": ["drawArrays"]},
                                 "demo_extension": {"extension": "EXT_demo",
                                                    "extension_methods": ["drawEXT"]}}}
    topology = {"edges": [{"pair": ["draw_calls", "demo_extension"]}]}
    contexts = [{"id": "webgl1", "version": 1, "extensions": [], "renderer": "R", "vendor": "V"},
                {"id": "webgl2", "version": 2, "extensions": ["EXT_demo"], "renderer": "R", "vendor": "V"}]
    row = {"id": "c", "source_path": "/c.html", "source_sha256": "c" * 64,
           "edits": [], "clean": True,
           "profile": {"contexts": contexts, "truncated": False, "outcomes": [],
                       "events": [{"seq": 1, "context": "webgl1", "method": "drawArrays", "args": [4, 0, 3]},
                                  {"seq": 2, "context": "webgl2", "method": "createVertexArray", "args": []},
                                  {"seq": 3, "context": "webgl2", "method": "drawEXT", "extension": "EXT_demo",
                                   "args": []}]},
           "reduced": {"methods": ["drawArrays", "createVertexArray"],
                       "extension_methods": {"EXT_demo": ["drawEXT"]},
                       "overloads": [], "value_classes": [], "flow_patterns": []}}
    report = metrics.make_report({"records": [row]}, surface=surface, categories=categories, topology=topology)
    assert report["requirement_status"]["extension:EXT_demo:drawEXT"] == "covered"
    scopes = {(scope["version"], tuple(scope["supported_extensions"] or [])): scope["requirements"]
              for scope in report["context_requirement_status"]}
    assert scopes[(1, ())]["extension:EXT_demo:drawEXT"] == "unsupported"
    assert scopes[(2, ("EXT_demo",))]["extension:EXT_demo:drawEXT"] == "covered"
    selected_requirements = metrics._requirements(row, selection_scope=True)
    assert "context:v2:extension:EXT_demo:drawEXT" in selected_requirements
    assert "context:v1:extension:EXT_demo:drawEXT" not in selected_requirements


def test_unobserved_webgl1_scope_remains_unmeasured_when_webgl2_was_observed():
    surface = {"methods": {"drawArrays": {"webgl_version": 1, "overloads": []},
                           "createVertexArray": {"webgl_version": 2, "overloads": []}},
               "extensions": {"EXT_demo": {"methods": {"drawEXT": {}}}}}
    row = {"id": "c", "edits": [], "clean": True,
           "profile": {"contexts": [{"id": "webgl2", "version": 2, "extensions": ["EXT_demo"]}],
                       "events": [{"seq": 1, "context": "webgl2", "method": "drawEXT", "extension": "EXT_demo",
                                   "args": []}], "truncated": False, "outcomes": []},
           "reduced": {"methods": [], "extension_methods": {"EXT_demo": ["drawEXT"]},
                       "overloads": [], "value_classes": [], "flow_patterns": []}}
    scopes = metrics._context_requirement_statuses({"records": [row]}, surface, {}, {})
    webgl1 = next(scope for scope in scopes if scope["version"] == 1)
    assert webgl1["supported_extensions"] is None
    assert webgl1["requirements"]["core:drawArrays"] == "unmeasured"
    assert webgl1["requirements"]["extension:EXT_demo:drawEXT"] == "unmeasured"


def test_clean_profile_requires_completed_positive_work_draw():
    result = {"completed": True, "passed": True}
    profile = {"contexts": [{"id": "c0"}], "truncated": False, "outcomes": []}
    assert not metrics._profile_clean(result, profile, {"positive_draws": 0})
    assert metrics._profile_clean(result, profile, {"positive_draws": 1})
