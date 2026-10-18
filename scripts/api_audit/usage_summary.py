"""Per-file usage summary shared by api_audit and feature_coverage."""
from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants
from api_audit.call_analysis import analyze_calls
from api_audit.glsl import (
    collect_shader_sources, extract_glsl_builtins, extract_glsl_variables)


def summarize_usage(root, surface: dict, extra_glsl_builtins: list[str] | None = None):
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    calls = analyze_calls(root, ctx, consts, surface)
    glsl = extract_glsl_builtins(root, ctx, consts, surface,
                                 extra_builtins=extra_glsl_builtins)
    glsl_vars = extract_glsl_variables(root, ctx, consts, surface)

    constants: dict = {}
    method_constants: dict = {}
    surface_constants = surface.get("constants", {})
    for method_name, call_records in calls.methods.items():
        used = set()
        for call in call_records:
            used.update(call.constants)
            for const_name, param_name in call.constant_roles.items():
                roles = surface_constants.get(const_name, {}).get("roles", [param_name])
                for role in roles:
                    per_role = constants.setdefault(const_name, {})
                    per_role[role] = per_role.get(role, 0) + 1
        if used:
            method_constants[method_name] = sorted(used)

    summary = {
        "methods": {k: len(v) for k, v in calls.methods.items()},
        "constants": constants,
        "extension_methods": {
            ext: {m: len(r) if isinstance(r, list) else r for m, r in methods.items()}
            for ext, methods in calls.extension_methods.items()},
        "method_constants": method_constants,
        "return_constants": sorted(calls.return_constants),
        "extensions": sorted(ctx.extensions),
        "api_version": ctx.api_version,
        "glsl_builtins": sorted(glsl),
        "glsl_variables": sorted(glsl_vars),
        "glsl_sources": collect_shader_sources(root, ctx, consts),
    }
    return summary, ctx
