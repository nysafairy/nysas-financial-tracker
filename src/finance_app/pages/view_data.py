"""Read-only view of everything currently in the profile database."""

from __future__ import annotations

from nicegui import ui

from finance_app.pages.layout import render_shell, require_profile
from finance_app.services import export as export_service
from finance_app.services import inventory as inventory_service
from finance_app.ui.components import format_gbp, page_header


def register() -> None:
    @ui.page("/view")
    def view_data_page() -> None:
        if not require_profile():
            return

        data = inventory_service.database_inventory()
        counts = data["counts"]

        with render_shell("/view"):
            page_header(
                "View data",
                "A clear read-only look at what is stored in this profile.",
            )

            with ui.element("div").classes("form-actions").style("margin-bottom: 1rem;"):
                def do_export() -> None:
                    filename, payload = export_service.build_export_zip()
                    ui.download(payload, filename)
                    ui.notify("Export ready", type="positive")

                ui.button("Export all data (CSV zip)", on_click=do_export).props(
                    "color=primary"
                )

            with ui.element("div").classes("inventory-stats"):
                for label, key in [
                    ("Income sources", "income_streams"),
                    ("Receipts", "income_receipts"),
                    ("Accounts", "accounts"),
                    ("Assets", "assets"),
                    ("Debts", "debts"),
                    ("Holdings", "holdings"),
                    ("Transactions", "transactions"),
                    ("Snapshots", "snapshots"),
                    ("Recurring", "recurring"),
                ]:
                    ui.html(
                        f'<span class="stat-chip">{label} <b>{counts[key]}</b></span>',
                        sanitize=False,
                    )

            with ui.tabs().classes("w-full") as tabs:
                tab_income = ui.tab("Income")
                tab_accounts = ui.tab("Accounts")
                tab_holdings = ui.tab("Holdings")
                tab_txns = ui.tab("Transactions")
                tab_snaps = ui.tab("Snapshots")
                tab_recurring = ui.tab("Recurring")

            with ui.tab_panels(tabs, value=tab_income).classes("w-full"):
                with ui.tab_panel(tab_income):
                    _income_tables(
                        data["income_streams"],
                        data["income_receipts"],
                        counts["income_receipts"],
                    )
                with ui.tab_panel(tab_accounts):
                    _accounts_table(data["accounts"])
                with ui.tab_panel(tab_holdings):
                    _holdings_table(data["holdings"])
                with ui.tab_panel(tab_txns):
                    _transactions_table(data["transactions"], counts["transactions"])
                with ui.tab_panel(tab_snaps):
                    _snapshots_grouped(
                        data["snapshot_groups"],
                        counts.get("snapshot_lines", 0),
                    )
                with ui.tab_panel(tab_recurring):
                    _recurring_table(data["recurring"])


def _income_tables(
    streams: list[dict], receipts: list[dict], receipt_total: int
) -> None:
    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Income sources</h2>', sanitize=False)
        if not streams:
            ui.label("No income sources yet.")
        else:
            ui.table(
                columns=[
                    {"name": "name", "label": "Name", "field": "name"},
                    {"name": "category", "label": "Category", "field": "category"},
                    {"name": "cadence", "label": "Cadence", "field": "cadence"},
                    {"name": "expected", "label": "Expected", "field": "expected"},
                    {"name": "active", "label": "Active", "field": "active"},
                    {"name": "notes", "label": "Notes", "field": "notes"},
                ],
                rows=[
                    {
                        **row,
                        "expected": format_gbp(row["expected_amount"])
                        if row["expected_amount"] is not None
                        else "—",
                        "active": "Yes" if row["active"] else "No",
                    }
                    for row in streams
                ],
                row_key="id",
                pagination={"rowsPerPage": 15},
            ).classes("w-full")

    with ui.element("div").classes("panel"):
        ui.html(
            f'<h2 class="panel-title">Receipts '
            f'<span style="color:var(--text-muted);font-size:0.9rem;font-weight:400">'
            f"(showing latest {len(receipts)} of {receipt_total})</span></h2>",
            sanitize=False,
        )
        if not receipts:
            ui.label("No receipts logged yet.")
            return
        ui.table(
            columns=[
                {"name": "date", "label": "Date", "field": "date"},
                {"name": "source", "label": "Source", "field": "source"},
                {"name": "amount", "label": "Amount", "field": "amount"},
                {"name": "description", "label": "Description", "field": "description"},
            ],
            rows=[
                {**row, "amount": format_gbp(row["amount"])} for row in receipts
            ],
            row_key="id",
            pagination={"rowsPerPage": 20},
        ).classes("w-full")


