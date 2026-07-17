"""Deeper and more varied visualisations."""

from __future__ import annotations

import plotly.graph_objects as go
from nicegui import ui

from finance_app.pages.layout import render_shell, require_profile
from finance_app.services import draft_session
from finance_app.services import income as income_service
from finance_app.services import metrics as metrics_service
from finance_app.ui.charts import (
    ACCENT_PINK,
    CHART_FONT,
    CHART_PALETTE,
    CHART_TEXT,
    allocation_treemap,
    style_fig,
)
from finance_app.ui.components import page_header, plotly_chart


def register() -> None:
    @ui.page("/visualisations")
    def visualisations_page() -> None:
        if not require_profile():
            return

        with render_shell("/visualisations"):
            page_header(
                "Visualisations",
                "Flows, composition, and trends — beyond plain bars where they help.",
            )
            draft_meta = draft_session.get_draft_meta()
            if draft_meta is not None:
                as_of = draft_meta["as_of_date"]
                as_of_text = (
                    as_of.isoformat() if hasattr(as_of, "isoformat") else str(as_of)
                )
                ui.html(
                    f'<div class="draft-banner">Showing draft overlay for snapshot '
                    f"{as_of_text}. Wealth charts include unsaved balances.</div>",
                    sanitize=False,
                )

            income = income_service.income_by_source()
            _income_sankey(income)
            _income_sunburst(income)

            series = metrics_service.net_worth_series()
            with ui.element("div").classes("panel"):
                ui.html(
                    '<h2 class="panel-title">Net worth trajectory</h2>',
                    sanitize=False,
                )
                if series:
                    fig = go.Figure(
                        data=[
                            go.Scatter(
                                x=[p["date"] for p in series],
                                y=[p["value"] for p in series],
                                mode="lines+markers",
                                line={"color": ACCENT_PINK, "width": 2.5},
                                marker={"size": 7, "color": CHART_PALETTE[1]},
                                name="Net worth",
                            )
                        ]
                    )
                    style_fig(fig)
                    plotly_chart(fig, height="400px")
                else:
                    ui.label("No snapshot history yet.")

            allocation = metrics_service.allocation_by_account_type()
            with ui.element("div").classes("panel"):
                ui.html(
                    '<h2 class="panel-title">Wealth treemap</h2>',
                    sanitize=False,
                )
                if allocation:
                    plotly_chart(allocation_treemap(allocation), height="420px")
                else:
                    ui.label("No allocation data yet.")

            account_series = metrics_service.account_balance_series()
            with ui.element("div").classes("panel"):
                ui.html(
                    '<h2 class="panel-title">Balances by account</h2>',
                    sanitize=False,
                )
                if account_series:
                    fig = go.Figure()
                    for idx, (name, points) in enumerate(account_series.items()):
                        fig.add_trace(
                            go.Scatter(
                                x=[p["date"] for p in points],
                                y=[p["value"] for p in points],
                                mode="lines",
                                name=name,
                                line={
                                    "color": CHART_PALETTE[idx % len(CHART_PALETTE)],
                                    "width": 2.5,
                                },
                            )
                        )
                    style_fig(fig, show_legend=True)
                    plotly_chart(fig, height="420px")
                else:
                    ui.label("No account balance series yet.")


def _income_sankey(income: dict) -> None:
    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Income flow (sources → category)</h2>',
            sanitize=False,
        )
        sources = [s for s in income.get("sources", []) if s["ytd_amount"] > 0]
        if not sources:
            ui.label(
                "Add income streams (Edit data → Income) to see salary, gigs, "
                "and investments flow into categories."
            )
            return

        categories = sorted({s["category_label"] for s in sources})
        labels = [s["name"] for s in sources] + categories
        source_idx = {s["name"]: i for i, s in enumerate(sources)}
        cat_idx = {c: len(sources) + i for i, c in enumerate(categories)}

        fig = go.Figure(
            data=[
                go.Sankey(
                    arrangement="snap",
                    node={
                        "label": labels,
                        "color": [
                            CHART_PALETTE[i % len(CHART_PALETTE)]
                            for i in range(len(labels))
                        ],
                        "pad": 16,
                        "thickness": 18,
                        "line": {"color": "#0f1419", "width": 0.5},
                    },
                    link={
                        "source": [source_idx[s["name"]] for s in sources],
                        "target": [cat_idx[s["category_label"]] for s in sources],
                        "value": [s["ytd_amount"] for s in sources],
                        "color": "rgba(244, 182, 200, 0.35)",
                    },
                    textfont={"family": CHART_FONT, "color": CHART_TEXT, "size": 13},
                )
            ]
        )
        style_fig(fig)
        fig.update_layout(height=420, font={"family": CHART_FONT, "color": CHART_TEXT, "size": 13})
        plotly_chart(fig, height="420px")


def _income_sunburst(income: dict) -> None:
    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Income mix (category → source)</h2>',
            sanitize=False,
        )
        sources = [s for s in income.get("sources", []) if s["ytd_amount"] > 0]
        if not sources:
            ui.label("No income sources to chart yet.")
            return

        labels = ["Income"]
        parents = [""]
        values = [sum(s["ytd_amount"] for s in sources)]
        colours = ["#243041"]

        categories = sorted({s["category_label"] for s in sources})
        for i, cat in enumerate(categories):
            cat_total = sum(
                s["ytd_amount"] for s in sources if s["category_label"] == cat
            )
            labels.append(cat)
            parents.append("Income")
            values.append(cat_total)
            colours.append(CHART_PALETTE[i % len(CHART_PALETTE)])

        for i, src in enumerate(sources):
            labels.append(src["name"])
            parents.append(src["category_label"])
            values.append(src["ytd_amount"])
            colours.append(CHART_PALETTE[(i + 3) % len(CHART_PALETTE)])

        fig = go.Figure(
            go.Sunburst(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                marker={"colors": colours, "line": {"width": 2, "color": "#0f1419"}},
                hovertemplate="%{label}<br>£%{value:,.2f}<extra></extra>",
                textfont={"family": CHART_FONT, "color": CHART_TEXT, "size": 13},
                insidetextfont={"family": CHART_FONT, "color": CHART_TEXT, "size": 13},
            )
        )
        style_fig(fig)
        fig.update_layout(
            margin={"l": 8, "r": 8, "t": 8, "b": 8},
            height=440,
            uniformtext={"minsize": 11, "mode": "hide"},
        )
        plotly_chart(fig, height="440px")
