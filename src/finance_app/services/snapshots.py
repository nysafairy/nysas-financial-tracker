"""Balance snapshot services."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

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


def _upsert_balance_snapshot(
    session: Session, account_id: int, as_of_date: date, balance: float
) -> None:
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


def upsert_balance_snapshot(
    account_id: int,
    as_of_date: date,
    balance: float,
    *,
    session: Session | None = None,
) -> None:
    if session is not None:
        _upsert_balance_snapshot(session, account_id, as_of_date, balance)
        return
    with get_session() as sess:
        _upsert_balance_snapshot(sess, account_id, as_of_date, balance)


def record_balances_for_date(
    as_of_date: date,
    balances: dict[int, float],
    *,
    session: Session | None = None,
) -> int:
    """Upsert many account balances for one snapshot date. Returns count written."""

    def _run(sess: Session) -> int:
        count = 0
        for account_id, balance in balances.items():
            if balance is None:
                continue
            _upsert_balance_snapshot(sess, account_id, as_of_date, balance)
            count += 1
        return count

    if session is not None:
        return _run(session)
    with get_session() as sess:
        return _run(sess)


def delete_balance_snapshot(snapshot_id: int) -> None:
    with get_session() as session:
        row = session.get(BalanceSnapshot, snapshot_id)
        if row is None:
            return
        session.delete(row)
