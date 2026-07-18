"""Export profile data as CSV (zip of tables) and import templates."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timezone

from finance_app.db.models import (
    ACCESS_TYPE_LABELS,
    ACCOUNT_TYPE_LABELS,
    FREQUENCY_LABELS,
    INCOME_CADENCE_LABELS,
    INCOME_CATEGORY_LABELS,
    INTEREST_FREQUENCY_LABELS,
    PAY_FREQUENCY_LABELS,
    RECURRING_KIND_LABELS,
    TRANSACTION_TYPE_LABELS,
)
from finance_app.services import accounts as account_service
from finance_app.services import csv_schema
from finance_app.services import income as income_service
from finance_app.services import recurring as recurring_service
from finance_app.services import snapshots as snapshot_service
from finance_app.services.inventory import database_inventory


def _write_csv(rows: list[dict], fieldnames: list[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode("utf-8")


def build_import_template_zip() -> tuple[str, bytes]:
    """Return (filename, zip_bytes) for an empty-schema template with examples."""
    examples = csv_schema.example_template_rows()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(csv_schema.README_TXT, csv_schema.template_readme().encode("utf-8"))
        for filename, fields in csv_schema.IMPORT_TABLES.items():
            zf.writestr(
                filename,
                _write_csv(examples.get(filename, []), fields),
            )
    return "nysas_financial_tracker_import_template.zip", buffer.getvalue()


def build_export_zip() -> tuple[str, bytes]:
    """Return (filename, zip_bytes) for all major tables."""
    inventory = database_inventory()
    accounts = account_service.list_accounts()
    transactions = account_service.list_transactions(limit=10_000)
    snaps = snapshot_service.list_balance_snapshots(limit=50_000)
    recurring = recurring_service.list_recurring()
    streams = income_service.list_streams()
    receipts = income_service.list_receipts(limit=10_000)

    account_rows = [
        {
            "id": a.id,
            "name": a.name,
            "type": a.account_type.value,
            "provider": a.provider or "",
            "account_number": a.account_number or "",
            "sort_code": a.sort_code or "",
            "interest_rate_pct": a.interest_rate_pct
            if a.interest_rate_pct is not None
            else "",
            "interest_frequency": a.interest_frequency.value
            if a.interest_frequency
            else "",
            "access_type": a.access_type.value if a.access_type else "",
            "notice_days": a.notice_days if a.notice_days is not None else "",
            "maturity_date": a.maturity_date.isoformat() if a.maturity_date else "",
            "opened_date": a.opened_date.isoformat() if a.opened_date else "",
            "currency": a.currency,
            "active": a.active,
            "notes": a.notes or "",
        }
        for a in accounts
    ]
    txn_rows = [
        {
            "id": t.id,
            "date": t.txn_date.isoformat(),
            "type": t.txn_type.value,
            "amount": t.amount,
            "account_id": t.account_id if t.account_id is not None else "",
            "description": t.description or "",
        }
        for t in transactions
    ]
    snap_rows = [
        {
            "id": s.id,
            "date": s.as_of_date.isoformat(),
            "account_id": s.account_id,
            "balance": s.balance,
        }
        for s in snaps
    ]
    recurring_rows = [
        {
            "id": r.id,
            "name": r.name,
            "kind": r.kind.value,
            "amount": r.amount,
            "frequency": r.frequency.value,
            "from_account_id": r.from_account_id or "",
            "to_account_id": r.to_account_id or "",
            "affects_net_worth": r.affects_net_worth,
            "active": r.active,
            "notes": r.notes or "",
        }
        for r in recurring
    ]
    stream_rows = [
        {
            "id": s.id,
            "name": s.name,
            "category": s.category.value,
            "cadence": s.cadence.value,
            "pay_frequency": s.pay_frequency.value if s.pay_frequency else "",
            "tax_treatment": (
                s.tax_treatment.value
                if getattr(s, "tax_treatment", None)
                else ""
            ),
            "tax_band": s.tax_band.value if getattr(s, "tax_band", None) else "",
            "expected_amount": s.expected_amount
            if s.expected_amount is not None
            else "",
            "active": s.active,
            "notes": s.notes or "",
        }
        for s in streams
    ]
    receipt_rows = [
        {
            "id": r.id,
            "stream_id": r.stream_id,
            "date": r.entry_date.isoformat(),
            "amount": r.amount,
            "description": r.description or "",
        }
        for r in receipts
    ]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"nysas_financial_tracker_export_{stamp}.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            csv_schema.ACCOUNTS_CSV,
            _write_csv(account_rows, csv_schema.ACCOUNT_FIELDS),
        )
        zf.writestr(
            csv_schema.TRANSACTIONS_CSV,
            _write_csv(txn_rows, csv_schema.TRANSACTION_FIELDS),
        )
        zf.writestr(
            csv_schema.BALANCE_SNAPSHOTS_CSV,
            _write_csv(snap_rows, csv_schema.BALANCE_SNAPSHOT_FIELDS),
        )
        zf.writestr(
            csv_schema.RECURRING_CSV,
            _write_csv(recurring_rows, csv_schema.RECURRING_FIELDS),
        )
        zf.writestr(
            csv_schema.INCOME_STREAMS_CSV,
            _write_csv(stream_rows, csv_schema.INCOME_STREAM_FIELDS),
        )
        zf.writestr(
            csv_schema.INCOME_RECEIPTS_CSV,
            _write_csv(receipt_rows, csv_schema.INCOME_RECEIPT_FIELDS),
        )
        counts = inventory["counts"]
        zf.writestr(
            csv_schema.SUMMARY_CSV,
            _write_csv(
                [{"key": k, "value": v} for k, v in counts.items()],
                ["key", "value"],
            ),
        )
        # Human-readable legend so exports stay usable without the template README.
        legend_lines = ["# Enum labels (for reference; import accepts value or label)", ""]
        for title, labels in [
            ("account type", ACCOUNT_TYPE_LABELS),
            ("interest_frequency", INTEREST_FREQUENCY_LABELS),
            ("access_type", ACCESS_TYPE_LABELS),
            ("transaction type", TRANSACTION_TYPE_LABELS),
            ("recurring kind", RECURRING_KIND_LABELS),
            ("frequency", FREQUENCY_LABELS),
            ("income category", INCOME_CATEGORY_LABELS),
            ("income cadence", INCOME_CADENCE_LABELS),
            ("pay_frequency", PAY_FREQUENCY_LABELS),
        ]:
            legend_lines.append(f"## {title}")
            for member, label in labels.items():
                legend_lines.append(f"  {member.value} = {label}")
            legend_lines.append("")
        zf.writestr("ENUMS.txt", "\n".join(legend_lines).encode("utf-8"))
    return filename, buffer.getvalue()
