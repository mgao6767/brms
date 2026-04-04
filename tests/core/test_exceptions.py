"""Tests for the BRMS domain exception hierarchy."""

# ruff: noqa: S101
import pytest

from brms.core.exceptions import (
    BRMSError,
    DataLoadError,
    InstrumentNotFoundError,
    InvalidTransactionError,
    ScenarioNotAvailableError,
)


def test_hierarchy() -> None:
    """All domain exceptions must derive from BRMSError."""
    assert issubclass(DataLoadError, BRMSError)
    assert issubclass(InvalidTransactionError, BRMSError)
    assert issubclass(InstrumentNotFoundError, BRMSError)
    assert issubclass(ScenarioNotAvailableError, BRMSError)


def test_catch_base() -> None:
    """DataLoadError must be catchable as BRMSError."""
    msg = "bad file"
    with pytest.raises(BRMSError):
        raise DataLoadError(msg)
