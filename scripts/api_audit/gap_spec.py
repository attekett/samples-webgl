"""Gap-driven seed recipe generation.

Consumes combination matrix gap output and produces structured recipe JSON
that an LLM (or seed author) can use to write seeds covering specific
3-way feature combinations.
"""
from __future__ import annotations

from api_audit.combination_matrix import UBIQUITOUS, SECURITY_RELEVANT


def _load_categories(categories_config):
    """Accept dict with or without outer 'categories' wrapping; return inner."""
    if isinstance(categories_config, dict) and "categories" in categories_config:
        return categories_config["categories"]
    return categories_config


def derive_extension_categories(categories_config):
    """Return the set of category names that have a non-empty `extensions` list.

    Reading this from feature_categories.json (instead of a hardcoded set)
    means adding a new ext_* category to the JSON automatically participates
    in the relevance filter without code changes.
    """
    cats = _load_categories(categories_config)
    return {name for name, defn in cats.items()
            if defn.get("extensions")}


def is_relevant(combo, extension_categories):
    """Filter out low-value gaps before recipe generation.

    Skip if:
      - every feature is in UBIQUITOUS (combo carries no signal)
      - combo is extension-only AND contains nothing from SECURITY_RELEVANT

    Args:
        combo: iterable of feature names.
        extension_categories: set of category names flagged as extensions
            (derive from categories_config via derive_extension_categories).
    """
    combo_set = set(combo)
    if all(f in UBIQUITOUS for f in combo_set):
        return False
    non_ext = [f for f in combo_set if f not in extension_categories]
    if not non_ext and not (combo_set & SECURITY_RELEVANT):
        return False
    return True
