"""Feature coverage report: per-category seed counts across the full corpus.

Replaces the grep-based feature_matrix.sh with AST-based detection using
the api_audit infrastructure and feature_categories.json definitions.

Usage:
    python scripts/feature_coverage.py [--dirs DIR...] [--categories FILE]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

# Allow running from project root without installing
sys.path.insert(0, str(Path(__file__).parent))

from api_audit.html_extract import extract_script
from api_audit.parse import parse_js
from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants
from api_audit.call_analysis import analyze_calls
from api_audit.glsl import extract_glsl_builtins, extract_glsl_variables
from api_audit.feature_detection import detect_features
from api_audit.cache import FileCache


# Display names for feature categories (matches old shell script terminology)
DISPLAY_NAMES = {
    "buffer_ops":                   "Buffer Operations",
    "ubo":                          "Uniform Buffer Objects",
    "transform_feedback":           "Transform Feedback",
    "texture_ops":                  "Texture Operations",
    "texture_3d":                   "3D Textures",
    "texture_arrays":               "Texture Arrays",
    "fbo":                          "Framebuffer Objects",
    "mrt":                          "Multiple Render Targets",
    "instancing":                   "Instanced Rendering",
    "vao":                          "Vertex Array Objects",
    "sync":                         "Sync Objects",
    "query":                        "Query Objects",
    "sampler":                      "Sampler Objects",
    "integer_textures":             "Integer Textures",
    "depth_stencil":                "Depth/Stencil Ops",
    "blending":                     "Blending",
    "pixel_ops":                    "Pixel Operations",
    "renderbuffer":                 "Renderbuffers",
    "attributes":                   "Vertex Attributes",
    "uniforms":                     "Uniforms",
    "shader_pipeline":              "Shader Pipeline",
    "draw_calls":                   "Draw Calls",
    "viewport_scissor":             "Viewport/Scissor",
    "ext_color_buffer_float":       "EXT: Color Buffer Float",
    "ext_draw_buffers_indexed":     "EXT: Draw Buffers Indexed",
    "ext_float_textures":           "EXT: Float Textures",
    "ext_compressed_textures":      "EXT: Compressed Textures",
    "ext_texture_filter_anisotropic": "EXT: Anisotropic Filter",
    "ext_disjoint_timer_query":     "EXT: Disjoint Timer Query",
    "glsl_builtins":                None,  # skip — always matches every file
}

# Ordered display groups (omit ubiquitous features from the matrix by default)
SKIP_UBIQUITOUS = {"attributes", "uniforms", "shader_pipeline", "draw_calls",
                   "viewport_scissor", "buffer_ops", "glsl_builtins"}


def is_passed(filepath: Path) -> bool:
    """Return True if the seed's sibling .json result reports passed: true."""
    json_path = filepath.with_suffix('.json')
    if not json_path.exists():
        return False
    try:
        data = json.loads(json_path.read_text())
        results = data.get('results', [])
        if not results:
            return False
        return bool(results[0].get('passed', False))
    except Exception:
        return False


def format_depth_summary(depth_counts: dict) -> str:
    """Format depth count dict as 'P:N M:N D:N' for table display."""
    p = depth_counts.get("present", 0)
    m = depth_counts.get("meaningful", 0)
    d = depth_counts.get("deep", 0)
    return f"P:{p} M:{m} D:{d}"


def summarize_combinations(matrix: dict) -> dict:
    """Summarize n-way combination matrix stats for display.

    Args:
        matrix: {combo_tuple: {seed_count, topology_connected, ...}}

    Returns:
        dict with total, connected, covered, gap_count, pct keys.
    """
    total = len(matrix)
    connected = sum(1 for d in matrix.values() if d.get("topology_connected", True))
    covered = sum(
        1 for d in matrix.values()
        if d.get("topology_connected", True) and d["seed_count"] >= 1
    )
    gap_count = connected - covered
    pct = round(covered * 100 / connected, 1) if connected else 0
    return {"total": total, "connected": connected, "covered": covered,
            "gap_count": gap_count, "pct": pct}


def compute_method_coverage(surface_methods: set, seen_methods: set) -> dict:
    """Compute what fraction of API surface methods appear in the corpus.

    Args:
        surface_methods: set of method names from webgl_api_surface.json
        seen_methods: set of method names found across all corpus files

    Returns:
        dict with total, exercised, pct, never_seen (sorted list)
    """
    total = len(surface_methods)
    exercised = len(seen_methods & surface_methods)
    pct = round(exercised * 100 / total, 1) if total else 0
    never_seen = sorted(surface_methods - seen_methods)
    return {"total": total, "exercised": exercised, "pct": pct, "never_seen": never_seen}


