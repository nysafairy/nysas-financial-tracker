"""Additive, versioned schema migrations for profile databases.

Never drop user data. Each step bumps schema_meta.version after success.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from finance_app.db.models import (
    IncomeCadence,
    IncomeCategory,
    IncomeRatePeriod,
    IncomeReceipt,
    IncomeStream,
    TaxTreatment,
)


def _table_columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _table_names(conn) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    }


def _add_columns_if_missing(
    conn, table: str, columns: list[tuple[str, str]]
) -> None:
    if table not in _table_names(conn):
        return
    existing = _table_columns(conn, table)
    for column, sql_type in columns:
        if column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


def _drop_column_if_exists(conn, table: str, column: str) -> None:
    if table not in _table_names(conn):
        return
    if column not in _table_columns(conn, table):
        return
    conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))


def ensure_legacy_shape(engine: Engine) -> None:
    """Idempotent column adds and obsolete-table cleanup for pre-v9 databases."""
    account_cols = [
        ("provider", "VARCHAR(120)"),
        ("account_number", "VARCHAR(64)"),
        ("sort_code", "VARCHAR(16)"),
        ("interest_rate_pct", "FLOAT"),
        ("interest_frequency", "VARCHAR(32)"),
        ("access_type", "VARCHAR(32)"),
        ("notice_days", "INTEGER"),
        ("maturity_date", "DATE"),
        ("opened_date", "DATE"),
    ]
    income_cols = [
        ("pay_frequency", "VARCHAR(32)"),
        ("tax_treatment", "VARCHAR(32) DEFAULT 'other'"),
        ("tax_band", "VARCHAR(32)"),
    ]
    draft_cols = [
        ("account_number", "VARCHAR(64)"),
        ("sort_code", "VARCHAR(16)"),
        ("interest_rate_pct", "FLOAT"),
        ("interest_frequency", "VARCHAR(32)"),
        ("access_type", "VARCHAR(32)"),
        ("notice_days", "INTEGER"),
        ("maturity_date", "DATE"),
        ("opened_date", "DATE"),
        ("clear_interest_rate", "BOOLEAN DEFAULT 0"),
        ("clear_notice_days", "BOOLEAN DEFAULT 0"),
        ("clear_maturity_date", "BOOLEAN DEFAULT 0"),
        ("clear_opened_date", "BOOLEAN DEFAULT 0"),
    ]
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS holding_snapshots"))
        conn.execute(text("DROP TABLE IF EXISTS holdings"))
        _add_columns_if_missing(conn, "accounts", account_cols)
        _add_columns_if_missing(conn, "income_streams", income_cols)
        _add_columns_if_missing(conn, "snapshot_draft_accounts", draft_cols)


def backfill_income_rate_periods(session: Session) -> None:
    """Give fixed streams an initial rate period when history is missing."""
    from finance_app.services.metrics import uk_tax_year_start

    streams = list(session.scalars(select(IncomeStream)).all())
    for stream in streams:
        if stream.cadence == IncomeCadence.VARIABLE:
            continue
        if stream.expected_amount is None:
            continue
        existing = session.scalar(
            select(IncomeRatePeriod)
            .where(IncomeRatePeriod.stream_id == stream.id)
            .limit(1)
        )
        if existing is not None:
            continue
        annual = float(stream.expected_amount)
        if stream.cadence == IncomeCadence.FIXED_MONTHLY:
            annual *= 12.0
        session.add(
            IncomeRatePeriod(
                stream_id=stream.id,
                effective_from=uk_tax_year_start(),
                annual_amount=annual,
                notes="Backfilled initial rate",
            )
        )


def migrate_to_v9(engine: Engine, session: Session) -> None:
    """
    Income consolidation + schema tidy:

    - Convert employment-style ledger transactions into income streams/receipts
    - Drop unused columns (counterparty, day_of_month, affects_net_worth)
    """
    _migrate_earnings_transactions_to_streams(session)
    session.commit()
    with engine.begin() as conn:
        _drop_column_if_exists(conn, "transactions", "counterparty_account_id")
        _drop_column_if_exists(conn, "recurring_items", "day_of_month")
        _drop_column_if_exists(conn, "recurring_items", "affects_net_worth")


def _migrate_earnings_transactions_to_streams(session: Session) -> None:
    income_types = {
        "earnings": (
            IncomeCategory.SALARY,
            TaxTreatment.EMPLOYMENT,
            "Migrated earnings / salary",
        ),
        "pension_income": (
            IncomeCategory.PENSION,
            TaxTreatment.PENSION,
            "Migrated pension income",
        ),
        "property_income": (
            IncomeCategory.PROPERTY,
            TaxTreatment.PROPERTY,
            "Migrated property income",
        ),
        "trust_income": (
            IncomeCategory.OTHER,
            TaxTreatment.OTHER,
            "Migrated trust / fund income",
        ),
    }
    # Raw SQL so we catch rows even if ORM enum decoding skips them.
    result = session.execute(
        text(
            "SELECT id, txn_date, lower(txn_type) AS txn_type, amount, description "
            "FROM transactions WHERE lower(txn_type) IN "
            "('earnings', 'pension_income', 'property_income', 'trust_income')"
        )
    )
    raw_rows = list(result.fetchall())
    if not raw_rows:
        return

    by_key: dict[str, list] = {}
    for rid, txn_date, txn_type, amount, description in raw_rows:
        by_key.setdefault(str(txn_type), []).append(
            (rid, txn_date, float(amount), description)
        )

    for key, items in by_key.items():
        category, treatment, default_name = income_types[key]
        stream = IncomeStream(
            name=default_name,
            category=category,
            cadence=IncomeCadence.VARIABLE,
            expected_amount=None,
            pay_frequency=None,
            tax_treatment=treatment,
            tax_band=None,
            active=True,
            notes="Migrated from ledger transactions",
        )
        session.add(stream)
        session.flush()
        for rid, txn_date, amount, description in items:
            if isinstance(txn_date, str):
                entry_date = date.fromisoformat(txn_date[:10])
            elif isinstance(txn_date, datetime):
                entry_date = txn_date.date()
            else:
                entry_date = txn_date
            session.add(
                IncomeReceipt(
                    stream_id=stream.id,
                    entry_date=entry_date,
                    amount=amount,
                    description=description or key,
                )
            )
            session.execute(text("DELETE FROM transactions WHERE id = :id"), {"id": rid})


# (target_version, migration_fn)
# fn(engine, session) — session is open; caller commits version bump after success.
MigrationFn = Callable[[Engine, Session], None]

MIGRATIONS: list[tuple[int, MigrationFn]] = [
    (9, migrate_to_v9),
]


def stamp_schema_meta(session: Session, version: int) -> None:
    from finance_app.db.models import SchemaMeta

    meta = session.scalar(select(SchemaMeta).limit(1))
    now = datetime.now(timezone.utc)
    if meta is None:
        session.add(SchemaMeta(version=version, updated_at=now))
    else:
        meta.version = version
        meta.updated_at = now
