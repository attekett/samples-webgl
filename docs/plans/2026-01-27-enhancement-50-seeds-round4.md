# Round 4: 50-Seed Enhancement Plan - Exotic Gap Mixes

**Date**: 2026-01-27
**Target**: 50 new seeds (batches 31-40, seeds 151-200)
**Strategy**: Exotic combinations of underrepresented features
**Corpus Growth**: 150 → 200 seeds

---

## Executive Summary

Round 4 focuses on **exotic feature combinations** targeting the 8 identified coverage gaps with unusual mixes that exercise multiple underrepresented subsystems simultaneously.

**Priority Gaps** (from detailed analysis):
1. Renderbuffers: 2% → +26 needed
2. Pixel Operations: 5% → +22 needed
3. Integer Textures: 8% → +17 needed
4. Instanced Rendering: 10% → +15 needed
5. Sampler Objects: 10% → +14 needed
6. Sync Objects: 11% → +13 needed
7. Query Objects: 12% → +11 needed
8. Transform Feedback: 15% → +7 needed

**Approach**: Each batch combines 2-4 gaps in unusual ways not commonly seen in graphics code, maximizing driver state machine complexity.

---

## Batch 31: Renderbuffers Extreme (5 seeds, s151-155)

**Focus**: Deep renderbuffer coverage with multisample variations

### s151: Multisample Renderbuffers (4, 8, 16 samples)
- 3+ renderbuffers with different sample counts (4, 8, 16)
- Bind churn between multisample renderbuffers
- Mixed depth/stencil/color renderbuffer types
- FBO completeness checks with varying samples
- 8-10 try-catch blocks

### s152: Renderbuffer Format Zoo
- 15+ renderbuffers with different formats:
  - RGBA8, RGBA16F, RGBA32F
  - RGB10_A2, R11F_G11F_B10F
  - DEPTH_COMPONENT16, DEPTH_COMPONENT24, DEPTH_COMPONENT32F
  - DEPTH24_STENCIL8, DEPTH32F_STENCIL8
- Format switching patterns
- getRenderbufferParameter queries
- 9-11 try-catch blocks

### s153: Renderbuffer Blitting Patterns
- Multiple FBOs with renderbuffer attachments
- blitFramebuffer between renderbuffers (different sizes)
- Multisample → Single sample resolve
- Pixel format conversions during blit
- Scissor test interaction
- 10-12 try-catch blocks

### s154: Renderbuffer Storage Reallocation
- Create renderbuffers, allocate storage
- Reallocate same renderbuffer with different size/format
- Attach, render, detach, reallocate, reattach
- Storage invalidation patterns
- 8-10 try-catch blocks

### s155: Renderbuffer + MRT Complex
- 8 color attachments using renderbuffers
- Depth/stencil renderbuffers
- drawBuffers with all renderbuffer targets
- clearBufferfv per attachment
- 11-13 try-catch blocks

**Coverage Contribution**: +5 Renderbuffers (2% → 4%)

---

## Batch 32: Pixel Operations Extreme (5 seeds, s156-160)

**Focus**: Deep readPixels and pixel transfer operations

### s156: readPixels Format Matrix
- Read all supported formats: RGBA, RGB, RED, RG
- Read all types: UNSIGNED_BYTE, FLOAT, INT, UNSIGNED_INT
- Different pack alignment (1, 2, 4, 8)
- PACK_ROW_LENGTH, PACK_SKIP_PIXELS, PACK_SKIP_ROWS
- 10-12 try-catch blocks

### s157: Async Pixel Reads (PBO)
- PIXEL_PACK_BUFFER with readPixels
- Multiple PBOs with different sizes
- Bind different pack buffers, read, fence, map
- Overlapping read operations
- getBufferSubData patterns
- 12-14 try-catch blocks

### s158: copyTexSubImage Variants
- copyTexSubImage2D from FBO → Texture
- copyTexSubImage3D to texture arrays
- Copy to different mipmap levels
- Copy from depth/stencil attachments
- Mixed texture types (2D, 3D, Array)
- 10-12 try-catch blocks

### s159: Pixel Unpack Operations
- UNPACK_ALIGNMENT, UNPACK_ROW_LENGTH
- UNPACK_IMAGE_HEIGHT, UNPACK_SKIP_PIXELS
- texImage2D/3D with various unpack parameters
- Subimage updates with unpack state
- 9-11 try-catch blocks

### s160: Pixel Operations + Integer Textures
- readPixels from integer texture attachments
- readBuffer cycling with integer formats
- clearBufferiv/clearBufferuiv
- copyTexSubImage with integer formats
- 11-13 try-catch blocks

