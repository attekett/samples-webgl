"""Inventory, profile, compare, and select WebGL mutation corpus seeds."""

import argparse
import asyncio
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import feature_coverage
from api_audit.cache import FileCache
from api_audit.flow_reducer import REDUCER_VERSION, reduce_trace
from api_audit.site_coverage import analyze_sites
import webgl_mutator


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def _canonical_html(paths):
    found = {}
    for path in paths:
        path = Path(path)
        if path.is_dir():
            candidates = path.rglob("*.html")
        else:
            candidates = [path] if path.suffix.lower() == ".html" else []
        for candidate in candidates:
            if candidate.is_file():
                canonical = candidate.resolve()
                found[str(canonical)] = canonical
    return [found[key] for key in sorted(found)]


def inventory(paths, surface_path, categories_path, topology_path, cache_dir=None):
    surface = _json(surface_path, {})
    categories = _json(categories_path, {})
    topology = _json(topology_path, {})
    cache = FileCache(cache_dir) if cache_dir else None
    seeds = []
    for path in _canonical_html(paths):
        try:
            fingerprint = feature_coverage.static_fingerprint(path, surface, categories, cache)
            if fingerprint is not None:
                seeds.append({**fingerprint, "measurement": "unmeasured"})
        except (OSError, ValueError, SyntaxError) as exc:
            seeds.append({"source_path": str(path), "source_sha256": _hash(path.read_bytes()),
                          "measurement": "static_error", "error": str(exc)})
    return {"schema_version": 1, "kind": "inventory", "surface_sha256": _hash(Path(surface_path).read_bytes()),
            "seeds": seeds, "seed_count": len(seeds), "unmeasured_count": len(seeds)}


def _manifest_paths(manifest):
    path = Path(manifest)
    if path.is_dir():
        return _canonical_html([path])
    if path.suffix.lower() == ".html":
        if not path.is_file():
            raise ValueError(f"manifest source is missing: {path}")
        return _canonical_html([path])
    data = _json(path)
    if isinstance(data, dict):
        data = data.get("seeds", data.get("manifest", []))
    if not isinstance(data, list):
        raise ValueError(f"manifest must be a directory, HTML file, or JSON list: {path}")
    explicit = []
    for item in data:
        source_path = Path(item if isinstance(item, str) else item["source_path"])
        if not source_path.is_file() or source_path.suffix.lower() != ".html":
            raise ValueError(f"manifest source is missing or not an HTML file: {source_path}")
        expected_hash = item.get("source_sha256") if isinstance(item, dict) else None
        if expected_hash and _hash(source_path.read_bytes()) != expected_hash:
            raise ValueError(f"manifest source hash mismatch: {source_path}")
        explicit.append(source_path)
    return _canonical_html(explicit)


def _unique_sources_by_hash(paths):
    """Choose one stable canonical source path for each byte-identical input."""
    grouped = defaultdict(list)
    for path in paths:
        canonical = Path(path).resolve()
        grouped[_hash(canonical.read_bytes())].append(canonical)
    representatives, aliases = [], {}
    for digest, copies in sorted(grouped.items()):
        copies = sorted(set(copies), key=str)
        representative = copies[0]
        representatives.append(representative)
        aliases[str(representative)] = [str(path) for path in copies[1:]]
    return representatives, aliases


def _profile_clean(result, profile, reduced=None):
    if not result or not profile or result.get("completed") is not True or not result.get("passed"):
        return False
    if any(result.get(key) for key in ("errors", "javascript_errors", "console_logs", "webgl_errors", "warnings")):
        return False
    invalid = {"missing_completion", "context_lost", "seed_webgl_error", "remaining_webgl_error",
               "event_buffer_full", "outcome_buffer_full", "error_drain_incomplete",
               "profiler_error", "navigation_failed", "runner_error", "no_positive_work_draw"}
    if any(outcome.get("code") in invalid for outcome in profile.get("outcomes", [])):
        return False
    return (bool(profile.get("contexts")) and not profile.get("truncated") and
            (reduced is None or reduced.get("positive_draws", 0) > 0))


def _run_record(result, source_path, output_path, source_sha256, output_sha256, edits=None, control=None):
    if _hash(Path(source_path).read_bytes()) != source_sha256:
        raise ValueError(f"source hash changed during profiling: {source_path}")
    if _hash(Path(output_path).read_bytes()) != output_sha256:
        raise ValueError(f"profiled output hash mismatch: {output_path}")
    raw = result.get("webgl_profile") or {}
    reduced = reduce_trace(raw, _json(ROOT / "docs/webgl_api_surface.json", {}))
    clean = _profile_clean(result, raw, reduced) and reduced["profile_clean"]
    browser = raw.get("identity", raw.get("browser", {}))
    return {
        "source_path": str(Path(source_path).resolve()), "output_path": str(Path(output_path).resolve()),
        "source_sha256": source_sha256, "output_sha256": output_sha256,
        "candidate_sites": {}, "edits": edits or [], "control_source_sha256": control,
        "result": {key: result.get(key) for key in ("passed", "completed", "duration_ms", "errors", "warnings",
                     "console_logs", "javascript_errors", "webgl_errors", "browser_info")},
        "profile": raw, "reduced": reduced, "clean": clean,
        "browser_ms": result.get("duration_ms", 0),
        "browser": browser,
        "renderer": sorted({str(c.get("renderer", "")) for c in raw.get("contexts", [])}),
        "context_versions": sorted({c.get("version") for c in raw.get("contexts", [])}),
        "supported_extensions": sorted({ext for c in raw.get("contexts", []) for ext in c.get("extensions", [])}),
    }


