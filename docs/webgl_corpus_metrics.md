# WebGL corpus metrics

`scripts/corpus_metrics.py` inventories static API use, profiles source controls and existing valid mutations in one browser lane, and produces a coverage report with a proposed seed manifest. It does not change mutation operators or test output semantics. Profiles are always rerun; there is no profile cache.

Run these commands with the project Python environment that has the repository's existing parser and browser dependencies installed.

```bash
python scripts/corpus_metrics.py inventory samples-webgl agent_outputs \
  --output /tmp/webgl-inventory.json

python scripts/corpus_metrics.py profile /tmp/seed-manifest.json \
  --output /tmp/webgl-campaign --browser chromium \
  --browser-config config/angle_vulkan.json \
  --chromium-path /usr/bin/google-chrome --timeout 30000 --headless \
  --rng-seed 13 --samples-per-family 1 --mixed-samples 3 --max-edits 3

python scripts/corpus_metrics.py report --ledger /tmp/webgl-campaign/ledger.json \
  --inventory /tmp/webgl-inventory.json --budget-minutes 5 --max-seeds 7 \
  --output /tmp/webgl-report.json
```

`inventory` accepts HTML files and directories and canonical-path deduplicates them. Each source gets a raw-byte SHA-256, static API fingerprint, and an `unmeasured` marker until a browser profile is recorded. The profile manifest can be an HTML path, a directory, or JSON containing a list of paths (or `{"seeds": [{"source_path": "..."}]}`). The profile command samples each existing edit family separately and adds deterministic `mixed` samples with one to three edits. It stores edited HTML, existing mutation replay sidecars, bounded raw profile JSON, and a ledger under the output directory.

Reports retain requirement status by WebGL version and observed extension set as well as an aggregate view. An extension method executed in WebGL2 can be covered even when WebGL1 reports that extension unsupported; an unobserved WebGL1 scope remains unmeasured. Selection baseline extension requirements carry their context version so a different context cannot silently substitute for the baseline capability.

The report reconciles inventory `measured_clean_count`, `measured_failed_count`, and `unmeasured_count` against profile controls by canonical source path and raw-byte SHA-256. `inventory.static_requirement_count` is the union of static requirements observed in inventory sources, not the full declared API denominator; the full runtime denominator and its gaps are reported separately.

Use separate ledgers for separate browser configurations or renderers. The ledger records the browser executable and launch identity, profiler and reducer versions, event and outcome caps, context versions, extensions, and renderer identity. Report ingestion checks source and output hashes, replay sidecars, raw profile files, and lane consistency. An identity mismatch is an error; unsupported or unobserved requirements remain separate from missing coverage.

The campaign time denominator includes the whole serial browser run, including controls, failed or timed-out mutations, and runner recovery overhead. Each seed's selection cost includes its control and all attempted mutations. The report ranks reproducible candidates by preserved baseline coverage and measured mutation yield under the requested time and seed caps. Flow requirements with multiple eligible source hashes request two carriers; a cap that cannot supply them is marked infeasible. The proposed manifest is provisional until it has an exact calibration and is not an automatic corpus change.

The report keeps one compact evidence row per case: canonical source/output paths and hashes, edit/replay-sidecar path and hash, raw-profile path and hash, control linkage, clean/novelty decisions, reduced flow/value evidence, and elapsed browser time. It omits raw event arrays. The top-level settings and lane identify the RNG seed, sample counts, edit bound, timeout, headless mode, browser executable/flags, renderer, context capabilities, event/outcome caps, and profiler/reducer versions needed to reproduce the run.

Per-seed static site evidence lists each recognized WebGL call argument and the existing mutation families with spans wholly contained in that argument. A full-statement wrapper is recorded separately and does not count as a direct argument edit; unresolved receivers or partial overlaps remain unknown. The trace identifies methods but not source positions, so matching a method marks `method_observed` while `site_execution` remains `unresolved`. The Markdown report shows family/site totals and static gaps among sites whose method was observed; it does not claim those particular sites ran. Report generation can reconstruct these spans from the validated source and existing candidate enumerator, so it does not require another browser run.

Calibration can be supplied with `profile --calibration calibration.json`. Its shape is:

