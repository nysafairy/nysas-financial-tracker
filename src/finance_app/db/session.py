"""Engine and session management for a selected profile database."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from finance_app.config import SCHEMA_VERSION, ensure_data_root, profile_db_path, profile_dir
from finance_app.db import migrations as migration_runner
from finance_app.db.models import Base, SchemaMeta

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None
_current_profile: str | None = None


class SchemaTooNewError(RuntimeError):
    """Raised when the profile DB was written by a newer app version."""


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


def init_db() -> None:
    """Create missing tables and apply additive migrations. Never drop user data."""
    if _engine is None or _SessionLocal is None:
        raise RuntimeError("No profile database is open")

    Base.metadata.create_all(_engine)
    migration_runner.ensure_legacy_shape(_engine)

    with _SessionLocal() as session:
        try:
            meta = session.scalar(select(SchemaMeta).limit(1))
        except Exception:
            session.rollback()
            meta = None

        current = meta.version if meta is not None else 0

        if current > SCHEMA_VERSION:
            raise SchemaTooNewError(
                f"This profile database is schema version {current}, but the app "
                f"only supports up to {SCHEMA_VERSION}. Update the app to open it."
            )

        # Fresh database: tables match current models — stamp and return.
        if current == 0:
            migration_runner.backfill_income_rate_periods(session)
            migration_runner.stamp_schema_meta(session, SCHEMA_VERSION)
            session.commit()
            return

        # Bring legacy DBs (version stamped below current) forward safely.
        if current < 8:
            migration_runner.backfill_income_rate_periods(session)
            migration_runner.stamp_schema_meta(session, 8)
            session.commit()
            current = 8

        for target_version, migrate_fn in migration_runner.MIGRATIONS:
            if current >= target_version:
                continue
            migrate_fn(_engine, session)
            migration_runner.stamp_schema_meta(session, target_version)
            session.commit()
            current = target_version

        if current < SCHEMA_VERSION:
            migration_runner.stamp_schema_meta(session, SCHEMA_VERSION)
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
