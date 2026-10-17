"""Availability-aware gap ranking.

Joins the API surface/feature categories against live browser capability
probes (docs/browser_webgl_info.txt written by check_gl.py) so that gap
recipes are prioritized by what is actually testable in this environment.
"""
import re

AVAILABILITY_RANK = {"available": 0, "partial": 1, "unavailable": 2}


def parse_browser_info_text(text):
    """Parse check_gl.py output text into {browser_name: {...}}.

    Recognized format:
        === <Browser> ===
        EXTENSIONS: EXT_a EXT_b ...
    """
    browsers = {}
    current = None
    for line in text.splitlines():
        header = re.match(r"^===\s*(.+?)\s*===\s*$", line)
        if header:
            current = header.group(1)
            browsers[current] = {"extensions": set()}
            continue
        if current is None:
            continue
        m = re.match(r"^EXTENSIONS:\s*(.*)$", line)
        if m:
            exts = m.group(1).split()
            browsers[current]["extensions"] = set(exts)
    return browsers


def parse_browser_info(path):
    """Parse a check_gl.py output file into {browser_name: {"extensions": set}}."""
    return parse_browser_info_text(open(path).read())


def extension_availability(surface_extension_names, browsers):
    """Map each surface extension to per-browser availability.

    Returns {ext_name: {"firefox": bool, "chromium": bool, "union": bool,
                        "browsers": [names...]}}.
    Browser keys are normalized case-insensitively ("Firefox"/"Chromium").
    """
    norm = {}
    for name, info in browsers.items():
        key = name.lower().split()[0]
        norm[key] = set(info.get("extensions", set()))

    firefox = norm.get("firefox", set())
    chromium = norm.get("chromium", set())

    result = {}
    for ext in surface_extension_names:
        in_ff = ext in firefox
        in_cr = ext in chromium
        browsers_with = []
        if in_ff:
            browsers_with.append("firefox")
        if in_cr:
            browsers_with.append("chromium")
        result[ext] = {
            "firefox": in_ff,
            "chromium": in_cr,
            "union": in_ff or in_cr,
            "browsers": browsers_with,
        }
    return result


def category_requirements(category_def):
    """Return (required_extensions, requires_any) for a category definition."""
    return (list(category_def.get("extensions", [])),
            bool(category_def.get("requires_any_extension", False)))


def classify_gap(combo, categories_config, avail_map):
    """Classify one gap combo by environment testability.

    Returns dict {availability, browsers, blocked_by}.
      - available: every extension-dependent feature is exposed somewhere
      - partial: testable in at least one browser but not all required
        extensions are universal
      - unavailable: at least one required extension exists in no probed
        browser (or its category is unknown — treated as available since
        core categories need no extensions)
    """
    cats = categories_config.get("categories", categories_config)
    browsers_per_feature = []
    blocked_by = []

    for feat in combo:
        cat_def = cats.get(feat)
        if not cat_def:
            continue
        required, _requires_any = category_requirements(cat_def)
        if not required:
            continue
        per_ext_browsers = [set(avail_map.get(e, {}).get("browsers", []))
                            for e in required]
        feature_browsers = set.intersection(*per_ext_browsers)
        if not feature_browsers:
            blocked_by.extend(required)
        browsers_per_feature.append(feature_browsers)

    if not browsers_per_feature:
        return {"availability": "available", "browsers":
                sorted({"firefox", "chromium"}), "blocked_by": []}

    feasible = set.intersection(*browsers_per_feature)
    universe = set()
    for info in avail_map.values():
        universe.update(info.get("browsers", []))
    universe = universe or {"firefox", "chromium"}

    if feasible == universe:
        return {"availability": "available",
                "browsers": sorted(feasible),
                "blocked_by": []}
    if feasible:
        return {"availability": "partial",
                "browsers": sorted(feasible),
                "blocked_by": []}
    return {"availability": "unavailable", "browsers": [],
            "blocked_by": sorted(set(blocked_by))}


def annotate_and_sort_gaps(gaps, categories_config, avail_map):
    """Annotate each gap with availability info and sort testable-first."""
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    annotated = []
    for gap in gaps:
        info = classify_gap(gap["combo"], categories_config, avail_map)
        g = dict(gap)
        g["availability"] = info["availability"]
        g["available_browsers"] = info["browsers"]
        g["blocked_by_extensions"] = info["blocked_by"]
        annotated.append(g)
    annotated.sort(key=lambda g: (AVAILABILITY_RANK.get(g["availability"], 3),
                                  priority_rank.get(g.get("priority"), 3)))
    return annotated


def summarize_extension_coverage(categories_config, avail_map):
    """Per-extension-category seed-relevant availability summary."""
    cats = categories_config.get("categories", categories_config)
    rows = []
    for name, cat_def in sorted(cats.items()):
        required, _ = category_requirements(cat_def)
        if not required:
            continue
        union = any(avail_map.get(e, {}).get("union") for e in required)
        rows.append({
            "category": name,
            "extensions": required,
            "testable_in_env": union,
            "browsers": sorted({b for e in required
                                for b in avail_map.get(e, {}).get("browsers", [])}),
        })
    return rows
