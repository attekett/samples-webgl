# Round 5: 25-Seed Enhancement Plan - Closing All Gaps to 20%

**Date**: 2026-01-27
**Target**: 25 new seeds (batches 41-45, seeds 201-225)
**Strategy**: Smart combinations to efficiently close all remaining gaps
**Corpus Growth**: 200 → 225 seeds

---

## Executive Summary

Round 5 is a focused "perfection round" to bring ALL feature categories to 20%+ coverage. Using smart multi-feature combinations, we can close 8 remaining gaps with just 25 seeds.

**Current Gaps** (seeds needed to reach 20%):
1. Renderbuffers: 14% (28 seeds) → needs +12
2. Integer Textures: 17% (35 seeds) → needs +5
3. Instanced Rendering: 18% (36 seeds) → needs +4
4. Pixel Operations: 18% (37 seeds) → needs +3
5. Sampler Objects: 18% (36 seeds) → needs +4
6. Sync Objects: 18% (37 seeds) → needs +3
7. Query Objects: 19% (39 seeds) → needs +1
8. Texture Arrays: 19% (38 seeds) → needs +2

**Total needed**: 34 individual contributions across 8 categories
**Strategy**: Use multi-feature seeds - each seed contributes to 2-3 gaps simultaneously

---

## Smart Combination Strategy

**Math**: 25 seeds × avg 1.4 gaps per seed = 35 gap contributions ✓

We'll use combinations that naturally fit together AND close multiple gaps:
- Renderbuffers + Pixel Ops (both need coverage)
- Integer Textures + Instancing (both need coverage)
- Samplers + Sync (both need coverage)
- Queries + Texture Arrays (both need coverage)

---

## Batch 41: Renderbuffers + Pixel Operations (5 seeds, s201-205)

**Strategy**: Close both Renderbuffers (-12) and Pixel Operations (-3) simultaneously

### s201: Renderbuffer + readPixels Mega
- 8 renderbuffers (RGBA8, RGBA16F, RGBA32F, R11F_G11F_B10F, RGB10_A2, DEPTH32F, DEPTH24_STENCIL8, STENCIL_INDEX8)
- readPixels from each with different pack parameters
- PBO async reads
- Format conversion patterns
- 12-14 try-catch blocks

### s202: Renderbuffer + copyTexSubImage
- 4 multisample renderbuffers (4, 8, 16, 32 samples)
- Blit to single-sample renderbuffers
- copyTexSubImage2D from renderbuffers to textures
- Multiple mipmap levels
- Texture array layer copies
- 11-13 try-catch blocks

### s203: Renderbuffer + Pixel Unpack
- 6 renderbuffers with different formats
- Blit between renderbuffers
- readPixels with complex UNPACK parameters
- Upload to textures with UNPACK state
- Pixel transfer pipeline
- 12-14 try-catch blocks

### s204: Renderbuffer Storage Extreme
- 12 renderbuffers
- Storage reallocation cycles (format changes)
- Size changes (256→128→64)
- Attachment/detachment patterns
- getRenderbufferParameter queries
- 11-13 try-catch blocks

### s205: Renderbuffer MRT + Pixel Reads
- 8 renderbuffers as MRT targets
- Per-target clearing
- Per-target readPixels with readBuffer cycling
- Different pack parameters per target
- Copy to texture array layers
- 13-15 try-catch blocks

**Coverage Contribution**:
- Renderbuffers: +5 (28→33, 16.5%)
- Pixel Operations: +5 (37→42, 21%) ✅ CLOSED

---

## Batch 42: Integer Textures + Instancing (5 seeds, s206-210)

**Strategy**: Close both Integer Textures (-5) and Instancing (-4) simultaneously

### s206: Integer Texture + Instancing Extreme
- 8 integer texture formats (R8I, R16I, R32I, RG32I, RGBA8UI, RGBA16UI, RGBA32I, RGBA32UI)
- 2048 instances with per-instance integer attributes
- Integer MRT (4 targets)
- clearBufferiv/clearBufferuiv
- 13-15 try-catch blocks