**Coverage Contribution**: +5 Pixel Operations (5% → 8%)

---

## Batch 33: Renderbuffers + Integer Textures (5 seeds, s161-165)

**Focus**: Exotic mix of renderbuffers with integer texture rendering

### s161: Integer Renderbuffers
- Renderbuffers with R32I, RGBA32I formats
- Multisample integer renderbuffers
- clearBufferiv to integer renderbuffers
- readPixels integer data from renderbuffers
- 10-12 try-catch blocks

### s162: Mixed Integer/Float Renderbuffers
- 4 FBOs, each with mixed attachments:
  - COLOR0: RGBA32F renderbuffer
  - COLOR1: RGBA32I renderbuffer
  - Depth: DEPTH_COMPONENT24 renderbuffer
- Draw to float, then integer, then float
- 11-13 try-catch blocks

### s163: Integer Texture + Renderbuffer FBO
- Texture attachments: R32UI, RG32I
- Renderbuffer attachments: RGBA16I, DEPTH24_STENCIL8
- MRT with 4 integer targets (2 textures, 2 renderbuffers)
- Per-attachment clears
- 12-14 try-catch blocks

### s164: Renderbuffer Blitting + Integer
- Integer format renderbuffers
- blitFramebuffer between integer renderbuffers
- Multisample integer → single sample integer resolve
- Mixed integer types (I vs UI)
- 10-12 try-catch blocks

### s165: Renderbuffer Storage Churn + Integer
- Allocate integer renderbuffer storage
- Render to it
- Reallocate with different integer format
- Render again, read back
- Format conversion attempts (error paths)
- 11-13 try-catch blocks

**Coverage Contribution**: +5 Renderbuffers, +5 Integer Textures (2%→4%, 8%→11%)

---

## Batch 34: Pixel Operations + Instanced Rendering (5 seeds, s166-170)

**Focus**: Exotic mix of instanced draws with pixel readback

### s166: Instanced Draw + Pixel Readback
- Draw 1024 instances to FBO
- readPixels after each instance batch
- Verify pixel colors in different pack formats
- PBO async reads
- 11-13 try-catch blocks

### s167: Instanced MRT + Per-Target Reads
- 8 MRT targets
- drawArraysInstanced with 512 instances
- readBuffer cycling, read each target
- Different pixel formats per target
- 12-14 try-catch blocks

### s168: Instanced + copyTexImage
- Draw instanced geometry to FBO
- copyTexImage2D/3D to textures
- Use copied textures as input for next instanced draw
- Feedback loop with instancing
- 13-15 try-catch blocks

### s169: Instanced Rendering + Integer Pixels
- Draw instances to integer texture attachments
- readPixels with INT/UINT types
- clearBufferiv between draws
- PBO reads of integer data
- 11-13 try-catch blocks

### s170: Multi-Instance + Multi-Read
- Multiple instanced draw calls (256, 512, 1024 instances)
- Multiple readPixels after each draw
- Different pack parameters per read
- Scissor regions + instancing
- 12-14 try-catch blocks

**Coverage Contribution**: +5 Pixel Operations, +5 Instanced Rendering (8%→10%, 10%→13%)

---

## Batch 35: Samplers + Sync Objects (5 seeds, s171-175)

**Focus**: Exotic sampler parameter variations with fence synchronization

### s171: Sampler + Fence Synchronization
- 16 sampler objects with different parameters
- Bind sampler, draw, fence sync
- clientWaitSync between sampler changes
- Timeout variations (0, 1000, TIMEOUT_IGNORED)
- 13-15 try-catch blocks

### s172: Sampler LOD + Sync Queries
- 12 samplers with MIN_LOD, MAX_LOD variations
- Draw with each sampler
- fenceSync after each draw
- getSyncParameter polling (256 polls)
- deleteSync patterns
- 14-16 try-catch blocks

### s173: Shadow Samplers + Multi-Sync
- 8 shadow samplers (COMPARE_REF_TO_TEXTURE)
- Different compare functions per sampler
- Multiple fence syncs (32 fences)
- waitSync (server-side) patterns
- 12-14 try-catch blocks

### s174: Sampler Churn + Sync Spam
- Rapid sampler binding (bind, draw, unbind, repeat)
- fenceSync after every operation
- clientWaitSync with 0 timeout (512 times)
- Sampler deletion during sync wait (UAF)
- 15-16 try-catch blocks