async def _profile_async(seeds, output, browser, browser_config, args):
    from webgl_test_runner import WebGPUTestRunner

    seeds, source_aliases = _unique_sources_by_hash(seeds)
    output = Path(output)
    variants_dir = output / "variants"
    raw_dir = output / "profiles"
    variants_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    control_specs, variants_by_seed, seed_data = [], defaultdict(list), {}
    for seed in seeds:
        original = seed.read_bytes()
        seed_hash = _hash(original)
        source = original.decode("utf-8")
        base_id = seed_hash[:12]
        seed_data[str(seed)] = {"source_sha256": seed_hash, "families": {}, "control_id": base_id}
        control_specs.append({"id": base_id, "source_path": seed, "output_path": seed, "source_sha256": seed_hash,
                              "output_sha256": seed_hash, "edits": [], "control": None})
        families = webgl_mutator.candidate_families(source)
        seed_data[str(seed)]["families"] = {name: len(items) for name, items in sorted(families.items())}
        seed_data[str(seed)]["candidate_site_count"] = sum(seed_data[str(seed)]["families"].values())
        seed_data[str(seed)]["argument_sites"] = _name_site_arguments(
            analyze_sites(original, families), _json(ROOT / "docs/webgl_api_surface.json", {}))
        seed_data[str(seed)]["source_aliases"] = source_aliases.get(str(seed.resolve()), [])
        control_specs[-1]["candidate_sites"] = seed_data[str(seed)]["families"]
        control_specs[-1]["argument_sites"] = seed_data[str(seed)]["argument_sites"]
        for family, candidates in sorted(families.items()):
            rng_seed = int(_hash(f"{args.rng_seed}:{seed_hash}:{family}".encode())[:16], 16)
            random.Random(rng_seed).shuffle(candidates)
            for index, candidate in enumerate(candidates[:args.samples_per_family]):
                edited = webgl_mutator.apply_candidate(source, candidate).encode("utf-8")
                variant_id = f"{base_id}-{family}-{index}"
                variant_path = variants_dir / f"{variant_id}.html"
                variant_path.write_bytes(edited)
                sidecar = {"source_path": str(seed), "source_sha256": seed_hash, "output_sha256": _hash(edited),
                           "seed": args.rng_seed, "arm": "valid", "edits": [candidate]}
                variant_path.with_suffix(".mutation.json").write_text(json.dumps(sidecar, indent=2) + "\n")
                variants_by_seed[str(seed)].append({"id": variant_id, "source_path": seed, "output_path": variant_path,
                                                     "source_sha256": seed_hash, "output_sha256": _hash(edited),
                                                     "edits": [candidate], "control": base_id,
                                                     "candidate_sites": seed_data[str(seed)]["families"]})
        for index in range(args.mixed_samples):
            rng_seed = int(_hash(f"{args.rng_seed}:{seed_hash}:mixed:{index}".encode())[:16], 16)
            edited_html, edits = webgl_mutator.mutate_bytes(original, random.Random(rng_seed),
                                                             max_edits=args.max_edits)
            edited = edited_html
            variant_id = f"{base_id}-mixed-{index}"
            variant_path = variants_dir / f"{variant_id}.html"
            variant_path.write_bytes(edited)
            sidecar = {"source_path": str(seed), "source_sha256": seed_hash, "output_sha256": _hash(edited),
                       "seed": rng_seed, "arm": "valid", "edits": edits}
            variant_path.with_suffix(".mutation.json").write_text(json.dumps(sidecar, indent=2) + "\n")
            variants_by_seed[str(seed)].append({"id": variant_id, "source_path": seed, "output_path": variant_path,
                                                 "source_sha256": seed_hash, "output_sha256": _hash(edited),
                                                 "edits": edits, "control": base_id,
                                                 "candidate_sites": seed_data[str(seed)]["families"]})

    specs = list(control_specs)
    seed_keys = sorted(variants_by_seed)
    offset = 0
    while any(offset < len(variants_by_seed[key]) for key in seed_keys):
        for key in seed_keys:
            if offset < len(variants_by_seed[key]):
                specs.append(variants_by_seed[key][offset])
        offset += 1
    planned_spec_count = len(specs)

    runner = WebGPUTestRunner(test_dir=str(output), timeout=args.timeout, headless=args.headless,
                              browser_config=browser_config, force_firefox=args.force_firefox,
                              capture_screenshots=True, max_workers=1, profile_webgl=True,
                              profile_event_cap=args.profile_event_cap)
    campaign_started = time.perf_counter()
    case_times, end_times = {}, {}
    if args.campaign_seconds is None:
        results = await runner.run_tests([str(spec["output_path"]) for spec in specs], [browser])
        campaign_elapsed_ms = (time.perf_counter() - campaign_started) * 1000
        result_by_path = {str(Path(item.test_path).resolve()): item.to_dict() for item in results}
    else:
        runner.timeout = args.timeout
        result_by_path, case_times, end_times, campaign_elapsed_ms = await _run_bounded(
            runner, specs, browser, args.campaign_seconds, campaign_started)
        specs = [spec for spec in specs if str(spec["output_path"].resolve()) in result_by_path]
    records, by_id = [], {}
    total_browser_ms = 0
    for spec in specs:
        row = result_by_path[str(spec["output_path"].resolve())]
        record = _run_record(row, spec["source_path"], spec["output_path"], spec["source_sha256"],
                             spec["output_sha256"], spec["edits"], spec["source_sha256"] if spec["control"] else None)
        record["id"] = spec["id"]
        record["control_id"] = spec["control"]
        record["candidate_sites"] = spec.get("candidate_sites", {})
        record["argument_sites"] = spec.get("argument_sites", [])
        if args.campaign_seconds is not None:
            record["browser_ms"] = case_times.get(str(spec["output_path"].resolve()), 0)
            record["campaign_end_ms"] = end_times.get(str(spec["output_path"].resolve()))
        total_browser_ms += record["browser_ms"]
        raw_path = raw_dir / f"{spec['id']}.profile.json"
        raw_path.write_text(json.dumps(record["profile"], indent=2, sort_keys=True) + "\n")
        record["profile_path"] = str(raw_path)
        by_id[spec["id"]] = record
        records.append(record)
    if records and args.campaign_seconds is not None:
        setup_and_close_ms = max(0, campaign_elapsed_ms - sum(row["browser_ms"] for row in records))
        records[0]["browser_ms"] += setup_and_close_ms / 2
        records[-1]["browser_ms"] += setup_and_close_ms / 2
    elif records:
        case_weights = [max(float(row["browser_ms"] or 0), 1.0) for row in records]
        weight_total = sum(case_weights)
        for row, weight in zip(records, case_weights):
            row["browser_ms"] = round(campaign_elapsed_ms * weight / weight_total, 3)
    control_records = {row["id"]: row for row in records if not row["edits"]}
    for row in records:
        if not row["edits"]:
            continue
        control = control_records.get(row.get("control_id"))
        row["flow_novel"] = bool(control and row["clean"] and control["clean"] and
                                 row["reduced"].get("flow_signature") != control["reduced"].get("flow_signature"))
        row["image_novel"] = bool(control and row["clean"] and control["clean"] and
                                 row["profile"].get("image_hash_kind") == "rgba_pixels" and
                                 control["profile"].get("image_hash_kind") == "rgba_pixels" and
                                 row["profile"].get("image_sha256") != control["profile"].get("image_sha256"))
        row["productive"] = row["flow_novel"] or row["image_novel"]
    profile0 = records[0]["profile"] if records else {}
    lane = {"browser": browser, "browser_identity": records[0]["browser"] if records else {},
            "renderer": sorted({renderer for row in records for renderer in row["renderer"]}),
            "context_versions": sorted({version for row in records for version in row["context_versions"]}),
            "contexts": _lane_contexts(records),
            "profiler_version": profile0.get("profiler_version"),
            "reducer_version": REDUCER_VERSION,
            "profile_event_cap": args.profile_event_cap,
            "outcome_cap": profile0.get("identity", {}).get("outcome_cap")}
    calibration = _calibration(args.calibration, records, lane)
    if calibration.get("status") == "calibrated":
        factor = calibration["median_grizzly_per_profile"]
        for row in records:
            row["calibrated_browser_ms"] = round(row["browser_ms"] * factor, 3)
    ledger = {"schema_version": 1, "kind": "profile_ledger", "lane": lane,
              "settings": {"rng_seed": args.rng_seed, "samples_per_family": args.samples_per_family,
                           "mixed_samples": args.mixed_samples, "max_edits": args.max_edits,
                           "timeout_ms": args.timeout, "headless": args.headless,
                           "campaign_seconds": args.campaign_seconds,
                           "profile_event_cap": args.profile_event_cap,
                           "outcome_cap": profile0.get("identity", {}).get("outcome_cap"),
                           "profiler_version": records[0]["profile"].get("profiler_version") if records else None,
                           "reducer_version": REDUCER_VERSION},
              "calibration": calibration, "records": records,
              "total_browser_ms": round(campaign_elapsed_ms, 3),
              "total_calibrated_browser_ms": round(campaign_elapsed_ms * calibration.get("median_grizzly_per_profile", 0), 3)
              if calibration.get("status") == "calibrated" else None,
              "total_profile_navigation_ms": sum((row["profile"].get("timing", {}).get("navigation_to_completion_ms", 0) or 0) for row in records),
              "seed_families": seed_data,
              "source_aliases": source_aliases}
    ledger["campaign"] = {"mode": "bounded" if args.campaign_seconds is not None else "complete",
                          "target_seconds": args.campaign_seconds,
                          "completed_prefix": args.campaign_seconds is not None,
                          "exhausted": bool(args.campaign_seconds is not None and len(records) == planned_spec_count and
                                            campaign_elapsed_ms < args.campaign_seconds * 1000),
                          "actual_wall_ms": round(campaign_elapsed_ms, 3)}
    output.mkdir(parents=True, exist_ok=True)
    path = output / "ledger.json"
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    return ledger


async def _run_bounded(runner, specs, browser, budget_seconds, campaign_started):
    """Run a deterministic serial prefix in one browser lifecycle until the wall cap."""
    browser_obj, context = await runner.setup_browser(browser)
    results, case_times, end_times = [], {}, {}
    configured_timeout = runner.timeout
    try:
        for spec in specs:
            remaining_ms = budget_seconds * 1000 - (time.perf_counter() - campaign_started) * 1000
            if remaining_ms <= 0:
                break
            runner.timeout = max(1, min(configured_timeout, int(remaining_ms)))
            path = str(spec["output_path"])
            case_started = time.perf_counter()
            result = await runner.run_test(path, browser, context)
            case_times[str(Path(path).resolve())] = (time.perf_counter() - case_started) * 1000
            end_times[str(Path(path).resolve())] = (time.perf_counter() - campaign_started) * 1000
            runner.results.append(result)
            results.append(result)
    finally:
        await context.close()
        if browser_obj:
            await browser_obj.close()
        temp_profile_dir = getattr(context, "_temp_profile_dir", None)
        if not temp_profile_dir and browser_obj:
            temp_profile_dir = getattr(browser_obj, "_temp_profile_dir", None)
        if temp_profile_dir:
            shutil.rmtree(temp_profile_dir, ignore_errors=True)
    elapsed_ms = (time.perf_counter() - campaign_started) * 1000
    by_path = {str(Path(item.test_path).resolve()): item.to_dict() for item in results}
    return by_path, case_times, end_times, elapsed_ms


