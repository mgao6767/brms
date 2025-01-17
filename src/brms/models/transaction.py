import datetime
from dataclasses import dataclass
from enum import Enum, auto

from brms.accounting.account import TAccount
from brms.instruments.base import Instrument


class TransactionType(Enum):
    """Enumeration of transaction types."""

    BUY_INSTRUMENT = auto()
    SELL_INSTRUMENT = auto()
    INTEREST_PAYMENT = auto()
    INTEREST_RECEIPT = auto()
    DIVIDEND_PAYMENT = auto()
    DIVIDEND_RECEIPT = auto()
    FEE_PAYMENT = auto()
    FEE_RECEIPT = auto()


@dataclass
class Transaction:
    """Class representing a transaction or non-transaction activity."""

    transaction_type: TransactionType
    instrument: Instrument
    account: TAccount
    value: float | None = None
    unit: float | None = None
    date: datetime.date | None = None
    description: str = ""

    def __post_init__(self) -> None:
        """Post-initialization checks."""
        if (
            self.transaction_type
            in {
                TransactionType.INTEREST_PAYMENT,
                TransactionType.INTEREST_RECEIPT,
                TransactionType.DIVIDEND_RECEIPT,
                TransactionType.FEE_PAYMENT,
                TransactionType.FEE_RECEIPT,
            }
            and self.value is None
        ):
            raise ValueError("Amount must be provided for interest, dividend, and fee transactions.")
