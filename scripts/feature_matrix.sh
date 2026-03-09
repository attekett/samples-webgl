#!/bin/bash
# Feature coverage matrix — delegates to AST-based Python analysis.
# Covers both samples-webgl/ and agent_outputs/ using feature_categories.json.
# Use --all to include ubiquitous features (buffer_ops, draw_calls, etc.)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
exec "$ROOT/venv/bin/python" "$SCRIPT_DIR/feature_coverage.py" "$@"
