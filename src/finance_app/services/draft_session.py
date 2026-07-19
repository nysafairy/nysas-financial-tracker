"""Draft snapshot editing session — autosaved until commit or discard."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select

from finance_app.db.models import (
    ACCESS_TYPE_LABELS,
    ACCOUNT_TYPE_LABELS,
    DEFAULT_ACCESS_FOR_TYPE,
    INTEREST_FREQUENCY_LABELS,
    LIABILITY_TYPES,
    PREMIUM_BONDS_ASSUMED_RATE_PCT,
    AccessType,
    Account,
    AccountType,
    BalanceSnapshot,
    InterestFrequency,
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


def _balances_on_date(session, as_of: date) -> dict[int, float]:
    rows = session.scalars(
        select(BalanceSnapshot).where(BalanceSnapshot.as_of_date == as_of)
    ).all()
    return {row.account_id: float(row.balance) for row in rows}


def start_draft(
    as_of_date: date | None = None,
    *,
    seed_from_history: bool = False,
) -> dict[str, Any]:
    """
    Open a new draft session, replacing any existing draft.

    When seed_from_history is False (default), balances come from each active
    account's latest committed snapshot (new snapshot workflow).

    When seed_from_history is True, balances come from the exact as_of_date
    (reopen / edit past snapshot). Includes accounts that had a balance that day
    even if later deactivated; active accounts with no row that day get empty
    balances.
    """
    as_of = as_of_date or date.today()
    with get_session() as session:
        for existing in list(session.scalars(select(SnapshotDraft)).all()):
            session.delete(existing)
        session.flush()

        draft = SnapshotDraft(as_of_date=as_of)
        session.add(draft)
        session.flush()

        if seed_from_history:
            dated = _balances_on_date(session, as_of)
            account_ids = set(dated.keys())
            for account in session.scalars(
                select(Account).where(Account.active.is_(True))
            ).all():
                account_ids.add(account.id)
            by_id = {a.id: a for a in session.scalars(select(Account)).all()}
            accounts = sorted(
                [by_id[i] for i in account_ids if i in by_id],
                key=lambda a: a.name.lower(),
            )
            for account in accounts:
                session.add(
                    SnapshotDraftBalance(
                        draft_id=draft.id,
                        account_id=account.id,
                        temp_key=None,
                        balance=dated.get(account.id),
                    )
                )
        else:
            accounts = list(
                session.scalars(
                    select(Account).where(Account.active.is_(True)).order_by(Account.name)
                ).all()
            )
            latest = _latest_committed_balances(session)
            for account in accounts:
                session.add(
                    SnapshotDraftBalance(
                        draft_id=draft.id,
                        account_id=account.id,
                        temp_key=None,
                        balance=latest.get(account.id),
                    )
                )

        session.flush()
        session.refresh(draft)
        return {
            "id": draft.id,
            "as_of_date": draft.as_of_date,
            "updated_at": draft.updated_at,
        }


def start_draft_for_date(as_of_date: date) -> dict[str, Any]:
    """Reopen a past snapshot date for editing."""
    return start_draft(as_of_date, seed_from_history=True)


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


def _find_or_create_update_op(
    session,
    draft: SnapshotDraft,
    *,
    account_id: int | None,
    temp_key: str | None,
) -> SnapshotDraftAccount:
    if temp_key:
        row = session.scalar(
            select(SnapshotDraftAccount).where(
                SnapshotDraftAccount.draft_id == draft.id,
                SnapshotDraftAccount.temp_key == temp_key,
            )
        )
        if row is None:
            raise ValueError("Draft account not found")
        return row
    if account_id is None:
        raise ValueError("account_id or temp_key is required")
    row = session.scalar(
        select(SnapshotDraftAccount).where(
            SnapshotDraftAccount.draft_id == draft.id,
            SnapshotDraftAccount.account_id == account_id,
        )
    )
    if row is None:
        row = SnapshotDraftAccount(
            draft_id=draft.id,
            op="update",
            temp_key=None,
            account_id=account_id,
        )
        session.add(row)
        session.flush()
    elif row.op != "deactivate":
        row.op = "update"
    return row


def add_draft_account(
    name: str,
    account_type: AccountType | str,
    *,
    provider: str | None = None,
    notes: str | None = None,
    account_number: str | None = None,
    sort_code: str | None = None,
    interest_rate_pct: float | None = None,
    interest_frequency: str | None = None,
    access_type: str | None = None,
    notice_days: int | None = None,
    maturity_date: date | None = None,
    opened_date: date | None = None,
    opening_balance: float | None = None,
) -> str:
    """Queue a new account in the draft. Returns temp_key."""
    if isinstance(account_type, str):
        account_type = AccountType(account_type)
    if not access_type and account_type in DEFAULT_ACCESS_FOR_TYPE:
        access_type = DEFAULT_ACCESS_FOR_TYPE[account_type].value
    if account_type == AccountType.PREMIUM_BONDS:
        if not interest_frequency:
            interest_frequency = InterestFrequency.NONE.value
        if interest_rate_pct is None:
            interest_rate_pct = PREMIUM_BONDS_ASSUMED_RATE_PCT
    temp_key = uuid.uuid4().hex[:12]
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            raise ValueError("No open snapshot session")
        count = len(
            list(
                session.scalars(
                    select(SnapshotDraftAccount).where(
                        SnapshotDraftAccount.draft_id == draft.id
                    )
                ).all()
            )
        )
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
                account_number=account_number,
                sort_code=sort_code,
                interest_rate_pct=interest_rate_pct,
                interest_frequency=interest_frequency,
                access_type=access_type,
                notice_days=notice_days,
                maturity_date=maturity_date,
                opened_date=opened_date,
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


def update_draft_account_fields(
    *,
    account_id: int | None = None,
    temp_key: str | None = None,
    name: str | None = None,
    account_type: str | None = None,
    provider: str | None = None,
    notes: str | None = None,
    account_number: str | None = None,
    sort_code: str | None = None,
    interest_rate_pct: float | None = None,
    clear_interest_rate: bool = False,
    interest_frequency: str | None = None,
    access_type: str | None = None,
    notice_days: int | None = None,
    clear_notice_days: bool = False,
    maturity_date: date | None = None,
    clear_maturity_date: bool = False,
    opened_date: date | None = None,
    clear_opened_date: bool = False,
) -> None:
    """Autosave account metadata changes into the draft ops table."""
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            raise ValueError("No open snapshot session")
        row = _find_or_create_update_op(
            session, draft, account_id=account_id, temp_key=temp_key
        )
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise ValueError("Name is required")
            row.name = cleaned
        if account_type is not None:
            row.account_type = account_type
            try:
                atype = AccountType(account_type)
            except ValueError:
                atype = None
            if atype is not None and access_type is None and atype in DEFAULT_ACCESS_FOR_TYPE:
                row.access_type = DEFAULT_ACCESS_FOR_TYPE[atype].value
            if atype == AccountType.PREMIUM_BONDS:
                if interest_frequency is None and not row.interest_frequency:
                    row.interest_frequency = InterestFrequency.NONE.value
                if (
                    not clear_interest_rate
                    and interest_rate_pct is None
                    and row.interest_rate_pct is None
                    and not row.clear_interest_rate
                ):
                    # Prefer live account rate when updating an existing row.
                    existing_rate = None
                    if row.account_id is not None:
                        live = session.get(Account, row.account_id)
                        if live is not None:
                            existing_rate = live.interest_rate_pct
                    if existing_rate is None:
                        row.interest_rate_pct = PREMIUM_BONDS_ASSUMED_RATE_PCT
                        row.clear_interest_rate = False
        if provider is not None:
            row.provider = provider or None
        if notes is not None:
            row.notes = notes or None
        if account_number is not None:
            row.account_number = account_number or None
        if sort_code is not None:
            row.sort_code = sort_code or None
        if clear_interest_rate:
            row.interest_rate_pct = None
            row.clear_interest_rate = True
        elif interest_rate_pct is not None:
            row.interest_rate_pct = float(interest_rate_pct)
            row.clear_interest_rate = False
        if interest_frequency is not None:
            row.interest_frequency = interest_frequency or None
        if access_type is not None:
            row.access_type = access_type or None
        if clear_notice_days:
            row.notice_days = None
            row.clear_notice_days = True
        elif notice_days is not None:
            row.notice_days = int(notice_days)
            row.clear_notice_days = False
        if clear_maturity_date:
            row.maturity_date = None
            row.clear_maturity_date = True
        elif maturity_date is not None:
            row.maturity_date = maturity_date
            row.clear_maturity_date = False
        if clear_opened_date:
            row.opened_date = None
            row.clear_opened_date = True
        elif opened_date is not None:
            row.opened_date = opened_date
            row.clear_opened_date = False
        _touch(draft)


def rename_draft_row(
    *,
    account_id: int | None = None,
    temp_key: str | None = None,
    name: str,
) -> None:
    update_draft_account_fields(
        account_id=account_id, temp_key=temp_key, name=name
    )


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


def _merge_account_fields(
    account: Account | None,
    draft_row: SnapshotDraftAccount | None,
) -> dict[str, Any]:
    """Effective display fields for a spreadsheet row."""
    if account is not None:
        base = {
            "name": account.name,
            "account_type": account.account_type.value,
            "provider": account.provider or "",
            "notes": account.notes or "",
            "account_number": account.account_number or "",
            "sort_code": account.sort_code or "",
            "interest_rate_pct": account.interest_rate_pct,
            "interest_frequency": (
                account.interest_frequency.value if account.interest_frequency else ""
            ),
            "access_type": account.access_type.value if account.access_type else "",
            "notice_days": account.notice_days,
            "maturity_date": account.maturity_date,
            "opened_date": account.opened_date,
        }
    else:
        base = {
            "name": "New account",
            "account_type": AccountType.OTHER.value,
            "provider": "",
            "notes": "",
            "account_number": "",
            "sort_code": "",
            "interest_rate_pct": None,
            "interest_frequency": "",
            "access_type": "",
            "notice_days": None,
            "maturity_date": None,
            "opened_date": None,
        }

    if draft_row is None:
        return base

    if draft_row.name:
        base["name"] = draft_row.name
    if draft_row.account_type:
        base["account_type"] = draft_row.account_type
    if draft_row.provider is not None:
        base["provider"] = draft_row.provider or ""
    if draft_row.notes is not None:
        base["notes"] = draft_row.notes or ""
    if draft_row.account_number is not None:
        base["account_number"] = draft_row.account_number or ""
    if draft_row.sort_code is not None:
        base["sort_code"] = draft_row.sort_code or ""
    if draft_row.clear_interest_rate:
        base["interest_rate_pct"] = None
    elif draft_row.interest_rate_pct is not None:
        base["interest_rate_pct"] = draft_row.interest_rate_pct
    if draft_row.interest_frequency is not None:
        base["interest_frequency"] = draft_row.interest_frequency or ""
    if draft_row.access_type is not None:
        base["access_type"] = draft_row.access_type or ""
    if getattr(draft_row, "clear_notice_days", False):
        base["notice_days"] = None
    elif draft_row.notice_days is not None:
        base["notice_days"] = draft_row.notice_days
    if getattr(draft_row, "clear_maturity_date", False):
        base["maturity_date"] = None
    elif draft_row.maturity_date is not None:
        base["maturity_date"] = draft_row.maturity_date
    if getattr(draft_row, "clear_opened_date", False):
        base["opened_date"] = None
    elif draft_row.opened_date is not None:
        base["opened_date"] = draft_row.opened_date
    return base


def effective_accounts_and_balances() -> dict[str, Any] | None:
    """Merged spreadsheet rows for UI and chart overlay."""
    with get_session() as session:
        draft = session.scalar(select(SnapshotDraft).limit(1))
        if draft is None:
            return None

        all_accounts = {
            a.id: a for a in session.scalars(select(Account)).all()
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
        updates_by_id = {
            row.account_id: row
            for row in draft_accounts
            if row.op == "update" and row.account_id is not None
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

        # Existing accounts present in the draft sheet (active, or inactive but seeded).
        sheet_account_ids = {
            row.account_id
            for row in draft_balances
            if row.account_id is not None
        }
        for account_id, account in all_accounts.items():
            if account.active and account_id not in deactivated:
                sheet_account_ids.add(account_id)

        rows: list[dict[str, Any]] = []
        for account_id in sorted(
            sheet_account_ids,
            key=lambda i: (all_accounts[i].name.lower() if i in all_accounts else ""),
        ):
            if account_id in deactivated:
                continue
            account = all_accounts.get(account_id)
            if account is None:
                continue
            fields = _merge_account_fields(account, updates_by_id.get(account_id))
            try:
                atype_enum = AccountType(fields["account_type"])
            except ValueError:
                atype_enum = account.account_type
            access_val = fields["access_type"]
            try:
                access_label = (
                    ACCESS_TYPE_LABELS[AccessType(access_val)] if access_val else ""
                )
            except ValueError:
                access_label = access_val
            freq_val = fields["interest_frequency"]
            try:
                freq_label = (
                    INTEREST_FREQUENCY_LABELS[InterestFrequency(freq_val)]
                    if freq_val
                    else ""
                )
            except ValueError:
                freq_label = freq_val
            rows.append(
                {
                    "key": f"a:{account.id}",
                    "account_id": account.id,
                    "temp_key": None,
                    "name": fields["name"],
                    "account_type": atype_enum.value,
                    "account_type_label": ACCOUNT_TYPE_LABELS.get(
                        atype_enum, atype_enum.value
                    ),
                    "is_liability": atype_enum in LIABILITY_TYPES,
                    "balance": bal_by_account.get(account.id),
                    "is_new": False,
                    "active": account.active,
                    "provider": fields["provider"],
                    "notes": fields["notes"],
                    "account_number": fields["account_number"],
                    "sort_code": fields["sort_code"],
                    "interest_rate_pct": fields["interest_rate_pct"],
                    "interest_frequency": fields["interest_frequency"],
                    "interest_frequency_label": freq_label,
                    "access_type": fields["access_type"],
                    "access_type_label": access_label,
                    "notice_days": fields["notice_days"],
                    "maturity_date": fields["maturity_date"],
                    "opened_date": fields["opened_date"],
                }
            )

        creates = [
            row
            for row in draft_accounts
            if row.op == "create" and row.temp_key
        ]
        creates.sort(key=lambda r: (r.sort_order, r.id))
        for row in creates:
            fields = _merge_account_fields(None, row)
            try:
                atype_enum = AccountType(fields["account_type"])
            except ValueError:
                atype_enum = AccountType.OTHER
            access_val = fields["access_type"]
            try:
                access_label = (
                    ACCESS_TYPE_LABELS[AccessType(access_val)] if access_val else ""
                )
            except ValueError:
                access_label = access_val
            freq_val = fields["interest_frequency"]
            try:
                freq_label = (
                    INTEREST_FREQUENCY_LABELS[InterestFrequency(freq_val)]
                    if freq_val
                    else ""
                )
            except ValueError:
                freq_label = freq_val
            rows.append(
                {
                    "key": f"t:{row.temp_key}",
                    "account_id": None,
                    "temp_key": row.temp_key,
                    "name": fields["name"],
                    "account_type": atype_enum.value,
                    "account_type_label": ACCOUNT_TYPE_LABELS.get(
                        atype_enum, atype_enum.value
                    ),
                    "is_liability": atype_enum in LIABILITY_TYPES,
                    "balance": bal_by_temp.get(row.temp_key),
                    "is_new": True,
                    "active": True,
                    "provider": fields["provider"],
                    "notes": fields["notes"],
                    "account_number": fields["account_number"],
                    "sort_code": fields["sort_code"],
                    "interest_rate_pct": fields["interest_rate_pct"],
                    "interest_frequency": fields["interest_frequency"],
                    "interest_frequency_label": freq_label,
                    "access_type": fields["access_type"],
                    "access_type_label": access_label,
                    "notice_days": fields["notice_days"],
                    "maturity_date": fields["maturity_date"],
                    "opened_date": fields["opened_date"],
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


def _create_kwargs_from_draft(row: SnapshotDraftAccount) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "provider": row.provider,
        "notes": row.notes,
        "account_number": row.account_number,
        "sort_code": row.sort_code,
        "interest_rate_pct": row.interest_rate_pct,
        "interest_frequency": row.interest_frequency,
        "access_type": row.access_type,
        "notice_days": row.notice_days,
        "maturity_date": row.maturity_date,
        "opened_date": row.opened_date,
    }
    return {
        k: v
        for k, v in kwargs.items()
        if v is not None and v != ""
    }


def _update_kwargs_from_draft(row: SnapshotDraftAccount) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if row.name:
        kwargs["name"] = row.name
    if row.account_type:
        kwargs["account_type"] = row.account_type
    if row.provider is not None:
        kwargs["provider"] = row.provider
    if row.notes is not None:
        kwargs["notes"] = row.notes
    if row.account_number is not None:
        kwargs["account_number"] = row.account_number
    if row.sort_code is not None:
        kwargs["sort_code"] = row.sort_code
    if row.clear_interest_rate:
        kwargs["clear_interest_rate"] = True
    elif row.interest_rate_pct is not None:
        kwargs["interest_rate_pct"] = row.interest_rate_pct
    if row.interest_frequency is not None:
        kwargs["interest_frequency"] = row.interest_frequency
    if row.access_type is not None:
        kwargs["access_type"] = row.access_type
    if getattr(row, "clear_notice_days", False):
        kwargs["clear_notice_days"] = True
    elif row.notice_days is not None:
        kwargs["notice_days"] = row.notice_days
    if getattr(row, "clear_maturity_date", False):
        kwargs["clear_maturity_date"] = True
    elif row.maturity_date is not None:
        kwargs["maturity_date"] = row.maturity_date
    if getattr(row, "clear_opened_date", False):
        kwargs["clear_opened_date"] = True
    elif row.opened_date is not None:
        kwargs["opened_date"] = row.opened_date
    return kwargs


def commit_draft() -> dict[str, Any]:
    """Apply draft account ops and balances in one DB transaction, then clear draft."""
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
    balance_rows = list(state["rows"])
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
        ops = [
            {
                "op": row.op,
                "temp_key": row.temp_key,
                "account_id": row.account_id,
                "name": row.name,
                "account_type": row.account_type,
                "create_kwargs": _create_kwargs_from_draft(row),
                "update_kwargs": _update_kwargs_from_draft(row),
            }
            for row in draft_accounts
        ]

        for row in ops:
            if row["op"] == "create" and row["temp_key"]:
                created = account_service.create_account(
                    row["name"] or "New account",
                    row["account_type"] or AccountType.OTHER.value,
                    session=session,
                    **row["create_kwargs"],
                )
                temp_to_id[row["temp_key"]] = created.id
            elif row["op"] == "update" and row["account_id"] is not None:
                kwargs = row["update_kwargs"]
                if kwargs:
                    account_service.update_account(
                        row["account_id"], session=session, **kwargs
                    )
            elif row["op"] == "deactivate" and row["account_id"] is not None:
                account_service.update_account(
                    row["account_id"], active=False, session=session
                )

        balances: dict[int, float] = {}
        for row in balance_rows:
            if row["balance"] is None:
                continue
            if row["account_id"] is not None:
                balances[int(row["account_id"])] = float(row["balance"])
            elif row["temp_key"] and row["temp_key"] in temp_to_id:
                balances[temp_to_id[row["temp_key"]]] = float(row["balance"])

        count = snapshot_service.record_balances_for_date(
            as_of, balances, session=session
        )

        for existing in list(session.scalars(select(SnapshotDraft)).all()):
            session.delete(existing)

    return {
        "as_of_date": as_of,
        "balances_written": count,
        "accounts_created": len(temp_to_id),
    }
