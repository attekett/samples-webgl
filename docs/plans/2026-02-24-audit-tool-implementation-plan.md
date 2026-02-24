# WebGL API Surface Auditor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a TDD-driven Python auditor (`scripts/api_audit/`) that measures spec-level WebGL API coverage of the fuzzing corpus, plus a Node.js extraction script that produces the API surface JSON.

**Architecture:** Bottom-up TDD — each auditor module is tested against synthetic HTML fixtures before implementation. Tests use a hand-written `test_surface.json` (not real spec data), so the Python auditor is fully testable without the extraction script. The extraction script (M1) runs last since no Python test depends on it.

**Tech Stack:** Python 3 (tree-sitter, tree-sitter-javascript, pytest, beautifulsoup4), Node.js (webidl2)

**Reference docs (read before implementing):**
- `docs/plans/2026-02-24-webgl-api-surface-extraction-design.md` — full auditor design
- `docs/plans/2026-02-24-audit-tool-testing-design.md` — test strategy

---

## Task 1: Project Scaffolding

**Files:**
- Create: `scripts/api_audit/__init__.py`
- Create: `scripts/api_audit/__main__.py` (stub)
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`
- Create: `tests/fixtures/surface/test_surface.json`
- Create: `tests/fixtures/synthetic/basic_draw.html`
- Create: `tests/fixtures/synthetic/const_forward_ref.html`
- Create: `tests/fixtures/synthetic/const_gl_alias.html`
- Create: `tests/fixtures/synthetic/ext_array_pattern.html`
- Create: `tests/fixtures/synthetic/ext_direct_assign.html`
- Create: `tests/fixtures/synthetic/ext_both_patterns.html`
- Create: `tests/fixtures/synthetic/ext_bare_enable.html`
- Create: `tests/fixtures/synthetic/ext_empty_array.html`
- Create: `tests/fixtures/synthetic/webgl_fallback.html`
- Create: `tests/fixtures/synthetic/helper_single_level.html`
- Create: `tests/fixtures/synthetic/helper_glsl_builtins.html`
- Create: `tests/fixtures/synthetic/lint_multilevel.html`
- Create: `tests/fixtures/synthetic/overload_size.html`
- Create: `tests/fixtures/synthetic/overload_data.html`
- Create: `tests/fixtures/synthetic/shader_template.html`
- Create: `tests/fixtures/synthetic/glsl_builtins.html`
- Create: `tests/fixtures/synthetic/return_compare.html`
- Create: `tests/fixtures/synthetic/lint_violations.html`
- Create: `tests/fixtures/seeds/README.md`
- Modify: `requirements.txt`
- Modify: `.gitignore` (add `.cache/api_audit/`)

**Step 1: Add Python dependencies**

Append to `requirements.txt`:

```
tree-sitter>=0.22.0
tree-sitter-javascript>=0.22.0
pytest>=7.0.0
```

**Step 2: Install dependencies**

Run: `source venv/bin/activate && pip install -r requirements.txt`

**Step 3: Create package scaffolding**

`scripts/api_audit/__init__.py`:
```python
"""WebGL API surface auditor — AST-based corpus coverage analysis."""
```

`scripts/api_audit/__main__.py`:
```python
"""CLI entry point — implemented in Task 10."""
import sys
sys.exit("Not yet implemented")
```

`tests/__init__.py`: empty file.

**Step 4: Create conftest.py**

`tests/conftest.py`:
```python
import sys
import json
import pytest
from pathlib import Path

# Make 'import api_audit' work without install
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def surface():
    """Minimal API surface for testing."""
    return json.loads((FIXTURES / "surface" / "test_surface.json").read_text())


@pytest.fixture
def parse_html():
    """Returns a function: filename -> tree-sitter root node."""
    from api_audit.html_extract import extract_script
    from api_audit.parse import parse_js

    def _parse(filename):
        html = (FIXTURES / "synthetic" / filename).read_text()
        script = extract_script(html)
        return parse_js(script)

    return _parse


@pytest.fixture
def fixture_path():
    """Returns a function: filename -> full Path to synthetic fixture."""
    def _path(filename):
        return FIXTURES / "synthetic" / filename
    return _path
