---
name: close-coverage-gaps
description: Use when the WebGL fuzzing corpus has uncovered feature COMBINATION gaps - looks up required methods/extensions per feature, designs interactions from topology edges, creates seeds to close specific 3-way gaps, validates and verifies via combination matrix delta
---

# Close Coverage Gaps

## Overview

Close N-way feature combination gaps from the combination matrix. Unlike `expand-webgl-coverage` (which targets missing API methods/constants), this skill targets **feature combination gaps** where individual features are covered but specific N-way combos have no seed exercising them together.

- **Input**: A gap combo like `["ext_float_textures", "fbo", "sampler"]`
- **Output**: A validated seed that covers all features in the combo, verified by matrix delta

**Announce at start:** "I'm using the close-coverage-gaps skill to close feature combination gaps."

## Prerequisites

Read these files before starting (in order):
1. `docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md` - Three-zone architecture, variable tiers, line repetition patterns
2. `AGENTS.md` - Seed creation rules and validation workflow
3. `UNSUPPORTED.md` - Extensions and features to avoid
4. `docs/feature_categories.json` - Method/extension lookups per feature category
5. `docs/interaction_topology.json` - Edge relationships between features

## The Workflow

### Step 1: Get the Gap Combo

Either receive the combo directly (e.g., from a pipeline) or generate the current gap list:

```bash
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix_current.json --n-way 3
```

Read `/tmp/matrix_current.json` and find combos with `"seed_count": 0`.

### Step 2: Look Up Feature Requirements

For each feature in the target combo, read `docs/feature_categories.json` and extract:
- **methods**: Which WebGL methods to call (check `min_methods_for_match`)
- **constants**: Which enum constants to use (check `requires_any_constant`)
- **extensions**: Which extensions to load (check `requires_any_extension`)
- **glsl_functions**: Which GLSL builtins to use in shaders (check `min_glsl_for_match`)
- **extension_methods**: Methods called on the extension object, not `gl`

Use the Extension Quick Reference and Feature Gate tables below to avoid common mistakes.

### Step 3: Look Up Topology Edges

Read `docs/interaction_topology.json`. Find all edges connecting features in the target combo. These describe **how** features should interact in the seed.

Example: For combo `["ext_float_textures", "fbo", "sampler"]`:
- `ext_float_textures ↔ fbo`: float textures as FBO attachments
- `ext_float_textures ↔ sampler`: sampler filtering on float textures
- `fbo ↔ sampler`: (no direct edge — interact via texture_ops)

Design the seed so each edge relationship is concretely implemented.

### Step 4: Determine REQUIRED_EXTENSIONS

1. For each feature in the combo, check if `requires_any_extension` is true
2. Collect the needed extensions from `feature_categories.json`
3. Cross-check `UNSUPPORTED.md` for Firefox/Chromium limitations
4. Pick the **safest** (most widely supported) extension per category
5. Add all to the `REQUIRED_EXTENSIONS` array in the seed

### Step 5: Write the Seed

Follow the **three-zone architecture** from `docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md`:

**File naming**: `agent_outputs/mutation_bN_sN_<descriptive>.html` — determine N before writing:

```bash
ls agent_outputs/mutation_b*.html 2>/dev/null | grep -oP 'b\K[0-9]+(?=_s)' | sort -n | tail -1
```

Use that number if adding to an in-progress batch, or increment by 1 to start a new batch. Seed number (sN) is the next available within that batch.

**Declaration Zone:**
- 5-8 Tier 1 amplification variables (cascading mutations)
- 4-6 Tier 3 enum constants
- Include constants from ALL features in the combo

**Setup Zone (4-8 try-catch blocks):**
- Resource creation for ALL features in the combo
- Topology edges dictate concrete interactions:
  - If edge says "float textures as FBO attachments" → create float texture, attach to FBO
  - If edge says "sampler filtering on float textures" → create sampler, bind to float texture unit
- Use 3+ line repetition patterns (bind ping-pong, creation redundancy, etc.)

**Execution Zone (2-4 try-catch blocks):**
- State configuration, draw calls, resource cleanup
- Exercise all features together in draw/readback operations

**Shader considerations:**
- `sampler` → shader must sample via sampler-bound texture unit
- `texture_3d` → use `sampler3D` and `texture(sampler, vec3)` in fragment shader
- `texture_arrays` → use `sampler2DArray` and `texture(sampler, vec3)` with layer index
- `integer_textures` → use `isampler2D`/`usampler2D`, output to `ivec4`/`uvec4`
- `glsl_builtins` → call target builtins in shader source
- `shader_pipeline` → needs **2+** methods (e.g., `createShader` + `createProgram`)

**Rules:**
- `catch(e) {}` in production (use `catch(e) { console.log(e); }` only during dev debugging)
- No comments, no console.log in final version
- 150-300 lines, 256x256 canvas, self-contained HTML
- Check `UNSUPPORTED.md` before using any extension
- Extension gating via `REQUIRED_EXTENSIONS` array pattern (see AGENTS.md boilerplate)

### Step 6: Validate

```bash
# During development (with console.log in catch blocks):
./run_tests.sh --test-file agent_outputs/<file>.html --browsers firefox
```

Read the JSON output file (same name, `.json` extension). Fix iteratively until:
- `"passed": true`
- `"console_logs": []`
- `"javascript_errors": []`

