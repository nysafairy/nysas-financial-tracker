"""Portfolio net-worth forecasting from balances, rates, and cashflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from sqlalchemy import select

from finance_app.db.models import (
    ACCOUNT_TYPE_LABELS,
    FORECAST_DEFAULT_ASSUMED_GROWTH_PCT,
    LIABILITY_TYPES,
    PREMIUM_BONDS_ASSUMED_RATE_PCT,
    TAX_EXEMPT_INTEREST_ACCOUNT_TYPES,
    Account,
    AccountType,
    BalanceSnapshot,
    IncomeCadence,
)
from finance_app.db.session import get_session
from finance_app.services import calculators as calc_service
from finance_app.services import income as income_service
from finance_app.services import recurring as recurring_service

AssumptionMode = Literal["overall", "per_account"]


@dataclass
class WhatIfs:
    """Session-only forecast overlays (not persisted)."""

    extra_monthly_saving: float = 0.0
    extra_monthly_spend: float = 0.0
    lump_sum: float = 0.0
    overall_growth_override_pct: float | None = None


@dataclass
class ForecastAssumptions:
    mode: AssumptionMode = "overall"
    overall_growth_pct: float = FORECAST_DEFAULT_ASSUMED_GROWTH_PCT
    per_account_pct: dict[str, float] = field(default_factory=dict)


def _latest_balances(session) -> dict[int, float]:
    rows = session.scalars(select(BalanceSnapshot)).all()
    latest: dict[int, tuple[date, float]] = {}
    for row in rows:
        prev = latest.get(row.account_id)
        if prev is None or row.as_of_date > prev[0]:
            latest[row.account_id] = (row.as_of_date, float(row.balance))
    return {aid: bal for aid, (_, bal) in latest.items()}


def _draft_account_rows() -> list[dict[str, Any]] | None:
    from finance_app.services import draft_session

    state = draft_session.effective_accounts_and_balances()
    if state is None:
        return None
    return list(state["rows"])


def forecast_accounts() -> list[dict[str, Any]]:
    """
    Active accounts with latest balance for the forecast sheet.

    Respects an open draft overlay when present.
    """
    draft_rows = _draft_account_rows()
    if draft_rows is not None:
        out: list[dict[str, Any]] = []
        for row in draft_rows:
            if row.get("balance") is None:
                continue
            try:
                atype = AccountType(row["account_type"])
            except ValueError:
                atype = AccountType.OTHER
            key = (
                f"id:{row['account_id']}"
                if row.get("account_id") is not None
                else f"temp:{row.get('temp_key')}"
            )
            out.append(
                {
                    "key": key,
                    "account_id": row.get("account_id"),
                    "name": row["name"],
                    "account_type": atype.value,
                    "type_label": ACCOUNT_TYPE_LABELS.get(atype, atype.value),
                    "balance": float(row["balance"]),
                    "is_liability": atype in LIABILITY_TYPES,
                    "stored_rate_pct": row.get("interest_rate_pct"),
                }
            )
        return out

    with get_session() as session:
        accounts = list(
            session.scalars(select(Account).where(Account.active.is_(True))).all()
        )
        latest = _latest_balances(session)
        out = []
        for account in accounts:
            balance = latest.get(account.id)
            if balance is None:
                continue
            out.append(
                {
                    "key": f"id:{account.id}",
                    "account_id": account.id,
                    "name": account.name,
                    "account_type": account.account_type.value,
                    "type_label": ACCOUNT_TYPE_LABELS[account.account_type],
                    "balance": float(balance),
                    "is_liability": account.account_type in LIABILITY_TYPES,
                    "stored_rate_pct": account.interest_rate_pct,
                }
            )
        return out


# Account types that use the forecast growth assumption when no stored rate is set.
GROWTH_ASSUMPTION_TYPES = {
    AccountType.SAVINGS_EASY_ACCESS,
    AccountType.SAVINGS_LIMITED_ACCESS,
    AccountType.SAVINGS_REGULAR,
    AccountType.SAVINGS_FIXED_1Y,
    AccountType.SAVINGS_FIXED_2Y,
    AccountType.SAVINGS_FIXED_5Y,
    AccountType.PREMIUM_BONDS,
    AccountType.ISA_CASH,
    AccountType.ISA_STOCKS,
    AccountType.LISA,
    AccountType.IFISA,
    AccountType.GIA,
    AccountType.PENSION_SIP,
    AccountType.PENSION_WORKPLACE,
}


def resolve_annual_rate_pct(
    account: dict[str, Any],
    assumptions: ForecastAssumptions,
    *,
    overall_override_pct: float | None = None,
) -> float:
    """
    Pick the annual % used for an account in the forecast.

    Priority:
    1. Per-account assumption when mode is per_account and a value is set
    2. Stored interest_rate_pct (Premium Bonds fall back to 3.8% if unset)
    3. Overall assumed growth for investment/savings wrappers without a rate
    4. 0% for current/other assets and liabilities without a rate
    """
    key = str(account["key"])
    if assumptions.mode == "per_account" and key in assumptions.per_account_pct:
        return float(assumptions.per_account_pct[key])

    stored = account.get("stored_rate_pct")
    atype_raw = account.get("account_type")
    try:
        atype = AccountType(atype_raw) if atype_raw else AccountType.OTHER
    except ValueError:
        atype = AccountType.OTHER

    if stored is None and atype == AccountType.PREMIUM_BONDS:
        stored = PREMIUM_BONDS_ASSUMED_RATE_PCT
    if stored is not None:
        return float(stored)

    if account.get("is_liability") or atype not in GROWTH_ASSUMPTION_TYPES:
        return 0.0

    overall = (
        float(overall_override_pct)
        if overall_override_pct is not None
        else float(assumptions.overall_growth_pct)
    )
    return overall


def monthly_cashflow_baseline(
    *,
    apply_tax: bool = False,
    assumptions: ForecastAssumptions | None = None,
) -> dict[str, Any]:
    """Fixed income + recurring income − subscriptions (standing orders excluded)."""
    assumptions = assumptions or ForecastAssumptions()
    fixed_income = 0.0
    for stream in income_service.list_streams(active_only=True):
        if stream.cadence == IncomeCadence.VARIABLE:
            continue
        monthly = income_service.monthly_equivalent(stream)
        if monthly:
            fixed_income += float(monthly)

    recurring = recurring_service.recurring_monthly_totals()
    subscriptions = float(recurring.get("subscriptions") or 0.0)
    recurring_income = float(recurring.get("income") or 0.0)
    net = fixed_income + recurring_income - subscriptions

    tax_info: dict[str, Any] | None = None
    if apply_tax:
        tax_info = estimate_forecast_tax(assumptions=assumptions)
        net = net - float(tax_info["monthly_tax"])

    return {
        "fixed_income": fixed_income,
        "recurring_income": recurring_income,
        "subscriptions": subscriptions,
        "net_monthly": net,
        "apply_tax": apply_tax,
        "tax": tax_info,
    }


def estimate_forecast_tax(
    *,
    assumptions: ForecastAssumptions | None = None,
) -> dict[str, Any]:
    """
    Estimate annual England income tax for forecasting.

    Employment/trading/pension/property from stream tax treatments.
    Taxable interest = sum(balance × rate) for accounts outside ISA/LISA/IFISA/
    Premium Bonds. Dividends not estimated from balances.
    """
    assumptions = assumptions or ForecastAssumptions()
    inputs = income_service.annual_tax_inputs_from_streams()
    recorded_bands = list(inputs.get("recorded_tax_bands") or [])
    accounts = forecast_accounts()
    taxable_interest = 0.0
    tax_free_interest = 0.0
    for account in accounts:
        if account.get("is_liability"):
            continue
        try:
            atype = AccountType(account["account_type"])
        except ValueError:
            atype = AccountType.OTHER
        rate = resolve_annual_rate_pct(account, assumptions) / 100.0
        annual_interest = abs(float(account["balance"])) * rate
        if atype in TAX_EXEMPT_INTEREST_ACCOUNT_TYPES:
            tax_free_interest += annual_interest
        else:
            taxable_interest += annual_interest

    estimate = calc_service.estimate_income_tax_england(
        employment=float(inputs["employment"]),
        pension=float(inputs["pension"]),
        property=float(inputs["property"]),
        trading_income=float(inputs["trading_income"]),
        savings_interest=taxable_interest,
        dividends=0.0,
        trust_non_dividend=float(inputs.get("other") or 0.0),
        apply_trading_allowance=float(inputs["trading_income"]) > 0,
    )
    annual_tax = float(estimate["tax"]["total"])
    return {
        "annual_tax": annual_tax,
        "monthly_tax": annual_tax / 12.0,
        "marginal_band": estimate["marginal_band"],
        "recorded_tax_bands": recorded_bands,
        "taxable_interest_assumed": taxable_interest,
        "tax_free_interest_assumed": tax_free_interest,
        "employment": float(inputs["employment"]),
        "estimate": estimate,
    }


def _signed_balances(
    accounts: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], float]]:
    signed: list[tuple[dict[str, Any], float]] = []
    for account in accounts:
        bal = float(account["balance"])
        if account["is_liability"]:
            signed.append((account, -abs(bal)))
        else:
            signed.append((account, bal))
    return signed


def project_series(
    *,
    years: int = 10,
    assumptions: ForecastAssumptions | None = None,
    what_ifs: WhatIfs | None = None,
    apply_tax: bool = False,
) -> dict[str, Any]:
    """
    Monthly compound projection of net worth.

    Returns baseline and (if what-ifs non-zero) adjusted series.
    """
    years = max(1, min(int(years), 40))
    assumptions = assumptions or ForecastAssumptions()
    what_ifs = what_ifs or WhatIfs()
    accounts = forecast_accounts()
    cashflow = monthly_cashflow_baseline(
        apply_tax=apply_tax, assumptions=assumptions
    )
    months = years * 12

    baseline = _run_projection(
        accounts=accounts,
        months=months,
        assumptions=assumptions,
        monthly_net=cashflow["net_monthly"],
        lump_sum=0.0,
        overall_override_pct=None,
    )
    has_what_ifs = any(
        [
            abs(what_ifs.extra_monthly_saving) > 1e-9,
            abs(what_ifs.extra_monthly_spend) > 1e-9,
            abs(what_ifs.lump_sum) > 1e-9,
            what_ifs.overall_growth_override_pct is not None,
        ]
    )
    adjusted = None
    if has_what_ifs:
        adjusted_net = (
            cashflow["net_monthly"]
            + float(what_ifs.extra_monthly_saving)
            - float(what_ifs.extra_monthly_spend)
        )
        adjusted = _run_projection(
            accounts=accounts,
            months=months,
            assumptions=assumptions,
            monthly_net=adjusted_net,
            lump_sum=float(what_ifs.lump_sum),
            overall_override_pct=what_ifs.overall_growth_override_pct,
        )

    rate_rows = []
    for account in accounts:
        rate = resolve_annual_rate_pct(
            account,
            assumptions,
            overall_override_pct=None,
        )
        rate_rows.append(
            {
                "key": account["key"],
                "name": account["name"],
                "account_type": account["account_type"],
                "type_label": account["type_label"],
                "balance": account["balance"],
                "is_liability": account["is_liability"],
                "annual_rate_pct": rate,
                "stored_rate_pct": account.get("stored_rate_pct"),
            }
        )

    end_baseline = baseline["points"][-1]["value"] if baseline["points"] else 0.0
    start = baseline["start_net_worth"]
    result: dict[str, Any] = {
        "years": years,
        "months": months,
        "start_net_worth": start,
        "end_net_worth": end_baseline,
        "total_growth": end_baseline - start,
        "cashflow": cashflow,
        "accounts": rate_rows,
        "assumptions": {
            "mode": assumptions.mode,
            "overall_growth_pct": assumptions.overall_growth_pct,
            "default_growth_pct": FORECAST_DEFAULT_ASSUMED_GROWTH_PCT,
            "premium_bonds_assumed_pct": PREMIUM_BONDS_ASSUMED_RATE_PCT,
            "apply_tax": apply_tax,
        },
        "baseline": baseline["points"],
        "adjusted": adjusted["points"] if adjusted else None,
        "end_adjusted": (
            adjusted["points"][-1]["value"] if adjusted and adjusted["points"] else None
        ),
        "has_what_ifs": has_what_ifs,
    }
    return result


def suggested_account_rate_pct(account: dict[str, Any]) -> float:
    """Initial per-account assumption for the Forecasting UI."""
    stored = account.get("stored_rate_pct")
    atype_raw = account.get("account_type")
    try:
        atype = AccountType(atype_raw) if atype_raw else AccountType.OTHER
    except ValueError:
        atype = AccountType.OTHER
    if stored is not None:
        return float(stored)
    if atype == AccountType.PREMIUM_BONDS:
        return PREMIUM_BONDS_ASSUMED_RATE_PCT
    if account.get("is_liability") or atype not in GROWTH_ASSUMPTION_TYPES:
        return 0.0
    return FORECAST_DEFAULT_ASSUMED_GROWTH_PCT


def _run_projection(
    *,
    accounts: list[dict[str, Any]],
    months: int,
    assumptions: ForecastAssumptions,
    monthly_net: float,
    lump_sum: float,
    overall_override_pct: float | None,
) -> dict[str, Any]:
    signed = _signed_balances(accounts)
    # Synthetic surplus holds income − spend not yet attributed to a real account.
    surplus = float(lump_sum)
    start_nw = sum(bal for _, bal in signed) + surplus

    rates = [
        resolve_annual_rate_pct(
            account,
            assumptions,
            overall_override_pct=overall_override_pct,
        )
        / 100.0
        / 12.0
        for account, _ in signed
    ]

    points: list[dict[str, Any]] = [{"month": 0, "label": "Now", "value": start_nw}]
    balances = [bal for _, bal in signed]

    for month in range(1, months + 1):
        for i, rate in enumerate(rates):
            # Liabilities are negative; a positive rate increases amount owed (more negative).
            balances[i] *= 1.0 + rate
        surplus *= 1.0  # surplus earns no separate rate; added to NW as cash
        surplus += monthly_net
        nw = sum(balances) + surplus
        label = f"Y{month // 12}" if month % 12 == 0 else ""
        points.append({"month": month, "label": label, "value": nw})

    return {"start_net_worth": start_nw, "points": points}