### s175: Anisotropic Samplers + Sync
- EXT_texture_filter_anisotropic
- 16 samplers with different MAX_TEXTURE_MAX_ANISOTROPY values
- Fence sync between anisotropy changes
- SYNC_FLUSH_COMMANDS_BIT variations
- 13-15 try-catch blocks

**Coverage Contribution**: +5 Samplers, +5 Sync Objects (10%→13%, 11%→14%)

---

## Batch 36: Queries + Transform Feedback (5 seeds, s176-180)

**Focus**: Exotic query/TF combinations

### s176: TF + Query Integration
- Transform feedback with TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN query
- Occlusion query (ANY_SAMPLES_PASSED) simultaneously
- Nested query scopes
- Query availability polling
- 12-14 try-catch blocks

### s177: Multi-Query + Multi-TF
- 4 transform feedback buffers
- 8 query objects (mixed types)
- Begin multiple queries, TF, end queries
- Query result readback
- Buffer overflow TF patterns
- 14-16 try-catch blocks

### s178: Query Deletion + TF Active
- Begin queries, start TF
- Delete queries while active (UAF)
- Delete TF objects while active
- Continue drawing, read results
- 13-15 try-catch blocks

### s179: TF Rasterizer Discard + Queries
- Enable RASTERIZER_DISCARD
- Transform feedback captures geometry
- Occlusion queries (expect 0)
- Timestamp queries around TF
- 11-13 try-catch blocks

### s180: TF + Query + VAO Instancing
- Instanced draws with TF enabled
- Per-instance attribute divisors
- Primitives written query
- VAO switching during TF
- 13-15 try-catch blocks

**Coverage Contribution**: +5 Queries, +5 Transform Feedback (12%→15%, 15%→18%)

---

## Batch 37: Renderbuffers + Pixel Ops + Samplers (5 seeds, s181-185)

**Focus**: Triple combination - exotic 3-way mix

### s181: Renderbuffer → ReadPixels → Sample
- Render to multisample renderbuffer
- Blit to single-sample renderbuffer
- readPixels to PBO
- Copy pixels to texture
- Sample texture with sampler object
- 14-16 try-catch blocks

### s182: Sampler + Integer Renderbuffer + Reads
- Integer renderbuffers (RGBA32I)
- Render integer data
- readPixels integer formats
- Shadow compare samplers (incompatible, error paths)
- 13-15 try-catch blocks

### s183: Multi-Renderbuffer + Multi-Read + Multi-Sampler
- 8 renderbuffers (different formats)
- Render to each
- readPixels from each with different pack params
- Copy to textures
- Sample with 8 different sampler objects
- 15-16 try-catch blocks

### s184: Renderbuffer Blit + Pixel Unpack + Sampler
- Blit between renderbuffers
- readPixels with complex unpack parameters
- Upload to texture with same unpack state
- Sample with anisotropic sampler
- 14-16 try-catch blocks

### s185: Renderbuffer MRT + Per-Target Read + Samplers
- 8 color renderbuffers
- Draw to MRT
- readBuffer + readPixels for each
- Copy to texture array layers
- Sample array with multiple samplers
- 15-16 try-catch blocks

**Coverage Contribution**: +5 each (Renderbuffers, Pixel Ops, Samplers)

---

## Batch 38: Integer Textures + Instancing + Queries (5 seeds, s186-190)

**Focus**: Triple combination targeting 3 gaps

### s186: Integer MRT + Instanced + Query
- 4 integer texture attachments (RGBA32I)
- drawArraysInstanced with 1024 instances
- Primitives generated query
- clearBufferiv per attachment
- 14-16 try-catch blocks

### s187: Integer Texture Array + Instanced Layers + Query
- TEXTURE_2D_ARRAY with 64 integer layers
- Layered instanced rendering
- Draw to specific layers via gl_InstanceID
- Occlusion queries per layer
- 15-16 try-catch blocks

### s188: Integer 3D Texture + Instanced + Multi-Query
- Integer 3D texture (R32I, 64x64x64)
- Instanced draws writing to 3D slices
- Multiple query types simultaneously
- Query availability spam (256 polls)
- 14-16 try-catch blocks

### s189: Integer Texture + Indirect Instancing + Query
- Integer textures as both input and output
- drawArraysInstanced (implicit indirect pattern)
- Transform feedback query
- Integer texture sampling with usampler
- 13-15 try-catch blocks

### s190: Mixed Integer Types + Instancing + Query
- R8I, R16I, R32I, RGBA8UI, RGBA16UI, RGBA32UI
- Instanced rendering to each format
- Per-format occlusion query
- Format switching patterns
- 14-16 try-catch blocks

