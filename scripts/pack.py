"""Build a platform-specific desktop binary with nicegui-pack / PyInstaller.

Run from the repo root (or via scripts/pack.sh / scripts/pack.ps1):

    uv sync --group dev
    uv run python scripts/pack.py

Produces a single artefact under dist/ named for the current OS, e.g.:
  NysasFinancialTracker-Windows.exe
  NysasFinancialTracker-macOS-arm64.zip   (contains NysasFinancialTracker.app)
  NysasFinancialTracker-Linux.zip         (contains NysasFinancialTracker)
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import zipfile
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
        # Zip so GitHub Releases / browsers download a file with an extension,
        # and so Finder users get a double-clickable .app after unzip.
        return f"{APP_NAME}-macOS-{arch}.zip"
    # Same for Linux: extensionless binaries look broken in downloads.
    return f"{APP_NAME}-Linux.zip"


def _zip_with_cli(paths: list[Path], zip_path: Path, *, preserve_symlinks: bool) -> None:
    """Create a zip via the system zip tool (preserves Unix modes / optional symlinks)."""
    if zip_path.exists():
        zip_path.unlink()
    args = ["zip", "-r"]
    if preserve_symlinks:
        args.append("-y")
    args.append(str(zip_path.name))
    args.extend(p.name for p in paths)
    result = subprocess.run(args, cwd=paths[0].parent, check=False)
    if result.returncode != 0 or not zip_path.is_file():
        raise RuntimeError(f"Failed to create {zip_path}")


def _zip_linux_binary(binary: Path, zip_path: Path) -> None:
    """Zip a single Linux binary, keeping the executable bit when possible."""
    if zip_path.exists():
        zip_path.unlink()

    # Prefer system zip so Unix permission bits are stored correctly.
    if shutil.which("zip"):
        _zip_with_cli([binary], zip_path, preserve_symlinks=False)
        return

    # Fallback (e.g. unusual CI images): mark as executable in the zip metadata.
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo(binary.name)
        info.create_system = 3  # Unix
        info.external_attr = 0o100755 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, binary.read_bytes())


def main() -> int:
    dist = ROOT / "dist"
    data_dir = ROOT / "src" / "finance_app" / "data"
    if not data_dir.is_dir():
        print(f"Missing package data directory: {data_dir}", file=sys.stderr)
        return 1

    sep = ";" if platform.system() == "Windows" else ":"
    add_data = f"{data_dir}{sep}finance_app/data"
    system = platform.system()
    is_macos = system == "Darwin"
    is_linux = system == "Linux"

    # macOS: onedir + windowed → proper .app (onefile+windowed is discouraged
    # by PyInstaller and ships an extensionless Mach-O that confuses downloads).
    # Windows / Linux: keep a single-file binary, then zip Linux for a clear download name.
    cmd = [
        sys.executable,
        "-m",
        "nicegui.scripts.pack",
        "--name",
        APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--add-data",
        add_data,
    ]
    if not is_macos:
        cmd.append("--onefile")
    cmd.append(str(ROOT / "main.py"))

    print("Running:")
    print(" ", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    if result.returncode != 0:
        return result.returncode

    target = dist / artefact_basename()

    if is_macos:
        app_bundle = dist / f"{APP_NAME}.app"
        if not app_bundle.is_dir():
            print(f"Expected macOS app bundle at {app_bundle}", file=sys.stderr)
            return 1
        try:
            _zip_with_cli([app_bundle], target, preserve_symlinks=True)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1
        # Drop unpackaged build leftovers so only the release zip remains.
        shutil.rmtree(app_bundle, ignore_errors=True)
        onedir = dist / APP_NAME
        if onedir.is_dir():
            shutil.rmtree(onedir, ignore_errors=True)
        bare = dist / APP_NAME
        if bare.is_file():
            bare.unlink()
    elif is_linux:
        built = dist / APP_NAME
        if not built.is_file():
            candidates = [p for p in sorted(dist.glob(f"{APP_NAME}*")) if p.is_file()]
            if not candidates:
                print(f"No build output found in {dist}", file=sys.stderr)
                return 1
            built = candidates[0]
        # Stable name inside the archive.
        packaged = dist / APP_NAME
        if built.resolve() != packaged.resolve():
            if packaged.exists():
                packaged.unlink()
            shutil.move(str(built), str(packaged))
        packaged.chmod(packaged.stat().st_mode | 0o111)
        try:
            _zip_linux_binary(packaged, target)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1
        packaged.unlink(missing_ok=True)
    else:
        built = dist / (f"{APP_NAME}.exe" if system == "Windows" else APP_NAME)
        if not built.exists():
            candidates = sorted(dist.glob(f"{APP_NAME}*"))
            if not candidates:
                print(f"No build output found in {dist}", file=sys.stderr)
                return 1
            built = candidates[0]

        if built.resolve() != target.resolve():
            if target.exists():
                target.unlink()
            shutil.move(str(built), str(target))

    print(f"Built: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
