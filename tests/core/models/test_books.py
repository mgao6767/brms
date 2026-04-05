"""Tests for BankingBook and TradingBook containers."""

# ruff: noqa: S101

from unittest.mock import MagicMock

import pytest

from brms.core.services.data_service import BankingBook, TradingBook
from brms.core.models.instruments.base import BookType


def test_banking_book_type() -> None:
    """BankingBook.book_type is BookType.BANKING."""
    assert BankingBook.book_type == BookType.BANKING


def test_trading_book_type() -> None:
    """TradingBook.book_type is BookType.TRADING."""
    assert TradingBook.book_type == BookType.TRADING


def test_add_and_iterate() -> None:
    """Added instrument is returned by iteration."""
    book = BankingBook()
    inst = MagicMock()
    inst.id = "i1"
    book.add(inst)
    assert list(book) == [inst]


def test_remove() -> None:
    """Removing by id empties the book."""
    book = BankingBook()
    inst = MagicMock()
    inst.id = "i1"
    book.add(inst)
    book.remove("i1")
    assert list(book) == []


def test_len() -> None:
    """len() reflects the number of instruments."""
    book = TradingBook()
    assert len(book) == 0
    inst = MagicMock()
    inst.id = "i1"
    book.add(inst)
    assert len(book) == 1


def test_remove_nonexistent_raises() -> None:
    """Removing a missing id raises InstrumentNotFoundError."""
    from brms.core.exceptions import InstrumentNotFoundError

    book = BankingBook()
    with pytest.raises(InstrumentNotFoundError):
        book.remove("nonexistent")
