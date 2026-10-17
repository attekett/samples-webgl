# WebGL mutator corpus baseline (2026-10-16)

Use [`agent_outputs/mutator_baseline/core/`](../agent_outputs/mutator_baseline/core/) as the input directory for the existing WebGL mutator on Firefox or Chrome. Its seven symlinks point to canonical, self-contained HTML seeds; they do not duplicate source files. Use [`agent_outputs/mutator_baseline/chrome_extensions/`](../agent_outputs/mutator_baseline/chrome_extensions/) only on Chrome/ANGLE-Vulkan, where `WEBGL_multi_draw` is available. Firefox did not expose that extension in the local probe.

The core selection is based on four properties: each source parses as one inline script, reaches `window.__done` after its WebGL error check, runs without warnings or JavaScript/WebGL errors in both browsers, and gives the current mutator a useful resource relationship or shader structure. With `glslangValidator` available, the seven core seeds collectively expose **all 25 valid-flow operator families** returned by `scripts/webgl_mutator.py` and 284 static candidate edits. The browser-fuzz base image installs `glslang-tools`. The previous 420-file source scan had no eligible typed-view, matrix-scalar, array-index, loop-bound, or buffer-redefinition seed. It had only one seed each for compatible buffer switching, compatible texture updates, and paired texture dimensions.

| Core seed | Eligible families | Candidate edits | Clean Chrome mutants | Changed screenshots |
| --- | ---: | ---: | ---: | ---: |
| Ping-pong texturing | 8 | 35 | 10/10 | 4 |
| Typed-view buffer capture | 13 | 47 | 10/10 | 6 |
| Structural shaders | 11 | 32 | 10/10 | 7 |
| Paired texture update and offscreen composite | 16 | 60 | 10/10 | 6 |
| Integrated buffer/texture two-pass | 18 | 59 | 10/10 | 7 |
| Core instancing | 7 | 30 | 10/10 | 8 |
| VAO state isolation | 6 | 21 | 10/10 | 0 |
| **Union / total** | **25** | **284** | **70/70** | **38** |

Each core baseline passed `run_tests.sh` on Firefox and system Chrome/ANGLE-Vulkan with completion and empty warning/error arrays. The 70-mutant sample used ten variants per seed, seed 947, and `--max-edits 3`; all 70 reached completion without page errors, observed WebGL errors, console warnings, or context loss on Chrome/ANGLE-Vulkan. Every mutant had a state-call trace hash different from its seed's baseline; these hashes describe observed API sequences and arguments, not driver coverage. The VAO seed remains useful for state-sequence variation even though that sample did not change pixels.

A separate 70-case batch through the Grizzly batch generator selected all seven sources, marked all 70 as having an explicit completion signal, and selected 24 of the 25 operator families. The remaining matrix-scalar family was exercised directly. Direct single-edit checks of matrix scalar, GLSL array index and loop bound, buffer redefinition, compatible buffer switch, vertex attribute offset, and typed-array view offset all completed cleanly and changed the screenshot. A linked-varying rename completed cleanly and preserved the screenshot, as expected for a coordinated name change.

The multi-draw extension seed is a separate Chrome-only input because Firefox lacks `WEBGL_multi_draw` here. Its extension call is part of the valid flow; the current mutator changes surrounding core WebGL state and parameters, not the extension method's arguments directly.

Static eligibility and this finite sample do not prove that every candidate edit is visually effective or that every browser backend behaves the same way. The baseline is ready to feed the present mutator; future corpus changes should preserve all 25 eligible families and rerun the completion, warning, and mutation-yield checks before replacing a seed.

The [six later coverage seeds](webgl_corpus_metrics.md#shortlist-additions-2026-10-16) are available in `agent_outputs/`. Their 12-second equal-time campaigns did not preserve mutation yield, so they have not replaced these baseline symlinks.
