"""Shared page chrome: header and nav."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from nicegui import ui

from finance_app.db.session import get_current_profile
from finance_app.services import profiles as profile_service
from finance_app.ui.theme import apply_theme

NAV_ITEMS = [
    ("/", "Overview"),
    ("/view", "View data"),
    ("/edit", "Edit data"),
    ("/visualisations", "Visualisations"),
    ("/tax", "Tax & tools"),
    ("/guide", "Guide"),
]


def _profile_label() -> str:
    slug = get_current_profile()
    if not slug:
        return "No profile"
    for profile in profile_service.list_profiles():
        if profile["slug"] == slug:
            return profile["name"]
    return slug


@contextmanager
def render_shell(active_path: str) -> Iterator[None]:
    """Shared chrome for pages that require an open profile."""
    apply_theme()
    with ui.element("div").classes("app-shell"):
        with ui.element("div").classes("app-header"):
            ui.html(
                f'<div class="brand"><span>Nysa\'s</span> Financial Tracker</div>',
                sanitize=False,
            )
            with ui.element("div").classes("nav-row"):
                for path, label in NAV_ITEMS:
                    classes = "nav-link active" if path == active_path else "nav-link"
                    ui.link(label, path).classes(classes)
            with ui.row().classes("items-center gap-3"):
                ui.label(_profile_label()).classes("text-sm").style(
                    "color: var(--text-muted);"
                )
                ui.button(
                    "Switch profile",
                    on_click=lambda: ui.navigate.to("/profiles"),
                ).props("flat dense").classes("text-sm")
        with ui.element("div").classes("page-wrap"):
            yield


def require_profile() -> bool:
    """Redirect to profile picker if none is open. Returns True when OK."""
    if get_current_profile() is None:
        ui.navigate.to("/profiles")
        return False
    return True
