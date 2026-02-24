# Batch 14: Query + Sampler Objects - Mutation-Optimized Seeds

**Creation Date**: 2026-01-27
**Batch**: 14 (Query + Sampler Objects)
**Seed Count**: 5 seeds (s66-s70)
**Status**: ✅ All tests passed validation

## Seed Overview

### 1. mutation_b14_s66_query_occlusion_conservative.html
**Features**: ANY_SAMPLES_PASSED_CONSERVATIVE, multiple queries, occlusion testing
**Amplification Variables**:
- queryCount=8, drawCount=32, occluderCount=4
- vertexCount=6, primitiveCount=16

**Enum Constants**:
- queryTarget=0x8D6A, queryAvailable=0x8867, queryResult=0x8866
- triangleMode=0x0004

**Mutation Patterns**:
- Query creation redundancy (8 queries)
- Enable/disable thrashing (depth test, blend)
- Multiple draw calls with query wrapping
- Deletion and reuse patterns (query UAF)

**Try-Catch Blocks**: 9 blocks
**Validation**: ✅ Passed

---

### 2. mutation_b14_s67_query_primitives_generated.html
**Features**: PRIMITIVES_GENERATED, TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN, transform feedback integration
**Amplification Variables**:
- primitiveCount=256, queryCount=6, compareCount=16
- vertexCount=3, tfBufferSize=3072

**Enum Constants**:
- primitivesGenerated=0x8C87, tfPrimitivesWritten=0x8C88
- triangleMode=0x0004, tfBufferTarget=0x8C8E

**Mutation Patterns**:
- Transform feedback buffer creation redundancy
- Query/TF interleaving
- RASTERIZER_DISCARD thrashing
- Nested query operations
- Buffer bind ping-pong

**Try-Catch Blocks**: 10 blocks
**Validation**: ✅ Passed

---

### 3. mutation_b14_s68_sampler_all_parameters.html
**Features**: All sampler parameters (min/mag filter, wrap modes, LOD)
**Amplification Variables**:
- samplerCount=8, parameterCount=12, textureUnits=8
- texSize=256, texPixels=65536

**Enum Constants**:
- textureTarget=0x0DE1, minFilter=0x2801, magFilter=0x2800
- wrapS=0x2802, wrapT=0x2803, wrapR=0x8072

**Mutation Patterns**:
- Sampler creation redundancy (8 samplers)
- Parameter cycling through all filter modes
- Bind ping-pong across texture units
- Multiple textures with different sizes
- Deletion and reuse patterns

**Try-Catch Blocks**: 11 blocks
**Validation**: ✅ Passed

---

### 4. mutation_b14_s69_sampler_shadow_compare.html
**Features**: TEXTURE_COMPARE_MODE, shadow samplers, depth textures
**Amplification Variables**:
- samplerCount=6, depthTexCount=4, compareCount=8
- texSize=256, shadowMapSize=512

**Enum Constants**:
- textureTarget=0x0DE1, compareMode=0x884C, compareFunc=0x884D
- compareToTexture=0x884E, depthComponent=0x1902

**Mutation Patterns**:
- Depth texture format variations (DEPTH_COMPONENT24, 32F, 16)
- Sampler comparison mode cycling (LEQUAL, GEQUAL, LESS, GREATER, etc.)
- Shadow sampler binding patterns
- Multiple compare functions
- Deletion patterns

**Try-Catch Blocks**: 10 blocks
**Validation**: ✅ Passed (shader precision warnings expected)

---

### 5. mutation_b14_s70_sampler_anisotropic.html
**Features**: EXT_texture_filter_anisotropic, max anisotropy levels
**Extensions**: EXT_texture_filter_anisotropic
**Amplification Variables**:
- maxAniso=16, samplerCount=6, levelCount=8
- texSize=256, mipLevels=8

**Enum Constants**:
- textureTarget=0x0DE1, minFilter=0x2801, magFilter=0x2800
- wrapS=0x2802, wrapT=0x2803

