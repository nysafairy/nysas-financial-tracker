"""Shared CSV table schemas for export, import, and downloadable templates."""

from __future__ import annotations

from finance_app.db.models import (
    ACCESS_TYPE_LABELS,
    ACCOUNT_TYPE_LABELS,
    FREQUENCY_LABELS,
    INCOME_CADENCE_LABELS,
    INCOME_CATEGORY_LABELS,
    INTEREST_FREQUENCY_LABELS,
    PAY_FREQUENCY_LABELS,
    RECURRING_KIND_LABELS,
    TAX_BAND_LABELS,
    TAX_TREATMENT_LABELS,
    TRANSACTION_TYPE_LABELS,
    AccessType,
    AccountType,
    Frequency,
    IncomeCadence,
    IncomeCategory,
    InterestFrequency,
    PayFrequency,
    RecurringKind,
    TaxBand,
    TaxTreatment,
    TransactionType,
)

# Filenames inside the zip (summary is export-only; ignored on import).
ACCOUNTS_CSV = "accounts.csv"
TRANSACTIONS_CSV = "transactions.csv"
BALANCE_SNAPSHOTS_CSV = "balance_snapshots.csv"
RECURRING_CSV = "recurring.csv"
INCOME_STREAMS_CSV = "income_streams.csv"
INCOME_RECEIPTS_CSV = "income_receipts.csv"
SUMMARY_CSV = "summary.csv"
README_TXT = "README.txt"

ACCOUNT_FIELDS = [
    "id",
    "name",
    "type",
    "provider",
    "account_number",
    "sort_code",
    "interest_rate_pct",
    "interest_frequency",
    "access_type",
    "notice_days",
    "maturity_date",
    "opened_date",
    "currency",
    "active",
    "notes",
]

TRANSACTION_FIELDS = [
    "id",
    "date",
    "type",
    "amount",
    "account_id",
    "description",
]

BALANCE_SNAPSHOT_FIELDS = [
    "id",
    "date",
    "account_id",
    "balance",
]

RECURRING_FIELDS = [
    "id",
    "name",
    "kind",
    "amount",
    "frequency",
    "from_account_id",
    "to_account_id",
    "affects_net_worth",
    "active",
    "notes",
]

INCOME_STREAM_FIELDS = [
    "id",
    "name",
    "category",
    "cadence",
    "pay_frequency",
    "tax_treatment",
    "tax_band",
    "expected_amount",
    "active",
    "notes",
]

INCOME_RECEIPT_FIELDS = [
    "id",
    "stream_id",
    "date",
    "amount",
    "description",
]

# Required files for a valid import zip (headers must match exactly).
IMPORT_TABLES: dict[str, list[str]] = {
    ACCOUNTS_CSV: ACCOUNT_FIELDS,
    TRANSACTIONS_CSV: TRANSACTION_FIELDS,
    BALANCE_SNAPSHOTS_CSV: BALANCE_SNAPSHOT_FIELDS,
    RECURRING_CSV: RECURRING_FIELDS,
    INCOME_STREAMS_CSV: INCOME_STREAM_FIELDS,
    INCOME_RECEIPTS_CSV: INCOME_RECEIPT_FIELDS,
}


def _enum_value_map(enum_cls, labels: dict) -> dict[str, str]:
    """Map label or value (case-insensitive) -> canonical enum value."""
    mapping: dict[str, str] = {}
    for member in enum_cls:
        mapping[member.value.lower()] = member.value
        mapping[member.name.lower()] = member.value
    for member, label in labels.items():
        mapping[label.lower()] = member.value
    return mapping


ENUM_LOOKUPS: dict[str, dict[str, str]] = {
    "account_type": _enum_value_map(AccountType, ACCOUNT_TYPE_LABELS),
    "interest_frequency": _enum_value_map(InterestFrequency, INTEREST_FREQUENCY_LABELS),
    "access_type": _enum_value_map(AccessType, ACCESS_TYPE_LABELS),
    "transaction_type": _enum_value_map(TransactionType, TRANSACTION_TYPE_LABELS),
    "recurring_kind": _enum_value_map(RecurringKind, RECURRING_KIND_LABELS),
    "frequency": _enum_value_map(Frequency, FREQUENCY_LABELS),
    "income_category": _enum_value_map(IncomeCategory, INCOME_CATEGORY_LABELS),
    "income_cadence": _enum_value_map(IncomeCadence, INCOME_CADENCE_LABELS),
    "pay_frequency": _enum_value_map(PayFrequency, PAY_FREQUENCY_LABELS),
    "tax_treatment": _enum_value_map(TaxTreatment, TAX_TREATMENT_LABELS),
    "tax_band": _enum_value_map(TaxBand, TAX_BAND_LABELS),
}


def resolve_enum(kind: str, raw: str | None) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    lookup = ENUM_LOOKUPS[kind]
    key = text.lower()
    if key not in lookup:
        allowed = ", ".join(sorted({m.value for m in _enum_for(kind)}))
        raise ValueError(f"Unknown {kind} '{raw}'. Use a value such as: {allowed}")
    return lookup[key]


