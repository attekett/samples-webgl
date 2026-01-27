# Iterative Corpus Expansion Workflow Package

**Version**: 1.0.0
**Date**: 2026-01-27
**Purpose**: Complete workflow for iterative WebGL fuzzing corpus expansion

---

## Overview

This package contains all tools and documentation needed to iteratively expand a WebGL fuzzing corpus based on feature coverage analysis. The workflow is fully reproducible and can be applied to any WebGL seed corpus.

**Key Features**:
- Automated corpus statistics generation
- Feature coverage matrix analysis
- Gap identification and planning tools
- Validation and testing scripts
- Production preparation automation
- Git workflow integration

---

## Package Contents

```
workflow_package/
├── README.md                                    # This file
├── ITERATIVE_CORPUS_EXPANSION_WORKFLOW.md      # Complete workflow guide
├── RADAMSA_INTEGRATION_GUIDE.md                # Fuzzing guide
├── scripts/
│   ├── analyze_corpus.sh                       # Generate corpus statistics
│   ├── feature_matrix.sh                       # Feature coverage matrix
│   ├── calculate_gap_seeds.sh                  # Calculate seeds needed per category
│   ├── validate_new_seeds.sh                   # Validate new seeds
│   ├── analyze_failures.sh                     # Analyze test failures
│   ├── strip_console_logs.sh                   # Production preparation
│   └── iterative_expansion.sh                  # Complete automated workflow
├── templates/
│   └── enhancement_plan_template.md            # Enhancement plan template
└── examples/
    └── [Example files added during installation]
```

---

## Installation

### Quick Start

```bash
# Copy entire package to your project
cp -r workflow_package /path/to/your/project/

# Make scripts executable
chmod +x /path/to/your/project/workflow_package/scripts/*.sh

# Verify installation
cd /path/to/your/project
./workflow_package/scripts/analyze_corpus.sh
```

### Directory Structure Requirements

Your project should have:
```
your-project/
├── agent_outputs/          # Seed files (mutation_b*.html)
├── docs/                   # Documentation
│   └── plans/              # Enhancement plans
├── run_tests.sh            # Test runner script
└── workflow_package/       # This package
```

---

## Quick Usage Guide

### 1. Generate Corpus Statistics

```bash
# Full analysis
./workflow_package/scripts/analyze_corpus.sh > corpus_stats.txt
./workflow_package/scripts/feature_matrix.sh >> corpus_stats.txt

# View results
cat corpus_stats.txt
```

### 2. Identify Coverage Gaps

```bash
# Calculate needed seeds per category
./workflow_package/scripts/calculate_gap_seeds.sh 25

# Example output:
#   UBO:                          Current: 16% (8/50) → Need: 12 more seeds
#   Transform Feedback:           Current:  8% (4/50) → Need: 11 more seeds
```

### 3. Create Enhancement Plan

```bash
# Copy template
cp workflow_package/templates/enhancement_plan_template.md \
   docs/plans/$(date +%Y-%m-%d)-enhancement-round-1.md

# Edit plan with your specifications
vim docs/plans/$(date +%Y-%m-%d)-enhancement-round-1.md
```

### 4. Run Complete Workflow

```bash
# Automated workflow (interactive)
./workflow_package/scripts/iterative_expansion.sh 1 25

# Arguments:
#   1 = Round number
#   25 = Number of new seeds to add
```

---

## Detailed Workflow Steps

### Phase 1: Generate Feature Matrix

```bash
./workflow_package/scripts/analyze_corpus.sh > stats.txt
./workflow_package/scripts/feature_matrix.sh >> stats.txt
```

**Output Includes**:
- File size metrics
- Try-catch block analysis
- Mutation pattern frequency
- Feature coverage matrix (16 categories)

### Phase 2: Identify Gaps

```bash
# Calculate gaps
./workflow_package/scripts/calculate_gap_seeds.sh 25

# Review coverage matrix
grep "%" stats.txt | awk -F'|' '{print $2, $4}' | sort -t'%' -k1 -n
```

### Phase 3: Create Enhancement Plan

Use the template at `templates/enhancement_plan_template.md` to specify:
- Target features for each new seed
- Amplification variables
- Enum constants
- Line repetition patterns
- Try-catch block counts

### Phase 4: Parallel Generation

Launch multiple AI agents (or developers) with:
- Enhancement plan specifications
- Mutation-fuzzing design document
- Project coding rules

Each agent creates 5 seeds for their assigned batch.

### Phase 5: Validation

```bash
# Validate specific batches
./workflow_package/scripts/validate_new_seeds.sh 11 15

# Analyze any failures
./workflow_package/scripts/analyze_failures.sh
```

