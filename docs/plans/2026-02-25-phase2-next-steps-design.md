# Phase 2 Next Steps: Topology Expansion + Recipe Generation

**Date**: 2026-02-25
**Status**: Design (pending implementation)
**Prerequisite**: Phase 1 complete (feature_detection.py, combination_matrix.py, CLI integration)

## Key Finding: Sparse Topology Hides Real Gaps

Phase 1 analysis with the original topology (55 edges across 30 features, 12.6% density) showed **0 actionable gaps** — every topology-connected combination is covered. However, the topology was missing fundamental WebGL interactions.

An expanded topology (90 edges, 20.7% density) reveals **50 actionable gaps**:

| Dimension | Before (55 edges) | After (90 edges) |
|---|---|---|
| 2-way gaps | 1 | 2 (1 high, 1 medium) |
| 3-way gaps | 22 | 48 (20 high, 28 medium) |
| Total actionable | 23 | 50 |
| 2-way coverage rate | 98.1% | 97.7% |
| 3-way coverage rate | 89.3% | 89.3% |

The corpus is robust (89% 3-way coverage maintained even with 90 edges), but 50 genuine gaps exist.

### Root Cause of Gaps

- **22 of 26 new 3-way gaps involve `ext_float_textures`** — only 2 seeds in the corpus use float texture extensions
- **4 new gaps involve `ext_compressed_textures`** with `texture_3d`/`texture_arrays`
- **1 low-diversity pair**: `ext_color_buffer_float + pixel_ops` has 13 seeds but only 2 distinct fingerprints

## Revised Phase Plan

The original design had: Phase 1 (Foundation) → Phase 2 (Depth Enrichment) → Phase 3 (Generation).

**Revised approach**: Insert a topology expansion step, then proceed directly to recipe generation. The optional depth enrichment (resource_tracking, interaction_graph, sequence_analyzer) is deferred — Phase 1 + topology expansion + recipe generation provides a complete pipeline.

### Step 1: Topology Expansion

**Goal**: Add 35 missing edges to `docs/interaction_topology.json`

**New edges grouped by tier:**

#### Critical (6 edges — core render pipeline)

| # | Pair | Relationship |
|---|---|---|
| 1 | draw_calls ↔ shader_pipeline | Every draw call requires an active shader program |
| 2 | draw_calls ↔ attributes | Draw calls consume vertex attribute data |
| 3 | draw_calls ↔ uniforms | Draw calls consume current uniform state |
| 4 | buffer_ops ↔ attributes | Buffers back vertex attribute pointers |
| 5 | mrt ↔ shader_pipeline | Fragment shader outputs map to MRT color attachments |
| 6 | shader_pipeline ↔ fbo | Shader outputs write to FBO attachments |

#### High (9 edges — common interactions with fuzzing value)

| # | Pair | Relationship |
|---|---|---|
| 7 | depth_stencil ↔ blending | Sequential per-fragment pipeline stages |
| 8 | viewport_scissor ↔ fbo | Viewport must match FBO dimensions |
| 9 | buffer_ops ↔ draw_calls | Element index buffers for drawElements |
| 10 | transform_feedback ↔ vao | Stream-out/stream-in buffer patterns |
| 11 | buffer_ops ↔ instancing | Instance attribute data from buffers |
| 12 | shader_pipeline ↔ blending | Shader output is blend source operand |
| 13 | shader_pipeline ↔ depth_stencil | gl_FragDepth overrides depth test value |
| 14 | ext_color_buffer_float ↔ blending | Float render target blending |
| 15 | ext_color_buffer_float ↔ renderbuffer | Float renderbuffer storage |

#### Medium (20 edges — real but less commonly exercised)

