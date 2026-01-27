# Corpus Enhancement Plan - Coverage Gap Analysis

**Date**: 2026-01-27
**Current Corpus**: 50 mutation-optimized WebGL2 seeds
**Purpose**: Address feature coverage gaps identified in corpus statistics

---

## Executive Summary

The current 50-seed corpus achieves excellent coverage of core WebGL2 features but has identified gaps in specific advanced features. This plan targets the creation of 25 additional seeds to achieve 80%+ coverage across all WebGL2 feature categories.

**Target**: 75 total seeds (50 existing + 25 new)
**Estimated Time**: ~1 hour using parallel agent generation
**Priority**: High-value features with low current coverage

---

## Feature Coverage Gap Analysis

### Current Coverage Summary

| Feature Category | Current Coverage | Target Coverage | Gap |
|------------------|-----------------|-----------------|-----|
| Buffer Operations | 50/50 (100%) | 50/75 (67%) | ✅ Adequate |
| Uniform Buffer Objects | 8/50 (16%) | 20/75 (27%) | ❌ **12 seeds needed** |
| Transform Feedback | 4/50 (8%) | 15/75 (20%) | ❌ **11 seeds needed** |
| Texture Operations | 23/50 (46%) | 35/75 (47%) | ⚠️ **12 seeds needed** |
| 3D Textures | 5/50 (10%) | 15/75 (20%) | ❌ **10 seeds needed** |
| Texture Arrays | 6/50 (12%) | 15/75 (20%) | ❌ **9 seeds needed** |
| Framebuffer Objects | 17/50 (34%) | 25/75 (33%) | ✅ Adequate |
| Multiple Render Targets | 6/50 (12%) | 15/75 (20%) | ❌ **9 seeds needed** |
| Instanced Rendering | 10/50 (20%) | 18/75 (24%) | ⚠️ **8 seeds needed** |
| Vertex Array Objects | 21/50 (42%) | 30/75 (40%) | ✅ Adequate |
| Sync Objects | 2/50 (4%) | 10/75 (13%) | ❌ **8 seeds needed** |
| Query Objects | 2/50 (4%) | 10/75 (13%) | ❌ **8 seeds needed** |
| Sampler Objects | 1/50 (2%) | 10/75 (13%) | ❌ **9 seeds needed** |
| Integer Textures | 2/50 (4%) | 10/75 (13%) | ❌ **8 seeds needed** |
| Depth/Stencil Ops | 5/50 (10%) | 15/75 (20%) | ❌ **10 seeds needed** |
| Blending | 5/50 (10%) | 15/75 (20%) | ❌ **10 seeds needed** |

---

## High-Priority Feature Gaps (25 New Seeds)

### Batch 11: UBO-Heavy Seeds (5 seeds)
**Focus**: Uniform Buffer Objects with complex binding patterns

1. **mutation_b11_s51_ubo_large_blocks.html**
   - Large UBO blocks (16KB each)
   - Multiple binding points (8+)
   - Shared UBO across programs
   - Dynamic offset thrashing

2. **mutation_b11_s52_ubo_std140_packing.html**
   - std140 layout with complex structs
   - Array of structs in UBOs
   - Nested struct alignment
   - Padding exploitation

3. **mutation_b11_s53_ubo_copy_between.html**
   - copyBufferSubData between UBOs
   - Overlapping copy ranges
   - UBO to UBO transfers
   - Range validation edge cases

4. **mutation_b11_s54_ubo_invalidate.html**
   - invalidateBufferSubData on UBOs
   - Partial invalidation patterns
   - Immediate use after invalidation
   - Multiple invalidation cycles

5. **mutation_b11_s55_ubo_map_ranges.html**
   - mapBufferRange with UBOs
   - MAP_INVALIDATE_BUFFER_BIT patterns
   - MAP_FLUSH_EXPLICIT_BIT usage
   - Nested map/unmap cycles

### Batch 12: Transform Feedback Heavy (5 seeds)
**Focus**: Transform Feedback with complex capture patterns

