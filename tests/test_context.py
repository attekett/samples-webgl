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
        assert len(ctx.extension_aliases) == 0

    def test_array_pattern_no_alias(self, parse_html):
        """forEach pattern does NOT create extension aliases."""
        root = parse_html('ext_array_pattern.html')
        ctx = detect_context(root, resolve_constants(root))
        assert 'EXT_color_buffer_float' in ctx.extensions
        assert len(ctx.extension_aliases) == 0


class TestHelperFunctions:
    def test_helper_gl_tracked(self, parse_html):
        """createShader(gl, ...) → gl tracked inside function body."""
        root = parse_html('helper_single_level.html')
        ctx = detect_context(root, resolve_constants(root))
        assert 'gl' in ctx.context_vars
        assert ctx.helper_functions  # at least one helper detected
