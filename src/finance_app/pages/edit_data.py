"""CRUD forms for accounts, holdings, transactions, snapshots, and recurring."""

from __future__ import annotations

from datetime import date

from nicegui import ui

from finance_app.db.models import (
    ACCOUNT_TYPE_LABELS,
    FREQUENCY_LABELS,
    INCOME_CADENCE_LABELS,
    INCOME_CATEGORY_LABELS,
    RECURRING_KIND_LABELS,
    TRANSACTION_TYPE_LABELS,
    AccountType,
    Frequency,
    IncomeCadence,
    IncomeCategory,
    RecurringKind,
    TransactionType,
)
from finance_app.pages.layout import render_shell, require_draft_session, require_profile
from finance_app.services import accounts as account_service
from finance_app.services import draft_session
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
            if not require_draft_session():
                page_header(
                    "Edit data",
                    "Editing opens inside a snapshot session so changes can be "
                    "reviewed on Overview before you commit.",
                )
                _no_session_gate()
                return

            page_header(
                "Edit data",
                "Draft session. Balances autosave. Commit with Save snapshot above.",
            )

            with ui.element("div").classes("session-sheet"):
                with ui.tabs().classes("w-full session-tabs").props(
                    "dense outside-arrows mobile-arrows"
                ) as tabs:
                    tab_balances = ui.tab("Balances")
                    tab_income = ui.tab("Income")
                    tab_holdings = ui.tab("Holdings")
                    tab_txns = ui.tab("Transactions")
                    tab_snaps = ui.tab("History")
                    tab_recurring = ui.tab("Recurring")

                with ui.tab_panels(tabs, value=tab_balances).classes(
                    "w-full session-tab-panels"
                ):
                    with ui.tab_panel(tab_balances):
                        _balances_panel()
                    with ui.tab_panel(tab_income):
                        _income_panel()
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


def _no_session_gate() -> None:
    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">No snapshot session open</h2>', sanitize=False)
        ui.label(
            "Start a new snapshot from the bar at the top of any page. "
            "That unlocks this spreadsheet and other edit tabs, autosaves your work, "
            "and lets Overview reflect the draft until you save or discard."
        ).style("color: var(--text-muted); margin-bottom: 1rem; max-width: 40rem;")
        ui.button(
            "Go to Overview",
            on_click=lambda: ui.navigate.to("/"),
        ).props("flat")


