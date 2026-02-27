"""Integration tests for Phase 1 pipeline."""
import json
import subprocess
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture
def venv_python():
    """Path to venv python."""
    venv = PROJECT_ROOT / "venv" / "bin" / "python"
    if venv.exists():
        return str(venv)
    return sys.executable


class TestCLIFlags:
    def test_combination_matrix_flag(self, venv_python, tmp_path):
        """--combination-matrix produces valid JSON output."""
        output = tmp_path / "matrix.json"
        env = {"PYTHONPATH": str(PROJECT_ROOT / "scripts"),
               "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [venv_python, "-m", "api_audit",
             "--surface", str(PROJECT_ROOT / "docs" / "webgl_api_surface.json"),
             "--corpus-dirs", str(PROJECT_ROOT / "samples-webgl"),
             "--feature-categories", str(PROJECT_ROOT / "docs" / "feature_categories.json"),
             "--interaction-topology", str(PROJECT_ROOT / "docs" / "interaction_topology.json"),
             "--combination-matrix", str(output),
             "--n-way", "2"],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert output.exists()
        data = json.loads(output.read_text())
        assert "2way_combinations" in data
        combos = data["2way_combinations"]
        assert combos["total"] > 0
        assert combos["covered"] > 0
        assert "gaps" in combos

    def test_existing_audit_still_works(self, venv_python):
        """Existing audit functionality is not broken."""
        env = {"PYTHONPATH": str(PROJECT_ROOT / "scripts"),
               "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [venv_python, "-m", "api_audit",
             "--surface", str(PROJECT_ROOT / "docs" / "webgl_api_surface.json"),
             "--corpus-dirs", str(PROJECT_ROOT / "samples-webgl")],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Analyzed" in result.stdout

    def test_matrix_includes_config_only_features(self, venv_python, tmp_path):
        """feature_count includes features from config even if 0-seed."""
        output = tmp_path / "matrix.json"
        cats_path = PROJECT_ROOT / "docs" / "feature_categories.json"
        env = {"PYTHONPATH": str(PROJECT_ROOT / "scripts"),
               "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [venv_python, "-m", "api_audit",
             "--surface", str(PROJECT_ROOT / "docs" / "webgl_api_surface.json"),
             "--corpus-dirs", str(PROJECT_ROOT / "samples-webgl"),
             str(PROJECT_ROOT / "agent_outputs"),
             "--feature-categories", str(cats_path),
             "--interaction-topology", str(PROJECT_ROOT / "docs" / "interaction_topology.json"),
             "--combination-matrix", str(output),
             "--n-way", "2"],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        data = json.loads(output.read_text())
        all_cats = json.loads(cats_path.read_text())["categories"]
        assert data["feature_count"] >= len(all_cats)
