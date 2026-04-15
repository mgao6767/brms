# ruff: noqa: S101
"""Tests for instrument repricing_frequency field."""

import datetime

from brms.core.models.instruments.deposits import Cash, Deposit
from brms.core.models.instruments.equity import CommonEquity


def test_fixed_rate_instrument_has_no_repricing_frequency() -> None:
    """Fixed-rate instruments default to repricing_frequency=None."""
    cash = Cash()
    assert cash.repricing_frequency is None

    deposit = Deposit(name="Test Deposit")
    assert deposit.repricing_frequency is None

    equity = CommonEquity(name="Equity")
    assert equity.repricing_frequency is None


def test_repricing_date_returns_none_for_fixed_rate() -> None:
    """repricing_date() returns None when repricing_frequency is None."""
    deposit = Deposit(name="Test")
    assert deposit.repricing_date(datetime.date(2024, 1, 1)) is None