**Then strip console.log** → `catch(e) {}`, re-validate. Never assume fixes work.

### Step 7: Verify Gap Closure

Run the combination matrix with a baseline to see the delta:

```bash
# Save baseline first (before adding new seed):
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix_before.json --n-way 3

# After adding seed, re-run:
PYTHONPATH=scripts ./venv/bin/python -m api_audit \
  --surface docs/webgl_api_surface.json \
  --corpus-dirs samples-webgl agent_outputs \
  --feature-categories docs/feature_categories.json \
  --interaction-topology docs/interaction_topology.json \
  --combination-matrix /tmp/matrix_after.json --n-way 3
```

Compare: target combo must now show `seed_count >= 1`. If the feature is still missing, diagnose which gate was not satisfied:
- Extension category: Was the extension actually loaded via `getExtension()`?
- `requires_any_constant`: Does the seed use one of the listed constants?
- `min_methods_for_match`: Does the seed call enough methods from the category?
- `extension_methods`: Are methods called on the extension object (not `gl`)?

## Extension Category Quick Reference

| Category | Extension(s) to Load | Gate | Extra Requirement |
|---|---|---|---|
| `ext_float_textures` | `OES_texture_float_linear` (safest) | Just load it | None |
| `ext_color_buffer_float` | `EXT_color_buffer_float` | Just load it | None |
| `ext_draw_buffers_indexed` | `OES_draw_buffers_indexed` | Load + call ext methods | `ext.enableiOES(...)`, `ext.colorMaskiOES(...)` |
| `ext_texture_filter_anisotropic` | `EXT_texture_filter_anisotropic` | Load + use constant | `ext.TEXTURE_MAX_ANISOTROPY_EXT` |
| `ext_compressed_textures` | `WEBGL_compressed_texture_etc` | Just load it | None |
| `ext_disjoint_timer_query` | `EXT_disjoint_timer_query` | Load + call ext method | `ext.queryCounterEXT(...)`. **NOT** `_webgl2` variant |

## Non-Obvious Feature Gates

| Feature | Gate Surprise |
|---|---|
| `shader_pipeline` | Needs **2** methods (not 1) — e.g., `createShader` + `createProgram` |
| `texture_arrays` | Needs method **AND** `TEXTURE_2D_ARRAY` constant (`requires_any_constant: true`) |
| `integer_textures` | Can match on constants alone (`min_methods_for_match: 0`) — use R8I, RGBA32UI, etc. |
| `mrt` | Needs `drawBuffers` method **AND** a COLOR_ATTACHMENTn constant (n >= 1) |
| `glsl_builtins` | Scans shader source strings, not JS calls — builtins must appear in GLSL code |
| `ext_draw_buffers_indexed` | Methods are on the extension object (`ext.enableiOES`), not on `gl` |

## Quick Reference

| Step | Command | Success Check |
|------|---------|---------------|
| Matrix | `PYTHONPATH=scripts ./venv/bin/python -m api_audit --surface docs/webgl_api_surface.json --corpus-dirs samples-webgl agent_outputs --feature-categories docs/feature_categories.json --interaction-topology docs/interaction_topology.json --combination-matrix /tmp/matrix.json --n-way 3` | Lists combos with seed_count=0 |
| Validate | `./run_tests.sh --test-file <file> --browsers firefox` | JSON: passed=true, no errors |
| Delta | Compare matrix before/after adding seed | Target combo seed_count >= 1 |

## Seed Correctness Checklist

Before committing a seed:
- [ ] All features in the target combo are exercised (methods, constants, extensions)
- [ ] Topology edges between combo features are concretely implemented
- [ ] Extension categories: extensions loaded via `getExtension()` in `REQUIRED_EXTENSIONS`
- [ ] Extension methods called on extension object (not `gl`) where required
- [ ] 5-8 Tier 1 amplification variables
- [ ] 4-6 Tier 3 enum constants
- [ ] 20-40 Tier 2 inline numeric literals
- [ ] 6-10 try-catch blocks (4-8 setup + 2-4 execution)
- [ ] 3+ line repetition patterns used
- [ ] All `catch(e) {}` (no console.log)
- [ ] No comments in code
- [ ] 150-300 lines total
- [ ] Test passes with zero errors
- [ ] Combination matrix delta shows gap closed

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Extension loaded but category method not called | `ext_draw_buffers_indexed` needs `ext.enableiOES()`, not just `getExtension()` |
| `texture_arrays` without `TEXTURE_2D_ARRAY` constant | Must use the constant — method alone won't match due to `requires_any_constant` |
| `shader_pipeline` with only 1 method | Needs `min_methods_for_match: 2` — use at least `createShader` + `createProgram` |
| `mrt` without `drawBuffers` call | `drawBuffers` is the only method — must call it with COLOR_ATTACHMENTn constants |
| GLSL builtins in JS instead of shader source | Scanner checks shader source strings, not JS — put `smoothstep`, `texelFetch`, etc. in GLSL |
| Using `EXT_disjoint_timer_query_webgl2` | Not supported in Firefox — use `EXT_disjoint_timer_query` instead |
| Seed covers features individually but not together | Topology edges must be implemented — features must interact, not just coexist |
| Missing try-catch blocks | Need 6-10 blocks per seed for mutation surface |
| Defensive programming in seeds | No validation, no error checking — seeds are mutation targets |
| console.log left in production | Strip all console.log before final validation |
