"""Income streams, pay-rate history, and receipts."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from finance_app.db.models import (
    INCOME_CADENCE_LABELS,
    INCOME_CATEGORY_LABELS,
    IncomeCadence,
    IncomeCategory,
    IncomeRatePeriod,
    IncomeReceipt,
    IncomeStream,
    Transaction,
    TransactionType,
)
from finance_app.db.session import get_session
from finance_app.services.metrics import uk_tax_year_end, uk_tax_year_start


def list_streams(*, active_only: bool = False) -> list[IncomeStream]:
    with get_session() as session:
        stmt = select(IncomeStream).order_by(IncomeStream.category, IncomeStream.name)
        if active_only:
            stmt = stmt.where(IncomeStream.active.is_(True))
        return list(session.scalars(stmt).all())


def _to_annual(amount: float, cadence: IncomeCadence) -> float:
    if cadence == IncomeCadence.FIXED_MONTHLY:
        return float(amount) * 12.0
    return float(amount)


def create_stream(
    name: str,
    category: IncomeCategory | str,
    cadence: IncomeCadence | str,
    *,
    expected_amount: float | None = None,
    notes: str | None = None,
    effective_from: date | None = None,
) -> IncomeStream:
    if isinstance(category, str):
        category = IncomeCategory(category)
    if isinstance(cadence, str):
        cadence = IncomeCadence(cadence)
    with get_session() as session:
        stream = IncomeStream(
            name=name.strip(),
            category=category,
            cadence=cadence,
            expected_amount=float(expected_amount) if expected_amount is not None else None,
            notes=notes,
            active=True,
        )
        session.add(stream)
        session.flush()
        if (
            expected_amount is not None
            and cadence != IncomeCadence.VARIABLE
        ):
            session.add(
                IncomeRatePeriod(
                    stream_id=stream.id,
                    effective_from=effective_from or uk_tax_year_start(),
                    annual_amount=_to_annual(float(expected_amount), cadence),
                    notes="Initial rate",
                )
            )
        session.refresh(stream)
        session.expunge(stream)
        return stream


def record_pay_change(
    stream_id: int,
    *,
    new_amount: float,
    effective_from: date,
    as_monthly: bool | None = None,
    notes: str | None = None,
) -> None:
    """
    Record a mid-role salary/pay change.

    Updates the stream's current expected_amount and appends a dated rate period
    so tax-year pro-rata can split old vs new pay.
    """
    with get_session() as session:
        stream = session.get(IncomeStream, stream_id)
        if stream is None:
            raise ValueError("Income stream not found")
        if stream.cadence == IncomeCadence.VARIABLE:
            raise ValueError("Pay changes apply to fixed yearly/monthly sources only")

        monthly = (
            as_monthly
            if as_monthly is not None
            else stream.cadence == IncomeCadence.FIXED_MONTHLY
        )
        cadence = IncomeCadence.FIXED_MONTHLY if monthly else IncomeCadence.FIXED_ANNUAL
        annual = _to_annual(float(new_amount), cadence)

        stream.expected_amount = float(new_amount)
        stream.cadence = cadence
        session.add(
            IncomeRatePeriod(
                stream_id=stream.id,
                effective_from=effective_from,
                annual_amount=annual,
                notes=notes or "Pay change",
            )
        )


def list_rate_periods(stream_id: int) -> list[IncomeRatePeriod]:
    with get_session() as session:
        stmt = (
            select(IncomeRatePeriod)
            .where(IncomeRatePeriod.stream_id == stream_id)
            .order_by(IncomeRatePeriod.effective_from.desc())
        )
        return list(session.scalars(stmt).all())


def delete_stream(stream_id: int) -> None:
    with get_session() as session:
        stream = session.get(IncomeStream, stream_id)
        if stream is None:
            return
        for receipt in list(stream.receipts):
            session.delete(receipt)
        for period in list(stream.rate_periods):
            session.delete(period)
        session.delete(stream)


def list_receipts(limit: int = 100) -> list[IncomeReceipt]:
    with get_session() as session:
        stmt = (
            select(IncomeReceipt)
            .order_by(IncomeReceipt.entry_date.desc(), IncomeReceipt.id.desc())
            .limit(limit)
        )
        return list(session.scalars(stmt).all())


def add_receipt(
    stream_id: int,
    amount: float,
    entry_date: date,
    *,
    description: str | None = None,
) -> IncomeReceipt:
    with get_session() as session:
        if session.get(IncomeStream, stream_id) is None:
            raise ValueError("Income stream not found")
        receipt = IncomeReceipt(
            stream_id=stream_id,
            amount=float(amount),
            entry_date=entry_date,
            description=description,
        )
        session.add(receipt)
        session.flush()
        session.refresh(receipt)
        session.expunge(receipt)
        return receipt


def delete_receipt(receipt_id: int) -> None:
    with get_session() as session:
        receipt = session.get(IncomeReceipt, receipt_id)
        if receipt is None:
            return
        session.delete(receipt)


def _annualise_expected(stream: IncomeStream) -> float:
    if stream.expected_amount is None:
        return 0.0
    return _to_annual(float(stream.expected_amount), stream.cadence)


def _pro_rata_with_rate_history(
    stream: IncomeStream,
    periods: list[IncomeRatePeriod],
    on: date,
) -> float:
    """Pro-rata fixed pay across dated rate periods within the UK tax year."""
    start = uk_tax_year_start(on)
    end = min(on, uk_tax_year_end(on))
    if end < start:
        return 0.0

    year_days = (uk_tax_year_end(on) - start).days + 1
    ordered = sorted(periods, key=lambda p: p.effective_from)

    # Fallback: single current rate for whole year-to-date.
    if not ordered:
        annual = _annualise_expected(stream)
        elapsed = (end - start).days + 1
        return annual * (elapsed / year_days) if year_days else 0.0

    # Find rate in force at tax-year start (latest period on or before start).
    def rate_on(day: date) -> float:
        applicable = [p for p in ordered if p.effective_from <= day]
        if applicable:
            return float(applicable[-1].annual_amount)
        # Before first period: use first period's rate from its start only
        return 0.0

    boundaries = {start, end + timedelta(days=1)}
    for period in ordered:
        if start < period.effective_from <= end:
            boundaries.add(period.effective_from)
    points = sorted(boundaries)

    total = 0.0
    for i in range(len(points) - 1):
        seg_start = points[i]
        seg_end_exclusive = points[i + 1]
        days = (seg_end_exclusive - seg_start).days
        if days <= 0:
            continue
        annual = rate_on(seg_start)
        total += annual * (days / year_days)
    return total


def income_by_source(on: date | None = None) -> dict[str, Any]:
    """
    Combine stream expectations/receipts with investment-style transaction totals.

    Fixed streams use dated rate periods (pay rises) for tax-year pro-rata.
    Variable streams use receipt totals only.
    """
    start = uk_tax_year_start(on)
    end = uk_tax_year_end(on)
    today = on or date.today()

    with get_session() as session:
        streams = list(
            session.scalars(select(IncomeStream).where(IncomeStream.active.is_(True))).all()
        )
        receipts = list(
            session.scalars(
                select(IncomeReceipt).where(
                    IncomeReceipt.entry_date >= start,
                    IncomeReceipt.entry_date <= end,
                )
            ).all()
        )
        periods = list(session.scalars(select(IncomeRatePeriod)).all())
        periods_by_stream: dict[int, list[IncomeRatePeriod]] = {}
        for period in periods:
            periods_by_stream.setdefault(period.stream_id, []).append(period)

        receipt_totals: dict[int, float] = {}
        for r in receipts:
            receipt_totals[r.stream_id] = receipt_totals.get(r.stream_id, 0.0) + r.amount

        sources: list[dict[str, Any]] = []
        by_category: dict[str, float] = {}

        for stream in streams:
            received = receipt_totals.get(stream.id, 0.0)
            if stream.cadence == IncomeCadence.VARIABLE:
                amount = received
                basis = "receipts"
                expected_annual = None
            else:
                amount = _pro_rata_with_rate_history(
                    stream, periods_by_stream.get(stream.id, []), today
                )
                basis = "expected_pro_rata"
                expected_annual = _annualise_expected(stream)

            cat_label = INCOME_CATEGORY_LABELS[stream.category]
            sources.append(
                {
                    "stream_id": stream.id,
                    "name": stream.name,
                    "category": stream.category.value,
                    "category_label": cat_label,
                    "cadence": stream.cadence.value,
                    "cadence_label": INCOME_CADENCE_LABELS[stream.cadence],
                    "expected_annual": expected_annual,
                    "ytd_amount": amount,
                    "basis": basis,
                }
            )
            by_category[cat_label] = by_category.get(cat_label, 0.0) + amount

        txns = session.scalars(
            select(Transaction).where(
                Transaction.txn_date >= start,
                Transaction.txn_date <= end,
                Transaction.txn_type.in_(
                    [TransactionType.INTEREST, TransactionType.DIVIDEND]
                ),
            )
        ).all()
        interest = sum(t.amount for t in txns if t.txn_type == TransactionType.INTEREST)
        dividends = sum(t.amount for t in txns if t.txn_type == TransactionType.DIVIDEND)
        if interest:
            sources.append(
                {
                    "stream_id": None,
                    "name": "Savings interest",
                    "category": IncomeCategory.INVESTMENT.value,
                    "category_label": INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT],
                    "cadence": IncomeCadence.VARIABLE.value,
                    "cadence_label": INCOME_CADENCE_LABELS[IncomeCadence.VARIABLE],
                    "expected_annual": None,
                    "ytd_amount": interest,
                    "basis": "ledger",
                }
            )
            label = INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT]
            by_category[label] = by_category.get(label, 0.0) + interest
        if dividends:
            sources.append(
                {
                    "stream_id": None,
                    "name": "Dividends",
                    "category": IncomeCategory.INVESTMENT.value,
                    "category_label": INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT],
                    "cadence": IncomeCadence.VARIABLE.value,
                    "cadence_label": INCOME_CADENCE_LABELS[IncomeCadence.VARIABLE],
                    "expected_annual": None,
                    "ytd_amount": dividends,
                    "basis": "ledger",
                }
            )
            label = INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT]
            by_category[label] = by_category.get(label, 0.0) + dividends

    total = sum(s["ytd_amount"] for s in sources)
    return {
        "sources": sorted(sources, key=lambda s: s["ytd_amount"], reverse=True),
        "by_category": [
            {"label": label, "value": value}
            for label, value in sorted(by_category.items(), key=lambda x: -x[1])
        ],
        "total_ytd": total,
        "tax_year_start": start.isoformat(),
        "tax_year_end": end.isoformat(),
    }


def salary_annual_for_tax() -> float:
    """Current annual salary rates (latest expected), for tax tool prefills."""
    total = 0.0
    for stream in list_streams(active_only=True):
        if stream.category == IncomeCategory.SALARY:
            total += _annualise_expected(stream)
    return total
