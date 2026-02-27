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


class TestTier3ExtraBuiltins:
    """Bug 3: extra_glsl_builtins should appear in Tier 3 when uncovered."""

    def test_extra_glsl_builtins_appear_in_tier3_gaps(self, surface):
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
            glsl_covered={},
        )
        report = generate_report(coverage, surface,
                                 extra_glsl_builtins=['smoothstep', 'refract'])
        tier3_names = [g for g in report.tier3_ambiguous]
        assert any('smoothstep' in g for g in tier3_names)
        assert any('refract' in g for g in tier3_names)

    def test_extra_glsl_covered_not_in_gaps(self, surface):
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
            glsl_covered={'smoothstep': 3},
        )
        report = generate_report(coverage, surface,
                                 extra_glsl_builtins=['smoothstep'])
        assert not any('smoothstep' in g for g in report.tier3_ambiguous)

    def test_backward_compatible_without_extra(self, surface):
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
            glsl_covered={},
        )
        report = generate_report(coverage, surface)
        assert not any('smoothstep' in g for g in report.tier3_ambiguous)

    def test_extra_glsl_deduplication(self, surface):
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
            glsl_covered={},
        )
        report = generate_report(coverage, surface,
                                 extra_glsl_builtins=['texelFetch'])
        count = sum(1 for g in report.tier3_ambiguous if 'texelFetch' in g)
        assert count == 1

    def test_empty_extra_builtins_list(self, surface):
        coverage = _make_coverage(
            methods_covered={'drawArrays': 5},
            constants_covered={},
            glsl_covered={},
        )
        base = generate_report(coverage, surface)
        with_empty = generate_report(coverage, surface,
                                     extra_glsl_builtins=[])
        assert base.tier3_ambiguous == with_empty.tier3_ambiguous
