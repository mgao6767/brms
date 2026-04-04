"""Immutable transaction record and transaction type enumeration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime
    from decimal import Decimal


class TransactionType(Enum):
    """Economic event type. Describes what happened, not how it's recorded."""

    INTEREST_PAYMENT = auto()
    MARK_TO_MARKET = auto()
    MATURITY_SETTLEMENT = auto()
    COUPON_PAYMENT = auto()
    LOAN_DISBURSEMENT = auto()
    LOAN_REPAYMENT = auto()
    DEPOSIT_RECEIVED = auto()
    DEPOSIT_WITHDRAWAL = auto()
    EQUITY_ISSUANCE = auto()
    SECURITY_PURCHASE = auto()
    SECURITY_SALE = auto()
    AMORTIZATION = auto()
    INTEREST_EXPENSE = auto()
    PRINCIPAL_PAYMENT = auto()
    REVALUATION = auto()


@dataclass(frozen=True, slots=True)
class Transaction:
    """Lightweight, immutable record of an economic event."""

    id: str
    type: TransactionType
    date: datetime.date
    amount: Decimal
    instrument_id: str | None = None
    metadata: tuple[tuple[str, Any], ...] = ()
