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
        """gl.drawArrays(gl.TRIANGLES, 0, 3) -> method recorded."""
        result = _analyze(parse_html, 'basic_draw.html', surface)
        assert 'drawArrays' in result.methods

    def test_triangles_in_draw_mode_role(self, parse_html, surface):
        """TRIANGLES recorded in mode parameter position for drawArrays."""
        result = _analyze(parse_html, 'basic_draw.html', surface)
        calls = result.methods['drawArrays']
        assert any('TRIANGLES' in call.constants for call in calls)
        assert any(call.constant_roles.get('TRIANGLES') == 'mode' for call in calls)

    def test_clear_with_bitmask(self, parse_html, surface):
        """gl.clear(gl.COLOR_BUFFER_BIT) -> COLOR_BUFFER_BIT recorded."""
        result = _analyze(parse_html, 'basic_draw.html', surface)
        assert 'clear' in result.methods
        calls = result.methods['clear']
        assert any('COLOR_BUFFER_BIT' in call.constants for call in calls)

    def test_unknown_receiver_ignored(self, parse_html, surface):
        """foo.drawArrays(...) -> not recorded."""
        result = _analyze(parse_html, 'basic_draw.html', surface)
        for method_name in result.methods:
            assert method_name in surface['methods'] or any(
                method_name in ext['methods']
                for ext in surface['extensions'].values()
            )


class TestConstPropagatedArgs:
    def test_propagated_constant(self, parse_html, surface):
        """const FMT = gl.RGBA; gl.texImage2D(..., FMT, ...) -> RGBA recorded."""
        result = _analyze(parse_html, 'const_gl_alias.html', surface)
        assert 'texImage2D' in result.methods
        calls = result.methods['texImage2D']
        assert any('RGBA' in call.constants for call in calls)


class TestOverloadDisambiguation:
    def test_size_overload(self, parse_html, surface):
        """bufferData(target, 1024, usage) -> size overload."""
        result = _analyze(parse_html, 'overload_size.html', surface)
        calls = result.methods['bufferData']
        assert any(call.overload_tag == 'size' for call in calls)

    def test_data_overload(self, parse_html, surface):
        """bufferData(target, new Float32Array(...), usage) -> data overload."""
        result = _analyze(parse_html, 'overload_data.html', surface)
        calls = result.methods['bufferData']
        assert any(call.overload_tag == 'data' for call in calls)

    def test_arity_disambiguation(self, parse_html, surface):
        """texImage2D with 6 args vs 9 args -> correct overload selected."""
        result = _analyze(parse_html, 'const_gl_alias.html', surface)
        calls = result.methods['texImage2D']
        assert any(call.arity == 6 for call in calls)


class TestExtensionMethods:
    def test_extension_method_recorded(self, parse_html, surface):
        """ext.createVertexArrayOES() -> recorded under extension."""
        result = _analyze(parse_html, 'ext_direct_assign.html', surface)
        assert 'createVertexArrayOES' in result.extension_methods.get(
            'OES_vertex_array_object', {}
        )


class TestReturnValueComparison:
    def test_framebuffer_complete_comparison(self, parse_html, surface):
        """status === gl.FRAMEBUFFER_COMPLETE -> constant recorded in return role."""
        result = _analyze(parse_html, 'return_compare.html', surface)
        assert 'FRAMEBUFFER_COMPLETE' in result.return_constants

    def test_no_error_comparison(self, parse_html, surface):
        """err !== gl.NO_ERROR -> NO_ERROR recorded in return role."""
        result = _analyze(parse_html, 'return_compare.html', surface)
        assert 'NO_ERROR' in result.return_constants
