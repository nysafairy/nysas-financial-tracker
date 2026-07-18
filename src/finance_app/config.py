"""Paths and application configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "NysasFinancialTracker"
APP_TITLE = "Nysa's Financial Tracker"
PROFILES_FILENAME = "profiles.json"
DB_FILENAME = "finance.db"
SCHEMA_VERSION = 8


def default_data_root() -> Path:
    """Return the default directory for profile databases."""
    override = os.environ.get("UK_FINANCE_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / "Documents" / APP_NAME).resolve()


def ensure_data_root(root: Path | None = None) -> Path:
    path = root or default_data_root()
    path.mkdir(parents=True, exist_ok=True)
    return path


def profiles_path(root: Path | None = None) -> Path:
    return ensure_data_root(root) / PROFILES_FILENAME


def profile_dir(slug: str, root: Path | None = None) -> Path:
    return ensure_data_root(root) / slug


def profile_db_path(slug: str, root: Path | None = None) -> Path:
    return profile_dir(slug, root) / DB_FILENAME


def load_profiles_meta(root: Path | None = None) -> dict:
    path = profiles_path(root)
    if not path.exists():
        return {"profiles": [], "last_opened": None}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("profiles", [])
    data.setdefault("last_opened", None)
    return data


def save_profiles_meta(meta: dict, root: Path | None = None) -> None:
    path = profiles_path(root)
    ensure_data_root(root)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)


def package_data_dir() -> Path:
    """Bundled reference data shipped with the app."""
    return Path(__file__).resolve().parent / "data"
