"""Tests for instrument base classes and enums."""

# ruff: noqa: S101

import pytest

from brms.core.enums import MeasurementBasis
from brms.core.models.instruments.base import BookType, Instrument


def test_book_type_enum() -> None:
    """BookType enum has banking and trading values."""
    assert BookType.BANKING.value == "banking"
    assert BookType.TRADING.value == "trading"


def test_measurement_basis_enum() -> None:
    """MeasurementBasis enum exposes expected accounting classifications."""
    assert MeasurementBasis.AMORTIZED_COST
    assert MeasurementBasis.FVOCI
    assert MeasurementBasis.FVTPL
    assert MeasurementBasis.NA


def test_instrument_is_abstract() -> None:
    """Instrument cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Instrument()  # type: ignore[abstract]
