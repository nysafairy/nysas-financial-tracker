"""SQLAlchemy models — ledger, snapshots, recurring flows, and debts."""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AccountType(str, enum.Enum):
    CURRENT = "current"
    SAVINGS = "savings"
    ISA_CASH = "isa_cash"
    ISA_STOCKS = "isa_stocks"
    LISA = "lisa"
    JUNIOR_ISA = "junior_isa"
    IFISA = "ifisa"
    GIA = "gia"
    PENSION_SIP = "pension_sip"
    PENSION_WORKPLACE = "pension_workplace"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    OTHER_DEBT = "other_debt"
    OTHER = "other"


class InterestFrequency(str, enum.Enum):
    NONE = "none"
    DAILY = "daily"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    ON_MATURITY = "on_maturity"


class AccessType(str, enum.Enum):
    NA = "na"
    EASY_ACCESS = "easy_access"
    NOTICE = "notice"
    FIXED_TERM = "fixed_term"
    LIMITED_ACCESS = "limited_access"


class TransactionType(str, enum.Enum):
    CONTRIBUTION = "contribution"
    WITHDRAWAL = "withdrawal"
    INTEREST = "interest"
    DIVIDEND = "dividend"
    EARNINGS = "earnings"
    PENSION_INCOME = "pension_income"
    PROPERTY_INCOME = "property_income"
    TRUST_INCOME = "trust_income"
    TAX_PAID = "tax_paid"
    TAX_REFUND = "tax_refund"
    FEE = "fee"
    SUBSCRIPTION = "subscription"
    TRANSFER = "transfer"
    OTHER = "other"


