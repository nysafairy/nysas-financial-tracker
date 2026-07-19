"""Account and transaction CRUD."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from finance_app.db.models import (
    DEFAULT_ACCESS_FOR_TYPE,
    DEPRECATED_INCOME_TRANSACTION_TYPES,
    PREMIUM_BONDS_ASSUMED_RATE_PCT,
    AccessType,
    Account,
    AccountType,
    InterestFrequency,
    Transaction,
    TransactionType,
)
from finance_app.db.session import get_session


def _premium_bonds_defaults(
    account_type: AccountType,
    interest_rate_pct: float | None,
    interest_frequency: InterestFrequency | None,
) -> tuple[float | None, InterestFrequency | None]:
    if account_type != AccountType.PREMIUM_BONDS:
        return interest_rate_pct, interest_frequency
    if interest_frequency is None:
        interest_frequency = InterestFrequency.NONE
    if interest_rate_pct is None:
        interest_rate_pct = PREMIUM_BONDS_ASSUMED_RATE_PCT
    return interest_rate_pct, interest_frequency


def list_accounts(*, active_only: bool = False) -> list[Account]:
    with get_session() as session:
        stmt = select(Account).order_by(Account.name)
        if active_only:
            stmt = stmt.where(Account.active.is_(True))
        return list(session.scalars(stmt).unique().all())


def _resolve_access(
    account_type: AccountType,
    access_type: AccessType | str | None,
) -> AccessType | None:
    if isinstance(access_type, str):
        if not access_type:
            access_type = None
        else:
            return AccessType(access_type)
    if access_type is not None:
        return access_type
    return DEFAULT_ACCESS_FOR_TYPE.get(account_type)


def _create_account(
    session: Session,
    name: str,
    account_type: AccountType,
    *,
    currency: str = "GBP",
    notes: str | None = None,
    provider: str | None = None,
    account_number: str | None = None,
    sort_code: str | None = None,
    interest_rate_pct: float | None = None,
    interest_frequency: InterestFrequency | None = None,
    access_type: AccessType | None = None,
    notice_days: int | None = None,
    maturity_date: date | None = None,
    opened_date: date | None = None,
) -> Account:
    interest_rate_pct, interest_frequency = _premium_bonds_defaults(
        account_type, interest_rate_pct, interest_frequency
    )
    account = Account(
        name=name.strip(),
        account_type=account_type,
        currency=currency.upper(),
        notes=notes,
        provider=(provider or None),
        account_number=(account_number or None),
        sort_code=(sort_code or None),
        interest_rate_pct=interest_rate_pct,
        interest_frequency=interest_frequency,
        access_type=access_type,
        notice_days=notice_days,
        maturity_date=maturity_date,
        opened_date=opened_date,
        active=True,
    )
    session.add(account)
    session.flush()
    return account


def create_account(
    name: str,
    account_type: AccountType | str,
    *,
    currency: str = "GBP",
    notes: str | None = None,
    provider: str | None = None,
    account_number: str | None = None,
    sort_code: str | None = None,
    interest_rate_pct: float | None = None,
    interest_frequency: InterestFrequency | str | None = None,
    access_type: AccessType | str | None = None,
    notice_days: int | None = None,
    maturity_date: date | None = None,
    opened_date: date | None = None,
    session: Session | None = None,
) -> Account:
    if isinstance(account_type, str):
        account_type = AccountType(account_type)
    if isinstance(interest_frequency, str) and interest_frequency:
        interest_frequency = InterestFrequency(interest_frequency)
    elif not interest_frequency:
        interest_frequency = None
    resolved_access = _resolve_access(account_type, access_type)

    def _run(sess: Session) -> Account:
        account = _create_account(
            sess,
            name,
            account_type,
            currency=currency,
            notes=notes,
            provider=provider,
            account_number=account_number,
            sort_code=sort_code,
            interest_rate_pct=interest_rate_pct,
            interest_frequency=interest_frequency,
            access_type=resolved_access,
            notice_days=notice_days,
            maturity_date=maturity_date,
            opened_date=opened_date,
        )
        sess.refresh(account)
        sess.expunge(account)
        return account

    if session is not None:
        account = _create_account(
            session,
            name,
            account_type,
            currency=currency,
            notes=notes,
            provider=provider,
            account_number=account_number,
            sort_code=sort_code,
            interest_rate_pct=interest_rate_pct,
            interest_frequency=interest_frequency,
            access_type=resolved_access,
            notice_days=notice_days,
            maturity_date=maturity_date,
            opened_date=opened_date,
        )
        return account
    with get_session() as sess:
        return _run(sess)


def _update_account(
    session: Session,
    account_id: int,
    *,
    name: str | None = None,
    account_type: AccountType | str | None = None,
    notes: str | None = None,
    active: bool | None = None,
    provider: str | None = None,
    account_number: str | None = None,
    sort_code: str | None = None,
    interest_rate_pct: float | None = None,
    interest_frequency: InterestFrequency | str | None = None,
    access_type: AccessType | str | None = None,
    notice_days: int | None = None,
    maturity_date: date | None = None,
    opened_date: date | None = None,
    clear_interest_rate: bool = False,
    clear_maturity_date: bool = False,
    clear_opened_date: bool = False,
    clear_notice_days: bool = False,
) -> None:
    account = session.get(Account, account_id)
    if account is None:
        raise ValueError("Account not found")
    if name is not None:
        account.name = name.strip()
    if account_type is not None:
        account.account_type = (
            AccountType(account_type) if isinstance(account_type, str) else account_type
        )
        if access_type is None and account.account_type in DEFAULT_ACCESS_FOR_TYPE:
            account.access_type = DEFAULT_ACCESS_FOR_TYPE[account.account_type]
        if account.account_type == AccountType.PREMIUM_BONDS:
            if interest_frequency is None and account.interest_frequency is None:
                account.interest_frequency = InterestFrequency.NONE
            if (
                not clear_interest_rate
                and interest_rate_pct is None
                and account.interest_rate_pct is None
            ):
                account.interest_rate_pct = PREMIUM_BONDS_ASSUMED_RATE_PCT
    if notes is not None:
        account.notes = notes
    if active is not None:
        account.active = active
    if provider is not None:
        account.provider = provider or None
    if account_number is not None:
        account.account_number = account_number or None
    if sort_code is not None:
        account.sort_code = sort_code or None
    if clear_interest_rate:
        account.interest_rate_pct = None
    elif interest_rate_pct is not None:
        account.interest_rate_pct = interest_rate_pct
    if interest_frequency is not None:
        account.interest_frequency = (
            InterestFrequency(interest_frequency)
            if isinstance(interest_frequency, str) and interest_frequency
            else interest_frequency or None
        )
    if access_type is not None:
        account.access_type = (
            AccessType(access_type)
            if isinstance(access_type, str) and access_type
            else access_type or None
        )
    if clear_notice_days:
        account.notice_days = None
    elif notice_days is not None:
        account.notice_days = notice_days if notice_days != "" else None
    if clear_maturity_date:
        account.maturity_date = None
    elif maturity_date is not None:
        account.maturity_date = maturity_date
    if clear_opened_date:
        account.opened_date = None
    elif opened_date is not None:
        account.opened_date = opened_date


def update_account(
    account_id: int,
    *,
    name: str | None = None,
    account_type: AccountType | str | None = None,
    notes: str | None = None,
    active: bool | None = None,
    provider: str | None = None,
    account_number: str | None = None,
    sort_code: str | None = None,
    interest_rate_pct: float | None = None,
    interest_frequency: InterestFrequency | str | None = None,
    access_type: AccessType | str | None = None,
    notice_days: int | None = None,
    maturity_date: date | None = None,
    opened_date: date | None = None,
    clear_interest_rate: bool = False,
    clear_maturity_date: bool = False,
    clear_opened_date: bool = False,
    clear_notice_days: bool = False,
    session: Session | None = None,
) -> None:
    kwargs = dict(
        name=name,
        account_type=account_type,
        notes=notes,
        active=active,
        provider=provider,
        account_number=account_number,
        sort_code=sort_code,
        interest_rate_pct=interest_rate_pct,
        interest_frequency=interest_frequency,
        access_type=access_type,
        notice_days=notice_days,
        maturity_date=maturity_date,
        opened_date=opened_date,
        clear_interest_rate=clear_interest_rate,
        clear_maturity_date=clear_maturity_date,
        clear_opened_date=clear_opened_date,
        clear_notice_days=clear_notice_days,
    )
    if session is not None:
        _update_account(session, account_id, **kwargs)
        return
    with get_session() as sess:
        _update_account(sess, account_id, **kwargs)


def delete_account(account_id: int) -> None:
    with get_session() as session:
        account = session.get(Account, account_id)
        if account is None:
            return
        session.delete(account)


def list_transactions(limit: int = 200) -> list[Transaction]:
    with get_session() as session:
        stmt = (
            select(Transaction)
            .order_by(Transaction.txn_date.desc(), Transaction.id.desc())
            .limit(limit)
        )
        return list(session.scalars(stmt).all())


def create_transaction(
    *,
    txn_date: date,
    txn_type: TransactionType | str,
    amount: float,
    account_id: int | None = None,
    description: str | None = None,
) -> Transaction:
    if isinstance(txn_type, str):
        txn_type = TransactionType(txn_type)
    if txn_type in DEPRECATED_INCOME_TRANSACTION_TYPES:
        raise ValueError(
            f"{txn_type.value} belongs under Income sources, not ledger transactions"
        )
    with get_session() as session:
        txn = Transaction(
            account_id=account_id,
            txn_date=txn_date,
            txn_type=txn_type,
            amount=float(amount),
            description=description,
        )
        session.add(txn)
        session.flush()
        session.refresh(txn)
        session.expunge(txn)
        return txn


def delete_transaction(txn_id: int) -> None:
    with get_session() as session:
        txn = session.get(Transaction, txn_id)
        if txn is None:
            return
        session.delete(txn)
