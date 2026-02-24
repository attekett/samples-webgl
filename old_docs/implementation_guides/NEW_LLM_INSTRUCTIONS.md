# WebGPU Complex Fuzzing Test Case Generator

## Core Mission

Create high-complexity, integrated WebGPU test cases that stress-test the interaction between different pipeline stages (Compute, Render, Copy).

**Goal:** Maximize "API Surface Area" per file.

**Anti-Pattern:** Do not create isolated unit tests.

**Target:** Create "Spaghetti-like" valid resource usage where buffers and textures are shared across multiple shaders and passes.

## 0. The UNSUPPORTED.md Protocol (Mandatory Pre-Check)

Before generating any code, you must strictly follow this protocol to prevent infinite "fixing" loops on features the environment simply doesn't have.

- **READ:** Check UNSUPPORTED.md. If the feature you plan to use is listed there, ABORT generation for this feature immediately and pick a different one.
- **DETECT:** In your generated code, you must explicitly check for feature availability (see Boilerplate).
- **WRITE:** If a test fails specifically because the browser threw an error regarding a missing feature (e.g., "Feature X is not enabled"), you must:

  - NOT try to polyfill or fix the code.
  - ADD the feature name to UNSUPPORTED.md.
  - mark the test case as skipped.

## 1. Complexity Guidelines (Maximize Entropy)

We want to give the mutation engine rich material to work with.

**Multi-Pass Dependencies:** Never just "Draw Triangle".

**Good:** Compute Shader writes to Buffer A -> Copy Buffer A to Texture B -> Render Pipeline samples Texture B -> Output to Screen.

**Resource Abuse:**
- Bind the same buffer as storage in one shader and uniform in another.
- Use multiple bind groups.
- Mix different texture formats in the same pass if spec allows.

**State Interaction:**
- Change pipeline state (blend modes, stencil masks, depth bias) dynamically if possible or setup complex initial states.
- Use heavy interleaving of writeBuffer and draw calls.

## 2. Technical Constraints

- **Single HTML File:** Self-contained.
- **Resolution:** 256x256 (Standard).
- **Determinism:** Output must be deterministic (no Math.random() inside the shader/logic).
- **Clean:** No comments, or unrequired code: logging, error checking, HTML status prints

**Mutation Ready:**
- Use explicit literals for numbers (e.g., `size: 1024` instead of `const size = 1024`). This allows the fuzzer to mutate the number 1024 easily.
- Avoid helper functions that hide API calls. We want raw API calls exposed to the fuzzer.

## 3. Error Handling & Fixing Strategy

You are expected to fix bugs, but you must distinguish between Bugs and Constraints.

| Error Type    | Example                                  | Action                          |
|---------------|------------------------------------------|---------------------------------|
| Logic/Syntax  | Variable 'x' not defined                | FIX IT. Rewrite the code to work. |
| API Misuse    | Buffer usage validation error           | FIX IT. Adjust usage flags to match spec. |
| Unsupported   | Feature 'texture-compression-bc' missing | STOP. Add to UNSUPPORTED.md.    |
| Unsupported   | Adapter does not support ...            | STOP. Add to UNSUPPORTED.md.    |

**CRITICAL:** Do NOT add try-catch blocks to suppress execution errors. If the logic fails, the test MUST crash so the fuzzer knows it found a bug or invalid state.

## 4. Required Boilerplate

Use this structure. It implements the "Fail Fast" mechanism for unsupported features.

**CRITICAL:** Remove comments from output. 
**CRITICAL:** Remove REQUIRED_FEATURES check if the array would be empty