### s207: Integer 3D Texture + Instanced Layers
- R32I 3D texture (128×128×128)
- 1024 instances distributed across 128 slices
- Instanced rendering to 3D texture layers
- Integer sampling with isampler3D
- 12-14 try-catch blocks

### s208: Integer Texture Array + Instancing
- RGBA32I texture array (128 layers, 256×256)
- 2048 instances with gl_InstanceID → layer mapping
- Layered instanced rendering
- Per-layer occlusion queries
- 14-16 try-catch blocks

### s209: Mixed Integer Instancing
- 6 integer formats, 6 FBOs, 6 shader programs
- 1024 instances per format
- Format switching with instanced draws
- Signed/unsigned mixing patterns
- 13-15 try-catch blocks

### s210: Integer Texture + Indirect Instancing
- Integer textures as input (R32UI, RG32I)
- usampler2D / isampler2D in vertex shader
- 2048 instances reading integer texture data
- Integer MRT output
- Transform feedback with integer varyings
- 14-16 try-catch blocks

**Coverage Contribution**:
- Integer Textures: +5 (35→40, 20%) ✅ CLOSED
- Instanced Rendering: +5 (36→41, 20.5%) ✅ CLOSED

---

## Batch 43: Samplers + Sync Objects (5 seeds, s211-215)

**Strategy**: Close both Samplers (-4) and Sync (-3) simultaneously

### s211: Sampler Extreme + Sync
- 24 sampler objects with all parameter combinations
- MIN_FILTER: 6 modes
- MAG_FILTER: 2 modes
- WRAP_S/T/R: 3 modes each
- 48 fence syncs (2 per sampler)
- clientWaitSync with various timeouts
- 14-16 try-catch blocks

### s212: Sampler LOD + Sync Polling
- 16 samplers with MIN_LOD/MAX_LOD variations
- 32 mipmap levels across 4 textures
- 32 fence syncs
- getSyncParameter polling (512 iterations)
- LOD bias patterns
- 15-17 try-catch blocks

### s213: Shadow Samplers + waitSync
- 16 shadow samplers (COMPARE_REF_TO_TEXTURE)
- All compare functions (8) on 2 samplers each
- DEPTH_COMPONENT32F textures
- 64 fence syncs with waitSync (server-side)
- SYNC_FLUSH_COMMANDS_BIT variations
- 14-16 try-catch blocks

### s214: Anisotropic Samplers + Sync Churn
- EXT_texture_filter_anisotropic
- 16 samplers with anisotropy 1.0 to MAX
- 128 fence syncs with rapid creation/deletion
- Sampler binding churn (512 bind operations)
- Sync deletion while potentially in-use (UAF)
- 15-17 try-catch blocks

### s215: Sampler + Sync + Query Triple
- 12 samplers, 24 syncs, 12 queries
- Synchronize sampler changes with fences
- Query texture sampling performance
- Complex inter-dependency patterns
- 16-18 try-catch blocks

**Coverage Contribution**:
- Sampler Objects: +5 (36→41, 20.5%) ✅ CLOSED
- Sync Objects: +5 (37→42, 21%) ✅ CLOSED

---

## Batch 44: Queries + Texture Arrays + Renderbuffers (5 seeds, s216-220)

**Strategy**: Close Queries (-1), Texture Arrays (-2), and add more Renderbuffers

### s216: Query Mega + Texture Array
- 32 query objects (all types)
- TEXTURE_2D_ARRAY with 128 layers
- Per-layer occlusion queries
- Nested query scopes (intentional errors)
- Query availability polling (1024 iterations)
- 15-17 try-catch blocks

### s217: Texture Array + Query + Transform Feedback
- 2D array (256 layers, 128×128)
- Transform feedback writes to texture array
- TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN query
- Layer selection via transform feedback
- 16 query objects
- 14-16 try-catch blocks

### s218: Renderbuffer + Texture Array + Query
- 8 renderbuffers (various formats)
- Blit to texture array layers
- Occlusion query per renderbuffer
- Layered FBO attachments
- 12 query objects
- 13-15 try-catch blocks

