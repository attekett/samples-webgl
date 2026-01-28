# Radamsa Mutation Analysis for WebGL Corpus

**Date**: 2026-01-28
**Corpus**: 259 seeds, mutation-optimized architecture
**Purpose**: Analyze how Radamsa mutators exploit our corpus design

---

## Executive Summary

Our corpus architecture is **specifically optimized** for Radamsa's mutation strategies. The three-zone structure, variable tiers, line repetition patterns, and error path exploitation create ideal targets for Radamsa's 30+ mutators.

**Key Synergies**:
- Line mutators (lr, ld, ls, lp) ↔ Extensive line repetition patterns
- Numeric mutators (num, bei, bed) ↔ Multi-tier variable exposure
- Tree mutators (td, tr, ts) ↔ Complex state machine structure
- Smart mutators (ft, fn, fo) ↔ Similar code block patterns

---

## Radamsa Mutator Categories

### 1. Byte-Level Mutators

| Mutator | Description | Corpus Targets | Expected Bugs |
|---------|-------------|----------------|---------------|
| **bd** | Drop a byte | Enum constants, numeric literals | Invalid enum values, corrupted numbers |
| **bf** | Flip one bit | gl.TEXTURE_2D → invalid, buffer sizes | Bit-flip vulnerabilities, off-by-one |
| **bi** | Insert random byte | Between digits in numbers | Parse errors, malformed literals |
| **br** | Repeat a byte | "128" → "1288", "gl.RGBA8" → "gl.RGBA88" | Buffer overflows, invalid enums |
| **bp** | Permute bytes | "256" → "652", enum value corruption | Logic errors, invalid parameters |
| **bei** | Increment byte by one | gl.TEXTURE_2D (0x0DE1) → 0x0DE2 | Invalid enum exploration, edge cases |
| **bed** | Decrement byte by one | Buffer size 1024 → 1023 | Off-by-one errors, alignment issues |
| **ber** | Swap byte with random | Random enum/number corruption | Unexpected parameter combinations |

**Architecture Synergy**:
- **Tier 2 variables** (30-60 inline literals per seed) = 30-60 mutation targets
- **Tier 3 variables** (9-15 enum constants) = high-value targets
- **bei/bed** are perfect for exploring WebGL enum boundaries

**Example Mutations**:
```javascript
// Original
const numLayers = 128;
gl.texStorage3D(gl.TEXTURE_2D_ARRAY, 1, gl.RGBA8, 256, 256, 128);

// bei mutation (increment byte)
const numLayers = 129;  // Off-by-one
gl.texStorage3D(gl.TEXTURE_2D_ARRAY, 1, gl.RGBA9, 256, 256, 128);  // Invalid format

// bed mutation (decrement byte)
const numLayers = 127;  // Mismatch
gl.texStorage3D(gl.TEXTURE_2D_ARRAY, 1, gl.RGBA7, 256, 256, 128);  // Invalid format

// br mutation (repeat byte)
const numLayers = 1288;  // Massive allocation
```

---

### 2. Sequence Mutators

| Mutator | Description | Corpus Targets | Expected Bugs |
|---------|-------------|----------------|---------------|
| **sr** | Repeat sequence of bytes | Line repetition patterns, loop bodies | Amplified resource allocation, OOM |
| **sd** | Delete sequence of bytes | Multi-line operations, setup sequences | Incomplete state, missing operations |

**Architecture Synergy**:
- **Line repetition patterns** (64-256 loop iterations) are PERFECT targets
- **sr** will amplify already-extensive repetition
- **sd** can delete critical setup sequences

**Example Mutations**:
```javascript
// Original: 128 iterations
for (let i = 0; i < 128; i++) {
    gl.bindTexture(gl.TEXTURE_2D, textures[i]);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
}

// sr mutation (repeat sequence) - amplifies to 256 or 512 iterations
for (let i = 0; i < 256; i++) {  // Radamsa doubled the iteration count
    gl.bindTexture(gl.TEXTURE_2D, textures[i]);  // Array overflow!
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
}

// sd mutation (delete sequence) - removes critical lines
for (let i = 0; i < 128; i++) {
    // gl.bindTexture line DELETED by sd
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    // Operates on wrong texture target!
}
```

---

### 3. Line Mutators (CRITICAL)

