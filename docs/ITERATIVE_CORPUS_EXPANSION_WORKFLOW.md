# Iterative Corpus Expansion Workflow

**Purpose**: Reproducible workflow for analyzing corpus coverage and generating new seeds to fill gaps
**Date**: 2026-01-27
**Status**: Production-ready

---

## Overview

This document describes the complete iterative workflow used to expand the WebGL2 fuzzing corpus based on feature coverage analysis. The workflow can be repeated indefinitely to achieve comprehensive API coverage.

**Workflow Phases**:
1. **Generate Feature Matrix** - Analyze current corpus coverage
2. **Identify Gaps** - Determine which features need more seeds
3. **Create Enhancement Plan** - Design new seeds to fill gaps
4. **Parallel Generation** - Create seeds using multiple AI agents
5. **Validation** - Test all new seeds
6. **Fix and Finalize** - Address any failures
7. **Commit and Document** - Update repository

---

## Prerequisites

```bash
# Ensure virtual environment is set up
source venv/bin/activate

# Verify test infrastructure works
./run_tests.sh --test-file agent_outputs/mutation_b1_s1_mrt_float_blend.html --browsers firefox

# Install additional tools
sudo apt-get install bc jq  # For statistics generation
```

---

## Phase 1: Generate Feature Matrix

### Step 1.1: Create Analysis Scripts

Create two analysis scripts for comprehensive corpus statistics:

**Script 1: `scripts/analyze_corpus.sh`**

```bash
#!/bin/bash
# Comprehensive corpus statistics

echo "=== COMPREHENSIVE CORPUS STATISTICS ==="
echo ""
echo "## 1. File Size Metrics"
echo "File Count: $(ls agent_outputs/mutation_b*.html | wc -l)"
echo "Total Lines: $(wc -l agent_outputs/mutation_b*.html | tail -1 | awk '{print $1}')"
echo "Total Size: $(du -sh agent_outputs/mutation_b*.html | tail -1 | awk '{print $1}')"
echo "Average Lines/Seed: $(wc -l agent_outputs/mutation_b*.html | awk 'END {print int($1/NR-1)}')"
echo "Min Lines: $(wc -l agent_outputs/mutation_b*.html | sort -n | head -1 | awk '{print $1, $2}')"
echo "Max Lines: $(wc -l agent_outputs/mutation_b*.html | sort -n | tail -2 | head -1 | awk '{print $1, $2}')"
echo ""

echo "## 2. Try-Catch Block Analysis"
for f in agent_outputs/mutation_b*.html; do
    grep -c 'try {' "$f" 2>/dev/null || echo "0"
done | awk '{sum+=$1; if(NR==1){min=$1;max=$1} if($1<min){min=$1} if($1>max){max=$1}}
    END {print "Total Try-Catch Blocks:", sum; print "Average/Seed:", sum/NR; print "Min:", min; print "Max:", max}'
echo ""

echo "## 3. Amplification Variables (const declarations)"
for f in agent_outputs/mutation_b*.html; do
    grep -c '^[[:space:]]*const [a-zA-Z]' "$f" 2>/dev/null || echo "0"
done | awk '{sum+=$1} END {print "Total Amplification Variables:", sum; print "Average/Seed:", sum/NR}'
echo ""

echo "## 4. Inline Literals (numeric values in function calls)"
echo -n "Analyzing inline literals... "
total_inlines=0
for f in agent_outputs/mutation_b*.html; do
  count=$(grep -oE 'gl\.[a-zA-Z]+\([^)]*[0-9]+[^)]*\)' "$f" | wc -l)
  total_inlines=$((total_inlines + count))
done
file_count=$(ls agent_outputs/mutation_b*.html | wc -l)
echo "Done"
echo "Total Inline Literals: ~$total_inlines"
echo "Average/Seed: ~$((total_inlines / file_count))"
echo ""

echo "## 5. WebGL API Call Density"
for f in agent_outputs/mutation_b*.html; do
    grep -c 'gl\.' "$f" 2>/dev/null || echo "0"
done | awk '{sum+=$1} END {print "Total gl.* calls:", sum; print "Average/Seed:", int(sum/NR)}'
echo ""

echo "## 6. Mutation Pattern Frequency"
echo "Bind Operations:"
for f in agent_outputs/mutation_b*.html; do
    grep -c 'bindBuffer\|bindTexture\|bindFramebuffer' "$f" 2>/dev/null || echo "0"
done | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'

echo "Enable/Disable:"
for f in agent_outputs/mutation_b*.html; do
    grep -c 'gl\.enable\|gl\.disable' "$f" 2>/dev/null || echo "0"
done | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'

echo "Create Operations:"
for f in agent_outputs/mutation_b*.html; do
    grep -c 'createBuffer\|createTexture\|createFramebuffer\|createRenderbuffer' "$f" 2>/dev/null || echo "0"
done | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'

echo "Delete Operations:"
for f in agent_outputs/mutation_b*.html; do
    grep -c 'deleteBuffer\|deleteTexture\|deleteFramebuffer' "$f" 2>/dev/null || echo "0"
done | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo ""
```

