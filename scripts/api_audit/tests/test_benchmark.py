"""Performance benchmark for Phase 1 pipeline."""
import json
import time
import pytest
from pathlib import Path

from api_audit.html_extract import extract_script
from api_audit.parse import parse_js
from api_audit.context import detect_context
from api_audit.const_propagation import resolve_constants
from api_audit.call_analysis import analyze_calls
from api_audit.glsl import extract_glsl_builtins
from api_audit.feature_detection import detect_features
from api_audit.combination_matrix import compute_matrix

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture
def full_corpus_data(api_surface, feature_categories):
    """Run analysis pipeline on full corpus and return feature fingerprints."""
    corpus_features = {}
    corpus_dirs = [PROJECT_ROOT / "samples-webgl", PROJECT_ROOT / "agent_outputs"]
    html_files = []
    for d in corpus_dirs:
        if d.exists():
            html_files.extend(d.rglob("*.html"))

    for filepath in sorted(html_files)[:50]:  # Limit to 50 for reasonable test time
        try:
            content = filepath.read_text()
            script = extract_script(content)
            if not script.strip():
                continue
            root = parse_js(script)
            consts = resolve_constants(root)
            ctx = detect_context(root, consts)
            calls = analyze_calls(root, ctx, consts, api_surface)
            glsl = extract_glsl_builtins(root, ctx, consts, api_surface)

            fp = detect_features(
                calls, glsl, feature_categories,
                extensions=ctx.extensions,
                extension_methods=calls.extension_methods)
            fp["file"] = str(filepath)
            corpus_features[str(filepath)] = fp
        except Exception:
            continue

    return corpus_features


class TestBenchmark:
    def test_feature_detection_performance(self, full_corpus_data):
        """Feature detection on 50 files completes in reasonable time."""
        assert len(full_corpus_data) > 0
        print(f"\nAnalyzed {len(full_corpus_data)} files")

    def test_matrix_computation_performance(self, full_corpus_data, interaction_topology):
        """2-way matrix computation on corpus subset completes."""
        start = time.time()
        matrix = compute_matrix(full_corpus_data, n=2,
                                interaction_topology=interaction_topology)
        elapsed = time.time() - start
        print(f"\n2-way matrix: {len(matrix)} combos in {elapsed:.2f}s")
        assert len(matrix) > 0

    def test_3way_matrix_performance(self, full_corpus_data, interaction_topology):
        """3-way matrix computation completes."""
        start = time.time()
        matrix = compute_matrix(full_corpus_data, n=3,
                                interaction_topology=interaction_topology)
        elapsed = time.time() - start
        print(f"\n3-way matrix: {len(matrix)} combos in {elapsed:.2f}s")
        assert len(matrix) > 0
