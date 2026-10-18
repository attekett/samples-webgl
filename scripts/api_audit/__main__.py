"""CLI entry point for the WebGL API surface auditor."""
import argparse
import json
import sys
import hashlib
from pathlib import Path

from api_audit.html_extract import extract_script
from api_audit.parse import parse_js
from api_audit.usage_summary import summarize_usage
from api_audit.lint import check_conventions
from api_audit.cache import FileCache
from api_audit.report import generate_report, generate_delta_report


# Bump when analysis output changes; the per-file cache is keyed on content plus this.
ANALYZER_VERSION = "11"


def analyze_file(filepath: Path, surface: dict, cache: FileCache | None = None,
                 extra_glsl_builtins: list[str] | None = None):
    """Run full analysis pipeline on a single HTML file."""
    content = filepath.read_text()

    if cache:
        cached = cache.lookup(filepath.name, content, config_hash=ANALYZER_VERSION)
        if cached:
            return cached

    script = extract_script(content)
    if not script.strip():
        return None

    root = parse_js(script)
    summary, ctx = summarize_usage(root, surface, extra_glsl_builtins)
    result = {
        'file': str(filepath),
        **summary,
        'glsl_builtins': {name: 1 for name in summary['glsl_builtins']},
        'lint_warnings': check_conventions(root, context_vars=ctx.context_vars),
    }

    if cache:
        cache.store(filepath.name, content, result, config_hash=ANALYZER_VERSION)

    return result