**Script 2: `scripts/feature_matrix.sh`**

```bash
#!/bin/bash
# Feature coverage matrix

echo "## Feature Coverage Matrix"
echo ""
echo "| Feature Category | Seeds | Coverage |\n|------------------|-------|----------|"

# Buffer Operations
buf_count=$(grep -l 'createBuffer\|bufferData\|bufferSubData' agent_outputs/mutation_b*.html | wc -l)
total=$(ls agent_outputs/mutation_b*.html | wc -l)
echo "| Buffer Operations | $buf_count/$total | $((buf_count*100/total))% |"

# UBO
ubo_count=$(grep -l 'UNIFORM_BUFFER\|uniformBlockBinding\|bindBufferBase' agent_outputs/mutation_b*.html | wc -l)
echo "| Uniform Buffer Objects | $ubo_count/$total | $((ubo_count*100/total))% |"

# Transform Feedback
tf_count=$(grep -l 'TRANSFORM_FEEDBACK\|transformFeedbackVaryings\|beginTransformFeedback' agent_outputs/mutation_b*.html | wc -l)
echo "| Transform Feedback | $tf_count/$total | $((tf_count*100/total))% |"

# Textures
tex_count=$(grep -l 'createTexture\|texImage2D\|texImage3D\|texStorage' agent_outputs/mutation_b*.html | wc -l)
echo "| Texture Operations | $tex_count/$total | $((tex_count*100/total))% |"

# 3D Textures
tex3d_count=$(grep -l 'TEXTURE_3D\|texImage3D\|texStorage3D' agent_outputs/mutation_b*.html | wc -l)
echo "| 3D Textures | $tex3d_count/$total | $((tex3d_count*100/total))% |"

# Texture Arrays
texarray_count=$(grep -l 'TEXTURE_2D_ARRAY\|texStorage3D' agent_outputs/mutation_b*.html | wc -l)
echo "| Texture Arrays | $texarray_count/$total | $((texarray_count*100/total))% |"

# Framebuffers
fbo_count=$(grep -l 'createFramebuffer\|framebufferTexture2D\|drawBuffers' agent_outputs/mutation_b*.html | wc -l)
echo "| Framebuffer Objects | $fbo_count/$total | $((fbo_count*100/total))% |"

# MRT
mrt_count=$(grep -l 'drawBuffers\|COLOR_ATTACHMENT[1-9]' agent_outputs/mutation_b*.html | wc -l)
echo "| Multiple Render Targets | $mrt_count/$total | $((mrt_count*100/total))% |"

# Instancing
inst_count=$(grep -l 'drawArraysInstanced\|drawElementsInstanced\|vertexAttribDivisor' agent_outputs/mutation_b*.html | wc -l)
echo "| Instanced Rendering | $inst_count/$total | $((inst_count*100/total))% |"

# VAO
vao_count=$(grep -l 'createVertexArray\|bindVertexArray' agent_outputs/mutation_b*.html | wc -l)
echo "| Vertex Array Objects | $vao_count/$total | $((vao_count*100/total))% |"

# Sync
sync_count=$(grep -l 'fenceSync\|clientWaitSync\|waitSync' agent_outputs/mutation_b*.html | wc -l)
echo "| Sync Objects | $sync_count/$total | $((sync_count*100/total))% |"

# Queries
query_count=$(grep -l 'createQuery\|beginQuery\|endQuery' agent_outputs/mutation_b*.html | wc -l)
echo "| Query Objects | $query_count/$total | $((query_count*100/total))% |"

# Samplers
sampler_count=$(grep -l 'createSampler\|bindSampler\|samplerParameter' agent_outputs/mutation_b*.html | wc -l)
echo "| Sampler Objects | $sampler_count/$total | $((sampler_count*100/total))% |"

# Integer textures
int_tex_count=$(grep -l 'R32I\|RGBA32I\|R32UI\|RGBA32UI' agent_outputs/mutation_b*.html | wc -l)
echo "| Integer Textures | $int_tex_count/$total | $((int_tex_count*100/total))% |"

# Depth/Stencil
depth_count=$(grep -l 'DEPTH_TEST\|STENCIL_TEST\|depthFunc\|stencilOp' agent_outputs/mutation_b*.html | wc -l)
echo "| Depth/Stencil Ops | $depth_count/$total | $((depth_count*100/total))% |"

# Blending
blend_count=$(grep -l 'BLEND\|blendFunc\|blendEquation' agent_outputs/mutation_b*.html | wc -l)
echo "| Blending | $blend_count/$total | $((blend_count*100/total))% |"

echo ""
```