| # | Pair | Relationship |
|---|---|---|
| 16 | texture_3d ↔ shader_pipeline | sampler3D uniforms in fragment shaders |
| 17 | texture_3d ↔ sampler | Sampler TEXTURE_WRAP_R for 3D textures |
| 18 | texture_3d ↔ pixel_ops | UNPACK_IMAGE_HEIGHT for texImage3D |
| 19 | texture_arrays ↔ sampler | Sampler applies to array texture bindings |
| 20 | texture_arrays ↔ shader_pipeline | sampler2DArray uniforms |
| 21 | pixel_ops ↔ texture_arrays | UNPACK params for array layer upload |
| 22 | renderbuffer ↔ pixel_ops | readPixels from renderbuffer-backed FBO |
| 23 | renderbuffer ↔ blending | Blend to renderbuffer color attachment |
| 24 | ext_color_buffer_float ↔ pixel_ops | Float data readback |
| 25 | ext_float_textures ↔ sampler | OES_texture_float_linear filtering |
| 26 | ext_compressed_textures ↔ texture_3d | compressedTexImage3D |
| 27 | ext_compressed_textures ↔ texture_arrays | Compressed array layers |
| 28 | ext_draw_buffers_indexed ↔ viewport_scissor | Per-draw-buffer colorMaskiOES |
| 29 | depth_stencil ↔ viewport_scissor | Write masks + scissor before depth |
| 30 | blending ↔ viewport_scissor | colorMask affects blending output |
| 31 | ubo ↔ uniforms | Shared uniform namespace in programs |
| 32 | instancing ↔ shader_pipeline | gl_InstanceID built-in |
| 33 | shader_pipeline ↔ viewport_scissor | gl_FragCoord from viewport transform |
| 34 | mrt ↔ integer_textures | Mixed int/float MRT attachments |
| 35 | ext_float_textures ↔ shader_pipeline | Float texture sampling in shaders |

**Implementation**: Direct edit to `docs/interaction_topology.json`. No code changes needed. Re-run pipeline to confirm 50 gaps.

### Step 2: Phase 3 — Recipe Generation (gap_spec.py)

**Goal**: Generate structured seed recipes from the 50 actionable gaps.

**Module**: `scripts/api_audit/gap_spec.py`

#### Gap Filtering

Before recipe generation, filter gaps for relevance:

```python
def is_relevant(combo, priority):
    """Filter out low-value gaps."""
    UBIQUITOUS = {"shader_pipeline", "draw_calls", "attributes",
                  "uniforms", "viewport_scissor", "pixel_ops"}
    EXTENSION_CATEGORIES = {"ext_float_textures", "ext_color_buffer_float",
                           "ext_draw_buffers_indexed", "ext_texture_filter_anisotropic",
                           "ext_compressed_textures", "ext_disjoint_timer_query"}

    # Skip all-ubiquitous combos
    if all(f in UBIQUITOUS for f in combo):
        return False

    # Skip extension-only combos without security relevance
    SECURITY_RELEVANT = {"fbo", "buffer_ops", "transform_feedback",
                         "renderbuffer", "sync", "ext_color_buffer_float"}
    non_ext = [f for f in combo if f not in EXTENSION_CATEGORIES]
    if len(non_ext) == 0 and not any(f in SECURITY_RELEVANT for f in combo):
        return False

    return True
```

#### Recipe Format

Each recipe is a JSON specification that provides context for an LLM to write a seed:

```json
{
    "recipe_id": "gap_001",
    "priority": "high",
    "target_features": ["ext_float_textures", "fbo", "sampler"],
    "topology_connected": true,
    "reason": "Uncovered 3-way: float textures sampled in FBO render target",

    "required_methods": {
        "ext_float_textures": ["getExtension"],
        "fbo": ["createFramebuffer", "bindFramebuffer", "framebufferTexture2D", "checkFramebufferStatus"],
        "sampler": ["createSampler", "bindSampler", "samplerParameteri", "deleteSampler"]
    },
    "bonus_methods": {
        "ext_float_textures": [],
        "fbo": ["blitFramebuffer", "readBuffer"],
        "sampler": ["samplerParameterf", "getSamplerParameter"]
    },

    "topology_edges": [
        {"pair": ["ext_float_textures", "sampler"], "relationship": "OES_texture_float_linear filtering"},
        {"pair": ["ext_float_textures", "fbo"], "relationship": "Float texture as FBO color attachment"},
        {"pair": ["fbo", "sampler"], "relationship": "Sampler bound to texture read from FBO"}
    ],

    "seed_constraints": {
        "tier1_vars": {"min": 5, "max": 8},
        "tier3_enums": {"min": 4, "max": 6},
        "try_catch_blocks": {"min": 6, "max": 10},
        "line_repetition_patterns": {"min": 3},
        "total_lines": {"min": 150, "max": 300}
    },

    "reference_seeds": []
}
```

#### Reference Seed Selection

