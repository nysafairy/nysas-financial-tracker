"""Landing overview with hero metrics and charts."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from nicegui import ui

from finance_app.pages.layout import render_shell, require_profile
from finance_app.services import allowances as allowance_service
from finance_app.services import metrics as metrics_service
from finance_app.ui.charts import ACCENT_PINK, allocation_treemap, style_fig
from finance_app.ui.components import format_gbp, page_header, plotly_chart


def register() -> None:
    @ui.page("/")
    def overview_page() -> None:
        if not require_profile():
            return

        data = metrics_service.overview_metrics()
        assets = float(data["assets"] or 0)
        debts = float(data["debts"] or 0)
        total = assets + debts
        asset_pct = (assets / total * 100) if total else 100.0
        debt_pct = (debts / total * 100) if total else 0.0
        change = data["net_worth_change"]
        progress = data["tax_year_progress"]
        income = data["income_by_source"]

        with render_shell("/"):
            page_header(
                "Overview",
                f"Tax year {data['tax_year_start']} to {data['tax_year_end']}.",
            )
            if data.get("draft_active"):
                ui.html(
                    f'<div class="draft-banner">Showing draft overlay for snapshot '
                    f'{data.get("draft_as_of")}. Save or discard from the bar above.</div>',
                    sanitize=False,
                )

            with ui.element("div").classes("hero-metrics"):
                with ui.element("div").classes("hero-networth"):
                    ui.html(
                        '<div class="hero-kicker">Net worth</div>', sanitize=False
                    )
                    ui.html(
                        f'<div class="hero-amount">{format_gbp(data["net_worth"])}</div>',
                        sanitize=False,
                    )
                    ui.html(
                        f'<div class="split-bar">'
                        f'<div class="assets" style="width:{asset_pct:.2f}%"></div>'
                        f'<div class="debts" style="width:{debt_pct:.2f}%"></div>'
                        f"</div>",
                        sanitize=False,
                    )
                    ui.html(
                        f'<div class="split-legend">'
                        f"<span>Assets <strong>{format_gbp(assets)}</strong></span>"
                        f"<span>Debts <strong>{format_gbp(debts)}</strong></span>"
                        f"</div>",
                        sanitize=False,
                    )

                    with ui.element("div").classes("hero-foot"):
                        series = data["net_worth_series"]
                        if len(series) >= 2:
                            with ui.element("div").classes("spark-wrap"):
                                spark = go.Figure(
                                    data=[
                                        go.Scatter(
                                            x=[p["date"] for p in series],
                                            y=[p["value"] for p in series],
                                            mode="lines",
                                            line={
                                                "color": ACCENT_PINK,
                                                "width": 2,
                                                "shape": "spline",
                                            },
                                            fill="tozeroy",
                                            fillcolor="rgba(244, 182, 200, 0.18)",
                                            hoverinfo="skip",
                                        )
                                    ]
                                )
                                spark.update_layout(
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)",
                                    margin={"l": 0, "r": 0, "t": 4, "b": 0},
                                    height=72,
                                    xaxis={"visible": False},
                                    yaxis={"visible": False},
                                    showlegend=False,
                                )
                                plotly_chart(spark, height="72px")

                        delta = float(change.get("delta") or 0)
                        cls = "up" if delta >= 0 else "down"
                        sign = "+" if delta >= 0 else ""
                        pct = change.get("pct")
                        pct_txt = f" ({sign}{pct:.1f}%)" if pct is not None else ""
                        ui.html(
                            f'<div class="hero-delta">'
                            f'<span class="{cls}">{sign}{format_gbp(delta)}</span>'
                            f'<span class="muted">since last snapshot{pct_txt}</span>'
                            f"</div>",
                            sanitize=False,
                        )
                        ui.html(
                            f'<div class="ty-progress">'
                            f'<div class="label">Tax year progress · '
                            f'{progress["elapsed_days"]} / {progress["total_days"]} days</div>'
                            f'<div class="ty-track"><div class="ty-fill" '
                            f'style="width:{progress["pct"]:.1f}%"></div></div>'
                            f"</div>",
                            sanitize=False,
                        )

                with ui.element("div").classes("side-stack"):
                    with ui.element("div").classes("flow-panel"):
                        ui.html("<h3>Income by source (YTD)</h3>", sanitize=False)
                        sources = income.get("sources") or []
                        if sources:
                            for src in sources[:5]:
                                ui.html(
                                    f'<div class="flow-row">'
                                    f'<span class="label">{src["name"]}'
                                    f' · {src["category_label"]}</span>'
                                    f'<span class="value pink">'
                                    f'{format_gbp(src["ytd_amount"])}</span></div>',
                                    sanitize=False,
                                )
                            if len(sources) > 5:
                                ui.html(
                                    f'<div class="flow-row"><span class="label">…and '
                                    f'{len(sources) - 5} more</span>'
                                    f'<span class="value blue">'
                                    f'{format_gbp(income["total_ytd"])} total</span></div>',
                                    sanitize=False,
                                )
                            else:
                                ui.html(
                                    f'<div class="flow-row"><span class="label">Total</span>'
                                    f'<span class="value blue">'
                                    f'{format_gbp(income["total_ytd"])}</span></div>',
                                    sanitize=False,
                                )
                        else:
                            ui.label(
                                "Add income streams under Edit data → Income "
                                "(e.g. yearly salary, freelance, gigs)."
                            ).style("color: var(--text-muted); font-size: 0.9rem;")

                    with ui.element("div").classes("flow-panel"):
                        ui.html("<h3>Monthly rhythm</h3>", sanitize=False)
                        ui.html(
                            f'<div class="flow-row"><span class="label">Subscriptions out</span>'
                            f'<span class="value pink">'
                            f'{format_gbp(data["subscriptions_monthly"])}</span></div>',
                            sanitize=False,
                        )
                        ui.html(
                            f'<div class="flow-row"><span class="label">Standing orders</span>'
                            f'<span class="value blue">'
                            f'{format_gbp(data["standing_orders_monthly"])}</span></div>',
                            sanitize=False,
                        )
                        ui.html(
                            '<div style="color:var(--text-muted);font-size:0.8rem;margin-top:0.45rem">'
                            "Standing orders only move money between your accounts.</div>",
                            sanitize=False,
                        )

            allowance = allowance_service.allowance_usage()
            tracked = [
                i
                for i in allowance["items"]
                if i.get("tracking") != "reference_only"
                and i["key"] in {"adult_isa", "lisa", "pension_annual"}
            ]
            if tracked:
                with ui.element("div").classes("panel").style("margin-bottom: 1rem;"):
                    with ui.row().classes(
                        "w-full items-center justify-between gap-2 flex-wrap"
                    ):
                        ui.html(
                            f'<h2 class="panel-title" style="margin:0">'
                            f'Allowances · {allowance["tax_year"]}</h2>',
                            sanitize=False,
                        )

                        def open_prior_dialog() -> None:
                            current = {
                                i["key"]: float(i.get("prior_used") or 0)
                                for i in tracked
                            }
                            with ui.dialog() as dialog, ui.card().classes(
                                "w-full"
                            ).style("max-width: 28rem;"):
                                ui.label(
                                    f"Prior usage this tax year ({allowance['tax_year']})"
                                ).classes("text-lg font-medium")
                                ui.label(
                                    "If you started this profile mid-year, enter how much "
                                    "allowance you had already used elsewhere. This is added "
                                    "on top of contribution transactions logged here. "
                                    "ISA should include any LISA subscriptions already used."
                                ).style(
                                    "color: var(--text-muted); font-size: 0.85rem; "
                                    "margin-bottom: 0.85rem;"
                                )
                                fields: dict[str, Any] = {}
                                labels = {
                                    "adult_isa": "ISA already used (£)",
                                    "lisa": "LISA already used (£)",
                                    "pension_annual": "Pension annual allowance already used (£)",
                                }
                                for key in ("adult_isa", "lisa", "pension_annual"):
                                    fields[key] = ui.number(
                                        labels[key],
                                        value=current.get(key) or None,
                                        format="%.2f",
                                        min=0,
                                    ).classes("w-full")

                                def save_priors() -> None:
                                    payload = {}
                                    for key, widget in fields.items():
                                        raw = widget.value
                                        payload[key] = (
                                            0.0
                                            if raw in (None, "")
                                            else float(raw)
                                        )
                                    try:
                                        allowance_service.set_baselines(payload)
                                    except ValueError as exc:
                                        ui.notify(str(exc), type="warning")
                                        return
                                    dialog.close()
                                    ui.notify("Prior allowance usage saved", type="positive")
                                    ui.navigate.to("/")

                                with ui.row().classes("w-full justify-end gap-2"):
                                    ui.button("Cancel", on_click=dialog.close).props(
                                        "flat"
                                    )
                                    ui.button("Save", on_click=save_priors).props(
                                        "color=primary unelevated"
                                    )
                            dialog.open()

                        ui.button(
                            "Set prior usage",
                            on_click=open_prior_dialog,
                        ).props("flat dense")

                    with ui.element("div").classes("allowance-grid"):
                        for item in tracked:
                            prior = float(item.get("prior_used") or 0)
                            prior_note = (
                                f" · includes {format_gbp(prior)} prior"
                                if prior > 0
                                else ""
                            )
                            ui.html(
                                f'<div class="allowance-card">'
                                f'<div class="title">{item["label"]}</div>'
                                f'<div class="used">{format_gbp(item["used"])} / '
                                f'{format_gbp(item["limit"])}</div>'
                                f'<div class="ty-track"><div class="ty-fill" '
                                f'style="width:{item["pct"]:.1f}%"></div></div>'
                                f'<div class="meta">{format_gbp(item["remaining"])} remaining'
                                f"{prior_note}"
                                f'{(" · est. bonus " + format_gbp(item["bonus_earned_estimate"])) if item.get("bonus_earned_estimate") is not None else ""}'
                                f"</div></div>",
                                sanitize=False,
                            )

            with ui.element("div").classes("responsive-grid"):
                with ui.element("div").classes("panel"):
                    ui.html(
                        '<h2 class="panel-title">Net worth over time</h2>',
                        sanitize=False,
                    )
                    series = data["net_worth_series"]
                    if series:
                        fig = go.Figure(
                            data=[
                                go.Scatter(
                                    x=[p["date"] for p in series],
                                    y=[p["value"] for p in series],
                                    fill="tozeroy",
                                    line={"color": ACCENT_PINK, "width": 2.5},
                                    fillcolor="rgba(244, 182, 200, 0.22)",
                                    name="Net worth",
                                )
                            ]
                        )
                        style_fig(fig)
                        plotly_chart(fig)
                    else:
                        ui.label("Record balance snapshots to see this chart.")

                with ui.element("div").classes("panel"):
                    ui.html(
                        '<h2 class="panel-title">Where your money sits</h2>',
                        sanitize=False,
                    )
                    allocation = data["allocation"]
                    if allocation:
                        plotly_chart(allocation_treemap(allocation))
                    else:
                        ui.label("Add accounts and snapshots to see allocation.")