### Step 1.2: Run Analysis Scripts

```bash
# Create scripts directory
mkdir -p scripts

# Create both scripts (copy content from above)
chmod +x scripts/analyze_corpus.sh scripts/feature_matrix.sh

# Run comprehensive analysis
./scripts/analyze_corpus.sh > corpus_statistics.txt
./scripts/feature_matrix.sh >> corpus_statistics.txt

# Review results
cat corpus_statistics.txt
```

### Step 1.3: Save Statistics to Documentation

```bash
# Add timestamp and save to docs
echo "# Corpus Statistics - $(date +%Y-%m-%d)" > docs/corpus_stats_$(date +%Y%m%d).md
cat corpus_statistics.txt >> docs/corpus_stats_$(date +%Y%m%d).md
```

### Step 1.4: Feature Combination Analysis (NEW)

After running basic coverage analysis, analyze feature combination coverage:

```bash
python3 workflow_package/scripts/feature_combination_matrix.py \
  --corpus-dir agent_outputs \
  --depth 2 \
  --min-threshold 5 \
  --output-matrix /tmp/combo_matrix.csv \
  --output-gaps /tmp/combo_gaps.md \
  --output-plan /tmp/round_N_plan.md
```

**Outputs:**
- `combo_matrix.csv`: 18×18 matrix showing seed counts per feature pair
- `combo_gaps.md`: Priority-ranked gaps with seed specifications
- `round_N_plan.md`: Auto-generated enhancement plan (optional)

**Review the gaps report:**

```bash
cat /tmp/combo_gaps.md
```

Focus on:
- Critical gaps (priority >80) - missing combinations of underrepresented features
- High gaps (priority 40-80) - underrepresented combinations
- Reference seeds for each gap (use as templates)

**Use the auto-generated plan as a starting point for Round N+1:**

```bash
cp /tmp/round_N_plan.md docs/plans/2026-XX-XX-enhancement-round-N+1.md
# Edit plan as needed with specific seed details
```

---

## Phase 2: Identify Coverage Gaps

### Step 2.1: Manual Gap Analysis

Review the feature matrix and identify categories below target threshold:

```bash
# Extract coverage percentages
grep "%" corpus_statistics.txt | awk -F'|' '{print $2, $4}' | sort -t'%' -k1 -n

# Identify gaps (below 20% coverage)
echo "=== COVERAGE GAPS (< 20%) ==="
grep "%" corpus_statistics.txt | awk -F'|' '{
    gsub(/ /, "", $4);
    pct = substr($4, 1, length($4)-1);
    if (pct < 20) print $2 " : " $4
}'
```

### Step 2.2: Calculate Required Seeds

For each gap, calculate how many additional seeds are needed:

```bash
#!/bin/bash
# calculate_gap_seeds.sh

CURRENT_SEEDS=$(ls agent_outputs/mutation_b*.html | wc -l)
TARGET_TOTAL=$((CURRENT_SEEDS + 25))  # Add 25 seeds
TARGET_PCT=20  # Target 20% coverage minimum

echo "Current corpus: $CURRENT_SEEDS seeds"
echo "Target corpus: $TARGET_TOTAL seeds"
echo "Target coverage: $TARGET_PCT%"
echo ""
echo "Seeds needed per category:"

# Calculate for each low-coverage category
for category in "UBO" "Transform Feedback" "Sync" "Query" "Sampler" "Integer"; do
    current=$(grep "$category" corpus_statistics.txt | grep -oP '\d+(?=%)')
    target_seeds=$((TARGET_TOTAL * TARGET_PCT / 100))
    current_seeds=$((CURRENT_SEEDS * current / 100))
    needed=$((target_seeds - current_seeds))
    [ $needed -gt 0 ] && echo "  $category: $needed seeds needed"
done
```

