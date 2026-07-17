"""Build a platform-specific desktop binary with nicegui-pack / PyInstaller.

Run from the repo root (or via scripts/pack.sh / scripts/pack.ps1):

    uv sync --group dev
    uv run python scripts/pack.py

Produces a single file under dist/ named for the current OS, e.g.:
  NysasFinancialTracker-Windows.exe
  NysasFinancialTracker-macOS-arm64
  NysasFinancialTracker-Linux
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "NysasFinancialTracker"


def artefact_basename() -> str:
    system = platform.system()
    if system == "Windows":
        return f"{APP_NAME}-Windows.exe"
    if system == "Darwin":
        machine = platform.machine().lower()
        arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
        return f"{APP_NAME}-macOS-{arch}"
    return f"{APP_NAME}-Linux"


def main() -> int:
    dist = ROOT / "dist"
    data_dir = ROOT / "src" / "finance_app" / "data"
    if not data_dir.is_dir():
        print(f"Missing package data directory: {data_dir}", file=sys.stderr)
        return 1

    sep = ";" if platform.system() == "Windows" else ":"
    add_data = f"{data_dir}{sep}finance_app/data"

    cmd = [
        sys.executable,
        "-m",
        "nicegui.scripts.pack",
        "--name",
        APP_NAME,
        "--windowed",
        "--onefile",
        "--noconfirm",
        "--clean",
        "--add-data",
        add_data,
        str(ROOT / "main.py"),
    ]
    print("Running:")
    print(" ", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        return result.returncode

    built = dist / (f"{APP_NAME}.exe" if platform.system() == "Windows" else APP_NAME)
    if not built.exists():
        # PyInstaller sometimes uses the name without extension on Windows too
        candidates = sorted(dist.glob(f"{APP_NAME}*"))
        if not candidates:
            print(f"No build output found in {dist}", file=sys.stderr)
            return 1
        built = candidates[0]

    target = dist / artefact_basename()
    if built.resolve() != target.resolve():
        if target.exists():
            target.unlink()
        shutil.move(str(built), str(target))

    print(f"Built: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