def aggregate_glsl_builtins(fingerprints: list) -> dict:
    """Count how many seeds use each GLSL builtin.

    Args:
        fingerprints: list of analyze_file() result dicts, each may have
            a "glsl_builtins" set or list.

    Returns:
        dict {builtin_name: seed_count}
    """
    counts = {}
    for fp in fingerprints:
        if fp is None:
            continue
        for b in fp.get("glsl_builtins", []):
            counts[b] = counts.get(b, 0) + 1
    return counts


def aggregate_glsl_variables(fingerprints: list) -> dict:
    """Count how many seeds reference each GLSL built-in variable.

    Args:
        fingerprints: list of analyze_file() result dicts, each may have
            a "glsl_variables" set or list.

    Returns:
        dict {variable_name: seed_count}
    """
    counts = {}
    for fp in fingerprints:
        if fp is None:
            continue
        for v in fp.get("glsl_variables", []):
            counts[v] = counts.get(v, 0) + 1
    return counts


def diff_coverage_snapshots(prev: dict, curr: dict) -> dict:
    """Compute delta between two coverage snapshots.

    Each snapshot is {feature_name: {seeds: N, pct: float}}.

    Returns:
        dict with:
          changed: {feature: {delta_seeds, delta_pct}} — only non-zero deltas
          new_features: sorted list of features in curr but not prev
          removed_features: sorted list of features in prev but not curr
    """
    prev_keys = set(prev)
    curr_keys = set(curr)
    changed = {}
    for feat in prev_keys & curr_keys:
        ds = curr[feat]["seeds"] - prev[feat]["seeds"]
        dp = round(curr[feat]["pct"] - prev[feat]["pct"], 1)
        if ds != 0 or dp != 0.0:
            changed[feat] = {"delta_seeds": ds, "delta_pct": dp}
    return {
        "changed": changed,
        "new_features": sorted(curr_keys - prev_keys),
        "removed_features": sorted(prev_keys - curr_keys),
    }


def analyze_file(filepath, surface, cats_config, cache=None, config_hash=""):
    content = filepath.read_text()
    if cache:
        cached = cache.lookup(filepath.name, content, config_hash=config_hash)
        if (cached and "features" in cached and "all_methods" in cached
                and "glsl_variables" in cached):
            return {**cached, "all_methods": set(cached.get("all_methods", [])),
                    "glsl_builtins": set(cached.get("glsl_builtins", [])),
                    "glsl_variables": set(cached.get("glsl_variables", []))}

    script = extract_script(content)
    if not script.strip():
        return None

    root = parse_js(script)
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    calls = analyze_calls(root, ctx, consts, surface)

    category_glsl = []
    for cat in cats_config.get("categories", {}).values():
        category_glsl.extend(cat.get("glsl_functions", []))
    glsl = extract_glsl_builtins(root, ctx, consts, surface,
                                 extra_builtins=category_glsl)
    glsl_vars = extract_glsl_variables(root, ctx, consts, surface)

    result = {
        "methods": {k: len(v) for k, v in calls.methods.items()},
        "constants": {},
        "extension_methods": {},
    }

    surface_constants = surface.get("constants", {})
    for method_name, call_records in calls.methods.items():
        for call in call_records:
            for const_name, param_name in call.constant_roles.items():
                if const_name not in result["constants"]:
                    result["constants"][const_name] = {}
                roles = surface_constants.get(const_name, {}).get("roles", [param_name])
                for role in roles:
                    result["constants"][const_name][role] = (
                        result["constants"][const_name].get(role, 0) + 1)

    for ext_name, methods in calls.extension_methods.items():
        result["extension_methods"][ext_name] = {
            m: len(r) for m, r in methods.items()}

    fp = detect_features(
        result,
        set(glsl),
        cats_config,
        extensions=set(ctx.extensions))

    all_methods = set(result["methods"].keys())
    for ext_methods in result["extension_methods"].values():
        all_methods.update(ext_methods.keys())

    if cache:
        cache.store(filepath.name, content,
                    {"features": fp["features"],
                     "feature_depth": fp["feature_depth"],
                     "methods_per_feature": fp.get("methods_per_feature", {}),
                     "all_methods": sorted(all_methods),
                     "glsl_builtins": list(glsl),
                     "glsl_variables": sorted(glsl_vars)},
                    config_hash=config_hash)

    return {**fp, "glsl_builtins": set(glsl), "all_methods": all_methods,
            "glsl_variables": set(glsl_vars)}