class RecurringKind(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    STANDING_ORDER = "standing_order"
    INCOME = "income"


class Frequency(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class IncomeCategory(str, enum.Enum):
    SALARY = "salary"
    FREELANCE = "freelance"
    GIG = "gig"
    INVESTMENT = "investment"
    PENSION = "pension"
    PROPERTY = "property"
    OTHER = "other"


class IncomeCadence(str, enum.Enum):
    FIXED_ANNUAL = "fixed_annual"
    FIXED_MONTHLY = "fixed_monthly"
    VARIABLE = "variable"


LIABILITY_TYPES = {
    AccountType.CREDIT_CARD,
    AccountType.LOAN,
    AccountType.MORTGAGE,
    AccountType.OTHER_DEBT,
}

ACCOUNT_TYPE_LABELS: dict[AccountType, str] = {
    AccountType.CURRENT: "Current account",
    AccountType.SAVINGS: "Savings",
    AccountType.ISA_CASH: "Cash ISA",
    AccountType.ISA_STOCKS: "Stocks & Shares ISA",
    AccountType.LISA: "Lifetime ISA (LISA)",
    AccountType.JUNIOR_ISA: "Junior ISA",
    AccountType.IFISA: "Innovative Finance ISA",
    AccountType.GIA: "General investment account",
    AccountType.PENSION_SIP: "SIPP",
    AccountType.PENSION_WORKPLACE: "Workplace pension",
    AccountType.CREDIT_CARD: "Credit card",
    AccountType.LOAN: "Loan",
    AccountType.MORTGAGE: "Mortgage",
    AccountType.OTHER_DEBT: "Other debt",
    AccountType.OTHER: "Other",
}

# Adult ISA wrappers that share the £20k annual subscription limit.
ADULT_ISA_TYPES = {
    AccountType.ISA_CASH,
    AccountType.ISA_STOCKS,
    AccountType.LISA,
    AccountType.IFISA,
}

INTEREST_FREQUENCY_LABELS: dict[InterestFrequency, str] = {
    InterestFrequency.NONE: "None / n/a",
    InterestFrequency.DAILY: "Daily",
    InterestFrequency.MONTHLY: "Monthly",
    InterestFrequency.QUARTERLY: "Quarterly",
    InterestFrequency.ANNUALLY: "Annually",
    InterestFrequency.ON_MATURITY: "On maturity",
}

ACCESS_TYPE_LABELS: dict[AccessType, str] = {
    AccessType.NA: "n/a",
    AccessType.EASY_ACCESS: "Easy access",
    AccessType.NOTICE: "Notice account",
    AccessType.FIXED_TERM: "Fixed rate / fixed term",
    AccessType.LIMITED_ACCESS: "Limited access",
}

TRANSACTION_TYPE_LABELS: dict[TransactionType, str] = {
    TransactionType.CONTRIBUTION: "Contribution",
    TransactionType.WITHDRAWAL: "Withdrawal",
    TransactionType.INTEREST: "Interest",
    TransactionType.DIVIDEND: "Dividend",
    TransactionType.EARNINGS: "Earnings / salary",
    TransactionType.PENSION_INCOME: "Pension income",
    TransactionType.PROPERTY_INCOME: "Property income",
    TransactionType.TRUST_INCOME: "Trust / fund income",
    TransactionType.TAX_PAID: "Tax paid",
    TransactionType.TAX_REFUND: "Tax refund",
    TransactionType.FEE: "Fee",
    TransactionType.SUBSCRIPTION: "Subscription",
    TransactionType.TRANSFER: "Transfer",
    TransactionType.OTHER: "Other",
}

RECURRING_KIND_LABELS: dict[RecurringKind, str] = {
    RecurringKind.SUBSCRIPTION: "Subscription",
    RecurringKind.STANDING_ORDER: "Standing order",
    RecurringKind.INCOME: "Recurring income",
}

FREQUENCY_LABELS: dict[Frequency, str] = {
    Frequency.WEEKLY: "Weekly",
    Frequency.MONTHLY: "Monthly",
    Frequency.YEARLY: "Yearly",
}

INCOME_CATEGORY_LABELS: dict[IncomeCategory, str] = {
    IncomeCategory.SALARY: "Salary / job",
    IncomeCategory.FREELANCE: "Freelance",
    IncomeCategory.GIG: "Gig / one-off",
    IncomeCategory.INVESTMENT: "Investments",
    IncomeCategory.PENSION: "Pension",
    IncomeCategory.PROPERTY: "Property",
    IncomeCategory.OTHER: "Other",
}

INCOME_CADENCE_LABELS: dict[IncomeCadence, str] = {
    IncomeCadence.FIXED_ANNUAL: "Fixed yearly",
    IncomeCadence.FIXED_MONTHLY: "Fixed monthly",
    IncomeCadence.VARIABLE: "Variable / as earned",
}


class SchemaMeta(Base):
    __tablename__ = "schema_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType), nullable=False, default=AccountType.OTHER
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Optional product / banking details (nullable — not all types use all fields).
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    interest_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_frequency: Mapped[InterestFrequency | None] = mapped_column(
        Enum(InterestFrequency), nullable=True
    )
    access_type: Mapped[AccessType | None] = mapped_column(
        Enum(AccessType), nullable=True
    )
    notice_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    opened_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    holdings: Mapped[list[Holding]] = relationship(back_populates="account")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="account",
        foreign_keys="Transaction.account_id",
    )
    balance_snapshots: Mapped[list[BalanceSnapshot]] = relationship(
        back_populates="account"
    )

    @property
    def is_liability(self) -> bool:
        return self.account_type in LIABILITY_TYPES

    @property
    def is_adult_isa(self) -> bool:
        return self.account_type in ADULT_ISA_TYPES


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(32), nullable=True)
    units: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped[Account] = relationship(back_populates="holdings")
    snapshots: Mapped[list[HoldingSnapshot]] = relationship(back_populates="holding")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    txn_date: Mapped[date] = mapped_column(Date, nullable=False)
    txn_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )

    account: Mapped[Account | None] = relationship(
        back_populates="transactions", foreign_keys=[account_id]
    )


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"
    __table_args__ = (
        UniqueConstraint("account_id", "as_of_date", name="uq_balance_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)

    account: Mapped[Account] = relationship(back_populates="balance_snapshots")


class HoldingSnapshot(Base):
    __tablename__ = "holding_snapshots"
    __table_args__ = (
        UniqueConstraint("holding_id", "as_of_date", name="uq_holding_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    holding_id: Mapped[int] = mapped_column(ForeignKey("holdings.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    units: Mapped[float] = mapped_column(Float, nullable=False)
    market_value: Mapped[float] = mapped_column(Float, nullable=False)

    holding: Mapped[Holding] = relationship(back_populates="snapshots")


class RecurringItem(Base):
    """Subscriptions, standing orders, and recurring income."""

    __tablename__ = "recurring_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[RecurringKind] = mapped_column(Enum(RecurringKind), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    frequency: Mapped[Frequency] = mapped_column(
        Enum(Frequency), nullable=False, default=Frequency.MONTHLY
    )
    from_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    to_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Standing orders move money between own accounts and do not change net worth.
    affects_net_worth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class IncomeStream(Base):
    """Named income sources — salary, freelance clients, gigs, etc."""

    __tablename__ = "income_streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[IncomeCategory] = mapped_column(
        Enum(IncomeCategory), nullable=False, default=IncomeCategory.OTHER
    )
    cadence: Mapped[IncomeCadence] = mapped_column(
        Enum(IncomeCadence), nullable=False, default=IncomeCadence.VARIABLE
    )
    # Current expected amount (yearly or monthly depending on cadence).
    # Pay rises are also recorded in IncomeRatePeriod for dated history.
    expected_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    receipts: Mapped[list[IncomeReceipt]] = relationship(back_populates="stream")
    rate_periods: Mapped[list[IncomeRatePeriod]] = relationship(
        back_populates="stream",
        order_by="IncomeRatePeriod.effective_from",
    )


class IncomeRatePeriod(Base):
    """Dated pay level for a fixed income stream (handles mid-year salary changes)."""

    __tablename__ = "income_rate_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("income_streams.id"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    # Always stored as annual GBP equivalent for clean pro-rata maths.
    annual_amount: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    stream: Mapped[IncomeStream] = relationship(back_populates="rate_periods")


class IncomeReceipt(Base):
    """Discrete income events (invoice paid, gig payout) — not a full transaction ledger."""

    __tablename__ = "income_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("income_streams.id"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    stream: Mapped[IncomeStream] = relationship(back_populates="receipts")
