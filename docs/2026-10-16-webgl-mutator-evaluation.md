# WebGL mutator evaluation (2026-10-16)

## Fixed-size browser comparison

Five mechanism-based seeds were tested: the integrated two-pass seed, VAO state isolation, ping-pong texturing, core instancing, and extension-gated multi-draw. The three existing core seeds without a completion marker were copied to `/tmp/webgl-eval-20261016/seeds/` with `window.__done = true` added after their final error check. Each arm generated 20 variants per seed with seed 801. The custom arm used `--max-edits 3`; the Radamsa arm used `-m num=6,lr2=2,ld=1,ls=1,li=1,bf=1 -p od`. All five baselines completed cleanly.

Pages ran in Playwright Chromium with `--use-angle=vulkan` and the same launch flags as `webgl_test_runner.py`. The renderer was `ANGLE (AMD, Vulkan 1.4.335 (Radeon 8060S Graphics (RADV STRIX_HALO) (0x00001586)), radv)`. Chrome exposed `WEBGL_multi_draw`. An init script counted WebGL1/2 prototype method calls and recorded selected state-changing calls and their primitive arguments. A case was clean only if `window.__done` was true and it had no page error, console warning/error, observed nonzero `getError`, or context loss. Screenshot and state-trace hashes were compared with that seed's baseline.

| Seed | Clean custom / Radamsa | Changed screenshots custom / Radamsa | Distinct new state traces custom / Radamsa | Median WebGL calls in clean cases custom / Radamsa |
| --- | ---: | ---: | ---: | ---: |
| Core instancing | 20 / 11 | 11 / 4 | 19 / 4 | 590 / 589 |
| Paired two-pass | 20 / 9 | 9 / 1 | 19 / 7 | 68 / 67 |
| Ping-pong texturing | 20 / 12 | 13 / 3 | 17 / 5 | 1059 / 1057 |
| VAO isolation | 20 / 14 | 0 / 0 | 16 / 2 | 535 / 534 |
| Multi-draw extension | 20 / 11 | 13 / 5 | 16 / 4 | 114 / 114 |
| **Total** | **100 / 57** | **46 / 13** | **87 / 22** | — |

Changed screenshots and new state traces count clean cases only. The trace count is a sum of per-seed distinct signatures that differ from that seed's baseline. The custom arm had no observed warning, page error, or context loss. Radamsa retained parseable inline JavaScript in 84/100 variants. The proxy counts core WebGL calls; extension object methods such as `multiDrawArraysWEBGL` are not included. Trace diversity shows different API sequences/arguments, not driver code coverage. The sample is small and thresholds were not set before this run, so these numbers are exploratory.

The separate validation arm was rerun on the integrated seed in Firefox and Chrome/Vulkan. Both runs reached `window.__done` and recorded `INVALID_VALUE` (1281) with one expected browser warning and no JavaScript error. The normal runner labels this arm failed because it treats any warning as a failure.

Raw case records are in [`agent_outputs/webgl_mutator_eval_2026-10-16.json`](../agent_outputs/webgl_mutator_eval_2026-10-16.json) and [`agent_outputs/webgl_mutator_eval_extension_2026-10-16.json`](../agent_outputs/webgl_mutator_eval_extension_2026-10-16.json). The validation result is `/tmp/webgl-eval-validation-20261016/valid_buffer_texture_paired_multipass_0.json`.

## Grizzly process checks

The adapter was installed into a temporary Python venv with the local Grizzly package and run against native Firefox 149.0a1 and the local Chromium-capable Grizzly fork. The integrated two-pass seed was the input. Before the throughput fix, three-case smoke tests in both lanes served all cases, recorded completion, and had no timeout. A separate same-binary browser probe reported Firefox's renderer as `Radeon R9 200 Series, or similar` (15 WebGL2 extensions, without `WEBGL_multi_draw`) and Chrome's as the AMD Vulkan renderer above (30 extensions, including `WEBGL_multi_draw`). The adapter does not currently record renderer/extensions per individual case.

The first equal-time pilot exposed an adapter delay: it marked completion but waited for the three-second backstop to close the page. After changing the completion setter to close immediately after its synchronous event request, a three-case smoke test completed in both lanes with no backstop or timeout; median case duration fell to 0.176 seconds in Firefox and 0.112 seconds in Chrome. The package suite passed 259 tests.

The corrected adapter and the existing Grizzly Radamsa adapter then ran for 45 seconds per arm and browser, each capped at 1,000 iterations. The Radamsa runs used a temporary process-only metadata path override because that adapter also assumes `/results` exists. No Grizzly finding was recorded in any lane.

| Browser | Custom served / completed | Radamsa served | Grizzly findings |
| --- | ---: | ---: | ---: |
| Native Firefox | 201 / 201 | 143 | 0 / 0 |
| Chrome with ANGLE/Vulkan | 320 / 320 | 191 | 0 / 0 |

All custom cases recorded `seed_done`, with no backstop or timeout. Radamsa's ledger marked 76/143 Firefox cases and 99/191 Chrome cases as `explicit`; the rest were `unmarked`. Those marks do not establish clean WebGL completion. The first and last custom selections in each lane replayed to their recorded mutation hashes. Raw Grizzly ledgers, Radamsa result tables, and logs are in [`agent_outputs/webgl_grizzly_eval_2026-10-16/`](../agent_outputs/webgl_grizzly_eval_2026-10-16/).

The 45-second Grizzly run is an adapter throughput check, not evidence that either arm finds more distinct browser defects. The next evaluation focuses on [corpus suitability for the existing operators](2026-10-16-webgl-mutator-corpus-baseline.md): eligible relationships, clean completion, and meaningful changes in rendered output or API state.