def _calibration(path, records, lane):
    data = _json(path, {}) if path else {}
    calibration_lane = data.get("lane", {}) if isinstance(data, dict) else {}
    required_lane = {key: lane.get(key) for key in ("browser", "browser_identity", "renderer", "contexts",
                                                     "profiler_version", "reducer_version", "profile_event_cap",
                                                     "outcome_cap")}
    if path and data and any(calibration_lane.get(key) != value for key, value in required_lane.items()):
        raise ValueError("calibration lane identity does not exactly match the profiled browser lane")
    if path and data.get("lane_verified") is False:
        raise ValueError("calibration lane is explicitly marked unverified")
    if not data or any(calibration_lane.get(key) != value for key, value in required_lane.items()):
        return {"status": "uncalibrated", "samples": 0, "source": str(path) if path else None,
                "reason": "lane_identity_mismatch"}
    by_output = {row.get("output_sha256"): row for row in records}
    rows = data.get("records", data.get("samples", [])) if isinstance(data, dict) else []
    valid = []
    for row in rows:
        paired = by_output.get(row.get("output_sha256"))
        if not paired:
            continue
        profile_ms = paired.get("profile", {}).get("timing", {}).get("navigation_to_completion_ms")
        grizzly_ms = row.get("duration_ms")
        if grizzly_ms is None and row.get("duration_s") is not None:
            grizzly_ms = float(row["duration_s"]) * 1000
        if profile_ms and grizzly_ms:
            valid.append((float(profile_ms), float(grizzly_ms)))
    if not valid:
        return {"status": "uncalibrated", "samples": 0, "source": str(path) if path else None,
                "reason": "no_paired_lifecycle_samples"}
    ratios = [grizzly / profile for profile, grizzly in valid if profile > 0]
    return {"status": "calibrated", "samples": len(ratios), "median_grizzly_per_profile": statistics.median(ratios),
            "source": str(path) if path else None, "lane": required_lane,
            "paired_outputs": [row.get("output_sha256") for row in rows if row.get("output_sha256") in by_output]}


def _apply_calibration(ledger, path):
    """Attach a newly verified calibration to an existing profile ledger copy."""
    lane = ledger.get("lane", {})
    calibration = _calibration(path, ledger.get("records", []), lane)
    ledger["calibration"] = calibration
    if calibration.get("status") == "calibrated":
        factor = calibration["median_grizzly_per_profile"]
        for row in ledger.get("records", []):
            row["calibrated_browser_ms"] = round(row.get("browser_ms", 0) * factor, 3)
        total = ledger.get("total_browser_ms", sum(row.get("browser_ms", 0) for row in ledger.get("records", [])))
        ledger["total_calibrated_browser_ms"] = round(total * factor, 3)
    else:
        for row in ledger.get("records", []):
            row.pop("calibrated_browser_ms", None)
        ledger["total_calibrated_browser_ms"] = None
    return ledger


def _requirements(row, selection_scope=False):
    reduced = row.get("reduced", {})
    keys = {f"core:{method}" for method in reduced.get("methods", [])}
    extensions = reduced.get("extension_methods", {})
    if selection_scope:
        profile = row.get("profile", {})
        contexts = {context.get("id"): context.get("version") for context in profile.get("contexts", [])}
        executions = defaultdict(set)
        for event in profile.get("events", []):
            extension = event.get("extension")
            version = contexts.get(event.get("context"))
            if extension and version is not None:
                executions[(extension, event.get("method"))].add(version)
        supported_by_version = defaultdict(set)
        for context in profile.get("contexts", []):
            for extension in context.get("extensions") or []:
                supported_by_version[extension].add(context.get("version"))
        for extension, methods in extensions.items():
            for method in methods:
                versions = executions.get((extension, method)) or supported_by_version.get(extension) or set()
                keys.update(f"context:v{version}:extension:{extension}:{method}"
                            for version in versions)
    else:
        keys.update(f"extension:{extension}:{method}" for extension, methods in extensions.items()
                    for method in methods)
    keys.update(reduced.get("overloads", []))
    keys.update(f"value:{value}" for value in reduced.get("value_classes", []))
    keys.update(f"flow:{flow}" for flow in reduced.get("flow_patterns", []))
    keys.update(row.get("productive_families", []))
    keys.update(row.get("executed_category_pairs", []))
    return keys


def _enrich_candidate_sites(ledger):
    """Recompute static edit-site evidence from current source bytes without profiling."""
    for source_text, info in ledger.get("seed_families", {}).items():
        source = Path(source_text).resolve()
        if not source.is_file():
            continue
        content = source.read_bytes()
        if _hash(content) != info.get("source_sha256"):
            raise ValueError(f"candidate-site source hash mismatch: {source}")
        families = webgl_mutator.candidate_families(content)
        info["families"] = {name: len(items) for name, items in sorted(families.items())}
        info["candidate_site_count"] = sum(info["families"].values())
        info["argument_sites"] = _name_site_arguments(analyze_sites(content, families),
                                                        _json(ROOT / "docs/webgl_api_surface.json", {}))
        for row in ledger.get("records", []):
            if row.get("source_sha256") == info.get("source_sha256") and not row.get("edits"):
                row["candidate_sites"] = info["families"]
                row["argument_sites"] = info["argument_sites"]


def _name_site_arguments(calls, surface):
    for call in calls:
        if call.get("kind") == "extension":
            method_data = surface.get("extensions", {}).get(call.get("extension"), {}).get("methods", {}).get(call.get("method"), {})
        else:
            method_data = surface.get("methods", {}).get(call.get("method"), {})
        arity = len(call.get("args", []))
        overloads = [overload for overload in method_data.get("overloads", [])
                     if overload.get("arity", len(overload.get("params", []))) == arity]
        for argument in call.get("args", []):
            names = sorted({overload.get("params", [])[argument["index"]].get("name", "")
                            for overload in overloads if argument["index"] < len(overload.get("params", []))})
            if names:
                argument["parameter_names"] = names
            else:
                argument.setdefault("parameter_names", [])
            argument["direct_candidate_count"] = argument.get("eligible_edits", 0)
    return calls


def _context_coverage(row, context, surface, categories, topology):
    context_id = context.get("id")
    profile = row.get("profile", {})
    scoped_profile = {**profile, "contexts": [context],
                      "events": [event for event in profile.get("events", [])
                                 if event.get("context") == context_id],
                      "outcomes": [], "truncated": False}
    reduced = reduce_trace(scoped_profile, surface)
    scoped_row = {**row, "profile": scoped_profile, "reduced": reduced}
    return _requirements(scoped_row) | set(_executed_category_pairs(scoped_row, categories, topology))


def _context_requirement_statuses(ledger, surface, categories, topology):
    scopes, observed_versions, contexts_by_scope = [], set(), defaultdict(list)
    clean_rows = [row for row in ledger.get("records", []) if row.get("clean")]
    for row in clean_rows:
        for context in row.get("profile", {}).get("contexts", []):
            version = context.get("version")
            extensions = sorted(context.get("extensions") or [])
            contexts_by_scope[(version, tuple(extensions))].append((row, context))
            observed_versions.add(version)
    for (version, extension_tuple), pairs in sorted(contexts_by_scope.items(), key=lambda item: (item[0][0], item[0][1])):
            extensions = list(extension_tuple)
            universe = feature_coverage.requirement_universe(surface, categories, topology, version, extensions)
            eligible = set().union(*(set(items) for items in universe.get("requirements", {}).values()))
            covered_sets = []
            for row, context in pairs:
                covered_sets.append(_context_coverage(row, context, surface, categories, topology))
            covered = set().union(*covered_sets) if covered_sets else set()
            status = {key: ("covered" if key in covered else "missing") for key in sorted(eligible)}
            for key in universe.get("unsupported_extensions", []):
                status[f"extension:{key}"] = "unsupported"
            for key in universe.get("unsupported_extension_methods", []):
                status[key] = "unsupported"
            for key in universe.get("unsupported_category_pairs", []):
                status[key] = "unsupported"
            for key in (universe.get("unmeasured_extensions", []) +
                        universe.get("unmeasured_core_methods", []) +
                        universe.get("unmeasured_core_overloads", []) +
                        universe.get("unmeasured_extension_methods", []) +
                        universe.get("unmeasured_category_pairs", [])):
                status[key] = "unmeasured"
            scopes.append({"version": version, "supported_extensions": extensions,
                           "requirements": status})
    declared_versions = {method.get("webgl_version", 1) for method in surface.get("methods", {}).values()}
    declared_versions.update(overload.get("webgl_version", method.get("webgl_version", 1))
                             for method in surface.get("methods", {}).values()
                             for overload in method.get("overloads", []))
    for version in sorted(declared_versions - observed_versions):
        universe = feature_coverage.requirement_universe(surface, categories, topology, version, None)
        keys = set().union(*(set(items) for items in universe.get("requirements", {}).values()))
        keys.update(universe.get("unmeasured_extensions", []))
        keys.update(universe.get("unmeasured_core_methods", []))
        keys.update(universe.get("unmeasured_core_overloads", []))
        keys.update(universe.get("unmeasured_extension_methods", []))
        keys.update(universe.get("unmeasured_category_pairs", []))
        # A version with no context observation has no runtime capability evidence.
        scopes.append({"version": version, "supported_extensions": None,
                       "requirements": {key: "unmeasured" for key in sorted(keys)}})
    return sorted(scopes, key=lambda item: (item.get("version") or 0,
                                             json.dumps(item.get("supported_extensions"), sort_keys=True)))


