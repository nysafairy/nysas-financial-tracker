"""Local profile registry (no cloud auth)."""

from __future__ import annotations

import re
from pathlib import Path

from finance_app.config import (
    load_profiles_meta,
    profile_db_path,
    save_profiles_meta,
)
from finance_app.db.seed import seed_demo_data
from finance_app.db.session import open_profile


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "profile"


def list_profiles(root: Path | None = None) -> list[dict]:
    meta = load_profiles_meta(root)
    return list(meta.get("profiles", []))


def get_last_opened(root: Path | None = None) -> str | None:
    return load_profiles_meta(root).get("last_opened")


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


def profile_exists(slug: str, root: Path | None = None) -> bool:
    return profile_db_path(slug, root).exists()
