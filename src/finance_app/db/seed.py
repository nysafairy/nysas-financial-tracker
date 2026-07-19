"""Optional demo data for a new profile."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select

from finance_app.db.models import (
    AccessType,
    Account,
    AccountType,
    BalanceSnapshot,
    Frequency,
    IncomeCadence,
    IncomeCategory,
    IncomeRatePeriod,
    IncomeReceipt,
    IncomeStream,
    InterestFrequency,
    PayFrequency,
    RecurringItem,
    RecurringKind,
    TaxBand,
    TaxTreatment,
    Transaction,
    TransactionType,
)
from finance_app.db.session import get_session


def profile_is_empty() -> bool:
    with get_session() as session:
        count = session.scalar(select(func.count()).select_from(Account)) or 0
        return count == 0


def seed_demo_data() -> None:
    """Populate a small England-oriented demo dataset if the profile is empty."""
    if not profile_is_empty():
        return

    today = date.today()
    with get_session() as session:
        current = Account(
            name="Everyday current",
            account_type=AccountType.CURRENT,
            notes="Day-to-day spending",
            provider="Demo Bank",
            sort_code="00-00-00",
        )
        savings = Account(
            name="Easy-access savings",
            account_type=AccountType.SAVINGS_EASY_ACCESS,
            notes="Emergency fund",
            provider="Demo Bank",
            interest_rate_pct=4.5,
            interest_frequency=InterestFrequency.MONTHLY,
            access_type=AccessType.EASY_ACCESS,
        )
        regular = Account(
            name="Regular saver",
            account_type=AccountType.SAVINGS_REGULAR,
            notes="Monthly deposit bonus rate",
            provider="Demo Bank",
            interest_rate_pct=6.0,
            interest_frequency=InterestFrequency.ANNUALLY,
            access_type=AccessType.LIMITED_ACCESS,
        )
        premium = Account(
            name="Premium Bonds",
            account_type=AccountType.PREMIUM_BONDS,
            notes="NS&I prize draw — assumed average prize rate for forecasting",
            provider="NS&I",
            interest_rate_pct=3.8,
            interest_frequency=InterestFrequency.NONE,
            access_type=AccessType.NA,
        )
        isa = Account(
            name="S&S ISA",
            account_type=AccountType.ISA_STOCKS,
            notes="Long-term investing — one balance for the wrapper",
            provider="Vanguard",
            access_type=AccessType.EASY_ACCESS,
        )
        lisa = Account(
            name="Lifetime ISA",
            account_type=AccountType.LISA,
            notes="First home / retirement",
            provider="Demo LISA",
            access_type=AccessType.LIMITED_ACCESS,
        )
        sipp = Account(
            name="SIPP",
            account_type=AccountType.PENSION_SIP,
            notes="Retirement",
        )
        card = Account(
            name="Credit card",
            account_type=AccountType.CREDIT_CARD,
            notes="Monthly spend — balance is amount owed",
        )
        session.add_all(
            [current, savings, regular, premium, isa, lisa, sipp, card]
        )
        session.flush()

        months = [today - timedelta(days=30 * i) for i in range(5, -1, -1)]
        balances = {
            current.id: [2400, 2100, 2650, 2300, 2800, 2550],
            savings.id: [8000, 8200, 8400, 8600, 8800, 9000],
            regular.id: [600, 800, 1000, 1200, 1400, 1600],
            premium.id: [5000, 5000, 5000, 5000, 5000, 5000],
            isa.id: [12000, 12400, 12850, 13100, 13600, 14200],
            lisa.id: [2000, 2200, 2400, 2600, 2800, 3000],
            sipp.id: [28000, 28500, 29100, 29800, 30500, 31200],
            card.id: [450, 520, 380, 610, 490, 430],
        }
        for account_id, series in balances.items():
            for as_of, value in zip(months, series, strict=True):
                session.add(
                    BalanceSnapshot(
                        account_id=account_id,
                        as_of_date=as_of,
                        balance=float(value),
                    )
                )

        tax_year_start = date(today.year if today.month >= 4 else today.year - 1, 4, 6)
        session.add_all(
            [
                Transaction(
                    account_id=savings.id,
                    txn_date=tax_year_start + timedelta(days=40),
                    txn_type=TransactionType.INTEREST,
                    amount=85.40,
                    description="Savings interest",
                ),
                Transaction(
                    account_id=None,
                    txn_date=tax_year_start + timedelta(days=25),
                    txn_type=TransactionType.TAX_PAID,
                    amount=620.00,
                    description="PAYE income tax",
                ),
                Transaction(
                    account_id=isa.id,
                    txn_date=tax_year_start + timedelta(days=60),
                    txn_type=TransactionType.CONTRIBUTION,
                    amount=500.00,
                    description="Monthly ISA contribution",
                ),
                Transaction(
                    account_id=lisa.id,
                    txn_date=tax_year_start + timedelta(days=70),
                    txn_type=TransactionType.CONTRIBUTION,
                    amount=1000.00,
                    description="LISA contribution",
                ),
                Transaction(
                    account_id=isa.id,
                    txn_date=tax_year_start + timedelta(days=90),
                    txn_type=TransactionType.DIVIDEND,
                    amount=42.15,
                    description="Fund distribution",
                ),
                RecurringItem(
                    name="Netflix",
                    kind=RecurringKind.SUBSCRIPTION,
                    amount=15.99,
                    frequency=Frequency.MONTHLY,
                    from_account_id=current.id,
                ),
                RecurringItem(
                    name="Savings top-up",
                    kind=RecurringKind.STANDING_ORDER,
                    amount=250.0,
                    frequency=Frequency.MONTHLY,
                    from_account_id=current.id,
                    to_account_id=savings.id,
                    notes="Moves money between own accounts",
                ),
                RecurringItem(
                    name="Side hustle (forecast)",
                    kind=RecurringKind.INCOME,
                    amount=200.0,
                    frequency=Frequency.MONTHLY,
                    notes="Forecast-only schedule — not salary history",
                ),
            ]
        )

        job = IncomeStream(
            name="Day job",
            category=IncomeCategory.SALARY,
            cadence=IncomeCadence.FIXED_ANNUAL,
            expected_amount=42000.0,
            pay_frequency=PayFrequency.MONTHLY,
            tax_treatment=TaxTreatment.EMPLOYMENT,
            tax_band=TaxBand.BASIC,
            notes="Gross annual salary, paid monthly",
        )
        freelance = IncomeStream(
            name="Design freelance",
            category=IncomeCategory.FREELANCE,
            cadence=IncomeCadence.VARIABLE,
            tax_treatment=TaxTreatment.TRADING,
            notes="Invoice as paid",
        )
        session.add_all([job, freelance])
        session.flush()
        session.add(
            IncomeRatePeriod(
                stream_id=job.id,
                effective_from=tax_year_start,
                annual_amount=42000.0,
                notes="Initial rate",
            )
        )
        session.add_all(
            [
                IncomeReceipt(
                    stream_id=freelance.id,
                    entry_date=tax_year_start + timedelta(days=50),
                    amount=1200.0,
                    description="Brand project invoice",
                ),
                IncomeReceipt(
                    stream_id=freelance.id,
                    entry_date=tax_year_start + timedelta(days=120),
                    amount=850.0,
                    description="One-off landing page",
                ),
            ]
        )
