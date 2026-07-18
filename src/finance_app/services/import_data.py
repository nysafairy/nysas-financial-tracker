"""Import profile data from a CSV zip matching the export / template schema."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date
from typing import Any

from finance_app.db.models import IncomeCadence
from finance_app.services import accounts as account_service
from finance_app.services import csv_schema
from finance_app.services import income as income_service
from finance_app.services import recurring as recurring_service
from finance_app.services import snapshots as snapshot_service


class CsvImportError(ValueError):
    """User-facing import validation or row error."""


def _validate_headers(filename: str, fieldnames: list[str] | None, expected: list[str]) -> None:
    if fieldnames is None:
        raise CsvImportError(f"{filename}: missing header row")
    actual = [f.strip() for f in fieldnames]
    if actual != expected:
        raise CsvImportError(
            f"{filename}: headers must match exactly.\n"
            f"Expected: {', '.join(expected)}\n"
            f"Found:    {', '.join(actual)}"
        )


def _parse_bool(raw: str, *, default: bool = True) -> bool:
    if raw is None or str(raw).strip() == "":
        return default
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    raise CsvImportError(f"Invalid boolean '{raw}' (use true/false)")


def _parse_optional_float(raw: str) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    return float(str(raw).strip())


def _parse_required_float(raw: str, field: str) -> float:
    value = _parse_optional_float(raw)
    if value is None:
        raise CsvImportError(f"Missing required number for {field}")
    return value


def _parse_optional_int(raw: str) -> int | None:
    if raw is None or str(raw).strip() == "":
        return None
    return int(float(str(raw).strip()))


def _parse_date(raw: str, field: str) -> date:
    if not raw or not str(raw).strip():
        raise CsvImportError(f"Missing required date for {field}")
    return date.fromisoformat(str(raw).strip()[:10])


def _parse_optional_date(raw: str) -> date | None:
    if raw is None or str(raw).strip() == "":
        return None
    return date.fromisoformat(str(raw).strip()[:10])


def _load_zip_tables(payload: bytes) -> dict[str, list[dict[str, str]]]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise CsvImportError("File is not a valid zip archive") from exc

    names = set(zf.namelist())

    def resolve(name: str) -> str | None:
        if name in names:
            return name
        suffix = f"/{name}"
        matches = [n for n in names if n.endswith(suffix) and not n.endswith("/")]
        return matches[0] if len(matches) == 1 else None

    tables: dict[str, list[dict[str, str]]] = {}
    missing: list[str] = []
    for filename, expected_fields in csv_schema.IMPORT_TABLES.items():
        path = resolve(filename)
        if path is None:
            missing.append(filename)
            continue
        raw = zf.read(path)
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        _validate_headers(filename, list(reader.fieldnames or []), expected_fields)
        rows: list[dict[str, str]] = []
        for row in reader:
            if not any((v or "").strip() for v in row.values() if v is not None):
                continue
            rows.append(
                {k: (v or "").strip() if v is not None else "" for k, v in row.items()}
            )
        tables[filename] = rows

    if missing:
        raise CsvImportError(
            "Zip is missing required CSV file(s): " + ", ".join(missing)
        )
    return tables


def import_csv_zip(payload: bytes) -> dict[str, Any]:
    """
    Import a template/export-shaped CSV zip into the open profile.

    Rows are appended (existing data is kept). CSV ids are remapped so links
    between accounts, snapshots, transactions, streams, and receipts stay intact.
    """
    tables = _load_zip_tables(payload)
    account_id_map: dict[int, int] = {}
    stream_id_map: dict[int, int] = {}
    counts = {
        "accounts": 0,
        "transactions": 0,
        "balance_snapshots": 0,
        "recurring": 0,
        "income_streams": 0,
        "income_receipts": 0,
    }

    for index, row in enumerate(tables[csv_schema.ACCOUNTS_CSV], start=2):
        try:
            csv_id = _parse_optional_int(row.get("id", ""))
            name = (row.get("name") or "").strip()
            if not name:
                raise CsvImportError("name is required")
            atype = csv_schema.resolve_enum("account_type", row.get("type"))
            if not atype:
                raise CsvImportError("type is required")
            interest_freq = csv_schema.resolve_enum(
                "interest_frequency", row.get("interest_frequency")
            )
            access = csv_schema.resolve_enum("access_type", row.get("access_type"))
            created = account_service.create_account(
                name,
                atype,
                currency=(row.get("currency") or "GBP").strip() or "GBP",
                notes=row.get("notes") or None,
                provider=row.get("provider") or None,
                account_number=row.get("account_number") or None,
                sort_code=row.get("sort_code") or None,
                interest_rate_pct=_parse_optional_float(row.get("interest_rate_pct", "")),
                interest_frequency=interest_freq,
                access_type=access,
                notice_days=_parse_optional_int(row.get("notice_days", "")),
                maturity_date=_parse_optional_date(row.get("maturity_date", "")),
                opened_date=_parse_optional_date(row.get("opened_date", "")),
            )
            if not _parse_bool(row.get("active", "true"), default=True):
                account_service.update_account(created.id, active=False)
            if csv_id is not None:
                account_id_map[csv_id] = created.id
            counts["accounts"] += 1
        except Exception as exc:
            raise CsvImportError(f"accounts.csv row {index}: {exc}") from exc

    def map_account(raw: str, *, required: bool = False) -> int | None:
        if raw is None or str(raw).strip() == "":
            if required:
                raise CsvImportError("account_id is required")
            return None
        old = int(float(str(raw).strip()))
        if old not in account_id_map:
            raise CsvImportError(
                f"account_id {old} not found in accounts.csv (link using the id column)"
            )
        return account_id_map[old]

    for index, row in enumerate(tables[csv_schema.INCOME_STREAMS_CSV], start=2):
        try:
            csv_id = _parse_optional_int(row.get("id", ""))
            name = (row.get("name") or "").strip()
            if not name:
                raise CsvImportError("name is required")
            category = csv_schema.resolve_enum("income_category", row.get("category"))
            cadence = csv_schema.resolve_enum("income_cadence", row.get("cadence"))
            if not category or not cadence:
                raise CsvImportError("category and cadence are required")
            pay_freq = csv_schema.resolve_enum("pay_frequency", row.get("pay_frequency"))
            tax_treatment = csv_schema.resolve_enum(
                "tax_treatment", row.get("tax_treatment")
            )
            tax_band = csv_schema.resolve_enum("tax_band", row.get("tax_band"))
            expected = _parse_optional_float(row.get("expected_amount", ""))
            if cadence != IncomeCadence.VARIABLE.value and expected is None:
                raise CsvImportError("expected_amount is required for fixed income")
            created = income_service.create_stream(
                name,
                category,
                cadence,
                expected_amount=expected,
                pay_frequency=pay_freq,
                tax_treatment=tax_treatment,
                tax_band=tax_band,
                notes=row.get("notes") or None,
            )
            if csv_id is not None:
                stream_id_map[csv_id] = created.id
            counts["income_streams"] += 1
        except Exception as exc:
            raise CsvImportError(f"income_streams.csv row {index}: {exc}") from exc

    for index, row in enumerate(tables[csv_schema.BALANCE_SNAPSHOTS_CSV], start=2):
        try:
            account_id = map_account(row.get("account_id", ""), required=True)
            assert account_id is not None
            snapshot_service.upsert_balance_snapshot(
                account_id,
                _parse_date(row.get("date", ""), "date"),
                _parse_required_float(row.get("balance", ""), "balance"),
            )
            counts["balance_snapshots"] += 1
        except Exception as exc:
            raise CsvImportError(f"balance_snapshots.csv row {index}: {exc}") from exc

    for index, row in enumerate(tables[csv_schema.TRANSACTIONS_CSV], start=2):
        try:
            txn_type = csv_schema.resolve_enum("transaction_type", row.get("type"))
            if not txn_type:
                raise CsvImportError("type is required")
            account_service.create_transaction(
                txn_date=_parse_date(row.get("date", ""), "date"),
                txn_type=txn_type,
                amount=_parse_required_float(row.get("amount", ""), "amount"),
                account_id=map_account(row.get("account_id", "")),
                description=row.get("description") or None,
            )
            counts["transactions"] += 1
        except Exception as exc:
            raise CsvImportError(f"transactions.csv row {index}: {exc}") from exc

    for index, row in enumerate(tables[csv_schema.RECURRING_CSV], start=2):
        try:
            name = (row.get("name") or "").strip()
            if not name:
                raise CsvImportError("name is required")
            kind = csv_schema.resolve_enum("recurring_kind", row.get("kind"))
            freq = csv_schema.resolve_enum("frequency", row.get("frequency"))
            if not kind or not freq:
                raise CsvImportError("kind and frequency are required")
            affects_raw = (row.get("affects_net_worth") or "").strip()
            item = recurring_service.create_recurring(
                name,
                kind,
                _parse_required_float(row.get("amount", ""), "amount"),
                freq,
                from_account_id=map_account(row.get("from_account_id", "")),
                to_account_id=map_account(row.get("to_account_id", "")),
                notes=row.get("notes") or None,
                affects_net_worth=(
                    _parse_bool(affects_raw, default=True) if affects_raw else None
                ),
            )
            if not _parse_bool(row.get("active", "true"), default=True):
                recurring_service.set_recurring_active(item.id, False)
            counts["recurring"] += 1
        except Exception as exc:
            raise CsvImportError(f"recurring.csv row {index}: {exc}") from exc

    for index, row in enumerate(tables[csv_schema.INCOME_RECEIPTS_CSV], start=2):
        try:
            stream_raw = row.get("stream_id", "")
            if not str(stream_raw).strip():
                raise CsvImportError("stream_id is required")
            old_stream = int(float(str(stream_raw).strip()))
            if old_stream not in stream_id_map:
                raise CsvImportError(
                    f"stream_id {old_stream} not found in income_streams.csv"
                )
            income_service.add_receipt(
                stream_id_map[old_stream],
                _parse_required_float(row.get("amount", ""), "amount"),
                _parse_date(row.get("date", ""), "date"),
                description=row.get("description") or None,
            )
            counts["income_receipts"] += 1
        except Exception as exc:
            raise CsvImportError(f"income_receipts.csv row {index}: {exc}") from exc

    return counts
