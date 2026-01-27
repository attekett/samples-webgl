# Corpus Enhancement Plan - Round [N]

**Date**: [YYYY-MM-DD]
**Current Corpus**: [X] seeds
**Target Corpus**: [X+25] seeds
**Purpose**: Address feature coverage gaps

---

## Coverage Gap Analysis

[Paste output from ./scripts/feature_matrix.sh here]

### Identified Gaps (< 20% coverage)

- **[Feature 1]**: Current [X]% → Target [Y]%
- **[Feature 2]**: Current [X]% → Target [Y]%
- **[Feature 3]**: Current [X]% → Target [Y]%

---

## New Seed Specifications

### Batch [N]: [Feature Focus] (5 seeds)

#### 1. mutation_b[N]_s[ID]_[descriptive_name].html

**Features**:
- Primary: [Main WebGL2 feature to exercise]
- Secondary: [Additional features]

**Amplification Variables** (4-6 variables):
```javascript
const texSize = 256;
const bufferSize = 1024;
const vertexCount = 36;
const instanceCount = 4;
```

**Enum Constants** (4-6 variables):
```javascript
const ARRAY_BUFFER = gl.ARRAY_BUFFER;
const TEXTURE_2D = gl.TEXTURE_2D;
const TRIANGLES = gl.TRIANGLES;
```

**Line Repetition Patterns**:
- [ ] Bind ping-pong (2-4 redundant binds)
- [ ] Enable/disable thrashing (3-5 state toggles)
- [ ] Resource creation redundancy (2-3 redundant creates)
- [ ] FBO attachment swapping (if applicable)
- [ ] Deletion and reuse patterns

**Try-Catch Blocks**: 6-12 blocks

**Extensions Required**: [List or "None"]

**Expected Mutation Targets**: ~60

---

#### 2. mutation_b[N]_s[ID]_[descriptive_name].html

[Repeat structure for each seed]

---

## Implementation Notes

### Variable Scoping
- Declare all WebGL objects with `let` in Declaration Zone
- Assign (not declare) inside try-catch blocks
- Example:
```javascript
let buffer, texture, framebuffer;

try {
    buffer = gl.createBuffer();
} catch(e) { console.log(e); }
```

### Extension Handling
- Check UNSUPPORTED.md before using extensions
- Only use widely-supported extensions
- Add extension availability check:
```javascript
const REQUIRED_EXTENSIONS = ['EXT_color_buffer_float'];
const missingExtensions = REQUIRED_EXTENSIONS.filter(ext => !gl.getExtension(ext));
if (missingExtensions.length > 0) {
    throw new Error(`UNSUPPORTED_EXTENSIONS: ${missingExtensions.join(', ')}`);
}
```

### Quality Checklist
- [ ] Three-zone architecture (Declaration/Setup/Execution)
- [ ] 4-6 amplification variables
- [ ] 4-6 enum constants
- [ ] 6-12 try-catch blocks with console.log(e)
- [ ] 20-40 inline numeric literals
- [ ] All line repetition patterns implemented
- [ ] No unsupported extensions
- [ ] 256x256 canvas resolution
- [ ] WebGL2 context required

---

## Success Metrics

**Primary**:
- [ ] All [N] seeds passing validation (100%)
- [ ] Target coverage achieved for gap categories
- [ ] Mutation density maintained at 1 target per 3-4 lines

**Secondary**:
- [ ] No extension-related failures
- [ ] No variable scoping errors
- [ ] First-pass success rate 95%+
- [ ] All seeds complete in < 5 seconds

---

## Implementation Timeline

1. **Phase 1: Parallel Creation** (30-40 min)
   - Launch [N] parallel agents
   - Each agent creates [X] seeds

2. **Phase 2: Sequential Validation** (~5 min)
   - Test all new seeds with run_tests.sh
   - Identify failures

3. **Phase 3: Fix and Finalize** (10-15 min)
   - Fix any failures
   - Strip console.log statements
   - Re-validate

4. **Phase 4: Commit** (5 min)
   - Update documentation
   - Commit and push to remote

**Total Estimated Time**: ~1 hour