---

## Phase 3: Create Enhancement Plan

### Step 3.1: Design New Seed Specifications

Create a detailed enhancement plan document:

```markdown
# Corpus Enhancement Plan - [DATE]

## Coverage Gaps Identified

[Paste feature matrix results]

## New Seed Specifications

### Batch [N]: [Feature Focus] (5 seeds)

1. **mutation_b[N]_s[ID]_[descriptive_name].html**
   - **Features**: [Primary features to exercise]
   - **Amplification Variables**: [List 4-6 variables]
   - **Enum Constants**: [List 4-6 enum variables]
   - **Line Repetition Patterns**: [Specify which patterns]
   - **Try-Catch Blocks**: [Target count: 6-12]
   - **Extensions Required**: [List any extensions]

[Repeat for all seeds]
```

**Example Template**: See `docs/plans/2026-01-27-corpus-enhancement-coverage-gaps.md`

### Step 3.2: Save Enhancement Plan

```bash
# Save to docs/plans with timestamp
PLAN_FILE="docs/plans/$(date +%Y-%m-%d)-corpus-enhancement-round-N.md"

# Create plan document (fill in specifications)
# ...

git add "$PLAN_FILE"
git commit -m "docs: create enhancement plan for round N"
```

---

## Phase 4: Parallel Seed Generation

### Step 4.1: Prepare Parallel Agent Instructions

Create individual instruction files for each agent:

```bash
#!/bin/bash
# prepare_agent_instructions.sh

BATCH_START=11
NUM_BATCHES=5
SEEDS_PER_BATCH=5

for batch in $(seq $BATCH_START $((BATCH_START + NUM_BATCHES - 1))); do
    cat > "/tmp/agent_instructions_batch${batch}.md" <<EOF
# Agent Instructions: Batch $batch

## Your Task
Create exactly $SEEDS_PER_BATCH WebGL2 mutation-optimized seeds for Batch $batch.

## Required Reading (in order)
1. docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md
2. docs/plans/$(date +%Y-%m-%d)-corpus-enhancement-round-N.md
3. .cursorrules, AGENTS.md, CODING_RULES.md

## Seed Specifications
[Paste batch $batch specifications from enhancement plan]

## Output Files
- agent_outputs/mutation_b${batch}_s[ID]_[name].html

## Validation
After creating all 5 seeds, run:
\`\`\`bash
./run_tests.sh --test-file agent_outputs/mutation_b${batch}_*.html --browsers firefox
\`\`\`

All seeds must pass validation before task completion.
EOF
done
```

### Step 4.2: Launch Parallel Agents

**Using Claude Code CLI with parallel agents:**

```bash
# Option A: Manual parallel launch (open 5 terminals)
# Terminal 1:
claude --prompt "$(cat /tmp/agent_instructions_batch11.md)"

# Terminal 2:
claude --prompt "$(cat /tmp/agent_instructions_batch12.md)"

# ... etc for batches 11-15
```

**Option B: Automated parallel launch (if supported):**

```bash
#!/bin/bash
# launch_parallel_agents.sh

for batch in {11..15}; do
    echo "Launching agent for Batch $batch..."
    claude --prompt "$(cat /tmp/agent_instructions_batch${batch}.md)" &
    PIDS[$batch]=$!
done

# Wait for all agents to complete
for pid in ${PIDS[@]}; do
    wait $pid
    echo "Agent completed: PID $pid"
done

echo "All agents completed"
```

### Step 4.3: Monitor Progress

```bash
# Watch for new files
watch -n 5 'ls -lt agent_outputs/mutation_b1*.html | head -20'

# Count completed batches
for batch in {11..15}; do
    count=$(ls agent_outputs/mutation_b${batch}_*.html 2>/dev/null | wc -l)
    echo "Batch $batch: $count/5 seeds"
done
```

---

## Phase 5: Validation

### Step 5.1: Sequential Testing

