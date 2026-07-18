"""Forecasting: portfolio projection with session-only what-ifs."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from nicegui import ui

from finance_app.db.models import (
    FORECAST_DEFAULT_ASSUMED_GROWTH_PCT,
    PREMIUM_BONDS_ASSUMED_RATE_PCT,
)
from finance_app.pages.layout import render_shell, require_profile
from finance_app.services import draft_session
from finance_app.services import forecasting as forecast_service
from finance_app.services.forecasting import ForecastAssumptions, WhatIfs
from finance_app.ui.charts import ACCENT_BLUE, ACCENT_PINK, style_fig
from finance_app.ui.components import format_gbp, metric_card, page_header, plotly_chart


def register() -> None:
    @ui.page("/forecasting")
    def forecasting_page() -> None:
        if not require_profile():
            return

        with render_shell("/forecasting"):
            page_header(
                "Forecasting",
                "Project net worth from balances, stored rates, and income — "
                "with temporary what-ifs for this page only.",
            )
            draft_meta = draft_session.get_draft_meta()
            if draft_meta is not None:
                as_of = draft_meta["as_of_date"]
                as_of_text = (
                    as_of.isoformat() if hasattr(as_of, "isoformat") else str(as_of)
                )
                ui.html(
                    f'<div class="draft-banner">Using draft balances for snapshot '
                    f"{as_of_text}.</div>",
                    sanitize=False,
                )

            accounts = forecast_service.forecast_accounts()
            state: dict[str, Any] = {
                "mode": "overall",
                "overall_pct": FORECAST_DEFAULT_ASSUMED_GROWTH_PCT,
                "years": 10,
                "per_account": {
                    a["key"]: forecast_service.suggested_account_rate_pct(a)
                    for a in accounts
                },
                "extra_save": 0.0,
                "extra_spend": 0.0,
                "lump_sum": 0.0,
                "override_growth": None,
                "use_override": False,
                "apply_tax": True,
            }

            results = ui.element("div").classes("w-full")

            def rebuild() -> None:
                results.clear()
                with results:
                    _render_results(state, accounts)

            with ui.element("div").classes("panel"):
                ui.html(
                    '<h2 class="panel-title">Growth assumptions</h2>',
                    sanitize=False,
                )
                ui.label(
                    f"Accounts without a stored interest rate need an assumed annual "
                    f"return. Default is {FORECAST_DEFAULT_ASSUMED_GROWTH_PCT:.0f}% — "
                    "change it to match your expectation. This is a planning "
                    "assumption, not a guarantee."
                ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
                ui.label(
                    f"Premium Bonds default to an assumed average prize rate of "
                    f"{PREMIUM_BONDS_ASSUMED_RATE_PCT}% when no rate is stored "
                    "(prizes are variable)."
                ).style("color: var(--text-muted); margin-bottom: 1rem;")

                mode = ui.toggle(
                    {"overall": "Overall estimate", "per_account": "Per account"},
                    value="overall",
                ).props("unelevated")

                overall_box = ui.element("div").classes("form-stack")
                with overall_box:
                    overall_input = ui.number(
                        f"Assumed annual growth (%) — default "
                        f"{FORECAST_DEFAULT_ASSUMED_GROWTH_PCT:.0f}%",
                        value=FORECAST_DEFAULT_ASSUMED_GROWTH_PCT,
                        format="%.2f",
                        min=0,
                        max=30,
                    ).classes("w-full")

                per_box = ui.element("div").classes("form-stack")
                per_box.set_visibility(False)
                per_inputs: dict[str, Any] = {}
                with per_box:
                    if not accounts:
                        ui.label("No account balances to forecast yet.")
                    else:
                        ui.label(
                            "Set an assumed annual % for each account. "
                            "Pre-filled from stored rates where available."
                        ).style("color: var(--text-muted);")
                        for account in accounts:
                            label = (
                                f"{account['name']} ({account['type_label']})"
                                + (" — liability" if account["is_liability"] else "")
                            )
                            per_inputs[account["key"]] = ui.number(
                                label,
                                value=state["per_account"][account["key"]],
                                format="%.2f",
                                min=0,
                                max=30,
                            ).classes("w-full")

                years_input = ui.number(
                    "Horizon (years)",
                    value=10,
                    min=1,
                    max=40,
                    format="%.0f",
                ).classes("w-full")

                apply_tax = ui.checkbox(
                    "Estimate England income tax on salary and taxable interest",
                    value=True,
                )
                ui.label(
                    "When on, monthly surplus is reduced by estimated income tax. "
                    "ISA / LISA / IFISA / Premium Bonds interest is treated as tax-free. "
                    "National Insurance is not included. Set a tax band on salary "
                    "sources under Edit data for your records; the estimate still "
                    "derives the band from total taxable income."
                ).style("color: var(--text-muted); margin-bottom: 0.75rem;")

                def on_mode_change() -> None:
                    state["mode"] = mode.value
                    overall_box.set_visibility(mode.value == "overall")
                    per_box.set_visibility(mode.value == "per_account")
                    rebuild()

                mode.on_value_change(lambda _: on_mode_change())

                def sync_and_rebuild() -> None:
                    state["mode"] = mode.value
                    state["overall_pct"] = float(overall_input.value or 0)
                    state["years"] = int(years_input.value or 10)
                    state["apply_tax"] = bool(apply_tax.value)
                    for key, inp in per_inputs.items():
                        state["per_account"][key] = float(inp.value or 0)
                    rebuild()

                overall_input.on_value_change(lambda _: sync_and_rebuild())
                years_input.on_value_change(lambda _: sync_and_rebuild())
                apply_tax.on_value_change(lambda _: sync_and_rebuild())
                for inp in per_inputs.values():
                    inp.on_value_change(lambda _: sync_and_rebuild())

            with ui.element("div").classes("panel"):
                ui.html(
                    '<h2 class="panel-title">What-ifs (this page only)</h2>',
                    sanitize=False,
                )
                ui.label(
                    "Temporary adjustments for exploring scenarios. They are not "
                    "saved to your profile and reset when you leave this page."
                ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
                with ui.element("div").classes("form-stack"):
                    extra_save = ui.number(
                        "Extra monthly saving (£)",
                        value=0,
                        format="%.2f",
                    ).classes("w-full")
                    extra_spend = ui.number(
                        "Extra monthly spend (£)",
                        value=0,
                        format="%.2f",
                    ).classes("w-full")
                    lump = ui.number(
                        "One-off lump sum at start (£)",
                        value=0,
                        format="%.2f",
                    ).classes("w-full")
                    use_override = ui.checkbox(
                        "Override overall assumed growth for this what-if"
                    )
                    override_input = ui.number(
                        "What-if overall growth (%)",
                        value=FORECAST_DEFAULT_ASSUMED_GROWTH_PCT,
                        format="%.2f",
                        min=0,
                        max=30,
                    ).classes("w-full")
                    override_input.set_visibility(False)

                    def on_override_toggle() -> None:
                        override_input.set_visibility(bool(use_override.value))
                        sync_whatifs()

                    def sync_whatifs() -> None:
                        state["extra_save"] = float(extra_save.value or 0)
                        state["extra_spend"] = float(extra_spend.value or 0)
                        state["lump_sum"] = float(lump.value or 0)
                        state["use_override"] = bool(use_override.value)
                        state["override_growth"] = (
                            float(override_input.value or 0)
                            if use_override.value
                            else None
                        )
                        rebuild()

                    use_override.on_value_change(lambda _: on_override_toggle())
                    for inp in (extra_save, extra_spend, lump, override_input):
                        inp.on_value_change(lambda _: sync_whatifs())

                    def clear_whatifs() -> None:
                        extra_save.value = 0
                        extra_spend.value = 0
                        lump.value = 0
                        use_override.value = False
                        override_input.value = FORECAST_DEFAULT_ASSUMED_GROWTH_PCT
                        override_input.set_visibility(False)
                        state["extra_save"] = 0.0
                        state["extra_spend"] = 0.0
                        state["lump_sum"] = 0.0
                        state["use_override"] = False
                        state["override_growth"] = None
                        rebuild()

                    ui.button("Clear what-ifs", on_click=clear_whatifs).props(
                        "outline"
                    )

            rebuild()


def _render_results(state: dict[str, Any], accounts: list[dict[str, Any]]) -> None:
    if not accounts:
        with ui.element("div").classes("panel"):
            ui.label(
                "Add accounts and save a balance snapshot first, then return here."
            )
        return

    assumptions = ForecastAssumptions(
        mode=state["mode"],
        overall_growth_pct=float(state["overall_pct"]),
        per_account_pct=dict(state["per_account"]),
    )
    what_ifs = WhatIfs(
        extra_monthly_saving=float(state["extra_save"]),
        extra_monthly_spend=float(state["extra_spend"]),
        lump_sum=float(state["lump_sum"]),
        overall_growth_override_pct=state["override_growth"],
    )
    data = forecast_service.project_series(
        years=int(state["years"]),
        assumptions=assumptions,
        what_ifs=what_ifs,
        apply_tax=bool(state.get("apply_tax")),
    )
    cashflow = data["cashflow"]

    with ui.element("div").classes("metric-grid"):
        metric_card("Starting net worth", format_gbp(data["start_net_worth"]))
        metric_card("Projected (baseline)", format_gbp(data["end_net_worth"]))
        metric_card("Growth (baseline)", format_gbp(data["total_growth"]))
        metric_card("Monthly surplus", format_gbp(cashflow["net_monthly"]))
        if data["has_what_ifs"] and data["end_adjusted"] is not None:
            metric_card("Projected (what-if)", format_gbp(data["end_adjusted"]))
        tax = cashflow.get("tax")
        if tax:
            metric_card("Est. monthly tax", format_gbp(tax["monthly_tax"]))
            metric_card(
                "Est. tax band",
                str(tax["marginal_band"]).replace("_", " ").title(),
            )

    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Cashflow used in the forecast</h2>',
            sanitize=False,
        )
        tax = cashflow.get("tax")
        tax_note = ""
        if tax:
            bands = ", ".join(tax.get("recorded_tax_bands") or []) or "none recorded"
            tax_note = (
                f" Estimated tax {format_gbp(tax['annual_tax'])}/yr "
                f"(band: {tax['marginal_band']}; recorded on sources: {bands}). "
                f"Assumed taxable interest {format_gbp(tax['taxable_interest_assumed'])}/yr; "
                f"tax-free wrappers {format_gbp(tax['tax_free_interest_assumed'])}/yr."
            )
        ui.label(
            f"Fixed income {format_gbp(cashflow['fixed_income'])}/mo · "
            f"Recurring income {format_gbp(cashflow['recurring_income'])}/mo · "
            f"Subscriptions −{format_gbp(cashflow['subscriptions'])}/mo."
            f"{tax_note} "
            "Variable/gig income is not included unless you add it as a what-if."
        ).style("color: var(--text-muted);")

    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Projected net worth</h2>',
            sanitize=False,
        )
        fig = go.Figure()
        baseline = data["baseline"]
        fig.add_trace(
            go.Scatter(
                x=[p["month"] / 12 for p in baseline],
                y=[p["value"] for p in baseline],
                mode="lines",
                name="Baseline",
                line={"color": ACCENT_PINK, "width": 2.5},
            )
        )
        if data["adjusted"]:
            fig.add_trace(
                go.Scatter(
                    x=[p["month"] / 12 for p in data["adjusted"]],
                    y=[p["value"] for p in data["adjusted"]],
                    mode="lines",
                    name="With what-ifs",
                    line={"color": ACCENT_BLUE, "width": 2.5, "dash": "dash"},
                )
            )
        style_fig(fig, show_legend=True)
        fig.update_layout(
            xaxis_title="Years",
            yaxis_title="Net worth",
            margin={"l": 56, "r": 20, "t": 24, "b": 56},
        )
        plotly_chart(fig, height="420px")

    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Rates applied</h2>',
            sanitize=False,
        )
        columns = [
            {"name": "name", "label": "Account", "field": "name", "align": "left"},
            {"name": "type", "label": "Type", "field": "type", "align": "left"},
            {"name": "balance", "label": "Balance", "field": "balance", "align": "right"},
            {"name": "rate", "label": "Annual %", "field": "rate", "align": "right"},
            {"name": "source", "label": "Source", "field": "source", "align": "left"},
        ]
        rows = []
        for row in data["accounts"]:
            stored = row.get("stored_rate_pct")
            applied = row["annual_rate_pct"]
            atype = row.get("account_type")
            if assumptions.mode == "per_account":
                source = "Per-account assumption"
            elif stored is not None:
                source = "Stored rate"
            elif atype == "premium_bonds":
                source = f"Premium Bonds default ({PREMIUM_BONDS_ASSUMED_RATE_PCT}%)"
            elif applied == 0:
                source = "No growth (current/other or liability)"
            else:
                source = f"Overall assumption ({assumptions.overall_growth_pct:g}%)"
            rows.append(
                {
                    "name": row["name"],
                    "type": row["type_label"],
                    "balance": format_gbp(
                        -abs(row["balance"]) if row["is_liability"] else row["balance"]
                    ),
                    "rate": f"{applied:.2f}",
                    "source": source,
                }
            )
        ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")

    ui.html(
        '<p class="guide-lead" style="margin-top:1rem">'
        "Planning aid only. Markets and Premium Bonds prizes vary; inflation is not "
        "modelled. Tax estimates use England 2026/27 income tax only (no NI). "
        "For a detailed Self Assessment-style breakdown, use Tax &amp; tools. "
        "For actual interest received, use the Income report."
        "</p>",
        sanitize=False,
    )