def _enum_for(kind: str):
    return {
        "account_type": AccountType,
        "interest_frequency": InterestFrequency,
        "access_type": AccessType,
        "transaction_type": TransactionType,
        "recurring_kind": RecurringKind,
        "frequency": Frequency,
        "income_category": IncomeCategory,
        "income_cadence": IncomeCadence,
        "pay_frequency": PayFrequency,
        "tax_treatment": TaxTreatment,
        "tax_band": TaxBand,
    }[kind]


def template_readme() -> str:
    lines = [
        "Nysa's Financial Tracker — CSV import template",
        "",
        "Fill these CSVs (keep the header row exactly as given), zip them together,",
        "and import the zip from View data. Column names must match exactly.",
        "",
        "IDs in the CSV are only used to link rows inside the zip (e.g. account_id).",
        "They are remapped on import and do not need to match existing database IDs.",
        "",
        "Enum fields accept either the machine value or the display label.",
        "Preferred (machine) values:",
        "",
    ]
    sections = [
        ("account type (accounts.csv type)", AccountType, ACCOUNT_TYPE_LABELS),
        (
            "interest_frequency",
            InterestFrequency,
            INTEREST_FREQUENCY_LABELS,
        ),
        ("access_type", AccessType, ACCESS_TYPE_LABELS),
        ("transaction type (transactions.csv type)", TransactionType, TRANSACTION_TYPE_LABELS),
        ("recurring kind", RecurringKind, RECURRING_KIND_LABELS),
        ("recurring frequency", Frequency, FREQUENCY_LABELS),
        ("income category", IncomeCategory, INCOME_CATEGORY_LABELS),
        ("income cadence", IncomeCadence, INCOME_CADENCE_LABELS),
        ("pay_frequency", PayFrequency, PAY_FREQUENCY_LABELS),
        ("tax_treatment", TaxTreatment, TAX_TREATMENT_LABELS),
        ("tax_band", TaxBand, TAX_BAND_LABELS),
    ]
    for title, enum_cls, labels in sections:
        lines.append(f"## {title}")
        for member in enum_cls:
            label = labels.get(member, member.value)
            lines.append(f"  - {member.value}  ({label})")
        lines.append("")
    lines.extend(
        [
            "Booleans (active, affects_net_worth): true/false, 1/0, yes/no.",
            "Dates: YYYY-MM-DD.",
            "Currency defaults to GBP if blank.",
            "Empty optional cells are fine.",
            "",
            "Required files:",
            *[f"  - {name}" for name in IMPORT_TABLES],
            "",
            "summary.csv is written on export only and is ignored on import.",
        ]
    )
    return "\n".join(lines) + "\n"


def example_template_rows() -> dict[str, list[dict]]:
    """One illustrative row per table (machine enum values)."""
    return {
        ACCOUNTS_CSV: [
            {
                "id": "1",
                "name": "Everyday current",
                "type": AccountType.CURRENT.value,
                "provider": "Demo Bank",
                "account_number": "",
                "sort_code": "00-00-00",
                "interest_rate_pct": "",
                "interest_frequency": "",
                "access_type": "",
                "notice_days": "",
                "maturity_date": "",
                "opened_date": "",
                "currency": "GBP",
                "active": "true",
                "notes": "Example row — replace or delete",
            },
            {
                "id": "2",
                "name": "Easy-access savings",
                "type": AccountType.SAVINGS_EASY_ACCESS.value,
                "provider": "Demo Bank",
                "account_number": "",
                "sort_code": "",
                "interest_rate_pct": "4.5",
                "interest_frequency": InterestFrequency.MONTHLY.value,
                "access_type": AccessType.EASY_ACCESS.value,
                "notice_days": "",
                "maturity_date": "",
                "opened_date": "",
                "currency": "GBP",
                "active": "true",
                "notes": "",
            },
        ],
        TRANSACTIONS_CSV: [
            {
                "id": "1",
                "date": "2026-05-01",
                "type": TransactionType.INTEREST.value,
                "amount": "12.50",
                "account_id": "2",
                "description": "Example interest",
            }
        ],
        BALANCE_SNAPSHOTS_CSV: [
            {
                "id": "1",
                "date": "2026-06-30",
                "account_id": "1",
                "balance": "2500.00",
            },
            {
                "id": "2",
                "date": "2026-06-30",
                "account_id": "2",
                "balance": "9000.00",
            },
        ],
        RECURRING_CSV: [
            {
                "id": "1",
                "name": "Netflix",
                "kind": RecurringKind.SUBSCRIPTION.value,
                "amount": "15.99",
                "frequency": Frequency.MONTHLY.value,
                "from_account_id": "1",
                "to_account_id": "",
                "affects_net_worth": "true",
                "active": "true",
                "notes": "",
            }
        ],
        INCOME_STREAMS_CSV: [
            {
                "id": "1",
                "name": "Day job",
                "category": IncomeCategory.SALARY.value,
                "cadence": IncomeCadence.FIXED_ANNUAL.value,
                "pay_frequency": PayFrequency.MONTHLY.value,
                "tax_treatment": TaxTreatment.EMPLOYMENT.value,
                "tax_band": TaxBand.BASIC.value,
                "expected_amount": "42000",
                "active": "true",
                "notes": "Gross annual",
            }
        ],
        INCOME_RECEIPTS_CSV: [
            {
                "id": "1",
                "stream_id": "1",
                "date": "2026-05-15",
                "amount": "100.00",
                "description": "Optional example receipt",
            }
        ],
    }