6. **mutation_b12_s56_tf_rasterizer_off.html**
   - RASTERIZER_DISCARD for TF-only passes
   - Multi-buffer TF capture
   - Feedback loop detection
   - TF to draw cycle

7. **mutation_b12_s57_tf_primitives_written.html**
   - TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN query
   - Overflow detection
   - Pause/resume with query
   - Query result validation

8. **mutation_b12_s58_tf_buffer_overflow.html**
   - Deliberate overflow patterns
   - Buffer boundary testing
   - Offset/size validation
   - Error recovery paths

9. **mutation_b12_s59_tf_multi_program.html**
   - TF with multiple programs
   - Program switching during TF
   - Varying compatibility checks
   - Buffer reuse patterns

10. **mutation_b12_s60_tf_indexed_drawing.html**
    - Transform feedback with indexed draws
    - gl_VertexID in TF varyings
    - Primitive restart with TF
    - Index buffer corruption patterns

### Batch 13: Sync and Query Heavy (5 seeds)
**Focus**: Synchronization primitives and query objects

11. **mutation_b13_s61_sync_multiple_fences.html**
    - Multiple fence sync objects
    - Fence creation/deletion churn
    - clientWaitSync with SYNC_FLUSH_COMMANDS_BIT
    - Timeout exhaustion patterns

12. **mutation_b13_s62_sync_gpu_commands_complete.html**
    - SYNC_GPU_COMMANDS_COMPLETE queries
    - getSyncParameter polling
    - Sync object state thrashing
    - Race condition exploitation

13. **mutation_b13_s63_query_any_samples_passed.html**
    - ANY_SAMPLES_PASSED queries
    - Conservative occlusion testing
    - Multiple simultaneous queries
    - Query result availability polling

14. **mutation_b13_s64_query_primitives_generated.html**
    - PRIMITIVES_GENERATED query
    - Comparison with TF queries
    - Query nesting attempts
    - Query result caching patterns

15. **mutation_b13_s65_query_delete_active.html**
    - Deleting active query objects
    - Immediate reuse after delete
    - Query object name recycling
    - State corruption patterns

### Batch 14: Sampler Objects and Integer Textures (5 seeds)
**Focus**: Sampler objects with various texture types

16. **mutation_b14_s66_sampler_all_parameters.html**
    - All sampler parameters (min/mag filter, wrap modes)
    - Sampler object binding churn
    - Multiple samplers per texture unit
    - Parameter state thrashing

17. **mutation_b14_s67_sampler_shadow_compare.html**
    - TEXTURE_COMPARE_MODE with samplers
    - Shadow sampler variations
    - Compare function exhaustion
    - Depth texture + sampler combos

18. **mutation_b14_s68_integer_r32i_texture.html**
    - R32I/R32UI texture formats
    - imageLoad/imageStore patterns
    - Integer texture sampling
    - Format reinterpretation

19. **mutation_b14_s69_integer_rgba32i_atomic.html**
    - RGBA32I with atomic operations
    - imageAtomicAdd/Min/Max
    - Memory barrier patterns
    - Atomic operation chaining

20. **mutation_b14_s70_sampler_anisotropic.html**
    - EXT_texture_filter_anisotropic
    - Anisotropy level variations
    - Sampler vs texture state
    - Extension availability patterns

### Batch 15: MRT and Advanced Blending (5 seeds)
**Focus**: Multiple render targets with complex blending

21. **mutation_b15_s71_mrt_eight_targets.html**
    - Maximum MRT count (8 targets)
    - All COLOR_ATTACHMENTx used
    - drawBuffers exhaustion
    - Per-target clear values

22. **mutation_b15_s72_mrt_mixed_formats.html**
    - Mixed texture formats across MRTs
    - Float + Integer + Normalized
    - Format compatibility validation
    - Read back from mixed MRTs

23. **mutation_b15_s73_blend_equation_separate.html**
    - blendEquationSeparate per target
    - RGB vs Alpha equation differences
    - All blend equation modes
    - Equation switching patterns