### s219: Renderbuffer Extreme Alpha
- 16 renderbuffers with all format permutations
- MSAA variants (2, 4, 8, 16, 32 samples)
- Attachment cycling across 8 FBOs
- Renderbuffer parameter queries
- 12-14 try-catch blocks

### s220: Renderbuffer Extreme Beta
- 12 renderbuffers
- Complex blitting patterns (multisample resolves)
- Format conversions during blit
- Scissor test with blitting
- Packed depth-stencil formats
- 13-15 try-catch blocks

**Coverage Contribution**:
- Query Objects: +4 (39→43, 21.5%) ✅ CLOSED
- Texture Arrays: +3 (38→41, 20.5%) ✅ CLOSED
- Renderbuffers: +3 (33→36, 18%)

---

## Batch 45: Renderbuffers Final + API Diversity (5 seeds, s221-225)

**Strategy**: Close Renderbuffers gap and cover unused APIs

### s221: Renderbuffer Perfection Alpha
- 16 renderbuffers
- All remaining format combinations
- Storage reallocation stress
- Multi-FBO ping-pong
- Renderbuffer state queries
- 12-14 try-catch blocks

### s222: Renderbuffer Perfection Beta
- 12 renderbuffers
- Depth/stencil attachment patterns
- Combined DEPTH24_STENCIL8 usage
- Renderbuffer blitting comprehensive
- 11-13 try-catch blocks

### s223: Renderbuffer + Unused APIs
- 8 renderbuffers
- getRenderbufferParameter extensive usage
- invalidateFramebuffer usage (previously unused!)
- invalidateSubFramebuffer patterns
- Tile-based rendering optimization hints
- 12-14 try-catch blocks

### s224: Complete API Coverage
- getBufferParameter usage (previously unused!)
- copyTexImage2D usage (previously unused!)
- texParameterf usage (previously unused!)
- getActiveUniformBlockParameter usage
- Comprehensive query of all state
- 11-13 try-catch blocks

### s225: Extension Diversity
- WEBGL_compressed_texture_astc (if available)
- WEBGL_compressed_texture_etc (if available)
- All S3TC formats (DXT1, DXT3, DXT5)
- Compressed 3D textures
- Compressed texture arrays
- 10-12 try-catch blocks

**Coverage Contribution**:
- Renderbuffers: +4 (36→40, 20%) ✅ CLOSED
- API Diversity: 87% → 95%+
- Extension Coverage: 14% → 20%+

---

## Coverage Impact Projection

### Before Round 5 (200 seeds)
- Renderbuffers: 14% (28 seeds) ❌
- Pixel Operations: 18% (37 seeds) ❌
- Integer Textures: 17% (35 seeds) ❌
- Instanced Rendering: 18% (36 seeds) ❌
- Sampler Objects: 18% (36 seeds) ❌
- Sync Objects: 18% (37 seeds) ❌
- Query Objects: 19% (39 seeds) ❌
- Texture Arrays: 19% (38 seeds) ❌

### After Round 5 (225 seeds - Projected)
- Renderbuffers: 20% (40 seeds) ✅ +400% from Round 4 start
- Pixel Operations: 21% (42 seeds) ✅ +425% from Round 4 start
- Integer Textures: 20% (40 seeds) ✅ +208% from Round 4 start
- Instanced Rendering: 20.5% (41 seeds) ✅ +173% from Round 4 start
- Sampler Objects: 20.5% (41 seeds) ✅ +156% from Round 4 start
- Sync Objects: 21% (42 seeds) ✅ +147% from Round 4 start
- Query Objects: 21.5% (43 seeds) ✅ +126% from Round 4 start
- Texture Arrays: 20.5% (41 seeds) ✅ +117% from Round 4 start

**MILESTONE**: ALL 18 tracked feature categories at 20%+ coverage! 🎯

---

## Mutation-Fuzzing Optimization

All seeds maintain mutation-optimized architecture:

### Three-Zone Structure
- **Declaration Zone**: 10-18 amplification variables per seed
- **Setup Zone**: Resource creation with redundancy
- **Execution Zone**: State thrashing + draws + cleanup

