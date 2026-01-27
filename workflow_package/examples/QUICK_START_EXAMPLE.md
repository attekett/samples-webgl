# Quick Start Example

This example demonstrates using the workflow package for Round 1 enhancement (adding 25 seeds to a 50-seed corpus).

---

## Starting Point

```
your-project/
├── agent_outputs/
│   ├── mutation_b1_s1_mrt_float_blend.html
│   ├── mutation_b1_s2_mrt_integer_layered.html
│   ├── ... (48 more seeds)
│   └── mutation_b10_s50_context_state.html
├── run_tests.sh
└── docs/
```

**Current Status**: 50 seeds (mutation_b1 through mutation_b10)

---

## Step 1: Copy Workflow Package

```bash
cd your-project
cp -r /path/to/workflow_package .
chmod +x workflow_package/scripts/*.sh
```

---

## Step 2: Generate Statistics

```bash
# Generate corpus analysis
./workflow_package/scripts/analyze_corpus.sh > round1_stats.txt
./workflow_package/scripts/feature_matrix.sh >> round1_stats.txt

# View results
cat round1_stats.txt
```

**Example Output**:
```
=== COMPREHENSIVE CORPUS STATISTICS ===

## 1. File Size Metrics
File Count: 50
Total Lines: 10307
Total Size: 350K
Average Lines/Seed: 206

## 8. Feature Coverage Matrix

| Feature Category | Seeds | Coverage |
|------------------|-------|----------|
| Buffer Operations | 50/50 | 100% |
| Uniform Buffer Objects | 8/50 | 16% |
| Transform Feedback | 4/50 | 8% |
| Sync Objects | 2/50 | 4% |
| Query Objects | 2/50 | 4% |
| Sampler Objects | 1/50 | 2% |
```

---

## Step 3: Identify Gaps

```bash
# Calculate needed seeds
./workflow_package/scripts/calculate_gap_seeds.sh 25
```

**Example Output**:
```
Current corpus: 50 seeds
Target addition: 25 seeds
Target corpus: 75 seeds
Target coverage: 20%

Seeds needed per category to reach 20% coverage:

  UBO:                          Current: 16% ( 8/50) → Need: 7 more seeds
  Transform Feedback:           Current:  8% ( 4/50) → Need: 11 more seeds
  Sync Objects:                 Current:  4% ( 2/50) → Need: 13 more seeds
  Query Objects:                Current:  4% ( 2/50) → Need: 13 more seeds
  Sampler Objects:              Current:  2% ( 1/50) → Need: 14 more seeds
```

---

## Step 4: Create Enhancement Plan

```bash
# Copy template
cp workflow_package/templates/enhancement_plan_template.md \
   docs/plans/2026-01-27-enhancement-round-1.md

# Edit with your specifications
# Fill in:
# - Batch 11: UBO-focused seeds (5 seeds)
# - Batch 12: Transform Feedback seeds (5 seeds)
# - Batch 13: Sync/Query seeds (5 seeds)
# - Batch 14: Sampler seeds (5 seeds)
# - Batch 15: Mixed advanced features (5 seeds)
```

---

## Step 5: Generate Seeds

**Manual Approach** (using AI agents or developers):

Create 5 agents/developers, each responsible for one batch:
- Agent 1: Creates mutation_b11_s51.html through mutation_b11_s55.html
- Agent 2: Creates mutation_b12_s56.html through mutation_b12_s60.html
- Agent 3: Creates mutation_b13_s61.html through mutation_b13_s65.html
- Agent 4: Creates mutation_b14_s66.html through mutation_b14_s70.html
- Agent 5: Creates mutation_b15_s71.html through mutation_b15_s75.html

Each follows the enhancement plan specifications.

---

## Step 6: Validate New Seeds

```bash
# Validate batches 11-15
./workflow_package/scripts/validate_new_seeds.sh 11 15
```

**Expected Output**:
```
=== Validating New Seeds ===
Start: Mon Jan 27 15:00:00 2026

Testing Batch 11...
[Test results...]

Testing Batch 12...
[Test results...]

...

Summary:
Total: 25
PASS: 25
FAIL: 0
```

**If failures occur**:
```bash
# Analyze failures
./workflow_package/scripts/analyze_failures.sh

# Output shows:
# FAILURE: mutation_b11_s51_ubo_large_blocks.html
# Errors:
# ReferenceError: buffer is not defined

# Fix the issues manually, then re-validate
./workflow_package/scripts/validate_new_seeds.sh 11 15
```