```

**Step 5: Create test_surface.json**

`tests/fixtures/surface/test_surface.json`:
```json
{
  "meta": {
    "sources": [{"name": "test", "url": "test", "sha256": "test"}],
    "schema_version": "3.0",
    "extracted_at": "2026-01-01T00:00:00Z"
  },
  "constants": {
    "TRIANGLES": {"value": "0x0004", "kind": "enum", "roles": ["draw_mode"], "webgl_version": 1},
    "TRIANGLE_STRIP": {"value": "0x0005", "kind": "enum", "roles": ["draw_mode"], "webgl_version": 1},
    "RGBA": {"value": "0x1908", "kind": "enum", "roles": ["format", "internalformat"], "webgl_version": 1},
    "FLOAT": {"value": "0x1406", "kind": "enum", "roles": ["pixel_type", "data_type"], "webgl_version": 1},
    "UNSIGNED_BYTE": {"value": "0x1401", "kind": "enum", "roles": ["pixel_type", "index_type"], "webgl_version": 1},
    "DEPTH_TEST": {"value": "0x0B71", "kind": "enum", "roles": ["capability"], "webgl_version": 1},
    "FRAMEBUFFER_COMPLETE": {"value": "0x8CD5", "kind": "enum", "roles": ["framebuffer_status"], "webgl_version": 1},
    "FRAMEBUFFER": {"value": "0x8D40", "kind": "enum", "roles": ["framebuffer_target"], "webgl_version": 1},
    "ARRAY_BUFFER": {"value": "0x8892", "kind": "enum", "roles": ["buffer_target"], "webgl_version": 1},
    "STATIC_DRAW": {"value": "0x88E4", "kind": "enum", "roles": ["buffer_usage"], "webgl_version": 1},
    "COLOR_BUFFER_BIT": {"value": "0x00004000", "kind": "bitmask", "roles": ["buffer_bit"], "webgl_version": 1},
    "DEPTH_BUFFER_BIT": {"value": "0x00000100", "kind": "bitmask", "roles": ["buffer_bit"], "webgl_version": 1},
    "VERTEX_SHADER": {"value": "0x8B31", "kind": "enum", "roles": ["shader_type"], "webgl_version": 1},
    "FRAGMENT_SHADER": {"value": "0x8B30", "kind": "enum", "roles": ["shader_type"], "webgl_version": 1},
    "NO_ERROR": {"value": "0", "kind": "enum", "roles": ["error_code"], "webgl_version": 1},
    "TEXTURE_2D": {"value": "0x0DE1", "kind": "enum", "roles": ["texture_target"], "webgl_version": 1}
  },
  "methods": {
    "drawArrays": {
      "webgl_version": 1,
      "overloads": [{
        "arity": 3,
        "params": [
          {"name": "mode", "type": "GLenum"},
          {"name": "first", "type": "GLint"},
          {"name": "count", "type": "GLsizei"}
        ]
      }]
    },
    "bufferData": {
      "webgl_version": 1,
      "ambiguous_arity": true,
      "overloads": [
        {
          "arity": 3,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "size", "type": "GLsizeiptr"},
            {"name": "usage", "type": "GLenum"}
          ]
        },
        {
          "arity": 3,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "srcData", "type": "AllowSharedBufferSource?"},
            {"name": "usage", "type": "GLenum"}
          ]
        }
      ]
    },
    "texImage2D": {
      "webgl_version": 1,
      "overloads": [
        {
          "arity": 6,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "level", "type": "GLint"},
            {"name": "internalformat", "type": "GLint"},
            {"name": "format", "type": "GLenum"},
            {"name": "type", "type": "GLenum"},
            {"name": "source", "type": "TexImageSource"}
          ]
        },
        {
          "arity": 9,
          "params": [
            {"name": "target", "type": "GLenum"},
            {"name": "level", "type": "GLint"},
            {"name": "internalformat", "type": "GLint"},
            {"name": "width", "type": "GLsizei"},
            {"name": "height", "type": "GLsizei"},
            {"name": "border", "type": "GLint"},
            {"name": "format", "type": "GLenum"},
            {"name": "type", "type": "GLenum"},
            {"name": "pixels", "type": "ArrayBufferView?"}
          ]
        }
      ]
    },
    "shaderSource": {
      "webgl_version": 1,
      "overloads": [{
        "arity": 2,
        "params": [
          {"name": "shader", "type": "WebGLShader"},
          {"name": "source", "type": "DOMString"}
        ]
      }]
    },
    "enable": {
      "webgl_version": 1,
      "overloads": [{
        "arity": 1,
        "params": [{"name": "cap", "type": "GLenum"}]
      }]
    },
    "clear": {
      "webgl_version": 1,
      "overloads": [{
        "arity": 1,
        "params": [{"name": "mask", "type": "GLbitfield"}]
      }]
    },
    "getError": {
      "webgl_version": 1,
      "overloads": [{"arity": 0, "params": []}]
    },
    "checkFramebufferStatus": {
      "webgl_version": 1,
      "overloads": [{
        "arity": 1,
        "params": [{"name": "target", "type": "GLenum"}]
      }]
    },
    "createShader": {
      "webgl_version": 1,
      "overloads": [{
        "arity": 1,
        "params": [{"name": "type", "type": "GLenum"}]
      }]
    },
    "compileShader": {
      "webgl_version": 1,
      "overloads": [{
        "arity": 1,
        "params": [{"name": "shader", "type": "WebGLShader"}]
      }]
    },
    "createBuffer": {
      "webgl_version": 1,
      "overloads": [{"arity": 0, "params": []}]
    },
    "bindBuffer": {
      "webgl_version": 1,
      "overloads": [{
        "arity": 2,
        "params": [
          {"name": "target", "type": "GLenum"},
          {"name": "buffer", "type": "WebGLBuffer?"}
        ]
      }]
    }
  },
  "extensions": {
    "OES_vertex_array_object": {
      "methods": {
        "createVertexArrayOES": {"overloads": [{"arity": 0, "params": []}]},
        "bindVertexArrayOES": {"overloads": [{"arity": 1, "params": [{"name": "arrayObject", "type": "WebGLVertexArrayObjectOES?"}]}]}
      },
      "constants": {
        "VERTEX_ARRAY_BINDING_OES": {"value": "0x85B5", "kind": "enum", "roles": ["get_parameter"]}
      }
    },
    "OES_standard_derivatives": {"methods": {}, "constants": {}},
    "EXT_color_buffer_float": {"methods": {}, "constants": {}}
  },
  "glsl_builtins": {
    "texture_sampling": ["texelFetch"],
    "pack_unpack": ["packHalf2x16", "unpackSnorm2x16"],
    "fragment_processing": ["dFdx"]
  }
}
```

**Step 6: Create all synthetic fixtures**

Each fixture is 10-30 lines. Create all 14 at once.

`tests/fixtures/synthetic/basic_draw.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
gl.clearColor(0, 0, 0, 1);
gl.clear(gl.COLOR_BUFFER_BIT);
gl.drawArrays(gl.TRIANGLES, 0, 3);
</script>
</body></html>
```

`tests/fixtures/synthetic/const_forward_ref.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
gl.drawArrays(MODE, 0, 3);
const MODE = gl.TRIANGLES;
</script>
</body></html>
```

`tests/fixtures/synthetic/const_gl_alias.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
const RGBA = gl.RGBA;
const FMT = RGBA;
gl.texImage2D(gl.TEXTURE_2D, 0, FMT, FMT, gl.UNSIGNED_BYTE, canvas);
</script>
</body></html>
```

`tests/fixtures/synthetic/ext_array_pattern.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const REQUIRED_EXTENSIONS = ['EXT_color_buffer_float'];
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));
</script>
</body></html>
```

`tests/fixtures/synthetic/ext_direct_assign.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
const ext = gl.getExtension('OES_vertex_array_object');
ext.createVertexArrayOES();
</script>
</body></html>
```

`tests/fixtures/synthetic/ext_both_patterns.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const REQUIRED_EXTENSIONS = ['EXT_color_buffer_float'];
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));
const vao = gl.getExtension('OES_vertex_array_object');
vao.createVertexArrayOES();
</script>
</body></html>
```

`tests/fixtures/synthetic/ext_bare_enable.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
gl.getExtension('OES_standard_derivatives');
</script>
</body></html>
```

`tests/fixtures/synthetic/ext_empty_array.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const REQUIRED_EXTENSIONS = [];
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
REQUIRED_EXTENSIONS.forEach(ext => gl.getExtension(ext));
gl.drawArrays(gl.TRIANGLES, 0, 3);
</script>
</body></html>
```

`tests/fixtures/synthetic/webgl_fallback.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
gl.drawArrays(gl.TRIANGLES, 0, 3);
</script>
</body></html>
```

`tests/fixtures/synthetic/helper_single_level.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
function createShader(gl, type, source) {
    const s = gl.createShader(type);
    gl.shaderSource(s, source);
    gl.compileShader(s);
    return s;
}
const vs = `#version 300 es
void main() { gl_Position = vec4(0); }`;
createShader(gl, gl.VERTEX_SHADER, vs);
</script>
</body></html>
```

`tests/fixtures/synthetic/overload_size.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
const buf = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buf);
gl.bufferData(gl.ARRAY_BUFFER, 1024, gl.STATIC_DRAW);
</script>
</body></html>
```

`tests/fixtures/synthetic/overload_data.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
const buf = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, buf);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([1, 2, 3]), gl.STATIC_DRAW);
</script>
</body></html>
```

`tests/fixtures/synthetic/shader_template.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
const vs = `#version 300 es
void main() { gl_Position = vec4(0); }`;
const s = gl.createShader(gl.VERTEX_SHADER);
gl.shaderSource(s, vs);
</script>
</body></html>
```

`tests/fixtures/synthetic/glsl_builtins.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
const fs = `#version 300 es
precision highp float;
uniform highp sampler2D tex;
out vec4 color;
void main() {
    color = texelFetch(tex, ivec2(0), 0);
    uint packed = packHalf2x16(color.xy);
    float dx = dFdx(color.x);
}`;
const s = gl.createShader(gl.FRAGMENT_SHADER);
gl.shaderSource(s, fs);
</script>
</body></html>
```

`tests/fixtures/synthetic/return_compare.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
if (status === gl.FRAMEBUFFER_COMPLETE) {}
const err = gl.getError();
if (err !== gl.NO_ERROR) {}
</script>
</body></html>
```

`tests/fixtures/synthetic/lint_violations.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
const methodName = 'drawArrays';
gl[methodName](gl.TRIANGLES, 0, 3);
const { DEPTH_TEST } = gl;
gl.enable(DEPTH_TEST);
const s = gl.createShader(gl.VERTEX_SHADER);
gl.shaderSource(s, 'void main(){}' + ' extra');
</script>
</body></html>
```

`tests/fixtures/synthetic/helper_glsl_builtins.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
function createShader(gl, type, source) {
    const s = gl.createShader(type);
    gl.shaderSource(s, source);
    gl.compileShader(s);
    return s;
}
const fs = `#version 300 es
precision highp float;
uniform highp sampler2D tex;
out vec4 color;
void main() {
    color = texelFetch(tex, ivec2(0), 0);
}`;
createShader(gl, gl.FRAGMENT_SHADER, fs);
</script>
</body></html>
```

`tests/fixtures/synthetic/lint_multilevel.html`:
```html
<!DOCTYPE html><html><body>
<canvas id="c" width="256" height="256"></canvas>
<script>
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2');
function innerHelper(gl) {
    gl.drawArrays(gl.TRIANGLES, 0, 3);
}
function outerHelper(gl) {
    innerHelper(gl);
}
outerHelper(gl);
</script>
</body></html>
```

`tests/fixtures/seeds/README.md`:
```markdown
# Pinned Seeds

Copies of real corpus seeds with companion `expected_output.json` files.
These are added during integration testing (Task 11).

Selection criteria:
- One minimal seed (few methods, no extensions)
- One seed with both extension patterns
- One seed with helper functions + template literal shaders
- One seed with overload-ambiguous bufferData calls
- One complex seed combining most features
```

**Step 7: Verify pytest discovers tests directory**

Run: `cd /home/attekett/git/samples-webgl && source venv/bin/activate && python -m pytest tests/ --collect-only 2>&1 | head -5`

Expected: `no tests ran` or `collected 0 items` (no test files yet, but no import errors).

**Step 8: Commit**

```bash
git add scripts/api_audit/__init__.py scripts/api_audit/__main__.py \
  tests/__init__.py tests/conftest.py \
  tests/fixtures/ requirements.txt
git commit -m "feat: scaffold audit tool package, test infrastructure, and fixtures"
```

---

## Task 2: html_extract + parse (TDD)

**Files:**
- Create: `tests/test_html_extract.py`
- Create: `scripts/api_audit/html_extract.py`
- Create: `scripts/api_audit/parse.py`

**Step 1: Write failing tests**

`tests/test_html_extract.py`:
```python
from api_audit.html_extract import extract_script
from api_audit.parse import parse_js