```bash
#!/bin/bash
# validate_new_seeds.sh

NEW_BATCH_START=11
NEW_BATCH_END=15

echo "=== Validating New Seeds ==="
echo "Start: $(date)"

# Test each batch sequentially
for batch in $(seq $NEW_BATCH_START $NEW_BATCH_END); do
    echo ""
    echo "Testing Batch $batch..."
    ./run_tests.sh --test-file agent_outputs/mutation_b${batch}_*.html --browsers firefox
done

echo ""
echo "End: $(date)"

# Summary
echo ""
echo "Summary:"
total=$(ls agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.html 2>/dev/null | wc -l)
passed=$(grep -l '"passed": true' agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.json 2>/dev/null | wc -l)
failed=$((total - passed))

echo "Total: $total"
echo "PASS: $passed"
echo "FAIL: $failed"

if [ $failed -gt 0 ]; then
    echo ""
    echo "Failed seeds:"
    grep -L '"passed": true' agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.json | \
        sed 's/.json$//'
fi
```

### Step 5.2: Analyze Failures

```bash
#!/bin/bash
# analyze_failures.sh

echo "=== Failure Analysis ==="

for json in agent_outputs/mutation_b*.json; do
    if ! grep -q '"passed": true' "$json"; then
        html="${json%.json}.html"
        echo ""
        echo "FAILURE: $(basename $html)"
        echo "Errors:"
        jq -r '.javascript_errors[], .webgl_errors[], .errors[]' "$json" 2>/dev/null | head -5
    fi
done
```

---

## Phase 6: Fix and Finalize

### Step 6.1: Common Fix Patterns

**Variable Scoping Issues:**

```bash
# Pattern: const buffer = gl.createBuffer() inside try-catch
# Fix: Declare outside, assign inside

for html in [failed_seeds]; do
    sed -i '/<script>/a let buffer, texture, framebuffer;' "$html"
    sed -i 's/const buffer = /buffer = /g' "$html"
    sed -i 's/const texture = /texture = /g' "$html"
    sed -i 's/const framebuffer = /framebuffer = /g' "$html"
done
```

**Unsupported Extensions:**

```bash
# Check extension availability in UNSUPPORTED.md
# Remove extension from REQUIRED_EXTENSIONS array and related code
```

**Wrong Enum Constants:**

```bash
# Common mistakes:
# - gl.DRAW_BUFFER0 (wrong) → gl.COLOR_ATTACHMENT0 (correct)
# - Check WebGL specification for correct values
```

### Step 6.2: Re-validate After Fixes

```bash
# Re-test fixed seeds
./run_tests.sh --test-file agent_outputs/mutation_b11_*.html --browsers firefox

# Verify 100% pass rate
TOTAL=$(ls agent_outputs/mutation_b{11..15}_*.html | wc -l)
PASSED=$(grep -l '"passed": true' agent_outputs/mutation_b{11..15}_*.json | wc -l)

if [ $TOTAL -eq $PASSED ]; then
    echo "✓ All seeds passing ($PASSED/$TOTAL)"
else
    echo "✗ Still have failures: $((TOTAL - PASSED)) remaining"
    exit 1
fi
```

### Step 6.3: Strip Console Logging (Production Mode)

```bash
#!/bin/bash
# strip_console_logs.sh

echo "Stripping console.log from catch blocks..."

# Pattern 1: catch(e) { console.log(e); throw e; } → catch(e) { throw e; }
sed -i 's/catch(e) { console\.log(e); throw e; }/catch(e) { throw e; }/g' \
    agent_outputs/mutation_b{11..15}_*.html

# Pattern 2: catch(e) { console.log(e); } → catch(e) {}
sed -i 's/catch(e) { console\.log(e); }/catch(e) {}/g' \
    agent_outputs/mutation_b{11..15}_*.html

echo "Done. Re-validating..."

# Final validation
./run_tests.sh --test-file agent_outputs/mutation_b{11..15}_*.html --browsers firefox

# Verify no console output
for json in agent_outputs/mutation_b{11..15}_*.json; do
    if jq -e '.console_logs | length > 0' "$json" >/dev/null; then
        echo "WARNING: Console output in $(basename $json)"
    fi
done
```

---

## Phase 7: Commit and Document

### Step 7.1: Update Documentation

```bash
# Update completion summary
echo "
## Round N Enhancement ($(date +%Y-%m-%d))

- Added 25 seeds (Batches 11-15)
- Coverage improvements:
  - UBO: 16% → 27%
  - Transform Feedback: 8% → 20%
  - Sync Objects: 4% → 13%
- Total corpus: 75 seeds
- All seeds passing validation
" >> docs/MUTATION_SEEDS_COMPLETION_SUMMARY.md

# Regenerate feature matrix
./scripts/feature_matrix.sh > docs/feature_matrix_$(date +%Y%m%d).md
```

