"""Feature detection: map WebGL API usage to feature categories.

Consumes call analysis results and a feature category configuration to
determine which WebGL feature categories are present in a test file,
along with depth metrics for each matched category.
"""

from __future__ import annotations

import json
from pathlib import Path


def _load_categories(categories_config):
    """Load categories from a config dict or file path.

    Args:
        categories_config: Either a dict (already loaded JSON), a Path to
            a JSON file, or a string path to a JSON file.

    Returns:
        dict of category definitions keyed by category name.
    """
    if isinstance(categories_config, dict):
        if "categories" in categories_config:
            return categories_config["categories"]
        return categories_config
    path = Path(categories_config)
    data = json.loads(path.read_text())
    return data.get("categories", data)


def _strip_gl_prefix(name):
    """Strip 'gl.' prefix from a constant name if present."""
    if name.startswith("gl."):
        return name[3:]
    return name


def _extract_from_call_analysis(call_analysis_result):
    """Extract methods, constants, and extension methods from a CallAnalysisResult object.

    Returns:
        (methods_found: set, constants_found: set, extension_methods_found: set)
    """
    methods_found = set(call_analysis_result.methods.keys())
    constants_found = set()
    for call_records in call_analysis_result.methods.values():
        for record in call_records:
            for c in record.constants:
                constants_found.add(_strip_gl_prefix(c))
    extension_methods_found = set()
    for ext_name, ext_methods in call_analysis_result.extension_methods.items():
        for method_name in ext_methods:
            extension_methods_found.add(method_name)
    return methods_found, constants_found, extension_methods_found


def _extract_from_dict(result_dict):
    """Extract methods, constants, and extension methods from an analyze_file() result dict.

    The dict has:
      - "methods": {name: count}
      - "constants": {name: {role: count}}
      - "extension_methods": {ext_name: {method_name: count}}

    Returns:
        (methods_found: set, constants_found: set, extension_methods_found: set)
    """
    methods_found = set(result_dict.get("methods", {}).keys())
    constants_found = set()
    for const_name in result_dict.get("constants", {}):
        constants_found.add(_strip_gl_prefix(const_name))
    extension_methods_found = set()
    for ext_name, ext_methods in result_dict.get("extension_methods", {}).items():
        for method_name in ext_methods:
            extension_methods_found.add(method_name)
    return methods_found, constants_found, extension_methods_found


def is_category_match(category_def, methods_found, constants_found,
                      extensions_loaded, glsl_found, extension_methods_found):
    """Determine if a category definition matches the observed API usage.

    Uses AND-composed gates: all applicable gates must pass for a match.

    Args:
        category_def: Dict from feature_categories.json for one category.
        methods_found: Set of WebGL method names found in the file.
        constants_found: Set of constant names found (without gl. prefix).
        extensions_loaded: Set of extension names loaded by the file.
        glsl_found: Set of GLSL builtin names found in shaders.
        extension_methods_found: Set of extension method names found.

    Returns:
        Tuple of (matched: bool, matched_methods: set, method_count: int).
    """
    cat_methods = set(category_def.get("methods", []))
    cat_constants = set(category_def.get("constants", []))
    cat_extensions = set(category_def.get("extensions", []))
    cat_glsl = set(category_def.get("glsl_functions", []))
    cat_ext_methods = set(category_def.get("extension_methods", []))

    min_methods = category_def.get("min_methods_for_match", 0)
    requires_any_constant = category_def.get("requires_any_constant", False)
    min_constants = category_def.get("min_constants_for_match", 0)
    requires_any_extension = category_def.get("requires_any_extension", False)
    min_glsl = category_def.get("min_glsl_for_match", 0)

    matched_methods = methods_found & cat_methods
    matched_ext_methods = extension_methods_found & cat_ext_methods
    method_count = len(matched_methods) + len(matched_ext_methods)

    if min_methods > 0 and method_count < min_methods:
        return (False, set(), 0)

    matched_constants = constants_found & cat_constants
    if requires_any_constant and not matched_constants:
        return (False, set(), 0)

    if min_constants > 0 and len(matched_constants) < min_constants:
        return (False, set(), 0)

    if requires_any_extension:
        matched_extensions = extensions_loaded & cat_extensions
        if not matched_extensions:
            return (False, set(), 0)

    matched_glsl = glsl_found & cat_glsl
    if min_glsl > 0 and len(matched_glsl) < min_glsl:
        return (False, set(), 0)

    all_matched = matched_methods | matched_ext_methods
    return (True, all_matched, method_count)


def detect_features(call_analysis_result, glsl_builtins, categories_config,
                    extensions=None, extension_methods=None):
    """Detect which feature categories are present in a file's API usage.

    Args:
        call_analysis_result: Either a CallAnalysisResult object (with .methods
            dict attribute) or a dict from analyze_file() (with "methods" key).
        glsl_builtins: Set of GLSL builtin names found in shaders.
        categories_config: Feature categories config (dict or path).
        extensions: Optional set of extension names loaded. If None, extracted
            from call_analysis_result if available.
        extension_methods: Optional set of extension method names. If None,
            extracted from call_analysis_result.

    Returns:
        Dict with keys:
            "features": sorted list of matched category names
            "feature_depth": {cat: "present"|"meaningful"|"deep"}
            "depth_ratios": {cat: float}
            "method_counts": {cat: int}
            "methods_per_feature": {cat: sorted list of method names}
    """
    categories = _load_categories(categories_config)

    if isinstance(call_analysis_result, dict):
        methods_found, constants_found, ext_methods_extracted = _extract_from_dict(
            call_analysis_result
        )
    else:
        methods_found, constants_found, ext_methods_extracted = _extract_from_call_analysis(
            call_analysis_result
        )

    if extensions is None:
        extensions = set()
    if extension_methods is None:
        extension_methods = ext_methods_extracted

    if glsl_builtins is None:
        glsl_builtins = set()

    features = []
    feature_depth = {}
    depth_ratios = {}
    method_counts = {}
    methods_per_feature = {}

    for cat_name, cat_def in categories.items():
        matched, matched_methods, method_count = is_category_match(
            cat_def, methods_found, constants_found,
            extensions, glsl_builtins, extension_methods
        )
        if not matched:
            continue

        features.append(cat_name)
        method_counts[cat_name] = method_count
        methods_per_feature[cat_name] = sorted(matched_methods)

        cat_method_list = cat_def.get("methods", [])
        cat_ext_method_list = cat_def.get("extension_methods", [])
        total_available = len(cat_method_list) + len(cat_ext_method_list)

        if total_available == 0:
            depth_ratios[cat_name] = 1.0
            feature_depth[cat_name] = "deep"
        else:
            ratio = method_count / total_available
            depth_ratios[cat_name] = ratio
            if ratio >= 0.66:
                feature_depth[cat_name] = "deep"
            elif ratio >= 0.33:
                feature_depth[cat_name] = "meaningful"
            else:
                feature_depth[cat_name] = "present"

    features.sort()

    return {
        "features": features,
        "feature_depth": feature_depth,
        "depth_ratios": depth_ratios,
        "method_counts": method_counts,
        "methods_per_feature": methods_per_feature,
    }
