# Feature Combination Matrix - Example Output

This document shows example output from running the combination matrix analysis on the 225-seed corpus.

## Command

```bash
python3 workflow_package/scripts/feature_combination_matrix.py \
  --corpus-dir agent_outputs \
  --depth 2 \
  --min-threshold 5 \
  --output-matrix /tmp/combo_matrix.csv \
  --output-gaps /tmp/combo_gaps.md \
  --output-plan /tmp/round6_plan.md
```

## Expected Output

```
Analyzing corpus: agent_outputs
Found 225 seed files
Detected 18 feature categories
Building 2-way combination matrix...
  Found 153 unique combinations
Identifying gaps (threshold: 5 seeds)...
  Critical gaps: 2, High gaps: 0, Total gaps: 2
Matrix written to: /tmp/combo_matrix.csv
Gap report written to: /tmp/combo_gaps.md
Enhancement plan written to: /tmp/round6_plan.md

✅ Analysis complete!
```

## Key Findings (from example corpus)

**Critical Gaps (Priority >80):**
1. Texture Arrays + Transform Feedback (4 seeds, priority: 160.0)
2. 3D Textures + Transform Feedback (4 seeds, priority: 80.0)

**Recommendation:**
Create Round 6 with 10 targeted seeds to close critical gaps.

## Files Generated

- `/tmp/combo_matrix.csv`: 18×18 CSV matrix
- `/tmp/combo_gaps.md`: Gap report with specifications
- `/tmp/round6_plan.md`: 2-batch enhancement plan (10 seeds)