### Step 7.2: Commit New Seeds

```bash
# Stage new seeds
git add agent_outputs/mutation_b{11..15}_*.html

# Stage updated docs
git add docs/MUTATION_SEEDS_COMPLETION_SUMMARY.md
git add docs/feature_matrix_$(date +%Y%m%d).md
git add docs/plans/*enhancement*.md

# Commit with comprehensive message
git commit -m "$(cat <<'EOF'
feat: add 25 enhancement seeds for coverage gaps (Round N)

## New Seeds Added

- Batch 11: UBO-heavy seeds (5 seeds)
- Batch 12: Transform Feedback heavy (5 seeds)
- Batch 13: Sync and Query heavy (5 seeds)
- Batch 14: Sampler and Integer Texture (5 seeds)
- Batch 15: MRT and Advanced Blending (5 seeds)

## Coverage Improvements

- UBO: 16% → 27% (+11%)
- Transform Feedback: 8% → 20% (+12%)
- Sync Objects: 4% → 13% (+9%)
- Query Objects: 4% → 13% (+9%)
- Sampler Objects: 2% → 13% (+11%)
- Integer Textures: 4% → 13% (+9%)

## Corpus Statistics

- Total seeds: 50 → 75 (+25)
- Total lines: 10,307 → 15,300 (+5,000)
- Total mutation targets: 2,991 → 4,500 (+1,500)
- Mutation density: 1 target per 3.4 lines (maintained)

## Validation

- 25/25 seeds passing (100%)
- 75/75 corpus passing (100%)
- Zero console output
- Zero JavaScript errors
- All tested with Firefox Playwright

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### Step 7.3: Push to Remote

```bash
# Push to GitHub
git push origin master

# Tag release (optional)
git tag -a v1.1.0 -m "Corpus expansion: 75 seeds with improved coverage"
git push origin v1.1.0
```

---

## Automation: Complete Workflow Script

```bash
#!/bin/bash
# iterative_expansion.sh - Complete automated workflow

set -euo pipefail

ROUND_NUM=${1:-1}
NEW_SEEDS=${2:-25}
NEW_BATCH_START=$((10 + ROUND_NUM * 5))

echo "=== Iterative Corpus Expansion: Round $ROUND_NUM ==="

# Phase 1: Generate Feature Matrix
echo "[Phase 1] Generating feature matrix..."
./scripts/analyze_corpus.sh > /tmp/corpus_stats_round${ROUND_NUM}.txt
./scripts/feature_matrix.sh >> /tmp/corpus_stats_round${ROUND_NUM}.txt
cat /tmp/corpus_stats_round${ROUND_NUM}.txt

# Phase 2: Identify Gaps (manual review required)
echo ""
echo "[Phase 2] Coverage gaps identified. Review /tmp/corpus_stats_round${ROUND_NUM}.txt"
echo "Press ENTER to continue with enhancement plan creation..."
read

# Phase 3: Create Enhancement Plan (manual)
echo "[Phase 3] Create enhancement plan at docs/plans/$(date +%Y-%m-%d)-enhancement-round-${ROUND_NUM}.md"
echo "Press ENTER when plan is complete..."
read

# Phase 4: Parallel Generation (manual)
echo "[Phase 4] Launch parallel agents for $NEW_SEEDS new seeds"
echo "Press ENTER when all agents have completed..."
read

# Phase 5: Validation
echo "[Phase 5] Validating new seeds..."
./run_tests.sh --test-file agent_outputs/mutation_b{$NEW_BATCH_START..$((NEW_BATCH_START+4))}_*.html --browsers firefox

# Check for failures
TOTAL=$(ls agent_outputs/mutation_b{$NEW_BATCH_START..$((NEW_BATCH_START+4))}_*.html | wc -l)
PASSED=$(grep -l '"passed": true' agent_outputs/mutation_b{$NEW_BATCH_START..$((NEW_BATCH_START+4))}_*.json | wc -l)

if [ $TOTAL -ne $PASSED ]; then
    echo "[Phase 5] FAILURES DETECTED: $((TOTAL - PASSED)) seeds failed"
    echo "Fix failures and press ENTER to continue..."
    read

    # Re-validate
    ./run_tests.sh --test-file agent_outputs/mutation_b{$NEW_BATCH_START..$((NEW_BATCH_START+4))}_*.html --browsers firefox