class TestExtractScript:
    def test_single_script(self):
        html = '<html><body><script>var x = 1;</script></body></html>'
        assert extract_script(html) == 'var x = 1;'

    def test_multiple_scripts_concatenated(self):
        html = '<script>var a = 1;</script><script>var b = 2;</script>'
        result = extract_script(html)
        assert 'var a = 1;' in result
        assert 'var b = 2;' in result

    def test_empty_script(self):
        html = '<script></script>'
        assert extract_script(html) == ''

    def test_malformed_html(self):
        html = '<script>var x = 1;<div>'
        # Should not crash
        result = extract_script(html)
        assert 'var x = 1;' in result

    def test_no_script(self):
        html = '<html><body><p>Hello</p></body></html>'
        assert extract_script(html) == ''


class TestParseJs:
    def test_returns_root_node(self):
        root = parse_js('var x = 1;')
        assert root is not None
        assert root.type == 'program'

    def test_empty_string(self):
        root = parse_js('')
        assert root is not None
        assert root.type == 'program'

    def test_gl_call_is_parseable(self):
        root = parse_js('gl.drawArrays(gl.TRIANGLES, 0, 3);')
        assert root.child_count > 0
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_html_extract.py -v`

Expected: `ModuleNotFoundError: No module named 'api_audit.html_extract'`

**Step 3: Implement html_extract.py and parse.py**

`scripts/api_audit/html_extract.py`:
```python
from bs4 import BeautifulSoup


