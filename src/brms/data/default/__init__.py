import datetime

import QuantLib as ql
from dateutil.relativedelta import relativedelta

from brms.instruments.base import CreditRating, Issuer, IssuerType, InstrumentClass
from brms.instruments.common_equity import CommonEquity
from brms.instruments.deposit import Deposit
from brms.instruments.treasury_security import TreasuryNote
from brms.instruments.visitors.valuation import BankingBookValuationVisitor
from brms.models.bank import Bank
from brms.models.base import BookType
from brms.models.scenario import ScenarioManager
from brms.models.transaction import Transaction, TransactionFactory, TransactionType

base_date = datetime.date(2021, 10, 21)

SIMULATION_START_DATE = datetime.date(2022, 1, 3)


def create_bank_init_transactions(bank: Bank, scenario_manager: ScenarioManager) -> list[Transaction]:
    """Create a default list of transactions that initializes a bank."""
    transactions = [
        TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.EQUITY_ISSUANCE,
            instrument=CommonEquity(value=1_000_000),
            transaction_date=base_date,
            description="Shareholders' contribution",
        ),
        TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.DEPOSIT_RECEIVED,
            instrument=Deposit(value=6_000_000),
            transaction_date=base_date + relativedelta(days=2),
            description="Deposits",
        ),
    ]

    # HTM banking book security, a Treasury Note
    today = base_date + relativedelta(days=4)
    assert scenario_manager.has_scenario(today)

    tn = _create_treasury_notes()
    tn.instrument_class = InstrumentClass.HTM
    tn.accept(BankingBookValuationVisitor(scenario_manager.get_scenario(today)))
    tx = TransactionFactory.create_transaction(
        bank=bank,
        transaction_type=TransactionType.SECURITY_PURCHASE_HTM,
        instrument=tn,
        transaction_date=today,
        description="Purchase banking book security HTM",
    )
    transactions.append(tx)

    # FVOCI banking book security, a Treasury Note
    tn_fvoci = _create_treasury_notes()
    tn_fvoci.instrument_class = InstrumentClass.FVOCI
    tn_fvoci.accept(BankingBookValuationVisitor(scenario_manager.get_scenario(today)))
    tx = TransactionFactory.create_transaction(
        bank=bank,
        transaction_type=TransactionType.SECURITY_PURCHASE_FVOCI,
        instrument=tn_fvoci,
        transaction_date=today,
        description="Purchase banking book security FVOCI",
    )
    transactions.append(tx)

    current_date = today
    end_date = scenario_manager.current_scenario.date

    while current_date <= end_date:
        if scenario_manager.has_scenario(current_date):
            tx = TransactionFactory.create_transaction(
                bank=bank,
                transaction_type=TransactionType.SECURITY_FVOCI_MARK_TO_MARKET,
                instrument=tn_fvoci,
                transaction_date=today,
                valuation_visitor=BankingBookValuationVisitor(scenario_manager.get_scenario(current_date)),
                description="Purchase banking book security FVOCI",
            )
            transactions.append(tx)
        current_date += relativedelta(days=1)

    return transactions


def _create_treasury_notes() -> TreasuryNote:
    face_value = 10000.0
    coupon_rate = 0.05
    issue_date = ql.Date(1, 1, 2020)
    maturity_date = ql.Date(1, 1, 2030)
    note = TreasuryNote(
        face_value=face_value,
        coupon_rate=coupon_rate,
        issue_date=issue_date,
        maturity_date=maturity_date,
        book_type=BookType.BANKING_BOOK,
        credit_rating=CreditRating.AA_MINUS,
        issuer=Issuer(
            name="Government",
            issuer_type=IssuerType.SOVEREIGN,
            credit_rating=CreditRating.AA,
        ),
    )
    return note
