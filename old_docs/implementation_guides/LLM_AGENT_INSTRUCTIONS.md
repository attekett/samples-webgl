# WebGPU Fuzzing Test Case Creation Instructions

## Core Mission
Create **fuzzable WebGPU test cases** that systematically increase coverage of the WebGPU specification while producing visually interesting outputs. Test cases must be **minimalist, self-contained, and machine-parseable** for mutation-based fuzzing, while demonstrating advanced WebGPU features through complex visual demos.

## Prerequisites
- **Read CONTRIBUTING_LLM.md thoroughly** - understand the fuzzing-first mentality
- **Review TODO.md** - identify under-tested features and edge cases
- **Examine existing test cases** in `amd/`, `examples/`, and `testcases/` directories
- **Study WebGPU specification** for accurate feature implementation

## Test Case Requirements

### Technical Constraints
- **Self-contained HTML file** - no external dependencies, libraries, or resources
- **No user interaction** required - demos run automatically on page load
- **256x256 canvas** (standard test resolution)
- **No console logging** - test runner captures all necessary information
- **No code comments** - code must be self-documenting
- **Simple structures** - avoid complex classes, verbose patterns, or abstractions
- **Fuzzing-friendly** - inline some values, parameterize others for mutation testing

### Visual Output
- **Complex visual demo** as primary validation method
- **Deterministic output** for reliable testing
- **Feature demonstration** through visual results (not just API calls)
- **Edge case coverage** that produces visible differences

## Development Workflow

### Step 1: Feature Selection
1. **Consult TODO.md** - identify under-covered features or edge cases
2. **Check existing coverage** in README.md project structure
3. **Select target feature** - focus on one specific WebGPU capability
4. **Plan visual demonstration** - how will the feature's behavior be made visible?

### Step 2: Directory and Naming
- **Output directory**: Output files to `agent_outputs/` and leave them there.
- **Naming convention**: `category_feature_description.html` (snake_case, descriptive)

### Step 3: Implementation Guidelines

#### WebGPU Setup (Required Boilerplate)
```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgpu-canvas" width="256" height="256"></canvas>
<script>
async function main() {
    if (!navigator.gpu) throw new Error("WebGPU not supported");
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) throw new Error("No GPUAdapter found");
    const device = await adapter.requestDevice();

    const canvas = document.getElementById('webgpu-canvas');
    const context = canvas.getContext('webgpu');
    const format = navigator.gpu.getPreferredCanvasFormat();
    context.configure({ device, format });

    // Your implementation here
}
main().catch(err => { throw err; });
</script>
</body>
</html>
```

#### Feature Implementation
- **Direct WebGPU API usage** - no helper libraries
- **WGSL shaders embedded as template literals** - no external shader files
- **Resource creation with explicit parameters** - mix inline values and variables for fuzzing
- **Error handling through exceptions** - let test runner capture validation errors

#### Fuzzing Optimization
- **Inline critical values**: `device.createBuffer({ size: 1024, usage: GPUBufferUsage.STORAGE })`
- **Parameterize variation points**: `const workgroupSize = 8;`
- **Avoid magic numbers without context**
- **Simple control flow** - prefer linear execution over complex branching

### Step 4: Validation Process

#### Automated Testing
```bash
# Test with Chromium (most feature-complete)
./run_tests.sh --test-file amd/your_test.html --browsers chromium

```

#### Result Validation
- **Check JSON output** for your test file (created automatically)
- **Required success criteria**:
  - `"passed": true`
  - `"console_logs": []` (no warnings/errors)
  - `"javascript_errors": []` (empty array)
  - `"webgpu_errors": []` (empty array)
  - `"errors": []` (empty array)

#### Iterative Fixing
- **If warnings/errors exist**: Fix the code and re-run tests
- **No compromises**: Remove test case if it cannot pass cleanly
- **Verify fixes work**: Never assume - always re-run validation

### Step 5: Documentation Updates
After successful validation:
1. **Update README.md test counts** in the project structure section
2. **Ensure feature coverage** is accurately reflected
3. **Verify no external files** were created or required

## Quality Standards

### Code Quality
- **Machine-readable**: Simple, consistent patterns for fuzzing tools
- **Self-documenting**: Clear variable names, obvious logic flow
- **Specification compliant**: Accurate WebGPU API usage
- **Cross-browser aware**: Handle feature availability appropriately

### Feature Coverage
- **Advanced features**: Use rarely-tested WebGPU capabilities (atomics, multisampling, bundles, etc.)
- **Edge cases**: Test boundary conditions and unusual combinations
- **Performance characteristics**: Demonstrate real-world usage patterns
- **Integration testing**: Combine multiple API components

### Visual Validation
- **Deterministic results**: Same output on repeated runs
- **Feature demonstration**: Visual output clearly shows the tested capability
- **Complexity appropriate**: Advanced enough to stress-test, simple enough to validate

## Browser Compatibility
- **Primary testing**: Chromium (most complete WebGPU implementation)
- **Feature detection**: Check adapter features before using advanced capabilities
- **Fallback handling**: Graceful degradation when features unavailable

## Common Pitfalls to Avoid
- **Overly complex logic** - breaks fuzzing capability
- **External dependencies** - violates self-containment requirement
- **Non-deterministic output** - makes validation unreliable
- **Console logging** - interferes with automated error detection
- **User interaction** - prevents automated testing
- **Comments in code** - reduces fuzzing effectiveness

## Success Metrics
- **Clean test execution**: No warnings, errors, or console output
- **Visual output**: Complex, deterministic demonstration of target feature
- **Fuzzing readiness**: Code structure supports mutation testing
- **Coverage contribution**: Addresses gaps identified in TODO.md
- **Maintainability**: Clear, simple code following project conventions

## Example Workflow Summary
1. Identify under-tested feature from TODO.md
2. Study existing similar test cases
3. Implement minimalist demo in correct directory
4. Run validation tests with appropriate browsers
5. Fix any warnings/errors through iteration
6. Update documentation counts
7. Verify clean execution on chromium

## Additional targeting instructions

Focus on features that leverage full power of WGSL.  