def extract_script(html: str) -> str:
    """Extract concatenated <script> content from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all('script')
    parts = [s.string or '' for s in scripts]
    return '\n'.join(parts).strip()
```

`scripts/api_audit/parse.py`:
```python
import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser

_JS_LANGUAGE = Language(tsjs.language())
_parser = Parser(_JS_LANGUAGE)


def parse_js(source: str):
    """Parse JavaScript source into a tree-sitter AST. Returns root node."""
    tree = _parser.parse(bytes(source, 'utf-8'))
    return tree.root_node
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_html_extract.py -v`

Expected: All 8 tests PASS.

**Step 5: Commit**

```bash
git add tests/test_html_extract.py scripts/api_audit/html_extract.py scripts/api_audit/parse.py
git commit -m "feat(audit): add html_extract and parse modules with tests"
```

---

## Task 3: const_propagation (TDD)

Implements two-pass const/template/array resolution. No dependency on context detection — operates purely on AST nodes.

**Files:**
- Create: `tests/test_const_propagation.py`
- Create: `scripts/api_audit/const_propagation.py`

**Step 1: Write failing tests**

`tests/test_const_propagation.py`:
```python
import pytest
from api_audit.const_propagation import resolve_constants


class TestResolveConstants:
    def test_gl_constant_alias(self, parse_html):
        """const RGBA = gl.RGBA → resolves to gl.RGBA"""
        root = parse_html('const_gl_alias.html')
        consts = resolve_constants(root)
        assert consts.get('RGBA') == 'gl.RGBA'

    def test_chain_resolution(self, parse_html):
        """const A = gl.RGBA; const FMT = A → FMT resolves to gl.RGBA"""
        root = parse_html('const_gl_alias.html')
        consts = resolve_constants(root)
        assert consts.get('FMT') == 'gl.RGBA'

    def test_forward_reference(self, parse_html):
        """Variable used before declaration resolves in pass 2."""
        root = parse_html('const_forward_ref.html')
        consts = resolve_constants(root)
        assert consts.get('MODE') == 'gl.TRIANGLES'

    def test_template_literal(self, parse_html):
        """Template literal content captured as string."""
        root = parse_html('shader_template.html')
        consts = resolve_constants(root)
        assert 'vs' in consts
        assert '#version 300 es' in consts['vs']

    def test_array_literal(self, parse_html):
        """Array of string literals extracted."""
        root = parse_html('ext_array_pattern.html')
        consts = resolve_constants(root)
        assert consts.get('REQUIRED_EXTENSIONS') == ['EXT_color_buffer_float']

    def test_unresolvable_no_crash(self, parse_html):
        """Function call initializer stays unresolved."""
        root = parse_html('basic_draw.html')
        consts = resolve_constants(root)
        # 'canvas' = document.getElementById('c') is a call, not resolvable
        assert consts.get('canvas') is None
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_const_propagation.py -v`

Expected: `ModuleNotFoundError: No module named 'api_audit.const_propagation'`

**Step 3: Implement const_propagation.py**

`scripts/api_audit/const_propagation.py`:

The module walks the AST in two passes:

- **Pass 1 (collection):** Find all `const`/`let`/`var` declarations. Record each identifier's initializer node without resolving references.
- **Pass 2 (resolution):** Resolve chains. `member_expression` on `gl` → `"gl.CONSTANT"`. `identifier` referencing another const → follow chain. `template_string` → extract text content. `array` of `string` → extract string list. `call_expression` / `new_expression` / others → `None` (unresolvable).

Key tree-sitter node types to handle:
- `variable_declaration` → `variable_declarator` → `.name` (identifier) + `.value` (initializer)
- `member_expression` → `.object` + `.property`
- `template_string` → `.children` where `string_fragment` nodes hold text
- `array` → child `string` nodes

```python
def resolve_constants(root_node) -> dict:
    """Two-pass const resolution. Returns {name: resolved_value}.

    resolved_value is one of:
    - str like "gl.RGBA" for member expressions on gl context
    - str content for template literals
    - list[str] for array literals of strings
    - None for unresolvable expressions (filtered out of returned dict)
    """
    ...
```

Implementation should walk `root_node` recursively collecting `variable_declarator` nodes, then resolve in a second pass. See design doc §4 "Const propagation" for full algorithm.

**Step 4: Run tests to verify they pass**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_const_propagation.py -v`

Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add tests/test_const_propagation.py scripts/api_audit/const_propagation.py
git commit -m "feat(audit): add two-pass const propagation with tests"
```

---

## Task 4: context detection (TDD)

Detects WebGL context variables, API version, extensions (all three patterns), and helper function context tracking.

**Files:**
- Create: `tests/test_context.py`
- Create: `scripts/api_audit/context.py`

**Step 1: Write failing tests**

`tests/test_context.py`:
```python
import pytest
from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants


class TestContextDetection:
    def test_webgl2_context(self, parse_html):
        """getContext('webgl2') → detected as WebGL2."""
        root = parse_html('basic_draw.html')
        ctx = detect_context(root, resolve_constants(root))
        assert ctx.api_version == 'webgl2'
        assert 'gl' in ctx.context_vars

    def test_webgl_fallback(self, parse_html):
        """getContext('webgl2') || getContext('webgl') → tagged as WebGL1-capable."""
        root = parse_html('webgl_fallback.html')
        ctx = detect_context(root, resolve_constants(root))
        assert ctx.api_version == 'webgl1-capable'
        assert 'gl' in ctx.context_vars

    def test_empty_extensions(self, parse_html):
        """No extension calls → empty extension set."""
        root = parse_html('basic_draw.html')
        ctx = detect_context(root, resolve_constants(root))
        assert ctx.extensions == set()

    def test_empty_required_extensions_array(self, parse_html):
        """REQUIRED_EXTENSIONS = [] with forEach → no extensions, no crash."""
        root = parse_html('ext_empty_array.html')
        ctx = detect_context(root, resolve_constants(root))
        assert ctx.extensions == set()


class TestExtensionDetection:
    @pytest.mark.parametrize("fixture,expected_extensions", [
        ("ext_array_pattern.html", {"EXT_color_buffer_float"}),
        ("ext_direct_assign.html", {"OES_vertex_array_object"}),
        ("ext_both_patterns.html", {"EXT_color_buffer_float", "OES_vertex_array_object"}),
        ("ext_bare_enable.html", {"OES_standard_derivatives"}),
    ])
    def test_extension_patterns(self, parse_html, fixture, expected_extensions):
        root = parse_html(fixture)
        ctx = detect_context(root, resolve_constants(root))
        assert ctx.extensions == expected_extensions

    def test_extension_alias_tracked(self, parse_html):
        """Direct assignment creates alias: ext → OES_vertex_array_object."""
        root = parse_html('ext_direct_assign.html')
        ctx = detect_context(root, resolve_constants(root))
        assert ctx.extension_aliases.get('ext') == 'OES_vertex_array_object'

    def test_both_patterns_no_duplicate(self, parse_html):
        """Both patterns in same file: no duplicate extensions."""
        root = parse_html('ext_both_patterns.html')
        ctx = detect_context(root, resolve_constants(root))
        assert len(ctx.extensions) == 2

    def test_bare_enable_no_alias(self, parse_html):
        """Expression statement getExtension: recorded but no alias."""
        root = parse_html('ext_bare_enable.html')
        ctx = detect_context(root, resolve_constants(root))
        assert 'OES_standard_derivatives' in ctx.extensions
        # No variable was assigned
        assert len(ctx.extension_aliases) == 0

    def test_array_pattern_no_alias(self, parse_html):
        """forEach pattern does NOT create extension aliases."""
        root = parse_html('ext_array_pattern.html')
        ctx = detect_context(root, resolve_constants(root))
        assert 'EXT_color_buffer_float' in ctx.extensions
        # forEach callback var 'ext' should not leak as alias
        assert len(ctx.extension_aliases) == 0


class TestHelperFunctions:
    def test_helper_gl_tracked(self, parse_html):
        """createShader(gl, ...) → gl tracked inside function body."""
        root = parse_html('helper_single_level.html')
        ctx = detect_context(root, resolve_constants(root))
        assert 'gl' in ctx.context_vars
        assert ctx.helper_functions  # at least one helper detected
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_context.py -v`

Expected: `ModuleNotFoundError: No module named 'api_audit.context'`

**Step 3: Implement context.py**

`scripts/api_audit/context.py`:

Returns a `ContextInfo` dataclass:

```python
from dataclasses import dataclass, field


@dataclass
class ContextInfo:
    api_version: str = 'unknown'           # 'webgl2', 'webgl', 'unknown'
    context_vars: set = field(default_factory=set)  # {'gl', 'ctx', ...}
    extensions: set = field(default_factory=set)     # {'EXT_color_buffer_float', ...}
    extension_aliases: dict = field(default_factory=dict)  # {'ext': 'OES_vertex_array_object'}
    helper_functions: dict = field(default_factory=dict)   # {'createShader': {'gl_param': 'gl'}}


def detect_context(root_node, resolved_consts: dict) -> ContextInfo:
    """Detect WebGL context, extensions, and helper functions from AST."""
    ...
```

Detection algorithm:
1. Walk AST for `call_expression` where callee is `.getContext('webgl2')` or `.getContext('webgl')`. Record assigned variable name and API version.
2. Walk for `getExtension` calls:
   - As `variable_declarator` init → direct assignment (track alias)
   - As `expression_statement` → bare enable (record extension, no alias)
   - Inside `.forEach` callback on a resolved array → array pattern (record each extension)
3. Walk for `function_declaration` where a parameter name matches a known context var → record as helper function.

See design doc §3 "Context & Alias Detection" for the three extension patterns and helper function tracking.

**Step 4: Run tests to verify they pass**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_context.py -v`

Expected: All 9 tests PASS.

**Step 5: Commit**

```bash
git add tests/test_context.py scripts/api_audit/context.py
git commit -m "feat(audit): add context/extension detection with tests"
```

---

## Task 5: call_analysis (TDD)

Covers basic method call tracking, const-propagated arguments, overload disambiguation, bitwise OR, extension methods, return-value comparison, and unknown receiver filtering.

**Files:**
- Create: `tests/test_call_analysis.py`
- Create: `scripts/api_audit/call_analysis.py`

**Step 1: Write failing tests**

`tests/test_call_analysis.py`:
```python
import pytest
from api_audit.call_analysis import analyze_calls
from api_audit.const_propagation import resolve_constants
from api_audit.context import detect_context


def _analyze(parse_html, fixture, surface):
    """Helper: run full analysis pipeline on a fixture."""
    root = parse_html(fixture)
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    return analyze_calls(root, ctx, consts, surface)


class TestBasicCalls:
    def test_draw_arrays_recorded(self, parse_html, surface):
        """gl.drawArrays(gl.TRIANGLES, 0, 3) → method recorded."""
        result = _analyze(parse_html, 'basic_draw.html', surface)
        assert 'drawArrays' in result.methods

    def test_triangles_in_draw_mode_role(self, parse_html, surface):
        """TRIANGLES recorded in mode parameter position for drawArrays."""
        result = _analyze(parse_html, 'basic_draw.html', surface)
        calls = result.methods['drawArrays']
        # At least one call has TRIANGLES mapped to 'mode' param
        assert any('TRIANGLES' in call.constants for call in calls)
        assert any(call.constant_roles.get('TRIANGLES') == 'mode' for call in calls)

    def test_clear_with_bitmask(self, parse_html, surface):
        """gl.clear(gl.COLOR_BUFFER_BIT) → COLOR_BUFFER_BIT recorded."""
        result = _analyze(parse_html, 'basic_draw.html', surface)
        assert 'clear' in result.methods
        calls = result.methods['clear']
        assert any('COLOR_BUFFER_BIT' in call.constants for call in calls)

    def test_unknown_receiver_ignored(self, parse_html, surface):
        """foo.drawArrays(...) → not recorded."""
        result = _analyze(parse_html, 'basic_draw.html', surface)
        # Only gl.* calls recorded
        for method_name in result.methods:
            assert method_name in surface['methods'] or any(
                method_name in ext['methods']
                for ext in surface['extensions'].values()
            )


class TestConstPropagatedArgs:
    def test_propagated_constant(self, parse_html, surface):
        """const FMT = gl.RGBA; gl.texImage2D(..., FMT, ...) → RGBA recorded."""
        result = _analyze(parse_html, 'const_gl_alias.html', surface)
        assert 'texImage2D' in result.methods
        calls = result.methods['texImage2D']
        assert any('RGBA' in call.constants for call in calls)


class TestOverloadDisambiguation:
    def test_size_overload(self, parse_html, surface):
        """bufferData(target, 1024, usage) → size overload."""
        result = _analyze(parse_html, 'overload_size.html', surface)
        calls = result.methods['bufferData']
        assert any(call.overload_tag == 'size' for call in calls)

    def test_data_overload(self, parse_html, surface):
        """bufferData(target, new Float32Array(...), usage) → data overload."""
        result = _analyze(parse_html, 'overload_data.html', surface)
        calls = result.methods['bufferData']
        assert any(call.overload_tag == 'data' for call in calls)

    def test_arity_disambiguation(self, parse_html, surface):
        """texImage2D with 6 args vs 9 args → correct overload selected."""
        result = _analyze(parse_html, 'const_gl_alias.html', surface)
        calls = result.methods['texImage2D']
        assert any(call.arity == 6 for call in calls)


class TestExtensionMethods:
    def test_extension_method_recorded(self, parse_html, surface):
        """ext.createVertexArrayOES() → recorded under extension."""
        result = _analyze(parse_html, 'ext_direct_assign.html', surface)
        assert 'createVertexArrayOES' in result.extension_methods.get(
            'OES_vertex_array_object', {}
        )


class TestReturnValueComparison:
    def test_framebuffer_complete_comparison(self, parse_html, surface):
        """status === gl.FRAMEBUFFER_COMPLETE → constant recorded in return role."""
        result = _analyze(parse_html, 'return_compare.html', surface)
        assert 'FRAMEBUFFER_COMPLETE' in result.return_constants

    def test_no_error_comparison(self, parse_html, surface):
        """err !== gl.NO_ERROR → NO_ERROR recorded in return role."""
        result = _analyze(parse_html, 'return_compare.html', surface)
        assert 'NO_ERROR' in result.return_constants
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_call_analysis.py -v`

Expected: `ModuleNotFoundError: No module named 'api_audit.call_analysis'`

**Step 3: Implement call_analysis.py**

`scripts/api_audit/call_analysis.py`:

Returns a `CallAnalysisResult` dataclass:

```python
from dataclasses import dataclass, field


@dataclass
class CallRecord:
    constants: set = field(default_factory=set)        # GL constant names used as args
    constant_roles: dict = field(default_factory=dict)  # {const_name: param_name} e.g. {'TRIANGLES': 'mode'}
    arity: int = 0
    overload_tag: str | None = None  # 'size', 'data', or None


@dataclass
class CallAnalysisResult:
    methods: dict = field(default_factory=dict)      # {method_name: [CallRecord]}
    extension_methods: dict = field(default_factory=dict)  # {ext_name: {method_name: [CallRecord]}}
    return_constants: set = field(default_factory=set)  # constants in === / !== comparisons


def analyze_calls(root_node, ctx, consts: dict, surface: dict) -> CallAnalysisResult:
    """Analyze method calls, resolve constants, disambiguate overloads."""
    ...
```

Implementation walks all `call_expression` nodes where the receiver is a known context variable or extension alias. For each argument:
- `member_expression` on `gl` → extract constant name directly
- `identifier` → look up in `consts` dict
- `binary_expression` with `|` operator → recurse into both sides (bitwise OR for bitmask constants)
- `new_expression` → tag as typed data (for overload disambiguation)
- `number` literal → tag as numeric (for overload disambiguation)

For return-value comparison: walk `binary_expression` nodes with `===` or `!==` operator. If one side is a `gl.CONSTANT` member expression, record that constant.

See design doc §5 "Call analysis & Disambiguation" for full algorithm.

**Step 4: Run tests to verify they pass**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_call_analysis.py -v`

Expected: All 11 tests PASS.

**Step 5: Commit**

```bash
git add tests/test_call_analysis.py scripts/api_audit/call_analysis.py
git commit -m "feat(audit): add call analysis with overload disambiguation and tests"
```

---

## Task 6: glsl.py (TDD)

Extracts shader source from `shaderSource()` calls, matches GLSL builtins, strips GLSL comments before matching.

**Files:**
- Create: `tests/test_glsl.py`
- Create: `scripts/api_audit/glsl.py`

**Step 1: Write failing tests**

`tests/test_glsl.py`:
```python
import pytest
from api_audit.glsl import extract_glsl_builtins, strip_glsl_comments


class TestStripGlslComments:
    def test_line_comment(self):
        assert 'texelFetch' not in strip_glsl_comments('// texelFetch(foo)')

    def test_block_comment(self):
        assert 'dFdx' not in strip_glsl_comments('/* dFdx(x) */')

    def test_preserves_code(self):
        result = strip_glsl_comments('vec4 c = texelFetch(t, p, 0);')
        assert 'texelFetch' in result


class TestExtractGlslBuiltins:
    def test_texelfetch_matched(self, parse_html, surface):
        """Shader containing texelFetch(...) → matched."""
        root = parse_html('glsl_builtins.html')
        from api_audit.const_propagation import resolve_constants
        from api_audit.context import detect_context
        consts = resolve_constants(root)
        ctx = detect_context(root, consts)
        builtins = extract_glsl_builtins(root, ctx, consts, surface)
        assert 'texelFetch' in builtins

    def test_packhalf2x16_matched(self, parse_html, surface):
        """Shader containing packHalf2x16(x) → matched."""
        root = parse_html('glsl_builtins.html')
        from api_audit.const_propagation import resolve_constants
        from api_audit.context import detect_context
        consts = resolve_constants(root)
        ctx = detect_context(root, consts)
        builtins = extract_glsl_builtins(root, ctx, consts, surface)
        assert 'packHalf2x16' in builtins

    def test_dfdx_matched(self, parse_html, surface):
        root = parse_html('glsl_builtins.html')
        from api_audit.const_propagation import resolve_constants
        from api_audit.context import detect_context
        consts = resolve_constants(root)
        ctx = detect_context(root, consts)
        builtins = extract_glsl_builtins(root, ctx, consts, surface)
        assert 'dFdx' in builtins

    def test_word_boundary_no_false_positive(self):
        """myTexelFetch(...) should not match texelFetch."""
        from api_audit.glsl import _match_builtins
        all_names = ['texelFetch']
        result = _match_builtins('myTexelFetch(foo);', all_names)
        assert 'texelFetch' not in result

    def test_glsl_comment_not_matched(self):
        """// texelFetch(...) → stripped, not matched."""
        from api_audit.glsl import _match_builtins
        all_names = ['texelFetch']
        code = '// texelFetch(foo)\nvoid main() {}'
        stripped = strip_glsl_comments(code)
        result = _match_builtins(stripped, all_names)
        assert 'texelFetch' not in result

    def test_shader_via_helper_function(self, parse_html, surface):
        """shaderSource inside helper: source traced back to call site argument."""
        root = parse_html('helper_glsl_builtins.html')
        from api_audit.const_propagation import resolve_constants
        from api_audit.context import detect_context
        consts = resolve_constants(root)
        ctx = detect_context(root, consts)
        builtins = extract_glsl_builtins(root, ctx, consts, surface)
        assert 'texelFetch' in builtins

    def test_no_shader_no_crash(self, parse_html, surface):
        """File with no shaderSource calls → empty set."""
        root = parse_html('ext_bare_enable.html')
        from api_audit.const_propagation import resolve_constants
        from api_audit.context import detect_context
        consts = resolve_constants(root)
        ctx = detect_context(root, consts)
        builtins = extract_glsl_builtins(root, ctx, consts, surface)
        assert builtins == set()
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_glsl.py -v`

Expected: FAIL.

**Step 3: Implement glsl.py**

`scripts/api_audit/glsl.py`:

```python
import re