| Mutator | Description | Corpus Targets | Expected Bugs |
|---------|-------------|----------------|---------------|
| **ld** | Delete a line | Setup code, cleanup code | Incomplete state, resource leaks |
| **lds** | Delete many lines | Entire setup blocks | Massive state corruption |
| **lr2** | Duplicate a line | Resource allocation, binding | Double allocation, leaks |
| **li** | Copy line closeby | Similar operations | Unintended duplication |
| **lr** | Repeat a line | Any line (amplification) | Excessive operations, OOM |
| **ls** | Swap two lines | Setup order, state transitions | Broken assumptions, use-before-init |
| **lp** | Swap order of lines | Block reordering | State machine corruption |
| **lis** | Insert line from elsewhere | Cross-function injection | Logic errors, type mismatches |
| **lrs** | Replace line with another | Substitute operations | Incompatible operations |

**Architecture Synergy**:
- **THIS IS WHY WE HAVE EXTENSIVE LINE REPETITION**
- Our seeds have 200-350 lines with MANY repeated patterns
- Layer/slice iteration loops provide dense mutation targets
- Line swapping breaks carefully ordered state machine transitions

**Example Mutations**:
```javascript
// Original (correct order)
const fbo = gl.createFramebuffer();
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
const tex = gl.createTexture();
gl.bindTexture(gl.TEXTURE_2D, tex);
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);

// ls mutation (swap two lines) - BREAKS STATE MACHINE
const fbo = gl.createFramebuffer();
const tex = gl.createTexture();  // SWAPPED with bindFramebuffer
gl.bindTexture(gl.TEXTURE_2D, tex);
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);  // SWAPPED - FBO not bound during texture creation
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);

// ld mutation (delete line) - CREATES RESOURCE LEAK
const fbo = gl.createFramebuffer();
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
const tex = gl.createTexture();
// gl.bindTexture line DELETED
gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 256, 256, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
// Operates on WRONG texture (whatever was previously bound)!

// lr2 mutation (duplicate line) - RESOURCE LEAK
const fbo = gl.createFramebuffer();
const fbo = gl.createFramebuffer();  // DUPLICATED - first FBO leaked!
gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);  // Binds second FBO, first is unreachable
```

---

### 4. Tree Mutators (AST-Level)

| Mutator | Description | Corpus Targets | Expected Bugs |
|---------|-------------|----------------|---------------|
| **td** | Delete a node | Function calls, expressions | Missing operations, incomplete state |
| **tr2** | Duplicate a node | Code blocks, functions | Double operations, leaks |
| **ts1** | Swap one node with another | Operation substitution | Type mismatches, logic errors |
| **ts2** | Swap two nodes pairwise | Parallel operations | Reordered effects |
| **tr** | Repeat a path of parse tree | Control flow duplication | Excessive operations |

**Architecture Synergy**:
- Works at JavaScript AST level (more sophisticated than line-based)
- Can duplicate/delete entire try-catch blocks
- Can swap function call arguments

**Example Mutations**:
```javascript
// Original
try {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
} catch (e) {}

// td mutation (delete node) - Removes function call
try {
    // gl.bindFramebuffer call DELETED at AST level
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    // Operates on wrong FBO!
} catch (e) {}

// tr2 mutation (duplicate node) - Duplicates try-catch block
try {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
} catch (e) {}
try {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);  // DUPLICATED
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
} catch (e) {}

// ts1 mutation (swap nodes) - Swaps function arguments
gl.framebufferTexture2D(gl.FRAMEBUFFER, tex, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, 0);
// Arguments in WRONG ORDER - type mismatch!
```

---

### 5. Numeric Mutators (HIGH VALUE)

| Mutator | Description | Corpus Targets | Expected Bugs |
|---------|-------------|----------------|---------------|
| **num** | Modify textual numbers | All numeric literals | Integer overflows, OOM, invalid ranges |

**Architecture Synergy**:
- **Tier 1 amplification variables** (8-12 per seed) are PRIMARY targets
- These control loop counts, buffer sizes, texture dimensions
- **CRITICAL**: num mutator is DEFAULT enabled with weight=5

**Example Mutations**:
```javascript
// Original
const numLayers = 128;
const texSize = 256;
const bufferSize = numLayers * texSize * texSize * 4;

// num mutation possibilities
const numLayers = 12800;  // 100x amplification → massive memory allocation
const numLayers = -128;   // Negative → undefined behavior
const numLayers = 0;      // Zero → division by zero, empty loops
const numLayers = 2147483647;  // INT_MAX → integer overflow

const texSize = 25600;  // 100x → 25600×25600 texture (exceeds MAX_TEXTURE_SIZE)
const bufferSize = 999999999;  // Direct large value → OOM

// Propagation through coupled resources
const numLayers = 256;  // Changed
const texSize = 256;    // Unchanged
const bufferSize = numLayers * texSize * texSize * 4;  // Now 2x expected size
// But texture array only has 128 layers → buffer overflow when writing!
```

