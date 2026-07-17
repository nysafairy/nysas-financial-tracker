"""Shared chart styling — UI accents stay pink/blue; charts use a wider palette."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

# Brand accents for primary series (net worth line, etc.)
ACCENT_PINK = "#f4b6c8"
ACCENT_BLUE = "#a8d4f0"

CHART_FONT = "Source Sans 3, Segoe UI, sans-serif"
CHART_TEXT = "#e8eef4"
CHART_MUTED = "#9aabbc"

# Distinct hues for multi-series charts (deliberately not near-identical shades).
CHART_PALETTE = [
    "#f4b6c8",  # baby pink
    "#5b9bd5",  # mid blue
    "#f0c75e",  # gold
    "#7dcea0",  # mint
    "#e07a5f",  # coral
    "#9b7ede",  # violet
    "#4ecdc4",  # teal
    "#f28482",  # salmon
    "#84a59d",  # sage
    "#f6bd60",  # amber
]

# Slightly deeper fills so light on-chart labels stay readable.
TREEMAP_PALETTE = [
    "#d4899c",
    "#4a8fc4",
    "#d4a84a",
    "#5fba8a",
    "#d06b52",
    "#8b6fd1",
    "#3db8b0",
    "#e0716e",
    "#6f9488",
    "#e0a84a",
]


def style_fig(fig: go.Figure, *, show_legend: bool = False) -> None:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": CHART_TEXT, "family": CHART_FONT, "size": 13},
        margin={"l": 48, "r": 20, "t": 24, "b": 48},
        showlegend=show_legend,
        legend={"orientation": "h", "font": {"family": CHART_FONT, "color": CHART_MUTED}},
        xaxis={"gridcolor": "rgba(232,238,244,0.08)"},
        yaxis={"gridcolor": "rgba(232,238,244,0.08)", "tickprefix": "£"},
        autosize=True,
    )


def allocation_treemap(allocation: list[dict[str, Any]]) -> go.Figure:
    """Dark-UI treemap with app typography; tiny tiles hide labels instead of cramping."""
    labels = [a["label"] for a in allocation]
    values = [a["value"] for a in allocation]
    colours = [TREEMAP_PALETTE[i % len(TREEMAP_PALETTE)] for i in range(len(allocation))]

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=[""] * len(labels),
            values=values,
            branchvalues="total",
            marker={
                "colors": colours,
                "line": {"width": 3, "color": "#0f1419"},
                "cornerradius": 8,
            },
            texttemplate=(
                "<span style='font-family:Source Sans 3,sans-serif'>"
                "<b>%{label}</b><br>"
                "%{percentRoot:.0%}<br>"
                "£%{value:,.0f}"
                "</span>"
            ),
            hovertemplate=(
                "<b>%{label}</b><br>£%{value:,.2f}<br>%{percentRoot:.1%}<extra></extra>"
            ),
            textposition="middle center",
            textfont={
                "family": CHART_FONT,
                "color": CHART_TEXT,
                "size": 15,
            },
            pathbar={"visible": False},
        )
    )
    style_fig(fig)
    fig.update_layout(
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        uniformtext={"minsize": 12, "mode": "hide"},
    )
    fig.update_traces(
        insidetextfont={"family": CHART_FONT, "color": CHART_TEXT, "size": 15},
        outsidetextfont={"family": CHART_FONT, "color": CHART_MUTED, "size": 12},
    )
    return fig