def strip_glsl_comments(source: str) -> str:
    """Remove // and /* */ comments from GLSL source."""
    # Remove block comments first, then line comments
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    source = re.sub(r'//[^\n]*', '', source)
    return source


def _match_builtins(shader_source: str, builtin_names: list[str]) -> set[str]:
    """Match GLSL builtins using word-boundary regex."""
    found = set()
    for name in builtin_names:
        if re.search(rf'\b{re.escape(name)}\s*\(', shader_source):
            found.add(name)
    return found


def extract_glsl_builtins(root_node, ctx, consts: dict, surface: dict) -> set[str]:
    """Extract GLSL builtins from shader sources in the file."""
    ...
```

Implementation:
1. Collect all GLSL builtin names from `surface['glsl_builtins']` (flatten all categories).
2. Walk AST for `shaderSource` calls where receiver is a known context var.
3. Resolve the second argument (shader source) via `consts` dict (template literal).
4. For helper functions: if `shaderSource` is called inside a helper, trace the `source` parameter back to the call site argument and resolve it.
5. Strip GLSL comments from resolved source.
6. Run `_match_builtins` on the stripped source.

**Step 4: Run tests to verify they pass**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_glsl.py -v`

Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add tests/test_glsl.py scripts/api_audit/glsl.py
git commit -m "feat(audit): add GLSL builtin extraction with tests"
```

---

## Task 7: lint.py (TDD)

Detects convention violations that the auditor cannot fully track.

**Files:**
- Create: `tests/test_lint.py`
- Create: `scripts/api_audit/lint.py`

**Step 1: Write failing tests**

`tests/test_lint.py`:
```python
import pytest
from api_audit.lint import check_conventions