def aggregate_results(results: list[dict]) -> dict:
    """Merge per-file results into corpus-wide coverage."""
    coverage = {
        'methods': {},
        'constants': {},
        'glsl_builtins': {},
        'extension_methods': {},
        'return_constants': set(),
    }
    for r in results:
        for method, count in r.get('methods', {}).items():
            coverage['methods'][method] = coverage['methods'].get(method, 0) + count
        for const, roles in r.get('constants', {}).items():
            if const not in coverage['constants']:
                coverage['constants'][const] = {}
            for role, cnt in roles.items():
                coverage['constants'][const][role] = coverage['constants'][const].get(role, 0) + cnt
        for name, count in r.get('glsl_builtins', {}).items():
            coverage['glsl_builtins'][name] = coverage['glsl_builtins'].get(name, 0) + count
        for ext, methods in r.get('extension_methods', {}).items():
            if ext not in coverage['extension_methods']:
                coverage['extension_methods'][ext] = {}
            for m, c in methods.items():
                coverage['extension_methods'][ext][m] = coverage['extension_methods'][ext].get(m, 0) + c
        for rc in r.get('return_constants', []):
            coverage['return_constants'].add(rc)
    return coverage


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
    parser.add_argument('--output', type=Path, default=None,
                        help='Output report path (JSON)')
    parser.add_argument('--feature-categories', type=Path, default=None,
                        help='Path to feature_categories.json config')
    parser.add_argument('--interaction-topology', type=Path, default=None,
                        help='Path to interaction_topology.json config')
    parser.add_argument('--availability', type=Path, default=None,
                        help='Path to browser_webgl_info.txt (check_gl.py '
                             'output) for availability-aware gap ranking')
    parser.add_argument('--combination-matrix', type=Path, default=None,
                        help='Output combination matrix report (JSON)')
    parser.add_argument('--n-way', type=int, default=2,
                        help='Compute N-way combinations (default: 2, max: 4)')
    parser.add_argument('--min-seeds', type=int, default=1,
                        help='Minimum seeds per combination (default: 1)')
    parser.add_argument('--baseline', type=Path, default=None,
                        help='Baseline matrix for incremental merge')
    parser.add_argument('--gap-recipes', type=Path, default=None,
                        help='Output gap recipes JSON path')
    parser.add_argument('--max-recipes', type=int, default=20,
                        help='Maximum recipes to emit (default: 20)')
    parser.add_argument('--max-batches', type=int, default=4,
                        help='Maximum batches to plan (default: 4)')
    parser.add_argument('--max-per-batch', type=int, default=5,
                        help='Maximum recipes per batch (default: 5)')
    args = parser.parse_args()

    surface = json.loads(args.surface.read_text())
    cache = FileCache(args.cache_dir)

    if args.file:
        # Delta mode: analyze single file against existing coverage
        extra_glsl = None
        if args.feature_categories:
            categories_config_delta = json.loads(args.feature_categories.read_text())
            cats_delta = categories_config_delta.get("categories", categories_config_delta)
            extra_glsl = list(set(
                fn for cat_def in cats_delta.values()
                for fn in cat_def.get("glsl_functions", [])))

        result = analyze_file(args.file, surface, extra_glsl_builtins=extra_glsl)
        if result is None:
            print(f"No script content found in {args.file}")
            sys.exit(1)

        # Try to load existing aggregated coverage from cache
        surface_hash = hashlib.sha256(args.surface.read_bytes()).hexdigest()[:16]
        existing = cache.lookup_evaluation(surface_hash, 'corpus_aggregate')
        delta = generate_delta_report(result, existing, surface)

        print(f"Delta report for {args.file}:")
        if delta.fallback_warning:
            print(f"  Warning: {delta.fallback_warning}")
        if delta.new_method_coverage:
            print(f"  New method coverage: {', '.join(delta.new_method_coverage)}")
        if delta.new_constant_coverage:
            print(f"  New constant coverage: {', '.join(delta.new_constant_coverage)}")
        if delta.redundant:
            print(f"  Redundant: {', '.join(delta.redundant)}")
        if result.get('lint_warnings'):
            print(f"  Lint warnings: {len(result['lint_warnings'])}")
            for w in result['lint_warnings']:
                print(f"    - {w}")
        print("Analyzed 1 file")

        # Phase 1: Incremental merge into baseline matrix
        if args.feature_categories and args.baseline and args.baseline.exists():
            from api_audit.feature_detection import detect_features
            from api_audit.combination_matrix import merge_seed_into_matrix

            categories_config = json.loads(args.feature_categories.read_text())
            fp = detect_features(
                result,
                set(result.get('glsl_builtins', {}).keys()),
                categories_config,
                extensions=set(result.get('extensions', [])))
            fp['file'] = str(args.file)

            baseline = json.loads(args.baseline.read_text())
            merge_seed_into_matrix(baseline, fp,
                                   n_way=baseline.get('n_way', 2))

            if args.combination_matrix:
                args.combination_matrix.parent.mkdir(parents=True, exist_ok=True)
                args.combination_matrix.write_text(
                    json.dumps(baseline, indent=2, default=str))
                print(f"Updated matrix written to {args.combination_matrix}")
    else:
        # Full corpus mode
        # Parse categories config once (used for report, matrix, and per-file analysis)
        categories_config = None
        extra_glsl = None
        if args.feature_categories:
            categories_config = json.loads(args.feature_categories.read_text())
            cats = categories_config.get("categories", categories_config)
            extra_glsl = list(set(
                fn for cat_def in cats.values()
                for fn in cat_def.get("glsl_functions", [])))

        html_files = []
        for d in args.corpus_dirs:
            if d.exists():
                html_files.extend(d.rglob('*.html'))

        results = []
        for f in sorted(html_files):
            result = analyze_file(f, surface, cache,
                                  extra_glsl_builtins=extra_glsl)
            if result:
                results.append(result)

        coverage = aggregate_results(results)
        report = generate_report(coverage, surface,
                                 extra_glsl_builtins=extra_glsl)

        print(f"Analyzed {len(results)} files")
        print(f"Methods: {report.covered_methods}/{report.total_methods} covered")
        if report.tier1_methods:
            print(f"Tier 1 gaps (missing methods): {len(report.tier1_methods)}")
            for m in report.tier1_methods[:10]:
                print(f"  - {m}")
        if report.tier2_gaps:
            print(f"Tier 2 gaps (missing constant roles): {len(report.tier2_gaps)}")
        if report.tier3_ambiguous:
            print(f"Tier 3 (ambiguous/GLSL): {len(report.tier3_ambiguous)}")

        if args.output:
            output_data = {
                'total_files': len(results),
                'methods_covered': report.covered_methods,
                'methods_total': report.total_methods,
                'tier1_methods': report.tier1_methods,
                'tier2_gaps': report.tier2_gaps,
                'tier3_ambiguous': report.tier3_ambiguous,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(output_data, indent=2))
            print(f"Report written to {args.output}")

        # Cache aggregated coverage for delta mode
        # Convert set to list for JSON serialization
        serializable_coverage = dict(coverage)
        serializable_coverage['return_constants'] = list(coverage['return_constants'])
        surface_hash = hashlib.sha256(json.dumps(surface, sort_keys=True).encode()).hexdigest()[:16]
        cache.store_evaluation(surface_hash, 'corpus_aggregate', serializable_coverage)

        # Phase 1: Feature detection + combination matrix pipeline
        if args.feature_categories:
            from api_audit.feature_detection import detect_features
            from api_audit.combination_matrix import (
                compute_matrix, generate_matrix_report)

            topology = None
            if args.interaction_topology:
                topology = json.loads(args.interaction_topology.read_text())

            # Run feature detection on each per-file result
            corpus_features = {}
            for r in results:
                filepath = r['file']
                fp = detect_features(
                    r,
                    set(r.get('glsl_builtins', {}).keys()),
                    categories_config,
                    extensions=set(r.get('extensions', [])))
                fp['file'] = filepath
                corpus_features[filepath] = fp

            if args.combination_matrix:
                n = min(args.n_way, 4)
                matrix = compute_matrix(corpus_features, n=n,
                                        interaction_topology=topology,
                                        categories_config=categories_config)
                report_matrix = generate_matrix_report(
                    matrix, corpus_features, topology)

                all_feature_names = set(
                    f for fp in corpus_features.values()
                    for f in fp["features"])
                if categories_config:
                    all_feature_names |= set(cats.keys())

                avail_summary = None
                if args.availability:
                    from api_audit.availability import (
                        parse_browser_info, extension_availability,
                        annotate_and_sort_gaps, summarize_extension_coverage)

                    browsers = parse_browser_info(args.availability)
                    surface_exts = list(surface.get('extensions', {}).keys())
                    avail_map = extension_availability(surface_exts, browsers)
                    testable = [e for e, v in avail_map.items() if v['union']]
                    print(f"Availability: {len(browsers)} browsers probed, "
                          f"{len(testable)}/{len(surface_exts)} extensions "
                          f"testable in env")

                    report_matrix['gaps'] = annotate_and_sort_gaps(
                        report_matrix['gaps'], categories_config, avail_map)
                    avail_summary = summarize_extension_coverage(
                        categories_config, avail_map)
                    not_testable = [r['category'] for r in avail_summary
                                    if not r['testable_in_env']]
                    print(f"  Extension categories testable now: "
                          f"{len(avail_summary) - len(not_testable)}"
                          f"/{len(avail_summary)}")
                    if not_testable:
                        print(f"  Not testable in env: "
                              f"{', '.join(not_testable)}")

                output_data = {
                    "corpus_size": len(results),
                    "feature_count": len(all_feature_names),
                    "phase2_enriched": False,
                    "availability": {
                        "source": str(args.availability),
                        "extensions": avail_map,
                    } if args.availability else None,
                    "extension_categories": avail_summary,
                    f"{n}way_combinations": report_matrix,
                }

                args.combination_matrix.parent.mkdir(parents=True, exist_ok=True)
                args.combination_matrix.write_text(
                    json.dumps(output_data, indent=2, default=str))
                print(f"Combination matrix written to {args.combination_matrix}")
                print(f"  {n}-way: {report_matrix['total']} combos, "
                      f"{report_matrix['covered']} covered, "
                      f"{report_matrix['uncovered']} uncovered")
                if report_matrix['gaps']:
                    print(f"  Top gaps ({len(report_matrix['gaps'])} total):")
                    for g in report_matrix['gaps'][:5]:
                        avail = g.get('availability', 'available')
                        browsers = ','.join(g.get('available_browsers', []))
                        print(f"    {g['priority']} [{avail}:{browsers}]: "
                              f"{g['combo']}")

                if args.gap_recipes:
                    from api_audit.gap_spec import generate_recipes

                    recipes_data = generate_recipes(
                        report_matrix,
                        corpus_features,
                        categories_config,
                        topology if topology is not None else {"edges": []},
                        n_way=n,
                        max_recipes=args.max_recipes,
                        max_batches=args.max_batches,
                        max_per_batch=args.max_per_batch,
                    )
                    recipes_data["generated_from_matrix"] = str(args.combination_matrix)

                    args.gap_recipes.parent.mkdir(parents=True, exist_ok=True)
                    args.gap_recipes.write_text(
                        json.dumps(recipes_data, indent=2, default=str))
                    print(f"Gap recipes written to {args.gap_recipes}")
                    print(f"  {len(recipes_data['recipes'])} recipes "
                          f"in {len(recipes_data['batches'])} batches")
                    if recipes_data.get("missing_categories"):
                        print(f"  Warning: {len(recipes_data['missing_categories'])} "
                              f"target features lack category definitions: "
                              f"{', '.join(recipes_data['missing_categories'])}")


if __name__ == '__main__':
    main()
