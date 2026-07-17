"""Tax estimator and interest tools."""

from __future__ import annotations

from nicegui import ui

from finance_app.pages.layout import render_shell, require_profile
from finance_app.services import calculators as calc_service
from finance_app.services import income as income_service
from finance_app.ui.components import format_gbp, page_header, result_box


def register() -> None:
    @ui.page("/tax")
    def tax_tools_page() -> None:
        if not require_profile():
            return
        _render_tools()

    # Keep old path working without the previous layout glitch.
    @ui.page("/calculators")
    def calculators_redirect() -> None:
        ui.navigate.to("/tax")


def _render_tools() -> None:
    with render_shell("/tax"):
        page_header(
            "Tax & tools",
            "England income tax estimate for 2026/27, plus a simple interest projection.",
        )
        with ui.element("div").classes("responsive-grid"):
            _tax_panel()
            _interest_panel()


def _interest_panel() -> None:
    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Interest projection</h2>', sanitize=False)
        with ui.element("div").classes("form-stack"):
            principal = ui.number("Principal (£)", value=10000, format="%.2f").classes(
                "w-full"
            )
            rate = ui.number("Annual rate (%)", value=4.5, format="%.2f").classes(
                "w-full"
            )
            years = ui.number("Years", value=5, format="%.1f").classes("w-full")
            compound = ui.checkbox("Compound annually", value=True)
            result = result_box("Enter values and project.")

            def run() -> None:
                data = calc_service.project_interest(
                    float(principal.value or 0),
                    float(rate.value or 0),
                    float(years.value or 0),
                    compound=bool(compound.value),
                )
                result.set_text(
                    f"Future value: {format_gbp(data['future_value'])}\n"
                    f"Interest earned: {format_gbp(data['interest_earned'])}"
                )

            with ui.element("div").classes("form-actions"):
                ui.button("Project", on_click=run).props("color=primary")


def _tax_panel() -> None:
    from finance_app.services.metrics import tax_year_progress

    salary_pref = income_service.salary_annual_for_tax()
    by_source = income_service.income_by_source()
    freelance_ytd = sum(
        s["ytd_amount"]
        for s in by_source["sources"]
        if s["category"] in {"freelance", "gig"}
    )
    # Annualise freelance/gig YTD for the estimator using tax-year progress.
    pct = max(tax_year_progress()["pct"] / 100.0, 0.05)
    freelance_annual_est = freelance_ytd / pct if freelance_ytd else 0.0

    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">England income tax (2026/27)</h2>',
            sanitize=False,
        )
        if salary_pref:
            ui.label(
                f"Prefilled employment from your salary income sources: "
                f"{format_gbp(salary_pref)} / year. Edit under Edit data → Income."
            ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
        with ui.element("div").classes("form-stack"):
            employment = ui.number(
                "Employment / working income (£)",
                value=salary_pref or 40000,
                format="%.2f",
            ).classes("w-full")
            pension = ui.number("Pension income (£)", value=0, format="%.2f").classes(
                "w-full"
            )
            property_income = ui.number(
                "Property income (£)", value=0, format="%.2f"
            ).classes("w-full")
            trading = ui.number(
                "Self-employment / trading (£)",
                value=round(freelance_annual_est, 2) if freelance_annual_est else 0,
                format="%.2f",
            ).classes("w-full")
            savings = ui.number(
                "Savings interest (£)", value=0, format="%.2f"
            ).classes("w-full")
            dividends = ui.number("Dividends (£)", value=0, format="%.2f").classes(
                "w-full"
            )
            trust_other = ui.number(
                "Trust / fund income — non-dividend (£)", value=0, format="%.2f"
            ).classes("w-full")
            trust_div = ui.number(
                "Trust / fund income — dividends (£)", value=0, format="%.2f"
            ).classes("w-full")
            use_property_allowance = ui.checkbox(
                "Apply £1,000 property allowance", value=True
            )
            use_trading_allowance = ui.checkbox(
                "Apply £1,000 trading allowance", value=False
            )
            result = result_box("Enter income sources and estimate.")

            def run() -> None:
                data = calc_service.estimate_income_tax_england(
                    employment=float(employment.value or 0),
                    pension=float(pension.value or 0),
                    property=float(property_income.value or 0),
                    trading_income=float(trading.value or 0),
                    savings_interest=float(savings.value or 0),
                    dividends=float(dividends.value or 0),
                    trust_non_dividend=float(trust_other.value or 0),
                    trust_dividend=float(trust_div.value or 0),
                    apply_property_allowance=bool(use_property_allowance.value),
                    apply_trading_allowance=bool(use_trading_allowance.value),
                )
                allowances = data["allowances_applied"]
                result.set_text(
                    f"Tax year: {data['tax_year']} ({data['jurisdiction']})\n"
                    f"Total income: {format_gbp(data['total_income'])}\n"
                    f"Personal allowance: {format_gbp(data['personal_allowance'])}\n"
                    f"Marginal band: {data['marginal_band']}\n"
                    f"Tax on earnings/pension/property/etc: {format_gbp(data['tax']['non_savings'])}\n"
                    f"Tax on savings: {format_gbp(data['tax']['savings'])}\n"
                    f"Tax on dividends: {format_gbp(data['tax']['dividends'])}\n"
                    f"Total estimated tax: {format_gbp(data['tax']['total'])}\n"
                    f"Effective rate: {data['effective_rate'] * 100:.1f}%\n"
                    f"PSA used: {format_gbp(allowances['personal_savings_allowance'])} | "
                    f"Dividend allowance used: {format_gbp(allowances['dividend_allowance'])}"
                )

            with ui.element("div").classes("form-actions"):
                ui.button("Estimate tax", on_click=run).props("color=primary")
