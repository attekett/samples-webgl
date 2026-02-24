import json
import pytest
from pathlib import Path
from api_audit.html_extract import extract_script
from api_audit.parse import parse_js
from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants
from api_audit.call_analysis import analyze_calls
from api_audit.glsl import extract_glsl_builtins

SEEDS = Path(__file__).parent / "fixtures" / "seeds"


def _full_pipeline(filepath: Path, surface: dict):
    """Run complete analysis pipeline on a file."""
    html = filepath.read_text()
    script = extract_script(html)
    root = parse_js(script)
    consts = resolve_constants(root)
    ctx = detect_context(root, consts)
    calls = analyze_calls(root, ctx, consts, surface)
    glsl = extract_glsl_builtins(root, ctx, consts, surface)
    return {
        'methods': set(calls.methods.keys()),
        'extensions': ctx.extensions,
        'context': ctx.api_version,
        'glsl_builtins': glsl,
    }


def _load_expected(seed_name):
    expected_path = SEEDS / f"{seed_name}_expected.json"
    if not expected_path.exists():
        pytest.skip(f"Expected output not yet created: {expected_path}")
    return json.loads(expected_path.read_text())


class TestPinnedSeeds:
    @pytest.mark.parametrize("seed_file", [
        "seed_minimal_test.html",
        "extensions_color_buffer_float_rendering.html",
        "seed_integer_sync_transform_mrt_instanced.html",
        "compute_procedural_geometry.html",
    ])
    def test_methods_detected(self, seed_file, surface):
        filepath = SEEDS / seed_file
        if not filepath.exists():
            pytest.skip(f"Pinned seed not yet copied: {filepath}")
        result = _full_pipeline(filepath, surface)
        expected = _load_expected(seed_file.replace('.html', ''))
        for method in expected.get('expected_methods', []):
            assert method in result['methods'], f"Missing method: {method}"

    @pytest.mark.parametrize("seed_file", [
        "seed_minimal_test.html",
        "extensions_color_buffer_float_rendering.html",
        "seed_integer_sync_transform_mrt_instanced.html",
        "compute_procedural_geometry.html",
    ])
    def test_context_detected(self, seed_file, surface):
        filepath = SEEDS / seed_file
        if not filepath.exists():
            pytest.skip(f"Pinned seed not yet copied: {filepath}")
        result = _full_pipeline(filepath, surface)
        expected = _load_expected(seed_file.replace('.html', ''))
        assert result['context'] == expected.get('expected_context', 'webgl2')

    @pytest.mark.parametrize("seed_file", [
        "seed_minimal_test.html",
        "extensions_color_buffer_float_rendering.html",
        "seed_integer_sync_transform_mrt_instanced.html",
        "compute_procedural_geometry.html",
    ])
    def test_min_method_count(self, seed_file, surface):
        filepath = SEEDS / seed_file
        if not filepath.exists():
            pytest.skip(f"Pinned seed not yet copied: {filepath}")
        result = _full_pipeline(filepath, surface)
        expected = _load_expected(seed_file.replace('.html', ''))
        min_count = expected.get('min_method_count', 1)
        assert len(result['methods']) >= min_count, (
            f"Expected at least {min_count} methods, got {len(result['methods'])}"
        )

    @pytest.mark.parametrize("seed_file", [
        "extensions_color_buffer_float_rendering.html",
    ])
    def test_extensions_detected(self, seed_file, surface):
        filepath = SEEDS / seed_file
        if not filepath.exists():
            pytest.skip(f"Pinned seed not yet copied: {filepath}")
        result = _full_pipeline(filepath, surface)
        expected = _load_expected(seed_file.replace('.html', ''))
        for ext in expected.get('expected_extensions', []):
            assert ext in result['extensions'], f"Missing extension: {ext}"
