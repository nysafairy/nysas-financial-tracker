"""Export profile data as CSV (zip of tables)."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timezone

from finance_app.db.models import (
    ACCOUNT_TYPE_LABELS,
    ACCESS_TYPE_LABELS,
    FREQUENCY_LABELS,
    INCOME_CADENCE_LABELS,
    INCOME_CATEGORY_LABELS,
    INTEREST_FREQUENCY_LABELS,
    RECURRING_KIND_LABELS,
    TRANSACTION_TYPE_LABELS,
)
from finance_app.services import accounts as account_service
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


def build_export_zip() -> tuple[str, bytes]:
    """Return (filename, zip_bytes) for all major tables."""
    inventory = database_inventory()
    accounts = account_service.list_accounts()
    holdings = account_service.list_holdings()
    transactions = account_service.list_transactions(limit=10_000)
    snaps = snapshot_service.list_balance_snapshots(limit=50_000)
    recurring = recurring_service.list_recurring()
    streams = income_service.list_streams()
    receipts = income_service.list_receipts(limit=10_000)

    account_rows = [
        {
            "id": a.id,
            "name": a.name,
            "type": ACCOUNT_TYPE_LABELS.get(a.account_type, a.account_type.value),
            "provider": a.provider or "",
            "account_number": a.account_number or "",
            "sort_code": a.sort_code or "",
            "interest_rate_pct": a.interest_rate_pct
            if a.interest_rate_pct is not None
            else "",
            "interest_frequency": INTEREST_FREQUENCY_LABELS.get(
                a.interest_frequency, ""
            )
            if a.interest_frequency
            else "",
            "access_type": ACCESS_TYPE_LABELS.get(a.access_type, "")
            if a.access_type
            else "",
            "notice_days": a.notice_days if a.notice_days is not None else "",
            "maturity_date": a.maturity_date.isoformat() if a.maturity_date else "",
            "opened_date": a.opened_date.isoformat() if a.opened_date else "",
            "currency": a.currency,
            "active": a.active,
            "notes": a.notes or "",
        }
        for a in accounts
    ]
    holding_rows = [
        {
            "id": h.id,
            "account_id": h.account_id,
            "name": h.name,
            "ticker": h.ticker or "",
            "units": h.units,
            "provider": h.provider or "",
            "notes": h.notes or "",
        }
        for h in holdings
    ]
    txn_rows = [
        {
            "id": t.id,
            "date": t.txn_date.isoformat(),
            "type": TRANSACTION_TYPE_LABELS.get(t.txn_type, t.txn_type.value),
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
            "kind": RECURRING_KIND_LABELS.get(r.kind, r.kind.value),
            "amount": r.amount,
            "frequency": FREQUENCY_LABELS.get(r.frequency, r.frequency.value),
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
            "category": INCOME_CATEGORY_LABELS.get(s.category, s.category.value),
            "cadence": INCOME_CADENCE_LABELS.get(s.cadence, s.cadence.value),
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
            "accounts.csv",
            _write_csv(
                account_rows,
                [
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
                ],
            ),
        )
        zf.writestr(
            "holdings.csv",
            _write_csv(
                holding_rows,
                ["id", "account_id", "name", "ticker", "units", "provider", "notes"],
            ),
        )
        zf.writestr(
            "transactions.csv",
            _write_csv(
                txn_rows,
                ["id", "date", "type", "amount", "account_id", "description"],
            ),
        )
        zf.writestr(
            "balance_snapshots.csv",
            _write_csv(snap_rows, ["id", "date", "account_id", "balance"]),
        )
        zf.writestr(
            "recurring.csv",
            _write_csv(
                recurring_rows,
                [
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
                ],
            ),
        )
        zf.writestr(
            "income_streams.csv",
            _write_csv(
                stream_rows,
                [
                    "id",
                    "name",
                    "category",
                    "cadence",
                    "expected_amount",
                    "active",
                    "notes",
                ],
            ),
        )
        zf.writestr(
            "income_receipts.csv",
            _write_csv(
                receipt_rows,
                ["id", "stream_id", "date", "amount", "description"],
            ),
        )
        # Lightweight inventory summary counts
        counts = inventory["counts"]
        zf.writestr(
            "summary.csv",
            _write_csv(
                [{"key": k, "value": v} for k, v in counts.items()],
                ["key", "value"],
            ),
        )
    return filename, buffer.getvalue()
