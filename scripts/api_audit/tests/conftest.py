import json
import pytest
from pathlib import Path

# Project root is 3 levels up from tests/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture
def feature_categories():
    """Load feature_categories.json config."""
    path = PROJECT_ROOT / "docs" / "feature_categories.json"
    return json.loads(path.read_text())


@pytest.fixture
def interaction_topology():
    """Load interaction_topology.json config."""
    path = PROJECT_ROOT / "docs" / "interaction_topology.json"
    return json.loads(path.read_text())


@pytest.fixture
def api_surface():
    """Load webgl_api_surface.json."""
    path = PROJECT_ROOT / "docs" / "webgl_api_surface.json"
    return json.loads(path.read_text())


@pytest.fixture
def corpus_dirs():
    """Return paths to corpus directories."""
    return [
        PROJECT_ROOT / "samples-webgl",
        PROJECT_ROOT / "agent_outputs",
    ]
