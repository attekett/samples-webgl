"""Tests for availability module — env-aware gap ranking."""
import json

from api_audit.availability import (
    parse_browser_info_text,
    parse_browser_info, extension_availability, classify_gap,
    annotate_and_sort_gaps, summarize_extension_coverage,
)

BROWSER_INFO = """=== Firefox ===
EXTENSION_COUNT: 3
EXTENSIONS: EXT_color_buffer_float EXT_depth_clamp OES_draw_buffers_indexed

=== Chromium ===
EXTENSION_COUNT: 4
EXTENSIONS: EXT_color_buffer_float WEBGL_multi_draw EXT_clip_control WEBGL_lose_context
"""

CATEGORIES = {
    "categories": {
        "fbo": {"methods": ["createFramebuffer"], "extensions": []},
        "blend": {"methods": ["blendFunc"], "extensions": []},
        "ext_color_buffer_float": {
            "extensions": ["EXT_color_buffer_float"],
            "requires_any_extension": True},
        "ext_depth_clamp": {
            "extensions": ["EXT_depth_clamp"],
            "requires_any_extension": True},
        "ext_multi_draw": {
            "extensions": ["WEBGL_multi_draw"],
            "requires_any_extension": True},
        "ext_pvrtc": {
            "extensions": ["WEBGL_compressed_texture_pvrtc"],
            "requires_any_extension": True},
        "ext_multi_and_lose": {
            "extensions": ["WEBGL_multi_draw", "WEBGL_lose_context"],
            "requires_any_extension": True},
    }
}


class TestParseBrowserInfo:
    def test_parses_sections(self):
        browsers = parse_browser_info_text(BROWSER_INFO)
        assert set(browsers.keys()) == {"Firefox", "Chromium"}
        assert "EXT_depth_clamp" in browsers["Firefox"]["extensions"]
        assert browsers["Chromium"]["extensions"] >= {"WEBGL_multi_draw"}

    def test_missing_extensions_line_yields_empty_set(self):
        browsers = parse_browser_info_text("=== Firefox ===\nnothing here\n")
        assert browsers["Firefox"]["extensions"] == set()


class TestExtensionAvailability:
    def test_union_and_per_browser_flags(self):
        avail = extension_availability(
            ["EXT_color_buffer_float", "EXT_depth_clamp",
             "WEBGL_compressed_texture_pvrtc"],
            parse_browser_info_text(BROWSER_INFO))
        assert avail["EXT_color_buffer_float"]["union"] is True
        assert avail["EXT_color_buffer_float"]["browsers"] == [
            "firefox", "chromium"]
        assert avail["EXT_depth_clamp"]["firefox"] is True
        assert avail["EXT_depth_clamp"]["chromium"] is False
        assert avail["WEBGL_compressed_texture_pvrtc"]["union"] is False


class TestClassifyGap:
    def setup_method(self):
        self.avail = extension_availability(
            ["EXT_color_buffer_float", "EXT_depth_clamp", "WEBGL_multi_draw",
             "WEBGL_lose_context", "WEBGL_compressed_texture_pvrtc"],
            parse_browser_info_text(BROWSER_INFO))

    def test_core_only_gap_is_available(self):
        info = classify_gap(["fbo"], CATEGORIES, self.avail)
        assert info["availability"] == "available"

    def test_single_ext_available_both_browsers(self):
        info = classify_gap(["ext_color_buffer_float"], CATEGORIES, self.avail)
        assert info["availability"] == "available"
        assert set(info["browsers"]) == {"firefox", "chromium"}

    def test_partial_when_one_browser_only(self):
        info = classify_gap(["ext_depth_clamp"], CATEGORIES, self.avail)
        assert info["availability"] == "partial"
        assert info["browsers"] == ["firefox"]

    def test_unavailable_when_no_browser_has_it(self):
        info = classify_gap(["ext_pvrtc"], CATEGORIES, self.avail)
        assert info["availability"] == "unavailable"
        assert info["blocked_by"] == ["WEBGL_compressed_texture_pvrtc"]

    def test_category_with_multiple_required_extensions_intersects(self):
        info = classify_gap(["ext_multi_and_lose"], CATEGORIES, self.avail)
        assert info["availability"] == "partial"
        assert info["browsers"] == ["chromium"]

    def test_combo_availability_is_intersection(self):
        info = classify_gap(
            ["fbo", "ext_color_buffer_float", "ext_depth_clamp"],
            CATEGORIES, self.avail)
        assert info["availability"] == "partial"
        assert info["browsers"] == ["firefox"]


class TestAnnotateAndSortGaps:
    def setup_method(self):
        self.avail = extension_availability(
            ["EXT_color_buffer_float", "EXT_depth_clamp",
             "WEBGL_compressed_texture_pvrtc"],
            parse_browser_info_text(BROWSER_INFO))

    def _gap(self, combo, priority="high"):
        return {"combo": combo, "seed_count": 0, "priority": priority,
                "topology_connected": True}

    def test_available_gaps_sorted_before_unavailable(self):
        gaps = [self._gap(["ext_pvrtc"]),
                self._gap(["ext_color_buffer_float"])]
        out = annotate_and_sort_gaps(gaps, CATEGORIES, self.avail)
        assert out[0]["combo"] == ["ext_color_buffer_float"]
        assert out[0]["availability"] == "available"
        assert out[1]["availability"] == "unavailable"

    def test_priority_respected_within_same_availability(self):
        gaps = [self._gap(["fbo"], priority="low"),
                self._gap(["blend", "fbo"], priority="high")]
        out = annotate_and_sort_gaps(gaps, CATEGORIES, self.avail)
        assert [g["priority"] for g in out] == ["high", "low"]


class TestSummarize:
    def test_summary_rows(self):
        avail = extension_availability(
            ["EXT_color_buffer_float", "WEBGL_compressed_texture_pvrtc"],
            parse_browser_info_text(BROWSER_INFO))
        rows = summarize_extension_coverage(CATEGORIES, avail)
        by_name = {r["category"]: r for r in rows}
        assert by_name["ext_color_buffer_float"]["testable_in_env"] is True
        assert by_name["ext_pvrtc"]["testable_in_env"] is False
