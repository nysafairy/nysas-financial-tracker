"""Draft snapshot editing session — autosaved until commit or discard."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select

from finance_app.db.models import (
    ACCOUNT_TYPE_LABELS,
    LIABILITY_TYPES,
    Account,
    AccountType,
    BalanceSnapshot,
    SnapshotDraft,
    SnapshotDraftAccount,
    SnapshotDraftBalance,
)
from finance_app.db.session import get_session
from finance_app.services import accounts as account_service
from finance_app.services import snapshots as snapshot_service


def has_draft() -> bool:
    with get_session() as session:
        return session.scalar(select(SnapshotDraft).limit(1)) is not None


def get_draft_meta() -> dict[str, Any] | None:
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            return None
        return {
            "id": draft.id,
            "as_of_date": draft.as_of_date,
            "created_at": draft.created_at,
            "updated_at": draft.updated_at,
            "notes": draft.notes,
        }


def _touch(draft: SnapshotDraft) -> None:
    draft.updated_at = datetime.now(timezone.utc)


def _latest_committed_balances(session) -> dict[int, float]:
    rows = session.scalars(select(BalanceSnapshot)).all()
    latest: dict[int, tuple[date, float]] = {}
    for row in rows:
        prev = latest.get(row.account_id)
        if prev is None or row.as_of_date > prev[0]:
            latest[row.account_id] = (row.as_of_date, row.balance)
    return {account_id: bal for account_id, (_, bal) in latest.items()}


def start_draft(as_of_date: date | None = None) -> dict[str, Any]:
    """Open a new draft session, replacing any existing draft."""
    as_of = as_of_date or date.today()
    with get_session() as session:
        for existing in list(session.scalars(select(SnapshotDraft)).all()):
            session.delete(existing)
        session.flush()

        draft = SnapshotDraft(as_of_date=as_of)
        session.add(draft)
        session.flush()

        accounts = list(
            session.scalars(
                select(Account).where(Account.active.is_(True)).order_by(Account.name)
            ).all()
        )
        latest = _latest_committed_balances(session)
        for index, account in enumerate(accounts):
            session.add(
                SnapshotDraftBalance(
                    draft_id=draft.id,
                    account_id=account.id,
                    temp_key=None,
                    balance=latest.get(account.id),
                )
            )
            _ = index
        session.flush()
        session.refresh(draft)
        return {
            "id": draft.id,
            "as_of_date": draft.as_of_date,
            "updated_at": draft.updated_at,
        }


def discard_draft() -> None:
    with get_session() as session:
        for existing in list(session.scalars(select(SnapshotDraft)).all()):
            session.delete(existing)


def set_as_of_date(as_of_date: date) -> None:
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            raise ValueError("No open snapshot session")
        draft.as_of_date = as_of_date
        _touch(draft)


def set_balance(
    *,
    balance: float | None,
    account_id: int | None = None,
    temp_key: str | None = None,
) -> None:
    if account_id is None and not temp_key:
        raise ValueError("account_id or temp_key is required")
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            raise ValueError("No open snapshot session")
        row = _find_balance(session, draft.id, account_id=account_id, temp_key=temp_key)
        if row is None:
            row = SnapshotDraftBalance(
                draft_id=draft.id,
                account_id=account_id,
                temp_key=temp_key,
            )
            session.add(row)
        row.balance = None if balance is None else float(balance)
        _touch(draft)


def _find_balance(
    session,
    draft_id: int,
    *,
    account_id: int | None,
    temp_key: str | None,
) -> SnapshotDraftBalance | None:
    stmt = select(SnapshotDraftBalance).where(SnapshotDraftBalance.draft_id == draft_id)
    if account_id is not None:
        stmt = stmt.where(SnapshotDraftBalance.account_id == account_id)
    else:
        stmt = stmt.where(SnapshotDraftBalance.temp_key == temp_key)
    return session.scalar(stmt)


def add_draft_account(
    name: str,
    account_type: AccountType | str,
    *,
    provider: str | None = None,
    notes: str | None = None,
    opening_balance: float | None = None,
) -> str:
    """Queue a new account in the draft. Returns temp_key."""
    if isinstance(account_type, str):
        account_type = AccountType(account_type)
    temp_key = uuid.uuid4().hex[:12]
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            raise ValueError("No open snapshot session")
        count = len(list(session.scalars(
            select(SnapshotDraftAccount).where(SnapshotDraftAccount.draft_id == draft.id)
        ).all()))
        session.add(
            SnapshotDraftAccount(
                draft_id=draft.id,
                op="create",
                temp_key=temp_key,
                account_id=None,
                name=name.strip(),
                account_type=account_type.value,
                provider=provider,
                notes=notes,
                sort_order=count,
            )
        )
        session.add(
            SnapshotDraftBalance(
                draft_id=draft.id,
                account_id=None,
                temp_key=temp_key,
                balance=opening_balance,
            )
        )
        _touch(draft)
    return temp_key


def rename_draft_row(
    *,
    account_id: int | None = None,
    temp_key: str | None = None,
    name: str,
) -> None:
    name = name.strip()
    if not name:
        raise ValueError("Name is required")
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            raise ValueError("No open snapshot session")
        if temp_key:
            row = session.scalar(
                select(SnapshotDraftAccount).where(
                    SnapshotDraftAccount.draft_id == draft.id,
                    SnapshotDraftAccount.temp_key == temp_key,
                )
            )
            if row is None:
                raise ValueError("Draft account not found")
            row.name = name
        elif account_id is not None:
            row = session.scalar(
                select(SnapshotDraftAccount).where(
                    SnapshotDraftAccount.draft_id == draft.id,
                    SnapshotDraftAccount.account_id == account_id,
                )
            )
            if row is None:
                session.add(
                    SnapshotDraftAccount(
                        draft_id=draft.id,
                        op="update",
                        temp_key=None,
                        account_id=account_id,
                        name=name,
                        account_type=None,
                    )
                )
            else:
                row.op = "deactivate" if row.op == "deactivate" else "update"
                row.name = name
        else:
            raise ValueError("account_id or temp_key is required")
        _touch(draft)


def deactivate_draft_account(
    *,
    account_id: int | None = None,
    temp_key: str | None = None,
) -> None:
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            raise ValueError("No open snapshot session")
        if temp_key:
            row = session.scalar(
                select(SnapshotDraftAccount).where(
                    SnapshotDraftAccount.draft_id == draft.id,
                    SnapshotDraftAccount.temp_key == temp_key,
                )
            )
            if row is not None:
                session.delete(row)
            bal = _find_balance(session, draft.id, account_id=None, temp_key=temp_key)
            if bal is not None:
                session.delete(bal)
        elif account_id is not None:
            row = session.scalar(
                select(SnapshotDraftAccount).where(
                    SnapshotDraftAccount.draft_id == draft.id,
                    SnapshotDraftAccount.account_id == account_id,
                )
            )
            if row is None:
                session.add(
                    SnapshotDraftAccount(
                        draft_id=draft.id,
                        op="deactivate",
                        temp_key=None,
                        account_id=account_id,
                    )
                )
            else:
                row.op = "deactivate"
            bal = _find_balance(session, draft.id, account_id=account_id, temp_key=None)
            if bal is not None:
                session.delete(bal)
        else:
            raise ValueError("account_id or temp_key is required")
        _touch(draft)


def effective_accounts_and_balances() -> dict[str, Any] | None:
    """Merged spreadsheet rows for UI and chart overlay."""
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            return None

        committed = {
            a.id: a
            for a in session.scalars(select(Account).where(Account.active.is_(True))).all()
        }
        draft_accounts = list(
            session.scalars(
                select(SnapshotDraftAccount).where(
                    SnapshotDraftAccount.draft_id == draft.id
                )
            ).all()
        )
        draft_balances = list(
            session.scalars(
                select(SnapshotDraftBalance).where(
                    SnapshotDraftBalance.draft_id == draft.id
                )
            ).all()
        )

        deactivated = {
            row.account_id
            for row in draft_accounts
            if row.op == "deactivate" and row.account_id is not None
        }
        renames = {
            row.account_id: row.name
            for row in draft_accounts
            if row.op == "update" and row.account_id is not None and row.name
        }
        type_overrides = {
            row.account_id: row.account_type
            for row in draft_accounts
            if row.op == "update" and row.account_id is not None and row.account_type
        }

        bal_by_account = {
            row.account_id: row.balance
            for row in draft_balances
            if row.account_id is not None
        }
        bal_by_temp = {
            row.temp_key: row.balance
            for row in draft_balances
            if row.temp_key is not None
        }

        rows: list[dict[str, Any]] = []
        for account in sorted(committed.values(), key=lambda a: a.name.lower()):
            if account.id in deactivated:
                continue
            atype = type_overrides.get(account.id) or account.account_type.value
            try:
                atype_enum = AccountType(atype)
            except ValueError:
                atype_enum = account.account_type
            rows.append(
                {
                    "key": f"a:{account.id}",
                    "account_id": account.id,
                    "temp_key": None,
                    "name": renames.get(account.id) or account.name,
                    "account_type": atype_enum.value,
                    "account_type_label": ACCOUNT_TYPE_LABELS.get(
                        atype_enum, atype_enum.value
                    ),
                    "is_liability": atype_enum in LIABILITY_TYPES,
                    "balance": bal_by_account.get(account.id),
                    "is_new": False,
                    "active": True,
                }
            )

        creates = [
            row
            for row in draft_accounts
            if row.op == "create" and row.temp_key
        ]
        creates.sort(key=lambda r: (r.sort_order, r.id))
        for row in creates:
            try:
                atype_enum = AccountType(row.account_type or AccountType.OTHER.value)
            except ValueError:
                atype_enum = AccountType.OTHER
            rows.append(
                {
                    "key": f"t:{row.temp_key}",
                    "account_id": None,
                    "temp_key": row.temp_key,
                    "name": row.name or "New account",
                    "account_type": atype_enum.value,
                    "account_type_label": ACCOUNT_TYPE_LABELS.get(
                        atype_enum, atype_enum.value
                    ),
                    "is_liability": atype_enum in LIABILITY_TYPES,
                    "balance": bal_by_temp.get(row.temp_key),
                    "is_new": True,
                    "active": True,
                }
            )

        return {
            "as_of_date": draft.as_of_date,
            "updated_at": draft.updated_at,
            "rows": rows,
        }


def missing_balances() -> list[str]:
    state = effective_accounts_and_balances()
    if state is None:
        return []
    return [
        row["name"]
        for row in state["rows"]
        if row["balance"] is None
    ]


def commit_draft() -> dict[str, Any]:
    """Apply draft account ops and balances, then clear the draft."""
    missing = missing_balances()
    if missing:
        raise ValueError(
            "Every active account needs a balance before saving. Missing: "
            + ", ".join(missing[:8])
            + ("…" if len(missing) > 8 else "")
        )

    state = effective_accounts_and_balances()
    if state is None:
        raise ValueError("No open snapshot session")

    as_of = state["as_of_date"]
    temp_to_id: dict[str, int] = {}

    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            raise ValueError("No open snapshot session")
        draft_accounts = list(
            session.scalars(
                select(SnapshotDraftAccount).where(
                    SnapshotDraftAccount.draft_id == draft.id
                )
            ).all()
        )

    for row in draft_accounts:
        if row.op == "create" and row.temp_key:
            created = account_service.create_account(
                row.name or "New account",
                row.account_type or AccountType.OTHER.value,
                provider=row.provider,
                notes=row.notes,
            )
            temp_to_id[row.temp_key] = created.id
        elif row.op == "update" and row.account_id is not None:
            kwargs: dict[str, Any] = {}
            if row.name:
                kwargs["name"] = row.name
            if row.account_type:
                kwargs["account_type"] = row.account_type
            if kwargs:
                account_service.update_account(row.account_id, **kwargs)
        elif row.op == "deactivate" and row.account_id is not None:
            account_service.update_account(row.account_id, active=False)

    balances: dict[int, float] = {}
    for row in state["rows"]:
        if row["balance"] is None:
            continue
        if row["account_id"] is not None:
            balances[int(row["account_id"])] = float(row["balance"])
        elif row["temp_key"] and row["temp_key"] in temp_to_id:
            balances[temp_to_id[row["temp_key"]]] = float(row["balance"])

    count = snapshot_service.record_balances_for_date(as_of, balances)
    discard_draft()
    return {"as_of_date": as_of, "balances_written": count, "accounts_created": len(temp_to_id)}
