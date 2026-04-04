"""Tests for the frozen Transaction dataclass and TransactionType enum."""

import datetime
from decimal import Decimal

import pytest

from brms.core.models.transaction import Transaction, TransactionType


def test_transaction_is_frozen() -> None:
    """A frozen Transaction raises AttributeError on mutation attempts."""
    tx = Transaction(
        id="tx-001",
        type=TransactionType.INTEREST_PAYMENT,
        date=datetime.date(2024, 1, 15),
        amount=Decimal("5000.00"),
    )
    with pytest.raises(AttributeError):
        tx.amount = Decimal("9999")  # type: ignore[misc]


def test_transaction_fields() -> None:
    """Optional fields instrument_id and metadata are stored correctly."""
    tx = Transaction(
        id="tx-002",
        type=TransactionType.MARK_TO_MARKET,
        date=datetime.date(2024, 1, 15),
        amount=Decimal("1200.50"),
        instrument_id="bond-001",
        metadata=(("reason", "fair_value_change"),),
    )
    assert tx.instrument_id == "bond-001"  # noqa: S101
    assert tx.metadata == (("reason", "fair_value_change"),)  # noqa: S101


def test_transaction_defaults() -> None:
    """instrument_id defaults to None and metadata defaults to empty tuple."""
    tx = Transaction(
        id="tx-003",
        type=TransactionType.COUPON_PAYMENT,
        date=datetime.date(2024, 6, 1),
        amount=Decimal("2500"),
    )
    assert tx.instrument_id is None  # noqa: S101
    assert tx.metadata == ()  # noqa: S101


def test_transaction_type_members() -> None:
    """All expected TransactionType members are present."""
    assert TransactionType.INTEREST_PAYMENT  # noqa: S101
    assert TransactionType.MARK_TO_MARKET  # noqa: S101
    assert TransactionType.MATURITY_SETTLEMENT  # noqa: S101
    assert TransactionType.COUPON_PAYMENT  # noqa: S101
    assert TransactionType.LOAN_DISBURSEMENT  # noqa: S101
    assert TransactionType.LOAN_REPAYMENT  # noqa: S101
    assert TransactionType.DEPOSIT_RECEIVED  # noqa: S101
    assert TransactionType.DEPOSIT_WITHDRAWAL  # noqa: S101
    assert TransactionType.EQUITY_ISSUANCE  # noqa: S101
    assert TransactionType.SECURITY_PURCHASE  # noqa: S101
    assert TransactionType.SECURITY_SALE  # noqa: S101
    assert TransactionType.AMORTIZATION  # noqa: S101
