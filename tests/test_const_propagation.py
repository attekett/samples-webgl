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