def _lane_contexts(records):
    contexts = {}
    for row in records:
        for context in row.get("profile", {}).get("contexts", []):
            identity = {"version": context.get("version"),
                        "extensions": sorted(context.get("extensions") or []),
                        "renderer": context.get("renderer"), "vendor": context.get("vendor"),
                        "renderer_verified": context.get("renderer_verified")}
            contexts[json.dumps(identity, sort_keys=True, separators=(",", ":"))] = identity
    return [contexts[key] for key in sorted(contexts)]


def _executed_category_pairs(row, categories, topology):
    defs = categories.get("categories", categories)
    core = set(row.get("reduced", {}).get("methods", []))
    ext = row.get("reduced", {}).get("extension_methods", {})
    called_exts = set(ext)
    present = set()
    for name, definition in defs.items():
        methods = set(definition.get("methods", [])) & core
        extension_methods = set(definition.get("extension_methods", []))
        methods.update(method for methods in ext.values() for method in extension_methods & set(methods))
        required_exts = set(definition.get("extensions", []))
        if definition.get("extension"):
            required_exts.add(definition["extension"])
        if methods and required_exts <= called_exts:
            present.add(name)
    return sorted("pair:" + "+".join(sorted(edge["pair"], key=str.casefold))
                  for edge in topology.get("edges", []) if set(edge.get("pair", [])) <= present)


def _applicable_universe(ledger, surface, categories, topology):
    requirements, unsupported, unmeasured = set(), set(), set()
    observations = {}
    for row in ledger.get("records", []):
        if not row.get("clean"):
            continue
        for context in row.get("profile", {}).get("contexts", []):
            key = (context.get("version"), tuple(sorted(context.get("extensions") or [])))
            observations[key] = context.get("extensions") or []
    capability_observations = [(version, extensions)
                               for (version, _), extensions in observations.items()]
    if not capability_observations:
        # Do not erase the API denominator when every profile failed, truncated,
        # or produced no context. No support/version claim is safe in that case.
        capability_observations = [(None, None)]
    for version, extensions in capability_observations:
        universe = feature_coverage.requirement_universe(surface, categories, topology, version, extensions)
        grouped = universe.get("requirements", {})
        if grouped:
            for items in grouped.values():
                requirements.update(items)
        else:
            for name in ("core_methods", "core_overloads", "extension_methods", "category_pairs"):
                requirements.update(universe.get(name, []))
        unsupported.update(universe.get("unsupported_extensions", []))
        unsupported.update(universe.get("unsupported_extension_methods", []))
        unsupported.update(universe.get("unsupported_category_pairs", []))
        unmeasured.update(universe.get("unmeasured_extensions", []))
        unmeasured.update(universe.get("unmeasured_core_methods", []))
        unmeasured.update(universe.get("unmeasured_core_overloads", []))
        unmeasured.update(universe.get("unmeasured_extension_methods", []))
        unmeasured.update(universe.get("unmeasured_category_pairs", []))
    generic_flows = ("buffer_attribute_draw", "buffer_attribute_draw_replace_draw", "attribute_toggle_draw",
                     "vao_switch_draw", "program_switch_draw", "instanced_attribute_draw", "element_buffer_draw",
                     "element_buffer_switch_draw", "texture_upload_attach_render", "texture_upload_attach_render_sample",
                     "resource_unbind_rebind_after_use", "resource_delete_after_use")
    generic_values = ("draw_count:zero", "draw_count:one", "draw_count:positive",
                      "instance_count:zero", "instance_count:one", "instance_count:positive",
                      "positive_subdraws:zero", "positive_subdraws:one", "positive_subdraws:few",
                      "positive_subdraws:many", "multi_draw_counts:zero", "multi_draw_counts:positive",
                      "multi_draw_counts:mixed_zero_positive", "buffer_data_overload:size",
                      "buffer_data_overload:data", "buffer_allocation:zero", "buffer_allocation:tiny",
                      "buffer_allocation:small", "buffer_allocation:medium", "buffer_allocation:large",
                      "buffer_allocation:very_large", "buffer_upload:zero", "buffer_upload:tiny",
                      "buffer_upload:small", "buffer_upload:medium", "buffer_upload:large",
                      "buffer_upload:very_large", "buffer_replacement:initial", "buffer_replacement:shrink",
                      "buffer_replacement:grow", "buffer_replacement:same", "buffer_subdata_offset:zero",
                      "buffer_subdata_offset:interior", "buffer_subdata_offset:end",
                      "buffer_subdata_offset:out_of_bounds", "buffer_subdata_offset:unknown",
                      "element_offset:zero", "element_offset:nonzero", "element_offset:in_bounds",
                      "element_offset:out_of_bounds", "element_offset:unknown",
                      "draw_mode:POINTS", "draw_mode:LINES", "draw_mode:LINE_LOOP", "draw_mode:LINE_STRIP",
                      "draw_mode:TRIANGLES", "draw_mode:TRIANGLE_STRIP", "draw_mode:TRIANGLE_FAN",
                      "index_type:UNSIGNED_BYTE", "index_type:UNSIGNED_SHORT", "index_type:UNSIGNED_INT",
                      "buffer_usage:STREAM_DRAW", "buffer_usage:STATIC_DRAW", "buffer_usage:DYNAMIC_DRAW",
                      "buffer_target:ARRAY_BUFFER", "buffer_target:ELEMENT_ARRAY_BUFFER",
                      "buffer_target:UNIFORM_BUFFER", "buffer_target:COPY_READ_BUFFER",
                      "buffer_target:COPY_WRITE_BUFFER")
    requirements.update(f"flow:{name}" for name in generic_flows)
    requirements.update(f"value:{name}" for name in generic_values)
    return requirements, unsupported, unmeasured


def select_manifest(candidates, baseline_requirements, budget_minutes=None, max_seeds=None, min_carriers=2):
    """Deterministic greedy selection, preserving measured baseline evidence first."""
    eligible = [row for row in candidates if row.get("clean")]
    by_source = {}
    for row in sorted(eligible, key=lambda item: (item.get("source_sha256", ""), item.get("id", ""))):
        by_source.setdefault(row.get("source_sha256"), row)
    eligible = list(by_source.values())
    if not eligible:
        return {"status": "infeasible", "selected": [], "unmet_baseline": sorted(baseline_requirements), "unmet_full": []}
    covered_by = defaultdict(list)
    requirements = {row["source_sha256"]: _requirements(row, selection_scope=True) for row in eligible}
    for row in eligible:
        for requirement in requirements[row["source_sha256"]]:
            covered_by[requirement].append(row)
    unmet_baseline = set(baseline_requirements) - set(covered_by)
    if unmet_baseline:
        return {"status": "infeasible", "selected": [], "unmet_baseline": sorted(unmet_baseline), "unmet_full": []}
    # Keep two independent carriers for requirements with at least two distinct sources.
    target_counts = {requirement: 1 for requirement in baseline_requirements}
    target_counts.update({requirement: min_carriers for requirement, rows in covered_by.items()
                          if requirement.startswith("flow:") and len(rows) >= min_carriers})
    selected, manifest, counts = [], [], Counter()
    spent = 0.0
    while any(counts[key] < target for key, target in target_counts.items()):
        ranked = []
        for row in eligible:
            if row in selected or (max_seeds is not None and len(selected) >= max_seeds):
                continue
            cost = max(float(row.get("campaign_cost_ms", row.get("calibrated_browser_ms", row.get("browser_ms", 0)))) / 60000, 1e-6)
            if budget_minutes is not None and spent + cost > budget_minutes:
                continue
            new = {req for req in requirements[row["source_sha256"]]
                   if counts[req] < target_counts.get(req, 0)}
            if new:
                deficit_utility = len(new)
                yield_utility = row.get("flow_variant_yield", 0) + row.get("image_variant_yield", 0)
                clean_yield = row.get("clean_variant_yield", 0)
                preserve_phase = any(counts[key] < 1 for key in baseline_requirements)
                utility = deficit_utility if preserve_phase else deficit_utility + yield_utility
                ranked.append((utility / cost, deficit_utility, clean_yield, row["source_sha256"], row, cost, new))
        if not ranked:
            break
        _, _, _, _, row, cost, new = sorted(ranked, key=lambda item: (-item[0], -item[1], -item[2], item[3]))[0]
        selected.append(row)
        manifest.append({"source_path": row["source_path"], "source_sha256": row["source_sha256"],
                         "marginal_requirements": sorted(new),
                         "campaign_cost_ms": row.get("campaign_cost_ms", row.get("browser_ms", 0)),
                         "clean_variant_yield": row.get("clean_variant_yield", 0),
                         "flow_variant_yield": row.get("flow_variant_yield", 0),
                         "image_variant_yield": row.get("image_variant_yield", 0)})
        counts.update(new)
        spent += cost
    preserved = set().union(*(requirements[r["source_sha256"]] for r in selected)) if selected else set()
    baseline_left = {key for key in baseline_requirements if counts[key] < 1}
    redundancy_left = {key for key, target in target_counts.items() if target > 1 and counts[key] < target}
    remaining = {key for key, target in target_counts.items() if counts[key] < target}
    return {"status": "selected" if not baseline_left and not redundancy_left else "infeasible", "selected": [row["source_path"] for row in selected],
            "selected_hashes": [row["source_sha256"] for row in selected], "spent_minutes": spent,
            "marginal_manifest": manifest,
            "unmet_baseline": sorted(baseline_left), "unmet_redundancy": sorted(redundancy_left),
            "unmet_full": sorted(remaining)}


