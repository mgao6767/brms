import datetime
from dateutil.relativedelta import relativedelta

from brms.instruments.common_equity import CommonEquity
from brms.instruments.deposit import Deposit
from brms.models.bank import Bank
from brms.models.transaction import Transaction, TransactionFactory, TransactionType


def create_bank_init_transactions(bank: Bank) -> list[Transaction]:
    """Create a default list of transactions that initializes a bank."""
    date = datetime.date(2020, 1, 1)
    return [
        TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.EQUITY_ISSUANCE,
            instrument=CommonEquity(value=1_000_000),
            transaction_date=date,
            description="Shareholders' contribution",
        ),
        TransactionFactory.create_transaction(
            bank=bank,
            transaction_type=TransactionType.DEPOSIT_RECEIVED,
            instrument=Deposit(value=6_000_000),
            transaction_date=date + relativedelta(days=2),
            description="Deposits",
        ),
    ]
