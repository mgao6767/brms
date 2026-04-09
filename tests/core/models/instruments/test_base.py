"""Tests for instrument base classes and enums."""

# ruff: noqa: S101

import pytest

from brms.core.models.instruments.base import BookType, Instrument, InstrumentClass


def test_book_type_enum() -> None:
    """BookType enum has banking and trading values."""
    assert BookType.BANKING.value == "banking"
    assert BookType.TRADING.value == "trading"


def test_instrument_class_enum() -> None:
    """InstrumentClass enum exposes expected accounting classifications."""
    assert InstrumentClass.HTM
    assert InstrumentClass.FVOCI
    assert InstrumentClass.FVTPL
    assert InstrumentClass.LOAN_AND_MORTGAGE


def test_instrument_is_abstract() -> None:
    """Instrument cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Instrument()  # type: ignore[abstract]
