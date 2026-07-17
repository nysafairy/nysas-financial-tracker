"""Account, holding, and transaction CRUD."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from finance_app.db.models import (
    AccessType,
    Account,
    AccountType,
    Holding,
    InterestFrequency,
    Transaction,
    TransactionType,
)
from finance_app.db.session import get_session


def list_accounts(*, active_only: bool = False) -> list[Account]:
    with get_session() as session:
        stmt = select(Account).order_by(Account.name)
        if active_only:
            stmt = stmt.where(Account.active.is_(True))
        return list(session.scalars(stmt).unique().all())


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
) -> Account:
    if isinstance(account_type, str):
        account_type = AccountType(account_type)
    if isinstance(interest_frequency, str) and interest_frequency:
        interest_frequency = InterestFrequency(interest_frequency)
    if isinstance(access_type, str) and access_type:
        access_type = AccessType(access_type)
    with get_session() as session:
        account = Account(
            name=name.strip(),
            account_type=account_type,
            currency=currency.upper(),
            notes=notes,
            provider=(provider or None),
            account_number=(account_number or None),
            sort_code=(sort_code or None),
            interest_rate_pct=interest_rate_pct,
            interest_frequency=interest_frequency or None,
            access_type=access_type or None,
            notice_days=notice_days,
            maturity_date=maturity_date,
            opened_date=opened_date,
            active=True,
        )
        session.add(account)
        session.flush()
        session.refresh(account)
        session.expunge(account)
        return account


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
) -> None:
    with get_session() as session:
        account = session.get(Account, account_id)
        if account is None:
            raise ValueError("Account not found")
        if name is not None:
            account.name = name.strip()
        if account_type is not None:
            account.account_type = (
                AccountType(account_type)
                if isinstance(account_type, str)
                else account_type
            )
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
        if notice_days is not None:
            account.notice_days = notice_days if notice_days != "" else None
        if maturity_date is not None:
            account.maturity_date = maturity_date
        if opened_date is not None:
            account.opened_date = opened_date


def delete_account(account_id: int) -> None:
    with get_session() as session:
        account = session.get(Account, account_id)
        if account is None:
            return
        session.delete(account)


def list_holdings(account_id: int | None = None) -> list[Holding]:
    with get_session() as session:
        stmt = select(Holding).order_by(Holding.name)
        if account_id is not None:
            stmt = stmt.where(Holding.account_id == account_id)
        return list(session.scalars(stmt).all())


def create_holding(
    account_id: int,
    name: str,
    *,
    ticker: str | None = None,
    units: float = 0.0,
    provider: str | None = None,
    notes: str | None = None,
) -> Holding:
    with get_session() as session:
        holding = Holding(
            account_id=account_id,
            name=name.strip(),
            ticker=(ticker or None),
            units=float(units),
            provider=provider,
            notes=notes,
        )
        session.add(holding)
        session.flush()
        session.refresh(holding)
        session.expunge(holding)
        return holding


def delete_holding(holding_id: int) -> None:
    with get_session() as session:
        holding = session.get(Holding, holding_id)
        if holding is None:
            return
        session.delete(holding)


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
    counterparty_account_id: int | None = None,
) -> Transaction:
    if isinstance(txn_type, str):
        txn_type = TransactionType(txn_type)
    with get_session() as session:
        txn = Transaction(
            account_id=account_id,
            txn_date=txn_date,
            txn_type=txn_type,
            amount=float(amount),
            description=description,
            counterparty_account_id=counterparty_account_id,
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