### Variable Tiers
- **Tier 1**: 10-18 amplification variables
- **Tier 2**: 30-60 inline literals
- **Tier 3**: 8-12 enum constants

### Line Repetition Patterns
- Renderbuffer storage reallocation
- Sampler parameter cycling
- Sync creation/deletion loops
- Query polling spam
- Texture array layer iteration
- Integer format switching

### Error Path Exploitation
- 11-18 try-catch blocks per seed
- Multi-feature combinations (natural error sources)
- UAF patterns (delete-then-use)
- Format mismatches
- Invalid synchronization

---

## Technical Notes

### Smart Combination Rationale

**Batch 41** (RBO + Pixel Ops):
- Natural pairing: Renderbuffers are read via pixel operations
- Both gaps closed efficiently

**Batch 42** (Integer Tex + Instancing):
- Natural pairing: Instancing often renders to textures
- Integer textures with instanced draws is realistic

**Batch 43** (Samplers + Sync):
- Natural pairing: Sampler changes benefit from synchronization
- Tests texture cache coherency

**Batch 44** (Query + TexArray + RBO):
- Triple combination closes 3 gaps
- Queries measure operations on texture arrays and renderbuffers

**Batch 45** (RBO Final + API Diversity):
- Closes renderbuffer gap completely
- Covers previously unused APIs for completeness

### Complexity Targets

- Batch 41-42: 11-16 try-catch blocks, 200-260 lines
- Batch 43-44: 13-18 try-catch blocks, 220-280 lines
- Batch 45: 10-14 try-catch blocks, 180-240 lines

**Average**: ~215 lines/seed (consistent with corpus)

---

## Success Criteria

1. ✅ 25 new seeds created (s201-s225)
2. ✅ All seeds pass validation (100% success rate target)
3. ✅ ALL 8 gaps closed to 20%+ (perfection target)
4. ✅ API diversity increased to 95%+
5. ✅ No JavaScript errors
6. ✅ No WebGL errors (except intentional error paths)
7. ✅ Console logs stripped for production
8. ✅ Complexity scores 180-350 range
9. ✅ All seeds under 6 seconds execution time
10. ✅ Documented and committed to repository

---

## Implementation Strategy

### Phase 1: Analysis (Complete)
- ✅ Generate detailed corpus analysis
- ✅ Identify 8 gaps below 20%
- ✅ Create smart combination plan (this document)

### Phase 2: Parallel Generation
- Launch 5 parallel agents (batches 41-45)
- Each agent creates 5 seeds following this plan
- Target: ~30 minutes for 25 seeds

### Phase 3: Validation
- Run validate_new_seeds.sh on all 25 seeds
- Verify 100% pass rate
- Check for any unsupported extensions

### Phase 4: Production Preparation
- Strip console.log from all catch blocks
- Verify mutation-friendly structure
- Confirm complexity scores

### Phase 5: Documentation
- Generate final detailed analysis
- Compare before/after metrics
- Create Round 5 completion summary
- Final commit and push to repository

---

## Workflow Integration

This plan follows the established iterative workflow:

```bash
# This plan will be executed by parallel agents
# Each agent will receive their batch specification (41-45)
# Seeds will be created as: mutation_b{batch}_s{seed}_descriptor.html
```

**Naming Convention**:
- `mutation_b41_s201_renderbuffer_readpixels_mega.html`
- `mutation_b42_s206_integer_instancing_extreme.html`
- `mutation_b43_s211_sampler_extreme_sync.html`
- `mutation_b44_s216_query_mega_texarray.html`
- `mutation_b45_s225_extension_diversity.html`

---

## Expected Final Corpus State

**After Round 5**:
- Total seeds: 225
- All 18 feature categories at 20%+ coverage ✅
- API diversity at 95%+ ✅
- Extension coverage at 20%+ ✅
- Avg complexity: ~255 (maintained)
- Total try-catch blocks: ~2,670
- Total lines: ~48,000
- Grade: A+ (100/100) - Perfect corpus

---

**Plan Ready for Execution**: Round 5 perfection round to close all gaps!
