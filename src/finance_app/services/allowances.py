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
    AllowanceBaseline,
    Transaction,
    TransactionType,
)
from finance_app.db.session import get_session
from finance_app.services.metrics import uk_tax_year_end, uk_tax_year_start

# Keys the user can set as mid-year prior usage.
TRACKED_BASELINE_KEYS = ("adult_isa", "lisa", "pension_annual")


def _load_tables() -> dict[str, Any]:
    path = package_data_dir() / "uk_allowances_2026_27.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def current_tax_year_label() -> str:
    tables = _load_tables()
    return str(tables["tax_year"])


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


def list_baselines(*, tax_year: str | None = None) -> list[AllowanceBaseline]:
    """Return baseline rows, optionally filtered to one tax year."""
    with get_session() as session:
        stmt = select(AllowanceBaseline).order_by(
            AllowanceBaseline.tax_year, AllowanceBaseline.allowance_key
        )
        if tax_year:
            stmt = stmt.where(AllowanceBaseline.tax_year == tax_year)
        return list(session.scalars(stmt).all())


def upsert_baseline(
    *,
    tax_year: str,
    allowance_key: str,
    prior_used: float,
    notes: str | None = None,
) -> None:
    """Upsert a single allowance baseline row (used by CSV import)."""
    if allowance_key not in TRACKED_BASELINE_KEYS:
        raise ValueError(f"Unknown allowance key: {allowance_key}")
    amount = float(prior_used or 0)
    if amount < 0:
        raise ValueError(f"{allowance_key} prior usage cannot be negative")
    with get_session() as session:
        existing = session.scalar(
            select(AllowanceBaseline).where(
                AllowanceBaseline.tax_year == tax_year,
                AllowanceBaseline.allowance_key == allowance_key,
            )
        )
        if amount <= 0:
            if existing is not None:
                session.delete(existing)
            return
        if existing is not None:
            existing.prior_used = amount
            if notes is not None:
                existing.notes = notes
        else:
            session.add(
                AllowanceBaseline(
                    tax_year=tax_year,
                    allowance_key=allowance_key,
                    prior_used=amount,
                    notes=notes,
                )
            )


def get_baselines(tax_year: str | None = None) -> dict[str, float]:
    """Return prior_used amounts keyed by allowance_key for the tax year."""
    year = tax_year or current_tax_year_label()
    with get_session() as session:
        rows = session.scalars(
            select(AllowanceBaseline).where(AllowanceBaseline.tax_year == year)
        ).all()
        return {row.allowance_key: float(row.prior_used) for row in rows}


def set_baselines(
    values: dict[str, float],
    *,
    tax_year: str | None = None,
    notes: str | None = None,
) -> dict[str, float]:
    """
    Upsert prior-usage baselines for tracked allowances in the given tax year.

    Keys omitted from values are left unchanged. Pass 0 to clear a key.
    """
    year = tax_year or current_tax_year_label()
    with get_session() as session:
        existing = {
            row.allowance_key: row
            for row in session.scalars(
                select(AllowanceBaseline).where(AllowanceBaseline.tax_year == year)
            ).all()
        }
        for key, raw in values.items():
            if key not in TRACKED_BASELINE_KEYS:
                raise ValueError(f"Unknown allowance key: {key}")
            amount = float(raw or 0)
            if amount < 0:
                raise ValueError(f"{key} prior usage cannot be negative")
            if amount <= 0:
                if key in existing:
                    session.delete(existing[key])
                continue
            if key in existing:
                existing[key].prior_used = amount
                if notes is not None:
                    existing[key].notes = notes
            else:
                session.add(
                    AllowanceBaseline(
                        tax_year=year,
                        allowance_key=key,
                        prior_used=amount,
                        notes=notes,
                    )
                )
    return get_baselines(year)


def allowance_usage() -> dict[str, Any]:
    tables = _load_tables()
    limits = tables["allowances"]
    by_type = _contributions_by_account_type()
    baselines = get_baselines(tables["tax_year"])

    lisa_from_txns = by_type.get(AccountType.LISA, 0.0)
    adult_from_txns = sum(by_type.get(t, 0.0) for t in ADULT_ISA_TYPES)
    pension_from_txns = by_type.get(AccountType.PENSION_SIP, 0.0) + by_type.get(
        AccountType.PENSION_WORKPLACE, 0.0
    )

    lisa_prior = baselines.get("lisa", 0.0)
    adult_prior = baselines.get("adult_isa", 0.0)
    pension_prior = baselines.get("pension_annual", 0.0)

    lisa_used = lisa_prior + lisa_from_txns
    adult_isa_used = adult_prior + adult_from_txns
    pension_used = pension_prior + pension_from_txns

    lisa_limit = float(limits["lisa"]["limit"])
    bonus_rate = float(limits["lisa"]["bonus_rate"])
    lisa_bonus_earned = min(lisa_used, lisa_limit) * bonus_rate

    def pack(
        key: str,
        used: float,
        *,
        from_txns: float = 0.0,
        prior: float = 0.0,
        extra: dict | None = None,
    ) -> dict[str, Any]:
        spec = limits[key]
        limit = float(spec["limit"])
        remaining = max(0.0, limit - used)
        row = {
            "key": key,
            "label": spec["label"],
            "limit": limit,
            "used": used,
            "from_transactions": from_txns,
            "prior_used": prior,
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
        "baselines": baselines,
        "items": [
            pack(
                "adult_isa",
                adult_isa_used,
                from_txns=adult_from_txns,
                prior=adult_prior,
            ),
            pack(
                "lisa",
                lisa_used,
                from_txns=lisa_from_txns,
                prior=lisa_prior,
                extra={
                    "bonus_rate": bonus_rate,
                    "bonus_earned_estimate": lisa_bonus_earned,
                    "max_bonus": float(limits["lisa"]["max_bonus"]),
                },
            ),
            pack(
                "pension_annual",
                pension_used,
                from_txns=pension_from_txns,
                prior=pension_prior,
            ),
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
