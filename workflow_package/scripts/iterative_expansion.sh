#!/bin/bash
# iterative_expansion.sh - Complete automated workflow for corpus expansion

set -euo pipefail

ROUND_NUM=${1:-1}
NEW_SEEDS=${2:-25}
NEW_BATCH_START=$((10 + ROUND_NUM * 5))
NEW_BATCH_END=$((NEW_BATCH_START + 4))

echo "=== Iterative Corpus Expansion: Round $ROUND_NUM ==="
echo ""

# Phase 1: Generate Feature Matrix
echo "[Phase 1] Generating feature matrix..."
./scripts/analyze_corpus.sh > /tmp/corpus_stats_round${ROUND_NUM}.txt
./scripts/feature_matrix.sh >> /tmp/corpus_stats_round${ROUND_NUM}.txt
echo ""
cat /tmp/corpus_stats_round${ROUND_NUM}.txt
echo ""

# Save to docs
mkdir -p docs
cp /tmp/corpus_stats_round${ROUND_NUM}.txt docs/corpus_stats_$(date +%Y%m%d).txt

# Phase 2: Identify Gaps (manual review required)
echo "[Phase 2] Coverage gaps identified."
echo "Running gap calculation..."
./scripts/calculate_gap_seeds.sh $NEW_SEEDS
echo ""
echo "Review /tmp/corpus_stats_round${ROUND_NUM}.txt"
echo "Press ENTER to continue with enhancement plan creation..."
read

# Phase 3: Create Enhancement Plan (manual)
echo "[Phase 3] Create enhancement plan"
echo "Location: docs/plans/$(date +%Y-%m-%d)-enhancement-round-${ROUND_NUM}.md"
echo "Template: workflow_package/templates/enhancement_plan_template.md"
echo ""
echo "Press ENTER when plan is complete..."
read

# Phase 4: Parallel Generation (manual)
echo "[Phase 4] Launch parallel agents for $NEW_SEEDS new seeds"
echo "Expected batches: ${NEW_BATCH_START} through ${NEW_BATCH_END}"
echo "Expected files: mutation_b${NEW_BATCH_START}_s*.html through mutation_b${NEW_BATCH_END}_s*.html"
echo ""
echo "Press ENTER when all agents have completed..."
read

# Check if files exist
FILE_COUNT=$(ls agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.html 2>/dev/null | wc -l)
echo "Found $FILE_COUNT new seed files"
if [ $FILE_COUNT -eq 0 ]; then
    echo "ERROR: No new seed files found in agent_outputs/"
    exit 1
fi

# Phase 5: Validation
echo ""
echo "[Phase 5] Validating new seeds..."
./scripts/validate_new_seeds.sh $NEW_BATCH_START $NEW_BATCH_END

# Check for failures
TOTAL=$(ls agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.html 2>/dev/null | wc -l)
PASSED=$(grep -l '"passed": true' agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.json 2>/dev/null | wc -l)

if [ $TOTAL -ne $PASSED ]; then
    echo ""
    echo "[Phase 5] FAILURES DETECTED: $((TOTAL - PASSED)) seeds failed"
    echo ""
    ./scripts/analyze_failures.sh
    echo ""
    echo "Fix failures and press ENTER to re-validate..."
    read

    # Re-validate
    echo "Re-validating..."
    ./scripts/validate_new_seeds.sh $NEW_BATCH_START $NEW_BATCH_END

    # Check again
    PASSED=$(grep -l '"passed": true' agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.json 2>/dev/null | wc -l)
    if [ $TOTAL -ne $PASSED ]; then
        echo "ERROR: Still have failures. Please fix manually."
        exit 1
    fi
fi

# Phase 6: Strip console logs
echo ""
echo "[Phase 6] Stripping console.log from catch blocks..."
./scripts/strip_console_logs.sh $NEW_BATCH_START $NEW_BATCH_END

# Final validation
echo "[Phase 6] Final validation..."
./scripts/validate_new_seeds.sh $NEW_BATCH_START $NEW_BATCH_END

# Verify no console output
echo "Checking for console output..."
for json in agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.json; do
    if grep -q '"console_logs":\[' "$json" && ! grep -q '"console_logs":\[\]' "$json"; then
        echo "WARNING: Console output detected in $(basename $json)"
    fi
done

# Phase 7: Generate updated statistics
echo ""
echo "[Phase 7] Generating updated statistics..."
./scripts/analyze_corpus.sh > docs/corpus_stats_after_round${ROUND_NUM}.txt
./scripts/feature_matrix.sh >> docs/corpus_stats_after_round${ROUND_NUM}.txt

echo ""
echo "=== Before and After Comparison ==="
echo ""
echo "BEFORE:"
grep "File Count:" /tmp/corpus_stats_round${ROUND_NUM}.txt
echo ""
echo "AFTER:"
grep "File Count:" docs/corpus_stats_after_round${ROUND_NUM}.txt
echo ""

# Commit
echo "[Phase 7] Ready to commit to git"
echo "Commit new seeds? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    git add agent_outputs/mutation_b{$NEW_BATCH_START..$NEW_BATCH_END}_*.html
    git add docs/
    git commit -m "feat: add $NEW_SEEDS enhancement seeds (Round $ROUND_NUM)

- Batches ${NEW_BATCH_START}-${NEW_BATCH_END}
- All seeds validated and passing
- Console logs stripped for production
- Updated corpus statistics

Total corpus: $(ls agent_outputs/mutation_b*.html | wc -l) seeds

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

    echo ""
    echo "Push to remote? (y/n)"
    read -r push_response
    if [[ "$push_response" =~ ^[Yy]$ ]]; then
        git push origin master
    fi
fi

echo ""
echo "=== Round $ROUND_NUM Complete ==="
echo "Total corpus: $(ls agent_outputs/mutation_b*.html | wc -l) seeds"
echo "All seeds validated and committed"
