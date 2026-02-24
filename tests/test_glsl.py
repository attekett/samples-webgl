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

    def test_shader_inside_async_main(self, parse_html, surface):
        """shaderSource inside async function main() → builtins detected."""
        root = parse_html('glsl_inside_main.html')
        from api_audit.const_propagation import resolve_constants
        from api_audit.context import detect_context
        consts = resolve_constants(root)
        ctx = detect_context(root, consts)
        builtins = extract_glsl_builtins(root, ctx, consts, surface)
        assert 'texelFetch' in builtins
        assert 'dFdx' in builtins

    def test_no_shader_no_crash(self, parse_html, surface):
        """File with no shaderSource calls → empty set."""
        root = parse_html('ext_bare_enable.html')
        from api_audit.const_propagation import resolve_constants
        from api_audit.context import detect_context
        consts = resolve_constants(root)
        ctx = detect_context(root, consts)
        builtins = extract_glsl_builtins(root, ctx, consts, surface)
        assert builtins == set()