24. **mutation_b15_s74_blend_func_separate.html**
    - blendFuncSeparate exhaustion
    - Source/dest factor combinations
    - Constant blend color variations
    - Dual source blending attempts

25. **mutation_b15_s75_depth_stencil_complex.html**
    - Complex depth/stencil interactions
    - Two-sided stencil with MRT
    - Depth bounds testing
    - Depth clamp (if available)

---

## Implementation Strategy

### Phase 1: Parallel Creation (Batches 11-15)
- **Agents**: 5 parallel agents (5 seeds each)
- **Time Estimate**: 30-40 minutes
- **Input**: This enhancement plan + original design document
- **Output**: 25 new mutation_b11-b15_s51-s75.html files

### Phase 2: Sequential Validation
- **Command**: `./run_tests.sh --test-file agent_outputs/mutation_b1[1-5]_*.html --browsers firefox`
- **Time Estimate**: ~2.5 minutes (5s per seed × 25 seeds + overhead)
- **Expected**: 95%+ pass rate (improved from 90% based on lessons learned)

### Phase 3: Fix and Production Preparation
- **Fix Failures**: Address any scoping or API misuse issues
- **Strip Logging**: Remove console.log from all catch blocks
- **Final Validation**: Re-test all 25 seeds
- **Time Estimate**: 10-15 minutes

### Total Time: ~1 hour (parallel approach)

---

## Agent Instructions for Enhancement Seeds

Each agent creating seeds from Batches 11-15 must:

1. **Read Required Documents**:
   - `docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md`
   - `docs/plans/2026-01-27-corpus-enhancement-coverage-gaps.md` (this file)
   - `.cursorrules`, `AGENTS.md`, `CODING_RULES.md`

2. **Follow Mutation-Optimized Architecture**:
   - Three-zone structure (Declaration/Setup/Execution)
   - Variable tier system (Amplification/Hot Spots/Enum Constants)
   - Five line repetition patterns
   - 6-12 try-catch blocks with console.log(e)

3. **Feature-Specific Requirements**:
   - **Batch 11 (UBO)**: Minimum 3 UBOs, 5+ binding points, dynamic offsets
   - **Batch 12 (TF)**: Minimum 2 TF buffers, interleaved or separate varyings
   - **Batch 13 (Sync/Query)**: Minimum 3 sync/query objects, polling patterns
   - **Batch 14 (Sampler/Int Tex)**: Minimum 3 sampler objects, integer formats
   - **Batch 15 (MRT/Blend)**: Minimum 4 render targets, complex blend modes

4. **Variable Scoping Lessons Learned**:
   - Declare all WebGL objects with `let` in Declaration Zone
   - Assign (not declare) inside try-catch blocks
   - Example: `let buffer; try { buffer = gl.createBuffer(); } catch(e) { console.log(e); }`

5. **Extension Handling**:
   - Check `UNSUPPORTED.md` before using extensions
   - Only use widely-supported extensions (EXT_color_buffer_float, etc.)
   - Add extension check before main()

6. **Validation Requirements**:
   - Must execute without JavaScript errors
   - Must not log to console (errors caught by try-catch)
   - Must complete within 5 seconds
   - Must render to 256x256 canvas

---

## Target Mutation Characteristics for Enhancement Seeds

### Expected Statistics (25 new seeds)

- **Total Lines**: ~5,000 additional lines (200 lines/seed average)
- **Try-Catch Blocks**: ~225 additional blocks (9 per seed)
- **Amplification Variables**: ~100 additional (4 per seed)
- **Inline Literals**: ~750 additional (30 per seed)
- **Total gl.* Calls**: ~2,200 additional (88 per seed)
- **Mutation Targets**: ~1,500 additional (60 per seed)

### Combined Corpus (75 seeds total)

- **Total Lines**: ~15,300 lines
- **Total Mutation Targets**: ~4,500 targets
- **Mutation Density**: 1 target per 3.4 lines (maintained)
- **Feature Coverage**: 80%+ across all categories

---

