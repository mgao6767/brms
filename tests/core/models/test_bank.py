"""Tests for the Bank model."""

# ruff: noqa: S101

from unittest.mock import MagicMock

from brms.core.models.bank import Bank
from brms.core.services.data_service import BankingBook, TradingBook


def test_bank_owns_books_and_ledger() -> None:
    """Bank stores name, both books, and the ledger."""
    bb = BankingBook()
    tb = TradingBook()
    ledger = MagicMock()
    bank = Bank(name="Test Bank", banking_book=bb, trading_book=tb, ledger=ledger)
    assert bank.name == "Test Bank"
    assert bank.banking_book is bb
    assert bank.trading_book is tb
    assert bank.ledger is ledger
