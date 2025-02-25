"""Module for default simulation."""

import datetime
import random
from collections.abc import Generator

from dateutil.relativedelta import relativedelta

from brms.instruments.base import InstrumentClass
from brms.instruments.factory import InstrumentFactory
from brms.instruments.visitors.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor
from brms.models.bank import Bank
from brms.models.bank_book import BookType
from brms.models.bank_engine import BankEngine
from brms.models.scenario import ScenarioManager
from brms.models.transaction import Transaction, TransactionFactory, TransactionType

random.seed(42)


# The oddest date of transactions
SIMULATION_BASE_DATE = datetime.date(2020, 10, 1)
# The start date of simulation
SIMULATION_START_DATE = datetime.date(2022, 1, 3)

base_date = datetime.date(2021, 10, 21)
mortgage_issue_date = SIMULATION_BASE_DATE


def create_bank_init_transactions(bank: Bank, scenario_manager: ScenarioManager) -> Generator[Transaction, None, None]:
    """Create a default list of transactions that initializes a bank."""

    yield TransactionFactory.create_transaction(
        bank=bank,
        transaction_type=TransactionType.EQUITY_ISSUANCE,
        instrument=InstrumentFactory.create_common_equity(value=1_000_000),
        transaction_date=base_date,
        description="Shareholders' contribution",
    )

    yield TransactionFactory.create_transaction(
        bank=bank,
        transaction_type=TransactionType.DEPOSIT_RECEIVED,
        instrument=InstrumentFactory.create_deposit(value=6_000_000),
        transaction_date=base_date + datetime.timedelta(days=2),
        description="Deposits",
    )

    # HTM banking book security, a Treasury Note
    today = base_date + datetime.timedelta(days=4)
    assert scenario_manager.has_scenario(today)

    tn = InstrumentFactory.create_treasury_note(
        face_value=10000.0,
        coupon_rate=0.05,
        issue_date=datetime.date(2020, 1, 1),
        maturity_date=datetime.date(2030, 1, 1),
        instrument_class=InstrumentClass.HTM,
    )
    tn.accept(BankingBookValuationVisitor(scenario_manager, valuation_date=today))
    yield TransactionFactory.create_transaction(
        bank=bank,
        transaction_type=TransactionType.SECURITY_PURCHASE_HTM,
        instrument=tn,
        transaction_date=today,
        description="Purchase banking book security HTM",
    )

    # Mortgage loan
    for i in range(5):
        mortgage = InstrumentFactory.create_residential_mortgage(
            face_value=200_000 + 100_000 * random.randint(1, 3),
            interest_rate=0.05 + 0.01 * random.randint(0, 3),
            issue_date=mortgage_issue_date + relativedelta(months=random.randint(0, 24)),
            maturity_years=random.choice([10, 20, 30]),
        )
        tx = TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.LOAN_DISBURSEMENT,
            instrument=mortgage,
            transaction_date=mortgage_issue_date,
            description="Issue a residential mortgage loan",
        )
        yield tx

    # FVOCI banking book security, a Treasury Note
    for i in range(10):
        tn_fvoci = InstrumentFactory.create_treasury_note(
            face_value=100_000.0,
            coupon_rate=0.0125 * random.randint(1, 5),
            issue_date=datetime.date(2020, 1, 1),
            maturity_date=datetime.date(2020, 1, 1) + relativedelta(years=random.choice([2, 3, 5, 7, 10])),
            instrument_class=InstrumentClass.FVOCI,
        )
        tn_fvoci.accept(BankingBookValuationVisitor(scenario_manager, valuation_date=today))
        tx = TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.SECURITY_PURCHASE_FVOCI,
            instrument=tn_fvoci,
            transaction_date=today,
            description="Purchase banking book security FVOCI",
        )
        yield tx

    # FVTPL
    for i in range(10):
        tn_fvtpl = InstrumentFactory.create_treasury_note(
            face_value=100_000.0,
            coupon_rate=0.0125 * random.randint(1, 5),
            issue_date=datetime.date(2020, 1, 1),
            maturity_date=datetime.date(2020, 1, 1) + relativedelta(years=random.choice([2, 3, 5, 7, 10])),
            instrument_class=InstrumentClass.FVTPL,
            book_type=BookType.TRADING_BOOK,
        )
        tn_fvtpl.accept(TradingBookValuationVisitor(scenario_manager, valuation_date=today))
        tx = TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.SECURITY_PURCHASE_TRADING,
            instrument=tn_fvtpl,
            transaction_date=today,
            description="Purchase trading book security FVTPL",
        )
        yield tx

    # Marking to market
    current_date = SIMULATION_BASE_DATE
    end_date = SIMULATION_START_DATE

    engine = BankEngine(bank, scenario_manager)
    # day by day
    while current_date <= end_date:
        yield from engine.generate_transactions(current_date)
        current_date += datetime.timedelta(days=1)