def _balances_panel() -> None:
    state = draft_session.effective_accounts_and_balances()
    meta = draft_session.get_draft_meta()
    if state is None or meta is None:
        ui.label("No draft session.")
        return

    as_of = meta["as_of_date"]
    as_of_text = as_of.isoformat() if hasattr(as_of, "isoformat") else str(as_of)
    type_options = {t.value: label for t, label in ACCOUNT_TYPE_LABELS.items()}

    with ui.element("div").classes("sheet-toolbar"):
        ui.html(
            f"<div><strong>As of {as_of_text}</strong>"
            "<span>Edit cells to autosave. Every row needs a balance to commit.</span></div>",
            sanitize=False,
        )
        with ui.element("div").classes("sheet-toolbar-right"):

            def open_date_dialog() -> None:
                with ui.dialog() as dialog, ui.card().classes("sheet-date-dialog"):
                    ui.label("Change snapshot date").classes("sheet-date-dialog-title")
                    picker = ui.date(value=as_of_text).classes("sheet-date-picker")

                    def apply_date() -> None:
                        raw = picker.value or as_of_text
                        parsed = date.fromisoformat(str(raw)[:10])
                        dialog.close()
                        if parsed == as_of:
                            return
                        draft_session.set_as_of_date(parsed)
                        _refresh()

                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button("Cancel", on_click=dialog.close).props("flat")
                        ui.button("Apply", on_click=apply_date).props(
                            "color=primary unelevated"
                        )
                dialog.open()

            ui.button(
                icon="edit_calendar",
                on_click=open_date_dialog,
            ).props("flat dense round").classes("sheet-date-btn").tooltip(
                "Change snapshot date"
            )

    with ui.element("div").classes("sheet-grid-wrap"):
        with ui.element("table").classes("sheet-table"):
            with ui.element("thead"):
                with ui.element("tr"):
                    with ui.element("th").classes("sheet-th"):
                        ui.label("Account")
                    with ui.element("th").classes("sheet-th"):
                        ui.label("Type")
                    with ui.element("th").classes("sheet-th sheet-th-num"):
                        ui.label("Balance (£)")
                    ui.element("th").classes("sheet-th sheet-th-action")
            with ui.element("tbody"):
                for row in state["rows"]:
                    with ui.element("tr").classes("sheet-tr"):
                        with ui.element("td").classes("sheet-td"):
                            name_input = ui.input(value=row["name"]).props(
                                "borderless dense hide-bottom-space"
                            ).classes("sheet-input")

                            def make_rename(r=row, widget=name_input):
                                def on_blur() -> None:
                                    new_name = (widget.value or "").strip()
                                    if not new_name or new_name == r["name"]:
                                        return
                                    try:
                                        draft_session.rename_draft_row(
                                            account_id=r["account_id"],
                                            temp_key=r["temp_key"],
                                            name=new_name,
                                        )
                                    except ValueError as exc:
                                        ui.notify(str(exc), type="warning")

                                return on_blur

                            name_input.on("blur", make_rename())

                        with ui.element("td").classes("sheet-td sheet-td-muted"):
                            badge = "New · " if row["is_new"] else ""
                            debt = " owed" if row["is_liability"] else ""
                            ui.label(f"{badge}{row['account_type_label']}{debt}")

                        with ui.element("td").classes("sheet-td sheet-td-num"):
                            bal_input = ui.number(
                                value=row["balance"],
                                format="%.2f",
                            ).props(
                                "borderless dense hide-bottom-space "
                                "input-class=text-right"
                            ).classes("sheet-input sheet-balance")

                            def make_save(r=row, widget=bal_input):
                                def on_change() -> None:
                                    raw = widget.value
                                    amount = None if raw in (None, "") else float(raw)
                                    draft_session.set_balance(
                                        balance=amount,
                                        account_id=r["account_id"],
                                        temp_key=r["temp_key"],
                                    )

                                return on_change

                            bal_input.on("blur", make_save())

                        with ui.element("td").classes("sheet-td sheet-td-action"):

                            def make_remove(r=row):
                                def remove() -> None:
                                    draft_session.deactivate_draft_account(
                                        account_id=r["account_id"],
                                        temp_key=r["temp_key"],
                                    )
                                    _refresh()

                                return remove

                            ui.button(icon="close", on_click=make_remove()).props(
                                "flat dense round size=md"
                            ).classes("sheet-remove")

    missing = draft_session.missing_balances()
    if missing:
        ui.label(f"{len(missing)} balance(s) still empty").classes("sheet-warn")

    with ui.element("div").classes("sheet-add"):
        with ui.row().classes("w-full items-end gap-2 flex-wrap no-wrap-md"):
            new_name = ui.input("Name").props("dense").classes("sheet-add-field grow")
            new_type = ui.select(
                type_options, value=AccountType.SAVINGS.value, label="Type"
            ).props("dense").classes("sheet-add-field")
            new_bal = ui.number("Balance (£)", value=None, format="%.2f").props(
                "dense"
            ).classes("sheet-add-field")

            def add_row() -> None:
                if not (new_name.value or "").strip():
                    ui.notify("Name is required", type="warning")
                    return
                opening = None
                if new_bal.value not in (None, ""):
                    opening = float(new_bal.value)
                draft_session.add_draft_account(
                    new_name.value,
                    new_type.value,
                    opening_balance=opening,
                )
                _refresh()

            ui.button("Add", on_click=add_row).props("color=primary unelevated dense")


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
                ).classes("sheet-toggle").props("unelevated toggle-color=primary")
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
                ).classes("sheet-toggle").props("unelevated toggle-color=primary")
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
    snaps = snapshot_service.list_balance_snapshots(limit=500)
    account_names = {a.id: a.name for a in account_service.list_accounts()}
    by_date: dict[date, list] = {}
    for snap in snaps:
        by_date.setdefault(snap.as_of_date, []).append(snap)

    with ui.element("div").classes("panel"):
        ui.html('<h2 class="panel-title">Committed snapshots</h2>', sanitize=False)
        ui.label(
            "Balances for a new date are edited on Balances, then Save snapshot. "
            "Expand a date below to delete individual account balances."
        ).classes("sheet-help")

        if not by_date:
            ui.label("No committed snapshots yet.")
            return

        summary_rows = []
        detail_by_date: dict[str, list] = {}
        for as_of, lines in sorted(by_date.items(), key=lambda item: item[0], reverse=True):
            key = as_of.isoformat()
            summary_rows.append(
                {
                    "date": key,
                    "accounts": len(lines),
                    "total": format_gbp(sum(line.balance for line in lines)),
                }
            )
            detail_by_date[key] = sorted(
                lines, key=lambda s: account_names.get(s.account_id, "")
            )

        ui.table(
            columns=[
                {"name": "date", "label": "Date", "field": "date", "align": "left"},
                {
                    "name": "accounts",
                    "label": "Accounts",
                    "field": "accounts",
                    "align": "left",
                },
                {"name": "total", "label": "Total", "field": "total", "align": "left"},
            ],
            rows=summary_rows[:20],
            row_key="date",
            pagination={"rowsPerPage": 10},
        ).classes("w-full sheet-history-summary")

        for key, lines in list(detail_by_date.items())[:12]:
            count = len(lines)
            account_word = "account" if count == 1 else "accounts"
            with ui.expansion(f"{key} · {count} {account_word}").classes(
                "w-full sheet-history-exp"
            ):
                rows = [
                    {
                        "id": s.id,
                        "account": account_names.get(s.account_id, str(s.account_id)),
                        "balance": format_gbp(s.balance),
                    }
                    for s in lines
                ]
                table = ui.table(
                    columns=[
                        {
                            "name": "account",
                            "label": "Account",
                            "field": "account",
                            "align": "left",
                        },
                        {
                            "name": "balance",
                            "label": "Balance",
                            "field": "balance",
                            "align": "left",
                        },
                        {"name": "actions", "label": "", "field": "actions"},
                    ],
                    rows=rows,
                    row_key="id",
                ).classes("w-full")

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
