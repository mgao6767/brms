import datetime

import QuantLib as ql
from dateutil.relativedelta import relativedelta

from brms.instruments.base import CreditRating, Issuer, IssuerType
from brms.instruments.common_equity import CommonEquity
from brms.instruments.deposit import Deposit
from brms.instruments.treasury_security import TreasuryNote
from brms.models.bank import Bank
from brms.models.base import BookType
from brms.models.transaction import Transaction, TransactionFactory, TransactionType

base_date = datetime.date(2021, 10, 21)

SIMULATION_START_DATE = datetime.date(2022, 1, 3)


def create_bank_init_transactions(bank: Bank) -> list[Transaction]:
    """Create a default list of transactions that initializes a bank."""
    return [
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


def _create_treasury_notes() -> TreasuryNote:
    face_value = 5000.0
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
            name="Central Bank",
            issuer_type=IssuerType.MDB,
            credit_rating=CreditRating.AA,
        ),
    )
    # value is 0 since we need a valuation visitor to get its value, yet visitor needs a scenario...
    # so we need to construct scenarios first and implement how scenario changes lead to transactions
    # otherwise the instrument value, if manually set, cannot accurately reflect true costs
    return note
