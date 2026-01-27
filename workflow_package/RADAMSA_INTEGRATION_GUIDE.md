# Radamsa Integration Guide for WebGL2 Fuzzing Corpus

**Date**: 2026-01-27
**Target**: Mutation-based fuzzing of WebGL2 drivers for memory corruption bugs
**Corpus**: 50+ mutation-optimized WebGL2 seed files
**Mutator**: Radamsa (general-purpose mutation fuzzer)

---

## Table of Contents

1. [Overview](#overview)
2. [Radamsa Basics](#radamsa-basics)
3. [Corpus Structure Optimization](#corpus-structure-optimization)
4. [Mutation Strategies](#mutation-strategies)
5. [Fuzzing Workflow](#fuzzing-workflow)
6. [Crash Detection](#crash-detection)
7. [Corpus Selection](#corpus-selection)
8. [Triaging and Minimization](#triaging-and-minimization)
9. [Advanced Techniques](#advanced-techniques)
10. [Automation Scripts](#automation-scripts)

---

## Overview

This guide explains how to use radamsa with the mutation-optimized WebGL2 corpus to find memory corruption bugs in WebGL drivers. The corpus is specifically designed for radamsa's mutation strategies:

- **Line repetition patterns** → radamsa's line/block duplication mutations
- **Numeric literals** → radamsa's numeric mutation strategies
- **Enum constants** → radamsa's line corruption patterns
- **Try-catch error paths** → allows driver state corruption to accumulate

**Target Bugs**:
- Use-after-free (UAF)
- Double-free
- Heap corruption
- Out-of-bounds access
- Integer overflows
- Type confusion

---

## Radamsa Basics

### Installation

```bash
# From source (recommended)
git clone https://gitlab.com/akihe/radamsa.git
cd radamsa
make
sudo make install

# Verify installation
radamsa --version
```

### Basic Usage

```bash
# Mutate single file to stdout
radamsa seed.html

# Generate 10 mutations
radamsa -n 10 seed.html

# Mutate multiple seeds
radamsa seed1.html seed2.html seed3.html

# Set seed for reproducibility
radamsa -s 12345 seed.html

# Output to file
radamsa seed.html > mutated.html
```

### Mutation Modes

Radamsa uses various mutation strategies:

| Strategy | Description | Corpus Optimization |
|----------|-------------|---------------------|
| **bd** (byte drop) | Remove bytes | Try-catch allows execution |
| **bi** (byte insert) | Insert random bytes | Inline literals targeted |
| **br** (byte repeat) | Repeat byte sequences | Line repetition patterns |
| **bp** (byte permute) | Swap byte order | Enum constant corruption |
| **bf** (byte flip) | Flip random bits | Numeric value fuzzing |
| **num** (number fuzzing) | Mutate numeric values | Amplification variables |
| **ld** (line drop) | Remove lines | Error recovery paths |
| **lr** (line repeat) | Duplicate lines | Bind ping-pong exploitation |
| **ls** (line swap) | Reorder lines | State thrashing patterns |

---

## Corpus Structure Optimization

### Three-Zone Architecture Exploitation

Our corpus uses a three-zone structure specifically designed for radamsa:

#### 1. Declaration Zone (Amplification Target)

```javascript
// Original seed
const texSize = 256;
const texPixels = texSize * texSize;
const bufferSize = texPixels * 4;
```

**Radamsa Mutations**:
- `texSize = 256` → `texSize = 256256` (digit duplication)
- `texSize = 256` → `texSize = -256` (sign flip)
- `texSize = 256` → `texSize = 0x100000` (numeric explosion)
- `texSize * texSize` → `texSize * texSize * texSize` (operator duplication)

**Impact**: Cascading mutations affect all dependent calculations

#### 2. Setup Zone (Line Repetition Target)

```javascript
// Original seed
try {
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer1);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer2);
} catch(e) {}
```

**Radamsa Mutations**:
- Line duplication: `bindBuffer` called 3-4 times consecutively
- Line swapping: bind operations reordered
- Line dropping: one bind removed, creating invalid state

**Impact**: Driver state machine corruption

#### 3. Execution Zone (Error Path Exploitation)

```javascript
// Original seed
try {
    gl.drawArrays(gl.TRIANGLES, 0, vertexCount);
} catch(e) {}
```

**Radamsa Mutations**:
- Remove try-catch (error propagation)
- Mutate parameters: `0` → `-1`, `vertexCount` → `999999999`
- Duplicate draw calls

**Impact**: Trigger corrupted driver state accumulated from Setup Zone

---

## Mutation Strategies

### Strategy 1: Numeric Fuzzing Focus

Target numeric literals in inline API calls:

```bash
# Focus on number mutations
radamsa -m num,bf,bp -n 100 agent_outputs/mutation_b*.html -o fuzz_%n.html
```

**Targets**:
- Buffer sizes: `gl.bufferData(gl.ARRAY_BUFFER, 1024, ...)`
- Texture dimensions: `gl.texImage2D(..., 256, 256, ...)`
- Vertex counts: `gl.drawArrays(gl.TRIANGLES, 0, 36)`
- Offsets: `gl.uniformBlockBinding(program, 0, 1)`

**Expected Bugs**: Integer overflows, out-of-bounds access

### Strategy 2: Line Repetition Exploitation

Target bind/enable/disable patterns:

```bash
# Focus on line repetition/duplication
radamsa -m lr,ld,ls -n 100 agent_outputs/mutation_b*.html -o fuzz_%n.html
```

**Targets**:
- Bind operations: `gl.bindBuffer(...)`, `gl.bindTexture(...)`
- State changes: `gl.enable(...)`, `gl.disable(...)`
- FBO attachments: `gl.framebufferTexture2D(...)`

**Expected Bugs**: Use-after-free, double-free, state corruption

### Strategy 3: Amplification Variable Corruption

Target declaration zone variables:

```bash
# Extract and mutate declaration zone specifically
sed -n '/DECLARATION ZONE/,/SETUP ZONE/p' agent_outputs/mutation_b1_*.html | \
radamsa -m num,bf -n 50 - > decl_mutations.txt

# Recombine with original seed
# (requires custom script, see Automation Scripts section)
```

**Targets**:
- `const texSize = 256` → `const texSize = 999999999`
- `const bufferCount = 4` → `const bufferCount = -1`
- `const ARRAY_BUFFER = gl.ARRAY_BUFFER` → corrupted enum value

**Expected Bugs**: Heap corruption, memory exhaustion

### Strategy 4: Error Path Corruption

Remove or corrupt try-catch blocks:

```bash
# Remove try-catch to propagate errors
sed 's/try {//g; s/} catch(e) {}//g' agent_outputs/mutation_b1_s1_mrt_float_blend.html | \
radamsa -n 50 - -o fuzz_noerror_%n.html
```

**Expected Bugs**: Unhandled exceptions triggering corrupted state

### Strategy 5: Mixed Strategy (Recommended)

Use all mutation types with weighted probability:

```bash
# Balanced mutation profile
radamsa -m lr=2,num=2,bf=1,bd=1,bi=1,ls=1,ld=1 -n 1000 \
    agent_outputs/mutation_b*.html -o fuzz_%n.html
```

**Weights**:
- `lr=2` (line repeat): High weight for bind/enable thrashing
- `num=2` (numeric): High weight for buffer size/offset corruption
- Others: Standard weight for byte-level corruption

---

## Fuzzing Workflow

### Single-Seed Campaign

```bash
#!/bin/bash
# Single seed, 1000 mutations

SEED="agent_outputs/mutation_b1_s1_mrt_float_blend.html"
OUTPUT_DIR="fuzz_campaign_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

for i in {1..1000}; do
    # Generate mutation
    radamsa -s $i "$SEED" > "$OUTPUT_DIR/mutation_$i.html"

    # Test in browser (example using Firefox headless)
    timeout 10s firefox --headless --screenshot "$OUTPUT_DIR/mutation_$i.html" \
        > "$OUTPUT_DIR/mutation_$i.log" 2>&1

    # Check for crashes
    if [ $? -eq 139 ]; then
        echo "CRASH: mutation_$i.html" | tee -a "$OUTPUT_DIR/crashes.txt"
        cp "$OUTPUT_DIR/mutation_$i.html" "$OUTPUT_DIR/crashes/"
    fi
done
```

### Multi-Seed Rotation

```bash
#!/bin/bash
# Rotate through all 50 seeds

SEEDS=(agent_outputs/mutation_b*.html)
MUTATIONS_PER_SEED=100
OUTPUT_DIR="fuzz_rotation_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR/crashes"

for seed in "${SEEDS[@]}"; do
    seed_name=$(basename "$seed" .html)

    for i in $(seq 1 $MUTATIONS_PER_SEED); do
        mutation_file="$OUTPUT_DIR/${seed_name}_mut_$i.html"
        radamsa "$seed" > "$mutation_file"

        # Test with timeout
        timeout 5s firefox --headless "$mutation_file" 2>&1 | \
            grep -i "crash\|segfault\|error" && \
            cp "$mutation_file" "$OUTPUT_DIR/crashes/"
    done
done

echo "Campaign complete. Crashes in $OUTPUT_DIR/crashes/"
```

### Parallel Fuzzing

```bash
#!/bin/bash
# Parallel fuzzing with GNU parallel

CORES=$(nproc)
OUTPUT_DIR="fuzz_parallel_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR/crashes"

fuzz_one() {
    id=$1
    seed=$(shuf -n 1 -e agent_outputs/mutation_b*.html)
    mutation="$OUTPUT_DIR/mutation_$id.html"

    radamsa -s $id "$seed" > "$mutation"

    # Run in Firefox with sanitizers enabled
    ASAN_OPTIONS=detect_leaks=1 \
    timeout 5s firefox --headless "$mutation" 2>&1 | \
        tee "$OUTPUT_DIR/mutation_$id.log"

    if grep -qi "asan\|crash\|segfault" "$OUTPUT_DIR/mutation_$id.log"; then
        cp "$mutation" "$OUTPUT_DIR/crashes/"
        echo "CRASH: $id" >> "$OUTPUT_DIR/crashes.txt"
    fi
}

export -f fuzz_one
export OUTPUT_DIR

# Generate 10,000 mutations across all cores
seq 1 10000 | parallel -j $CORES fuzz_one {}

echo "Parallel fuzzing complete. Check $OUTPUT_DIR/crashes/"
```

---

## Crash Detection

### Method 1: Exit Code Monitoring

```bash
# Detect crashes by exit code (139 = SIGSEGV)
firefox --headless mutation.html
if [ $? -eq 139 ]; then
    echo "SEGFAULT detected"
fi
```

### Method 2: Log Pattern Matching

```bash
# Detect crashes in error output
firefox --headless mutation.html 2>&1 | grep -i "crash\|segfault\|assertion"
```

### Method 3: ASAN Integration

Build Firefox with AddressSanitizer:

```bash
# Run Firefox with ASAN
ASAN_OPTIONS="detect_leaks=1:abort_on_error=1:symbolize=1" \
firefox --headless mutation.html 2>&1 | tee asan.log

# Parse ASAN output
if grep -q "AddressSanitizer" asan.log; then
    echo "Memory error detected"
    # Extract crash info
    grep -A 20 "ERROR: AddressSanitizer" asan.log > crash_report.txt
fi
```

### Method 4: Playwright Crash Detection

Use the existing test infrastructure:

```bash
#!/bin/bash
# Leverage webgl_test_runner.py for crash detection

source venv/bin/activate

for mutation in fuzz_output/*.html; do
    timeout 10s python webgl_test_runner.py \
        --test-file "$mutation" \
        --browsers firefox \
        --output-dir crash_detection/

    # Check if test failed catastrophically
    json_result="${mutation%.html}.json"
    if [ ! -f "$json_result" ]; then
        echo "CRASH (no output): $mutation" >> crashes.txt
        cp "$mutation" crash_samples/
    fi
done
```

---

## Corpus Selection

### Strategy 1: Feature Coverage Rotation

Ensure all feature categories get fuzzing time:

```bash
#!/bin/bash
# Weighted corpus selection based on coverage gaps

declare -A weights=(
    ["b1"]=10  # Rendering pipeline
    ["b2"]=10
    ["b3"]=20  # Buffer operations (high value)
    ["b4"]=20
    ["b5"]=15  # Texture operations
    ["b6"]=15
    ["b7"]=10  # Shader features
    ["b8"]=10
    ["b9"]=25  # Sync/Query (high value, low coverage)
    ["b10"]=15 # Advanced features
)

# Select seed based on weights
select_weighted_seed() {
    batch=$(shuf -e $(for k in "${!weights[@]}"; do \
        for i in $(seq 1 ${weights[$k]}); do echo "$k"; done; done) -n 1)
    shuf -n 1 -e agent_outputs/mutation_${batch}_*.html
}

for i in {1..1000}; do
    seed=$(select_weighted_seed)
    radamsa "$seed" > "fuzz_weighted_$i.html"
done
```

### Strategy 2: Complexity-Based Selection

Prioritize seeds with high mutation density:

```bash
#!/bin/bash
# Select seeds by line count (proxy for complexity)

# Sort seeds by line count
find agent_outputs -name "mutation_b*.html" -exec wc -l {} \; | \
    sort -rn | awk '{print $2}' > seeds_by_complexity.txt

# Fuzz top 25% (most complex) more frequently
head -n 13 seeds_by_complexity.txt | while read seed; do
    radamsa -n 100 "$seed" -o "fuzz_complex_%n.html"
done

# Fuzz bottom 75% less frequently
tail -n 37 seeds_by_complexity.txt | while read seed; do
    radamsa -n 25 "$seed" -o "fuzz_simple_%n.html"
done
```

### Strategy 3: Error Path Focus

Prioritize seeds with many try-catch blocks:

```bash
#!/bin/bash
# Count try-catch blocks per seed

for seed in agent_outputs/mutation_b*.html; do
    count=$(grep -c "try {" "$seed")
    echo "$count $seed"
done | sort -rn | head -20 > high_error_path_seeds.txt

# Fuzz these seeds more aggressively
cat high_error_path_seeds.txt | awk '{print $2}' | while read seed; do
    radamsa -n 200 "$seed" -o "fuzz_errorpath_%n.html"
done
```

---

## Triaging and Minimization

### Step 1: Crash Deduplication

```bash
#!/bin/bash
# Deduplicate crashes by stack trace similarity

mkdir -p crash_buckets

for crash in crashes/*.html; do
    # Run with ASAN to get stack trace
    ASAN_OPTIONS="symbolize=1" firefox --headless "$crash" 2>&1 | \
        grep -A 10 "ERROR: AddressSanitizer" > "${crash%.html}.trace"

    # Extract crash location (first frame)
    crash_site=$(grep "^    #0" "${crash%.html}.trace" | head -1)

    # Bucket by crash site
    bucket=$(echo "$crash_site" | md5sum | cut -d' ' -f1)
    mkdir -p "crash_buckets/$bucket"
    cp "$crash" "crash_buckets/$bucket/"
done

# Report unique crashes
for bucket in crash_buckets/*; do
    count=$(ls "$bucket"/*.html 2>/dev/null | wc -l)
    [ $count -gt 0 ] && echo "Bucket $(basename $bucket): $count crashes"
done
```

### Step 2: Minimization with delta-debugging

```bash
#!/bin/bash
# Minimize crashing test case

minimize_crash() {
    crash_file=$1

    # Remove comments (if any)
    sed '/^\/\//d; /^\/\*/,/\*\//d' "$crash_file" > "${crash_file%.html}_nocomments.html"

    # Remove whitespace
    sed 's/^[[:space:]]*//; /^$/d' "${crash_file%.html}_nocomments.html" > \
        "${crash_file%.html}_minimal.html"

    # Test if still crashes
    timeout 5s firefox --headless "${crash_file%.html}_minimal.html" 2>&1 | \
        grep -qi "crash" && echo "Minimized: ${crash_file%.html}_minimal.html"
}

for crash in crash_buckets/*/*.html; do
    minimize_crash "$crash"
done
```

### Step 3: Automated Reduction

```python
#!/usr/bin/env python3
# Automated HTML test case reducer

import re
import subprocess
import sys

def test_crash(html_file):
    """Test if HTML file still crashes"""
    result = subprocess.run(
        ["timeout", "5s", "firefox", "--headless", html_file],
        capture_output=True,
        text=True
    )
    return "crash" in result.stderr.lower() or result.returncode == 139

def reduce_html(crash_file):
    """Iteratively reduce HTML while preserving crash"""
    with open(crash_file) as f:
        lines = f.readlines()

    # Try removing each line
    for i in range(len(lines)):
        test_lines = lines[:i] + lines[i+1:]
        test_file = f"{crash_file}.test"

        with open(test_file, 'w') as f:
            f.writelines(test_lines)

        if test_crash(test_file):
            print(f"Removed line {i}: {lines[i][:50]}")
            lines = test_lines
        else:
            subprocess.run(["rm", test_file])

    # Write minimal crash
    minimal_file = crash_file.replace(".html", "_minimal.html")
    with open(minimal_file, 'w') as f:
        f.writelines(lines)

    print(f"Reduced {len(lines)} lines -> {len(lines)} lines: {minimal_file}")
    return minimal_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} crash.html")
        sys.exit(1)

    reduce_html(sys.argv[1])
```

---

## Advanced Techniques

### Technique 1: Grammar-Aware Mutations

Preserve HTML/JS structure while mutating values:

```python
#!/usr/bin/env python3
# Grammar-aware WebGL mutation

import re
import random
import sys

def mutate_numeric_literals(html_content):
    """Mutate only numeric literals in gl.* calls"""
    def replace_number(match):
        num = int(match.group(1))
        mutations = [
            num * 2,
            num - 1,
            -num,
            0,
            0x7FFFFFFF,
            num + random.randint(-100, 100)
        ]
        return str(random.choice(mutations))

    pattern = r'\bgl\.[a-zA-Z]+\([^)]*?(\d+)[^)]*?\)'
    return re.sub(pattern, replace_number, html_content)

def mutate_enum_constants(html_content):
    """Corrupt enum constant definitions"""
    pattern = r'(const\s+\w+\s*=\s*gl\.)([A-Z_]+)'

    def replace_enum(match):
        # Replace with different WebGL enum
        enums = ['ARRAY_BUFFER', 'ELEMENT_ARRAY_BUFFER', 'TEXTURE_2D',
                 'FRAMEBUFFER', 'RENDERBUFFER', 'VERTEX_SHADER']
        return match.group(1) + random.choice(enums)

    return re.sub(pattern, replace_enum, html_content)

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        html = f.read()

    html = mutate_numeric_literals(html)
    html = mutate_enum_constants(html)

    print(html)
```

### Technique 2: Cross-Seed Splicing

Combine fragments from different seeds:

```bash
#!/bin/bash
# Splice declaration zones between seeds

splice_seeds() {
    seed1=$1
    seed2=$2
    output=$3

    # Extract declaration zone from seed1
    sed -n '/DECLARATION ZONE/,/SETUP ZONE/p' "$seed1" > /tmp/decl1.txt

    # Extract setup+execution from seed2
    sed -n '/SETUP ZONE/,$p' "$seed2" > /tmp/setup2.txt

    # Combine
    cat /tmp/decl1.txt /tmp/setup2.txt > "$output"
}

# Generate 100 spliced mutations
for i in {1..100}; do
    seed1=$(shuf -n 1 -e agent_outputs/mutation_b*.html)
    seed2=$(shuf -n 1 -e agent_outputs/mutation_b*.html)
    splice_seeds "$seed1" "$seed2" "fuzz_spliced_$i.html"
done
```

### Technique 3: Stacked Mutations

Apply multiple mutation strategies sequentially:

```bash
#!/bin/bash
# Multi-stage mutation pipeline

SEED="agent_outputs/mutation_b1_s1_mrt_float_blend.html"

# Stage 1: Numeric fuzzing
radamsa -m num "$SEED" > /tmp/stage1.html

# Stage 2: Line repetition
radamsa -m lr /tmp/stage1.html > /tmp/stage2.html

# Stage 3: Byte-level corruption
radamsa -m bf,bd /tmp/stage2.html > final_mutation.html

echo "Stacked mutation complete: final_mutation.html"
```

---

## Automation Scripts

### Complete Fuzzing Harness

```bash
#!/bin/bash
# production_fuzz.sh - Complete fuzzing automation

set -euo pipefail

# Configuration
CORPUS_DIR="agent_outputs"
OUTPUT_BASE="fuzz_runs"
MUTATIONS_PER_SEED=1000
TIMEOUT=10
BROWSERS="firefox"

# Create output directory
RUN_ID="run_$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="$OUTPUT_BASE/$RUN_ID"
mkdir -p "$OUTPUT_DIR"/{mutations,crashes,logs}

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$OUTPUT_DIR/fuzzing.log"
}

# Crash detection
detect_crash() {
    local mutation=$1
    local log_file=$2

    # Check exit code
    local exit_code=$?
    [ $exit_code -eq 139 ] && return 0

    # Check log for crash indicators
    grep -qi "crash\|segfault\|asan\|assertion" "$log_file" && return 0

    return 1
}

# Main fuzzing loop
log "Starting fuzzing campaign: $RUN_ID"
log "Corpus: $CORPUS_DIR"
log "Mutations per seed: $MUTATIONS_PER_SEED"

total_mutations=0
total_crashes=0

for seed in "$CORPUS_DIR"/mutation_b*.html; do
    seed_name=$(basename "$seed" .html)
    log "Fuzzing seed: $seed_name"

    for i in $(seq 1 $MUTATIONS_PER_SEED); do
        mutation_file="$OUTPUT_DIR/mutations/${seed_name}_${i}.html"
        log_file="$OUTPUT_DIR/logs/${seed_name}_${i}.log"

        # Generate mutation
        radamsa -m lr=2,num=2,bf=1,bd=1 "$seed" > "$mutation_file"

        # Test mutation
        timeout $TIMEOUT firefox --headless "$mutation_file" \
            > "$log_file" 2>&1 || true

        # Check for crash
        if detect_crash "$mutation_file" "$log_file"; then
            log "CRASH DETECTED: ${seed_name}_${i}"
            cp "$mutation_file" "$OUTPUT_DIR/crashes/"
            cp "$log_file" "$OUTPUT_DIR/crashes/${seed_name}_${i}.log"
            ((total_crashes++))
        fi

        ((total_mutations++))

        # Progress update every 100 mutations
        if [ $((total_mutations % 100)) -eq 0 ]; then
            log "Progress: $total_mutations mutations, $total_crashes crashes"
        fi
    done
done

log "Fuzzing campaign complete"
log "Total mutations: $total_mutations"
log "Total crashes: $total_crashes"
log "Crash rate: $(echo "scale=2; $total_crashes * 100 / $total_mutations" | bc)%"
log "Results: $OUTPUT_DIR"
```

### Continuous Fuzzing Service

```bash
#!/bin/bash
# continuous_fuzz.sh - Run fuzzing campaigns continuously

CAMPAIGN_DURATION=3600  # 1 hour per campaign
CORPUS_DIR="agent_outputs"

while true; do
    echo "Starting new fuzzing campaign ($(date))"

    # Run fuzzing campaign
    ./production_fuzz.sh

    # Wait for campaign duration
    sleep $CAMPAIGN_DURATION

    # Deduplicate crashes
    ./deduplicate_crashes.sh

    # Report statistics
    ./report_statistics.sh
done
```

---

## Conclusion

This guide provides comprehensive strategies for using radamsa with the mutation-optimized WebGL2 corpus. The corpus is specifically designed to maximize the effectiveness of radamsa's mutation strategies:

- **Line repetition patterns** trigger driver state corruption
- **Numeric literals** enable buffer/texture size fuzzing
- **Try-catch blocks** allow error accumulation
- **Amplification variables** create cascading mutations

**Recommended Starting Point**:
1. Run single-seed campaign (1000 mutations) with Strategy 5 (Mixed)
2. Monitor crash rate and adjust mutation weights
3. Scale to multi-seed rotation with parallel fuzzing
4. Implement crash deduplication and minimization
5. Continuously fuzz with automated triaging

**Expected Results**:
- Crash rate: 0.01% - 1% (depends on driver implementation)
- Unique bugs: 5-20 per 100,000 mutations (typical for mature drivers)
- High-severity bugs: UAF, heap corruption, OOB access

For questions or issues, refer to:
- `docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md`
- `docs/MUTATION_SEEDS_COMPLETION_SUMMARY.md`
- `CLAUDE.md`
