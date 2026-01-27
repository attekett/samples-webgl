# WebGL/WebGL2 Coding Rules and Guidelines

This guide provides specific instructions for developing WebGL/WebGL2 test cases. It builds upon the core principles outlined in [.cursorrules](.cursorrules) and the detailed agent instructions in [AGENTS.md](AGENTS.md).

**For mutation-based fuzzing seed creation**, see the comprehensive design document: [docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md](docs/plans/2026-01-27-mutation-fuzzing-seed-structure-design.md). This document provides detailed instructions for creating seeds optimized for radamsa line repetition and numeric mutations targeting driver memory corruption bugs.

## 1. Core Principles for Test Case Development

Adhere to these principles strictly:

1.  **Self-Contained**: Each test case MUST be a single `.html` file with all JavaScript, GLSL shaders, and any necessary data embedded. **No external files, libraries, or resources are permitted.**
2.  **Minimalist and Fuzzable**: Code must be concise and easy for a machine to parse and modify.
    *   **No Comments**: Avoid explanatory comments in the code. The code's function should be clear from its structure.
    *   **No Logging**: Do not use `console.log()` or other console output. The test runner automatically captures all necessary error and validation information.
    *   **Simple Structures**: Use simple variables, functions, and control flow. Avoid complex classes, abstractions, or verbose coding patterns.
    *   **Variable Parameterize**: Inline some of the values, use variables for some. This makes the test more suitable for mutation-based fuzzing.
3.  **Focus on Visual Complexity**: The primary purpose of a test is to create a complex visual demo. The visual output should demonstrate advanced WebGL features and extension interactions.
4.  **Extension-Aware**: Always check for required WebGL extensions before using advanced features.

## 2. How to Create a New Test Case: Step-by-Step Workflow

### Step 1: Identify a Target Feature to Test

- **Consult TODO.md**: The `TODO.md` file contains a roadmap of features that require test cases.
- **Check existing coverage**: Review project documentation to identify under-tested areas of the WebGL/WebGL2 specifications.
- **Combine Features**: Propose novel test cases that combine multiple API features and extensions in unconventional ways to uncover edge-case bugs.

### Step 2: Create the Test Files