### Phase 6: Fix and Finalize

```bash
# Fix failures (manual)
# ... fix code ...

# Strip console logs for production
./workflow_package/scripts/strip_console_logs.sh 11 15

# Re-validate
./workflow_package/scripts/validate_new_seeds.sh 11 15
```

### Phase 7: Commit

```bash
# Stage changes
git add agent_outputs/mutation_b*.html docs/

# Commit with statistics
git commit -m "feat: add 25 enhancement seeds (Round 1)"

# Push
git push origin master
```

---

## Script Reference

### analyze_corpus.sh

Generates comprehensive corpus statistics:
- File count, lines, size
- Try-catch block counts
- Amplification variable counts
- Inline literal counts
- WebGL API call density
- Mutation pattern frequency

**Usage**: `./scripts/analyze_corpus.sh > output.txt`

### feature_matrix.sh

Generates feature coverage matrix for 16 WebGL2 categories:
- Buffer Operations, UBO, Transform Feedback
- Textures (2D, 3D, Arrays)
- Framebuffers, MRT
- VAO, Instancing
- Sync, Query, Sampler objects
- Integer textures, Depth/Stencil, Blending

**Usage**: `./scripts/feature_matrix.sh >> output.txt`

### calculate_gap_seeds.sh

Calculates how many seeds needed per category to reach target coverage.

**Usage**: `./scripts/calculate_gap_seeds.sh [num_seeds_to_add]`

**Example**: `./scripts/calculate_gap_seeds.sh 25`

### validate_new_seeds.sh

Validates new seeds using run_tests.sh and reports pass/fail summary.

**Usage**: `./scripts/validate_new_seeds.sh [batch_start] [batch_end]`

**Example**: `./scripts/validate_new_seeds.sh 11 15`

### analyze_failures.sh

Analyzes failed tests and extracts error messages from JSON results.

**Usage**: `./scripts/analyze_failures.sh`

### strip_console_logs.sh

Removes console.log statements from catch blocks for production fuzzing.

**Usage**: `./scripts/strip_console_logs.sh [batch_start] [batch_end]`

**Example**: `./scripts/strip_console_logs.sh 11 15`

### iterative_expansion.sh

Complete automated workflow integrating all phases.

**Usage**: `./scripts/iterative_expansion.sh [round_num] [num_seeds]`

**Example**: `./scripts/iterative_expansion.sh 1 25`

---

## Customization

### Adapting to Your Project

1. **Update file patterns**: If your seeds don't match `mutation_b*.html`, update glob patterns in scripts

2. **Modify coverage targets**: Change `TARGET_PCT` in `calculate_gap_seeds.sh` (default: 20%)

3. **Add custom categories**: Edit `feature_matrix.sh` to track additional WebGL features

4. **Adjust mutation patterns**: Modify `analyze_corpus.sh` to detect your specific patterns

### Example: Custom Feature Detection

```bash
# Edit feature_matrix.sh
# Add new category:

compute_count=$(grep -l 'dispatchCompute\|bindImageTexture' agent_outputs/mutation_b*.html 2>/dev/null | wc -l)
echo "| Compute Shaders | $compute_count/$total | $((compute_count*100/total))% |"
```

---

## Troubleshooting

### Script Permission Denied

```bash
chmod +x workflow_package/scripts/*.sh
```

### "Command not found: run_tests.sh"

Ensure you're running scripts from project root directory where `run_tests.sh` exists.

### Scripts Not Finding Seed Files

Check that seed files are in `agent_outputs/` directory matching pattern `mutation_b*.html`.

### Feature Matrix Shows 0% Coverage

Verify grep patterns match your seed file structure. Update patterns in `feature_matrix.sh`.

---

## Integration with Radamsa

See `RADAMSA_INTEGRATION_GUIDE.md` for:
- Mutation strategies optimized for corpus
- Fuzzing workflows (single-seed, multi-seed, parallel)
- Crash detection and triaging
- Production-ready fuzzing harness
- Continuous fuzzing automation

---

## Version History

**v1.0.0** (2026-01-27)
- Initial release
- Complete 7-phase workflow
- 7 automation scripts
- Enhancement plan template
- Radamsa integration guide

---

## License

This workflow package is provided as-is for WebGL fuzzing corpus development.

---

## Support

For issues or questions:
1. Review `ITERATIVE_CORPUS_EXPANSION_WORKFLOW.md` for detailed explanations
2. Check script comments for usage details
3. Refer to original project documentation

---

## Credits

**Developed by**: Anthropic Claude Sonnet 4.5
**Original Project**: WebGL2 Mutation-Based Fuzzing Corpus
**Workflow Design Date**: 2026-01-27

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
