# Screenshot Triage — 2026-08-24

Follow-up to corpus quality improvements handoff (item #2). Source data: `/tmp/shots_now.json` (before) and `/tmp/shots_after.json` (after).

## Headline numbers

| Metric | Before | After |
|---|---|---|
| Blank frames (root `screenshots/` + `agent_outputs/screenshots/`) | 124 | 109 |
| Duplicate redundant frames | 431 | 423 |
| Stale copies purged from `agent_outputs/screenshots/` | 336 | 0 remaining |
| Orphan PNGs (no living HTML) deleted | 10 | 0 remaining |

## Root causes found

### 1. MSAA default framebuffer blocks blit-present (systemic, legacy corpus)
`canvas.getContext('webgl2')` defaults to `antialias: true`. In this Firefox/Mesa
environment the default framebuffer is then multisampled, and
`blitFramebuffer(..., dst = default FB)` is **invalid** ("DRAW_FRAMEBUFFER may not
have multiple samples") — silently swallowed by `catch(e) {}`. Every legacy seed
that presents via a final blit therefore rendered nothing. Verified by pixel probe:
FBO attachment had correct content, default FB had garbage.

**Fix applied** (`antialias: false` added) where it produced visible output and
clean logs:
- `agent_outputs/mutation_b60_s277_edbi_blend_mrt_fbo_rb.html`
- `agent_outputs/mutation_b60_s278_edbi_depth_stencil_mrt_fbo_rb.html`
- `agent_outputs/mutation_b60_s280_edbi_int_tex3d_texarray_float_mrt.html`
- `samples-webgl/mutations/mutation_b2_s7_sample_shading_min.html`
- `samples-webgl/mutations/mutation_b2_s9_fbo_blit_resolve.html`
- `samples-webgl/mutations/mutation_b2_s6_alpha_coverage_ms.html` (kept: removed
  MSAA warnings; output faint sd=0.5, borderline)

**Reverted** (no visibility gain; restored exact prior state to honor
surgical-change discipline — these need dedicated presentation fixes):
mutation_b22_s107, b33_s164, b37_s182, b39_s193, b39_s194, b40_s196..s200,
seed_sparse_texture_view_msa_indirect_churn.

### 2. Saturated-white shader math (new seed bug, fixed)
`mutation_b95_s1_buffer_ops_edbi_glsl.html` consumed raw `uintBitsToFloat` /
`intBitsToFloat` garbage patterns as multipliers → Inf/NaN → pure white frame
(white-on-white with page background). Fixed by bit-masking float constructions
into bounded ranges (`0x3f800000` mantissa trick → [1,2) and [0.5,1)) and
`clamp()` on outputs. Now visible (sd=42.3), still 0 warnings/errors.

### 3. Stale screenshot copies (infrastructure)
`samples-webgl/**` seeds screenshot only to root `screenshots/`;
`agent_outputs/screenshots/` held 336 stale January-era duplicates that polluted
blank/dedupe counts. Purged. `agent_outputs/screenshots/` now contains only
screenshots of `agent_outputs/*.html` seeds.

### 4. Orphans deleted (10)
PNGs for deleted HTML: check_extensions, extension_soup,
integrated_extension_orgasm_extreme, test, plus probe artifacts.

## Remaining blanks (109) — recommended follow-up

All are legacy `samples-webgl/**` seeds in two classes:
- **~91 render-only-to-FBO / state-only seeds** (sync, UBO, TF-capture, buffer
  patterns): they never present anything to the canvas. Fixing requires adding a
  presentation pass per seed (blit or direct draw) — a dedicated batch task, not a
  mechanical patch.
- **~18 heavy-error-path seeds** (megamix/octopus family, 10-37 pre-existing
  warnings each): presentation swallowed by earlier error paths; also pre-existing.

Note: `seed_sparse_texture_view_msa_indirect_churn` fails validation outright
(`shaderSource: Argument 1 is not an object` — createShader returns null then is
used unguarded). Pre-existing; candidate for deletion or repair in the same
follow-up batch.

## Visual monoculture

Largest duplicate groups after cleanup are the blank/black clusters above
(they vanish as blanks get fixed). One real monoculture signal:
`{mutation_b31_s153, mutation_b94_s1, mutation_b97_s3}` share the split-screen
MRT-blit layout. Future seed batches should vary presentation geometry
(quadrants, insets, animated-free static composites) per batch.


## Campaign-hostility audit (2026-08-24, post-triage addendum)

Static + dynamic scan of all 432 files against the mutation-campaign exclusion
criteria (no OOM-adjacent allocations, no unbounded loops/polling, no churn):

**Fixed**
- 9 unbounded `requestAnimationFrame` animation loops bounded to 8 frames
  (multipass_post_processing_chain, compute_gpu_data_processing_pipeline,
  edge_cases_numerical_limits, extensions_fragment_depth,
  creative_fractal_nebula_forge, creative_quantum_foam_simulator,
  texture_tech_atlasing_packing, webgl2_3d_textures,
  resource_buffer_orphaning_cycles). Unbounded loops would have run to the full
  30s runner timeout on every campaign execution.
- 2 dead seeds repaired (were fatal-JS-error blanks, nothing executed):
  - extensions_fragment_depth: duplicate `const isWebGL2` + missing
    `#version 300 es` on both WebGL2 shader branches. Now passes clean, visible.
  - creative_fractal_nebula_forge: stray GLSL line in JS scope, missing
    `transformFeedbackVaryings`, TF ping-pong buffer conflict (attrib pointer
    never rebound), pool-texture feedback loop (now double-buffered with
    per-frame re-attach). Now passes clean, visible.

**Audited and accepted (no action)**
- 15 `while` loops: all bounded query-availability polls (100-200 iters)
- 17 `waitSync` uses: non-blocking per spec (validation-only console warning)
- 14 texStorage/texImage with dims 99999/33333/32856: intentionally invalid
  (> MAX_*), error-path tests, no runtime allocation; mutating them to valid
  huge values requires multi-digit changes
- bufferData 128KB-2MB / typed arrays up to 4MB: millisecond-scale, not OOM-class
- for-loops up to 131072 cheap JS iterations (~1ms)
- 3-4 context files: moderate init cost, not farm-level
