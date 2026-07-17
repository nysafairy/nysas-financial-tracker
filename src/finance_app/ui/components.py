"""Reusable UI building blocks."""

from __future__ import annotations

from typing import Any

from nicegui import ui


def page_header(title: str, subtitle: str = "") -> None:
    ui.html(f'<h1 class="page-title">{title}</h1>', sanitize=False)
    if subtitle:
        ui.html(f'<p class="page-subtitle">{subtitle}</p>', sanitize=False)


def metric_card(label: str, value: str) -> None:
    with ui.element("div").classes("metric-card"):
        ui.html(f'<div class="metric-label">{label}</div>', sanitize=False)
        ui.html(f'<div class="metric-value">{value}</div>', sanitize=False)


def panel(title: str):
    container = ui.element("div").classes("panel")
    with container:
        ui.html(f'<h2 class="panel-title">{title}</h2>', sanitize=False)
    return container


def format_gbp(amount: float | None) -> str:
    if amount is None:
        return "—"
    sign = "-" if amount < 0 else ""
    return f"{sign}£{abs(amount):,.2f}"


def plotly_chart(
    figure: Any,
    *,
    height: str = "360px",
    show_modebar: bool = False,
) -> None:
    """Render a Plotly chart. Mode bar is off by default — it steals chart space."""
    if hasattr(figure, "to_plotly_json"):
        payload = figure.to_plotly_json()
    else:
        payload = dict(figure)
    payload["config"] = {
        **(payload.get("config") or {}),
        "displayModeBar": show_modebar,
        "responsive": True,
        "displaylogo": False,
    }
    ui.plotly(payload).classes("w-full").style(f"height: {height}; min-height: {height};")


def result_box(text: str = "") -> ui.label:
    label = ui.label(text).classes("result-box w-full")
    return label