1.  **Choose the Correct Directory**: Place your new test file in the most relevant sub-directory within `testcases/`. For example, a test for texture operations belongs in `testcases/textures/`.
2.  **Create the HTML File**: Name the file descriptively, e.g., `texture_float_rendering.html`. Start with this minimal boilerplate:

    ```html
    <!DOCTYPE html>
    <html>
    <body>
        <canvas id="webgl-canvas" width="256" height="256"></canvas>
        <script>
            const REQUIRED_EXTENSIONS = [
                // Add required extensions here, e.g., 'OES_texture_float'
            ];

            async function main() {
                const canvas = document.getElementById('webgl-canvas');
                const gl = canvas.getContext('webgl2');
                if (!gl) throw new Error("WebGL2 not supported - required for all tests");

                // Check and enable required extensions
                const missingExtensions = REQUIRED_EXTENSIONS.filter(ext => !gl.getExtension(ext));
                if (missingExtensions.length > 0) {
                    throw new Error(`UNSUPPORTED_EXTENSIONS: ${missingExtensions.join(', ')}`);
                }
                REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));

                // Your WebGL implementation goes here.
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

- **Write Concise GLSL**: Embed your GLSL shader source directly into JavaScript template literals. Use imagination to build surprising ways to leverage GLSL.
- **Write Direct WebGL Code**: Implement the test using the WebGL API directly. Avoid helper functions or libraries unless absolutely necessary.
- **Design for Fuzzing**:
    - **Example**: Use inline values `gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)`, instead of `const minFilter = gl.LINEAR; gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, minFilter)`.
- **Extension Integration**: Design tests that properly check for and utilize WebGL extensions.
- **Think Creatively**: Design tests that stress the interactions between different parts of the WebGL pipeline. See Section 5 for examples.

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

- **Example**: To test a new file `testcases/textures/texture_float_rendering.html` in Chromium:
  ```bash
  ./run_tests.sh --test-file testcases/textures/texture_float_rendering.html --browsers firefox
  ```

**Note**: The `run_tests.sh` script will automatically use the `venv` directory if it exists, so you don't need to manually activate the virtual environment each time you run tests.

### Step 3: Analyze the Results

The test runner will generate a `.json` file with the same name as your test file (e.g., `texture_float_rendering.json`). You must inspect this file to confirm the test passed correctly.

- **A successful test's JSON output will have:**
    - `"passed": true`
    - `"console_logs": [` should contain only info level messages, no warnings or errors: `"level": "warning"`
    - An empty array for `"javascript_errors": []`
    - An empty array for `"webgl_errors": []`
    - An empty array for `"errors": []`

- **A failed test will have:**
    - `"passed": false`
    - One or more of the error arrays populated with detailed error messages.

**Your test case is NOT complete until it passes with zero errors and warnings in the target browser.**

**After fixing issues always redo run_tests.sh and verify from .json that the files actually worked.**

**Do not presume that the fixes worked.**

**If you cannot fix the test case, remove it. NEVER LEAVE TEST CASES WITH ERRORS OR WARNINGS TO THE TEST CORPUS**

## 4. Tracking Progress and Coverage

To track our progress in covering the WebGL/WebGL2 specifications without consuming large amounts of context, we use a simple, low-overhead method.

### Your Responsibility:

After you have created and **successfully verified** a new test case, you must update the test count for the corresponding category in the main project documentation.

## 5. Creative Test Case Design

To find deeper bugs, create test cases that combine multiple WebGL features and extensions in novel ways.

These are examples, do not get stuck on creating only these types of test cases:

-   **Render-to-Texture Pipelines**: Create a test where you render to a framebuffer texture, then use that texture as input for a subsequent rendering pass with different shaders or blend modes.
-   **Extension Combinations**: Have a fragment shader that uses floating-point textures (OES_texture_float) and multiple render targets (WEBGL_draw_buffers) simultaneously.
-   **Complex State Management**: Write a test that heavily interleaves texture binding, shader switching, uniform updates, and draw calls to stress state management.
-   **Limits as Parameters**: Write a test that queries WebGL limits (e.g., `gl.getParameter(gl.MAX_TEXTURE_SIZE)`) and then immediately attempts to create resources and operations that use that exact limit value.
-   **Shader Complexity**: Create vertex shaders that perform complex transformations and fragment shaders that use multiple texture samplers with different filtering modes.

By following these instructions, you will contribute high-quality, valuable test cases that enhance the robustness and specification compliance of WebGL implementations.

## 6. WebGL-Specific Considerations

### Extension Management
- Always check extension availability before use
- Use descriptive error messages for missing extensions
- Consider fallback paths when extensions are unavailable
- Test extension interactions and combinations

### Context Management
- Handle potential context loss scenarios
- Check for WebGL errors after critical operations
- Ensure proper cleanup of resources when applicable

### Shader Considerations
- Validate shader compilation and linking
- Test various GLSL versions and precision qualifiers
- Use both vertex and fragment shader complexity
- Test uniform and attribute limits

### Performance Characteristics
- Test with different texture formats and sizes
- Exercise various buffer usage patterns
- Combine multiple rendering passes
- Test state change frequency and patterns

## 7. Browser Compatibility Matrix

- **Primary Testing**: Firefox (superior WebGL extension support)
- **Chromium**: Do not use for extension-heavy tests
- **Compatibility Checks**: Always verify extension availability
- **Fallback Strategies**: Design tests that can degrade gracefully

## 8. Related Documentation

- **[.cursorrules](.cursorrules)**: Core project rules and mission
- **[AGENTS.md](AGENTS.md)**: Detailed agent instructions for test case creation
- **TODO.md**: Current development roadmap and priorities
- **UNSUPPORTED.md**: Known limitations and unsupported features