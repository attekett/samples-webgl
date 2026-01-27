# Detailed Coverage Analysis Guide

## Overview

The `detailed_coverage_analysis.py` script provides comprehensive WebGL feature coverage analysis far beyond the basic shell scripts. It generates detailed reports including:

- **Granular API Call Frequency**: Not just presence/absence, but exact call counts per seed
- **Feature Co-occurrence Matrix**: Which features are commonly used together
- **Per-Seed Complexity Scoring**: Algorithmic complexity metrics for each seed
- **API Parameter Diversity**: How many different API variations are used
- **Coverage Heatmaps**: Visual representation of feature distribution (CSV export)
- **Edge Case Detection**: Identifies missing API patterns and unused functions
- **Extension Usage Tracking**: WebGL extension adoption across corpus
- **Gap Analysis**: Precise recommendations for improving coverage

## Quick Start

### Basic Usage

```bash
# Run analysis on default agent_outputs/ directory
python3 workflow_package/scripts/detailed_coverage_analysis.py

# Specify custom corpus directory
python3 workflow_package/scripts/detailed_coverage_analysis.py --corpus-dir samples-webgl

# Save report to file
python3 workflow_package/scripts/detailed_coverage_analysis.py --output coverage_report.md

# Generate both report and heatmap CSV
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --output report.md \
  --heatmap heatmap.csv
```

### Output Formats

```bash
# Markdown report (default, human-readable)
python3 workflow_package/scripts/detailed_coverage_analysis.py --format markdown

# JSON output (machine-readable, for tooling integration)
python3 workflow_package/scripts/detailed_coverage_analysis.py --format json
```

## Report Sections Explained

### 1. Feature Coverage Summary

Shows coverage percentage, total API calls, and average calls per seed for each feature category.

**Key Metrics:**
- **Seeds**: How many seeds use this feature
- **Coverage**: Percentage of corpus using this feature
- **Total API Calls**: Aggregate call count across all seeds
- **Avg Calls/Seed**: Average API calls per seed (among seeds using this feature)

**Use Cases:**
- Identify underrepresented features (< 20% coverage)
- Understand API usage intensity per feature
- Track coverage improvements between rounds

### 2. Most Used WebGL APIs

Ranks individual WebGL function calls by frequency across the entire corpus.

**Key Insights:**
- Reveals which APIs are mutation "hot spots" (high frequency = more radamsa targets)
- Identifies overused patterns that might need diversification
- Shows API usage distribution (is corpus balanced or biased?)

**Example:**
```
| 1 | `bindBuffer` | 1250 | 8.3 |
```
Means `bindBuffer` is called 1,250 times total (avg 8.3 per seed).

### 3. WebGL Extension Usage

Tracks which WebGL extensions are enabled in seeds.

**Use Cases:**
- Ensure extension diversity for testing different driver code paths
- Identify underutilized extensions that could expand attack surface
- Plan Round N to increase extension coverage

### 4. Feature Co-occurrence

Shows which features are commonly used together in the same seeds.

**Key Insights:**
- **High co-occurrence**: These features naturally complement each other (e.g., MRT + FBO)
- **Low co-occurrence**: Opportunities for creating combined "kitchen sink" seeds
- Guides creation of integrated tests that exercise multiple subsystems

**Example:**
```
| Buffer Operations | Texture Operations | 85 |
```
85 seeds use both buffers and textures together.

### 5. Seed Complexity Analysis

Algorithmic complexity scoring for each seed based on:
- Try-catch blocks × 2
- Total GL calls
- Bind operations × 1.5
- Create operations × 2
- Delete operations × 3 (UAF patterns)
- Extensions × 5
- Shader lines × 0.5

**Use Cases:**
- Identify "hypercomplex" seeds (high mutation potential)
- Find simple seeds that need enhancement
- Balance corpus complexity distribution
- Prioritize seeds for manual review

### 6. Aggregate Corpus Metrics

High-level statistics about the entire corpus:
- Total lines of code
- Total try-catch blocks (error path exploitation)
- Total GL API calls
- Mutation target density (targets per line of code)

**Key Metric: Mutation Target Density**
```
1 target per 5.5 lines
```
Lower is better (more mutation targets per line = denser fuzzing biomass).

### 7. Coverage Gaps & Recommendations

**Automatic gap analysis** showing features below 20% coverage threshold with exact seed counts needed to reach 20%.

**Example:**
```
| Integer Textures | 8% (13 seeds) | +17 |
```
Means you need +17 more seeds with integer textures to reach 20% coverage.

**Use Cases:**
- Directly informs Round N planning
- Prioritize feature additions
- Track progress toward coverage goals

### 8. API Diversity Analysis

For each feature category, shows what percentage of available APIs are actually used in the corpus.

**Key Insights:**
- **High diversity (>90%)**: Feature is well-exercised
- **Medium diversity (70-90%)**: Good coverage, minor gaps
- **Low diversity (<70%)**: Missing important API variants

Lists unused APIs for each low-diversity feature.

**Example:**
```
**Integer Textures**: 66% diversity (8/12 APIs used)
- Unused APIs: `RGBA16I, RGBA16UI, RGBA8I, RGBA8UI`
```

## Heatmap CSV Export

The `--heatmap` option generates a CSV file with binary feature presence (1/0) for each seed.

**Format:**
```csv
Seed,3D Textures,Blending,Buffer Operations,...
mutation_b1_s1.html,0,1,1,...
mutation_b1_s2.html,1,1,1,...
```

**Use Cases:**
- Import into Excel/Google Sheets for visual heatmap
- Generate charts with matplotlib/seaborn
- Integration with corpus management tools
- Quick visual identification of coverage patterns