class TestLintConventions:
    def test_computed_property_flagged(self, parse_html):
        """gl[methodName]() → flagged as computed property."""
        root = parse_html('lint_violations.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert any('computed' in w.lower() for w in warnings)

    def test_destructuring_flagged(self, parse_html):
        """const { DEPTH_TEST } = gl → flagged."""
        root = parse_html('lint_violations.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert any('destructur' in w.lower() for w in warnings)

    def test_concatenated_shader_flagged(self, parse_html):
        """shaderSource(s, a + b) → flagged."""
        root = parse_html('lint_violations.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert any('concat' in w.lower() or 'shader' in w.lower() for w in warnings)

    def test_multilevel_helper_flagged(self, parse_html):
        """Helper calling another helper with gl → flagged as multi-level indirection."""
        root = parse_html('lint_multilevel.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert any('multi-level' in w.lower() or 'indirection' in w.lower() for w in warnings)

    def test_normal_code_no_flags(self, parse_html):
        """Clean code produces no warnings."""
        root = parse_html('basic_draw.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert warnings == []
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_lint.py -v`

Expected: FAIL.

**Step 3: Implement lint.py**

`scripts/api_audit/lint.py`:

```python
def check_conventions(root_node, context_vars: set) -> list[str]:
    """Check for patterns the auditor cannot track. Returns warning strings."""
    ...
```

Walk AST looking for:
- `subscript_expression` where object is a context var → "Computed property access on WebGL context"
- `variable_declarator` with `object_pattern` init from a context var → "Destructuring of context object"
- `call_expression` for `shaderSource` where second arg is `binary_expression` with `+` → "Concatenated shader source"
- Multi-level helper indirection: build call graph of functions with a `gl` parameter. If function A calls function B and both accept `gl`, flag as "Multi-level indirection detected" (call graph depth > 1)

**Step 4: Run tests to verify they pass**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_lint.py -v`

Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add tests/test_lint.py scripts/api_audit/lint.py
git commit -m "feat(audit): add convention lint with tests"
```

---

## Task 8: report.py (TDD)

Generates tiered gap reports from aggregated call data vs surface JSON. Supports full and delta modes.

**Files:**
- Create: `tests/test_report.py`
- Create: `scripts/api_audit/report.py`

**Step 1: Write failing tests**

`tests/test_report.py`:
```python
import pytest
from api_audit.report import generate_report, generate_delta_report


def _make_coverage(methods_covered, constants_covered, glsl_covered=None,
                   extension_methods=None, return_constants=None):
    """Helper to build a coverage dict matching aggregated call data structure."""
    return {
        'methods': methods_covered,           # {method_name: call_count}
        'constants': constants_covered,       # {const_name: {role: count}}
        'glsl_builtins': glsl_covered or {},  # {name: count}
        'extension_methods': extension_methods or {},
        'return_constants': return_constants or set(),
    }


class TestFullReport:
    def test_tier1_missing_method(self, surface):
        """Method with 0 seeds → appears in Tier 1."""
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},  # only drawArrays covered
            constants_covered={},
        )
        report = generate_report(coverage, surface)
        # checkFramebufferStatus has 0 coverage → Tier 1
        assert 'checkFramebufferStatus' in report.tier1_methods

    def test_tier2_missing_constant_role(self, surface):
        """Constant never used in expected role → Tier 2."""
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={'TRIANGLES': {'draw_mode': 5}},
            # FLOAT never used → should be Tier 2
        )
        report = generate_report(coverage, surface)
        assert any('FLOAT' in gap for gap in report.tier2_gaps)

    def test_covered_method_not_in_gaps(self, surface):
        """Method with >0 seeds → NOT in Tier 1."""
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
        )
        report = generate_report(coverage, surface)
        assert 'drawArrays' not in report.tier1_methods


class TestDeltaReport:
    def test_new_method_coverage(self, surface):
        """New seed covering a Tier 1 gap → reported as 'adds coverage for'."""
        existing_coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
        )
        new_seed_calls = {
            'methods': {'checkFramebufferStatus': 1},
            'constants': {},
            'glsl_builtins': {},
            'extension_methods': {},
            'return_constants': set(),
        }
        delta = generate_delta_report(new_seed_calls, existing_coverage, surface)
        assert 'checkFramebufferStatus' in delta.new_method_coverage

    def test_redundant_method(self, surface):
        """Seed exercising already-covered method → reported as redundant."""
        existing_coverage = _make_coverage(
            methods_covered={'drawArrays': 50},
            constants_covered={},
        )
        new_seed_calls = {
            'methods': {'drawArrays': 1},
            'constants': {},
            'glsl_builtins': {},
            'extension_methods': {},
            'return_constants': set(),
        }
        delta = generate_delta_report(new_seed_calls, existing_coverage, surface)
        assert 'drawArrays' in delta.redundant

    def test_delta_no_prior_cache(self, surface):
        """Delta mode with no existing coverage → falls back gracefully with warning."""
        new_seed_calls = {
            'methods': {'drawArrays': 1},
            'constants': {},
            'glsl_builtins': {},
            'extension_methods': {},
            'return_constants': set(),
        }
        delta = generate_delta_report(new_seed_calls, None, surface)
        assert delta.fallback_warning is not None
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_report.py -v`

Expected: FAIL.

**Step 3: Implement report.py**

`scripts/api_audit/report.py`:

```python
from dataclasses import dataclass, field


@dataclass
class GapReport:
    tier1_methods: list = field(default_factory=list)     # method names with 0 coverage
    tier2_gaps: list = field(default_factory=list)         # "CONSTANT as role: 0 seeds"
    tier3_ambiguous: list = field(default_factory=list)    # ambiguous overloads, missing GLSL
    total_methods: int = 0
    covered_methods: int = 0


@dataclass
class DeltaReport:
    new_method_coverage: list = field(default_factory=list)    # methods this seed newly covers
    new_constant_coverage: list = field(default_factory=list)  # constants this seed newly covers
    redundant: list = field(default_factory=list)              # already well-covered items
    fallback_warning: str | None = None                        # set when no prior cache exists


def generate_report(coverage: dict, surface: dict) -> GapReport:
    """Generate tiered gap report from aggregated coverage vs surface."""
    ...


def generate_delta_report(new_seed_calls: dict, existing_coverage: dict,
                          surface: dict) -> DeltaReport:
    """Compare new seed's calls against existing coverage."""
    ...
```

Implementation:
- `generate_report`: iterate all methods in `surface['methods']`. If method not in `coverage['methods']` → Tier 1. For each constant in `surface['constants']`, check if it appears in `coverage['constants']` with at least one of its expected roles → Tier 2 if missing. GLSL builtins not matched → Tier 3.
- `generate_delta_report`: for each method/constant in `new_seed_calls`, check if it was at 0 in `existing_coverage` → new coverage. If already well-covered (>3 seeds) → redundant.

**Step 4: Run tests to verify they pass**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_report.py -v`

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add tests/test_report.py scripts/api_audit/report.py
git commit -m "feat(audit): add gap report generation with delta mode and tests"
```

---

## Task 9: cache.py (TDD)

Two-layer SHA256-keyed caching. Layer 1: per-file parse cache. Layer 2: coverage evaluation cache.

**Files:**
- Create: `tests/test_cache.py`
- Create: `scripts/api_audit/cache.py`

**Step 1: Write failing tests**

`tests/test_cache.py`:
```python
import pytest
import json
from api_audit.cache import FileCache


class TestFileCache:
    def test_cache_hit(self, tmp_path):
        """Same content → cache hit, returns stored data."""
        cache = FileCache(tmp_path / 'cache')
        data = {'methods': {'drawArrays': 1}}
        cache.store('file.html', 'content_abc', data)
        result = cache.lookup('file.html', 'content_abc')
        assert result == data

    def test_cache_miss_different_content(self, tmp_path):
        """Modified content → cache miss."""
        cache = FileCache(tmp_path / 'cache')
        cache.store('file.html', 'content_v1', {'methods': {}})
        result = cache.lookup('file.html', 'content_v2')
        assert result is None

    def test_cache_dir_created(self, tmp_path):
        """Cache directory created automatically."""
        cache_dir = tmp_path / 'nonexistent' / 'cache'
        cache = FileCache(cache_dir)
        cache.store('f.html', 'content', {})
        assert cache_dir.exists()

    def test_layer2_hit(self, tmp_path):
        """Same surface + same aggregated data → Layer 2 hit."""
        cache = FileCache(tmp_path / 'cache')
        surface_hash = 'surface_abc'
        agg_hash = 'agg_xyz'
        report = {'tier1': ['method1']}
        cache.store_evaluation(surface_hash, agg_hash, report)
        result = cache.lookup_evaluation(surface_hash, agg_hash)
        assert result == report

    def test_layer2_miss_surface_change(self, tmp_path):
        """Changed surface JSON → Layer 2 miss."""
        cache = FileCache(tmp_path / 'cache')
        cache.store_evaluation('surface_v1', 'agg_xyz', {'tier1': []})
        result = cache.lookup_evaluation('surface_v2', 'agg_xyz')
        assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_cache.py -v`

Expected: FAIL.

**Step 3: Implement cache.py**

`scripts/api_audit/cache.py`:

```python
import hashlib
import json
from pathlib import Path


