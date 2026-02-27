"""Validation tests for feature_categories.json, interaction_topology.json,
and their consistency with webgl_api_surface.json."""

import warnings


def test_categories_schema(feature_categories):
    """Every category has methods (list), constants (list), min_methods_for_match (int >= 0).
    Assert at least 25 categories."""
    cats = feature_categories["categories"]
    assert len(cats) >= 25, f"Expected >= 25 categories, got {len(cats)}"

    for name, cat in cats.items():
        assert "methods" in cat, f"{name} missing 'methods'"
        assert isinstance(cat["methods"], list), f"{name}.methods is not a list"

        assert "constants" in cat, f"{name} missing 'constants'"
        assert isinstance(cat["constants"], list), f"{name}.constants is not a list"

        assert "min_methods_for_match" in cat, f"{name} missing 'min_methods_for_match'"
        assert isinstance(cat["min_methods_for_match"], int), (
            f"{name}.min_methods_for_match is not int"
        )
        assert cat["min_methods_for_match"] >= 0, (
            f"{name}.min_methods_for_match is negative"
        )


def test_category_methods_exist_in_surface(feature_categories, api_surface):
    """All method names in categories exist in webgl_api_surface.json methods
    section. Extension_methods entries must exist in their respective
    extension method lists."""
    surface_methods = set(api_surface["methods"].keys())

    # Collect all extension methods across all extensions
    all_ext_methods = {}
    for ext_name, ext_data in api_surface["extensions"].items():
        for method_name in ext_data.get("methods", {}):
            all_ext_methods.setdefault(method_name, set()).add(ext_name)

    missing = []
    for cat_name, cat in feature_categories["categories"].items():
        for method in cat.get("methods", []):
            if method not in surface_methods:
                missing.append(f"{cat_name}.methods: {method}")

        for ext_method in cat.get("extension_methods", []):
            cat_extensions = set(cat.get("extensions", []))
            surface_extensions = api_surface["extensions"]
            found = False
            for ext_name in cat_extensions:
                if ext_name in surface_extensions:
                    if ext_method in surface_extensions[ext_name].get("methods", {}):
                        found = True
                        break
            if not found:
                # Also check if the method exists in ANY extension
                if ext_method in all_ext_methods:
                    found = True
            if not found:
                missing.append(
                    f"{cat_name}.extension_methods: {ext_method} "
                    f"(not in extensions {cat_extensions})"
                )

    assert not missing, (
        f"Methods not found in api_surface:\n" + "\n".join(missing)
    )


def test_category_constants_exist_in_surface(feature_categories, api_surface):
    """All constant names in categories exist in webgl_api_surface.json
    constants section or in an extension constants section."""
    surface_constants = set(api_surface["constants"].keys())

    # Also collect extension constants
    ext_constants = set()
    for ext_data in api_surface["extensions"].values():
        ext_constants.update(ext_data.get("constants", {}).keys())

    all_constants = surface_constants | ext_constants

    missing = []
    for cat_name, cat in feature_categories["categories"].items():
        for const in cat.get("constants", []):
            if const not in all_constants:
                missing.append(f"{cat_name}.constants: {const}")

    assert not missing, (
        f"Constants not found in api_surface:\n" + "\n".join(missing)
    )


def test_topology_references_valid_categories(
    interaction_topology, feature_categories
):
    """Every topology edge pair element references a category that exists
    in feature_categories.json."""
    valid_cats = set(feature_categories["categories"].keys())
    invalid_refs = []

    for i, edge in enumerate(interaction_topology["edges"]):
        for node in edge["pair"]:
            if node not in valid_cats:
                invalid_refs.append(
                    f"edge[{i}] pair {edge['pair']}: '{node}' not in categories"
                )

    assert not invalid_refs, (
        f"Invalid category references in topology:\n" + "\n".join(invalid_refs)
    )


def test_topology_no_duplicates(interaction_topology):
    """No duplicate edges (normalize by sorting pairs)."""
    seen = set()
    duplicates = []

    for i, edge in enumerate(interaction_topology["edges"]):
        normalized = tuple(sorted(edge["pair"]))
        if normalized in seen:
            duplicates.append(f"edge[{i}]: {edge['pair']} (duplicate)")
        seen.add(normalized)

    assert not duplicates, (
        f"Duplicate topology edges:\n" + "\n".join(duplicates)
    )


def test_categories_with_zero_topology_edges(
    feature_categories, interaction_topology
):
    """Warn about categories with zero topology edges. Informational only."""
    connected = set()
    for edge in interaction_topology["edges"]:
        connected.update(edge["pair"])

    disconnected = set(feature_categories["categories"].keys()) - connected
    if disconnected:
        warnings.warn(
            f"Categories with zero topology edges: {sorted(disconnected)}"
        )


def test_surface_method_completeness(feature_categories, api_surface):
    """Every method in webgl_api_surface.json methods section should appear
    in at least one category. Warn about uncategorized methods."""
    all_cat_methods = set()
    for cat in feature_categories["categories"].values():
        all_cat_methods.update(cat.get("methods", []))

    surface_methods = set(api_surface["methods"].keys())
    uncategorized = sorted(surface_methods - all_cat_methods)

    if uncategorized:
        warnings.warn(
            f"{len(uncategorized)} uncategorized methods in api_surface: "
            f"{uncategorized}"
        )


def test_category_glsl_functions_in_surface_or_known_extras(
    feature_categories, api_surface
):
    """All glsl_functions in categories exist in api_surface or are known GLSL3 extras."""
    surface_glsl = set()
    for category, names in api_surface.get("glsl_builtins", {}).items():
        surface_glsl.update(names)
    KNOWN_EXTRAS = {
        "smoothstep", "refract", "reflect", "faceforward",
        "matrixCompMult", "inversesqrt", "textureGather", "textureGatherOffset",
    }
    missing = []
    for cat_name, cat in feature_categories["categories"].items():
        for fn in cat.get("glsl_functions", []):
            if fn not in surface_glsl and fn not in KNOWN_EXTRAS:
                missing.append(f"{cat_name}.glsl_functions: {fn}")
    assert not missing, (
        f"GLSL functions not in surface or known extras:\n" + "\n".join(missing)
    )
