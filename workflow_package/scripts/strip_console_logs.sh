#!/bin/bash
# strip_console_logs.sh - Remove console.log from catch blocks for production

BATCH_START=${1:-11}
BATCH_END=${2:-15}

echo "Stripping console.log from catch blocks..."

# Pattern 1: catch(e) { console.log(e); throw e; } → catch(e) { throw e; }
sed -i 's/catch(e) { console\.log(e); throw e; }/catch(e) { throw e; }/g' \
    agent_outputs/mutation_b{$BATCH_START..$BATCH_END}_*.html

# Pattern 2: catch(e) { console.log(e); } → catch(e) {}
sed -i 's/catch(e) { console\.log(e); }/catch(e) {}/g' \
    agent_outputs/mutation_b{$BATCH_START..$BATCH_END}_*.html

echo "Done."

# Count changes
total_files=$(ls agent_outputs/mutation_b{$BATCH_START..$BATCH_END}_*.html 2>/dev/null | wc -l)
echo "Processed $total_files files"
