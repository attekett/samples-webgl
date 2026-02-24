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
    """Run full analysis pipeline on a single HTML file."""
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
        'constants': {},
        'glsl_builtins': {name: 1 for name in glsl},
        'extension_methods': {},
        'return_constants': list(calls.return_constants),
        'lint_warnings': warnings,
    }

    # Aggregate constant roles from call records
    for method_name, call_records in calls.methods.items():
        for call in call_records:
            for const_name, role in call.constant_roles.items():
                if const_name not in result['constants']:
                    result['constants'][const_name] = {}
                result['constants'][const_name][role] = result['constants'][const_name].get(role, 0) + 1

    # Aggregate extension methods
    for ext_name, methods in calls.extension_methods.items():
        if ext_name not in result['extension_methods']:
            result['extension_methods'][ext_name] = {}
        for method_name, records in methods.items():
            result['extension_methods'][ext_name][method_name] = len(records) if isinstance(records, list) else records

    if cache:
        cache.store(filepath.name, content, result)

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
    args = parser.parse_args()

    surface = json.loads(args.surface.read_text())
    cache = FileCache(args.cache_dir)

    if args.file:
        # Delta mode: analyze single file against existing coverage
        result = analyze_file(args.file, surface)
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


if __name__ == '__main__':
    main()
