# Feature Combination Matrix Tool - Design Document

**Date**: 2026-01-28
**Author**: Claude Sonnet 4.5
**Status**: Design Complete, Ready for Implementation

---

## Problem Statement

Mutation-based fuzzers (e.g., Radamsa) operate within single seed files rather than performing cross-seed mutations. To maximize fuzzing effectiveness, we must ensure the corpus contains maximal variety of feature combinations within individual seeds.

Current gap: We track single-feature coverage (e.g., "18% of seeds use Renderbuffers") but lack visibility into feature combination coverage (e.g., "How many seeds combine Renderbuffers + Instancing?").

---

## Objectives

1. **Analyze** which feature combinations exist in the corpus
2. **Identify** missing or underrepresented combinations
3. **Generate actionable recommendations** for filling combination gaps
4. **Auto-generate enhancement plans** for new seed creation rounds

---

## Architecture Overview

### Tool Name
`feature_combination_matrix.py`

### Integration Point
- Extends existing analysis pipeline alongside `detailed_coverage_analysis.py`
- Uses same HTML parsing infrastructure (BeautifulSoup4)
- Reuses feature detection patterns from current codebase

### Input Parameters
```bash
python3 workflow_package/scripts/feature_combination_matrix.py \
  --corpus-dir agent_outputs \
  --depth 2 \
  --min-threshold 5 \
  --output-matrix /tmp/combo_matrix.csv \
  --output-gaps /tmp/combo_gaps.md \
  --output-plan /tmp/round_N_plan.md \
  --heatmap /tmp/combo_heatmap.png
```

**Parameters:**
- `--corpus-dir`: Seed directory to analyze (default: `agent_outputs/`)
- `--depth`: Combination depth (2-way, 3-way, 4-way; default: 2)
- `--min-threshold`: Minimum seeds for "covered" status (default: 5)
- `--output-matrix`: CSV matrix output path
- `--output-gaps`: Markdown gap report path
- `--output-plan`: Auto-generated enhancement plan path (optional)
- `--heatmap`: PNG heatmap visualization path (optional)

### Output Artifacts

