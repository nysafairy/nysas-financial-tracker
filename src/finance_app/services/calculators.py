"""England tax and interest calculators (2026/27)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finance_app.config import package_data_dir


def _load_tax_tables() -> dict[str, Any]:
    path = package_data_dir() / "uk_tax_england.json"
    legacy = package_data_dir() / "uk_tax_england.placeholder.json"
    target = path if path.exists() else legacy
    with target.open(encoding="utf-8") as fh:
        return json.load(fh)


def project_interest(
    principal: float,
    annual_rate_pct: float,
    years: float,
    *,
    compound: bool = True,
) -> dict[str, Any]:
    principal = float(principal)
    rate = float(annual_rate_pct) / 100.0
    years = float(years)
    if compound:
        future = principal * ((1 + rate) ** years)
    else:
        future = principal * (1 + rate * years)
    return {
        "principal": principal,
        "annual_rate_pct": annual_rate_pct,
        "years": years,
        "compound": compound,
        "future_value": future,
        "interest_earned": future - principal,
    }


@dataclass
class IncomeInputs:
    employment: float = 0.0
    pension: float = 0.0
    property: float = 0.0
    savings_interest: float = 0.0
    dividends: float = 0.0
    trust_non_dividend: float = 0.0
    trust_dividend: float = 0.0
    apply_property_allowance: bool = True
    apply_trading_allowance: bool = False
    trading_income: float = 0.0


def _personal_allowance(adjusted_net_income: float, tables: dict[str, Any]) -> float:
    pa = float(tables["personal_allowance"])
    threshold = float(tables["personal_allowance_taper_threshold"])
    if adjusted_net_income <= threshold:
        return pa
    reduction = (adjusted_net_income - threshold) / 2.0
    return max(0.0, pa - reduction)


def _tax_on_banded_slice(
    amount: float,
    band_room: list[tuple[str, float, float]],
) -> tuple[float, list[dict[str, Any]], list[tuple[str, float, float]]]:
    """Tax `amount` using remaining band room. Returns tax, breakdown, leftover rooms."""
    remaining = amount
    tax = 0.0
    parts: list[dict[str, Any]] = []
    updated: list[tuple[str, float, float]] = []
    for name, room, rate in band_room:
        if remaining <= 0:
            updated.append((name, room, rate))
            continue
        used = min(remaining, room)
        chunk_tax = used * rate
        tax += chunk_tax
        if used > 0:
            parts.append(
                {"band": name, "amount": used, "rate": rate, "tax": chunk_tax}
            )
        updated.append((name, max(0.0, room - used), rate))
        remaining -= used
    return tax, parts, updated


def estimate_income_tax_england(
    employment: float = 0.0,
    pension: float = 0.0,
    property: float = 0.0,
    savings_interest: float = 0.0,
    dividends: float = 0.0,
    trust_non_dividend: float = 0.0,
    trust_dividend: float = 0.0,
    trading_income: float = 0.0,
    *,
    apply_property_allowance: bool = True,
    apply_trading_allowance: bool = False,
) -> dict[str, Any]:
    """
    Estimate England / NI / Wales-style income tax for 2026/27.

    Ordering (simplified HMRC stacking):
    1. Non-savings non-dividend (employment, pension, property, trading, trust other)
    2. Savings interest (starting rate + Personal Savings Allowance)
    3. Dividends (including trust dividends) with dividend allowance

    Sources: GOV.UK income tax rates, tax on dividends, tax on savings interest,
    and Budget 2025 Annex A rates for 2026/27.
    """
    tables = _load_tax_tables()
    rates = tables["rates"]
    basic_band = float(tables["basic_rate_band"])
    additional_threshold = float(tables["additional_rate_threshold"])

    property_gross = max(0.0, float(property))
    trading_gross = max(0.0, float(trading_income))
    property_taxable = property_gross
    trading_taxable = trading_gross
    if apply_property_allowance:
        property_taxable = max(0.0, property_gross - float(tables["property_allowance"]))
    if apply_trading_allowance:
        trading_taxable = max(0.0, trading_gross - float(tables["trading_allowance"]))

    non_savings = (
        max(0.0, float(employment))
        + max(0.0, float(pension))
        + property_taxable
        + trading_taxable
        + max(0.0, float(trust_non_dividend))
    )
    savings = max(0.0, float(savings_interest))
    divs = max(0.0, float(dividends)) + max(0.0, float(trust_dividend))

    total_income = non_savings + savings + divs
    pa = _personal_allowance(total_income, tables)

    # Allocate personal allowance: non-savings first, then savings, then dividends.
    pa_left = pa
    ns_after_pa = max(0.0, non_savings - pa_left)
    pa_used_ns = min(pa_left, non_savings)
    pa_left -= pa_used_ns

    savings_after_pa = max(0.0, savings - pa_left)
    pa_used_savings = min(pa_left, savings)
    pa_left -= pa_used_savings

    divs_after_pa = max(0.0, divs - pa_left)
    pa_used_divs = min(pa_left, divs)

    # Starting rate for savings: up to £5,000, reduced by non-savings above PA.
    starting_limit = float(tables["savings"]["starting_rate_limit"])
    other_above_pa = max(0.0, non_savings - pa)
    starting_rate_available = max(0.0, starting_limit - other_above_pa)

    # Band rooms on taxable income (after PA), per HMRC Annex A 2026/27:
    # basic £1–£37,700; higher to £125,140; additional above that.
    higher_room = max(0.0, additional_threshold - basic_band)
    band_room: list[tuple[str, float, float]] = [
        ("basic", basic_band, float(rates["basic"])),
        ("higher", higher_room, float(rates["higher"])),
        ("additional", 1e15, float(rates["additional"])),
    ]

    ns_tax, ns_parts, band_room = _tax_on_banded_slice(ns_after_pa, band_room)

    # Personal Savings Allowance depends on which band the taxpayer reaches
    # using total taxable income (including savings/dividends for band test).
    taxable_total = ns_after_pa + savings_after_pa + divs_after_pa
    if taxable_total > basic_band + higher_room:
        psa = float(tables["savings"]["personal_savings_allowance"]["additional"])
        marginal = "additional"
    elif taxable_total > basic_band:
        psa = float(tables["savings"]["personal_savings_allowance"]["higher"])
        marginal = "higher"
    else:
        psa = float(tables["savings"]["personal_savings_allowance"]["basic"])
        marginal = "basic"

    savings_taxable = savings_after_pa
    starting_used = min(savings_taxable, starting_rate_available)
    savings_taxable -= starting_used
    psa_used = min(savings_taxable, psa)
    savings_taxable -= psa_used

    savings_rates = tables["savings"]["rates"]
    savings_band_room = [
        ("basic", band_room[0][1], float(savings_rates["basic"])),
        ("higher", band_room[1][1], float(savings_rates["higher"])),
        ("additional", band_room[2][1], float(savings_rates["additional"])),
    ]
    sav_tax, sav_parts, savings_band_room = _tax_on_banded_slice(
        savings_taxable, savings_band_room
    )
    # Consume general band room by savings that used a rate band.
    band_room = [
        (band_room[0][0], savings_band_room[0][1], band_room[0][2]),
        (band_room[1][0], savings_band_room[1][1], band_room[1][2]),
        (band_room[2][0], savings_band_room[2][1], band_room[2][2]),
    ]

    div_allowance = float(tables["dividends"]["allowance"])
    divs_taxable = max(0.0, divs_after_pa - div_allowance)
    div_rates = tables["dividends"]["rates"]
    div_band_room = [
        ("basic", band_room[0][1], float(div_rates["basic"])),
        ("higher", band_room[1][1], float(div_rates["higher"])),
        ("additional", band_room[2][1], float(div_rates["additional"])),
    ]
    div_tax, div_parts, _ = _tax_on_banded_slice(divs_taxable, div_band_room)

    total_tax = ns_tax + sav_tax + div_tax
    return {
        "jurisdiction": tables.get("jurisdiction", "England"),
        "tax_year": tables.get("tax_year", "2026-27"),
        "total_income": total_income,
        "personal_allowance": pa,
        "personal_allowance_used": {
            "non_savings": pa_used_ns,
            "savings": pa_used_savings,
            "dividends": pa_used_divs,
        },
        "taxable": {
            "non_savings": ns_after_pa,
            "savings": savings_after_pa,
            "dividends": divs_after_pa,
        },
        "allowances_applied": {
            "property_allowance": float(tables["property_allowance"])
            if apply_property_allowance and property_gross
            else 0.0,
            "trading_allowance": float(tables["trading_allowance"])
            if apply_trading_allowance and trading_gross
            else 0.0,
            "starting_rate_for_savings": starting_used,
            "personal_savings_allowance": psa_used,
            "dividend_allowance": min(div_allowance, divs_after_pa),
        },
        "marginal_band": marginal,
        "tax": {
            "non_savings": ns_tax,
            "savings": sav_tax,
            "dividends": div_tax,
            "total": total_tax,
        },
        "breakdown": {
            "non_savings": ns_parts,
            "savings": sav_parts,
            "dividends": div_parts,
        },
        "effective_rate": (total_tax / total_income) if total_income else 0.0,
        "components": {
            "employment": float(employment),
            "pension": float(pension),
            "property_gross": property_gross,
            "property_taxable": property_taxable,
            "trading_gross": trading_gross,
            "trading_taxable": trading_taxable,
            "savings_interest": savings,
            "dividends": float(dividends),
            "trust_non_dividend": float(trust_non_dividend),
            "trust_dividend": float(trust_dividend),
        },
        "notes": [
            "Uses England bands for 2026/27 from GOV.UK.",
            "Dividend rates 10.75% / 35.75% / 39.35% from 6 April 2026.",
            "Savings and property rates remain aligned with main rates until April 2027.",
            "Trust income is a simplified beneficiary view; discretionary trusts have separate rates inside the trust.",
        ],
        "sources": [
            "https://www.gov.uk/income-tax-rates",
            "https://www.gov.uk/tax-on-dividends",
            "https://www.gov.uk/apply-tax-free-interest-on-savings",
        ],
    }


# Backwards-compatible thin wrapper used by older call sites.
def estimate_simple_income(taxable_income: float) -> dict[str, Any]:
    return estimate_income_tax_england(employment=float(taxable_income))