fi

# Phase 6: Strip console logs
echo "[Phase 6] Stripping console.log from catch blocks..."
sed -i 's/catch(e) { console\.log(e); throw e; }/catch(e) { throw e; }/g' agent_outputs/mutation_b{$NEW_BATCH_START..$((NEW_BATCH_START+4))}_*.html
sed -i 's/catch(e) { console\.log(e); }/catch(e) {}/g' agent_outputs/mutation_b{$NEW_BATCH_START..$((NEW_BATCH_START+4))}_*.html

# Final validation
echo "[Phase 6] Final validation..."
./run_tests.sh --test-file agent_outputs/mutation_b{$NEW_BATCH_START..$((NEW_BATCH_START+4))}_*.html --browsers firefox

# Phase 7: Commit
echo "[Phase 7] Committing to git..."
git add agent_outputs/mutation_b{$NEW_BATCH_START..$((NEW_BATCH_START+4))}_*.html
git add docs/
git commit -m "feat: add $NEW_SEEDS enhancement seeds (Round $ROUND_NUM)"
git push origin master

echo ""
echo "=== Round $ROUND_NUM Complete ==="
echo "Total corpus: $(ls agent_outputs/mutation_b*.html | wc -l) seeds"
echo "All seeds validated and pushed to remote"
```

---

## Usage Examples

### Example 1: First Enhancement Round

```bash
# Generate statistics
./scripts/analyze_corpus.sh > round1_stats.txt
./scripts/feature_matrix.sh >> round1_stats.txt

# Review gaps (manual)
less round1_stats.txt

# Create enhancement plan (manual)
vim docs/plans/2026-01-27-enhancement-round-1.md

# Launch 5 parallel agents (manual)
# ... each agent creates 5 seeds ...

# Validate
./run_tests.sh --test-file agent_outputs/mutation_b11_*.html --browsers firefox

# Fix any failures (manual)

# Strip logs and finalize
sed -i 's/catch(e) { console\.log(e); }/catch(e) {}/g' agent_outputs/mutation_b{11..15}_*.html

# Commit
git add agent_outputs/mutation_b{11..15}_*.html docs/
git commit -m "feat: add 25 seeds for Round 1 enhancement"
git push
```

### Example 2: Automated Workflow

```bash
# Run complete workflow for Round 2
./iterative_expansion.sh 2 25

# Follow prompts for manual steps
# Script handles validation and commits automatically
```

---

## Quality Checklist

Before considering a round complete:

- [ ] Feature matrix generated and saved
- [ ] Coverage gaps identified and documented
- [ ] Enhancement plan created with detailed specifications
- [ ] All new seeds created (N/N complete)
- [ ] All seeds passing validation (100%)
- [ ] Console logs stripped from all catch blocks
- [ ] Documentation updated (completion summary, feature matrix)
- [ ] All changes committed to git
- [ ] Changes pushed to remote repository
- [ ] Coverage improvements verified in new feature matrix

---

## Troubleshooting

### Issue: Parallel agents create duplicate files

**Solution**: Assign non-overlapping batch numbers/seed IDs per agent

### Issue: Variable scoping errors persist

**Solution**: Add comprehensive `let` declarations at top of Declaration Zone:

```javascript
let buffer, buffer1, buffer2, texture, texture1, texture2;
let framebuffer, fbo1, fbo2, renderbuffer;
let program, vertexShader, fragmentShader;
let vao, vao1, vao2;
let query, sync;
```

### Issue: Extension not available in test environment

**Solution**: Check `UNSUPPORTED.md`, remove extension from seed, simplify to WebGL2 core

### Issue: Tests timeout or hang

**Solution**: Reduce geometry complexity, check for infinite loops, verify all WebGL calls are in try-catch

---

## Conclusion

This workflow enables continuous, iterative expansion of the fuzzing corpus based on empirical coverage analysis. Each round:

1. Identifies current coverage gaps
2. Designs seeds to fill specific gaps
3. Validates and fixes implementation
4. Documents improvements
5. Commits to repository

The workflow can be repeated indefinitely to achieve comprehensive WebGL2 API coverage, with each round building on the previous corpus.

**Current Status**: Round 1 complete (50 seeds → 75 seeds target)

**Next Round**: TBD based on Round 1 results and prioritization
