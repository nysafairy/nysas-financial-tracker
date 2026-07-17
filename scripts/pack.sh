#!/usr/bin/env bash
# Package Nysa's Financial Tracker for the current OS (macOS / Linux).
# For Windows, use scripts/pack.ps1 from PowerShell.
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --group dev
uv run python scripts/pack.py
echo "Built artefacts are under ./dist/"
