"""Tests for ValuationService."""

from unittest.mock import MagicMock

from brms.core.models.instruments.base import BookType
from brms.core.services.valuation_service import ValuationService

EXPECTED_SINGLE = 42.0
EXPECTED_I1 = 100.0
EXPECTED_I2 = 200.0
EXPECTED_BOOK_LEN = 2


def test_value_instrument_selects_strategy_by_book() -> None:
    """value_instrument returns the result from instrument.accept and calls the visitor."""
    service = ValuationService()
    instrument = MagicMock()
    market_state = MagicMock()
    instrument.accept.return_value = EXPECTED_SINGLE
    result = service.value_instrument(instrument, BookType.BANKING, market_state)
    assert instrument.accept.called  # noqa: S101
    assert result == EXPECTED_SINGLE  # noqa: S101


def test_value_book() -> None:
    """value_book iterates the book and returns a value per instrument."""
    service = ValuationService()
    book = MagicMock()
    book.book_type = BookType.TRADING
    i1, i2 = MagicMock(), MagicMock()
    i1.accept.return_value = EXPECTED_I1
    i2.accept.return_value = EXPECTED_I2
    book.__iter__ = MagicMock(return_value=iter([i1, i2]))
    results = service.value_book(book, MagicMock())
    assert len(results) == EXPECTED_BOOK_LEN  # noqa: S101