```json
{
  "lane": {
    "browser": "chromium",
    "browser_identity": {},
    "renderer": ["ANGLE (AMD, AMD Radeon R9 200 Series, Vulkan 1.3)"],
    "contexts": [],
    "profiler_version": "webgl-trace-2",
    "reducer_version": "webgl-flow-3",
    "profile_event_cap": 20000,
    "outcome_cap": 2048
  },
  "records": [
    {"output_sha256": "<exact SHA-256>", "duration_s": 0.42}
  ]
}
```

The `lane` must exactly match the freshly observed profile lane, including `outcome_cap`. Pair lifecycle measurements by output hash; records may use `duration_ms` instead of `duration_s`. A supplied lane mismatch is rejected, and missing calibration leaves selection provisional. Historical durations without a verified matching lane are not imported. A calibration producer may include `"lane_verified": true` after verifying the actual executable, flags, and observed context; explicit `false` is rejected.

If calibration arrives after profiling, attach it during report generation without rerunning the browser:

```bash
python scripts/corpus_metrics.py report --ledger /tmp/webgl-campaign/ledger.json \
  --calibration /path/to/verified-calibration.json \
  --output /tmp/webgl-calibrated-report.json
```

For reproducible Grizzly lifecycle samples, use the local helper with the exact browser binary and fixed control manifest. Set the three import paths to the installed DuoGrizzly, BrowserPuppet, and dependency site-packages locations:

```bash
PYTHONPATH="$DUOGRIZZLY_SRC:$BROWSERPUPPET_SRC:$DEPENDENCY_SITE_PACKAGES" \
  python scripts/calibrate_webgl_lifecycle.py \
  --manifest <fixed-controls-dir-or-html> --binary <exact-browser-binary> \
  --browser <firefox|chromium> --rounds 2 \
  --profile-ledger <lane-ledger.json> --output <calibration.json>
```

The helper marks calibration verified only after matching executable identity, requested flags, completion, renderer, context versions, extensions, and vendor against the profile lane. Without `--profile-ledger`, it retains raw timing samples with `lane_verified: false`, which cannot be attached to a report.

For an equal-time campaign comparison, run both manifests with the same browser lane and settings, adding `--campaign-seconds 300` to each `profile` command. The profiler stops after the next completed case at or beyond the wall-time target and records each case's completion offset; each in-flight test gets only the remaining budget as its timeout. Controls run first, followed by deterministic interleaving of variants from the admitted sources. If all finite samples finish before the target, the ledger marks the campaign exhausted and it cannot be used as an equal-time comparison. Then add `--compare-ledger /path/to/baseline/ledger.json` to `report`. Different manifests and per-seed context capability sets are allowed within the same executable/renderer/profiler lane: the proposed campaign must preserve the baseline ledger's clean-control requirement subset with its own clean controls, and its measured clean, distinct-flow, and distinct-pixel yields must each match or exceed the baseline within the common completed prefix. The comparison counts actual completed variants and never extrapolates distinct coverage linearly. Image novelty requires decoded RGBA pixel hashes; encoded screenshot bytes do not count. The comparison describes these measured campaigns rather than claiming a global optimum.

The runtime value denominator includes a fixed set of executed draw-count and instance-count bands, multi-draw selection classes, geometric buffer allocation/upload bands, buffer replacement (`initial`, `shrink`, `grow`, `same`), `bufferSubData` destination offsets (`zero`, `interior`, `end`, `out_of_bounds`, `unknown`), element offsets, WebGL draw modes, index types, buffer usages, and buffer targets. For source-sliced typed-array uploads, byte counts reflect the selected view range. A value is covered only when the trace contains evidence; missing or unprovable state does not count as false coverage.

## Initial validation (2026-10-16)

The [Chrome/ANGLE-Vulkan report](snapshots/webgl-corpus-chrome-2026-10-16.md) measured 8 clean controls and 101 clean sampled variants. The [Firefox report](snapshots/webgl-corpus-firefox-2026-10-16.md) measured 7 clean controls and 93 clean variants. All 15 control images matched the ordinary runner's decoded RGBA images, and both lanes represented all 25 existing mutation families. The full inventory contains 422 canonical sources; 414 remain unmeasured in Chrome and 415 in Firefox. Grizzly calibration completed 24/24 Chrome and 21/21 Firefox control runs with the same verified lane settings.

