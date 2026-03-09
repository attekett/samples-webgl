#!/bin/bash
ALL_HTML=$(find agent_outputs/ -maxdepth 1 -name "*.html"; find samples-webgl/ -name "*.html")
echo "=== COMPREHENSIVE CORPUS STATISTICS ==="
echo ""
echo "## 1. File Size Metrics"
echo "File Count: $(echo "$ALL_HTML" | wc -l)"
echo "Total Lines: $(echo "$ALL_HTML" | xargs wc -l | tail -1 | awk '{print $1}')"
echo "Total Size: $(echo "$ALL_HTML" | xargs du -ch 2>/dev/null | tail -1 | awk '{print $1}')"
echo "Average Lines/Seed: $(echo "$ALL_HTML" | xargs wc -l | awk 'END {print int($1/(NR-1))}')"
echo "Min Lines: $(echo "$ALL_HTML" | xargs wc -l | sort -n | head -1 | awk '{print $1, $2}')"
echo "Max Lines: $(echo "$ALL_HTML" | xargs wc -l | sort -n | tail -2 | head -1 | awk '{print $1, $2}')"
echo ""

echo "## 2. Try-Catch Block Analysis"
echo "$ALL_HTML" | xargs -I{} sh -c 'grep -c "try {" "$1" 2>/dev/null || echo "0"' -- {} | awk '{sum+=$1; if(NR==1){min=$1;max=$1} if($1<min){min=$1} if($1>max){max=$1}} END {print "Total Try-Catch Blocks:", sum; print "Average/Seed:", sum/NR; print "Min:", min; print "Max:", max}'
echo ""

echo "## 3. Amplification Variables (const declarations in main)"
echo "$ALL_HTML" | xargs -I{} sh -c 'grep -c "^[[:space:]]*const [a-zA-Z]" "$1" 2>/dev/null || echo "0"' -- {} | awk '{sum+=$1} END {print "Total Amplification Variables:", sum; print "Average/Seed:", sum/NR}'
echo ""

echo "## 4. Inline Literals (numeric values in function calls)"
echo -n "Analyzing inline literals... "
total_inlines=0
while IFS= read -r f; do
  count=$(grep -oE 'gl\.[a-zA-Z]+\([^)]*[0-9]+[^)]*\)' "$f" | wc -l)
  total_inlines=$((total_inlines + count))
done <<< "$ALL_HTML"
file_count=$(echo "$ALL_HTML" | wc -l)
echo "Done"
echo "Total Inline Literals: ~$total_inlines"
echo "Average/Seed: ~$((total_inlines / file_count))"
echo ""

echo "## 5. WebGL API Call Density"
echo "$ALL_HTML" | xargs -I{} sh -c 'grep -c "gl\." "$1" 2>/dev/null || echo "0"' -- {} | awk '{sum+=$1} END {print "Total gl.* calls:", sum; print "Average/Seed:", int(sum/NR)}'
echo ""

echo "## 6. Mutation Pattern Frequency"
echo "Bind Operations:"
echo "$ALL_HTML" | xargs -I{} sh -c 'grep -c "bindBuffer\|bindTexture\|bindFramebuffer" "$1" 2>/dev/null || echo "0"' -- {} | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo "Enable/Disable:"
echo "$ALL_HTML" | xargs -I{} sh -c 'grep -c "gl\.enable\|gl\.disable" "$1" 2>/dev/null || echo "0"' -- {} | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo "Create Operations:"
echo "$ALL_HTML" | xargs -I{} sh -c 'grep -c "createBuffer\|createTexture\|createFramebuffer\|createRenderbuffer" "$1" 2>/dev/null || echo "0"' -- {} | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo "Delete Operations:"
echo "$ALL_HTML" | xargs -I{} sh -c 'grep -c "deleteBuffer\|deleteTexture\|deleteFramebuffer" "$1" 2>/dev/null || echo "0"' -- {} | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo ""

echo "## 2b. Mutation Seed Batch Stats"
echo "Mutation Batch File Count: $(find agent_outputs/ samples-webgl/ -name "mutation_b*.html" 2>/dev/null | wc -l)"
echo "Mutation Batch Total Lines: $(find agent_outputs/ samples-webgl/ -name "mutation_b*.html" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')"
echo ""