## Quality Assurance Checklist

Before considering the enhancement complete, verify:

- [ ] All 25 seeds follow three-zone architecture
- [ ] All 25 seeds have 6-12 try-catch blocks
- [ ] All 25 seeds have 4-6 amplification variables
- [ ] All 25 seeds have 20-40 inline literals
- [ ] All 25 seeds pass validation (100%)
- [ ] All 25 seeds have console.log stripped
- [ ] Coverage matrix shows 80%+ for target categories
- [ ] No unsupported extensions used
- [ ] All files 256x256 canvas resolution
- [ ] All files WebGL2 context required

---

## Extension Considerations

**Safe Extensions** (widely supported in Firefox):
- EXT_color_buffer_float
- EXT_texture_filter_anisotropic
- WEBGL_compressed_texture_s3tc
- WEBGL_compressed_texture_etc
- OES_texture_float_linear

**Avoid** (limited support):
- OES_sample_variables (not in Firefox Playwright)
- WEBGL_draw_instanced_base_vertex_base_instance
- Any WEBGL_multi_draw extensions

---

## Success Metrics

**Primary Metrics**:
- [ ] 75/75 seeds passing validation (100%)
- [ ] 80%+ coverage for UBO, TF, Sync, Query, Sampler, Integer Textures
- [ ] 50%+ coverage for all other categories
- [ ] Mutation density maintained at 1 target per 3-4 lines

**Secondary Metrics**:
- [ ] No extension-related failures
- [ ] No variable scoping errors
- [ ] First-pass success rate 95%+
- [ ] All seeds complete in < 5 seconds

---

## Commit Strategy

After enhancement completion:

```bash
# Stage new seeds
git add agent_outputs/mutation_b1[1-5]_s*.html

# Stage updated documentation
git add docs/plans/2026-01-27-corpus-enhancement-coverage-gaps.md
git add docs/MUTATION_SEEDS_COMPLETION_SUMMARY.md

# Commit with statistics
git commit -m "feat: add 25 enhancement seeds for coverage gaps

- Batch 11: UBO-heavy seeds (5 seeds)
- Batch 12: Transform Feedback heavy (5 seeds)
- Batch 13: Sync and Query heavy (5 seeds)
- Batch 14: Sampler and Integer Texture (5 seeds)
- Batch 15: MRT and Advanced Blending (5 seeds)

Coverage improvements:
- UBO: 16% → 27%
- Transform Feedback: 8% → 20%
- Sync Objects: 4% → 13%
- Query Objects: 4% → 13%
- Sampler Objects: 2% → 13%

Total corpus: 75 seeds, ~15,300 lines, ~4,500 mutation targets

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push to remote
git push origin master
```

---

## Future Work (Beyond 75 Seeds)

After completing this enhancement:

1. **WebGL1 Compatibility Layer** (25 seeds)
   - Target drivers with WebGL1-only paths
   - Extension-heavy WebGL1 patterns
   - Fallback code path exploration

2. **Error Recovery Patterns** (25 seeds)
   - Deliberate API misuse patterns
   - Context loss simulation
   - Resource exhaustion patterns

3. **Compression Format Focus** (10 seeds)
   - All compressed texture formats
   - Partial update patterns
   - Mipmap generation with compression

4. **Geometry Shader Simulation** (10 seeds)
   - Transform feedback emulating geometry shaders
   - Layered rendering patterns
   - Primitive assembly simulation

**Total Roadmap**: 145 seeds for comprehensive WebGL fuzzing corpus

---

## Conclusion

This enhancement plan addresses the most significant coverage gaps identified in the initial 50-seed corpus. By focusing on under-represented features (UBO, TF, Sync, Query, Sampler, Integer Textures) and using proven parallel generation techniques, we can achieve 80%+ coverage across all WebGL2 features within ~1 hour.

The resulting 75-seed corpus will provide comprehensive mutation targets for radamsa-based fuzzing while maintaining the high mutation density (1 target per 3.4 lines) that makes this corpus effective for finding driver memory corruption bugs.
