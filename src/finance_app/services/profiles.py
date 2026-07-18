"""Local profile registry (no cloud auth)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from finance_app.config import (
    default_data_root,
    load_profiles_meta,
    profile_db_path,
    profile_dir,
    save_profiles_meta,
)
from finance_app.db.seed import seed_demo_data
from finance_app.db.session import close_profile, get_current_profile, open_profile


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "profile"


def list_profiles(root: Path | None = None) -> list[dict]:
    meta = load_profiles_meta(root)
    current = get_current_profile()
    rows: list[dict] = []
    for profile in meta.get("profiles", []):
        slug = profile["slug"]
        db_path = profile_db_path(slug, root)
        rows.append(
            {
                **profile,
                "is_open": slug == current,
                "is_last_opened": slug == meta.get("last_opened"),
                "db_exists": db_path.exists(),
                "data_path": str(profile_dir(slug, root)),
            }
        )
    return rows


def get_profile(slug: str, root: Path | None = None) -> dict | None:
    for profile in list_profiles(root):
        if profile["slug"] == slug:
            return profile
    return None


def get_last_opened(root: Path | None = None) -> str | None:
    return load_profiles_meta(root).get("last_opened")


def data_root_path(root: Path | None = None) -> Path:
    return default_data_root() if root is None else Path(root)


def create_profile(
    display_name: str,
    *,
    seed_demo: bool = False,
    root: Path | None = None,
) -> dict:
    name = display_name.strip()
    if not name:
        raise ValueError("Profile name is required")

    meta = load_profiles_meta(root)
    base_slug = _slugify(name)
    slug = base_slug
    existing = {p["slug"] for p in meta["profiles"]}
    suffix = 2
    while slug in existing:
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    profile = {"slug": slug, "name": name}
    meta["profiles"].append(profile)
    meta["last_opened"] = slug
    save_profiles_meta(meta, root)

    open_profile(slug, root)
    if seed_demo:
        seed_demo_data()
    return profile


def select_profile(slug: str, root: Path | None = None) -> Path:
    meta = load_profiles_meta(root)
    if not any(p["slug"] == slug for p in meta["profiles"]):
        raise ValueError(f"Unknown profile: {slug}")
    meta["last_opened"] = slug
    save_profiles_meta(meta, root)
    return open_profile(slug, root)


def rename_profile(
    slug: str,
    display_name: str,
    *,
    root: Path | None = None,
) -> dict:
    """Change the display name. Folder slug stays the same so paths remain stable."""
    name = display_name.strip()
    if not name:
        raise ValueError("Profile name is required")

    meta = load_profiles_meta(root)
    for profile in meta["profiles"]:
        if profile["slug"] == slug:
            profile["name"] = name
            save_profiles_meta(meta, root)
            return {"slug": slug, "name": name}
    raise ValueError(f"Unknown profile: {slug}")


def delete_profile(slug: str, *, root: Path | None = None) -> None:
    """Remove a profile from the registry and delete its local database folder."""
    meta = load_profiles_meta(root)
    if not any(p["slug"] == slug for p in meta["profiles"]):
        raise ValueError(f"Unknown profile: {slug}")

    if get_current_profile() == slug:
        close_profile()

    meta["profiles"] = [p for p in meta["profiles"] if p["slug"] != slug]
    if meta.get("last_opened") == slug:
        meta["last_opened"] = (
            meta["profiles"][0]["slug"] if meta["profiles"] else None
        )
    save_profiles_meta(meta, root)

    directory = profile_dir(slug, root)
    if directory.exists():
        shutil.rmtree(directory)


def clear_open_profile() -> None:
    """Leave the current profile without deleting it (return to picker)."""
    close_profile()


def profile_exists(slug: str, root: Path | None = None) -> bool:
    return profile_db_path(slug, root).exists()
