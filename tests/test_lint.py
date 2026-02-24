import pytest
from api_audit.lint import check_conventions


class TestLintConventions:
    def test_computed_property_flagged(self, parse_html):
        """gl[methodName]() -> flagged as computed property."""
        root = parse_html('lint_violations.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert any('computed' in w.lower() for w in warnings)

    def test_destructuring_flagged(self, parse_html):
        """const { DEPTH_TEST } = gl -> flagged."""
        root = parse_html('lint_violations.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert any('destructur' in w.lower() for w in warnings)

    def test_concatenated_shader_flagged(self, parse_html):
        """shaderSource(s, a + b) -> flagged."""
        root = parse_html('lint_violations.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert any('concat' in w.lower() or 'shader' in w.lower() for w in warnings)

    def test_multilevel_helper_flagged(self, parse_html):
        """Helper calling another helper with gl -> flagged as multi-level indirection."""
        root = parse_html('lint_multilevel.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert any('multi-level' in w.lower() or 'indirection' in w.lower() for w in warnings)

    def test_normal_code_no_flags(self, parse_html):
        """Clean code produces no warnings."""
        root = parse_html('basic_draw.html')
        warnings = check_conventions(root, context_vars={'gl'})
        assert warnings == []
