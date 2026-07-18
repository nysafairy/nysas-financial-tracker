"""Profile picker and management — local profiles only."""

from __future__ import annotations

from nicegui import ui

from finance_app.db.session import get_current_profile
from finance_app.services import profiles as profile_service
from finance_app.ui.components import page_header
from finance_app.ui.theme import apply_theme


def register() -> None:
    @ui.page("/profiles")
    def profiles_page() -> None:
        apply_theme()
        with ui.element("div").classes("page-wrap"):
            page_header(
                "Profiles",
                "Each profile is a separate local database on this computer.",
            )

            data_root = profile_service.data_root_path()
            ui.label(f"Data folder: {data_root}").style(
                "color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem;"
            )

            current = get_current_profile()
            if current:
                current_meta = profile_service.get_profile(current)
                current_name = (
                    current_meta["name"] if current_meta else current
                )
                with ui.row().classes("items-center gap-2").style("margin-bottom: 1rem;"):
                    ui.label(f"Open: {current_name}").style(
                        "color: var(--text-muted);"
                    )

                    def leave() -> None:
                        profile_service.clear_open_profile()
                        ui.notify("Closed profile", type="info")
                        ui.navigate.to("/profiles")

                    def back_to_app() -> None:
                        ui.navigate.to("/")

                    ui.button("Back to app", on_click=back_to_app).props(
                        "flat dense"
                    )
                    ui.button("Close profile", on_click=leave).props("flat dense")

            profiles = profile_service.list_profiles()
            if profiles:
                ui.label("Your profiles").classes("text-lg font-medium mb-2")
                with ui.element("div").classes("responsive-grid").style(
                    "margin-bottom: 1.5rem;"
                ):
                    for profile in profiles:
                        _profile_card(profile)
            else:
                ui.label("No profiles yet — create one below.").style(
                    "color: var(--text-muted); margin-bottom: 1rem;"
                )

            with ui.element("div").classes("panel"):
                ui.html('<h2 class="panel-title">Create profile</h2>', sanitize=False)
                with ui.element("div").classes("form-stack"):
                    name_input = ui.input(
                        "Profile name", placeholder="e.g. Personal"
                    ).classes("w-full")
                    seed_demo = ui.checkbox("Load demo sample data", value=True)

                    def create() -> None:
                        try:
                            profile_service.create_profile(
                                name_input.value or "",
                                seed_demo=bool(seed_demo.value),
                            )
                            ui.notify("Profile created", type="positive")
                            ui.navigate.to("/")
                        except ValueError as exc:
                            ui.notify(str(exc), type="negative")

                    with ui.element("div").classes("form-actions"):
                        ui.button("Create and open", on_click=create)


def _refresh() -> None:
    ui.navigate.to("/profiles")


def _profile_card(profile: dict) -> None:
    slug = profile["slug"]

    def open_this() -> None:
        profile_service.select_profile(slug)
        ui.navigate.to("/")

    with ui.element("div").classes("profile-card profile-card-managed"):
        with ui.element("div").classes("profile-card-main").on("click", open_this):
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.label(profile["name"]).classes("text-lg font-semibold")
                if profile.get("is_open"):
                    ui.html(
                        '<span class="badge badge-accent">Open</span>',
                        sanitize=False,
                    )
                elif profile.get("is_last_opened"):
                    ui.html(
                        '<span class="badge">Last used</span>',
                        sanitize=False,
                    )
                else:
                    ui.html('<span class="badge">Local</span>', sanitize=False)
            ui.label(slug).style(
                "color: var(--text-muted); font-size: 0.85rem; display: block;"
            )
            ui.label(profile.get("data_path", "")).style(
                "color: var(--text-muted); font-size: 0.75rem; word-break: break-all;"
            )

        with ui.row().classes("profile-card-actions gap-1"):
            ui.button(
                "Open",
                on_click=open_this,
            ).props("flat dense color=primary")

            def rename() -> None:
                with ui.dialog() as dialog, ui.card().classes("w-96"):
                    ui.label("Rename profile").classes("text-lg font-medium")
                    ui.label(
                        "Only the display name changes. The folder id stays the same."
                    ).style(
                        "color: var(--text-muted); font-size: 0.85rem; margin-bottom: 0.75rem;"
                    )
                    new_name = ui.input("Name", value=profile["name"]).classes("w-full")

                    def apply_rename() -> None:
                        try:
                            profile_service.rename_profile(slug, new_name.value or "")
                        except ValueError as exc:
                            ui.notify(str(exc), type="warning")
                            return
                        dialog.close()
                        ui.notify("Profile renamed", type="positive")
                        _refresh()

                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button("Cancel", on_click=dialog.close).props("flat")
                        ui.button("Save", on_click=apply_rename).props(
                            "color=primary unelevated"
                        )
                dialog.open()

            ui.button("Rename", on_click=rename).props("flat dense")

            def confirm_delete() -> None:
                with ui.dialog() as dialog, ui.card().classes("w-96"):
                    ui.label("Delete profile?").classes("text-lg font-medium")
                    ui.html(
                        f"<p>This permanently deletes <strong>{profile['name']}</strong> "
                        f"and its local database folder.</p>"
                        "<p style='color:var(--text-muted);font-size:0.9rem'>"
                        "This cannot be undone. Export a CSV zip from View data first "
                        "if you need a backup.</p>",
                        sanitize=False,
                    )

                    def do_delete() -> None:
                        try:
                            profile_service.delete_profile(slug)
                        except ValueError as exc:
                            ui.notify(str(exc), type="warning")
                            return
                        dialog.close()
                        ui.notify("Profile deleted", type="info")
                        _refresh()

                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button("Cancel", on_click=dialog.close).props("flat")
                        ui.button("Delete forever", on_click=do_delete).props(
                            "color=negative unelevated"
                        )
                dialog.open()

            ui.button("Delete", on_click=confirm_delete).props(
                "flat dense color=negative"
            )
