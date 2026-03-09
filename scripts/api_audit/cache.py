import hashlib
import json
from pathlib import Path


class FileCache:
    """Two-layer SHA256-keyed cache for audit results."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self._layer1_dir = self.cache_dir / 'files'
        self._layer2_dir = self.cache_dir / 'eval'

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def store(self, filename: str, content: str, data: dict, config_hash: str = ""):
        """Layer 1: store per-file parse results keyed by content + config hash."""
        self._layer1_dir.mkdir(parents=True, exist_ok=True)
        combined = content + "\x00" + config_hash
        content_hash = self._hash(combined)
        cache_file = self._layer1_dir / f'{content_hash}.json'
        cache_file.write_text(json.dumps(data))

    def lookup(self, filename: str, content: str, config_hash: str = "") -> dict | None:
        """Layer 1: look up cached parse results."""
        combined = content + "\x00" + config_hash
        content_hash = self._hash(combined)
        cache_file = self._layer1_dir / f'{content_hash}.json'
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        return None

    def store_evaluation(self, surface_hash: str, agg_hash: str, report: dict):
        """Layer 2: store evaluation results keyed by surface + aggregated data."""
        self._layer2_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._layer2_dir / f'{surface_hash}_{agg_hash}.json'
        cache_file.write_text(json.dumps(report))

    def lookup_evaluation(self, surface_hash: str, agg_hash: str) -> dict | None:
        """Layer 2: look up cached evaluation."""
        cache_file = self._layer2_dir / f'{surface_hash}_{agg_hash}.json'
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        return None
