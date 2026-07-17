"""Application entrypoint and page registration."""

from __future__ import annotations

import multiprocessing
from multiprocessing import freeze_support

from nicegui import app, native, ui

from finance_app.config import APP_TITLE
from finance_app.db.session import get_current_profile
from finance_app.pages import (
    calculators,
    edit_data,
    guide,
    overview,
    profile_select,
    view_data,
    visualisations,
)
from finance_app.services import profiles as profile_service


def _register_pages() -> None:
    profile_select.register()
    overview.register()
    view_data.register()
    edit_data.register()
    visualisations.register()
    calculators.register()
    guide.register()


def _startup() -> None:
    """Auto-open last profile when present; otherwise land on picker."""
    if get_current_profile() is not None:
        return
    last = profile_service.get_last_opened()
    if last and profile_service.profile_exists(last):
        try:
            profile_service.select_profile(last)
        except ValueError:
            pass


def main(*, native_window: bool | None = None, reload: bool = False) -> None:
    """Run the UK Finance desktop app."""
    import os
    import sys

    freeze_support()
    _register_pages()
    app.on_startup(_startup)

    if native_window is None:
        if os.environ.get("UK_FINANCE_BROWSER") == "1":
            native_window = False
        elif sys.platform == "linux" and not os.environ.get(
            "DISPLAY"
        ) and not os.environ.get("WAYLAND_DISPLAY"):
            native_window = False
        else:
            native_window = True

    # Native window settings must be set outside the main-guard child process path.
    if native_window:
        app.native.window_args["title"] = APP_TITLE
        app.native.window_args["min_size"] = (1100, 720)

    ui.run(
        title=APP_TITLE,
        dark=True,
        reload=reload,
        native=native_window,
        port=native.find_open_port() if native_window else 8080,
        show=not native_window,
        storage_secret="nysas-financial-tracker-local",
    )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