---

### 6. Unicode/String Mutators

| Mutator | Description | Corpus Targets | Expected Bugs |
|---------|-------------|----------------|---------------|
| **uw** | Make code point too wide | Shader strings, uniform names | Parser errors, encoding issues |
| **ui** | Insert funny unicode | Shader source, variable names | Lexer/parser bugs |
| **ab** | ASCII handling issues | Shader strings | String processing bugs |

**Architecture Synergy**:
- Less relevant for numeric WebGL code
- Might corrupt shader source strings
- Could affect uniform/attribute names

**Example Mutations**:
```javascript
// Original
const vertexShader = `
    attribute vec4 position;
    void main() {
        gl_Position = position;
    }
`;

// ui mutation (insert unicode)
const vertexShader = `
    attribute vec4 posit️ion;  // Inserted zero-width joiner
    void main() {
        gl_Position = position;  // Name mismatch!
    }
`;

// uw mutation (wide code point)
const uniformName = "modelMatrix\uFFFD";  // Replacement character
gl.getUniformLocation(program, uniformName);  // Lookup fails
```

---

### 7. Smart Mutators (SOPHISTICATED)

| Mutator | Description | Corpus Targets | Expected Bugs |
|---------|-------------|----------------|---------------|
| **ft** | Jump to similar position in block | Repeated patterns | Block-level corruption |
| **fn** | Clone data between similar positions | Line repetition loops | Sophisticated duplication |
| **fo** | Fuse previously seen data elsewhere | Across seeds | Cross-seed patterns |

**Architecture Synergy**:
- **ft/fn** will find our extensive line repetition patterns
- **fo** can inject patterns from other seeds (cross-pollination)
- These are the "smart" mutators that understand structure

**Example Mutations**:
```javascript
// Original seed A
for (let i = 0; i < 128; i++) {
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, texArray);
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, 256, 256, 1, gl.RGBA, gl.UNSIGNED_BYTE, data);
}

// Original seed B (different file)
for (let i = 0; i < 64; i++) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbos[i]);
    gl.clear(gl.COLOR_BUFFER_BIT);
}

// ft mutation (jump to similar position) - finds loop pattern, jumps mid-loop
for (let i = 0; i < 128; i++) {
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, texArray);
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, 256, 256, 1, gl.RGBA, gl.UNSIGNED_BYTE, data);
}
// JUMP: Execution continues from middle of loop
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, 256, 256, 1, gl.RGBA, gl.UNSIGNED_BYTE, data);
}  // Unbalanced braces, corrupted control flow

// fo mutation (fuse from seed B into seed A)
for (let i = 0; i < 128; i++) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbos[i]);  // FUSED from seed B
    gl.clear(gl.COLOR_BUFFER_BIT);                // FUSED from seed B
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, 256, 256, 1, gl.RGBA, gl.UNSIGNED_BYTE, data);
}
// Binds FBO but then writes to texture array → wrong target!
```

---

### 8. XML Mutator

| Mutator | Description | Corpus Targets | Expected Bugs |
|---------|-------------|----------------|---------------|
| **xp** | Parse as XML and mutate | HTML structure | Minimal impact |

**Architecture Synergy**:
- Low relevance for JavaScript/WebGL code
- Might occasionally trigger on HTML boilerplate
- Default weight is high (9) but limited applicability

---

## Mutation Patterns

### Pattern: od (Mutate Once)
- Single mutation per seed
- Good for isolating specific bug triggers
- Lower noise-to-signal ratio

### Pattern: nd (Mutate Many Times)
- Multiple mutations in sequence
- **Cascading failures** - one mutation enables another
- Can create complex bug conditions

**Example**:
```javascript
// Original
const numLayers = 128;
const bufferSize = numLayers * 256 * 256 * 4;
for (let i = 0; i < numLayers; i++) {
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, 256, 256, 1, gl.RGBA, gl.UNSIGNED_BYTE, buffer);
}

// nd pattern (multiple mutations)
const numLayers = 256;  // Mutation 1: num doubles value
const bufferSize = numLayers * 256 * 256 * 4;
for (let i = 0; i < numLayers; i++) {
    // Mutation 2: ld deletes bindTexture line
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, 256, 256, 1, gl.RGBA, gl.UNSIGNED_BYTE, buffer);
}
// Mutation 1 causes loop to exceed texture array size (128 layers)
// Mutation 2 causes operations on wrong texture
// Combined: buffer overflow on wrong target!
```

