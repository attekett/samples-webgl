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
from api_audit.glsl import extract_glsl_builtins
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


def analyze_file(filepath, surface, cats_config, cache=None, config_hash=""):
    content = filepath.read_text()
    if cache:
        cached = cache.lookup(filepath.name, content, config_hash=config_hash)
        if cached and "features" in cached:
            return cached

    script = extract_script(content)
    if not script.strip():
        return None

    root = parse_js(script)
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    calls = analyze_calls(root, ctx, consts, surface)
    glsl = extract_glsl_builtins(root, ctx, consts, surface)

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

    if cache:
        cache.store(filepath.name, content, {"features": fp["features"],
                                              "feature_depth": fp["feature_depth"]},
                    config_hash=config_hash)

    return fp


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
    total = 0

    for f in html_files:
        fp = analyze_file(f, surface, cats_config, cache, config_hash=cats_config_hash)
        if fp is None:
            continue
        total += 1
        for feat in fp["features"]:
            if feat == "glsl_builtins":
                continue
            feature_counts[feat] = feature_counts.get(feat, 0) + 1

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
    print(f"| {'Feature Category':<40} | {'Seeds':>7} | {'Coverage':>9} |")
    print(f"|{'-'*42}|{'-'*9}|{'-'*11}|")

    for feat, count in sorted(feature_counts.items(), key=lambda x: x[1]):
        if feat in skip:
            continue
        display = DISPLAY_NAMES.get(feat, feat)
        if display is None:
            continue
        pct = count * 100 // total if total else 0
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        print(f"| {display:<40} | {count:>4}/{total:<3} | {pct:>4}% {bar} |")

    print()
    if not args.all:
        ubiq = {f: c for f, c in feature_counts.items() if f in SKIP_UBIQUITOUS}
        if ubiq:
            ubiq_line = "  ".join(
                f"{DISPLAY_NAMES.get(f, f)}: {c}/{total}"
                for f, c in sorted(ubiq.items(), key=lambda x: x[1]))
            print(f"Ubiquitous (excluded from matrix): {ubiq_line}")
            print()


if __name__ == "__main__":
    main()