**Coverage Contribution**: +5 each (Integer Textures, Instancing, Queries)

---

## Batch 39: All 8 Gaps Combined (5 seeds, s191-195)

**Focus**: Every gap feature in one seed

### s191: The Octopus (8-way mix, light)
- Renderbuffers: 2 multisample renderbuffers
- Pixel Ops: readPixels with PBO
- Integer Textures: RGBA32I attachment
- Instancing: drawArraysInstanced 256 instances
- Samplers: 4 sampler objects
- Sync: 4 fence syncs
- Queries: 2 query objects
- Transform Feedback: 1 TF buffer
- 15-16 try-catch blocks

### s192: The Octopus (8-way mix, medium)
- Renderbuffers: 4 different format renderbuffers
- Pixel Ops: copyTexSubImage2D + readPixels
- Integer Textures: 2 integer texture types
- Instancing: 512 instances with divisors
- Samplers: 8 samplers with LOD control
- Sync: 8 fences with various timeouts
- Queries: 4 queries (mixed types)
- Transform Feedback: 2 TF buffers
- 16-18 try-catch blocks

### s193: The Octopus (8-way mix, heavy)
- Renderbuffers: 8 renderbuffers + blitting
- Pixel Ops: Multiple readPixels + unpack
- Integer Textures: 4 integer formats
- Instancing: 1024 instances + VAO
- Samplers: 12 samplers + anisotropic
- Sync: 16 syncs + waitSync
- Queries: 8 queries + nested scopes
- Transform Feedback: 4 TF buffers
- 18-20 try-catch blocks

### s194: The Octopus (integrated workflow)
- All 8 features in a single render pipeline:
  - TF captures geometry → integer texture
  - Instances read integer texture
  - Draw to renderbuffers (MRT)
  - Blit renderbuffers, readPixels
  - Upload to sampled textures
  - Sync between stages
  - Queries measure each stage
- 19-21 try-catch blocks

### s195: The Octopus (stress test)
- Maximum complexity for each gap:
  - 16 renderbuffers
  - 32 pixel operations
  - 8 integer formats
  - 2048 instances
  - 16 samplers
  - 32 syncs
  - 16 queries
  - 8 TF buffers
- 20-22 try-catch blocks

**Coverage Contribution**: +5 to all 8 gaps

---

## Batch 40: Hypercomplex Kitchen Sink (5 seeds, s196-200)

**Focus**: Maximum complexity with all gaps + advanced features

### s196: Megamix Alpha
- Renderbuffers (16) + UBO + MRT (8)
- Pixel Ops (readPixels PBO async)
- Integer Textures (RGBA32I MRT)
- Instancing (1024 instances)
- Samplers (16 shadow samplers)
- Sync (32 fences)
- Queries (16 queries)
- Transform Feedback (8 buffers)
- 20-22 try-catch blocks

### s197: Megamix Beta
- All 8 gaps + 3D textures + Texture arrays
- Complex state machine with feedback loops
- Layered rendering + instancing
- Multiple sync barriers
- Query result propagation
- 21-23 try-catch blocks

### s198: Megamix Gamma
- All 8 gaps + Depth/Stencil (two-sided)
- All 8 gaps + Blending (per-target)
- Complex FBO ping-pong
- Renderbuffer resolves
- Integer/float format mixing
- 22-24 try-catch blocks

### s199: Megamix Delta
- All 8 gaps + All extensions
- EXT_color_buffer_float
- EXT_texture_filter_anisotropic
- WEBGL_compressed_texture_s3tc
- Maximum API diversity
- 23-25 try-catch blocks

### s200: The Final Boss (Hypercomplex)
- Every gap feature maxed out
- Every advanced feature (UBO, TF, MRT, VAO, etc.)
- Every extension enabled
- 100+ amplification variables
- 25-30 try-catch blocks
- Complexity score target: 800+
- "The ultimate fuzzing seed"

**Coverage Contribution**: +5 to all gaps + baseline maintenance

---

## Coverage Impact Projection

### Before Round 4 (150 seeds)
- Renderbuffers: 2% (4 seeds)
- Pixel Operations: 5% (8 seeds)
- Integer Textures: 8% (13 seeds)
- Instanced Rendering: 10% (15 seeds)
- Sampler Objects: 10% (16 seeds)
- Sync Objects: 11% (17 seeds)
- Query Objects: 12% (19 seeds)
- Transform Feedback: 15% (23 seeds)

