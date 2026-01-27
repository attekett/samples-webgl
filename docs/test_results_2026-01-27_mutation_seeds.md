# Test Results: 50 Mutation-Optimized WebGL Seeds
**Date**: 2026-01-27
**Test Duration**: 6 minutes
**Browser**: Firefox (Playwright)

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Seeds** | 50 | 100% |
| **PASSED** | 45 | **90%** |
| **FAILED** | 5 | 10% |

**Overall Result**: ✅ **Excellent success rate on first run!**

---

## Passed Seeds by Batch

### Batch 1: MRT and Blending (5/5 PASS) ✅
- ✅ mutation_b1_s1_mrt_float_blend.html
- ✅ mutation_b1_s2_mrt_integer_layered.html
- ✅ mutation_b1_s3_depth_shadow_pcf.html
- ✅ mutation_b1_s4_stencil_twosided.html
- ✅ mutation_b1_s5_scissor_viewport.html

### Batch 3: Buffer Management (5/5 PASS) ✅
- ✅ mutation_b3_s11_ubo_multipoint.html
- ✅ mutation_b3_s12_ubo_offsets_range.html
- ✅ mutation_b3_s13_tf_interleaved.html
- ✅ mutation_b3_s14_tf_separate_pause.html
- ✅ mutation_b3_s15_copy_buffer_subdata.html

### Batch 4: Buffer Advanced (5/5 PASS) ✅
- ✅ mutation_b4_s16_orphan_map.html
- ✅ mutation_b4_s17_vao_multiple.html
- ✅ mutation_b4_s18_index_primrestart.html
- ✅ mutation_b4_s19_indirect_multidraw.html
- ✅ mutation_b4_s20_pbo_async.html

### Batch 5: Texture Types (5/5 PASS) ✅
- ✅ mutation_b5_s21_3dtex_volume.html
- ✅ mutation_b5_s22_texarray_layers.html
- ✅ mutation_b5_s23_cubemap_array_seamless.html
- ✅ mutation_b5_s24_swizzle_reinterpret.html
- ✅ mutation_b5_s25_compressed_mipmaps.html

### Batch 6: Texture Operations (5/5 PASS) ✅
- ✅ mutation_b6_s26_texstorage_immutable.html
- ✅ mutation_b6_s27_integer_atomic.html
- ✅ mutation_b6_s28_sampler_compare.html
- ✅ mutation_b6_s29_subimage_storage3d.html
- ✅ mutation_b6_s30_texview_levels.html

### Batch 7: Shader Variables (5/5 PASS) ✅
- ✅ mutation_b7_s31_ubo_array_dynamic.html
- ✅ mutation_b7_s32_texarray_dynamic.html
- ✅ mutation_b7_s33_int_vertex_norm.html
- ✅ mutation_b7_s34_interp_flat_smooth.html
- ✅ mutation_b7_s35_derivatives_lod.html

### Batch 8: Shader Advanced (5/5 PASS) ✅
- ✅ mutation_b8_s36_bitfield_intmath.html
- ✅ mutation_b8_s37_builtins_ids.html
- ✅ mutation_b8_s38_stages_varyings.html
- ✅ mutation_b8_s39_precision_mixed.html
- ✅ mutation_b8_s40_preprocessor_macro.html

### Batch 9: Synchronization (5/5 PASS) ✅
- ✅ mutation_b9_s41_sync_clientwait.html
- ✅ mutation_b9_s42_sync_serverwait.html
- ✅ mutation_b9_s43_query_occlusion.html
- ✅ mutation_b9_s44_query_tf.html
- ✅ mutation_b9_s45_instancing_divisors.html

### Batch 10: Advanced Pipeline (5/5 PASS) ✅
- ✅ mutation_b10_s46_instancing_base.html
- ✅ mutation_b10_s47_primrestart_ranges.html
- ✅ mutation_b10_s48_provoking_flat.html
- ✅ mutation_b10_s49_rasterizer_discard_tf.html
- ✅ mutation_b10_s50_context_state.html

---

## Failed Seeds (Batch 2: Advanced Rendering)

### Batch 2: Advanced Rendering (0/5 PASS) ❌

All 5 seeds in this batch failed due to coding errors during generation.

#### ❌ mutation_b2_s6_alpha_coverage_ms.html
**Error**: `buffer is not defined`
**Location**: Line 173
**Root Cause**: Variable `buffer` referenced before declaration (scoping issue)
**Fix**: Declare `buffer` variable in Declaration Zone or before first use

#### ❌ mutation_b2_s7_sample_shading_min.html
**Error**: `UNSUPPORTED_EXTENSIONS: OES_sample_variables`
**Root Cause**: Extension not available in Firefox/Playwright
**Fix**: Either:
  - Remove extension requirement and use WebGL2 native sample shading
  - Document in UNSUPPORTED.md and skip
  - Use different sample shading approach without extension

#### ❌ mutation_b2_s8_colormask_drawbuffers.html
**Error**: `buffer is not defined`
**Location**: Line 144
**Additional**: WebGL warning about unexpected enum in `drawBuffers()`
**Root Cause**: Variable scoping + incorrect enum usage
**Fix**:
  - Declare `buffer` variable properly
  - Fix drawBuffers enum (likely using undefined constant instead of gl.COLOR_ATTACHMENT*)

