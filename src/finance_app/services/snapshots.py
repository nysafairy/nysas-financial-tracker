"""Balance snapshot services."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from finance_app.db.models import BalanceSnapshot
from finance_app.db.session import get_session


def list_balance_snapshots(limit: int = 500) -> list[BalanceSnapshot]:
    with get_session() as session:
        stmt = (
            select(BalanceSnapshot)
            .order_by(BalanceSnapshot.as_of_date.desc(), BalanceSnapshot.account_id)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())


def balances_for_date(as_of_date: date) -> dict[int, float]:
    """Return account_id -> balance for a specific snapshot date."""
    with get_session() as session:
        rows = session.scalars(
            select(BalanceSnapshot).where(BalanceSnapshot.as_of_date == as_of_date)
        ).all()
        return {row.account_id: float(row.balance) for row in rows}


def upsert_balance_snapshot(account_id: int, as_of_date: date, balance: float) -> None:
    with get_session() as session:
        existing = session.scalar(
            select(BalanceSnapshot).where(
                BalanceSnapshot.account_id == account_id,
                BalanceSnapshot.as_of_date == as_of_date,
            )
        )
        if existing:
            existing.balance = float(balance)
        else:
            session.add(
                BalanceSnapshot(
                    account_id=account_id,
                    as_of_date=as_of_date,
                    balance=float(balance),
                )
            )


def record_balances_for_date(
    as_of_date: date, balances: dict[int, float]
) -> int:
    """Upsert many account balances for one snapshot date. Returns count written."""
    count = 0
    for account_id, balance in balances.items():
        if balance is None:
            continue
        upsert_balance_snapshot(account_id, as_of_date, balance)
        count += 1
    return count


def delete_balance_snapshot(snapshot_id: int) -> None:
    with get_session() as session:
        row = session.get(BalanceSnapshot, snapshot_id)
        if row is None:
            return
        session.delete(row)