---

## Step 7: Production Preparation

```bash
# Strip console.log from catch blocks
./workflow_package/scripts/strip_console_logs.sh 11 15

# Final validation
./workflow_package/scripts/validate_new_seeds.sh 11 15

# Should show:
# Total: 25
# PASS: 25
# FAIL: 0
```

---

## Step 8: Verify Improvements

```bash
# Generate new statistics
./workflow_package/scripts/analyze_corpus.sh > round1_after.txt
./workflow_package/scripts/feature_matrix.sh >> round1_after.txt

# Compare before/after
diff -u round1_stats.txt round1_after.txt
```

**Example Comparison**:
```diff
- File Count: 50
+ File Count: 75

- | Uniform Buffer Objects | 8/50 | 16% |
+ | Uniform Buffer Objects | 20/75 | 27% |

- | Transform Feedback | 4/50 | 8% |
+ | Transform Feedback | 15/75 | 20% |

- | Sync Objects | 2/50 | 4% |
+ | Sync Objects | 10/75 | 13% |
```

---

## Step 9: Commit Changes

```bash
# Stage new seeds
git add agent_outputs/mutation_b{11..15}_*.html

# Stage documentation
git add docs/

# Commit
git commit -m "feat: add 25 enhancement seeds (Round 1)

- Batch 11: UBO-heavy seeds (5 seeds)
- Batch 12: Transform Feedback seeds (5 seeds)
- Batch 13: Sync/Query seeds (5 seeds)
- Batch 14: Sampler seeds (5 seeds)
- Batch 15: Advanced features (5 seeds)

Coverage improvements:
- UBO: 16% → 27%
- Transform Feedback: 8% → 20%
- Sync Objects: 4% → 13%

Total corpus: 50 → 75 seeds

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push
git push origin master
```

---

## Step 10: Automated Workflow (Alternative)

Instead of manual steps 1-9, use the automated script:

```bash
# Run complete workflow interactively
./workflow_package/scripts/iterative_expansion.sh 1 25

# The script will:
# 1. Generate statistics
# 2. Calculate gaps
# 3. Prompt for enhancement plan creation
# 4. Prompt when seeds are ready
# 5. Validate automatically
# 6. Strip console logs
# 7. Generate updated stats
# 8. Commit and push
```

---

## Expected Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Statistics | 1 min | Generate feature matrix |
| Planning | 15 min | Create enhancement plan |
| Generation | 30 min | Create 25 seeds (parallel) |
| Validation | 3 min | Test all seeds |
| Fixes | 10 min | Fix any failures |
| Finalization | 2 min | Strip logs, re-test |
| Commit | 2 min | Git operations |
| **Total** | **~1 hour** | **Round 1 complete** |

---

## Success Criteria

- ✅ 25 new seeds created (mutation_b11 through mutation_b15)
- ✅ 75/75 seeds passing validation (100%)
- ✅ Coverage gaps addressed (UBO, TF, Sync, Query, Sampler > 20%)
- ✅ No console output in production seeds
- ✅ All changes committed and pushed
- ✅ Updated documentation

---

## Next Steps

**Round 2** (if needed):
```bash
# Repeat workflow for next 25 seeds
./workflow_package/scripts/iterative_expansion.sh 2 25

# This creates batches 16-20 (mutation_b16 through mutation_b20)
```

**Fuzzing**:
```bash
# Use Radamsa to generate mutations
radamsa -n 1000 agent_outputs/mutation_b*.html -o fuzz_%n.html

# See RADAMSA_INTEGRATION_GUIDE.md for complete fuzzing workflows
```

---

## Troubleshooting

### "No such file or directory: agent_outputs/"

Ensure you're in the project root where `agent_outputs/` exists.

### Scripts don't execute

```bash
chmod +x workflow_package/scripts/*.sh
```

### Feature matrix shows 0/0

Check that seed files match pattern `agent_outputs/mutation_b*.html`.

### Git commit fails

Ensure git is initialized:
```bash
git init
git remote add origin <your-repo-url>
```

---

This example demonstrates a complete Round 1 enhancement cycle from 50 to 75 seeds in approximately 1 hour using the workflow package.