def make_report(ledger, inventory_data=None, budget_minutes=None, max_seeds=None, surface=None, categories=None,
                topology=None, comparison=None):
    records = ledger.get("records", [])
    categories = categories or {}
    topology = topology or {}
    surface = surface or {}
    for row in records:
        row["executed_category_pairs"] = _executed_category_pairs(row, categories, topology)
    controls = [row for row in records if not row.get("edits") and row.get("clean")]
    productive = defaultdict(set)
    for row in records:
        if row.get("clean") and row.get("productive"):
            if len(row.get("edits", [])) == 1:
                family = row["edits"][0].get("operator")
                productive[row.get("control_source_sha256")].add(f"productive:{family}")
    candidates = [row for row in records if not row.get("edits")]
    for row in candidates:
        row["productive_families"] = sorted(productive[row.get("source_sha256")])
        variants_for_seed = [variant for variant in records
                             if variant.get("control_source_sha256") == row.get("source_sha256") and variant.get("edits")]
        raw_cost = row.get("browser_ms", 0) + sum(variant.get("browser_ms", 0) for variant in variants_for_seed)
        calibrated_cost = row.get("calibrated_browser_ms", 0) + sum(
            variant.get("calibrated_browser_ms", 0) for variant in variants_for_seed)
        row["campaign_cost_ms"] = calibrated_cost or raw_cost
        row["campaign_raw_cost_ms"] = raw_cost
        row["campaign_mutation_count"] = len(variants_for_seed)
        variants = [variant for variant in records if variant.get("control_id") == row.get("id") and variant.get("edits") and variant.get("clean")]
        row["clean_variant_yield"] = len(variants)
        row["flow_variant_yield"] = len({variant["reduced"].get("flow_signature") for variant in variants
                                          if variant.get("flow_novel")})
        row["image_variant_yield"] = len({variant["profile"].get("image_sha256") for variant in variants
                                           if variant.get("image_novel") and variant["profile"].get("image_sha256")})
    baseline = set().union(*(_requirements(row, selection_scope=True) for row in controls)) if controls else set()
    selection = select_manifest(candidates, baseline, budget_minutes, max_seeds)
    if selection["status"] == "selected" and ledger.get("calibration", {}).get("status") != "calibrated":
        selection["status"] = "provisional"
    covered = set().union(*(_requirements(row) for row in controls)) if controls else set()
    universe, unsupported, unmeasured = _applicable_universe(ledger, surface, categories, topology)
    universe.update(f"productive:{family}" for info in ledger.get("seed_families", {}).values()
                    for family in info.get("families", {}))
    family_report = defaultdict(lambda: {"eligible_sites": 0, "generated": 0, "clean": 0,
                                         "flow_distinct": 0, "image_distinct": 0, "browser_ms": 0,
                                         "median_ms": None})
    family_flows, family_images = defaultdict(set), defaultdict(set)
    for seed, info in ledger.get("seed_families", {}).items():
        for family, count in info.get("families", {}).items():
            family_report[family]["eligible_sites"] += count
    times = defaultdict(list)
    for row in records:
        if not row.get("edits"):
            continue
        family = row["edits"][0].get("operator", "mixed") if len(row["edits"]) == 1 else "mixed"
        item = family_report[family]
        item["generated"] += 1
        item["clean"] += int(row.get("clean", False))
        if row.get("clean") and row.get("flow_novel"):
            family_flows[family].add(row["reduced"].get("flow_signature"))
        if row.get("clean") and row.get("image_novel"):
            family_images[family].add(row["profile"].get("image_sha256"))
        item["browser_ms"] += row.get("browser_ms", 0)
        item.setdefault("calibrated_browser_ms", 0)
        if ledger.get("calibration", {}).get("status") == "calibrated":
            item["calibrated_browser_ms"] += row.get("calibrated_browser_ms", 0)
        times[family].append(row.get("browser_ms", 0))
    for family, item in family_report.items():
        item.setdefault("calibrated_browser_ms", 0)
        item["flow_distinct"] = len(family_flows[family])
        item["image_distinct"] = len(family_images[family])
        item["median_ms"] = statistics.median(times[family]) if times[family] else None
        item["flow_per_family_minute"] = (round(item["flow_distinct"] / (item["calibrated_browser_ms"] / 60000), 6)
                                           if item["calibrated_browser_ms"] else None)
        item["image_per_family_minute"] = (round(item["image_distinct"] / (item["calibrated_browser_ms"] / 60000), 6)
                                            if item["calibrated_browser_ms"] else None)
    campaign_calibrated_ms = (sum(row.get("calibrated_browser_ms", 0) for row in records)
                              if ledger.get("calibration", {}).get("status") == "calibrated" else 0)
    campaign_browser_ms = ledger.get("total_browser_ms", sum(row.get("browser_ms", 0) for row in records))
    for item in family_report.values():
        item["flow_per_campaign_minute"] = (round(item["flow_distinct"] / (campaign_calibrated_ms / 60000), 6)
                                             if campaign_calibrated_ms else None)
        item["image_per_campaign_minute"] = (round(item["image_distinct"] / (campaign_calibrated_ms / 60000), 6)
                                              if campaign_calibrated_ms else None)
    unresolved = {entry for row in records for entry in row.get("reduced", {}).get("unresolved", [])}
    status = {key: "covered" if key in covered else "missing" for key in sorted(universe)}
    for key in status:
        method = key.removeprefix("overload:").split(":", 1)[0] if key.startswith("overload:") else ""
        if status[key] == "missing" and (f"overload:{method}" in unresolved or key in unresolved):
            status[key] = "unresolved"
    unresolved_requirements = {
        "active_attribute_slots": ("flow:buffer_attribute_draw_replace_draw", "flow:attribute_toggle_draw",
                                   "flow:vao_switch_draw", "flow:instanced_attribute_draw"),
        "attribute_consumption": ("flow:buffer_attribute_draw_replace_draw", "flow:attribute_toggle_draw",
                                  "flow:instanced_attribute_draw"),
        "attribute_pointer_binding": ("flow:buffer_attribute_draw_replace_draw", "flow:attribute_toggle_draw"),
        "element_buffer_binding": ("flow:element_buffer_draw", "flow:element_buffer_switch_draw"),
        "sampler_type": ("flow:texture_upload_attach_render_sample",),
        "texture_upload_binding": ("flow:texture_upload_attach_render", "flow:texture_upload_attach_render_sample"),
        "sampler_array_assignment": ("flow:texture_upload_attach_render_sample",),
        "unknown_uniform_location": ("flow:texture_upload_attach_render_sample",),
        "stale_uniform_location": ("flow:texture_upload_attach_render_sample",),
        "multi_draw_selection": ("value:multi_draw_counts:mixed_zero_positive",),
        "program_link_reflection": ("flow:buffer_attribute_draw", "flow:buffer_attribute_draw_replace_draw",
                                    "flow:attribute_toggle_draw", "flow:instanced_attribute_draw",
                                    "flow:texture_upload_attach_render_sample"),
    }
    for reason in unresolved:
        for key in unresolved_requirements.get(reason, ()):
            if status.get(key) == "missing":
                status[key] = "unresolved"
    for item in unsupported:
        key = item if item.startswith(("pair:", "extension:")) else f"extension:{item}"
        if key not in covered and key not in universe:
            status[key] = "unsupported"
    for item in unmeasured:
        key = item if item.startswith(("core:", "overload:", "extension:", "pair:")) else f"extension:{item}"
        if key not in covered and key not in universe:
            status[key] = "unmeasured"
    if comparison:
        comparison["adoption_eligible"] = bool(comparison.get("adoption_eligible") and
                                               selection.get("status") == "selected" and
                                               not selection.get("unmet_baseline"))
    static_counts = defaultdict(int)
    inventory_measurements = {}
    if inventory_data:
        controls_by_identity = {}
        for row in records:
            if row.get("edits"):
                continue
            key = (str(Path(row.get("source_path", "")).resolve()), row.get("source_sha256"))
            controls_by_identity[key] = row
        for seed in inventory_data.get("seeds", []):
            key = (str(Path(seed.get("source_path", "")).resolve()), seed.get("source_sha256"))
            control = controls_by_identity.get(key)
            inventory_measurements[key[0]] = (
                "measured_clean" if control.get("clean") else "measured_failed") if control else "unmeasured"
            for requirement in seed.get("static_requirements", []):
                static_counts[requirement] += 1
    inventory_counts = Counter(inventory_measurements.values())
    seed_candidate_sites = []
    for source_path, info in sorted(ledger.get("seed_families", {}).items()):
        control = next((row for row in controls if row.get("source_sha256") == info.get("source_sha256")), None)
        calls = info.get("argument_sites", control.get("argument_sites", []) if control else [])
        calls = _name_site_arguments(calls, surface)
        executed_core = set(control.get("reduced", {}).get("methods", [])) if control else set()
        executed_ext = control.get("reduced", {}).get("extension_methods", {}) if control else {}
        summarized_calls = []
        for call in calls:
            method_observed = (call.get("method") in executed_core if call.get("kind") == "core" else
                               call.get("method") in executed_ext.get(call.get("extension"), []))
            summarized_calls.append({**call, "method_observed": method_observed,
                                     "site_execution": "unresolved"})
        seed_candidate_sites.append({"source_path": source_path,
                                     "source_sha256": info.get("source_sha256"),
                                     "source_aliases": info.get("source_aliases", []),
                                     "families": info.get("families", {}),
                                     "candidate_site_count": info.get("candidate_site_count",
                                         sum(info.get("families", {}).values())),
                                     "argument_sites": summarized_calls,
                                     "method_observed_call_count": sum(call["method_observed"] for call in summarized_calls),
                                     "direct_argument_count": sum(arg.get("status") == "eligible"
                                                                   for call in summarized_calls for arg in call.get("args", [])),
                                     "direct_candidate_count": sum(arg.get("direct_candidate_count", 0)
                                                                    for call in summarized_calls for arg in call.get("args", [])),
                                     "static_gaps_for_observed_methods": [{"method": call.get("method"),
                                                           "extension": call.get("extension"),
                                                           "kind": call.get("kind"),
                                                           "argument_index": arg.get("index"),
                                                           "parameter_names": arg.get("parameter_names", []),
                                                           "status": arg.get("status"),
                                                           "wrapper_only_families": arg.get("wrapper_only_families", [])}
                                                          for call in summarized_calls if call["method_observed"]
                                                          for arg in call.get("args", [])
                                                          if arg.get("status") != "eligible"]})
    return {"schema_version": 1, "kind": "corpus_report", "lane": ledger.get("lane", {}),
            "settings": ledger.get("settings", {}),
            "calibration": ledger.get("calibration", {}),
            "campaign_comparison": comparison,
            "campaign_time": {"browser_ms": campaign_browser_ms,
                              "calibrated_browser_ms": campaign_calibrated_ms or None,
                              "includes_controls_variants_failures_and_recovery": True},
            "inventory": {"seed_count": inventory_data.get("seed_count", 0) if inventory_data else None,
                          "measured_clean_count": inventory_counts["measured_clean"] if inventory_data else None,
                          "measured_failed_count": inventory_counts["measured_failed"] if inventory_data else None,
                          "unmeasured_count": inventory_counts["unmeasured"] if inventory_data else None,
                          "measurement_by_source": dict(sorted(inventory_measurements.items())),
                          "static_requirement_count": len(static_counts),
                          "static_requirement_seed_counts": dict(sorted(static_counts.items()))},
            "measured_baseline": sorted(baseline), "baseline_requirement_count": len(baseline),
            "covered_by_controls": sorted(covered), "selection": selection,
            "full_universe_gaps": sorted(universe - covered),
            "unsupported_requirements": sorted(unsupported), "unmeasured_requirements": sorted(unmeasured),
            "requirement_status": status,
            "context_requirement_status": _context_requirement_statuses(ledger, surface, categories, topology),
            "source_aliases": ledger.get("source_aliases", {}),
            "seed_candidate_sites": seed_candidate_sites,
            "mutation_yield": dict(sorted(family_report.items())),
            "records": [_report_record(row) for row in records]}


