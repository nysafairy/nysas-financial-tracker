"""UK tax-year allowance usage (ISA, LISA, pension, etc.)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from finance_app.config import package_data_dir
from finance_app.db.models import (
    ADULT_ISA_TYPES,
    Account,
    AccountType,
    Transaction,
    TransactionType,
)
from finance_app.db.session import get_session
from finance_app.services.metrics import uk_tax_year_end, uk_tax_year_start


def _load_tables() -> dict[str, Any]:
    path = package_data_dir() / "uk_allowances_2026_27.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _contributions_by_account_type() -> dict[AccountType, float]:
    start = uk_tax_year_start()
    end = uk_tax_year_end()
    with get_session() as session:
        accounts = {a.id: a for a in session.scalars(select(Account)).all()}
        rows = session.scalars(
            select(Transaction).where(
                Transaction.txn_date >= start,
                Transaction.txn_date <= end,
                Transaction.txn_type == TransactionType.CONTRIBUTION,
            )
        ).all()
        totals: dict[AccountType, float] = {}
        for row in rows:
            if row.account_id is None:
                continue
            account = accounts.get(row.account_id)
            if account is None:
                continue
            totals[account.account_type] = (
                totals.get(account.account_type, 0.0) + float(row.amount)
            )
        return totals


def allowance_usage() -> dict[str, Any]:
    tables = _load_tables()
    limits = tables["allowances"]
    by_type = _contributions_by_account_type()

    lisa_used = by_type.get(AccountType.LISA, 0.0)
    adult_isa_used = sum(by_type.get(t, 0.0) for t in ADULT_ISA_TYPES)
    junior_used = by_type.get(AccountType.JUNIOR_ISA, 0.0)
    pension_used = by_type.get(AccountType.PENSION_SIP, 0.0) + by_type.get(
        AccountType.PENSION_WORKPLACE, 0.0
    )

    lisa_limit = float(limits["lisa"]["limit"])
    adult_limit = float(limits["adult_isa"]["limit"])
    bonus_rate = float(limits["lisa"]["bonus_rate"])
    lisa_bonus_earned = min(lisa_used, lisa_limit) * bonus_rate

    def pack(key: str, used: float, *, extra: dict | None = None) -> dict[str, Any]:
        spec = limits[key]
        limit = float(spec["limit"])
        remaining = max(0.0, limit - used)
        row = {
            "key": key,
            "label": spec["label"],
            "limit": limit,
            "used": used,
            "remaining": remaining,
            "pct": min(100.0, (used / limit * 100.0) if limit else 0.0),
            "notes": spec.get("notes", ""),
        }
        if extra:
            row.update(extra)
        return row

    return {
        "tax_year": tables["tax_year"],
        "notes": tables.get("source_notes", []),
        "items": [
            pack("adult_isa", adult_isa_used),
            pack(
                "lisa",
                lisa_used,
                extra={
                    "bonus_rate": bonus_rate,
                    "bonus_earned_estimate": lisa_bonus_earned,
                    "max_bonus": float(limits["lisa"]["max_bonus"]),
                },
            ),
            pack("junior_isa", junior_used),
            pack("pension_annual", pension_used),
            {
                **pack("dividend_allowance", 0.0),
                "used": None,
                "remaining": None,
                "pct": None,
                "tracking": "reference_only",
                "notes": limits["dividend_allowance"]["notes"]
                + " Usage is estimated in Tax & tools, not from contributions.",
            },
            {
                **pack("capital_gains", 0.0),
                "used": None,
                "remaining": None,
                "pct": None,
                "tracking": "reference_only",
                "notes": limits["capital_gains"]["notes"],
            },
        ],
    }
