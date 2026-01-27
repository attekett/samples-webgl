#!/bin/bash
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
for f in agent_outputs/mutation_b*.html; do grep -c 'try {' "$f" 2>/dev/null || echo "0"; done | awk '{sum+=$1; if(NR==1){min=$1;max=$1} if($1<min){min=$1} if($1>max){max=$1}} END {print "Total Try-Catch Blocks:", sum; print "Average/Seed:", sum/NR; print "Min:", min; print "Max:", max}'
echo ""

echo "## 3. Amplification Variables (const declarations in main)"
for f in agent_outputs/mutation_b*.html; do grep -c '^[[:space:]]*const [a-zA-Z]' "$f" 2>/dev/null || echo "0"; done | awk '{sum+=$1} END {print "Total Amplification Variables:", sum; print "Average/Seed:", sum/NR}'
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
for f in agent_outputs/mutation_b*.html; do grep -c 'gl\.' "$f" 2>/dev/null || echo "0"; done | awk '{sum+=$1} END {print "Total gl.* calls:", sum; print "Average/Seed:", int(sum/NR)}'
echo ""

echo "## 6. Mutation Pattern Frequency"
echo "Bind Operations:"
for f in agent_outputs/mutation_b*.html; do grep -c 'bindBuffer\|bindTexture\|bindFramebuffer' "$f" 2>/dev/null || echo "0"; done | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo "Enable/Disable:"
for f in agent_outputs/mutation_b*.html; do grep -c 'gl\.enable\|gl\.disable' "$f" 2>/dev/null || echo "0"; done | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo "Create Operations:"
for f in agent_outputs/mutation_b*.html; do grep -c 'createBuffer\|createTexture\|createFramebuffer\|createRenderbuffer' "$f" 2>/dev/null || echo "0"; done | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo "Delete Operations:"
for f in agent_outputs/mutation_b*.html; do grep -c 'deleteBuffer\|deleteTexture\|deleteFramebuffer' "$f" 2>/dev/null || echo "0"; done | awk '{sum+=$1} END {print "  Total:", sum, "  Average/Seed:", int(sum/NR)}'
echo ""