def _report_record(row):
    """Keep committed reports replayable without embedding browser event traces."""
    profile_path = row.get("profile_path")
    output_path = row.get("output_path")
    sidecar_path = (str(Path(output_path).with_suffix(".mutation.json"))
                    if output_path and row.get("edits") else None)
    profile_sha = _hash(Path(profile_path).read_bytes()) if profile_path and Path(profile_path).is_file() else None
    sidecar_sha = _hash(Path(sidecar_path).read_bytes()) if sidecar_path and Path(sidecar_path).is_file() else None
    return {"id": row.get("id"), "kind": "variant" if row.get("edits") else "control",
            "source_path": row.get("source_path"), "source_sha256": row.get("source_sha256"),
            "output_path": output_path, "output_sha256": row.get("output_sha256"),
            "profile_path": profile_path, "profile_sha256": profile_sha,
            "mutation_sidecar_path": sidecar_path, "mutation_sidecar_sha256": sidecar_sha,
            "edits": row.get("edits", []), "control_id": row.get("control_id"),
            "control_source_sha256": row.get("control_source_sha256"),
            "clean": row.get("clean"), "flow_novel": row.get("flow_novel"),
            "image_novel": row.get("image_novel"),
            "image_hash_kind": row.get("profile", {}).get("image_hash_kind"),
            "image_sha256": row.get("profile", {}).get("image_sha256"),
            "methods": row.get("reduced", {}).get("methods", []),
            "extension_methods": row.get("reduced", {}).get("extension_methods", {}),
            "overloads": row.get("reduced", {}).get("overloads", []),
            "flow_signature": row.get("reduced", {}).get("flow_signature"),
            "flow_patterns": row.get("reduced", {}).get("flow_patterns", []),
            "positive_draws": row.get("reduced", {}).get("positive_draws", 0),
            "value_classes": row.get("reduced", {}).get("value_classes", []),
            "unresolved": row.get("reduced", {}).get("unresolved", []),
            "candidate_sites": row.get("candidate_sites", {}),
            "argument_sites": row.get("argument_sites", []),
            "browser_ms": row.get("browser_ms"), "campaign_end_ms": row.get("campaign_end_ms")}


