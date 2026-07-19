"""Aggregations for overview and visualisation pages."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import select

from finance_app.db.models import (
    ACCOUNT_TYPE_LABELS,
    LIABILITY_TYPES,
    Account,
    AccountType,
    BalanceSnapshot,
    Transaction,
    TransactionType,
)
from finance_app.db.session import get_session
from finance_app.services import recurring as recurring_service


def uk_tax_year_start(on: date | None = None) -> date:
    """UK tax year starts 6 April."""
    on = on or date.today()
    year = on.year if on.month > 4 or (on.month == 4 and on.day >= 6) else on.year - 1
    return date(year, 4, 6)


def uk_tax_year_end(on: date | None = None) -> date:
    start = uk_tax_year_start(on)
    return date(start.year + 1, 4, 5)


def _latest_balances(session) -> dict[int, tuple[date, float]]:
    rows = session.scalars(select(BalanceSnapshot)).all()
    latest: dict[int, tuple[date, float]] = {}
    for row in rows:
        prev = latest.get(row.account_id)
        if prev is None or row.as_of_date > prev[0]:
            latest[row.account_id] = (row.as_of_date, row.balance)
    return latest


def _signed_balance(account: Account, balance: float) -> float:
    """Liabilities are stored as amounts owed and reduce net worth."""
    if account.account_type in LIABILITY_TYPES:
        return -abs(balance)
    return balance


def _draft_wealth_overlay() -> dict[str, Any] | None:
    """If a draft session is open, compute assets/debts from the draft sheet."""
    from finance_app.services import draft_session

    state = draft_session.effective_accounts_and_balances()
    if state is None:
        return None
    assets = 0.0
    debts = 0.0
    allocation: dict[AccountType, float] = defaultdict(float)
    for row in state["rows"]:
        if row["balance"] is None:
            continue
        balance = float(row["balance"])
        try:
            atype = AccountType(row["account_type"])
        except ValueError:
            atype = AccountType.OTHER
        allocation[atype] += abs(balance)
        if atype in LIABILITY_TYPES:
            debts += abs(balance)
        else:
            assets += balance
    return {
        "assets": assets,
        "debts": debts,
        "net_worth": assets - debts,
        "as_of_date": state["as_of_date"],
        "allocation": allocation,
        "draft": True,
    }


def assets_and_debts() -> dict[str, float]:
    overlay = _draft_wealth_overlay()
    if overlay is not None:
        return {
            "assets": overlay["assets"],
            "debts": overlay["debts"],
            "net_worth": overlay["net_worth"],
        }
    with get_session() as session:
        accounts = {
            a.id: a for a in session.scalars(select(Account).where(Account.active)).all()
        }
        latest = _latest_balances(session)
        assets = 0.0
        debts = 0.0
        for account_id, (_, balance) in latest.items():
            account = accounts.get(account_id)
            if account is None:
                continue
            if account.account_type in LIABILITY_TYPES:
                debts += abs(balance)
            else:
                assets += balance
        return {"assets": assets, "debts": debts, "net_worth": assets - debts}


def net_worth() -> float:
    return assets_and_debts()["net_worth"]


def allocation_by_account_type() -> list[dict[str, Any]]:
    overlay = _draft_wealth_overlay()
    if overlay is not None:
        totals: dict[AccountType, float] = overlay["allocation"]
        return [
            {
                "type": account_type.value,
                "label": ACCOUNT_TYPE_LABELS[account_type],
                "value": value,
                "is_liability": account_type in LIABILITY_TYPES,
            }
            for account_type, value in sorted(
                totals.items(), key=lambda item: item[1], reverse=True
            )
        ]
    with get_session() as session:
        accounts = {
            a.id: a for a in session.scalars(select(Account).where(Account.active)).all()
        }
        latest = _latest_balances(session)
        totals = defaultdict(float)
        for account_id, (_, balance) in latest.items():
            account = accounts.get(account_id)
            if account is None:
                continue
            totals[account.account_type] += abs(balance)
        return [
            {
                "type": account_type.value,
                "label": ACCOUNT_TYPE_LABELS[account_type],
                "value": value,
                "is_liability": account_type in LIABILITY_TYPES,
            }
            for account_type, value in sorted(
                totals.items(), key=lambda item: item[1], reverse=True
            )
        ]


def net_worth_series() -> list[dict[str, Any]]:
    with get_session() as session:
        accounts = {a.id: a for a in session.scalars(select(Account)).all()}
        rows = session.scalars(select(BalanceSnapshot)).all()
        by_date: dict[date, dict[int, float]] = defaultdict(dict)
        for row in rows:
            by_date[row.as_of_date][row.account_id] = row.balance

        all_dates = sorted(by_date)
        carried: dict[int, float] = {}
        series: list[dict[str, Any]] = []
        for as_of in all_dates:
            carried.update(by_date[as_of])
            total = 0.0
            for account_id, balance in carried.items():
                account = accounts.get(account_id)
                if account is None:
                    continue
                total += _signed_balance(account, balance)
            series.append({"date": as_of.isoformat(), "value": float(total)})

    overlay = _draft_wealth_overlay()
    if overlay is not None:
        point = {
            "date": overlay["as_of_date"].isoformat(),
            "value": float(overlay["net_worth"]),
        }
        if series and series[-1]["date"] == point["date"]:
            series[-1] = point
        else:
            series.append(point)
            series.sort(key=lambda item: item["date"])
    return series


def account_balance_series() -> dict[str, list[dict[str, Any]]]:
    with get_session() as session:
        accounts = {a.id: a.name for a in session.scalars(select(Account)).all()}
        rows = session.scalars(
            select(BalanceSnapshot).order_by(BalanceSnapshot.as_of_date)
        ).all()
        series: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            name = accounts.get(row.account_id, f"Account {row.account_id}")
            series[name].append(
                {"date": row.as_of_date.isoformat(), "value": row.balance}
            )

    from finance_app.services import draft_session

    state = draft_session.effective_accounts_and_balances()
    if state is not None:
        as_of = state["as_of_date"].isoformat()
        for row in state["rows"]:
            if row["balance"] is None:
                continue
            name = row["name"]
            points = series.setdefault(name, [])
            if points and points[-1]["date"] == as_of:
                points[-1] = {"date": as_of, "value": float(row["balance"])}
            else:
                points.append({"date": as_of, "value": float(row["balance"])})
                points.sort(key=lambda item: item["date"])
    return dict(series)


def tax_year_transaction_totals(
    on: date | None = None,
) -> dict[str, float]:
    start = uk_tax_year_start(on)
    end = uk_tax_year_end(on)
    with get_session() as session:
        rows = session.scalars(
            select(Transaction).where(
                Transaction.txn_date >= start,
                Transaction.txn_date <= end,
            )
        ).all()
        totals: dict[str, float] = defaultdict(float)
        for row in rows:
            if row.txn_type == TransactionType.TRANSFER:
                continue
            totals[row.txn_type.value] += row.amount
        return dict(totals)


def net_worth_change() -> dict[str, Any]:
    series = net_worth_series()
    if len(series) < 2:
        return {"delta": 0.0, "pct": None, "from_value": None, "to_value": None}
    previous = series[-2]["value"]
    current = series[-1]["value"]
    delta = current - previous
    pct = (delta / previous * 100.0) if previous else None
    return {
        "delta": delta,
        "pct": pct,
        "from_value": previous,
        "to_value": current,
        "from_date": series[-2]["date"],
        "to_date": series[-1]["date"],
    }


def tax_year_progress(on: date | None = None) -> dict[str, Any]:
    on = on or date.today()
    start = uk_tax_year_start(on)
    end = uk_tax_year_end(on)
    total_days = (end - start).days + 1
    elapsed = min(max((on - start).days + 1, 0), total_days)
    return {
        "elapsed_days": elapsed,
        "total_days": total_days,
        "pct": (elapsed / total_days * 100.0) if total_days else 0.0,
    }


def overview_metrics() -> dict[str, Any]:
    from finance_app.services import draft_session
    from finance_app.services import income as income_service

    wealth = assets_and_debts()
    recurring = recurring_service.recurring_monthly_totals()
    income = income_service.income_by_source()
    draft_meta = draft_session.get_draft_meta()
    return {
        "net_worth": wealth["net_worth"],
        "assets": wealth["assets"],
        "debts": wealth["debts"],
        "subscriptions_monthly": recurring["subscriptions"],
        "recurring_income_monthly": recurring["income"],
        "standing_orders_monthly": recurring["standing_orders"],
        "tax_year_start": uk_tax_year_start().isoformat(),
        "tax_year_end": uk_tax_year_end().isoformat(),
        "allocation": allocation_by_account_type(),
        "net_worth_series": net_worth_series(),
        "net_worth_change": net_worth_change(),
        "tax_year_progress": tax_year_progress(),
        "income_by_source": income,
        "draft_active": draft_meta is not None,
        "draft_as_of": draft_meta["as_of_date"].isoformat() if draft_meta else None,
    }
