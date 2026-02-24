import pytest
from api_audit.report import generate_report, generate_delta_report


def _make_coverage(methods_covered, constants_covered, glsl_covered=None,
                   extension_methods=None, return_constants=None):
    """Helper to build a coverage dict matching aggregated call data structure."""
    return {
        'methods': methods_covered,
        'constants': constants_covered,
        'glsl_builtins': glsl_covered or {},
        'extension_methods': extension_methods or {},
        'return_constants': return_constants or set(),
    }


class TestFullReport:
    def test_tier1_missing_method(self, surface):
        """Method with 0 seeds -> appears in Tier 1."""
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
        )
        report = generate_report(coverage, surface)
        assert 'checkFramebufferStatus' in report.tier1_methods

    def test_tier2_missing_constant_role(self, surface):
        """Constant never used in expected role -> Tier 2."""
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={'TRIANGLES': {'draw_mode': 5}},
        )
        report = generate_report(coverage, surface)
        assert any('FLOAT' in gap for gap in report.tier2_gaps)

    def test_covered_method_not_in_gaps(self, surface):
        """Method with >0 seeds -> NOT in Tier 1."""
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
        )
        report = generate_report(coverage, surface)
        assert 'drawArrays' not in report.tier1_methods


class TestDeltaReport:
    def test_new_method_coverage(self, surface):
        """New seed covering a Tier 1 gap -> reported."""
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
        """Seed exercising already-covered method -> reported as redundant."""
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
        """Delta mode with no existing coverage -> falls back gracefully with warning."""
        new_seed_calls = {
            'methods': {'drawArrays': 1},
            'constants': {},
            'glsl_builtins': {},
            'extension_methods': {},
            'return_constants': set(),
        }
        delta = generate_delta_report(new_seed_calls, None, surface)
        assert delta.fallback_warning is not None