class FileCache:
    """Two-layer SHA256-keyed cache for audit results."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self._layer1_dir = self.cache_dir / 'files'
        self._layer2_dir = self.cache_dir / 'eval'

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def store(self, filename: str, content: str, data: dict):
        """Layer 1: store per-file parse results keyed by content hash."""
        ...

    def lookup(self, filename: str, content: str) -> dict | None:
        """Layer 1: look up cached parse results."""
        ...

    def store_evaluation(self, surface_hash: str, agg_hash: str, report: dict):
        """Layer 2: store evaluation results keyed by surface + aggregated data."""
        ...

    def lookup_evaluation(self, surface_hash: str, agg_hash: str) -> dict | None:
        """Layer 2: look up cached evaluation."""
        ...
```

Implementation uses JSON files in the cache directory, keyed by SHA256 hashes. Layer 1 files are stored under `files/{content_hash}.json`. Layer 2 files under `eval/{surface_hash}_{agg_hash}.json`.

**Step 4: Run tests to verify they pass**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_cache.py -v`

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add tests/test_cache.py scripts/api_audit/cache.py
git commit -m "feat(audit): add two-layer SHA256 cache with tests"
```

---

## Task 10: CLI entry point (__main__.py)

Wires all modules into the `python -m api_audit` command.

**Files:**
- Modify: `scripts/api_audit/__main__.py`

**Step 1: Implement CLI**

`scripts/api_audit/__main__.py`:

```python
"""CLI entry point for the WebGL API surface auditor."""
import argparse
import json
import sys
import hashlib
from pathlib import Path

from api_audit.html_extract import extract_script
from api_audit.parse import parse_js
from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants
from api_audit.call_analysis import analyze_calls
from api_audit.glsl import extract_glsl_builtins
from api_audit.lint import check_conventions
from api_audit.cache import FileCache
from api_audit.report import generate_report, generate_delta_report


def analyze_file(filepath: Path, surface: dict, cache: FileCache | None = None):
    """Run full analysis pipeline on a single HTML file.
    Returns per-file call data dict.
    """
    content = filepath.read_text()

    if cache:
        cached = cache.lookup(filepath.name, content)
        if cached:
            return cached

    script = extract_script(content)
    if not script.strip():
        return None

    root = parse_js(script)
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    calls = analyze_calls(root, ctx, consts, surface)
    glsl = extract_glsl_builtins(root, ctx, consts, surface)
    warnings = check_conventions(root, context_vars=ctx.context_vars)

    result = {
        'file': str(filepath),
        'methods': {k: len(v) for k, v in calls.methods.items()},
        'constants': {},  # aggregate constant usage with roles
        'glsl_builtins': {name: 1 for name in glsl},
        'extension_methods': calls.extension_methods,
        'return_constants': list(calls.return_constants),
        'lint_warnings': warnings,
    }

    # Aggregate constant roles from call records
    for method_name, call_records in calls.methods.items():
        for call in call_records:
            for const_name in call.constants:
                if const_name not in result['constants']:
                    result['constants'][const_name] = {}
                # Role tracking derived from surface method params
                # (implementation detail)

    if cache:
        cache.store(filepath.name, content, result)

    return result


def aggregate_results(results: list[dict]) -> dict:
    """Merge per-file results into corpus-wide coverage."""
    ...


def main():
    parser = argparse.ArgumentParser(description='WebGL API Surface Auditor')
    parser.add_argument('--surface', type=Path, default=Path('docs/webgl_api_surface.json'),
                        help='Path to API surface JSON')
    parser.add_argument('--file', type=Path, default=None,
                        help='Single file delta mode')
    parser.add_argument('--cache-dir', type=Path, default=Path('.cache/api_audit'),
                        help='Cache directory')
    parser.add_argument('--corpus-dirs', nargs='+', type=Path,
                        default=[Path('samples-webgl'), Path('agent_outputs')],
                        help='Corpus directories to scan')
    parser.add_argument('--output', type=Path, default=Path('docs/api_coverage_report.md'),
                        help='Output report path')
    args = parser.parse_args()

    surface = json.loads(args.surface.read_text())
    cache = FileCache(args.cache_dir)

    if args.file:
        # Delta mode
        result = analyze_file(args.file, surface)
        # Load existing coverage from cache...
        # generate_delta_report(...)
        ...
    else:
        # Full corpus mode
        html_files = []
        for d in args.corpus_dirs:
            if d.exists():
                html_files.extend(d.rglob('*.html'))

        results = []
        for f in sorted(html_files):
            result = analyze_file(f, surface, cache)
            if result:
                results.append(result)

        coverage = aggregate_results(results)
        report = generate_report(coverage, surface)
        # Write report to output path
        ...

    print(f'Analyzed {len(results) if not args.file else 1} files')


if __name__ == '__main__':
    main()
```

**Step 2: Verify the CLI runs (help only)**

Run: `cd /home/attekett/git/samples-webgl && python -m api_audit --help` (from scripts/ or with PYTHONPATH)

Actually, since the package is at `scripts/api_audit/`, run:

Run: `cd /home/attekett/git/samples-webgl && PYTHONPATH=scripts python -m api_audit --help`

Expected: Help text printed, exit 0.

**Step 3: Commit**

```bash
git add scripts/api_audit/__main__.py
git commit -m "feat(audit): add CLI entry point wiring all modules"
```

---

## Task 11: Integration tests with pinned seeds

Copy 3-5 real corpus seeds, create expected_output.json for each, write integration test.

**Files:**
- Create: `tests/test_integration.py`
- Copy: `tests/fixtures/seeds/seed_minimal_test.html` (from `samples-webgl/seeds/`)
- Copy: `tests/fixtures/seeds/extensions_color_buffer_float_rendering.html` (from `samples-webgl/extensions/`)
- Copy: `tests/fixtures/seeds/seed_integer_sync_transform_mrt_instanced.html` (from `samples-webgl/seeds/`)
- Copy: `tests/fixtures/seeds/compute_procedural_geometry.html` (from `samples-webgl/compute/`)
- Create: `tests/fixtures/seeds/seed_minimal_test_expected.json`
- Create: `tests/fixtures/seeds/extensions_color_buffer_float_rendering_expected.json`
- Create: `tests/fixtures/seeds/seed_integer_sync_transform_mrt_instanced_expected.json`
- Create: `tests/fixtures/seeds/compute_procedural_geometry_expected.json`

**Step 1: Copy pinned seeds**

Run:
```bash
cp samples-webgl/seeds/seed_minimal_test.html tests/fixtures/seeds/
cp samples-webgl/extensions/extensions_color_buffer_float_rendering.html tests/fixtures/seeds/
cp samples-webgl/seeds/seed_integer_sync_transform_mrt_instanced.html tests/fixtures/seeds/
cp samples-webgl/compute/compute_procedural_geometry.html tests/fixtures/seeds/
```

**Step 2: Generate expected output by running auditor on each seed**

Run the auditor on each pinned seed manually and inspect the output. Save verified results as `*_expected.json`. Each expected file contains:

```json
{
  "expected_methods": ["drawArrays", "bufferData", "shaderSource", ...],
  "expected_extensions": ["EXT_color_buffer_float"],
  "expected_context": "webgl2",
  "min_method_count": 5
}
```

The exact contents depend on what's actually in each seed. Run the auditor and inspect — do NOT guess.

**Step 3: Write integration test**

`tests/test_integration.py`:
```python
import json
import pytest
from pathlib import Path
from api_audit.html_extract import extract_script
from api_audit.parse import parse_js
from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants
from api_audit.call_analysis import analyze_calls
from api_audit.glsl import extract_glsl_builtins

SEEDS = Path(__file__).parent / "fixtures" / "seeds"


def _full_pipeline(filepath: Path, surface: dict):
    """Run complete analysis pipeline on a file."""
    html = filepath.read_text()
    script = extract_script(html)
    root = parse_js(script)
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    calls = analyze_calls(root, ctx, consts, surface)
    glsl = extract_glsl_builtins(root, ctx, consts, surface)
    return {
        'methods': set(calls.methods.keys()),
        'extensions': ctx.extensions,
        'context': ctx.api_version,
        'glsl_builtins': glsl,
    }


def _load_expected(seed_name):
    expected_path = SEEDS / f"{seed_name}_expected.json"
    if not expected_path.exists():
        pytest.skip(f"Expected output not yet created: {expected_path}")
    return json.loads(expected_path.read_text())


@pytest.fixture
def real_surface():
    """Load real surface JSON if available, else skip."""
    surface_path = Path('docs/webgl_api_surface.json')
    if not surface_path.exists():
        # Fall back to test surface for initial development
        surface_path = Path(__file__).parent / 'fixtures' / 'surface' / 'test_surface.json'
    return json.loads(surface_path.read_text())


class TestPinnedSeeds:
    @pytest.mark.parametrize("seed_file", [
        "seed_minimal_test.html",
        "extensions_color_buffer_float_rendering.html",
        "seed_integer_sync_transform_mrt_instanced.html",
        "compute_procedural_geometry.html",
    ])
    def test_methods_detected(self, seed_file, real_surface):
        filepath = SEEDS / seed_file
        if not filepath.exists():
            pytest.skip(f"Pinned seed not yet copied: {filepath}")
        result = _full_pipeline(filepath, real_surface)
        expected = _load_expected(seed_file.replace('.html', ''))
        for method in expected.get('expected_methods', []):
            assert method in result['methods'], f"Missing method: {method}"

    @pytest.mark.parametrize("seed_file", [
        "seed_minimal_test.html",
        "extensions_color_buffer_float_rendering.html",
        "seed_integer_sync_transform_mrt_instanced.html",
        "compute_procedural_geometry.html",
    ])
    def test_context_detected(self, seed_file, real_surface):
        filepath = SEEDS / seed_file
        if not filepath.exists():
            pytest.skip(f"Pinned seed not yet copied: {filepath}")
        result = _full_pipeline(filepath, real_surface)
        expected = _load_expected(seed_file.replace('.html', ''))
        assert result['context'] == expected.get('expected_context', 'webgl2')

    @pytest.mark.parametrize("seed_file", [
        "extensions_color_buffer_float_rendering.html",
    ])
    def test_extensions_detected(self, seed_file, real_surface):
        filepath = SEEDS / seed_file
        if not filepath.exists():
            pytest.skip(f"Pinned seed not yet copied: {filepath}")
        result = _full_pipeline(filepath, real_surface)
        expected = _load_expected(seed_file.replace('.html', ''))
        for ext in expected.get('expected_extensions', []):
            assert ext in result['extensions'], f"Missing extension: {ext}"
```

**Step 4: Run integration tests**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/test_integration.py -v`

Expected: Tests pass (or skip if expected_output.json not yet created).

**Step 5: Create expected output files by inspecting auditor output**

After running the auditor on each pinned seed, create the `*_expected.json` files with verified data.

**Step 6: Commit**

```bash
git add tests/test_integration.py tests/fixtures/seeds/
git commit -m "feat(audit): add integration tests with pinned corpus seeds"
```

---

## Task 12: IDL Extraction Script

Build `scripts/extract_webidl.js` from the existing prototype (`scripts/extract_webidl_proto.js`). This is the M1 milestone — produces `docs/webgl_api_surface.json`.

**Files:**
- Create: `scripts/extract_webidl.js` (full script, extend proto)
- Output: `docs/webgl_api_surface.json` (committed artifact)

**Step 1: Read the prototype and design doc extraction section**

Read:
- `scripts/extract_webidl_proto.js` — existing Tier A block scraping
- Design doc §"Extraction process" — full specification
- Design doc §"Constant role mapping — hybrid approach" — Tier A/B/C strategy

**Step 2: Implement extraction script**

`scripts/extract_webidl.js` extends the prototype with:

1. **Core IDL parsing** (already prototyped): `webidl2.parse()` on cached `.idl` files. Extract methods (with overloads, arities, parameter names/types) and constants (with values).

2. **Tier A — Block comment scraping** (already prototyped): Parse `/* GroupName */` comments in WebGL1 IDL to assign roles. ~159 constants tagged automatically.

3. **Tier B — Manual mapping table**: A hardcoded object mapping ~150 WebGL2 constant names to roles. Organized by role group per design doc §"Tier B". This is the largest single effort.

   ```javascript
   const TIER_B_ROLES = {
     // buffer_usage (WebGL2 additions)
     'STREAM_READ': ['buffer_usage'], 'STREAM_COPY': ['buffer_usage'],
     'STATIC_READ': ['buffer_usage'], 'STATIC_COPY': ['buffer_usage'],
     'DYNAMIC_READ': ['buffer_usage'], 'DYNAMIC_COPY': ['buffer_usage'],
     // buffer_target
     'COPY_READ_BUFFER': ['buffer_target'], 'COPY_WRITE_BUFFER': ['buffer_target'],
     'PIXEL_PACK_BUFFER': ['buffer_target'], 'PIXEL_UNPACK_BUFFER': ['buffer_target'],
     'UNIFORM_BUFFER': ['buffer_target'], 'TRANSFORM_FEEDBACK_BUFFER': ['buffer_target'],
     // ... ~140 more entries organized by role group
   };
   ```

   **Methodology**: For each WebGL2 constant not tagged by Tier A, look up in the [WebGL 2.0 spec](https://registry.khronos.org/webgl/specs/latest/2.0/) and/or MDN to determine which method parameter(s) accept it. Record the role(s). Add a comment with the provenance source.

4. **Tier C — Heuristics**: `_BIT` suffix + power-of-two → `buffer_bit` / `bitmask`. Sized format suffixes → `sized_internalformat`. `INVALID_` prefix → `error_code`. `PACK_`/`UNPACK_` prefix → `pixel_store`.

5. **Kind classification**: All constants get `"kind": "bitmask"` if `_BIT` suffix + power-of-two value, else `"kind": "enum"`.

6. **Extension XML parsing**: Download `extension.xml` for each extension, extract `<idl>` content, parse with `webidl2`. Handle empty extensions (no methods/constants) and parser failures (skip with warning).

7. **GLSL builtins**: Hardcode the categorized list from the design doc §"glsl_builtins" section of the JSON schema.

8. **Canary checks**:
   - Fail if <150 unique method names
   - Fail if <300 constants
   - Warn if <20 extensions parsed
   - Warn if Tier A produces <100 constants
   - Fail if any WebGL2 constant is unclassified after all tiers

9. **Output**: Write `docs/webgl_api_surface.json` following the schema v3.0.

**Step 3: Install fast-xml-parser for extension XML parsing**

Run: `cd /home/attekett/git/samples-webgl && npm install fast-xml-parser`

**Step 4: Run the extraction script**

Run: `cd /home/attekett/git/samples-webgl && node scripts/extract_webidl.js`

Expected: `docs/webgl_api_surface.json` created, all canary checks pass.

**Step 5: Validate output**

Run: `node -e "const s = require('./docs/webgl_api_surface.json'); console.log('Methods:', Object.keys(s.methods).length, 'Constants:', Object.keys(s.constants).length, 'Extensions:', Object.keys(s.extensions).length)"`

Expected: Methods: ~183, Constants: ~361, Extensions: ~20+.

**Step 6: Commit**

```bash
git add scripts/extract_webidl.js docs/webgl_api_surface.json package.json
git commit -m "feat: add IDL extraction script producing webgl_api_surface.json (M1)"
```

---

## Task 13: Full pipeline smoke test

Run the complete auditor against the real corpus with the real surface JSON. Verify sanity of output.

**Files:**
- No new files created

**Step 1: Run full test suite**

Run: `cd /home/attekett/git/samples-webgl && python -m pytest tests/ -v`

Expected: All tests PASS.

**Step 2: Run auditor on full corpus**

Run: `cd /home/attekett/git/samples-webgl && PYTHONPATH=scripts python -m api_audit`

Expected: Analyzes 367 files, produces `docs/api_coverage_report.md`.

**Step 3: Inspect report for sanity**

Check that:
- Tier 1 lists fewer than ~20 missing methods (most of ~183 should be covered)
- Tier 2 identifies specific constant/role gaps
- No crash or unhandled exception

**Step 4: Run delta mode on a single seed**

Run: `cd /home/attekett/git/samples-webgl && PYTHONPATH=scripts python -m api_audit --file agent_outputs/mutation_b1_s1_mrt_float_blend.html`

Expected: Delta report showing which gaps this seed covers.

**Step 5: Update integration test expected outputs with real surface**

Re-run integration tests against `docs/webgl_api_surface.json` (not test surface). Update `*_expected.json` files if needed.

**Step 6: Final commit**

```bash
git add docs/api_coverage_report.md tests/fixtures/seeds/*_expected.json
git commit -m "feat: complete API surface auditor - full pipeline validated (M2-M5)"
```

---

## Dependency graph

```
Task 1 (scaffolding)
  ├── Task 2 (html_extract + parse)
  │     ├── Task 3 (const_propagation)
  │     │     ├── Task 5 (call_analysis) ← also needs Task 4
  │     │     └── Task 6 (glsl)
  │     ├── Task 4 (context)
  │     │     └── Task 5 (call_analysis)
  │     └── Task 7 (lint)
  ├── Task 8 (report)  ← needs Task 5 for result types
  ├── Task 9 (cache)   ← standalone, uses primitives only
  └── Task 10 (CLI)    ← needs all modules
        └── Task 11 (integration tests) ← needs CLI + pinned seeds
              └── Task 13 (smoke test) ← needs Task 12

Task 12 (IDL extraction) ← independent of Tasks 2-11, can run in parallel
  └── Task 13 (smoke test)
```

**Parallelizable pairs** (if using subagent-driven development):
- Task 3 + Task 4 (const_propagation + context — both depend only on Task 2)
- Task 6 + Task 7 (glsl + lint — independent of each other)
- Task 8 + Task 9 (report + cache — independent of each other)
- Task 12 (IDL extraction) can run in parallel with any Python task

## Notes for implementer

1. **Import path**: `conftest.py` adds `scripts/` to `sys.path`. All imports use `from api_audit.xxx import yyy`.

2. **tree-sitter API**: The modern tree-sitter (v0.22+) API is used. Node traversal: `node.children`, `node.type`, `node.text` (bytes), `node.child_by_field_name('field')`. See tree-sitter Python docs.

3. **AST node types** (tree-sitter-javascript): `variable_declaration`, `variable_declarator`, `call_expression`, `member_expression`, `identifier`, `string`, `template_string`, `string_fragment`, `binary_expression`, `new_expression`, `number`, `array`, `arrow_function`, `function_declaration`, `subscript_expression`, `object_pattern`.

4. **Tier B is the bottleneck**: The manual constant mapping table (~150 entries) is the most tedious part of Task 12. Build incrementally — start with the high-frequency role groups (sized_internalformat ~56, get_parameter ~35) and add the rest.

5. **Run tests after every change**: `python -m pytest tests/ -v --tb=short` should complete in <10 seconds.