```html
<!DOCTYPE html>
<html>
<body>
<canvas id="webgpu-canvas" width="256" height="256"></canvas>
<script>
// CONFIGURATION: Define required features here
const REQUIRED_FEATURES = [
    // e.g., 'texture-compression-bc', 'timestamp-query'
];

async function main() {
    if (!navigator.gpu) throw new Error("WebGPU not supported");
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) throw new Error("No GPUAdapter found");

    // 1. FEATURE GATING
    const missingFeatures = REQUIRED_FEATURES.filter(f => !adapter.features.has(f));
    if (missingFeatures.length > 0) {
        // Signal to the Test Runner that this is an environment limit, not a code bug
        throw new Error(`UNSUPPORTED_FEATURE: ${missingFeatures.join(', ')}`);
    }

    // 2. DEVICE CREATION
    const device = await adapter.requestDevice({
        requiredFeatures: REQUIRED_FEATURES
    });

    const canvas = document.getElementById('webgpu-canvas');
    const context = canvas.getContext('webgpu');
    const format = navigator.gpu.getPreferredCanvasFormat();
    context.configure({ device, format });

    // 3. ERROR SCOPE
    // Capture validation errors (these are usually silent in JS but vital for fuzzing)
    device.pushErrorScope('validation');

    // ==========================================
    // COMPLEX IMPLEMENTATION STARTS HERE
    // ==========================================

    // [Insert Multi-pass, Multi-resource logic here]
    // [Avoid abstractions. Use raw API calls.]

    // ==========================================
    // COMPLEX IMPLEMENTATION ENDS HERE
    // ==========================================

    // 4. VALIDATION CHECK
    const error = await device.popErrorScope();
    if (error) {
        throw new Error(`WebGPU Validation Error: ${error.message}`);
    }
}

main().catch(err => {
    // If the error string contains "UNSUPPORTED_FEATURE", the Python runner
    // knows to log it to UNSUPPORTED.md and skip.
    // Otherwise, it counts as a test failure/crash.
    console.error(err); // Allowed for debugging, but DOM update is primary signal
});
</script>
</body>
</html>
```

## 5. Verification Protocol

You must verify the generated test case using the automated test runner.

### 1. Run the Test

Execute the following command in the terminal:

```bash
./run_tests.sh --test-file agent_outputs/your_filename.html --browsers chromium
```

The script can be found from rpoject root.

### 2. Analyze JSON Output

The command generates a JSON file with the same name as your test file, but with a .json extension (e.g., `agent_outputs/your_filename.json`). Read this file to check the results. Focus on the `results` array (specifically `results[0]`).

**Success Criteria (The test is GOOD):**
- `"passed": true`
- `"javascript_errors": []` (Empty array)
- `"webgpu_errors": []` (Empty array)

**Failure Criteria (The test is BAD or UNSUPPORTED):**
- `"passed": false`
- `"javascript_errors"` contains entries.

### 3. Verification Decision Logic

If `passed` is `false`, examine the message inside `javascript_errors` or `webgpu_errors`.

**Case A: Unsupported Feature**
- **Symptom:** Error message mentions "unsupported", "not enabled", or matches your UNSUPPORTED_FEATURE error from the boilerplate.
- **Action:** DO NOT FIX. Log the feature to UNSUPPORTED.md and mark the test as valid but skipped. Move the test case to `agent_output/unsupported`.

**Case B: Validation/Logic Error**
- **Symptom:** "Buffer usage validation", "Shader parsing error", "Binding size mismatch".
- **Action:** FIX IT. The logic is flawed. You must rewrite the code to satisfy the spec. Retry the verification.

**Case C: Timeout / Crash**
- **Symptom:** Test runner crashes or reports timeout.
- **Action:** FIX IT. The code is likely invalid or stuck in an infinite loop.

## 6. Development Workflow

1. Check UNSUPPORTED.md: Ensure your target features aren't banned.
2. Plan the Complexity: Define at least 2 distinct passes (e.g., Compute -> Render).
3. Generate Code: Use the required boilerplate.
4. Verify: Run `./run_tests.sh`, read the resulting `.json` file, and apply the Verification Decision Logic (Section 5).
5. **Pass:** Success.
6. **Fail (Bug):** Fix code -> Goto Step 4.
7. **Fail (Unsupported):** Log to UNSUPPORTED.md -> Stop.
8. **Final Output:** Ensure the clean, working file is in `agent_outputs/`.

## 7. Additional targetting instructions

Create test cases that somehow leverage GPUTextureView and/or different methods of GPUCommandEncoder and/or GPUSampler an/or createComputePipelineAsync