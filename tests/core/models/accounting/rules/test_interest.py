"""Tests for InterestPaymentRule."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.models.accounting.rules.interest import InterestPaymentRule
from brms.core.models.transaction import TransactionType


def _make_instrument(
    coupon_dates: list[datetime.date] | None,
    face_value: Decimal = Decimal("1000000"),
    coupon_rate: Decimal = Decimal("0.05"),
) -> MagicMock:
    """Return a mock instrument with the given coupon dates, face value, and coupon rate."""
    inst = MagicMock()
    inst.id = "bond-1"
    inst.face_value = face_value
    inst.coupon_rate = coupon_rate
    if coupon_dates is not None:
        inst.coupon_dates = coupon_dates
    else:
        del inst.coupon_dates
    return inst


def test_applies_on_coupon_date() -> None:
    """Rule should apply when the date is in the instrument's coupon_dates list."""
    rule = InterestPaymentRule()
    inst = _make_instrument([datetime.date(2024, 6, 15), datetime.date(2024, 12, 15)])
    assert rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 15))


def test_does_not_apply_on_non_coupon_date() -> None:
    """Rule should not apply when the date is not in coupon_dates."""
    rule = InterestPaymentRule()
    inst = _make_instrument([datetime.date(2024, 6, 15)])
    assert not rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 14))


def test_does_not_apply_if_no_coupon_dates_attr() -> None:
    """Rule should not apply when the instrument has no coupon_dates attribute."""
    rule = InterestPaymentRule()
    inst = MagicMock(spec=[])
    assert not rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 15))


def test_generates_coupon_payment_transaction() -> None:
    """Rule should generate a COUPON_PAYMENT transaction with semi-annual amount."""
    rule = InterestPaymentRule()
    face_value = Decimal("1000000")
    coupon_rate = Decimal("0.05")
    inst = _make_instrument([datetime.date(2024, 6, 15)], face_value=face_value, coupon_rate=coupon_rate)
    txs = rule.generate(inst, MagicMock(), MagicMock(), MagicMock(), datetime.date(2024, 6, 15))
    assert len(txs) >= 1
    assert txs[0].type == TransactionType.COUPON_PAYMENT
    assert txs[0].instrument_id == "bond-1"
    expected_amount = face_value * coupon_rate / Decimal("2")
    assert txs[0].amount == expected_amount
