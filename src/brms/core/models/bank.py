"""Bank model owning the banking book, trading book, and general ledger."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brms.core.models.books import BankingBook, TradingBook


class Bank:
    """Owns the two books and the ledger. No business logic."""

    def __init__(self, name: str, banking_book: BankingBook, trading_book: TradingBook, ledger: object) -> None:
        """Initialize a bank with its books and ledger."""
        self.name = name
        self.banking_book = banking_book
        self.trading_book = trading_book
        self.ledger = ledger