For each recipe, select up to 3 reference seeds that:
1. Cover the most target features (partial overlap is fine)
2. Have the highest depth ratios for shared features
3. Are validated (pass test runner)

Algorithm:
```python
def select_references(target_features, corpus_features, max_refs=3):
    """Select reference seeds by feature overlap score."""
    scored = []
    for filepath, fp in corpus_features.items():
        overlap = len(set(target_features) & set(fp["features"]))
        if overlap == 0:
            continue
        depth_score = sum(fp["depth_ratios"].get(f, 0) for f in target_features)
        scored.append((overlap, depth_score, filepath))
    scored.sort(reverse=True)
    return [s[2] for s in scored[:max_refs]]
```

#### Batch Planning

Produce up to 4 batches of max 5 recipes each (20 total):

```python
def plan_batches(recipes, max_batches=4, max_per_batch=5):
    """Distribute recipes across batches with feature concentration limits."""
    MAX_FEATURE_PER_BATCH = 3  # Max recipes targeting same feature in one batch

    sorted_recipes = sorted(recipes, key=lambda r: r["priority_key"])
    batches = []
    remaining = list(sorted_recipes)

    for _ in range(max_batches):
        if not remaining:
            break
        batch = []
        feature_counts = {}
        deferred = []
        for recipe in remaining:
            # Check concentration limit
            over_limit = False
            for f in recipe["target_features"]:
                if feature_counts.get(f, 0) >= MAX_FEATURE_PER_BATCH:
                    over_limit = True
                    break
            if over_limit:
                deferred.append(recipe)
                continue
            batch.append(recipe)
            for f in recipe["target_features"]:
                feature_counts[f] = feature_counts.get(f, 0) + 1
            if len(batch) >= max_per_batch:
                deferred.extend(remaining[remaining.index(recipe)+1:])
                break
        batches.append(batch)
        remaining = deferred

    return batches
```

### Step 3: CLI Integration

Add flags to `__main__.py`:

```
--gap-recipes PATH      Output gap recipes (JSON)
--max-recipes N         Maximum recipes to generate (default: 20)
--max-batches N         Maximum batches (default: 4)
```

When `--gap-recipes` is provided alongside `--combination-matrix`:
1. Run feature detection + combination matrix (existing)
2. Filter gaps for relevance
3. Generate recipes with reference seeds
4. Plan batches
5. Write recipes JSON

### Step 4: Weak Coverage Recipes (Optional Enhancement)

For combos with high seed count but low fingerprint diversity (from `low_diversity` output), generate "diversity recipes" that target the same features but with different API method patterns.

This is a minor enhancement since only 1-2 low-diversity pairs exist currently. Defer until after initial recipe generation proves useful.

## Deferred: Phase 2 Depth Enrichment

The original design's Phase 2 modules (resource_tracking.py, interaction_graph.py, sequence_analyzer.py) are deferred. Rationale:

1. **50 gaps exist without depth analysis** — recipe generation can proceed with Phase 1 data alone
2. **Depth enrichment adds implementation complexity** — AST-based resource tracking, scope disambiguation, miss rate monitoring
3. **The design explicitly states Phase 2 is optional** — "Phase 1 + Phase 3 form a complete, self-sufficient pipeline"
4. **If recipes prove insufficient**, depth analysis can be added later to improve recipe quality with interaction_requirements and required_state_paths

## Implementation Order

| Task | Description | Dependencies | Effort |
|---|---|---|---|
| 1 | Expand interaction_topology.json (35 edges) | None | Small |
| 2 | Verify expanded topology results | Task 1 | Small |
| 3 | Implement gap_spec.py (filtering, recipes, references, batches) | Task 1 | Medium |
| 4 | Add CLI flags (--gap-recipes, --max-recipes, --max-batches) | Task 3 | Small |
| 5 | Write tests for gap_spec.py | Task 3 | Medium |
| 6 | End-to-end validation | Tasks 1-5 | Small |

## Expected Outcome

After implementation:
- `python -m api_audit --feature-categories ... --interaction-topology ... --combination-matrix ... --gap-recipes recipes.json --n-way 3`
- Produces: Matrix report (50 gaps) + Recipe file (up to 20 prioritized recipes in 4 batches)
- Each recipe has: target features, required methods, topology context, reference seeds, seed constraints
- Recipes feed into the `expand-webgl-coverage` skill or direct LLM-guided seed writing