1. **Combination Matrix CSV** (`combination_matrix.csv`)
   - N×N grid showing seed counts for each feature pair
   - Symmetric matrix (combination order doesn't matter)
   - Diagonal = single-feature coverage

2. **Gap Report Markdown** (`combination_gaps.md`)
   - Executive summary with statistics
   - Critical gaps (priority >80) with seed specifications
   - Underrepresented combinations (<threshold)
   - Reference seed finder for each gap

3. **Enhancement Plan Markdown** (`round_N_plan.md`)
   - Auto-generated batch structure
   - Seed specifications per batch
   - Target complexity metrics
   - Estimated corpus impact

4. **Heatmap Visualization** (optional, `combo_heatmap.png`)
   - Color-coded matrix: Red (0 seeds), Yellow (1-4), Green (5+)
   - Requires matplotlib

---

## Feature Detection

### Feature Categories (18 total)
Reuse existing regex patterns from `detailed_coverage_analysis.py`:

1. 3D Textures
2. Blending
3. Buffer Operations
4. Depth/Stencil Operations
5. Framebuffer Objects
6. Instanced Rendering
7. Integer Textures
8. Multiple Render Targets (MRT)
9. Pixel Operations
10. Query Objects
11. Renderbuffers
12. Sampler Objects
13. Sync Objects
14. Texture Arrays
15. Texture Operations
16. Transform Feedback
17. Uniform Buffer Objects (UBO)
18. Vertex Array Objects (VAO)

### Feature Vector Extraction
```python
def extract_features(html_content: str) -> Set[str]:
    """
    Parse HTML seed file and extract feature presence.
    Returns set of feature names detected in the seed.

    Example: {"Renderbuffers", "Pixel Operations", "MRT"}
    """
```

Each seed gets a feature vector indicating presence/absence of each category.

---

## Combination Analysis

### 2-Way Combinations

**Generation:**
- For each seed, generate all pairs from its feature set
- Example: Seed with `[Renderbuffers, MRT, Queries]` → 3 pairs:
  - (Renderbuffers, MRT)
  - (Renderbuffers, Queries)
  - (MRT, Queries)

**Storage:**
```python
combination_matrix = {
    ("Renderbuffers", "Instancing"): 2,  # 2 seeds have both
    ("Integer Textures", "Sync Objects"): 1,
    ("Renderbuffers", "Pixel Operations"): 5,
    # ...
}
```

**Matrix Properties:**
- Symmetric: `(A, B) == (B, A)`
- Size: 18×18 = 324 cells (153 unique pairs above diagonal)
- Complexity: O(n × f²) where n=seeds, f=features

### 3-Way Combinations

**Generation:**
- Generate all triples from each seed's feature set
- Example: Seed with `[RBO, MRT, Queries]` → 1 triple

**Storage:**
- List format (too large for matrix visualization)
- Total possible: C(18,3) = 816 triples

**Use Case:**
- Finding missing "triads" for exotic combinations
- Optional, only computed when `--depth 3` specified

### 4-Way Combinations

**Generation:**
- Generate all 4-tuples from each seed's feature set
- Total possible: C(18,4) = 3,060 combinations

**Performance:**
- ~20 seconds for 225 seeds
- Optional, only computed when `--depth 4` specified

---

## Priority Ranking Algorithm

### Formula
```python
priority_score = (feature1_gap + feature2_gap) * rarity_multiplier
```

**Components:**

1. **Feature Gap** (`feature_gap`)
   - How far below 20% threshold each feature is
   - Example: Renderbuffers at 17% → gap = 3%
   - Features above 20% have gap = 0

2. **Rarity Multiplier** (`rarity_multiplier`)
   - Inverse of seed count
   - 0 seeds → multiplier = 100 (maximum priority)
   - 1 seed → multiplier = 50
   - 2 seeds → multiplier = 25
   - 5+ seeds → multiplier = 10

3. **Priority Score**
   - Range: 0-200
   - >80 = CRITICAL (missing combo of underrepresented features)
   - 40-80 = HIGH (missing combo, at least one feature underrepresented)
   - 20-40 = MEDIUM (underrepresented combo)
   - <20 = LOW (well-covered features)

### Example Calculations

**Critical Priority:**
- Renderbuffers (17%, gap=3%) + Instancing (18%, gap=2%) + 0 seeds
- Priority = (3 + 2) × 100 = 500 → CRITICAL

**Low Priority:**
- Buffer Ops (94%, gap=0%) + Texture Ops (62%, gap=0%) + 0 seeds
- Priority = (0 + 0) × 100 = 0 → LOW (both well-covered)

**Medium Priority:**
- Samplers (18%, gap=2%) + MRT (27%, gap=0%) + 3 seeds
- Priority = (2 + 0) × 16 = 32 → MEDIUM

---

## Data Structures

### Internal Representation

```python
# Per-seed feature presence
seed_features: Dict[str, Set[str]] = {
    "mutation_b41_s201.html": {"Renderbuffers", "Pixel Operations", "FBO"},
    "mutation_b42_s206.html": {"Integer Textures", "Instancing", "MRT"},
    # ...
}

# 2-way combination matrix
combination_matrix: Dict[Tuple[str, str], int] = {
    ("Renderbuffers", "Instancing"): 2,
    ("Integer Textures", "Sync Objects"): 1,
    # ...
}

# Feature coverage percentages
feature_coverage: Dict[str, float] = {
    "Renderbuffers": 17.3,
    "Instancing": 18.2,
    # ...
}

# Missing/underrepresented combinations (priority sorted)
gaps: List[Dict] = [
    {
        "combo": ("Renderbuffers", "Instancing"),
        "count": 0,
        "priority": 95.5,
        "features": [
            {"name": "Renderbuffers", "coverage": 17.3, "gap": 2.7},
            {"name": "Instancing", "coverage": 18.2, "gap": 1.8}
        ],
        "reason": "Both features below 20% threshold"
    },
    # ...
]
```

---

## Output Formats

### 1. Combination Matrix CSV

```csv
Feature,3D Textures,Blending,Buffer Operations,Depth/Stencil Ops,Framebuffer Objects,Instanced Rendering,Integer Textures,MRT,Pixel Operations,Query Objects,Renderbuffers,Sampler Objects,Sync Objects,Texture Arrays,Texture Operations,Transform Feedback,UBO,VAO
3D Textures,50,12,45,18,35,8,14,22,9,15,7,11,10,28,42,17,19,15
Blending,12,55,48,25,30,6,9,27,11,14,8,10,12,16,45,13,18,20
Buffer Operations,45,48,212,65,107,41,41,58,42,44,39,41,42,46,131,47,48,77
Depth/Stencil Ops,18,25,65,66,45,12,11,28,15,18,10,14,13,19,47,16,22,25
Framebuffer Objects,35,30,107,45,118,18,20,60,25,30,28,22,24,32,100,28,35,42
Instanced Rendering,8,6,41,12,18,41,5,15,7,12,2,8,9,14,30,18,16,22
Integer Textures,14,9,41,11,20,5,41,18,8,12,6,9,10,16,35,14,15,18
MRT,22,27,58,28,60,15,18,61,20,25,18,20,22,26,55,22,28,32
Pixel Operations,9,11,42,15,25,7,8,20,42,14,12,10,11,15,38,13,16,18
Query Objects,15,14,44,18,30,12,12,25,14,44,11,14,15,18,40,20,18,22
Renderbuffers,7,8,39,10,28,2,6,18,12,11,39,8,9,12,35,10,12,15
Sampler Objects,11,10,41,14,22,8,9,20,10,14,8,41,15,16,38,16,18,20
Sync Objects,10,12,42,13,24,9,10,22,11,15,9,15,42,17,40,18,19,21
Texture Arrays,28,16,46,19,32,14,16,26,15,18,12,16,17,46,46,20,22,24
Texture Operations,42,45,131,47,100,30,35,55,38,40,35,38,40,46,140,42,45,65
Transform Feedback,17,13,47,16,28,18,14,22,13,20,10,16,18,20,42,47,24,28
UBO,19,18,48,22,35,16,15,28,16,18,12,18,19,22,45,24,48,30
VAO,15,20,77,25,42,22,18,32,18,22,15,20,21,24,65,28,30,77
```

### 2. Gap Report Markdown

```markdown
# Feature Combination Gap Analysis

**Corpus**: 225 seeds
**Analysis Date**: 2026-01-28
**Combination Depth**: 2-way
**Coverage Threshold**: 5 seeds

---

## Executive Summary

- **Total 2-way combinations possible**: 153 (18×17/2)
- **Missing combinations (0 seeds)**: 12
- **Underrepresented (<5 seeds)**: 28
- **Well-covered (≥5 seeds)**: 113
- **Average seeds per combination**: 18.4

### Coverage Distribution
- CRITICAL gaps (priority >80): 4 combinations
- HIGH gaps (priority 40-80): 8 combinations
- MEDIUM gaps (priority 20-40): 16 combinations
- LOW priority: 125 combinations

---

## Critical Gaps (Priority Score >80)

### 1. Renderbuffers + Instancing (Priority: 95.5) ⚠️

**Current Status:**
- Seeds with combination: 0
- Renderbuffers coverage: 17.3% (39/225 seeds, gap: 2.7%)
- Instancing coverage: 18.2% (41/225 seeds, gap: 1.8%)

**Seed Specification:**
- **Target**: Create 3-5 seeds
- **Core pattern**: Renderbuffer MRT + drawArraysInstanced/drawElementsInstanced
- **Suggested variations**:
  * RBO MSAA resolve + 1024 instances with per-instance attributes
  * RBO integer formats (R32I, RGBA8UI) + instanced MRT rendering
  * RBO depth attachment + instanced occlusion queries
- **Complexity targets**: 12-15 try-catch blocks per seed
- **Estimated lines**: 180-240 per seed

**Reference Seeds (Templates):**
- `mutation_b42_s206_integer_instancing_extreme.html` - Has Instancing (2048 instances)
- `mutation_b41_s201_renderbuffer_readpixels_mega.html` - Has Renderbuffers (8 RBOs)
- `mutation_b37_s185_rbo_mrt_read_samplers.html` - Has Renderbuffers + MRT
- **Merge pattern**: Take RBO MRT setup from s185 + instancing loop from s206

---

### 2. Integer Textures + Sync Objects (Priority: 87.2) ⚠️

**Current Status:**
- Seeds with combination: 1
- Integer Textures coverage: 18.2% (41/225 seeds, gap: 1.8%)
- Sync Objects coverage: 18.7% (42/225 seeds, gap: 1.3%)

**Seed Specification:**
- **Target**: Create 2-4 seeds
- **Core pattern**: Integer texture uploads + fence sync polling
- **Suggested variations**:
  * R32I/RG32UI texture updates with fenceSync after each upload
  * Integer MRT rendering with sync before readPixels
  * 3D integer texture with per-slice sync objects (128 slices, 128 syncs)
- **Complexity targets**: 14-17 try-catch blocks per seed
- **Estimated lines**: 200-250 per seed

**Reference Seeds (Templates):**
- `mutation_b42_s206_integer_instancing_extreme.html` - Has Integer Textures (8 formats)
- `mutation_b43_s212_sampler_lod_sync_polling.html` - Has Sync (32 syncs, 512 polls)
- **Merge pattern**: Take integer MRT setup from s206 + sync polling from s212

---

### 3. Renderbuffers + Integer Textures (Priority: 84.8) ⚠️

**Current Status:**
- Seeds with combination: 6
- Renderbuffers coverage: 17.3% (39/225 seeds, gap: 2.7%)
- Integer Textures coverage: 18.2% (41/225 seeds, gap: 1.8%)

**Note**: Already has some coverage (6 seeds) but still below threshold (5+ seeds).

**Seed Specification:**
- **Target**: Create 2-3 additional seeds
- **Core pattern**: Integer renderbuffers with integer texture sampling
- **Suggested variations**:
  * R32I/RGBA8UI renderbuffers with blitFramebuffer to integer textures
  * Integer RBO MRT with integer texture sampling in fragment shader
- **Complexity targets**: 13-16 try-catch blocks per seed

**Reference Seeds (Templates):**
- `mutation_b33_s161_integer_renderbuffer_extreme.html` - Has both (existing combo)

---

### 4. Pixel Operations + Instancing (Priority: 82.1) ⚠️

**Current Status:**
- Seeds with combination: 7
- Pixel Operations coverage: 18.7% (42/225 seeds, gap: 1.3%)
- Instancing coverage: 18.2% (41/225 seeds, gap: 1.8%)

**Note**: Close to threshold but worth reinforcing.

**Seed Specification:**
- **Target**: Create 1-2 seeds
- **Core pattern**: Instanced rendering with per-instance readPixels
- **Suggested variations**:
  * 1024 instances with unique colors, readPixels validation per instance
  * Instanced MRT with readBuffer cycling + readPixels

**Reference Seeds (Templates):**
- `mutation_b34_s166_instanced_readback_extreme.html` - Has both (existing combo)

---

## High Priority Gaps (Priority Score 40-80)

### 5. Renderbuffers + Sampler Objects (Priority: 68.5)
- Current seeds: 8
- Recommended: +2 seeds
- Pattern: RBO textures with sampler objects for filtering

### 6. Renderbuffers + Sync Objects (Priority: 67.2)
- Current seeds: 9
- Recommended: +1-2 seeds
- Pattern: RBO blitFramebuffer + fence syncs

### 7. Instanced Rendering + Query Objects (Priority: 54.8)
- Current seeds: 12
- Recommended: +1 seed (already decent coverage)

### 8. Integer Textures + Sampler Objects (Priority: 52.3)
- Current seeds: 9
- Recommended: +1-2 seeds
- Pattern: Integer texture sampling with isampler2D/usampler2D

[... additional gaps omitted for brevity ...]

---

## Medium Priority Gaps (Priority Score 20-40)

These combinations have at least one well-covered feature but are still underrepresented:

- Renderbuffers + 3D Textures (7 seeds)
- Renderbuffers + Texture Arrays (12 seeds)
- Integer Textures + 3D Textures (14 seeds)
- [... 13 more combinations ...]

---

## Well-Covered Combinations (≥5 seeds)

113 combinations have adequate coverage. Highlights:

- Buffer Operations + Texture Operations: 131 seeds ✅
- Buffer Operations + Framebuffer Objects: 107 seeds ✅
- Texture Operations + Framebuffer Objects: 100 seeds ✅
- Buffer Operations + VAO: 77 seeds ✅

---

## Recommendations

### Immediate Action (Round 6 - Micro)
Create 10-15 seeds targeting the 4 critical gaps:
- 3-5 seeds: Renderbuffers + Instancing
- 2-4 seeds: Integer Textures + Sync Objects
- 2-3 seeds: Renderbuffers + Integer Textures (reinforce)
- 1-2 seeds: Pixel Operations + Instancing (reinforce)

**Expected Impact:**
- Eliminate all critical gaps (priority >80)
- Reduce high-priority gaps from 8 to 4
- Improve combination coverage: 113/153 → 120/153 (78% → 78.4%)

### Long-Term Strategy
- Maintain minimum 5 seeds per combination
- Monitor combination coverage after each round
- Use this tool to guide seed creation priorities
```

### 3. Auto-Generated Enhancement Plan

```markdown
# Round 6: Combination Gap Closure Enhancement Plan

**Date**: 2026-01-28
**Target**: Close critical combination gaps (priority >80)
**Strategy**: Focused 10-seed micro-round
**Corpus Growth**: 225 → 235 seeds

---

## Executive Summary

Round 6 targets 4 critical feature combination gaps identified by combination matrix analysis. Using focused seed specifications, we can eliminate all priority >80 gaps with just 10 seeds.

---

## Batch 46: Renderbuffers + Instancing (5 seeds, s226-230)

### s226: RBO MSAA Instanced Resolve
- 8 multisample renderbuffers (2x, 4x, 8x, 16x MSAA)
- 1024 instanced draws with per-instance colors
- Blit to single-sample RBOs
- Per-instance validation via readPixels
- 13-15 try-catch blocks

### s227: Integer RBO Instanced MRT
- 4 integer renderbuffers (R32I, RG32UI, RGBA8UI, RGBA16I)
- 2048 instances with per-instance integer attributes
- MRT rendering to integer RBOs
- clearBufferiv/clearBufferuiv patterns
- 14-16 try-catch blocks

### s228: RBO Depth Instanced Queries
- DEPTH32F renderbuffer attachment
- 1024 instanced draws with varying depth
- Occlusion query per instance batch (32 queries)
- Query availability polling
- 12-14 try-catch blocks

### s229: RBO Layered Instanced Array
- 8 renderbuffers with different formats
- Layered FBO attachments (gl_Layer in geometry shader)
- 512 instances distributed across 8 layers
- Per-layer blitting patterns
- 15-17 try-catch blocks

### s230: RBO Churn Instanced Stress
- 16 renderbuffers with rapid storage reallocation
- 2048 instances with FBO attachment cycling
- Storage format changes mid-render
- Renderbuffer deletion while attached (UAF)
- 16-18 try-catch blocks

**Coverage Contribution:**
- Renderbuffers: 39 → 44 seeds (19.6%)
- Instancing: 41 → 46 seeds (20.4%) ✅ CROSSED 20%
- Combination coverage: 0 → 5 seeds ✅

---

## Batch 47: Integer Textures + Sync Objects (3 seeds, s231-233)

### s231: Integer Texture Upload Sync
- 8 integer texture formats (R8I, R16UI, R32I, RG32UI, RGBA8I, RGBA16UI, RGBA32I, RGBA32UI)
- PBO async uploads with fence sync per texture
- clientWaitSync polling (1024 iterations)
- Texture completeness validation
- 14-16 try-catch blocks

### s232: Integer MRT Sync Readback
- 4 integer MRT targets (R32I, RG32UI, RGBA8UI, RGBA16I)
- Fence sync after each draw call
- getSyncParameter extensive polling
- readPixels with sync synchronization
- 15-17 try-catch blocks

### s233: Integer 3D Texture Slice Sync
- R32I 3D texture (128×128×128)
- 128 fence syncs (one per slice)
- Per-slice texture updates with sync barriers
- waitSync (server-side) patterns
- SYNC_FLUSH_COMMANDS_BIT variations
- 16-18 try-catch blocks

**Coverage Contribution:**
- Integer Textures: 41 → 44 seeds (19.6%)
- Sync Objects: 42 → 45 seeds (20%) ✅ CROSSED 20%
- Combination coverage: 1 → 4 seeds ✅

---

## Batch 48: Reinforcement Seeds (2 seeds, s234-235)

### s234: RBO + Integer Texture Hybrid
- 8 integer renderbuffers (R32I, RGBA8UI variants)
- 8 integer texture samplers
- Render to integer RBO → blit to integer texture
- isampler2D/usampler2D in fragment shader
- 14-16 try-catch blocks

### s235: Pixel Ops + Instancing Validation
- 1024 instances with unique per-instance colors
- MRT rendering (4 targets)
- readBuffer cycling + readPixels per target
- PBO async readback with instanced validation
- 13-15 try-catch blocks

**Coverage Contribution:**
- Renderbuffers: 44 → 45 seeds (20%) ✅ CROSSED 20%
- Integer Textures: 44 → 45 seeds (20%) ✅ CROSSED 20%
- Pixel Operations: 42 → 43 seeds (19.1%)
- Instancing: 46 → 47 seeds (20.9%)

---

## Success Criteria

1. ✅ 10 new seeds created (s226-s235)
2. ✅ All seeds pass validation (100% success rate target)
3. ✅ 4 critical gaps eliminated (priority >80 → 0)
4. ✅ 3 features cross 20% threshold (RBO, Integer Tex, Sync, Instancing)
5. ✅ No JavaScript errors
6. ✅ No WebGL errors (except intentional error paths)
7. ✅ Console logs stripped for production
8. ✅ Complexity scores 180-350 range
9. ✅ All seeds under 6 seconds execution time
10. ✅ Documented and committed to repository
```

### 4. Heatmap Visualization (Optional)

Generated using matplotlib with color mapping:
- **Red (0 seeds)**: Critical gap
- **Orange (1-2 seeds)**: Severe gap
- **Yellow (3-4 seeds)**: Below threshold
- **Light Green (5-9 seeds)**: At threshold
- **Dark Green (10+ seeds)**: Well-covered

Features ordered by coverage percentage (lowest to highest) for visual clustering of gaps.

---

## Implementation Details

### Core Functions

```python
def extract_features(html_content: str) -> Set[str]:
    """
    Parse HTML seed file and extract feature presence.
    Reuses regex patterns from detailed_coverage_analysis.py.

    Returns:
        Set of feature names detected in the seed.
    """
    features = set()

    # Reuse existing patterns
    if re.search(r'texImage3D|texSubImage3D|texStorage3D', html_content):
        features.add('3D Textures')

    if re.search(r'drawArraysInstanced|drawElementsInstanced', html_content):
        features.add('Instanced Rendering')

    # ... (all 18 feature patterns)

    return features


def build_combination_matrix(
    seed_features: Dict[str, Set[str]],
    depth: int = 2
) -> Dict[Tuple[str, ...], int]:
    """
    Generate N-way combinations from seed feature sets.

    Args:
        seed_features: Dict mapping seed filename to set of features
        depth: Combination depth (2, 3, or 4)

    Returns:
        Dict mapping feature tuple to seed count
    """
    from itertools import combinations

    combo_matrix = {}

    for seed_name, features in seed_features.items():
        # Generate all N-way combinations from this seed's features
        for combo in combinations(sorted(features), depth):
            combo_matrix[combo] = combo_matrix.get(combo, 0) + 1

    return combo_matrix


def calculate_priority(
    combo: Tuple[str, ...],
    feature_coverage: Dict[str, float],
    seed_count: int,
    threshold: float = 20.0
) -> float:
    """
    Calculate priority score for a combination gap.

    Formula: priority = sum(feature_gaps) * rarity_multiplier

    Args:
        combo: Tuple of feature names
        feature_coverage: Dict mapping feature to coverage percentage
        seed_count: Number of seeds with this combination
        threshold: Coverage threshold (default 20%)

    Returns:
        Priority score (0-200+)
    """
    # Calculate total gap across all features in combination
    total_gap = 0.0
    for feature in combo:
        coverage = feature_coverage.get(feature, 0.0)
        if coverage < threshold:
            total_gap += (threshold - coverage)

    # Rarity multiplier based on seed count
    if seed_count == 0:
        rarity = 100
    elif seed_count == 1:
        rarity = 50
    elif seed_count == 2:
        rarity = 25
    elif seed_count <= 4:
        rarity = 15
    else:
        rarity = 10

    return total_gap * rarity


def find_reference_seeds(
    combo: Tuple[str, ...],
    seed_features: Dict[str, Set[str]]
) -> List[str]:
    """
    Find seeds containing any feature in the combo (potential templates).

    Args:
        combo: Tuple of feature names to search for
        seed_features: Dict mapping seed filename to set of features

    Returns:
        List of seed filenames containing at least one feature from combo
    """
    reference_seeds = []

    for seed_name, features in seed_features.items():
        # Check if seed has any feature from the combo
        if any(f in features for f in combo):
            # Count how many features match
            match_count = sum(1 for f in combo if f in features)
            reference_seeds.append((seed_name, match_count, features))

    # Sort by match count (seeds with more matching features first)
    reference_seeds.sort(key=lambda x: x[1], reverse=True)

    return reference_seeds


def generate_seed_specification(
    combo: Tuple[str, ...],
    references: List[Tuple[str, int, Set[str]]],
    priority: float
) -> str:
    """
    Create actionable seed specification for filling a combination gap.

    Args:
        combo: Feature combination to target
        references: Reference seeds (from find_reference_seeds)
        priority: Priority score

    Returns:
        Markdown string with seed specification
    """
    spec = f"### {' + '.join(combo)}\n\n"
    spec += f"**Priority**: {priority:.1f}\n\n"

    # Suggested seed count based on priority
    if priority > 80:
        seed_count = "3-5 seeds"
    elif priority > 40:
        seed_count = "2-3 seeds"
    else:
        seed_count = "1-2 seeds"

    spec += f"**Target**: Create {seed_count}\n\n"

    # Core pattern suggestion (hardcoded mappings for common combos)
    spec += "**Core pattern**: "
    spec += generate_pattern_suggestion(combo)
    spec += "\n\n"

    # Complexity targets
    spec += "**Complexity targets**: 12-17 try-catch blocks per seed\n"
    spec += "**Estimated lines**: 180-250 per seed\n\n"

    # Reference seeds
    if references:
        spec += "**Reference Seeds (Templates)**:\n"
        for seed_name, match_count, features in references[:3]:
            spec += f"- `{seed_name}` - Has {match_count}/{len(combo)} features\n"
        spec += "\n"

    return spec


def generate_batch_plan(
    gaps: List[Dict],
    seeds_per_batch: int = 5,
    start_batch: int = 46,
    start_seed: int = 226
) -> str:
    """
    Auto-generate Round N enhancement plan markdown from gaps.

    Args:
        gaps: List of gap dicts from combination analysis
        seeds_per_batch: Seeds per batch (default 5)
        start_batch: Starting batch number
        start_seed: Starting seed number

    Returns:
        Markdown string with complete enhancement plan
    """
    plan = f"# Round N: Combination Gap Closure Enhancement Plan\n\n"
    plan += f"**Generated**: {datetime.now().strftime('%Y-%m-%d')}\n"
    plan += f"**Strategy**: Close critical combination gaps\n\n"

    batch_num = start_batch
    seed_num = start_seed

    # Group gaps by priority tier
    critical_gaps = [g for g in gaps if g['priority'] > 80]

    for gap in critical_gaps:
        combo_name = '_'.join([f.lower().replace(' ', '_') for f in gap['combo']])

        plan += f"## Batch {batch_num}: {' + '.join(gap['combo'])}\n\n"

        # Generate seed specifications for this batch
        # (simplified - real implementation would be more detailed)
        for i in range(seeds_per_batch):
            plan += f"### s{seed_num}: {combo_name}_variant_{i+1}\n"
            plan += "- [Seed specification details]\n"
            plan += "- 12-15 try-catch blocks\n\n"
            seed_num += 1

        batch_num += 1

    return plan


def generate_heatmap(
    combination_matrix: Dict[Tuple[str, str], int],
    features: List[str],
    output_path: str
):
    """
    Generate heatmap visualization of combination matrix.

    Args:
        combination_matrix: 2-way combination counts
        features: List of feature names (ordered)
        output_path: PNG output file path
    """
    import matplotlib.pyplot as plt
    import numpy as np

    # Build NxN matrix
    n = len(features)
    matrix = np.zeros((n, n))

    for i, f1 in enumerate(features):
        for j, f2 in enumerate(features):
            if i == j:
                # Diagonal: single feature coverage (placeholder)
                matrix[i][j] = -1  # Special value for diagonal
            else:
                combo = tuple(sorted([f1, f2]))
                matrix[i][j] = combination_matrix.get(combo, 0)

    # Create heatmap
    fig, ax = plt.subplots(figsize=(14, 12))

    # Color map: red (0) -> yellow (4) -> green (10+)
    cmap = plt.cm.RdYlGn
    im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=15)

    # Labels
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(features, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(features, fontsize=8)

    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Seeds with combination', rotation=270, labelpad=20)

    # Title
    ax.set_title('Feature Combination Coverage Matrix', fontsize=14, pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
```

### Main Execution Flow

```python
def main():
    parser = argparse.ArgumentParser(
        description='Analyze feature combination coverage in WebGL corpus'
    )
    parser.add_argument('--corpus-dir', default='agent_outputs')
    parser.add_argument('--depth', type=int, default=2, choices=[2,3,4])
    parser.add_argument('--min-threshold', type=int, default=5)
    parser.add_argument('--output-matrix', required=True)
    parser.add_argument('--output-gaps', required=True)
    parser.add_argument('--output-plan')
    parser.add_argument('--heatmap')

    args = parser.parse_args()

    # 1. Parse corpus
    print(f"Analyzing {args.corpus_dir}...")
    seed_features = {}
    feature_coverage = {}

    for html_file in glob.glob(f"{args.corpus_dir}/*.html"):
        with open(html_file, 'r') as f:
            content = f.read()
            features = extract_features(content)
            seed_features[os.path.basename(html_file)] = features

    # 2. Calculate single-feature coverage
    total_seeds = len(seed_features)
    all_features = set()
    for features in seed_features.values():
        all_features.update(features)

    for feature in all_features:
        count = sum(1 for f in seed_features.values() if feature in f)
        feature_coverage[feature] = (count / total_seeds) * 100

    # 3. Build combination matrix
    combination_matrix = build_combination_matrix(seed_features, args.depth)

    # 4. Identify gaps
    gaps = []
    for combo, count in combination_matrix.items():
        if count < args.min_threshold:
            priority = calculate_priority(combo, feature_coverage, count)
            references = find_reference_seeds(combo, seed_features)

            gaps.append({
                'combo': combo,
                'count': count,
                'priority': priority,
                'references': references
            })

    gaps.sort(key=lambda x: x['priority'], reverse=True)

    # 5. Generate outputs
    write_matrix_csv(combination_matrix, all_features, args.output_matrix)
    write_gaps_markdown(gaps, feature_coverage, args.output_gaps)

    if args.output_plan:
        write_batch_plan(gaps, args.output_plan)

    if args.heatmap:
        generate_heatmap(combination_matrix, sorted(all_features), args.heatmap)

    print(f"Analysis complete!")
    print(f"- Matrix: {args.output_matrix}")
    print(f"- Gaps: {args.output_gaps}")
```

---

## Performance Characteristics

### Time Complexity

- **Feature extraction**: O(n × m) where n = seeds, m = file size
  - 225 seeds × ~200KB avg = ~450ms

- **2-way combinations**: O(n × f²) where f = features per seed
  - 225 seeds × 18² = ~73K operations = ~1 second

- **3-way combinations**: O(n × f³)
  - 225 seeds × 18³ = ~1.3M operations = ~5 seconds

- **4-way combinations**: O(n × f⁴)
  - 225 seeds × 18⁴ = ~23M operations = ~20 seconds

### Space Complexity

- **seed_features dict**: O(n × f) = 225 × 18 = ~4KB
- **2-way matrix**: O(f²) = 18² = 324 entries = ~10KB
- **3-way combinations**: O(f³) = 18³ = 5,832 entries = ~180KB
- **4-way combinations**: O(f⁴) = 18⁴ = 104,976 entries = ~3MB

**Memory efficient for corpus sizes up to 1000 seeds.**

---

## Workflow Integration

### Updated Corpus Expansion Workflow

```bash
# Step 1: After Round N completion, run detailed coverage analysis
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --corpus-dir agent_outputs \
  --output /tmp/round_N_coverage.md

# Step 2: NEW - Run combination analysis
python3 workflow_package/scripts/feature_combination_matrix.py \
  --corpus-dir agent_outputs \
  --depth 2 \
  --min-threshold 5 \
  --output-matrix /tmp/combo_matrix.csv \
  --output-gaps /tmp/combo_gaps.md \
  --output-plan /tmp/round_N+1_plan.md \
  --heatmap /tmp/combo_heatmap.png

# Step 3: Review gaps and decide on Round N+1 strategy
cat /tmp/combo_gaps.md

# Step 4: Use auto-generated plan as template
cp /tmp/round_N+1_plan.md docs/plans/2026-01-XX-enhancement-round-N+1.md
# Edit plan as needed

# Step 5: Execute Round N+1 using parallel agents
# (existing workflow continues)
```

### Documentation Updates

**Files to update:**

1. **`docs/ITERATIVE_CORPUS_EXPANSION_WORKFLOW.md`**
   - Add "Combination Analysis" step after coverage analysis
   - Document how to interpret gap reports
   - Link to combination matrix tool

2. **`workflow_package/README.md`**
   - Add `feature_combination_matrix.py` to tool listing
   - Include usage examples
   - Document output formats

3. **Enhancement plan templates**
   - Reference combination gap reports in planning phase
   - Include "combination targets" in batch specifications

---

## Success Metrics

### Tool Validation (Initial Run)

Run on current 225-seed corpus and verify:

1. **Matrix completeness**: All 153 2-way combinations accounted for
2. **Gap identification**: Correctly identifies known gaps (e.g., Renderbuffers + Instancing)
3. **Priority ranking**: Critical gaps align with feature coverage gaps
4. **Reference seeds**: Finds appropriate templates for each gap
5. **Performance**: Completes in <5 seconds for 2-way analysis

### Corpus Quality Metrics (Post-Round 6)

After using tool to guide Round 6:

1. **Gap closure**: Critical gaps (priority >80) eliminated
2. **Combination coverage**: Well-covered combinations (≥5 seeds) increases
3. **Feature synergy**: Features below 20% benefit most from combinations
4. **No regression**: Single-feature coverage maintained or improved

---

## Future Enhancements

### Phase 2 (Optional)

1. **Semantic depth scoring**
   - Parse shader code to verify features are deeply integrated
   - Distinguish superficial presence from meaningful interaction
   - Example: Seed has "renderbuffer" and "instancing" but they don't interact

2. **Mutation impact prediction**
   - Estimate how likely mutators are to preserve combination
   - Weight combinations by mutation resilience
   - Guide seed design for mutator-friendly patterns

3. **Temporal analysis**
   - Track combination coverage growth over rounds
   - Identify persistent gaps across multiple enhancement rounds
   - Flag combinations that are difficult to create

4. **WebGL API pairing analysis**
   - Beyond feature categories, analyze specific API call pairs
   - Example: "How many seeds use both `renderbufferStorage` and `drawArraysInstanced`?"
   - Finer-grained gap detection

---

## Deliverables

1. **`workflow_package/scripts/feature_combination_matrix.py`** (400-500 lines)
   - Complete implementation of all core functions
   - CLI argument parsing
   - Error handling and validation

2. **Updated documentation**
   - `docs/ITERATIVE_CORPUS_EXPANSION_WORKFLOW.md` (section added)
   - `workflow_package/README.md` (tool documentation)

3. **Integration test**
   - Run on current 225-seed corpus
   - Generate all output formats
   - Validate against known gaps

4. **Example outputs**
   - `example_combo_matrix.csv`
   - `example_combo_gaps.md`
   - `example_combo_heatmap.png`

---

## Implementation Timeline

**Estimated effort**: 3-4 hours

1. **Core implementation** (2 hours)
   - Feature extraction (reuse existing)
   - Combination matrix builder
   - Priority calculation
   - CSV/Markdown output

2. **Advanced features** (1 hour)
   - Reference seed finder
   - Seed specification generator
   - Batch plan auto-generation

3. **Testing & validation** (0.5 hours)
   - Run on 225-seed corpus
   - Verify gap identification
   - Check output formats

4. **Documentation** (0.5 hours)
   - Update workflow docs
   - Add usage examples
   - Create integration guide

---

## Conclusion

The Feature Combination Matrix tool fills a critical gap in corpus analysis by revealing which feature combinations exist (or are missing) within individual seeds. Since mutation-based fuzzers cannot cross-pollinate features across seeds, maximizing intra-seed feature diversity is essential for comprehensive coverage.

By providing actionable gap reports, reference seed templates, and auto-generated enhancement plans, this tool streamlines the corpus expansion workflow and ensures systematic coverage of all feature combinations.

**Ready for implementation.**
