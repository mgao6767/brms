# ruff: noqa: S101
"""Tests for AccountingService.post_all and position management (V2)."""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.enums import PositionStatus, TransactionType  # noqa: F401
from brms.core.models.accounting.accounts import BankChartOfAccounts
from brms.core.models.accounting.journal import Journal
from brms.core.models.accounting.ledger import Ledger
from brms.core.models.accounting.service import AccountingService
from brms.core.models.transaction import Transaction


def _make_full_ledger() -> Ledger:
    """Create a Ledger backed by BankChartOfAccounts with a starting cash balance."""
    coa = BankChartOfAccounts()
    journal = Journal()
    ledger = Ledger(chart_of_accounts=coa, journal=journal)
    coa.cash_account.debit(500_000.0)
    return ledger


def test_post_all_posts_to_ledger() -> None:
    """post_all posts each transaction to the ledger journal."""
    service = AccountingService()
    ledger = _make_full_ledger()
    positions = MagicMock()
    tx = Transaction(
        id="t1",
        type=TransactionType.DEPOSIT_RECEIVED,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("10000"),
    )
    service.post_all([tx], ledger, positions)
    assert len(ledger.journal.entries) == 1


def test_post_all_closes_position_on_maturity() -> None:
    """post_all closes position when a MATURITY_SETTLEMENT transaction is posted."""
    service = AccountingService()
    ledger = _make_full_ledger()
    positions = MagicMock()
    tx = Transaction(
        id="t1",
        type=TransactionType.MATURITY_SETTLEMENT,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("100000"),
        position_id="pos-1",
        metadata=[("instrument_class", "HTM")],
    )
    service.post_all([tx], ledger, positions)
    positions.close.assert_called_with("pos-1")


def test_post_all_closes_position_on_sale() -> None:
    """post_all closes position when a SECURITY_SALE transaction is posted."""
    service = AccountingService()
    ledger = _make_full_ledger()
    positions = MagicMock()
    tx = Transaction(
        id="t1",
        type=TransactionType.SECURITY_SALE,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("50000"),
        position_id="pos-2",
        metadata=[("instrument_class", "HTM")],
    )
    service.post_all([tx], ledger, positions)
    positions.close.assert_called_with("pos-2")


def test_post_all_no_close_for_other_types() -> None:
    """post_all does not close any position for non-closing transaction types."""
    service = AccountingService()
    ledger = _make_full_ledger()
    positions = MagicMock()
    tx = Transaction(
        id="t1",
        type=TransactionType.INTEREST_PAYMENT,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("500"),
    )
    service.post_all([tx], ledger, positions)
    positions.close.assert_not_called()
