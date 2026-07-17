"""CRUD forms for accounts, holdings, transactions, snapshots, and recurring."""

from __future__ import annotations

from datetime import date

from nicegui import ui

from finance_app.db.models import (
    ACCESS_TYPE_LABELS,
    ACCOUNT_TYPE_LABELS,
    FREQUENCY_LABELS,
    INCOME_CADENCE_LABELS,
    INCOME_CATEGORY_LABELS,
    INTEREST_FREQUENCY_LABELS,
    RECURRING_KIND_LABELS,
    TRANSACTION_TYPE_LABELS,
    AccessType,
    AccountType,
    Frequency,
    IncomeCadence,
    IncomeCategory,
    InterestFrequency,
    RecurringKind,
    TransactionType,
)
from finance_app.pages.layout import render_shell, require_profile
from finance_app.services import accounts as account_service
from finance_app.services import income as income_service
from finance_app.services import recurring as recurring_service
from finance_app.services import snapshots as snapshot_service
from finance_app.ui.components import format_gbp, page_header


def register() -> None:
    @ui.page("/edit")
    def edit_page() -> None:
        if not require_profile():
            return

        with render_shell("/edit"):
            page_header(
                "Edit data",
                "Accounts, income sources (salary / freelance / gigs), holdings, "
                "snapshots, subscriptions and standing orders.",
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
                    _income_panel()
                with ui.tab_panel(tab_accounts):
                    _accounts_panel()
                with ui.tab_panel(tab_holdings):
                    _holdings_panel()
                with ui.tab_panel(tab_txns):
                    _transactions_panel()
                with ui.tab_panel(tab_snaps):
                    _snapshots_panel()
                with ui.tab_panel(tab_recurring):
                    _recurring_panel()


def _refresh() -> None:
    ui.navigate.to("/edit")


def _income_panel() -> None:
    cat_options = {c.value: label for c, label in INCOME_CATEGORY_LABELS.items()}
    arrival_options = {
        "fixed": "Fixed (salary / retainer)",
        "variable": "Variable (freelance / gigs)",
    }

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Add income source</h2>', sanitize=False)
        ui.label(
            "Fixed sources use an expected amount (pro-rated across the tax year). "
            "Variable sources only count receipts you log when you get paid."
        ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
        with ui.element("div").classes("form-stack"):
            name = ui.input("Name", placeholder="e.g. Day job, Upwork, Client X").classes(
                "w-full"
            )
            category = ui.select(
                cat_options, value=IncomeCategory.SALARY.value, label="Category"
            ).classes("w-full")
            arrival = ui.select(
                arrival_options,
                value="fixed",
                label="How it arrives",
            ).classes("w-full")
            amount_block = ui.element("div").classes("form-stack")
            with amount_block:
                ui.label("Expected amount is").style(
                    "color: var(--text-muted); margin-bottom: 0.25rem;"
                )
                period = ui.toggle(
                    {"yearly": "Yearly", "monthly": "Monthly"},
                    value="yearly",
                ).props("unelevated toggle-color=primary")
                expected = ui.number(
                    "Expected amount (£)",
                    value=None,
                    format="%.2f",
                ).classes("w-full")
            notes = ui.input("Notes").classes("w-full")

            def sync_amount_visibility() -> None:
                amount_block.set_visibility(arrival.value == "fixed")

            arrival.on_value_change(lambda _: sync_amount_visibility())
            sync_amount_visibility()

            def add_stream() -> None:
                if not (name.value or "").strip():
                    ui.notify("Name is required", type="warning")
                    return
                if arrival.value == "variable":
                    cadence = IncomeCadence.VARIABLE.value
                    amount = None
                else:
                    cadence = (
                        IncomeCadence.FIXED_MONTHLY.value
                        if period.value == "monthly"
                        else IncomeCadence.FIXED_ANNUAL.value
                    )
                    amount = None
                    if expected.value not in (None, ""):
                        amount = float(expected.value)
                    if amount is None or amount <= 0:
                        ui.notify("Enter a positive expected amount", type="warning")
                        return
                income_service.create_stream(
                    name.value,
                    category.value,
                    cadence,
                    expected_amount=amount,
                    notes=notes.value or None,
                )
                ui.notify("Income source added", type="positive")
                _refresh()

            with ui.element("div").classes("form-actions"):
                ui.button("Add income source", on_click=add_stream)

    streams = income_service.list_streams()
    stream_options = {str(s.id): s.name for s in streams if s.active}
    fixed_streams = [
        s
        for s in streams
        if s.active and s.cadence != IncomeCadence.VARIABLE
    ]
    fixed_options = {str(s.id): s.name for s in fixed_streams}

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Record a pay change</h2>', sanitize=False)
        ui.label(
            "Same role, new salary or retainer: keep the source and set the date the "
            "new rate starts. Overview pro-rates old vs new pay across the tax year."
        ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
        if not fixed_options:
            ui.label("Add a fixed income source first.")
        else:
            with ui.element("div").classes("form-stack"):
                pay_stream = ui.select(
                    fixed_options,
                    value=next(iter(fixed_options)),
                    label="Income source",
                ).classes("w-full")
                ui.label("New amount is").style(
                    "color: var(--text-muted); margin-bottom: 0.25rem;"
                )
                pay_period = ui.toggle(
                    {"yearly": "Yearly", "monthly": "Monthly"},
                    value="yearly",
                ).props("unelevated toggle-color=primary")
                pay_amount = ui.number(
                    "New expected amount (£)", value=None, format="%.2f"
                ).classes("w-full")
                pay_from = ui.date_input(
                    "Effective from", value=date.today()
                ).classes("w-full")
                pay_notes = ui.input(
                    "Notes", placeholder="Promotion, cost-of-living rise…"
                ).classes("w-full")

                def _sync_pay_period_default() -> None:
                    stream = next(
                        (s for s in fixed_streams if str(s.id) == str(pay_stream.value)),
                        None,
                    )
                    if stream is None:
                        return
                    pay_period.value = (
                        "monthly"
                        if stream.cadence == IncomeCadence.FIXED_MONTHLY
                        else "yearly"
                    )

                pay_stream.on_value_change(lambda _: _sync_pay_period_default())
                _sync_pay_period_default()

                def save_pay_change() -> None:
                    if pay_amount.value in (None, "") or float(pay_amount.value) <= 0:
                        ui.notify("Enter a positive new amount", type="warning")
                        return
                    raw_date = pay_from.value or date.today()
                    if isinstance(raw_date, str):
                        effective = date.fromisoformat(raw_date[:10])
                    else:
                        effective = raw_date
                    try:
                        income_service.record_pay_change(
                            int(pay_stream.value),
                            new_amount=float(pay_amount.value),
                            effective_from=effective,
                            as_monthly=pay_period.value == "monthly",
                            notes=pay_notes.value or None,
                        )
                    except ValueError as exc:
                        ui.notify(str(exc), type="warning")
                        return
                    ui.notify("Pay change recorded", type="positive")
                    _refresh()

                with ui.element("div").classes("form-actions"):
                    ui.button("Record pay change", on_click=save_pay_change)

            for stream in fixed_streams:
                periods = income_service.list_rate_periods(stream.id)
                if not periods:
                    continue
                with ui.expansion(
                    f"Rate history — {stream.name} ({len(periods)} period(s))"
                ).classes("w-full").style("margin-top: 0.5rem;"):
                    ui.table(
                        columns=[
                            {
                                "name": "from",
                                "label": "Effective from",
                                "field": "from",
                            },
                            {
                                "name": "annual",
                                "label": "Annual equivalent",
                                "field": "annual",
                            },
                            {"name": "notes", "label": "Notes", "field": "notes"},
                        ],
                        rows=[
                            {
                                "id": p.id,
                                "from": p.effective_from.isoformat(),
                                "annual": format_gbp(p.annual_amount),
                                "notes": p.notes or "",
                            }
                            for p in periods
                        ],
                        row_key="id",
                    ).classes("w-full")

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Log a receipt / payout</h2>', sanitize=False)
        if not stream_options:
            ui.label("Add an income source first.")
        else:
            with ui.element("div").classes("form-stack"):
                stream_id = ui.select(
                    stream_options,
                    value=next(iter(stream_options)),
                    label="Source",
                ).classes("w-full")
                amount = ui.number("Amount (£)", value=0, format="%.2f").classes("w-full")
                entry_date = ui.date_input("Date", value=date.today()).classes("w-full")
                description = ui.input(
                    "Description", placeholder="Invoice #12, weekend gig…"
                ).classes("w-full")

                def add_receipt() -> None:
                    raw_date = entry_date.value or date.today()
                    if isinstance(raw_date, str):
                        parsed = date.fromisoformat(raw_date[:10])
                    else:
                        parsed = raw_date
                    if float(amount.value or 0) <= 0:
                        ui.notify("Amount must be positive", type="warning")
                        return
                    income_service.add_receipt(
                        int(stream_id.value),
                        float(amount.value),
                        parsed,
                        description=description.value or None,
                    )
                    ui.notify("Receipt logged", type="positive")
                    _refresh()

                with ui.element("div").classes("form-actions"):
                    ui.button("Log receipt", on_click=add_receipt)

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Income sources</h2>', sanitize=False)
        if not streams:
            ui.label("No income sources yet.")
        else:
            columns = [
                {"name": "name", "label": "Name", "field": "name"},
                {"name": "category", "label": "Category", "field": "category"},
                {"name": "cadence", "label": "Cadence", "field": "cadence"},
                {"name": "expected", "label": "Expected", "field": "expected"},
                {"name": "active", "label": "Active", "field": "active"},
                {"name": "actions", "label": "", "field": "actions"},
            ]
            rows = [
                {
                    "id": s.id,
                    "name": s.name,
                    "category": INCOME_CATEGORY_LABELS.get(s.category, s.category.value),
                    "cadence": INCOME_CADENCE_LABELS.get(s.cadence, s.cadence.value),
                    "expected": format_gbp(s.expected_amount)
                    if s.expected_amount is not None
                    else "—",
                    "active": "Yes" if s.active else "No",
                }
                for s in streams
            ]
            table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

            def remove(e) -> None:
                income_service.delete_stream(e.args["id"])
                ui.notify("Income source deleted", type="info")
                _refresh()

            table.add_slot(
                "body-cell-actions",
                r'''
                <q-td :props="props">
                  <q-btn dense flat label="Delete" color="negative"
                         @click="() => $parent.$emit('remove', props.row)" />
                </q-td>
                ''',
            )
            table.on("remove", remove)

    receipts = income_service.list_receipts(limit=50)
    names = {s.id: s.name for s in streams}
    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Recent receipts</h2>', sanitize=False)
        if not receipts:
            ui.label("No receipts logged yet.")
            return
        columns = [
            {"name": "date", "label": "Date", "field": "date"},
            {"name": "source", "label": "Source", "field": "source"},
            {"name": "amount", "label": "Amount", "field": "amount"},
            {"name": "description", "label": "Description", "field": "description"},
            {"name": "actions", "label": "", "field": "actions"},
        ]
        rows = [
            {
                "id": r.id,
                "date": r.entry_date.isoformat(),
                "source": names.get(r.stream_id, str(r.stream_id)),
                "amount": format_gbp(r.amount),
                "description": r.description or "",
            }
            for r in receipts
        ]
        table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        def remove_receipt(e) -> None:
            income_service.delete_receipt(e.args["id"])
            ui.notify("Receipt deleted", type="info")
            _refresh()

        table.add_slot(
            "body-cell-actions",
            r'''
            <q-td :props="props">
              <q-btn dense flat label="Delete" color="negative"
                     @click="() => $parent.$emit('remove', props.row)" />
            </q-td>
            ''',
        )
        table.on("remove", remove_receipt)


def _parse_optional_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    if isinstance(value, date):
        return value
    return None


def _accounts_panel() -> None:
    accounts = account_service.list_accounts()
    type_options = {t.value: label for t, label in ACCOUNT_TYPE_LABELS.items()}
    freq_options = {f.value: label for f, label in INTEREST_FREQUENCY_LABELS.items()}
    access_options = {a.value: label for a, label in ACCESS_TYPE_LABELS.items()}

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Add account or debt</h2>', sanitize=False)
        ui.label(
            "Leave banking/rate fields blank when they do not apply "
            "(e.g. pensions, credit cards)."
        ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
        with ui.element("div").classes("form-stack"):
            name = ui.input("Name").classes("w-full")
            account_type = ui.select(
                type_options, value=AccountType.SAVINGS.value, label="Type"
            ).classes("w-full")
            provider = ui.input("Provider / bank").classes("w-full")
            account_number = ui.input("Account number").classes("w-full")
            sort_code = ui.input("Sort code", placeholder="12-34-56").classes("w-full")
            rate = ui.number(
                "Interest rate % (AER / gross)", value=None, format="%.2f"
            ).classes("w-full")
            interest_frequency = ui.select(
                freq_options,
                value=InterestFrequency.MONTHLY.value,
                label="Interest paid",
            ).classes("w-full")
            access_type = ui.select(
                access_options,
                value=AccessType.EASY_ACCESS.value,
                label="Access / rate type",
            ).classes("w-full")
            notice_days = ui.number("Notice days (if notice account)", value=None).classes(
                "w-full"
            )
            maturity = ui.input(
                "Maturity / fixed-term end (YYYY-MM-DD, optional)"
            ).classes("w-full")
            opened = ui.input("Opened date (YYYY-MM-DD, optional)").classes("w-full")
            notes = ui.textarea("Notes").classes("w-full")

            def add_account() -> None:
                if not (name.value or "").strip():
                    ui.notify("Name is required", type="warning")
                    return
                account_service.create_account(
                    name.value,
                    account_type.value,
                    provider=provider.value or None,
                    account_number=account_number.value or None,
                    sort_code=sort_code.value or None,
                    interest_rate_pct=float(rate.value)
                    if rate.value not in (None, "")
                    else None,
                    interest_frequency=interest_frequency.value,
                    access_type=access_type.value,
                    notice_days=int(notice_days.value)
                    if notice_days.value not in (None, "")
                    else None,
                    maturity_date=_parse_optional_date(maturity.value),
                    opened_date=_parse_optional_date(opened.value),
                    notes=notes.value or None,
                )
                ui.notify("Account added", type="positive")
                _refresh()

            with ui.element("div").classes("form-actions"):
                ui.button("Add account", on_click=add_account)

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Accounts</h2>', sanitize=False)
        if not accounts:
            ui.label("No accounts yet.")
            return
        columns = [
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "type", "label": "Type", "field": "type"},
            {"name": "provider", "label": "Provider", "field": "provider"},
            {"name": "rate", "label": "Rate %", "field": "rate"},
            {"name": "access", "label": "Access", "field": "access"},
            {"name": "maturity", "label": "Maturity", "field": "maturity"},
            {"name": "kind", "label": "Kind", "field": "kind"},
            {"name": "actions", "label": "", "field": "actions"},
        ]
        rows = [
            {
                "id": a.id,
                "name": a.name,
                "type": ACCOUNT_TYPE_LABELS.get(a.account_type, a.account_type.value),
                "provider": a.provider or "",
                "rate": f"{a.interest_rate_pct:.2f}"
                if a.interest_rate_pct is not None
                else "—",
                "access": ACCESS_TYPE_LABELS.get(a.access_type, "—")
                if a.access_type
                else "—",
                "maturity": a.maturity_date.isoformat() if a.maturity_date else "—",
                "kind": "Debt" if a.is_liability else "Asset",
            }
            for a in accounts
        ]
        table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        def deactivate(e) -> None:
            account_service.update_account(e.args["id"], active=False)
            ui.notify("Account deactivated", type="info")
            _refresh()

        table.add_slot(
            "body-cell-actions",
            r'''
            <q-td :props="props">
              <q-btn dense flat label="Deactivate" color="warning"
                     @click="() => $parent.$emit('deactivate', props.row)" />
            </q-td>
            ''',
        )
        table.on("deactivate", deactivate)


def _holdings_panel() -> None:
    accounts = account_service.list_accounts(active_only=True)
    account_options = {str(a.id): a.name for a in accounts}
    holdings = account_service.list_holdings()

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Add holding</h2>', sanitize=False)
        if not account_options:
            ui.label("Create an account first.")
        else:
            with ui.element("div").classes("form-stack"):
                account_id = ui.select(
                    account_options,
                    value=next(iter(account_options)),
                    label="Account",
                ).classes("w-full")
                name = ui.input("Name").classes("w-full")
                ticker = ui.input("Ticker").classes("w-full")
                units = ui.number("Units", value=0, format="%.4f").classes("w-full")
                provider = ui.input("Provider").classes("w-full")

                def add_holding() -> None:
                    if not (name.value or "").strip():
                        ui.notify("Name is required", type="warning")
                        return
                    account_service.create_holding(
                        int(account_id.value),
                        name.value,
                        ticker=ticker.value or None,
                        units=float(units.value or 0),
                        provider=provider.value or None,
                    )
                    ui.notify("Holding added", type="positive")
                    _refresh()

                with ui.element("div").classes("form-actions"):
                    ui.button("Add holding", on_click=add_holding)

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Holdings</h2>', sanitize=False)
        if not holdings:
            ui.label("No holdings yet.")
            return
        account_names = {a.id: a.name for a in account_service.list_accounts()}
        columns = [
            {"name": "account", "label": "Account", "field": "account"},
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "ticker", "label": "Ticker", "field": "ticker"},
            {"name": "units", "label": "Units", "field": "units"},
            {"name": "actions", "label": "", "field": "actions"},
        ]
        rows = [
            {
                "id": h.id,
                "account": account_names.get(h.account_id, str(h.account_id)),
                "name": h.name,
                "ticker": h.ticker or "",
                "units": h.units,
            }
            for h in holdings
        ]
        table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        def remove(e) -> None:
            account_service.delete_holding(e.args["id"])
            ui.notify("Holding deleted", type="info")
            _refresh()

        table.add_slot(
            "body-cell-actions",
            r'''
            <q-td :props="props">
              <q-btn dense flat label="Delete" color="negative"
                     @click="() => $parent.$emit('remove', props.row)" />
            </q-td>
            ''',
        )
        table.on("remove", remove)


def _transactions_panel() -> None:
    accounts = account_service.list_accounts(active_only=True)
    account_options = {"": "— None —", **{str(a.id): a.name for a in accounts}}
    type_options = {t.value: label for t, label in TRANSACTION_TYPE_LABELS.items()}

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Add transaction</h2>', sanitize=False)
        with ui.element("div").classes("form-stack"):
            txn_date = ui.date_input("Date", value=date.today()).classes("w-full")
            txn_type = ui.select(
                type_options, value=TransactionType.INTEREST.value, label="Type"
            ).classes("w-full")
            amount = ui.number("Amount (£)", value=0, format="%.2f").classes("w-full")
            account_id = ui.select(account_options, value="", label="Account").classes(
                "w-full"
            )
            description = ui.input("Description").classes("w-full")

            def add_txn() -> None:
                raw_date = txn_date.value or date.today()
                if isinstance(raw_date, str):
                    parsed = date.fromisoformat(raw_date[:10])
                else:
                    parsed = raw_date
                account_service.create_transaction(
                    txn_date=parsed,
                    txn_type=txn_type.value,
                    amount=float(amount.value or 0),
                    account_id=int(account_id.value) if account_id.value else None,
                    description=description.value or None,
                )
                ui.notify("Transaction added", type="positive")
                _refresh()

            with ui.element("div").classes("form-actions"):
                ui.button("Add transaction", on_click=add_txn)

    txns = account_service.list_transactions()
    account_names = {a.id: a.name for a in account_service.list_accounts()}
    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Recent transactions</h2>', sanitize=False)
        if not txns:
            ui.label("No transactions yet.")
            return
        columns = [
            {"name": "date", "label": "Date", "field": "date"},
            {"name": "type", "label": "Type", "field": "type"},
            {"name": "amount", "label": "Amount", "field": "amount"},
            {"name": "account", "label": "Account", "field": "account"},
            {"name": "description", "label": "Description", "field": "description"},
            {"name": "actions", "label": "", "field": "actions"},
        ]
        rows = [
            {
                "id": t.id,
                "date": t.txn_date.isoformat(),
                "type": TRANSACTION_TYPE_LABELS.get(t.txn_type, t.txn_type.value),
                "amount": format_gbp(t.amount),
                "account": account_names.get(t.account_id, "—") if t.account_id else "—",
                "description": t.description or "",
            }
            for t in txns
        ]
        table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        def remove(e) -> None:
            account_service.delete_transaction(e.args["id"])
            ui.notify("Transaction deleted", type="info")
            _refresh()

        table.add_slot(
            "body-cell-actions",
            r'''
            <q-td :props="props">
              <q-btn dense flat label="Delete" color="negative"
                     @click="() => $parent.$emit('remove', props.row)" />
            </q-td>
            ''',
        )
        table.on("remove", remove)


def _snapshots_panel() -> None:
    accounts = account_service.list_accounts(active_only=True)

    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Record balances as of a date</h2>',
            sanitize=False,
        )
        ui.label(
            "For credit cards, loans and mortgages, enter the amount still owed."
        ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
        with ui.element("div").classes("form-stack"):
            as_of = ui.date_input("As of date", value=date.today()).classes("w-full")
            inputs: dict[int, ui.number] = {}
            if not accounts:
                ui.label("Create an account first.")
            else:
                for account in accounts:
                    label = account.name
                    if account.is_liability:
                        label = f"{account.name} (owed £)"
                    else:
                        label = f"{account.name} (£)"
                    inputs[account.id] = ui.number(
                        label, value=None, format="%.2f"
                    ).classes("w-full")

                def save_snapshots() -> None:
                    raw_date = as_of.value or date.today()
                    if isinstance(raw_date, str):
                        as_of_date = date.fromisoformat(raw_date[:10])
                    else:
                        as_of_date = raw_date
                    balances: dict[int, float] = {}
                    for account_id, widget in inputs.items():
                        if widget.value is None or widget.value == "":
                            continue
                        balances[account_id] = float(widget.value)
                    if not balances:
                        ui.notify("Enter at least one balance", type="warning")
                        return
                    count = snapshot_service.record_balances_for_date(
                        as_of_date, balances
                    )
                    ui.notify(f"Saved {count} snapshot(s)", type="positive")
                    _refresh()

                with ui.element("div").classes("form-actions"):
                    ui.button("Save snapshots", on_click=save_snapshots)

    snaps = snapshot_service.list_balance_snapshots(limit=500)
    account_names = {a.id: a.name for a in account_service.list_accounts()}
    by_date: dict[date, list] = {}
    for snap in snaps:
        by_date.setdefault(snap.as_of_date, []).append(snap)

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Recent balance snapshots</h2>', sanitize=False)
        ui.label(
            "Each date is one snapshot. Expand a date to edit or delete individual lines."
        ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
        if not by_date:
            ui.label("No snapshots yet.")
            return

        for as_of, lines in sorted(by_date.items(), key=lambda item: item[0], reverse=True)[
            :12
        ]:
            total = sum(line.balance for line in lines)
            with ui.expansion(
                f"{as_of.isoformat()} · {len(lines)} accounts · {format_gbp(total)}"
            ).classes("w-full"):
                columns = [
                    {"name": "account", "label": "Account", "field": "account"},
                    {"name": "balance", "label": "Balance", "field": "balance"},
                    {"name": "actions", "label": "", "field": "actions"},
                ]
                rows = [
                    {
                        "id": s.id,
                        "account": account_names.get(s.account_id, str(s.account_id)),
                        "balance": format_gbp(s.balance),
                    }
                    for s in sorted(
                        lines,
                        key=lambda s: account_names.get(s.account_id, ""),
                    )
                ]
                table = ui.table(columns=columns, rows=rows, row_key="id").classes(
                    "w-full"
                )

                def remove(e) -> None:
                    snapshot_service.delete_balance_snapshot(e.args["id"])
                    ui.notify("Snapshot line deleted", type="info")
                    _refresh()

                table.add_slot(
                    "body-cell-actions",
                    r'''
                    <q-td :props="props">
                      <q-btn dense flat label="Delete" color="negative"
                             @click="() => $parent.$emit('remove', props.row)" />
                    </q-td>
                    ''',
                )
                table.on("remove", remove)


def _recurring_panel() -> None:
    accounts = account_service.list_accounts(active_only=True)
    account_options = {"": "— None —", **{str(a.id): a.name for a in accounts}}
    kind_options = {k.value: label for k, label in RECURRING_KIND_LABELS.items()}
    freq_options = {f.value: label for f, label in FREQUENCY_LABELS.items()}

    with ui.element("div").classes("panel"):
        ui.html(
            '<h2 class="panel-title">Add subscription, standing order, or income</h2>',
            sanitize=False,
        )
        ui.label(
            "Standing orders move money between your own accounts and do not change "
            "net worth. Subscriptions reduce forecast cash."
        ).style("color: var(--text-muted); margin-bottom: 0.75rem;")
        with ui.element("div").classes("form-stack"):
            name = ui.input("Name").classes("w-full")
            kind = ui.select(
                kind_options,
                value=RecurringKind.SUBSCRIPTION.value,
                label="Kind",
            ).classes("w-full")
            amount = ui.number("Amount (£)", value=0, format="%.2f").classes("w-full")
            frequency = ui.select(
                freq_options, value=Frequency.MONTHLY.value, label="Frequency"
            ).classes("w-full")
            from_account = ui.select(
                account_options, value="", label="From account"
            ).classes("w-full")
            to_account = ui.select(
                account_options, value="", label="To account (standing orders)"
            ).classes("w-full")
            notes = ui.input("Notes").classes("w-full")

            def add_item() -> None:
                if not (name.value or "").strip():
                    ui.notify("Name is required", type="warning")
                    return
                if float(amount.value or 0) <= 0:
                    ui.notify("Amount must be positive", type="warning")
                    return
                recurring_service.create_recurring(
                    name.value,
                    kind.value,
                    float(amount.value or 0),
                    frequency.value,
                    from_account_id=int(from_account.value) if from_account.value else None,
                    to_account_id=int(to_account.value) if to_account.value else None,
                    notes=notes.value or None,
                )
                ui.notify("Recurring item added", type="positive")
                _refresh()

            with ui.element("div").classes("form-actions"):
                ui.button("Add recurring item", on_click=add_item)

    items = recurring_service.list_recurring()
    account_names = {a.id: a.name for a in account_service.list_accounts()}
    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Recurring items</h2>', sanitize=False)
        if not items:
            ui.label("No subscriptions or standing orders yet.")
            return
        columns = [
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "kind", "label": "Kind", "field": "kind"},
            {"name": "amount", "label": "Amount", "field": "amount"},
            {"name": "frequency", "label": "Frequency", "field": "frequency"},
            {"name": "from", "label": "From", "field": "from"},
            {"name": "to", "label": "To", "field": "to"},
            {"name": "net", "label": "Affects net worth", "field": "net"},
            {"name": "actions", "label": "", "field": "actions"},
        ]
        rows = [
            {
                "id": item.id,
                "name": item.name,
                "kind": RECURRING_KIND_LABELS.get(item.kind, item.kind.value),
                "amount": format_gbp(item.amount),
                "frequency": FREQUENCY_LABELS.get(item.frequency, item.frequency.value),
                "from": account_names.get(item.from_account_id, "—")
                if item.from_account_id
                else "—",
                "to": account_names.get(item.to_account_id, "—")
                if item.to_account_id
                else "—",
                "net": "Yes" if item.affects_net_worth else "No",
            }
            for item in items
        ]
        table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")

        def remove(e) -> None:
            recurring_service.delete_recurring(e.args["id"])
            ui.notify("Deleted", type="info")
            _refresh()

        table.add_slot(
            "body-cell-actions",
            r'''
            <q-td :props="props">
              <q-btn dense flat label="Delete" color="negative"
                     @click="() => $parent.$emit('remove', props.row)" />
            </q-td>
            ''',
        )
        table.on("remove", remove)