### After Round 4 (200 seeds - Projected)
- Renderbuffers: 20% (40 seeds) → +900% improvement ✅
- Pixel Operations: 17% (34 seeds) → +213% improvement ✅
- Integer Textures: 16% (33 seeds) → +154% improvement ✅
- Instanced Rendering: 17% (34 seeds) → +127% improvement ✅
- Sampler Objects: 17% (34 seeds) → +113% improvement ✅
- Sync Objects: 17% (34 seeds) → +100% improvement ✅
- Query Objects: 17% (34 seeds) → +79% improvement ✅
- Transform Feedback: 19% (38 seeds) → +65% improvement ✅

**All 8 gaps brought to ~17-20% coverage threshold!**

---

## Mutation-Fuzzing Optimization

All seeds maintain mutation-optimized architecture:

### Three-Zone Structure
- **Declaration Zone**: 10-20 amplification variables per seed
- **Setup Zone**: Resource creation with redundancy
- **Execution Zone**: State thrashing + exotic mixes

### Variable Tiers
- **Tier 1**: 10-20 amplification variables (unusual parameters)
- **Tier 2**: 30-50 inline literals (hot spots)
- **Tier 3**: 8-15 enum constants

### Line Repetition Patterns
- Renderbuffer storage reallocation
- Pixel operation parameter cycling
- Sampler binding churn
- Sync object creation/deletion loops
- Query availability polling spam
- Transform feedback buffer swapping

### Error Path Exploitation
- 13-30 try-catch blocks per seed
- Exotic feature combinations (natural error sources)
- UAF patterns (delete-then-use)
- Format mismatches
- Invalid synchronization patterns

---

## Technical Notes

### Exotic Combinations Rationale

**Why these mixes?**
1. **Renderbuffers + Integer Textures**: Forces drivers to handle MSAA resolve with integer formats (rare code path)
2. **Pixel Operations + Instancing**: Stresses pixel transfer + vertex processing simultaneously
3. **Samplers + Sync**: Tests texture cache coherency with explicit synchronization
4. **Queries + Transform Feedback**: Stresses GPU counter subsystems
5. **3-way and 8-way mixes**: Maximum subsystem interaction

**Fuzzing Value**: These combinations are rarely tested by application developers, making them high-value targets for finding driver bugs.

### Complexity Targets

- Batch 31-36 (Focused): 8-14 try-catch blocks, 150-220 lines
- Batch 37-38 (Triple): 13-16 try-catch blocks, 200-280 lines
- Batch 39 (Octopus): 15-22 try-catch blocks, 250-350 lines
- Batch 40 (Megamix): 20-30 try-catch blocks, 300-450 lines

**Average**: ~220 lines/seed (vs 197 current average)

---

## Success Criteria

1. ✅ 50 new seeds created (s151-s200)
2. ✅ All seeds pass validation (100% success rate target)
3. ✅ All 8 gaps improved by at least 60%
4. ✅ Renderbuffers reach 20% threshold
5. ✅ No JavaScript errors
6. ✅ No WebGL errors (except intentional error paths)
7. ✅ Console logs stripped for production
8. ✅ Complexity scores 200-800+ range
9. ✅ All seeds under 6 seconds execution time
10. ✅ Documented and committed to repository

---

## Implementation Strategy

### Phase 1: Analysis (Complete)
- ✅ Generate detailed corpus analysis
- ✅ Identify 8 priority gaps
- ✅ Create enhancement plan (this document)

### Phase 2: Parallel Generation
- Launch 10 parallel agents (batches 31-40)
- Each agent creates 5 seeds following this plan
- Target: ~40 minutes for 50 seeds

### Phase 3: Validation
- Run validate_new_seeds.sh on all 50 seeds
- Verify 100% pass rate
- Check for any unsupported extensions

### Phase 4: Production Preparation
- Strip console.log from all catch blocks
- Verify mutation-friendly structure
- Confirm complexity scores

### Phase 5: Documentation
- Generate updated detailed analysis
- Compare before/after metrics
- Create Round 4 completion summary
- Commit and push to repository

---

## Workflow Integration

This plan follows the established iterative workflow:

```bash
# This plan will be executed by parallel agents
# Each agent will receive their batch specification (31-40)
# Seeds will be created as: mutation_b{batch}_s{seed}_descriptor.html
```

**Naming Convention**:
- `mutation_b31_s151_renderbuffer_multisample.html`
- `mutation_b32_s156_readpixels_formats.html`
- `mutation_b39_s195_octopus_stress.html`
- `mutation_b40_s200_final_boss.html`

---

**Plan Ready for Execution**: Round 4 targeting exotic gap combinations!