def _markdown(report):
    selection = report["selection"]
    lines = ["# WebGL corpus coverage report", "", f"Lane: `{json.dumps(report.get('lane', {}), sort_keys=True)}`", "",
             f"Measured baseline: {report['baseline_requirement_count']} requirements; selection status: **{selection['status']}**.", "",
             f"Inventory: {report['inventory']['seed_count']} sources; {report['inventory']['measured_clean_count']} clean controls, {report['inventory']['measured_failed_count']} failed controls, {report['inventory']['unmeasured_count']} unmeasured; {report['inventory']['static_requirement_count']} static requirements observed.", "",
             "## Context capability scopes", "",
             "| WebGL | Supported extensions | Covered | Missing | Unsupported | Unmeasured |",
             "|---|---|---:|---:|---:|---:|"]
    for scope in report.get("context_requirement_status", []):
        statuses = scope.get("requirements", {}).values()
        counts = Counter(statuses)
        extensions = scope.get("supported_extensions")
        ext_label = ", ".join(extensions) if extensions is not None else "unobserved"
        lines.append(f"| {scope.get('version') or '?'} | {ext_label or '(none)'} | {counts['covered']} | {counts['missing']} | {counts['unsupported']} | {counts['unmeasured']} |")
    comparison = report.get("campaign_comparison")
    if comparison:
        current = comparison.get("current", {})
        baseline = comparison.get("baseline", {})
        yes_no = lambda value: "yes" if value else "no"
        lines.extend(["", "## Equal-time campaign comparison", "",
                      f"Common observed wall time: {comparison.get('common_actual_wall_ms', 0)} ms.", "",
                      "| Yield | Baseline | Current |", "|---|---:|---:|"])
        for label, key in (("Clean variants", "clean"), ("Distinct flow changes", "flow_distinct"),
                           ("Distinct pixel images", "image_distinct")):
            lines.append(f"| {label} | {baseline.get(key, 0)} | {current.get(key, 0)} |")
        lines.extend(["", f"Baseline requirements preserved: **{yes_no(comparison.get('preserves_baseline_requirements'))}**.",
                      f"Each yield preserved: **{yes_no(comparison.get('preserves_each_yield'))}**.",
                      f"Adoption eligible: **{yes_no(comparison.get('adoption_eligible'))}**."])
    lines.extend(["", "## Per-seed edit-site coverage", "",
                  "| Source | Candidate sites by family | Direct argument sites | Static gaps for observed methods (examples) |",
                  "|---|---|---:|---|"])
    for seed in report.get("seed_candidate_sites", []):
        families = ", ".join(f"{name}:{count}" for name, count in seed.get("families", {}).items()) or "(none)"
        gaps = seed.get("static_gaps_for_observed_methods", [])
        def gap_priority(gap):
            if gap.get("kind") == "extension":
                group = 0
            elif any(token in gap.get("method", "").lower()
                     for token in ("buffer", "texture", "teximage", "texsubimage")):
                group = 1
            else:
                group = 2
            parameter = " ".join(gap.get("parameter_names", [])).lower()
            semantic = 0 if any(token in parameter for token in ("count", "data", "size", "list")) else 1
            return group, semantic, gap.get("method", ""), gap.get("argument_index", -1)
        groups = [[gap for gap in sorted(gaps, key=gap_priority) if gap_priority(gap)[0] == group]
                  for group in range(3)]
        ordered_gaps = [gap for group in groups for gap in group[:4]]
        examples = []
        for gap in ordered_gaps:
            method = f"{gap['extension']}.{gap['method']}" if gap.get("extension") else gap["method"]
            parameter = "/".join(gap.get("parameter_names", [])) or f"arg{gap.get('argument_index')}"
            label = f"{method}({parameter})"
            if gap.get("wrapper_only_families"):
                label += " [wrapper only]"
            elif gap.get("status") == "unknown":
                label += " [unknown]"
            if label not in examples:
                examples.append(label)
        examples = examples[:12]
        source = Path(seed.get("source_path", "")).name or seed.get("source_sha256", "")[:12]
        lines.append(f"| `{source}` | {families} | {seed.get('direct_argument_count', 0)} | "
                     f"{'; '.join(examples) if examples else '(none)'} |")
    lines.extend(["", "## Proposed manifest", ""])
    if selection.get("selected"):
        lines.extend(f"- `{path}`" for path in selection["selected"])
    else:
        lines.append("No qualifying manifest at this cap.")
    lines.extend(["", f"Unmet baseline requirements: {len(selection.get('unmet_baseline', []))}.",
                  f"Unmet full-universe requirements: {len(report['full_universe_gaps'])}.", "",
                  "## Mutation yield", "", "| Family | Sites | Generated | Clean | Flow changes | Image changes | Browser ms | Median ms |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for family, item in report["mutation_yield"].items():
        lines.append(f"| {family} | {item['eligible_sites']} | {item['generated']} | {item['clean']} | {item['flow_distinct']} | {item['image_distinct']} | {item['browser_ms']} | {item['median_ms']} |")
    lines.append("")
    return "\n".join(lines)


def _write_report(report, output):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    path.with_suffix(".md").write_text(_markdown(report))


def _validate_ledger(ledger, check_files=True):
    records = ledger.get("records", [])
    settings = ledger.get("settings", {})
    identity = ledger.get("lane", {}).get("browser_identity")
    fingerprint = identity.get("fingerprint") if isinstance(identity, dict) else None
    ids = [row.get("id") for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("profile ledger contains duplicate record ids")
    surface = _json(ROOT / "docs/webgl_api_surface.json", {})
    for row in records:
        if row.get("browser") != identity:
            raise ValueError("profile ledger mixes browser executable or launch configuration identities")
        profile = row.get("profile", {})
        profile_identity = profile.get("identity", profile.get("browser", {}))
        if identity and profile_identity != identity:
            raise ValueError(f"profile identity mismatch: {row.get('id')}")
        if fingerprint and profile_identity.get("fingerprint") != fingerprint:
            raise ValueError(f"profile fingerprint mismatch: {row.get('id')}")
        if settings.get("profile_event_cap") is not None and profile_identity.get("event_cap") != settings["profile_event_cap"]:
            raise ValueError(f"profile event cap mismatch: {row.get('id')}")
        if settings.get("profiler_version") and profile.get("profiler_version") != settings["profiler_version"]:
            raise ValueError(f"profiler version mismatch: {row.get('id')}")
        if settings.get("profile_event_cap") is not None and profile.get("identity", {}).get("event_cap") != settings["profile_event_cap"]:
            raise ValueError(f"profile event cap mismatch: {row.get('id')}")
        if settings.get("outcome_cap") is not None and profile.get("identity", {}).get("outcome_cap") != settings["outcome_cap"]:
            raise ValueError(f"profile outcome cap mismatch: {row.get('id')}")
        if row.get("reduced", {}).get("reducer_version") != settings.get("reducer_version"):
            raise ValueError(f"reducer version mismatch: {row.get('id')}")
        expected_contexts = _lane_contexts([row])
        if (row.get("context_versions") != sorted({context["version"] for context in expected_contexts}) or
                row.get("renderer") != sorted({str(context.get("renderer", "")) for context in expected_contexts}) or
                row.get("supported_extensions") != sorted({extension for context in expected_contexts
                                                             for extension in context["extensions"]})):
            raise ValueError(f"profile context summary mismatch: {row.get('id')}")
        if check_files:
            for field, expected in (("source_path", row.get("source_sha256")),
                                    ("output_path", row.get("output_sha256"))):
                path = Path(row[field])
                if not path.is_file() or _hash(path.read_bytes()) != expected:
                    raise ValueError(f"{field} hash mismatch: {path}")
            if row.get("edits"):
                output = Path(row["output_path"])
                sidecar_path = output.with_suffix(".mutation.json")
                sidecar = _json(sidecar_path)
                if (not sidecar or sidecar.get("source_sha256") != row.get("source_sha256") or
                        Path(sidecar.get("source_path", "")).resolve() != Path(row["source_path"]).resolve() or
                        sidecar.get("output_sha256") != row.get("output_sha256") or
                        sidecar.get("edits") != row.get("edits")):
                    raise ValueError(f"mutation replay sidecar mismatch: {sidecar_path}")
                replayed = webgl_mutator.replay(Path(row["source_path"]).read_bytes(), sidecar)
                if _hash(replayed) != row.get("output_sha256"):
                    raise ValueError(f"mutation replay output mismatch: {sidecar_path}")
            if row.get("profile_path"):
                raw_profile = _json(row["profile_path"])
                if raw_profile != profile:
                    raise ValueError(f"raw profile file mismatch: {row['profile_path']}")
        expected_reduced = reduce_trace(profile, surface)
        if row.get("reduced") != expected_reduced:
            raise ValueError(f"reduced profile evidence mismatch: {row.get('id')}")
        expected_clean = _profile_clean(row.get("result", {}), profile, expected_reduced) and expected_reduced["profile_clean"]
        if row.get("clean") is not expected_clean:
            raise ValueError(f"profile clean status mismatch: {row.get('id')}")
    by_id = {row.get("id"): row for row in records}
    for row in records:
        if not row.get("edits"):
            if row.get("control_id") is not None or row.get("control_source_sha256") is not None:
                raise ValueError(f"control record has variant linkage: {row.get('id')}")
            continue
        control = by_id.get(row.get("control_id"))
        if (not control or control.get("edits") or
                control.get("source_sha256") != row.get("source_sha256") or
                row.get("control_source_sha256") != control.get("source_sha256")):
            raise ValueError(f"variant control linkage mismatch: {row.get('id')}")
        expected_flow = bool(row.get("clean") and control.get("clean") and
                             row["reduced"].get("flow_signature") != control["reduced"].get("flow_signature"))
        expected_image = bool(row.get("clean") and control.get("clean") and
                              row["profile"].get("image_hash_kind") == "rgba_pixels" and
                              control["profile"].get("image_hash_kind") == "rgba_pixels" and
                              row["profile"].get("image_sha256") != control["profile"].get("image_sha256"))
        if (row.get("flow_novel") is not expected_flow or row.get("image_novel") is not expected_image or
                row.get("productive") is not (expected_flow or expected_image)):
            raise ValueError(f"variant novelty evidence mismatch: {row.get('id')}")
    if ledger.get("lane") and ledger["lane"].get("contexts") is not None:
        if ledger["lane"]["contexts"] != _lane_contexts(records):
            raise ValueError("profile ledger mixes context versions, extensions, or renderer capabilities")
    return True


def _campaign_yield(ledger):
    rows = [row for row in ledger.get("records", []) if row.get("edits")]
    return {"variants": len(rows), "clean": sum(bool(row.get("clean")) for row in rows),
            "flow_distinct": len({row.get("reduced", {}).get("flow_signature") for row in rows
                                  if row.get("clean") and row.get("flow_novel")}),
            "image_distinct": len({row.get("profile", {}).get("image_sha256") for row in rows
                                   if row.get("clean") and row.get("image_novel") and
                                   row.get("profile", {}).get("image_hash_kind") == "rgba_pixels"}),
            "browser_ms": sum(row.get("browser_ms", 0) for row in ledger.get("records", [])),
            "calibrated_browser_ms": sum(row.get("calibrated_browser_ms", 0) for row in ledger.get("records", []))}


def compare_campaigns(current, baseline):
    lane_fields = ("browser", "browser_identity", "renderer", "profiler_version", "reducer_version",
                   "profile_event_cap", "outcome_cap")
    if any(current.get("lane", {}).get(key) != baseline.get("lane", {}).get(key) for key in lane_fields):
        raise ValueError("cannot compare profile ledgers from different browser lanes")
    for setting in ("rng_seed", "samples_per_family", "mixed_samples", "max_edits", "timeout_ms", "headless", "profile_event_cap", "outcome_cap", "campaign_seconds"):
        if current.get("settings", {}).get(setting) != baseline.get("settings", {}).get(setting):
            raise ValueError(f"campaign settings differ: {setting}")
    if current.get("campaign", {}).get("mode") != "bounded" or baseline.get("campaign", {}).get("mode") != "bounded":
        raise ValueError("equal-time comparison requires `profile --campaign-seconds` for both ledgers")
    if current.get("campaign", {}).get("exhausted") or baseline.get("campaign", {}).get("exhausted"):
        raise ValueError("equal-time comparison requires campaigns that ran through their full time budget")
    current_end = float(current.get("campaign", {}).get("actual_wall_ms", 0))
    baseline_end = float(baseline.get("campaign", {}).get("actual_wall_ms", 0))
    common_ms = min(current_end, baseline_end)
    def prefix(ledger):
        return [row for row in ledger.get("records", [])
                if row.get("campaign_end_ms") is not None and row["campaign_end_ms"] <= common_ms]
    current_rows, baseline_rows = prefix(current), prefix(baseline)
    baseline_requirements = set().union(*(_requirements(row, selection_scope=True) for row in baseline.get("records", [])
                                         if not row.get("edits") and row.get("clean")))
    current_control_rows = [row for row in current_rows if not row.get("edits") and row.get("clean")]
    current_control_coverage = set().union(*(_requirements(row, selection_scope=True) for row in current_control_rows)) if current_control_rows else set()
    current_yield = _prefix_yield(current_rows)
    baseline_yield = _prefix_yield(baseline_rows)
    preserves_yield = all(current_yield[key] >= baseline_yield[key]
                          for key in ("clean", "flow_distinct", "image_distinct"))
    preserves_baseline = baseline_requirements <= current_control_coverage
    preserves = bool(common_ms and preserves_yield and preserves_baseline)
    return {"common_actual_wall_ms": common_ms,
            "current": current_yield, "baseline": baseline_yield,
            "current_control_requirements": sorted(current_control_coverage),
            "baseline_control_requirements": sorted(baseline_requirements),
            "unmet_baseline_requirements": sorted(baseline_requirements - current_control_coverage),
            "preserves_baseline_requirements": preserves_baseline,
            "preserves_each_yield": preserves_yield,
            "adoption_eligible": preserves and current.get("calibration", {}).get("status") == "calibrated"}


def _prefix_yield(records):
    controls = {row.get("id"): row for row in records if not row.get("edits") and row.get("clean")}
    variants = [row for row in records if row.get("edits")]
    validated = [row for row in variants if row.get("clean") and row.get("control_id") in controls]
    return {"variants": len(variants), "clean": len(validated),
            "flow_distinct": len({row.get("reduced", {}).get("flow_signature") for row in variants
                                  if row in validated and row.get("flow_novel")}),
            "image_distinct": len({row.get("profile", {}).get("image_sha256") for row in variants
                                   if row in validated and row.get("image_novel") and
                                   row.get("profile", {}).get("image_hash_kind") == "rgba_pixels"}),
            "browser_ms": sum(row.get("browser_ms", 0) for row in records),
            "calibrated_browser_ms": sum(row.get("calibrated_browser_ms", 0) for row in records)}


def _browser_config(args):
    config = _json(args.browser_config, {}) if args.browser_config else {}
    config = dict(config or {})
    if args.chromium_path:
        config["chromium_path"] = args.chromium_path
    return config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory", help="static inventory of HTML seeds")
    inv.add_argument("paths", nargs="+", type=Path)
    inv.add_argument("--surface", type=Path, default=ROOT / "docs/webgl_api_surface.json")
    inv.add_argument("--categories", type=Path, default=ROOT / "docs/feature_categories.json")
    inv.add_argument("--topology", type=Path, default=ROOT / "docs/interaction_topology.json")
    inv.add_argument("--cache-dir", type=Path, default=ROOT / ".cache/api_audit")
    inv.add_argument("--output", type=Path, required=True)

    profile = sub.add_parser("profile", help="profile controls and mutation samples in one browser lane")
    profile.add_argument("manifest", help="HTML directory, HTML file, or JSON seed list")
    profile.add_argument("--output", type=Path, required=True)
    profile.add_argument("--browser", choices=("firefox", "chromium"), default="chromium")
    profile.add_argument("--browser-config", type=Path)
    profile.add_argument("--chromium-path")
    profile.add_argument("--timeout", type=int, default=30000, help="per-test timeout in milliseconds")
    profile.add_argument("--headless", action="store_true")
    profile.add_argument("--force-firefox", action="store_true")
    profile.add_argument("--rng-seed", type=int, default=0)
    profile.add_argument("--samples-per-family", type=int, default=1)
    profile.add_argument("--mixed-samples", type=int, default=3)
    profile.add_argument("--max-edits", type=int, choices=(1, 2, 3), default=3)
    profile.add_argument("--profile-event-cap", type=int, default=20000)
    profile.add_argument("--calibration", type=Path)
    profile.add_argument("--campaign-seconds", type=float,
                         help="run a deterministic serial prefix until this actual browser wall-time budget")

    report = sub.add_parser("report", help="combine inventory and profile ledger; propose a manifest")
    report.add_argument("--ledger", type=Path, required=True)
    report.add_argument("--inventory", type=Path)
    report.add_argument("--budget-minutes", type=float)
    report.add_argument("--max-seeds", type=int, help="maximum canonical sources in the proposed manifest")
    report.add_argument("--compare-ledger", type=Path, help="equal-time baseline campaign ledger")
    report.add_argument("--calibration", type=Path,
                        help="attach an exact-lane, output-hash-paired calibration without rerunning profiles")
    report.add_argument("--output", type=Path, required=True)
    report.add_argument("--surface", type=Path, default=ROOT / "docs/webgl_api_surface.json")
    report.add_argument("--categories", type=Path, default=ROOT / "docs/feature_categories.json")
    report.add_argument("--topology", type=Path, default=ROOT / "docs/interaction_topology.json")
    args = parser.parse_args(argv)

    if args.command == "inventory":
        result = inventory(args.paths, args.surface, args.categories, args.topology, args.cache_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 0
    if args.command == "profile":
        if (args.samples_per_family < 0 or args.mixed_samples < 0 or args.timeout <= 0 or
                args.profile_event_cap <= 0 or
                (args.campaign_seconds is not None and args.campaign_seconds <= 0)):
            parser.error("sample counts must be nonnegative and timeout positive")
        seeds = _manifest_paths(args.manifest)
        if not seeds:
            parser.error("manifest contains no HTML seeds")
        ledger = asyncio.run(_profile_async(seeds, args.output, args.browser,
                                            _browser_config(args), args))
        print(args.output / "ledger.json")
        return 0 if ledger["records"] else 1
    ledger = _json(args.ledger)
    if args.max_seeds is not None and args.max_seeds < 1:
        parser.error("--max-seeds must be positive")
    _validate_ledger(ledger)
    if args.calibration:
        ledger = _apply_calibration(ledger, args.calibration)
    _enrich_candidate_sites(ledger)
    comparison = None
    if args.compare_ledger:
        baseline_ledger = _json(args.compare_ledger)
        _validate_ledger(baseline_ledger)
        comparison = compare_campaigns(ledger, baseline_ledger)
    inv_data = _json(args.inventory) if args.inventory else None
    _write_report(make_report(ledger, inventory_data=inv_data, budget_minutes=args.budget_minutes,
                              max_seeds=args.max_seeds, surface=_json(args.surface, {}),
                              categories=_json(args.categories, {}), topology=_json(args.topology, {}),
                              comparison=comparison), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
