# Package Nysa's Financial Tracker for Windows.
# Run from PowerShell (not WSL) so the .exe is a native Windows binary.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
uv sync --group dev
uv run python scripts/pack.py
Write-Host "Built artefacts are under .\dist\"