def _accounts_table(rows: list[dict]) -> None:
    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Accounts & debts</h2>', sanitize=False)
        if not rows:
            ui.label("No accounts yet.")
            return
        ui.table(
            columns=[
                {"name": "name", "label": "Name", "field": "name", "sortable": True},
                {"name": "type", "label": "Type", "field": "type"},
                {"name": "provider", "label": "Provider", "field": "provider"},
                {"name": "sort_code", "label": "Sort code", "field": "sort_code"},
                {"name": "account_number", "label": "Account no.", "field": "account_number"},
                {"name": "rate", "label": "Rate %", "field": "rate"},
                {"name": "interest_frequency", "label": "Interest", "field": "interest_frequency"},
                {"name": "access_type", "label": "Access", "field": "access_type"},
                {"name": "maturity_date", "label": "Maturity", "field": "maturity_date"},
                {"name": "latest_balance", "label": "Latest balance", "field": "latest_balance"},
                {"name": "notes", "label": "Notes", "field": "notes"},
            ],
            rows=[
                {
                    **row,
                    "rate": f"{row['interest_rate_pct']:.2f}"
                    if row["interest_rate_pct"] is not None
                    else "—",
                    "latest_balance": format_gbp(row["latest_balance"])
                    if row["latest_balance"] is not None
                    else "—",
                }
                for row in rows
            ],
            row_key="id",
            pagination={"rowsPerPage": 15},
        ).classes("w-full")


def _holdings_table(rows: list[dict]) -> None:
    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Holdings</h2>', sanitize=False)
        if not rows:
            ui.label("No holdings yet.")
            return
        ui.table(
            columns=[
                {"name": "account", "label": "Account", "field": "account"},
                {"name": "name", "label": "Name", "field": "name"},
                {"name": "ticker", "label": "Ticker", "field": "ticker"},
                {"name": "units", "label": "Units", "field": "units"},
                {"name": "provider", "label": "Provider", "field": "provider"},
            ],
            rows=rows,
            row_key="id",
            pagination={"rowsPerPage": 15},
        ).classes("w-full")


def _transactions_table(rows: list[dict], total: int) -> None:
    with ui.element("div").classes("panel"):
        ui.html(
            f'<h2 class="panel-title">Transactions '
            f'<span style="color:var(--text-muted);font-size:0.9rem;font-weight:400">'
            f"(showing latest {len(rows)} of {total})</span></h2>",
            sanitize=False,
        )
        if not rows:
            ui.label("No transactions yet.")
            return
        ui.table(
            columns=[
                {"name": "date", "label": "Date", "field": "date", "sortable": True},
                {"name": "type", "label": "Type", "field": "type"},
                {"name": "amount", "label": "Amount", "field": "amount"},
                {"name": "account", "label": "Account", "field": "account"},
                {"name": "description", "label": "Description", "field": "description"},
            ],
            rows=[{**row, "amount": format_gbp(row["amount"])} for row in rows],
            row_key="id",
            pagination={"rowsPerPage": 20},
        ).classes("w-full")


def _snapshots_grouped(groups: list[dict], line_total: int) -> None:
    with ui.element("div").classes("panel"):
        ui.html(
            f'<h2 class="panel-title">Balance snapshots '
            f'<span style="color:var(--text-muted);font-size:0.9rem;font-weight:400">'
            f"({len(groups)} dates · {line_total} account lines)</span></h2>",
            sanitize=False,
        )
        ui.label(
            "Each date is one snapshot of balances across accounts. Expand a date to see the detail."
        ).style("color: var(--text-muted); margin-bottom: 0.85rem;")
        if not groups:
            ui.label("No snapshots yet.")
            return

        summary_rows = [
            {
                "date": g["date"],
                "accounts": g["account_count"],
                "total": format_gbp(g["total"]),
            }
            for g in groups
        ]
        ui.table(
            columns=[
                {"name": "date", "label": "Snapshot date", "field": "date", "sortable": True},
                {"name": "accounts", "label": "Accounts recorded", "field": "accounts"},
                {"name": "total", "label": "Sum of balances", "field": "total"},
            ],
            rows=summary_rows,
            row_key="date",
            pagination={"rowsPerPage": 12},
        ).classes("w-full").style("margin-bottom: 1rem;")

        for group in groups[:12]:
            with ui.expansion(
                f"{group['date']} · {group['account_count']} accounts · "
                f"{format_gbp(group['total'])}"
            ).classes("w-full"):
                ui.table(
                    columns=[
                        {"name": "account", "label": "Account", "field": "account"},
                        {"name": "balance", "label": "Balance", "field": "balance"},
                    ],
                    rows=[
                        {
                            "id": line["id"],
                            "account": line["account"],
                            "balance": format_gbp(line["balance"]),
                        }
                        for line in group["lines"]
                    ],
                    row_key="id",
                ).classes("w-full")


def _recurring_table(rows: list[dict]) -> None:
    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Subscriptions & standing orders</h2>',
            sanitize=False,
        )
        if not rows:
            ui.label("No recurring items yet.")
            return
        ui.table(
            columns=[
                {"name": "name", "label": "Name", "field": "name"},
                {"name": "kind", "label": "Kind", "field": "kind"},
                {"name": "amount", "label": "Amount", "field": "amount"},
                {"name": "frequency", "label": "Frequency", "field": "frequency"},
                {"name": "from", "label": "From", "field": "from"},
                {"name": "to", "label": "To", "field": "to"},
                {"name": "net", "label": "Affects net worth", "field": "net"},
                {"name": "active", "label": "Active", "field": "active"},
                {"name": "notes", "label": "Notes", "field": "notes"},
            ],
            rows=[
                {
                    **row,
                    "amount": format_gbp(row["amount"]),
                    "net": "Yes" if row["affects_net_worth"] else "No",
                    "active": "Yes" if row["active"] else "No",
                }
                for row in rows
            ],
            row_key="id",
            pagination={"rowsPerPage": 15},
        ).classes("w-full")
