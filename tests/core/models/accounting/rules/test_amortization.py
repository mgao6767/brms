"""Tests for AmortizationRule."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.models.accounting.rules.amortization import AmortizationRule
from brms.core.models.transaction import TransactionType


def _make_instrument(
    payment_dates: list[datetime.date] | None,
    periodic_payment: Decimal = Decimal("5000"),
) -> MagicMock:
    """Return a mock instrument with the given payment_dates and periodic_payment."""
    inst = MagicMock()
    inst.id = "loan-1"
    inst.periodic_payment = periodic_payment
    if payment_dates is not None:
        inst.payment_dates = payment_dates
    else:
        del inst.payment_dates
    # No callable payment_schedule for plain payment_dates instruments
    del inst.payment_schedule
    return inst


def _make_position(instrument_id: str = "loan-1") -> MagicMock:
    """Return a mock position."""
    pos = MagicMock()
    pos.id = "pos-1"
    pos.instrument_id = instrument_id
    return pos


def test_applies_on_payment_date() -> None:
    """Rule should apply when the date is in the instrument's payment_dates list."""
    rule = AmortizationRule()
    inst = _make_instrument([datetime.date(2024, 6, 15), datetime.date(2024, 12, 15)])
    assert rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 15))


def test_does_not_apply_on_non_payment_date() -> None:
    """Rule should not apply when the date is not in payment_dates."""
    rule = AmortizationRule()
    inst = _make_instrument([datetime.date(2024, 6, 15)])
    assert not rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 14))


def test_does_not_apply_if_no_payment_dates_attr() -> None:
    """Rule should not apply when the instrument has no payment_dates attribute."""
    rule = AmortizationRule()
    inst = MagicMock(spec=[])
    assert not rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 15))


def test_generates_amortization_transaction() -> None:
    """Rule should generate an AMORTIZATION transaction with the periodic_payment amount."""
    rule = AmortizationRule()
    periodic_payment = Decimal("5000")
    inst = _make_instrument([datetime.date(2024, 6, 15)], periodic_payment=periodic_payment)
    pos = _make_position()
    txs = rule.generate(inst, pos, MagicMock(), MagicMock(), datetime.date(2024, 6, 15))
    assert len(txs) >= 1
    assert txs[0].type == TransactionType.AMORTIZATION
    assert txs[0].instrument_id == "loan-1"
    assert txs[0].position_id == "pos-1"
    assert txs[0].amount == periodic_payment
