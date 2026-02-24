import sys
import json
import pytest
from pathlib import Path

# Make 'import api_audit' work without install
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def surface():
    """Minimal API surface for testing."""
    return json.loads((FIXTURES / "surface" / "test_surface.json").read_text())


@pytest.fixture
def parse_html():
    """Returns a function: filename -> tree-sitter root node."""
    from api_audit.html_extract import extract_script
    from api_audit.parse import parse_js

    def _parse(filename):
        html = (FIXTURES / "synthetic" / filename).read_text()
        script = extract_script(html)
        return parse_js(script)

    return _parse


@pytest.fixture
def fixture_path():
    """Returns a function: filename -> full Path to synthetic fixture."""
    def _path(filename):
        return FIXTURES / "synthetic" / filename
    return _path
