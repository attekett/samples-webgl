"""Gap report generation: tiered reports from aggregated coverage vs API surface.

Supports full mode (complete gap analysis) and delta mode (incremental seed
evaluation against existing coverage).
"""

from __future__ import annotations

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
    new_method_coverage: list = field(default_factory=list)
    new_constant_coverage: list = field(default_factory=list)
    redundant: list = field(default_factory=list)
    fallback_warning: str | None = None


def generate_report(coverage: dict, surface: dict) -> GapReport:
    """Generate tiered gap report from aggregated coverage vs surface.

    Args:
        coverage: Aggregated call data with keys 'methods', 'constants',
                  'glsl_builtins', 'extension_methods', 'return_constants'.
        surface: API surface dict (test_surface.json structure).

    Returns:
        GapReport with tier1 (uncovered methods), tier2 (uncovered constant
        roles), and tier3 (missing GLSL builtins) gaps.
    """
    report = GapReport()
    covered_methods = coverage.get('methods', {})

    # Tier 1: methods with zero coverage
    all_methods = surface.get('methods', {})
    report.total_methods = len(all_methods)

    for method_name in all_methods:
        count = covered_methods.get(method_name, 0)
        if count > 0:
            report.covered_methods += 1
        else:
            report.tier1_methods.append(method_name)

    # Tier 2: constants not covered in at least one of their expected roles
    covered_constants = coverage.get('constants', {})
    all_constants = surface.get('constants', {})

    for const_name, const_info in all_constants.items():
        roles = const_info.get('roles', [])
        const_coverage = covered_constants.get(const_name, {})
        for role in roles:
            role_count = const_coverage.get(role, 0) if isinstance(const_coverage, dict) else 0
            if role_count == 0:
                report.tier2_gaps.append(f"{const_name} as {role}: 0 seeds")

    # Tier 3: missing GLSL builtins
    covered_glsl = coverage.get('glsl_builtins', {})
    all_glsl = surface.get('glsl_builtins', {})

    # Flatten all GLSL builtin names from the surface
    all_builtin_names = set()
    for category, builtins in all_glsl.items():
        for name in builtins:
            all_builtin_names.add(name)

    # Flatten covered GLSL builtin names
    covered_builtin_names = set()
    if isinstance(covered_glsl, dict):
        for key, value in covered_glsl.items():
            if isinstance(value, (list, set)):
                for name in value:
                    covered_builtin_names.add(name)
            else:
                # Key itself might be a builtin name
                covered_builtin_names.add(key)

    for builtin_name in sorted(all_builtin_names):
        if builtin_name not in covered_builtin_names:
            report.tier3_ambiguous.append(f"GLSL builtin missing: {builtin_name}")

    return report


def generate_delta_report(new_seed_calls: dict, existing_coverage: dict | None,
                          surface: dict) -> DeltaReport:
    """Compare new seed's calls against existing coverage.

    Args:
        new_seed_calls: Call data from a single new seed, with keys 'methods',
                        'constants', 'glsl_builtins', 'extension_methods',
                        'return_constants'.
        existing_coverage: Aggregated coverage from prior seeds, or None if
                          no prior cache exists.
        surface: API surface dict (test_surface.json structure).

    Returns:
        DeltaReport indicating new coverage, redundant calls, and any warnings.
    """
    delta = DeltaReport()

    if existing_coverage is None:
        delta.fallback_warning = (
            "No prior coverage cache found; treating all coverage as new."
        )
        # Treat everything in new_seed_calls as new coverage
        for method_name in new_seed_calls.get('methods', {}):
            delta.new_method_coverage.append(method_name)
        for const_name in new_seed_calls.get('constants', {}):
            delta.new_constant_coverage.append(const_name)
        return delta

    existing_methods = existing_coverage.get('methods', {})
    new_methods = new_seed_calls.get('methods', {})

    for method_name in new_methods:
        existing_count = existing_methods.get(method_name, 0)
        if existing_count == 0:
            # This method was previously uncovered -> new coverage
            delta.new_method_coverage.append(method_name)
        elif existing_count > 3:
            # Already well-covered -> redundant
            delta.redundant.append(method_name)

    existing_constants = existing_coverage.get('constants', {})
    new_constants = new_seed_calls.get('constants', {})

    for const_name in new_constants:
        existing_const = existing_constants.get(const_name, {})
        if not existing_const or (isinstance(existing_const, dict)
                                  and all(v == 0 for v in existing_const.values())):
            delta.new_constant_coverage.append(const_name)

    return delta