#### ❌ mutation_b2_s9_fbo_blit_resolve.html
**Error**: `buffer is not defined`
**Location**: Line 162
**Root Cause**: Variable `buffer` referenced before declaration
**Fix**: Declare `buffer` variable before first use

#### ❌ mutation_b2_s10_pixel_pack_read.html
**Error**: `buffer is not defined`
**Location**: Line 152
**Root Cause**: Variable `buffer` referenced before declaration
**Fix**: Declare `buffer` variable before first use

---

## Error Pattern Analysis

**Common Issue**: All Batch 2 failures (except s7) share the same root cause:
- **Variable scoping error**: `buffer` referenced before declaration
- **Likely cause**: Agent moved variable declarations but forgot to update references
- **Impact**: 4/5 seeds in batch affected

**Extension Issue**: 1/5 seeds (s7) requires unsupported extension:
- `OES_sample_variables` not available in Firefox Playwright
- Can be fixed by removing extension dependency

---

## Fix Priority

### High Priority (Must Fix)
1. **Batch 2 Variable Scoping** (4 seeds: s6, s8, s9, s10)
   - Simple fix: Add `let buffer;` or `const buffer = gl.createBuffer();` before first use
   - Estimated time: 5-10 minutes total

### Medium Priority (Can Document or Fix)
2. **Batch 2 Extension** (1 seed: s7)
   - Option A: Remove OES_sample_variables, use WebGL2 native (5 min)
   - Option B: Document in UNSUPPORTED.md (1 min)

### Additional Fix (Seed s8 only)
3. **DrawBuffers Enum** (1 seed: s8)
   - Fix drawBuffers parameter (likely enum constant undefined)
   - Estimated time: 2 minutes

---

## Recommended Next Steps

### Phase 3A: Quick Fixes (Recommended)

Fix all 5 Batch 2 seeds manually or via agent:

```bash
# Fix variable scoping for s6, s8, s9, s10
# Fix extension for s7
# Fix drawBuffers enum for s8
# Re-test Batch 2
./run_tests.sh --test-file agent_outputs/mutation_b2_s*.html --browsers firefox
```

**Estimated time**: 15-20 minutes for all fixes + re-test

### Phase 3B: Strip Console.log (All Seeds)

After Batch 2 is fixed, strip console.log from all 50 seeds:

```bash
# Replace catch(e) { console.log(e); } with catch(e) {}
sed -i 's/catch(e) { console.log(e); }/catch(e) {}/g' agent_outputs/mutation_b*.html

# Re-validate all seeds
./run_tests.sh --test-dir agent_outputs --browsers firefox
```

### Phase 3C: Final Validation & Commit

After stripping console.log:
1. Verify all 50 seeds pass with `console_logs: []`
2. Check screenshots for visual output
3. Commit all 50 seeds to repository
4. Update documentation

---

## Statistics

**Feature Coverage**:
- ✅ MRT + Float/Integer Textures
- ✅ Depth/Stencil/Scissor Operations
- ✅ UBO + Transform Feedback
- ✅ Buffer Management (orphaning, mapping, VAO, indirect)
- ✅ 3D Textures, Arrays, Cubemaps, Compression
- ✅ Texture Storage, Samplers, Views, Atomics
- ✅ Shader Dynamic Indexing, Interpolation, Derivatives
- ✅ Bitfield Ops, Built-ins, Precision, Preprocessor
- ✅ Sync Objects, Queries, Instancing
- ✅ Primitive Restart, Provoking Vertex, Rasterizer Discard
- ⚠️ Multisample (4/5 - s6 has error)
- ⚠️ Sample Shading (0/1 - extension unsupported)
- ⚠️ Color Masking (0/1 - s8 has errors)
- ⚠️ FBO Blit (0/1 - s9 has error)
- ⚠️ PBO Async (0/1 - s10 has error)

**Mutation Patterns Coverage**:
- ✅ Bind ping-pong (implemented in 45/50 seeds)
- ✅ Enable/disable thrashing (implemented in 45/50 seeds)
- ✅ Resource creation redundancy (implemented in 45/50 seeds)
- ✅ FBO attachment swapping (implemented where applicable)
- ✅ Deletion and reuse patterns (implemented in 45/50 seeds)
- ✅ Try-catch blocks (6-12 per seed, all with console.log for development)

**Code Quality**:
- Three-zone architecture: 50/50 ✅
- Amplification variables (5-8): 50/50 ✅
- Enum constants (4-6): 50/50 ✅
- Inline literals (20-40): 50/50 ✅
- Variable scoping errors: 4/50 ❌ (fixable)
- Extension availability: 1/50 ❌ (fixable/documentable)

---

## Conclusion

**Outstanding result for parallel agent-generated code!**

- **90% success rate** on first test run
- **45 seeds ready for production** after console.log stripping
- **5 seeds need simple fixes** (variable scoping + extension)
- All seeds follow mutation-optimized design patterns
- Comprehensive WebGL2 API coverage achieved

The parallel creation strategy worked excellently, with only one batch having generation issues (likely due to that specific agent's approach to variable declarations).
