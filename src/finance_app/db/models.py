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
    SAVINGS_EASY_ACCESS = "savings_easy_access"
    SAVINGS_LIMITED_ACCESS = "savings_limited_access"
    SAVINGS_REGULAR = "savings_regular"
    SAVINGS_FIXED_1Y = "savings_fixed_1y"
    SAVINGS_FIXED_2Y = "savings_fixed_2y"
    SAVINGS_FIXED_5Y = "savings_fixed_5y"
    PREMIUM_BONDS = "premium_bonds"
    ISA_CASH = "isa_cash"
    ISA_STOCKS = "isa_stocks"
    LISA = "lisa"
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


class PayFrequency(str, enum.Enum):
    WEEKLY = "weekly"
    BI_WEEKLY = "bi_weekly"
    FOUR_WEEKLY = "four_weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class TaxBand(str, enum.Enum):
    """Optional recorded UK income-tax band for a salary / employment source."""

    BASIC = "basic"
    HIGHER = "higher"
    ADDITIONAL = "additional"


class TaxTreatment(str, enum.Enum):
    """How a stream is classified when estimating England income tax."""

    EMPLOYMENT = "employment"
    TRADING = "trading"
    PENSION = "pension"
    PROPERTY = "property"
    EXEMPT = "exempt"
    OTHER = "other"


LIABILITY_TYPES = {
    AccountType.CREDIT_CARD,
    AccountType.LOAN,
    AccountType.MORTGAGE,
    AccountType.OTHER_DEBT,
}

# Cash-style savings (non-ISA) — used for defaults and grouping helpers.
CASH_SAVINGS_TYPES = {
    AccountType.SAVINGS_EASY_ACCESS,
    AccountType.SAVINGS_LIMITED_ACCESS,
    AccountType.SAVINGS_REGULAR,
    AccountType.SAVINGS_FIXED_1Y,
    AccountType.SAVINGS_FIXED_2Y,
    AccountType.SAVINGS_FIXED_5Y,
    AccountType.PREMIUM_BONDS,
}

# Assumed average prize rate for Premium Bonds (NS&I). Not a guaranteed AER.
PREMIUM_BONDS_ASSUMED_RATE_PCT = 3.8

# Default annual growth assumption on the Forecasting page for accounts without a stored rate.
FORECAST_DEFAULT_ASSUMED_GROWTH_PCT = 5.0