### Pattern: bu (Closeby Mutations)
- Clusters mutations in same region
- Corrupts entire code sections
- Can completely break subsystems

---

## Default Radamsa Configuration

```
[ft=2, fo=2, fn, num=5, ld, lds, lr2, li, ls, lp, lr, lis, lrs,
 sr, sd, bd, bf, bi, br, bp, bei, bed, ber, uw, ui=2, xp=9, ab]
```

**Weighted mutators** (higher probability):
- **num=5**: Numeric mutations (CRITICAL for our corpus)
- **xp=9**: XML parsing (low relevance for us)
- **ft=2, fo=2, ui=2**: Smart mutators and unicode (moderate)

**Implications for our corpus**:
- Numeric mutations will dominate (num=5) - PERFECT for amplification variables
- Line mutations are all enabled - PERFECT for line repetition patterns
- Byte mutations are all enabled - PERFECT for enum/literal corruption

---

## Corpus Architecture → Mutation Surface Mapping

| Corpus Feature | Mutation Targets | Key Mutators | Bug Classes |
|----------------|------------------|--------------|-------------|
| **Tier 1 Amplification Variables** (8-12/seed) | Loop counts, buffer sizes, dimensions | num, bei, bed | Integer overflow, OOM, buffer overflow |
| **Tier 2 Inline Literals** (30-60/seed) | WebGL parameters, sizes, formats | num, bei, bed, bei, br | Invalid parameters, alignment errors |
| **Tier 3 Enum Constants** (9-15/seed) | gl.TEXTURE_2D, gl.RGBA8, etc. | bei, bed, ber, bf | Invalid enum values, format mismatches |
| **Line Repetition** (64-256 iterations/seed) | Loop bodies, resource allocation | lr, sr, ld, ls, lp | Amplified allocation, state corruption |
| **Try-Catch Blocks** (13-21/seed) | Error handling boundaries | td, ld, lds | Unhandled exceptions, control flow errors |
| **State Machine Transitions** (bind/unbind, enable/disable) | Operation ordering | ls, lp, ld, td | Use-before-init, invalid state transitions |
| **Resource Coupling** (shared buffers/textures) | Cross-resource dependencies | num, ls, ld | Cascading failures, use-after-free |

---

## Expected Bug Categories from Mutations

### 1. Memory Safety Bugs
**Caused by**: num (amplification), br (repeat), sr (sequence repeat)
- Buffer overflows (numLayers mutation)
- Out-of-bounds access (array index corruption)
- Use-after-free (resource coupling + line deletion)
- Memory leaks (lr2 duplicating allocation, ld deleting cleanup)
- OOM (massive amplification of allocation loops)

### 2. State Machine Bugs
**Caused by**: ls (line swap), lp (line permutation), ld (line deletion)
- Invalid state transitions (bind order corruption)
- Use-before-initialization (swapped setup order)
- Missing operations (deleted setup steps)
- Incomplete state (lds deleting entire blocks)
- Resource conflicts (wrong binding context)

### 3. Integer Overflow Bugs
**Caused by**: num, bei, br
- Signed overflow (numLayers = INT_MAX)
- Unsigned underflow (size - 1 when size = 0)
- Multiplication overflow (width * height * depth)
- Division by zero (num → 0 mutation)
- Negative indices (num → negative)

### 4. API Misuse Bugs
**Caused by**: bei/bed (enum corruption), ts1 (argument swap), ld (missing calls)
- Invalid enum values (gl.RGBA8 + 1)
- Wrong argument types (swapped parameters)
- Missing required calls (deleted glBindTexture)
- Incompatible formats (enum corruption)
- Incorrect parameter combinations

### 5. Resource Management Bugs
**Caused by**: ld (delete cleanup), lr2 (duplicate allocation), ls (swap create/delete)
- Resource leaks (deleted cleanup, duplicated allocation)
- Double-free (duplicated delete operations)
- Use-after-delete (swapped delete/use order)
- Handle corruption (resource ID reuse)
- Exhaustion (amplified allocation without cleanup)

---

## Optimization Recommendations

### Radamsa Flags for Maximum Effectiveness

```bash
# Maximize numeric mutations (our corpus's strength)
radamsa -m num=10,bei=3,bed=3,lr=3,ld=3,ls=3,sr=2,fo=2,ft=2 \
        -p nd \  # Multiple mutations per seed
        -n 10000 \  # Generate 10,000 mutations per seed
        -o mutations/%n.html \
        agent_outputs/mutation_b*.html
```