**Mutation Patterns**:
- Anisotropy level cycling (1.0, 2.0, 4.0, 8.0, 16.0, max)
- Mipmap generation and sampling
- Sampler parameter thrashing
- Rotation-based texture access patterns
- Deletion patterns

**Try-Catch Blocks**: 9 blocks
**Validation**: ✅ Passed (EXT_texture_filter_anisotropic supported)

---

## Architecture Compliance

All seeds follow the three-zone architecture:

### Zone 1: Declaration Zone
- 5-8 Tier 1 amplification variables per seed ✓
- 4-6 Tier 3 enum constant variables per seed ✓
- Proper variable coupling for cascading mutations ✓

### Zone 2: Setup Zone
- 4-8 try-catch blocks for resource creation ✓
- Bind ping-pong patterns (2-4 per resource) ✓
- Resource creation redundancy ✓
- Mixed inline literals and variable references ✓

### Zone 3: Execution Zone
- 2-4 try-catch blocks for rendering/operations ✓
- Enable/disable state thrashing ✓
- Draw call patterns with state changes ✓
- Deletion and reuse patterns (UAF potential) ✓

## Mutation Characteristics

### Line Repetition Targets
- Query creation/deletion (8+ queries per seed)
- Sampler binding cycles (6-8 samplers)
- State enable/disable pairs
- Buffer/texture bind operations
- Parameter setting sequences

### Numeric Mutation Targets
- Query counts (6-8 per seed)
- Sampler counts (6-8 per seed)
- Texture dimensions (128, 256, 512, 1024)
- Draw counts (8-32 iterations)
- Anisotropy levels (1.0-16.0)

### Error Path Exploitation
- Deleted object reuse (queries, samplers)
- Active query conflicts (multiple beginQuery)
- Invalid parameter combinations
- Buffer overflow patterns
- State corruption accumulation

## Validation Summary

**Test Command**:
```bash
./run_tests.sh --test-file agent_outputs/mutation_b14_*.html --browsers firefox
```

**Results**:
- Total Seeds: 5
- Passed: 5 ✅
- Failed: 0
- JavaScript Errors: 0
- WebGL Errors: 0

**Expected Warnings** (mutation patterns):
- Query conflicts (beginQuery when active)
- Deleted object usage (UAF patterns)
- Shader precision (shadow samplers)
- Lazy texture initialization (mipmap generation)

## Coverage Contribution

**Batch 14 Coverage**:
- Query Objects: 2 → 4 seeds (+100% increase)
- Sampler Objects: 1 → 4 seeds (+300% increase)
- Transform Feedback + Queries: 1 new integrated seed
- Anisotropic Filtering: 1 new seed (extension-based)

**Total Corpus**: 70/100 seeds (70% complete)

## File Locations

All seeds created in: `/home/attekett/git/samples-webgl/agent_outputs/`

Files:
- mutation_b14_s66_query_occlusion_conservative.html (5.8 KB)
- mutation_b14_s67_query_primitives_generated.html (6.7 KB)
- mutation_b14_s68_sampler_all_parameters.html (9.2 KB)
- mutation_b14_s69_sampler_shadow_compare.html (9.8 KB)
- mutation_b14_s70_sampler_anisotropic.html (9.6 KB)

Screenshots: `agent_outputs/screenshots/mutation_b14_*_firefox.png`
JSON Reports: `agent_outputs/mutation_b14_*.json`

## Next Steps

1. **Production Phase**: Strip `console.log(e)` from all catch blocks
2. **Fuzzing Integration**: Feed seeds to radamsa for mutation-based fuzzing
3. **Batch 15**: Integer Textures (5 seeds: s71-s75)
4. **Batch 16**: 3D Textures + Texture Arrays (5 seeds: s76-s80)

## Notes

- All seeds use WebGL2 context (required)
- Canvas resolution: 256x256 (standard)
- Extension checking implemented correctly
- Try-catch blocks enable error path exploitation
- Console.log present for development validation
- No external dependencies or resources
- Self-contained HTML files ready for fuzzing
