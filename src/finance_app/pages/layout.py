"""Shared page chrome: header, nav, and snapshot session bar."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Iterator

from nicegui import ui

from finance_app.db.session import get_current_profile
from finance_app.services import draft_session
from finance_app.services import profiles as profile_service
from finance_app.ui.theme import apply_theme

NAV_ITEMS = [
    ("/", "Overview"),
    ("/view", "View data"),
    ("/edit", "Edit data"),
    ("/visualisations", "Visualisations"),
    ("/forecasting", "Forecasting"),
    ("/income-report", "Income report"),
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


def _format_updated(updated_at) -> str:
    if updated_at is None:
        return ""
    if hasattr(updated_at, "strftime"):
        return updated_at.strftime("%H:%M:%S")
    return str(updated_at)


def _render_session_bar() -> None:
    meta = draft_session.get_draft_meta()
    with ui.element("div").classes("session-bar"):
        if meta is None:
            ui.html(
                '<span class="session-bar-label">View mode</span>'
                "<span class=\"session-bar-hint\">"
                "Charts and data are read-only until you start a snapshot session. "
                "To change a past date, start a session then use History → Edit this snapshot."
                "</span>",
                sanitize=False,
            )
            with ui.element("div").classes("session-bar-actions"):
                start_date = ui.date_input(
                    "Snapshot date", value=date.today()
                ).classes("session-date")

                def start() -> None:
                    raw = start_date.value or date.today()
                    if isinstance(raw, str):
                        as_of = date.fromisoformat(raw[:10])
                    else:
                        as_of = raw
                    draft_session.start_draft(as_of)
                    ui.notify(
                        f"Snapshot session started for {as_of.isoformat()}",
                        type="positive",
                    )
                    ui.navigate.to("/edit")

                ui.button("Start new snapshot", on_click=start).props(
                    "color=primary unelevated"
                )
            return

        as_of = meta["as_of_date"]
        as_of_text = as_of.isoformat() if hasattr(as_of, "isoformat") else str(as_of)
        ui.html(
            f'<span class="session-bar-badge">Editing snapshot · {as_of_text}</span>'
            f'<span class="session-bar-hint">Autosaved {_format_updated(meta["updated_at"])}. '
            "Overview and charts include this draft until you save or discard.</span>",
            sanitize=False,
        )

        with ui.element("div").classes("session-bar-actions"):

            def save() -> None:
                try:
                    result = draft_session.commit_draft()
                except ValueError as exc:
                    ui.notify(str(exc), type="warning", close_button=True)
                    return
                ui.notify(
                    f"Saved snapshot for {result['as_of_date'].isoformat()} "
                    f"({result['balances_written']} balances)",
                    type="positive",
                )
                ui.navigate.to("/")

            def discard() -> None:
                with ui.dialog() as dialog, ui.card():
                    ui.label(
                        "Discard this draft? Committed history is unchanged."
                    )
                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button("Cancel", on_click=dialog.close).props("flat")

                        def confirm() -> None:
                            draft_session.discard_draft()
                            dialog.close()
                            ui.notify("Draft discarded", type="info")
                            ui.navigate.to("/")

                        ui.button("Discard draft", on_click=confirm).props(
                            "color=negative"
                        )
                dialog.open()

            ui.button("Save snapshot", on_click=save).props("color=primary unelevated")
            ui.button("Discard draft", on_click=discard).props("flat")


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
                    "Manage profiles",
                    on_click=lambda: ui.navigate.to("/profiles"),
                ).props("flat dense").classes("text-sm")
        _render_session_bar()
        with ui.element("div").classes("page-wrap"):
            yield


def require_profile() -> bool:
    """Redirect to profile picker if none is open. Returns True when OK."""
    if get_current_profile() is None:
        ui.navigate.to("/profiles")
        return False
    return True


def require_draft_session() -> bool:
    """True when a draft is open; otherwise caller should show the gate UI."""
    return draft_session.has_draft()