ACCOUNT_TYPE_LABELS: dict[AccountType, str] = {
    AccountType.CURRENT: "Current account",
    AccountType.SAVINGS_EASY_ACCESS: "Easy access savings",
    AccountType.SAVINGS_LIMITED_ACCESS: "Limited access savings",
    AccountType.SAVINGS_REGULAR: "Regular saver",
    AccountType.SAVINGS_FIXED_1Y: "Fixed term (1 year)",
    AccountType.SAVINGS_FIXED_2Y: "Fixed term (2 years)",
    AccountType.SAVINGS_FIXED_5Y: "Fixed term (5 years)",
    AccountType.PREMIUM_BONDS: "Premium Bonds (NS&I)",
    AccountType.ISA_CASH: "Cash ISA",
    AccountType.ISA_STOCKS: "Stocks & Shares ISA",
    AccountType.LISA: "Lifetime ISA (LISA)",
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

# Implied access when the account type already encodes it.
DEFAULT_ACCESS_FOR_TYPE: dict[AccountType, AccessType] = {
    AccountType.SAVINGS_EASY_ACCESS: AccessType.EASY_ACCESS,
    AccountType.SAVINGS_LIMITED_ACCESS: AccessType.LIMITED_ACCESS,
    AccountType.SAVINGS_REGULAR: AccessType.LIMITED_ACCESS,
    AccountType.SAVINGS_FIXED_1Y: AccessType.FIXED_TERM,
    AccountType.SAVINGS_FIXED_2Y: AccessType.FIXED_TERM,
    AccountType.SAVINGS_FIXED_5Y: AccessType.FIXED_TERM,
    AccountType.PREMIUM_BONDS: AccessType.NA,
}

# ISA wrappers that share the £20k annual subscription limit.
ADULT_ISA_TYPES = {
    AccountType.ISA_CASH,
    AccountType.ISA_STOCKS,
    AccountType.LISA,
    AccountType.IFISA,
}

# Interest / prizes treated as tax-free in England income-tax estimates.
TAX_EXEMPT_INTEREST_ACCOUNT_TYPES = ADULT_ISA_TYPES | {
    AccountType.PREMIUM_BONDS,  # NS&I prizes are tax-free
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

PAY_FREQUENCY_LABELS: dict[PayFrequency, str] = {
    PayFrequency.WEEKLY: "Weekly",
    PayFrequency.BI_WEEKLY: "Bi-weekly (fortnightly)",
    PayFrequency.FOUR_WEEKLY: "Four-weekly",
    PayFrequency.MONTHLY: "Monthly",
    PayFrequency.YEARLY: "Yearly",
}

TAX_BAND_LABELS: dict[TaxBand, str] = {
    TaxBand.BASIC: "Basic rate",
    TaxBand.HIGHER: "Higher rate",
    TaxBand.ADDITIONAL: "Additional rate",
}

TAX_TREATMENT_LABELS: dict[TaxTreatment, str] = {
    TaxTreatment.EMPLOYMENT: "Employment (PAYE / salary)",
    TaxTreatment.TRADING: "Self-employment / trading",
    TaxTreatment.PENSION: "Pension income",
    TaxTreatment.PROPERTY: "Property income",
    TaxTreatment.EXEMPT: "Tax-exempt",
    TaxTreatment.OTHER: "Other taxable",
}


def default_tax_treatment(category: IncomeCategory) -> TaxTreatment:
    if category == IncomeCategory.SALARY:
        return TaxTreatment.EMPLOYMENT
    if category in (IncomeCategory.FREELANCE, IncomeCategory.GIG):
        return TaxTreatment.TRADING
    if category == IncomeCategory.PENSION:
        return TaxTreatment.PENSION
    if category == IncomeCategory.PROPERTY:
        return TaxTreatment.PROPERTY
    if category == IncomeCategory.INVESTMENT:
        return TaxTreatment.EXEMPT
    return TaxTreatment.OTHER


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


class SnapshotDraft(Base):
    """At most one open editing session per profile database."""

    __tablename__ = "snapshot_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    accounts: Mapped[list[SnapshotDraftAccount]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )
    balances: Mapped[list[SnapshotDraftBalance]] = relationship(
        back_populates="draft", cascade="all, delete-orphan"
    )


class SnapshotDraftAccount(Base):
    """Pending account create / update / deactivate within a draft session."""

    __tablename__ = "snapshot_draft_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("snapshot_drafts.id"), nullable=False
    )
    op: Mapped[str] = mapped_column(String(16), nullable=False)  # create|update|deactivate
    temp_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    interest_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    access_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notice_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    opened_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    clear_interest_rate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clear_notice_days: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clear_maturity_date: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clear_opened_date: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    draft: Mapped[SnapshotDraft] = relationship(back_populates="accounts")


class SnapshotDraftBalance(Base):
    """Pending balance for an existing account or a draft-created account."""

    __tablename__ = "snapshot_draft_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("snapshot_drafts.id"), nullable=False
    )
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temp_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)

    draft: Mapped[SnapshotDraft] = relationship(back_populates="balances")


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
    # How often pay actually arrives (independent of expected-amount unit).
    pay_frequency: Mapped[PayFrequency | None] = mapped_column(
        Enum(PayFrequency), nullable=True
    )
    # How this stream feeds England income-tax estimates.
    tax_treatment: Mapped[TaxTreatment] = mapped_column(
        Enum(TaxTreatment), nullable=False, default=TaxTreatment.OTHER
    )
    # Optional recorded band for salary sources (informational + forecast display).
    tax_band: Mapped[TaxBand | None] = mapped_column(Enum(TaxBand), nullable=True)
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


class AllowanceBaseline(Base):
    """
    Manual prior usage for the current UK tax year.

    Use when starting the app mid-year after already using ISA / LISA / pension
    room outside this ledger. Added on top of contribution transactions.
    """

    __tablename__ = "allowance_baselines"
    __table_args__ = (
        UniqueConstraint("tax_year", "allowance_key", name="uq_allowance_baseline"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # e.g. "2026-27" matching uk_allowances JSON tax_year field
    tax_year: Mapped[str] = mapped_column(String(16), nullable=False)
    # adult_isa | lisa | pension_annual
    allowance_key: Mapped[str] = mapped_column(String(40), nullable=False)
    prior_used: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
