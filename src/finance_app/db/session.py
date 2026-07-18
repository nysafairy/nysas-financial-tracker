"""Engine and session management for a selected profile database."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from finance_app.config import SCHEMA_VERSION, ensure_data_root, profile_db_path, profile_dir
from finance_app.db.models import Base, SchemaMeta

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None
_current_profile: str | None = None

# SQLite cannot ALTER ENUM cleanly; new nullable columns are added if missing.
_ACCOUNT_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
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

_INCOME_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("pay_frequency", "VARCHAR(32)"),
    ("tax_treatment", "VARCHAR(32) DEFAULT 'other'"),
    ("tax_band", "VARCHAR(32)"),
]

_DRAFT_ACCOUNT_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
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


def get_current_profile() -> str | None:
    return _current_profile


def close_profile() -> None:
    """Dispose the open database connection without selecting another profile."""
    global _engine, _SessionLocal, _current_profile
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    _current_profile = None


def open_profile(slug: str, root: Path | None = None) -> Path:
    """Open (or create) the SQLite database for a profile slug."""
    global _engine, _SessionLocal, _current_profile

    ensure_data_root(root)
    directory = profile_dir(slug, root)
    directory.mkdir(parents=True, exist_ok=True)
    db_path = profile_db_path(slug, root)

    if _engine is not None:
        _engine.dispose()

    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    _SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    _current_profile = slug
    init_db()
    return db_path


def _table_columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _migrate_sqlite_columns() -> None:
    if _engine is None:
        return
    with _engine.begin() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "accounts" in tables:
            existing = _table_columns(conn, "accounts")
            for column, sql_type in _ACCOUNT_COLUMN_MIGRATIONS:
                if column not in existing:
                    conn.execute(
                        text(f"ALTER TABLE accounts ADD COLUMN {column} {sql_type}")
                    )
        if "income_streams" in tables:
            existing = _table_columns(conn, "income_streams")
            for column, sql_type in _INCOME_COLUMN_MIGRATIONS:
                if column not in existing:
                    conn.execute(
                        text(
                            f"ALTER TABLE income_streams ADD COLUMN {column} {sql_type}"
                        )
                    )
        if "snapshot_draft_accounts" in tables:
            existing = _table_columns(conn, "snapshot_draft_accounts")
            for column, sql_type in _DRAFT_ACCOUNT_COLUMN_MIGRATIONS:
                if column not in existing:
                    conn.execute(
                        text(
                            "ALTER TABLE snapshot_draft_accounts "
                            f"ADD COLUMN {column} {sql_type}"
                        )
                    )


def _drop_obsolete_tables() -> None:
    """Remove holdings tables from pre-v7 schemas (no live users yet)."""
    if _engine is None:
        return
    with _engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS holding_snapshots"))
        conn.execute(text("DROP TABLE IF EXISTS holdings"))


def _schema_needs_rebuild(session: Session) -> bool:
    meta = session.scalar(select(SchemaMeta).limit(1))
    if meta is None:
        return False
    return meta.version < SCHEMA_VERSION


def init_db() -> None:
    if _engine is None or _SessionLocal is None:
        raise RuntimeError("No profile database is open")

    with _SessionLocal() as session:
        needs_rebuild = False
        try:
            needs_rebuild = _schema_needs_rebuild(session)
        except Exception:
            # Missing / broken schema_meta — create fresh.
            session.rollback()
            needs_rebuild = False

    if needs_rebuild:
        # Destructive recreate: nobody is using live data yet.
        Base.metadata.drop_all(_engine)
        Base.metadata.create_all(_engine)
        with _SessionLocal() as session:
            session.add(
                SchemaMeta(
                    version=SCHEMA_VERSION,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        return

    Base.metadata.create_all(_engine)
    _drop_obsolete_tables()
    _migrate_sqlite_columns()
    _backfill_income_rate_periods()
    with _SessionLocal() as session:
        meta = session.scalar(select(SchemaMeta).limit(1))
        if meta is None:
            session.add(
                SchemaMeta(
                    version=SCHEMA_VERSION,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        elif meta.version < SCHEMA_VERSION:
            meta.version = SCHEMA_VERSION
            meta.updated_at = datetime.now(timezone.utc)
            session.commit()


def _backfill_income_rate_periods() -> None:
    """Give existing fixed streams an initial rate period if history is missing."""
    from finance_app.db.models import (
        IncomeCadence,
        IncomeRatePeriod,
        IncomeStream,
    )
    from finance_app.services.metrics import uk_tax_year_start

    if _SessionLocal is None:
        return
    with _SessionLocal() as session:
        streams = list(session.scalars(select(IncomeStream)).all())
        changed = False
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
            changed = True
        if changed:
            session.commit()


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("No profile database is open")
    return _engine


@contextmanager
def get_session() -> Iterator[Session]:
    if _SessionLocal is None:
        raise RuntimeError("No profile database is open")
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