def main():
    parser = argparse.ArgumentParser(description="WebGL feature coverage matrix")
    parser.add_argument("--dirs", nargs="+", type=Path,
                        default=[Path("samples-webgl"), Path("agent_outputs")],
                        help="Corpus directories to scan")
    parser.add_argument("--surface", type=Path,
                        default=Path("docs/webgl_api_surface.json"))
    parser.add_argument("--categories", type=Path,
                        default=Path("docs/feature_categories.json"))
    parser.add_argument("--cache-dir", type=Path,
                        default=Path(".cache/api_audit"))
    parser.add_argument("--all", action="store_true",
                        help="Include ubiquitous features (attributes, uniforms, etc.)")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of markdown table")
    parser.add_argument("--passed-only", action="store_true",
                        help="Only count seeds whose sibling .json result has passed:true")
    parser.add_argument("--combinations", type=int, default=0, metavar="N",
                        help="Also report N-way combination coverage gaps (2 or 3)")
    parser.add_argument("--api-surface-coverage", action="store_true",
                        help="Show per-method API surface coverage report")
    parser.add_argument("--glsl-detail", action="store_true",
                        help="Show per-GLSL-builtin seed counts")
    parser.add_argument("--glsl-vars-detail", action="store_true",
                        help="Show per-GLSL-built-in-variable seed counts")
    parser.add_argument("--snapshot", type=Path, metavar="FILE",
                        help="Save current coverage to FILE as JSON snapshot")
    parser.add_argument("--diff", type=Path, metavar="PREV_SNAPSHOT",
                        help="Compare current coverage against PREV_SNAPSHOT and print delta")
    args = parser.parse_args()

    surface = json.loads(args.surface.read_text())
    cats_config = json.loads(args.categories.read_text())
    cats_config_hash = hashlib.sha256(args.categories.read_bytes()).hexdigest()[:16]
    cache = FileCache(args.cache_dir)

    html_files = []
    for d in args.dirs:
        if d.exists():
            html_files.extend(sorted(d.rglob("*.html")))

    feature_counts = {}
    feature_depths = {}  # {feat: {"present": N, "meaningful": N, "deep": N}}
    corpus_fingerprints = {}  # {filename: feature_fingerprint}
    all_seen_methods = set()
    total = 0

    for f in html_files:
        if args.passed_only and not is_passed(f):
            continue
        fp = analyze_file(f, surface, cats_config, cache, config_hash=cats_config_hash)
        if fp is None:
            continue
        total += 1
        for feat in fp["features"]:
            if feat == "glsl_builtins":
                continue
            feature_counts[feat] = feature_counts.get(feat, 0) + 1
            # Accumulate depth level for this feature in this file
            fd = fp.get("feature_depth", {}).get(feat, "present")
            if feat not in feature_depths:
                feature_depths[feat] = {"present": 0, "meaningful": 0, "deep": 0}
            feature_depths[feat][fd] += 1
        all_seen_methods.update(fp.get("all_methods", set()))
        corpus_fingerprints[str(f)] = {
            "features": fp["features"],
            "methods_per_feature": fp.get("methods_per_feature", {}),
            "feature_depth": fp.get("feature_depth", {}),
            "glsl_builtins": fp.get("glsl_builtins", []),
            "glsl_variables": fp.get("glsl_variables", []),
        }

    snapshot = {feat: {"seeds": count, "total": total,
                        "pct": round(count * 100 / total, 1) if total else 0}
                for feat, count in feature_counts.items()}

    if args.snapshot:
        args.snapshot.write_text(json.dumps(snapshot, indent=2))
        print(f"Snapshot saved to {args.snapshot}")

    if args.json:
        out = {feat: {"seeds": count, "total": total,
                      "pct": round(count * 100 / total, 1) if total else 0}
               for feat, count in sorted(feature_counts.items(),
                                         key=lambda x: x[1])}
        print(json.dumps(out, indent=2))
        return

    skip = set() if args.all else SKIP_UBIQUITOUS

    print(f"## Feature Coverage Matrix ({total} files)")
    print()
    print(f"| {'Feature Category':<40} | {'Seeds':>7} | {'Coverage':>9} | {'Depth (P/M/D)':<16} |")
    print(f"|{'-'*42}|{'-'*9}|{'-'*11}|{'-'*18}|")

    for feat, count in sorted(feature_counts.items(), key=lambda x: x[1]):
        if feat in skip:
            continue
        display = DISPLAY_NAMES.get(feat, feat)
        if display is None:
            continue
        pct = count * 100 // total if total else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        depth_str = format_depth_summary(feature_depths.get(feat, {}))
        print(f"| {display:<40} | {count:>4}/{total:<3} | {pct:>4}% {bar} | {depth_str:<16} |")

    print()
    if not args.all:
        ubiq = {f: c for f, c in feature_counts.items() if f in SKIP_UBIQUITOUS}
        if ubiq:
            ubiq_line = "  ".join(
                f"{DISPLAY_NAMES.get(f, f)}: {c}/{total}"
                for f, c in sorted(ubiq.items(), key=lambda x: x[1]))
            print(f"Ubiquitous (excluded from matrix): {ubiq_line}")
            print()

    if args.combinations >= 2:
        from api_audit.combination_matrix import compute_matrix
        topology_path = Path("docs/interaction_topology.json")
        topology = json.loads(topology_path.read_text()) if topology_path.exists() else None
        matrix = compute_matrix(corpus_fingerprints, n=args.combinations,
                                interaction_topology=topology,
                                categories_config=cats_config)
        summary = summarize_combinations(matrix)
        n = args.combinations
        print(f"## {n}-Way Combination Coverage")
        print(f"Connected combos: {summary['connected']}, "
              f"covered: {summary['covered']} ({summary['pct']}%), "
              f"gaps: {summary['gap_count']}")
        gaps = sorted(
            [(c, d) for c, d in matrix.items()
             if d.get("topology_connected", True) and d["seed_count"] == 0],
            key=lambda x: x[0]
        )[:10]
        if gaps:
            print("Top uncovered combos (up to 10):")
            for combo, _ in gaps:
                print(f"  - {' + '.join(combo)}")
        print()

    if args.api_surface_coverage:
        surface_method_names = set(surface.get("methods", {}).keys())
        report = compute_method_coverage(surface_method_names, all_seen_methods)
        print(f"## API Surface Method Coverage")
        print(f"{report['exercised']}/{report['total']} methods exercised "
              f"({report['pct']}%)")
        if report["never_seen"]:
            print(f"Never-seen methods ({len(report['never_seen'])}):")
            for m in report["never_seen"]:
                print(f"  - {m}")
        print()

    if args.glsl_vars_detail:
        var_counts = aggregate_glsl_variables(list(corpus_fingerprints.values()))
        all_vars = set()
        var_categories = surface.get("glsl_builtin_variables", {})
        for category_names in var_categories.values():
            all_vars.update(category_names)
        used = sorted(var_counts.items(), key=lambda x: x[1], reverse=True)
        used_in_known = set(var_counts) & all_vars
        never = sorted(all_vars - set(var_counts))
        print("## GLSL Built-in Variable Coverage")
        print(f"Used variables ({len(used_in_known)}/{len(all_vars)}):")
        for name, count in used:
            print(f"  {name:<40} {count:>4} seeds")
        if never:
            print(f"Never used ({len(never)}): {', '.join(never)}")
        print()

    if args.glsl_detail:
        glsl_counts = aggregate_glsl_builtins(list(corpus_fingerprints.values()))
        all_builtins = set()
        for cat in cats_config.get("categories", {}).values():
            all_builtins.update(cat.get("glsl_functions", []))
        for category_names in surface.get("glsl_builtins", {}).values():
            all_builtins.update(category_names)
        print("## GLSL Builtin Coverage")
        used_in_known = set(glsl_counts) & all_builtins
        never = sorted(all_builtins - set(glsl_counts))
        used = sorted(glsl_counts.items(), key=lambda x: x[1], reverse=True)
        print(f"Used builtins ({len(used_in_known)}/{len(all_builtins)}):")
        for name, count in used:
            print(f"  {name:<30} {count:>4} seeds")
        if never:
            print(f"Never used ({len(never)}): {', '.join(never)}")
        print()

    if args.diff and args.diff.exists():
        prev_snapshot = json.loads(args.diff.read_text())
        delta = diff_coverage_snapshots(prev_snapshot, snapshot)
        print("## Coverage Delta")
        if delta["new_features"]:
            print(f"New features: {', '.join(delta['new_features'])}")
        if delta["removed_features"]:
            print(f"Removed features: {', '.join(delta['removed_features'])}")
        if delta["changed"]:
            for feat, d in sorted(delta["changed"].items()):
                sign = "+" if d["delta_seeds"] >= 0 else ""
                print(f"  {feat:<40} {sign}{d['delta_seeds']} seeds  "
                      f"({sign}{d['delta_pct']}%)")
        else:
            print("No coverage changes.")
        print()
    elif args.diff and not args.diff.exists():
        print(f"Warning: diff snapshot file not found: {args.diff}", file=sys.stderr)


if __name__ == "__main__":
    main()
