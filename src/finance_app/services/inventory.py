"""Read-only inventory of what is in the current profile database."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select

from finance_app.db.models import (
    ACCESS_TYPE_LABELS,
    ACCOUNT_TYPE_LABELS,
    FREQUENCY_LABELS,
    INCOME_CADENCE_LABELS,
    INCOME_CATEGORY_LABELS,
    INTEREST_FREQUENCY_LABELS,
    LIABILITY_TYPES,
    PAY_FREQUENCY_LABELS,
    RECURRING_KIND_LABELS,
    TAX_BAND_LABELS,
    TAX_TREATMENT_LABELS,
    TRANSACTION_TYPE_LABELS,
    Account,
    BalanceSnapshot,
    IncomeReceipt,
    IncomeStream,
    RecurringItem,
    Transaction,
    default_tax_treatment,
)
from finance_app.db.session import get_session


def _latest_balances(session) -> dict[int, float]:
    rows = session.scalars(select(BalanceSnapshot)).all()
    latest: dict[int, tuple] = {}
    for row in rows:
        prev = latest.get(row.account_id)
        if prev is None or row.as_of_date > prev[0]:
            latest[row.account_id] = (row.as_of_date, row.balance)
    return {aid: bal for aid, (_, bal) in latest.items()}


def database_inventory() -> dict[str, Any]:
    with get_session() as session:
        accounts = list(session.scalars(select(Account).order_by(Account.name)).all())
        transactions = list(
            session.scalars(
                select(Transaction)
                .order_by(Transaction.txn_date.desc(), Transaction.id.desc())
                .limit(100)
            ).all()
        )
        snapshots = list(
            session.scalars(
                select(BalanceSnapshot).order_by(
                    BalanceSnapshot.as_of_date.desc(), BalanceSnapshot.account_id
                )
            ).all()
        )
        recurring = list(
            session.scalars(
                select(RecurringItem).order_by(RecurringItem.kind, RecurringItem.name)
            ).all()
        )
        streams = list(
            session.scalars(
                select(IncomeStream).order_by(IncomeStream.category, IncomeStream.name)
            ).all()
        )
        receipts = list(
            session.scalars(
                select(IncomeReceipt)
                .order_by(IncomeReceipt.entry_date.desc(), IncomeReceipt.id.desc())
                .limit(100)
            ).all()
        )
        latest = _latest_balances(session)
        account_names = {a.id: a.name for a in accounts}
        stream_names = {s.id: s.name for s in streams}

        counts = {
            "accounts": len(accounts),
            "assets": sum(1 for a in accounts if a.account_type not in LIABILITY_TYPES),
            "debts": sum(1 for a in accounts if a.account_type in LIABILITY_TYPES),
            "income_streams": len(streams),
            "income_receipts": session.scalar(select(func.count()).select_from(IncomeReceipt))
            or 0,
            "transactions": session.scalar(select(func.count()).select_from(Transaction))
            or 0,
            "snapshot_lines": session.scalar(
                select(func.count()).select_from(BalanceSnapshot)
            )
            or 0,
            "recurring": len(recurring),
        }

        account_rows = [
            {
                "id": a.id,
                "name": a.name,
                "type": ACCOUNT_TYPE_LABELS.get(a.account_type, a.account_type.value),
                "kind": "Debt" if a.account_type in LIABILITY_TYPES else "Asset",
                "provider": a.provider or "",
                "account_number": a.account_number or "",
                "sort_code": a.sort_code or "",
                "interest_rate_pct": a.interest_rate_pct,
                "interest_frequency": INTEREST_FREQUENCY_LABELS.get(
                    a.interest_frequency, ""
                )
                if a.interest_frequency
                else "",
                "access_type": ACCESS_TYPE_LABELS.get(a.access_type, "")
                if a.access_type
                else "",
                "notice_days": a.notice_days,
                "maturity_date": a.maturity_date.isoformat() if a.maturity_date else "",
                "opened_date": a.opened_date.isoformat() if a.opened_date else "",
                "active": a.active,
                "latest_balance": latest.get(a.id),
                "notes": a.notes or "",
            }
            for a in accounts
        ]
        txn_rows = [
            {
                "id": t.id,
                "date": t.txn_date.isoformat(),
                "type": TRANSACTION_TYPE_LABELS.get(t.txn_type, t.txn_type.value),
                "amount": t.amount,
                "account": account_names.get(t.account_id, "—") if t.account_id else "—",
                "description": t.description or "",
            }
            for t in transactions
        ]
        by_date: dict = defaultdict(list)
        for s in snapshots:
            by_date[s.as_of_date].append(
                {
                    "id": s.id,
                    "account": account_names.get(s.account_id, str(s.account_id)),
                    "balance": s.balance,
                }
            )
        snapshot_groups = []
        for as_of, lines in sorted(by_date.items(), key=lambda item: item[0], reverse=True):
            snapshot_groups.append(
                {
                    "date": as_of.isoformat(),
                    "account_count": len(lines),
                    "total": float(sum(line["balance"] for line in lines)),
                    "lines": sorted(lines, key=lambda line: line["account"]),
                }
            )
        counts["snapshots"] = len(snapshot_groups)
        recurring_rows = [
            {
                "id": r.id,
                "name": r.name,
                "kind": RECURRING_KIND_LABELS.get(r.kind, r.kind.value),
                "amount": r.amount,
                "frequency": FREQUENCY_LABELS.get(r.frequency, r.frequency.value),
                "from": account_names.get(r.from_account_id, "—")
                if r.from_account_id
                else "—",
                "to": account_names.get(r.to_account_id, "—") if r.to_account_id else "—",
                "active": r.active,
                "notes": r.notes or "",
            }
            for r in recurring
        ]
        stream_rows = [
            {
                "id": s.id,
                "name": s.name,
                "category": INCOME_CATEGORY_LABELS.get(s.category, s.category.value),
                "cadence": INCOME_CADENCE_LABELS.get(s.cadence, s.cadence.value),
                "pay_frequency": (
                    PAY_FREQUENCY_LABELS.get(s.pay_frequency, s.pay_frequency.value)
                    if s.pay_frequency
                    else "—"
                ),
                "tax_treatment": TAX_TREATMENT_LABELS.get(
                    getattr(s, "tax_treatment", None) or default_tax_treatment(s.category),
                    "—",
                ),
                "tax_band": (
                    TAX_BAND_LABELS.get(s.tax_band, s.tax_band.value)
                    if getattr(s, "tax_band", None)
                    else "—"
                ),
                "expected_amount": s.expected_amount,
                "active": s.active,
                "notes": s.notes or "",
            }
            for s in streams
        ]
        receipt_rows = [
            {
                "id": r.id,
                "date": r.entry_date.isoformat(),
                "source": stream_names.get(r.stream_id, str(r.stream_id)),
                "amount": r.amount,
                "description": r.description or "",
            }
            for r in receipts
        ]

        return {
            "counts": counts,
            "accounts": account_rows,
            "transactions": txn_rows,
            "snapshot_groups": snapshot_groups,
            "recurring": recurring_rows,
            "income_streams": stream_rows,
            "income_receipts": receipt_rows,
        }
