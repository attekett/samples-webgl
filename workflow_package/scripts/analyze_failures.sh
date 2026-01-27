#!/bin/bash
# analyze_failures.sh - Analyze failed seed tests

echo "=== Failure Analysis ==="

for json in agent_outputs/mutation_b*.json; do
    if ! grep -q '"passed": true' "$json"; then
        html="${json%.json}.html"
        echo ""
        echo "FAILURE: $(basename $html)"
        echo "Errors:"

        # Check if jq is available
        if command -v jq &> /dev/null; then
            jq -r '.javascript_errors[], .webgl_errors[], .errors[]' "$json" 2>/dev/null | head -5
        else
            # Fallback to grep if jq not available
            grep -o '"javascript_errors":\[.*\]' "$json" | head -1
            grep -o '"webgl_errors":\[.*\]' "$json" | head -1
            grep -o '"errors":\[.*\]' "$json" | head -1
        fi
    fi
done

echo ""
echo "=== Summary ==="
total=$(ls agent_outputs/mutation_b*.json 2>/dev/null | wc -l)
failed=$(grep -L '"passed": true' agent_outputs/mutation_b*.json 2>/dev/null | wc -l)
echo "Total tests: $total"
echo "Failed tests: $failed"
echo "Pass rate: $(( (total - failed) * 100 / total ))%"
