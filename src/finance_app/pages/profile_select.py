"""Profile picker — first screen for personal local tooling."""

from __future__ import annotations

from nicegui import ui

from finance_app.services import profiles as profile_service
from finance_app.ui.components import page_header
from finance_app.ui.theme import apply_theme


def register() -> None:
    @ui.page("/profiles")
    def profiles_page() -> None:
        apply_theme()
        with ui.element("div").classes("page-wrap"):
            page_header(
                "Nysa's Financial Tracker",
                "Choose a local profile. Data is stored on this computer.",
            )

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


def _profile_card(profile: dict) -> None:
    def open_profile() -> None:
        profile_service.select_profile(profile["slug"])
        ui.navigate.to("/")

    with ui.element("div").classes("profile-card").on("click", open_profile):
        ui.label(profile["name"]).classes("text-lg font-semibold")
        ui.label(profile["slug"]).style("color: var(--text-muted); font-size: 0.85rem;")
        ui.html('<span class="badge">Local</span>', sanitize=False)
