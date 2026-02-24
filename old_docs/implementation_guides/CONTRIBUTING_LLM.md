# LLM Contributor Guide: Developing WebGPU Test Cases

This guide provides specific instructions for a Large Language Model (LLM) on how to create, verify, and contribute new WebGPU test cases to this repository. The primary goal is to increase coverage of the [WebGPU Specification](https://www.w3.org/TR/webgpu/) with high-quality, fuzzable, and self-contained tests.

## 1. Core Principles for Test Case Development

Adhere to these principles strictly:

1.  **Self-Contained**: Each test case MUST be a single `.html` file with all JavaScript, WGSL, and any necessary data embedded. **No external files, libraries, or resources are permitted.**
2.  **Minimalist and Fuzzable**: Code must be concise and easy for a machine to parse and modify.
    *   **No Comments**: Avoid explanatory comments in the code. The code's function should be clear from its structure.
    *   **No Logging**: Do not use `console.log()` or other console output. The test runner automatically captures all necessary error and validation information.
    *   **Simple Structures**: Use simple variables, functions, and control flow. Avoid complex classes, abstractions, or verbose coding patterns.
    *   **Variable Parameterize**: Inline some of the values, use variables for some. This makes the test more suitable for mutation-based fuzzing.
3.  **Focus on Coolness**: The primary purpose of a test is to create a complex visual demo. The visual output should be composed of different sources.

## 2. How to Create a New Test Case: Step-by-Step Workflow

### Step 1: Identify a Target Feature to Test

- **Consult the Documentation**: Review `TESTCASES.md` and the directory structure in `README.md` to identify under-tested areas of the WebGPU specification.
- **Analyze `TODO.md`**: The `TODO.md` file contains a roadmap of features that require test cases.
- **Combine Features**: Propose novel test cases that combine multiple API features in unconventional ways to uncover edge-case bugs.

### Step 2: Create the Test Files

1.  **Choose the Correct Directory**: Place your new test file in the most relevant sub-directory within `testcases/`. For example, a test for buffer mapping belongs in `testcases/buffers/`.
2.  **Create the HTML File**: Name the file descriptively, e.g., `buffer_map_read_write.html`. Start with this minimal boilerplate:

    ```html
    <!DOCTYPE html>
    <html>
    <body>
        <canvas id="webgpu-canvas" width="256" height="256"></canvas>
        <script>
            async function main() {
                // Your WebGPU implementation goes here.
                // The script must be self-executing and run to completion.
                // Do not add any console logs.
            }
            main().catch(err => {
                // The test runner will capture unhandled exceptions.
                // Do not add custom error logging here.
                throw err;
            });
        </script>
    </body>
    </html>
    ```

### Step 3: Implement the Test Logic

- **Write Concise WGSL**: Embed your WGSL shader source directly into a JavaScript template literal. Use imagination to build surprising ways to leverage WGSL.
- **Write Direct WebGPU Code**: Implement the test using the WebGPU API directly. Avoid helper functions or libraries unless absolutely necessary.
- **Design for Fuzzing**:
    - **Example**: Use inline values example `device.createBuffer({ size: 64, ... })`, instead of `const bufferSize = 64; device.createBuffer({ size: bufferSize, ... })`.
- **Think Creatively**: Design tests that stress the interactions between different parts of the API. See Section 5 for examples.

## 3. Verifying Your Test Case

**This is a critical step. A test case is only complete if it runs successfully without generating any errors or warnings.**

### Step 1: Set Up the Virtual Environment

Before running tests, you must set up a Python virtual environment to ensure proper dependency isolation:

1. **Create the virtual environment**:
   ```bash
   python3 -m venv venv
   ```

2. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Deactivate when done** (optional):
   ```bash
   deactivate
   ```

### Step 2: Execute the Test Runner

Use the `run_tests.sh` script to execute your test case. The script automatically detects and uses the virtual environment if it exists, or falls back to system Python.

- **Command Syntax**:
  ```bash
  ./run_tests.sh --test-file [path_to_your_html_file] --browsers [browser_name]
  ```

- **Example**: To test a new file `testcases/buffers/buffer_map_validation.html` in Chromium:
  ```bash
  ./run_tests.sh --test-file testcases/buffers/buffer_map_validation.html --browsers chromium
  ```

**Note**: The `run_tests.sh` script will automatically use the `venv` directory if it exists, so you don't need to manually activate the virtual environment each time you run tests.

### Step 3: Analyze the Results

The test runner will generate a `.json` file with the same name as your test file (e.g., `buffer_map_validation.json`). You must inspect this file to confirm the test passed correctly.

- **A successful test's JSON output will have:**
    - `"passed": true`
    - `"console_logs": [` should contain only info level messages, no warnings or errors: `"level": "warning"`
    - An empty array for `"javascript_errors": []`
    - An empty array for `"webgpu_errors": []`
    - An empty array for `"errors": []`

- **A failed test will have:**
    - `"passed": false`
    - One or more of the error arrays populated with detailed error messages.

**Your test case is NOT complete until it passes with zero errors and warnings in the target browser.**

**After fixing issues always redo run_tests.sh and verify from .json that the files actually worked.**

**Do not presume that the fixes worked.**

**If you cannot fix the test case, remove it. NEVER LEAVE TEST CASES WITH ERRORS OR WARNINGS TO THE TEST CORPUS**


## 4. Tracking Progress and Coverage

To track our progress in covering the WebGPU specification without consuming large amounts of context, we use a simple, low-overhead method.

### Your Responsibility:

After you have created and **successfully verified** a new test case, you must update the test count for the corresponding category in the main `README.md` file.

- **Example**: If you add a new test to the `testcases/buffers/` directory:
    1.  Open `README.md`.
    2.  Locate the line under "Project Structure" for buffers:
        `- │   ├── buffers/                 # GPUBuffer operations (13 tests)`
    3.  Increment the count:
        `- │   ├── buffers/                 # GPUBuffer operations (14 tests)`

This ensures our coverage metrics stay up-to-date.

## 5. Creative Test Case Design

To find deeper bugs, create test cases that combine multiple WebGPU features in novel ways.

These are examples, do not get stuck on creating only these types of test cases:
-   **Compute to Render**: Create a test where a compute shader procedurally generates complex vertex data into a storage buffer. Then, use that buffer in a subsequent render pass with an unusual primitive topology (like `triangle-strip`).
-   **Texture Pipelines**: Have a compute shader write to a storage texture. Then, use that texture as a sampled source in a render pipeline, which in turn writes to a different render target texture. This stresses synchronization and texture state transitions.
-   **Bundles and Queries**: Record a complex scene into multiple render bundles. Execute them in a render pass and wrap the execution with timestamp queries to measure the performance and validation of pre-recorded commands.
-   **Limits as Parameters**: Write a test that queries a device limit (e.g., `maxColorAttachments`) and then immediately attempts to create a pipeline and render pass that uses that exact number of attachments, testing the boundary condition directly.

By following these instructions, you will contribute high-quality, valuable test cases that enhance the robustness and specification compliance of WebGPU implementations.
