"""Income report: actual income, interest, and dividends for a date range."""

from __future__ import annotations

from datetime import date

from nicegui import ui

from finance_app.pages.layout import render_shell, require_profile
from finance_app.services import income as income_service
from finance_app.services.metrics import uk_tax_year_start
from finance_app.ui.components import format_gbp, metric_card, page_header


def register() -> None:
    @ui.page("/income-report")
    def income_report_page() -> None:
        if not require_profile():
            return

        today = date.today()
        default_start = uk_tax_year_start(today)

        with render_shell("/income-report"):
            page_header(
                "Income report",
                "Actual income sources, receipts, and ledger interest for a period — "
                "not forecasted returns.",
            )

            results = ui.element("div").classes("w-full")

            with ui.element("div").classes("panel"):
                ui.html('<h2 class="panel-title">Period</h2>', sanitize=False)
                ui.label(
                    "Default is UK tax year to date (6 April → today). "
                    "Change the dates and refresh to report on another window."
                ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
                with ui.element("div").classes("form-stack"):
                    start_input = ui.date_input(
                        "From", value=default_start
                    ).classes("w-full")
                    end_input = ui.date_input("To", value=today).classes("w-full")

                    def parse_date(value) -> date:
                        if isinstance(value, date):
                            return value
                        if hasattr(value, "date"):
                            return value.date()
                        return date.fromisoformat(str(value)[:10])

                    def ytd() -> None:
                        start_input.value = uk_tax_year_start(date.today())
                        end_input.value = date.today()
                        rebuild()

                    def rebuild() -> None:
                        results.clear()
                        try:
                            start = parse_date(start_input.value)
                            end = parse_date(end_input.value)
                        except Exception:
                            with results:
                                ui.label("Enter valid dates (YYYY-MM-DD).")
                            return
                        report = income_service.income_report(start, end)
                        with results:
                            _render_report(report)

                    with ui.element("div").classes("form-actions"):
                        ui.button("Tax year to date", on_click=ytd).props("outline")
                        ui.button("Refresh report", on_click=rebuild).props(
                            "color=primary"
                        )

            rebuild()


def _render_report(report: dict) -> None:
    totals = report["totals"]
    with ui.element("div").classes("metric-grid"):
        metric_card("Gross in period", format_gbp(totals["gross"]))
        metric_card("From income sources", format_gbp(totals["streams"]))
        metric_card("Taxable interest", format_gbp(totals["taxable_interest"]))
        metric_card("Tax-free interest", format_gbp(totals["tax_free_interest"]))
        metric_card("Dividends", format_gbp(totals["dividends"]))
        metric_card(
            "Est. tax in period",
            format_gbp(totals["estimated_tax_in_period"]),
        )
        metric_card(
            "Est. net in period",
            format_gbp(totals["estimated_net_in_period"]),
        )

    band = report["tax_estimate_annualised"].get("marginal_band", "—")
    recorded = ", ".join(report.get("recorded_tax_bands") or []) or "none recorded"
    ui.label(
        f"Period {report['start']} → {report['end']}. "
        f"Estimated marginal band (annualised): {band}. "
        f"Recorded on sources: {recorded}."
    ).style("color: var(--text-muted); margin-bottom: 1rem;")

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Income sources</h2>', sanitize=False)
        sources = report["sources"]
        if not sources:
            ui.label("No active income sources.")
        else:
            ui.table(
                columns=[
                    {"name": "name", "label": "Name", "field": "name"},
                    {"name": "category", "label": "Category", "field": "category"},
                    {
                        "name": "tax_treatment",
                        "label": "Tax treatment",
                        "field": "tax_treatment",
                    },
                    {"name": "tax_band", "label": "Tax band", "field": "tax_band"},
                    {"name": "amount", "label": "Amount in period", "field": "amount"},
                    {"name": "basis", "label": "Basis", "field": "basis"},
                ],
                rows=[
                    {
                        **row,
                        "amount": format_gbp(row["amount"]),
                        "basis": (
                            "Receipts"
                            if row["basis"] == "receipts"
                            else "Pro-rated expected"
                        ),
                    }
                    for row in sources
                ],
                row_key="name",
                pagination={"rowsPerPage": 20},
            ).classes("w-full data-table")

    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Interest and dividends (ledger)</h2>',
            sanitize=False,
        )
        ui.label(
            "Actual logged transactions only. ISA / LISA / IFISA / Premium Bonds "
            "are marked tax-free."
        ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
        lines = report["interest_and_dividends"]
        if not lines:
            ui.label("No interest or dividend transactions in this period.")
        else:
            ui.table(
                columns=[
                    {"name": "date", "label": "Date", "field": "date"},
                    {"name": "kind", "label": "Kind", "field": "kind"},
                    {"name": "account", "label": "Account", "field": "account"},
                    {"name": "type", "label": "Account type", "field": "type"},
                    {"name": "amount", "label": "Amount", "field": "amount"},
                    {"name": "taxable", "label": "Taxable", "field": "taxable"},
                    {
                        "name": "description",
                        "label": "Description",
                        "field": "description",
                    },
                ],
                rows=[
                    {
                        **row,
                        "amount": format_gbp(row["amount"]),
                        "taxable": "Yes" if row["taxable"] else "No (tax-free)",
                        "_key": f"{row['date']}-{row['kind']}-{row['account']}-{i}",
                    }
                    for i, row in enumerate(lines)
                ],
                row_key="_key",
                pagination={"rowsPerPage": 25},
            ).classes("w-full data-table")

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Receipts logged</h2>', sanitize=False)
        receipts = report["receipts"]
        if not receipts:
            ui.label("No receipts in this period.")
        else:
            ui.table(
                columns=[
                    {"name": "date", "label": "Date", "field": "date"},
                    {"name": "source", "label": "Source", "field": "source"},
                    {"name": "amount", "label": "Amount", "field": "amount"},
                    {
                        "name": "description",
                        "label": "Description",
                        "field": "description",
                    },
                ],
                rows=[
                    {**row, "amount": format_gbp(row["amount"])} for row in receipts
                ],
                row_key="date",
                pagination={"rowsPerPage": 25},
            ).classes("w-full data-table")

    for note in report.get("notes") or []:
        ui.label(note).style("color: var(--text-muted); display: block; margin-top: 0.35rem;")
