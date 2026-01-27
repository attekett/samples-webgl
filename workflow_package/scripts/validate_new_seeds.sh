#!/bin/bash
# validate_new_seeds.sh - Validate newly created seeds

NEW_BATCH_START=${1:-11}
NEW_BATCH_END=${2:-15}

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