The 12-second [Chrome comparison](snapshots/webgl-corpus-chrome-comparison-2026-10-16.md) preserved baseline requirements but measured 48 clean variants, 29 distinct flow signatures, and 21 distinct images for the proposed seven seeds, versus 52, 32, and 24 for the existing eight. The [Firefox comparison](snapshots/webgl-corpus-firefox-comparison-2026-10-16.md) measured 21, 15, and 16 versus 25, 18, and 18; its proposed manifest contains the same seven core sources as the existing one, so that difference reflects run-to-run timing near the cap. Neither proposal passed the adoption gate. The current manifests remain the baseline for further measurements.

The raw ledgers, replay sidecars, and event traces for this run are under `/tmp/periwinkle-coverage-*-v3-20261016` and `/tmp/periwinkle-coverage-*-time-v3-20261016`. Preserve those directories if full replay is needed; the reports retain hashes and compact evidence but omit event arrays.

## Shortlist additions (2026-10-16)

Six self-contained seeds now cover the main measured gaps. The five WebGL2 core seeds passed the ordinary Firefox runner with empty warning and error arrays; the `WEBGL_multi_draw` seed passed Chrome/ANGLE-Vulkan and is gated on that extension. All six controls passed the profiled Chrome lane, and the five core controls passed the profiled Firefox lane.

| Seed | Coverage added |
| --- | --- |
| [Uniform buffer palette](../agent_outputs/webgl2_uniform_buffer_palette_tiles.html) | Uniform block binding and aligned buffer ranges |
| [Transform feedback particles](../agent_outputs/webgl2_transform_feedback_wave_particles.html) | Captured vertex output reused for a visible draw |
| [Occlusion query panels](../agent_outputs/webgl2_occlusion_query_visibility_panels.html) | Query results driving deterministic visible panels |
| [Sampler filter split](../agent_outputs/webgl2_sampler_objects_split_filter.html) | One texture sampled with separate nearest and linear sampler objects |
| [Buffer rebind and value grid](../agent_outputs/webgl2_buffer_rebind_value_grid.html) | Buffer replacement, unbind/rebind, interior updates, and zero/one/positive draw values |
| [Indexed and instanced multi-draw rows](../agent_outputs/webgl2_multidraw_indexed_instanced_rows.html) | The three previously missing `WEBGL_multi_draw` methods on Chrome/ANGLE-Vulkan |

Compared with the original clean controls, the [expanded Chrome report](snapshots/webgl-corpus-expanded-chrome-2026-10-16.md) adds 72 executed requirements and the [expanded Firefox report](snapshots/webgl-corpus-expanded-firefox-2026-10-16.md) adds 73, without losing a baseline requirement. The additions include 23 core methods and 23 overloads in each lane, plus new value classes, API pairs, and resource-flow sequences. The full inventory is now 428 canonical HTML sources. The complete campaigns measured 14/14 clean Chrome controls with 143/144 clean variants, and 12/12 clean Firefox controls with 129/130 clean variants. The single non-clean variant in each lane replaced a UBO seed's final draw count with zero, so it had no positive-work draw.

The 12-second [Chrome comparison](snapshots/webgl-corpus-expanded-chrome-comparison-2026-10-16.md) preserved baseline requirements and increased distinct images from 24 to 30, but produced 48 rather than 52 clean variants; distinct flow signatures stayed at 32. The [Firefox comparison](snapshots/webgl-corpus-expanded-firefox-comparison-2026-10-16.md) produced 18 clean variants, 13 flow signatures, and 15 images, versus 25, 18, and 18 for the existing baseline. These finite campaigns do not pass the equal-time adoption gate, and the new controls have no Grizzly calibration. The six files remain in `agent_outputs/` for targeted corpus use; the active `mutator_baseline` symlinks remain unchanged. The expanded raw ledgers are under `/tmp/periwinkle-coverage-expanded-*-release-20261016` and `/tmp/periwinkle-coverage-expanded-*-time-20261016`.
