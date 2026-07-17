"""Desktop entrypoint for development and PyInstaller packaging."""

from __future__ import annotations

import multiprocessing
import os
import sys
from multiprocessing import freeze_support

from nicegui import app, native, ui

from finance_app.app import _register_pages, _startup
from finance_app.config import APP_TITLE


def _use_native_window() -> bool:
    """Prefer a native window when a display is available."""
    if os.environ.get("UK_FINANCE_BROWSER") == "1":
        return False
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not os.environ.get(
        "WAYLAND_DISPLAY"
    ):
        return False
    return True


app.native.window_args["title"] = APP_TITLE
app.native.window_args["min_size"] = (1100, 720)


if __name__ == "__main__":
    freeze_support()
    multiprocessing.freeze_support()
    _register_pages()
    app.on_startup(_startup)
    use_native = _use_native_window()
    ui.run(
        title=APP_TITLE,
        dark=True,
        reload=False,
        native=use_native,
        port=native.find_open_port() if use_native else 8080,
        show=not use_native,
        storage_secret="nysas-financial-tracker-local",
    )