**Example Visualization (pseudocode):**
```python
import pandas as pd
import seaborn as sns

df = pd.read_csv('heatmap.csv', index_col=0)
sns.heatmap(df, cmap='YlGnBu')
```

## JSON Output Format

Use `--format json` for machine-readable output suitable for:
- CI/CD pipeline integration
- Automated corpus management
- Custom visualization tools
- Historical tracking and diff analysis

**JSON Structure:**
```json
{
  "total_seeds": 150,
  "seeds": [
    {
      "filename": "mutation_b1_s1.html",
      "lines": 198,
      "features": { ... },
      "api_calls": { ... },
      "extensions": [ ... ],
      "metrics": {
        "complexity_score": 225.8,
        "try_catch_blocks": 10,
        ...
      }
    }
  ],
  "feature_matrix": { ... },
  "api_frequency": { ... },
  "extension_usage": { ... },
  "feature_cooccurrence": { ... }
}
```

## Integration with Workflow

### Phase 1: Pre-Round Analysis

```bash
# Generate baseline report
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --output /tmp/before_round_N.md \
  --heatmap /tmp/before_round_N.csv

# Review coverage gaps
grep "Coverage Gaps" /tmp/before_round_N.md
```

### Phase 2: Enhancement Planning

Use gap analysis to create enhancement plan:
```bash
# Extract features needing attention
grep "Seeds Needed" /tmp/before_round_N.md | awk '{print $2, $4}'
```

### Phase 3: Post-Round Validation

```bash
# Generate updated report
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --output /tmp/after_round_N.md \
  --heatmap /tmp/after_round_N.csv

# Compare before/after
diff <(grep "Coverage" /tmp/before_round_N.md) \
     <(grep "Coverage" /tmp/after_round_N.md)
```

## Advanced Usage

### Comparing Corpus Versions

```bash
# Analyze two corpus snapshots
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --corpus-dir corpus_v1 \
  --format json \
  --output corpus_v1.json

python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --corpus-dir corpus_v2 \
  --format json \
  --output corpus_v2.json

# Use jq to compare coverage changes
diff <(jq '.feature_matrix | keys[]' corpus_v1.json) \
     <(jq '.feature_matrix | keys[]' corpus_v2.json)
```

### Finding Specific Seeds

```bash
# Find all seeds using a specific feature
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --format json | \
  jq '.feature_matrix["Integer Textures"][]'

# Find seeds with complexity > 300
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --format json | \
  jq '.complexity_distribution[] | select(.score > 300) | .filename'
```

### Custom Filtering

```bash
# Seeds with low complexity (need enhancement)
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --format json | \
  jq '.seeds[] | select(.metrics.complexity_score < 100) | .filename'

# Seeds with no extensions (add extension coverage)
python3 workflow_package/scripts/detailed_coverage_analysis.py \
  --format json | \
  jq '.seeds[] | select(.extensions | length == 0) | .filename'
```

## Performance

**Typical Performance** (150 seeds):
- Analysis time: ~5-10 seconds
- Memory usage: ~50 MB
- Report generation: ~1 second

For large corpora (500+ seeds):
- Consider using `--format json` for faster processing
- Pipe through `jq` for targeted queries instead of generating full markdown

## Comparison with Basic Scripts

| Feature | analyze_corpus.sh | feature_matrix.sh | detailed_coverage_analysis.py |
|---------|-------------------|-------------------|-------------------------------|
| **Feature Coverage** | Basic counts | Present/absent | Present + call frequency |
| **API Analysis** | None | None | Top 20 APIs + full frequency table |
| **Extensions** | None | None | Full tracking with coverage % |
| **Co-occurrence** | None | None | Full matrix with counts |
| **Complexity Scoring** | Basic metrics | None | Algorithmic scoring + ranking |
| **Gap Analysis** | Manual | Manual | Automatic with seed counts |
| **API Diversity** | None | None | Percentage + unused API list |
| **Heatmap Export** | None | None | CSV for visualization |
| **JSON Output** | None | None | Full machine-readable format |
| **Speed** | Fast (~1s) | Fast (~1s) | Moderate (~10s) |

## Troubleshooting

**Issue**: Script runs slowly on large corpus
**Solution**: Use `--format json` and pipe to file, then process with `jq`

**Issue**: Missing features in report
**Solution**: Check that seed filenames match `mutation_b*.html` pattern

**Issue**: Coverage percentages seem wrong
**Solution**: Verify corpus directory path with `--corpus-dir`

**Issue**: Want to add custom feature categories
**Solution**: Edit `self.features` dictionary in the script (lines 30-110)

## Future Enhancements

Potential additions to the analysis tool:

1. **Temporal Coverage**: Track coverage changes over time (commit history)
2. **Radamsa Integration**: Predict mutation effectiveness based on target density
3. **Crash Correlation**: Link crashes to specific feature combinations
4. **Visual Heatmaps**: Built-in matplotlib generation (not just CSV export)
5. **API Sequence Analysis**: Common API call patterns and anti-patterns
6. **Shader Complexity Metrics**: More detailed shader analysis (uniforms, varyings, etc.)
7. **WebGL Error Patterns**: Analyze intentional error-triggering code
8. **State Machine Visualization**: Graph of state transitions

## Contributing

To add new feature categories:

1. Edit the `self.features` dictionary (around line 30)
2. Add feature name as key
3. List API patterns to detect as array value
4. Patterns are regex-matched against seed content

Example:
```python
'My New Feature': [
    'newAPICall1', 'newAPICall2', 'CONSTANT_NAME'
]
```

## See Also

- `analyze_corpus.sh` - Fast basic statistics
- `feature_matrix.sh` - Simple feature presence detection
- `calculate_gap_seeds.sh` - Coverage gap calculator
- `ITERATIVE_CORPUS_EXPANSION_WORKFLOW.md` - Full workflow guide
