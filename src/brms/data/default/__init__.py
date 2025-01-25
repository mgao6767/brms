import datetime
import random

from dateutil.relativedelta import relativedelta

from brms.instruments.base import InstrumentClass
from brms.instruments.factory import InstrumentFactory
from brms.instruments.visitors.valuation import BankingBookValuationVisitor
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager
from brms.models.transaction import Transaction, TransactionFactory, TransactionType

random.seed(42)

base_date = datetime.date(2021, 10, 21)

SIMULATION_START_DATE = datetime.date(2022, 1, 3)


def create_bank_init_transactions(bank: Bank, scenario_manager: ScenarioManager) -> list[Transaction]:
    """Create a default list of transactions that initializes a bank."""
    transactions = [
        TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.EQUITY_ISSUANCE,
            instrument=InstrumentFactory.create_common_equity(value=1_000_000),
            transaction_date=base_date,
            description="Shareholders' contribution",
        ),
        TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.DEPOSIT_RECEIVED,
            instrument=InstrumentFactory.create_deposit(value=6_000_000),
            transaction_date=base_date + relativedelta(days=2),
            description="Deposits",
        ),
    ]

    # HTM banking book security, a Treasury Note
    today = base_date + relativedelta(days=4)
    assert scenario_manager.has_scenario(today)

    tn = InstrumentFactory.create_treasury_note(
        face_value=10000.0,
        coupon_rate=0.05,
        issue_date=datetime.date(2020, 1, 1),
        maturity_date=datetime.date(2030, 1, 1),
        instrument_class=InstrumentClass.HTM,
    )
    tn.accept(BankingBookValuationVisitor(scenario_manager, valuation_date=today))
    tx = TransactionFactory.create_transaction(
        bank=bank,
        transaction_type=TransactionType.SECURITY_PURCHASE_HTM,
        instrument=tn,
        transaction_date=today,
        description="Purchase banking book security HTM",
    )
    transactions.append(tx)

    # FVOCI banking book security, a Treasury Note
    fvoci_securities = []

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
        fvoci_securities.append(tn_fvoci)
        transactions.append(tx)

    # Marking to market
    current_date = today + relativedelta(days=1)
    end_date = scenario_manager.current_scenario.date

    visitor = BankingBookValuationVisitor(scenario_manager)
    while current_date <= end_date:
        if scenario_manager.has_scenario(current_date):
            matured = [sec for sec in fvoci_securities if sec.maturity_date <= current_date]
            for sec in matured:
                tx = TransactionFactory.create_transaction(
                    bank=bank,
                    transaction_type=TransactionType.SECURITY_SALE_FVOCI,
                    instrument=sec,
                    transaction_date=current_date,  # or last day before maturity
                    description="Sell banking book security FVOCI",
                )
                transactions.append(tx)

            fvoci_securities = [sec for sec in fvoci_securities if sec not in matured]
            for fvoci_security in fvoci_securities:
                tx = TransactionFactory.create_transaction(
                    bank=bank,
                    transaction_type=TransactionType.SECURITY_FVOCI_MARK_TO_MARKET,
                    instrument=fvoci_security,
                    transaction_date=current_date,
                    valuation_visitor=visitor,
                    description="Mark to market banking book security FVOCI",
                )
                transactions.append(tx)
        current_date += relativedelta(days=1)

    return transactions
