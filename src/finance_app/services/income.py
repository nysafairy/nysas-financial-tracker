"""Income streams, pay-rate history, and receipts."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from finance_app.db.models import (
    INCOME_CADENCE_LABELS,
    INCOME_CATEGORY_LABELS,
    PAY_FREQUENCY_LABELS,
    TAX_BAND_LABELS,
    TAX_TREATMENT_LABELS,
    IncomeCadence,
    IncomeCategory,
    IncomeRatePeriod,
    IncomeReceipt,
    IncomeStream,
    PayFrequency,
    TaxBand,
    TaxTreatment,
    Transaction,
    TransactionType,
    default_tax_treatment,
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
    pay_frequency: PayFrequency | str | None = None,
    tax_treatment: TaxTreatment | str | None = None,
    tax_band: TaxBand | str | None = None,
    notes: str | None = None,
    effective_from: date | None = None,
) -> IncomeStream:
    if isinstance(category, str):
        category = IncomeCategory(category)
    if isinstance(cadence, str):
        cadence = IncomeCadence(cadence)
    if isinstance(pay_frequency, str) and pay_frequency:
        pay_frequency = PayFrequency(pay_frequency)
    elif not pay_frequency:
        pay_frequency = None
    if isinstance(tax_treatment, str) and tax_treatment:
        tax_treatment = TaxTreatment(tax_treatment)
    elif not tax_treatment:
        tax_treatment = default_tax_treatment(category)
    if isinstance(tax_band, str) and tax_band:
        tax_band = TaxBand(tax_band)
    elif not tax_band:
        tax_band = None
    if cadence != IncomeCadence.VARIABLE and pay_frequency is None:
        pay_frequency = PayFrequency.MONTHLY
    if cadence == IncomeCadence.VARIABLE:
        pay_frequency = None
    with get_session() as session:
        stream = IncomeStream(
            name=name.strip(),
            category=category,
            cadence=cadence,
            expected_amount=float(expected_amount) if expected_amount is not None else None,
            pay_frequency=pay_frequency,
            tax_treatment=tax_treatment,
            tax_band=tax_band,
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


def monthly_equivalent(stream: IncomeStream) -> float | None:
    """
    Approximate monthly cash from a fixed stream.

    Expected amount unit (yearly/monthly cadence) drives annualisation;
    pay_frequency is stored for payday scheduling. Monthly planning totals
    use annual / 12 regardless of payday cadence.
    """
    if stream.cadence == IncomeCadence.VARIABLE:
        return None
    annual = _annualise_expected(stream)
    if annual <= 0:
        return 0.0
    return annual / 12.0


def payday_amount(stream: IncomeStream) -> float | None:
    """Amount typically received on each payday for a fixed stream."""
    if stream.cadence == IncomeCadence.VARIABLE:
        return None
    annual = _annualise_expected(stream)
    if annual <= 0:
        return 0.0
    freq = stream.pay_frequency or PayFrequency.MONTHLY
    divisors = {
        PayFrequency.WEEKLY: 52.0,
        PayFrequency.BI_WEEKLY: 26.0,
        PayFrequency.FOUR_WEEKLY: 13.0,
        PayFrequency.MONTHLY: 12.0,
        PayFrequency.YEARLY: 1.0,
    }
    return annual / divisors[freq]


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
                    "pay_frequency": (
                        stream.pay_frequency.value if stream.pay_frequency else None
                    ),
                    "pay_frequency_label": (
                        PAY_FREQUENCY_LABELS[stream.pay_frequency]
                        if stream.pay_frequency
                        else None
                    ),
                    "expected_annual": expected_annual,
                    "monthly_equivalent": (
                        monthly_equivalent(stream)
                        if stream.cadence != IncomeCadence.VARIABLE
                        else None
                    ),
                    "ytd_amount": amount,
                    "basis": basis,
                }
            )
            by_category[cat_label] = by_category.get(cat_label, 0.0) + amount

        from finance_app.db.models import (
            ACCOUNT_TYPE_LABELS,
            TAX_EXEMPT_INTEREST_ACCOUNT_TYPES,
            Account,
        )

        accounts = {
            a.id: a for a in session.scalars(select(Account)).all()
        }
        txns = session.scalars(
            select(Transaction).where(
                Transaction.txn_date >= start,
                Transaction.txn_date <= end,
                Transaction.txn_type.in_(
                    [TransactionType.INTEREST, TransactionType.DIVIDEND]
                ),
            )
        ).all()
        taxable_interest = 0.0
        tax_free_interest = 0.0
        interest_lines: list[dict[str, Any]] = []
        for t in txns:
            if t.txn_type != TransactionType.INTEREST:
                continue
            account = accounts.get(t.account_id) if t.account_id else None
            exempt = (
                account is not None
                and account.account_type in TAX_EXEMPT_INTEREST_ACCOUNT_TYPES
            )
            if exempt:
                tax_free_interest += float(t.amount)
            else:
                taxable_interest += float(t.amount)
            interest_lines.append(
                {
                    "date": t.txn_date.isoformat(),
                    "account": account.name if account else "—",
                    "account_type": (
                        ACCOUNT_TYPE_LABELS[account.account_type]
                        if account
                        else "—"
                    ),
                    "amount": float(t.amount),
                    "taxable": not exempt,
                    "description": t.description or "",
                }
            )
        dividends = sum(
            float(t.amount) for t in txns if t.txn_type == TransactionType.DIVIDEND
        )
        interest = taxable_interest + tax_free_interest
        if taxable_interest:
            sources.append(
                {
                    "stream_id": None,
                    "name": "Taxable savings interest",
                    "category": IncomeCategory.INVESTMENT.value,
                    "category_label": INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT],
                    "cadence": IncomeCadence.VARIABLE.value,
                    "cadence_label": INCOME_CADENCE_LABELS[IncomeCadence.VARIABLE],
                    "pay_frequency": None,
                    "pay_frequency_label": None,
                    "expected_annual": None,
                    "monthly_equivalent": None,
                    "ytd_amount": taxable_interest,
                    "basis": "ledger",
                }
            )
            label = INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT]
            by_category[label] = by_category.get(label, 0.0) + taxable_interest
        if tax_free_interest:
            sources.append(
                {
                    "stream_id": None,
                    "name": "Tax-free interest (ISA / LISA / Premium Bonds)",
                    "category": IncomeCategory.INVESTMENT.value,
                    "category_label": INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT],
                    "cadence": IncomeCadence.VARIABLE.value,
                    "cadence_label": INCOME_CADENCE_LABELS[IncomeCadence.VARIABLE],
                    "pay_frequency": None,
                    "pay_frequency_label": None,
                    "expected_annual": None,
                    "monthly_equivalent": None,
                    "ytd_amount": tax_free_interest,
                    "basis": "ledger_tax_free",
                }
            )
            label = INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT]
            by_category[label] = by_category.get(label, 0.0) + tax_free_interest
        if dividends:
            sources.append(
                {
                    "stream_id": None,
                    "name": "Dividends",
                    "category": IncomeCategory.INVESTMENT.value,
                    "category_label": INCOME_CATEGORY_LABELS[IncomeCategory.INVESTMENT],
                    "cadence": IncomeCadence.VARIABLE.value,
                    "cadence_label": INCOME_CADENCE_LABELS[IncomeCadence.VARIABLE],
                    "pay_frequency": None,
                    "pay_frequency_label": None,
                    "expected_annual": None,
                    "monthly_equivalent": None,
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
        "taxable_interest": taxable_interest,
        "tax_free_interest": tax_free_interest,
        "dividends": dividends,
        "interest_lines": interest_lines,
        "tax_year_start": start.isoformat(),
        "tax_year_end": end.isoformat(),
    }


def salary_annual_for_tax() -> float:
    """Current annual salary / employment rates (latest expected), for tax tool prefills."""
    total = 0.0
    for stream in list_streams(active_only=True):
        treatment = getattr(stream, "tax_treatment", None) or default_tax_treatment(
            stream.category
        )
        if (
            stream.category == IncomeCategory.SALARY
            or treatment == TaxTreatment.EMPLOYMENT
        ):
            total += _annualise_expected(stream)
    return total


def annual_tax_inputs_from_streams() -> dict[str, Any]:
    """Annualise active streams into England tax calculator buckets."""
    buckets: dict[str, Any] = {
        "employment": 0.0,
        "pension": 0.0,
        "property": 0.0,
        "trading_income": 0.0,
        "other": 0.0,
        "recorded_tax_bands": [],
    }
    for stream in list_streams(active_only=True):
        annual = (
            _annualise_expected(stream)
            if stream.cadence != IncomeCadence.VARIABLE
            else 0.0
        )
        treatment = getattr(stream, "tax_treatment", None) or default_tax_treatment(
            stream.category
        )
        if stream.tax_band is not None:
            buckets["recorded_tax_bands"].append(TAX_BAND_LABELS[stream.tax_band])
        if treatment == TaxTreatment.EXEMPT or annual <= 0:
            continue
        if treatment == TaxTreatment.EMPLOYMENT:
            buckets["employment"] += annual
        elif treatment == TaxTreatment.PENSION:
            buckets["pension"] += annual
        elif treatment == TaxTreatment.PROPERTY:
            buckets["property"] += annual
        elif treatment == TaxTreatment.TRADING:
            buckets["trading_income"] += annual
        else:
            buckets["other"] += annual
    return buckets


def income_report(
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    """
    Actual income report for a date range (default: UK tax year to date).

    Uses pro-rated fixed pay through `end`, receipts in range, and ledger
    interest/dividends in range (not forecasted interest).
    """
    today = date.today()
    start = start or uk_tax_year_start(today)
    end = end or today
    if end < start:
        start, end = end, start

    # Reuse income_by_source logic by temporarily using end as "on" for tax year
    # bounds, then re-filter — simpler to build directly for arbitrary ranges.
    from finance_app.db.models import (
        ACCOUNT_TYPE_LABELS,
        TAX_EXEMPT_INTEREST_ACCOUNT_TYPES,
        Account,
    )
    from finance_app.services import calculators as calc_service

    with get_session() as session:
        streams = list(
            session.scalars(select(IncomeStream).where(IncomeStream.active.is_(True))).all()
        )
        periods = list(session.scalars(select(IncomeRatePeriod)).all())
        periods_by_stream: dict[int, list[IncomeRatePeriod]] = {}
        for period in periods:
            periods_by_stream.setdefault(period.stream_id, []).append(period)

        receipts = list(
            session.scalars(
                select(IncomeReceipt).where(
                    IncomeReceipt.entry_date >= start,
                    IncomeReceipt.entry_date <= end,
                )
            ).all()
        )
        receipt_totals: dict[int, float] = {}
        receipt_rows: list[dict[str, Any]] = []
        stream_names = {s.id: s.name for s in streams}
        for r in receipts:
            receipt_totals[r.stream_id] = receipt_totals.get(r.stream_id, 0.0) + r.amount
            receipt_rows.append(
                {
                    "date": r.entry_date.isoformat(),
                    "source": stream_names.get(r.stream_id, str(r.stream_id)),
                    "amount": float(r.amount),
                    "description": r.description or "",
                }
            )

        source_rows: list[dict[str, Any]] = []
        for stream in streams:
            treatment = stream.tax_treatment or default_tax_treatment(stream.category)
            if stream.cadence == IncomeCadence.VARIABLE:
                amount = receipt_totals.get(stream.id, 0.0)
                basis = "receipts"
                expected_annual = None
            else:
                # Pro-rate from period start through end (not full tax year).
                amount = _pro_rata_range(
                    stream,
                    periods_by_stream.get(stream.id, []),
                    start,
                    end,
                )
                basis = "expected_pro_rata"
                expected_annual = _annualise_expected(stream)
            source_rows.append(
                {
                    "name": stream.name,
                    "category": INCOME_CATEGORY_LABELS[stream.category],
                    "tax_treatment": TAX_TREATMENT_LABELS[treatment],
                    "tax_band": (
                        TAX_BAND_LABELS[stream.tax_band] if stream.tax_band else "—"
                    ),
                    "amount": amount,
                    "basis": basis,
                    "expected_annual": expected_annual,
                }
            )

        accounts = {a.id: a for a in session.scalars(select(Account)).all()}
        txns = list(
            session.scalars(
                select(Transaction).where(
                    Transaction.txn_date >= start,
                    Transaction.txn_date <= end,
                    Transaction.txn_type.in_(
                        [TransactionType.INTEREST, TransactionType.DIVIDEND]
                    ),
                )
            ).all()
        )
        interest_rows: list[dict[str, Any]] = []
        taxable_interest = 0.0
        tax_free_interest = 0.0
        dividends = 0.0
        for t in txns:
            account = accounts.get(t.account_id) if t.account_id else None
            if t.txn_type == TransactionType.DIVIDEND:
                dividends += float(t.amount)
                interest_rows.append(
                    {
                        "date": t.txn_date.isoformat(),
                        "kind": "Dividend",
                        "account": account.name if account else "—",
                        "type": (
                            ACCOUNT_TYPE_LABELS[account.account_type]
                            if account
                            else "—"
                        ),
                        "amount": float(t.amount),
                        "taxable": True,
                        "description": t.description or "",
                    }
                )
                continue
            exempt = (
                account is not None
                and account.account_type in TAX_EXEMPT_INTEREST_ACCOUNT_TYPES
            )
            if exempt:
                tax_free_interest += float(t.amount)
            else:
                taxable_interest += float(t.amount)
            interest_rows.append(
                {
                    "date": t.txn_date.isoformat(),
                    "kind": "Interest",
                    "account": account.name if account else "—",
                    "type": (
                        ACCOUNT_TYPE_LABELS[account.account_type] if account else "—"
                    ),
                    "amount": float(t.amount),
                    "taxable": not exempt,
                    "description": t.description or "",
                }
            )

    stream_total = sum(r["amount"] for r in source_rows)
    gross = stream_total + taxable_interest + tax_free_interest + dividends

    # Annualise period figures to full-year estimate for tax band display, or
    # run tax on period-scaled amounts * (365/days) for estimate — use
    # annualised stream rates + period interest annualised.
    days = max(1, (end - start).days + 1)
    scale = 365.0 / days
    tax_inputs = annual_tax_inputs_from_streams()
    recorded_bands = tax_inputs.pop("recorded_tax_bands", [])
    tax_estimate = calc_service.estimate_income_tax_england(
        employment=float(tax_inputs["employment"]),
        pension=float(tax_inputs["pension"]),
        property=float(tax_inputs["property"]),
        trading_income=float(tax_inputs["trading_income"]),
        savings_interest=taxable_interest * scale,
        dividends=dividends * scale,
        trust_non_dividend=float(tax_inputs.get("other") or 0.0),
        apply_trading_allowance=float(tax_inputs["trading_income"]) > 0,
    )
    # Scale tax estimate back to the report window for "tax in period" view.
    period_tax = float(tax_estimate["tax"]["total"]) / scale

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "sources": source_rows,
        "receipts": sorted(receipt_rows, key=lambda r: r["date"], reverse=True),
        "interest_and_dividends": sorted(
            interest_rows, key=lambda r: r["date"], reverse=True
        ),
        "totals": {
            "streams": stream_total,
            "taxable_interest": taxable_interest,
            "tax_free_interest": tax_free_interest,
            "dividends": dividends,
            "gross": gross,
            "estimated_tax_in_period": period_tax,
            "estimated_net_in_period": gross - period_tax,
        },
        "tax_estimate_annualised": tax_estimate,
        "recorded_tax_bands": recorded_bands,
        "notes": [
            "Amounts are actuals for the selected window (pro-rated fixed pay, "
            "logged receipts, and ledger interest/dividends).",
            "ISA, LISA, IFISA, and Premium Bonds interest/prizes are treated as tax-free.",
            "Estimated tax uses England 2026/27 rules; National Insurance is not included.",
        ],
    }


def _pro_rata_range(
    stream: IncomeStream,
    periods: list[IncomeRatePeriod],
    start: date,
    end: date,
) -> float:
    """Pro-rate fixed stream across an arbitrary inclusive date range."""
    if end < start:
        return 0.0
    # Reuse day-weighted logic by shifting the "today" window.
    # Build rate map then walk days from start to end inclusive.
    sorted_periods = sorted(periods, key=lambda p: p.effective_from)
    fallback = _annualise_expected(stream)

    def rate_on(day: date) -> float:
        applicable = [p for p in sorted_periods if p.effective_from <= day]
        if applicable:
            return float(applicable[-1].annual_amount)
        return fallback

    if not sorted_periods and fallback <= 0:
        return 0.0

    # Segment approach matching _pro_rata_with_rate_history
    year_days = 365.25
    points = [start]
    for p in sorted_periods:
        if start < p.effective_from <= end:
            points.append(p.effective_from)
    points.append(end + timedelta(days=1))
    total = 0.0
    for i in range(len(points) - 1):
        seg_start = points[i]
        seg_end_exclusive = points[i + 1]
        days = (seg_end_exclusive - seg_start).days
        if days <= 0:
            continue
        total += rate_on(seg_start) * (days / year_days)
    return total