**Rationale**:
- **num=10**: Amplify numeric mutations (our Tier 1 variables)
- **bei=3, bed=3**: Increase enum corruption (Tier 3 variables)
- **lr=3, ld=3, ls=3**: Amplify line mutations (our repetition patterns)
- **sr=2**: Sequence repetition (amplify our loops)
- **fo=2, ft=2**: Smart mutators (cross-seed patterns)
- **nd pattern**: Multiple mutations → cascading failures

### Alternative: Focused Campaigns

**Campaign 1: Memory Safety**
```bash
radamsa -m num=15,br=5,sr=5,bei=3 -p nd -n 5000 ...
# Focus on amplification and repetition
```

**Campaign 2: State Machine**
```bash
radamsa -m ls=10,lp=5,ld=5,lds=3 -p bu -n 5000 ...
# Focus on line reordering and deletion
```

**Campaign 3: API Misuse**
```bash
radamsa -m bei=10,bed=10,ber=5,ts1=5 -p od -n 5000 ...
# Focus on enum corruption and argument swapping
```

---

## Try-Catch Block Strategy

Our seeds have **13-21 try-catch blocks per seed** (avg: ~16).

**Purpose**:
- Catch mutations that cause JavaScript exceptions
- Allow fuzzer to continue executing even with corrupted code
- Mutations still stress WebGL driver even if caught

**Example**:
```javascript
try {
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, texArray);
} catch (e) {}  // Catches if texArray is null (deleted by ld)

try {
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, 256, 256, 1, gl.RGBA, gl.UNSIGNED_BYTE, data);
} catch (e) {}  // Catches if parameters are invalid (corrupted by num)
```

**Even when caught**:
- WebGL driver still processed invalid state
- Driver may have partial state corruption
- Subsequent operations may trigger bugs
- Error paths in driver are exercised

---

## Monitoring and Detection

### What to Monitor During Fuzzing

**Browser Crashes**:
- Segmentation faults in WebGL driver
- GPU process crashes
- Renderer process crashes

**Memory Issues**:
- OOM conditions
- Memory leaks (growing RSS)
- GPU memory exhaustion

**Hangs**:
- Infinite loops (num → 0 in loop condition)
- Deadlocks (resource contention)
- GPU hangs (driver lockup)

**Undefined Behavior**:
- ASAN/MSAN/UBSAN findings
- Valgrind errors
- Race conditions (ThreadSanitizer)

**Performance Anomalies**:
- Excessive execution time (amplification)
- High CPU usage (tight loops)
- High GPU usage (massive draws)

---

## Corpus Quality Metrics for Radamsa

| Metric | Value | Impact on Fuzzing |
|--------|-------|-------------------|
| Total seeds | 259 | Large mutation space |
| Avg lines per seed | ~260 | Dense mutation targets |
| Avg try-catch per seed | ~16 | High error resilience |
| Tier 1 variables per seed | 8-12 | Prime num mutation targets |
| Tier 2 literals per seed | 30-60 | Extensive byte mutation surface |
| Tier 3 enums per seed | 9-15 | Enum corruption targets |
| Line repetition iterations | 64-256 | lr/sr amplification targets |
| Feature combinations (2-way) | 100% coverage | Diverse code paths |
| Feature combinations (3-way) | 99% coverage | Complex interactions |

**Estimated Mutation Space**:
- Single seed: ~260 lines × 30+ mutators = ~7,800 mutation points
- Full corpus: 259 seeds × 7,800 = **~2,000,000 mutation points**
- With nd pattern (multi-mutation): **Virtually infinite**

---

## Conclusion

Our corpus architecture is **exceptionally well-suited** for Radamsa mutation fuzzing:

✅ **Extensive line repetition** → Perfect targets for lr, ld, ls, lp, sr mutators
✅ **Multi-tier variable exposure** → Optimal num, bei, bed mutation surface
✅ **Complex state machines** → Line swapping breaks assumptions
✅ **High error resilience** (try-catch) → Fuzzer continues despite mutations
✅ **Resource coupling** → Mutations propagate across subsystems
✅ **259 diverse seeds** → Large mutation space
✅ **~60,000 lines of code** → Dense mutation surface
✅ **Complete 2-way/3-way coverage** → All interaction paths represented

**Expected Outcome**: High-quality crashes, memory safety bugs, state machine vulnerabilities, and API misuse patterns discovered through systematic mutation-based exploration.

**Ready for production fuzzing campaign** with Radamsa or similar mutation-based fuzzers.
