"""Tests for MaturityRule."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.rules.maturity import MaturityRule
from brms.core.models.transaction import TransactionType


def _make_instrument(maturity_date: datetime.date | None) -> MagicMock:
    """Return a mock instrument with the given maturity date and a fixed face value."""
    inst = MagicMock()
    inst.id = "bond-1"
    inst.maturity_date = maturity_date
    inst.face_value = Decimal("1000000")
    return inst


def _make_position(instrument_id: str = "bond-1", acquisition_cost: Decimal = Decimal("1000000")) -> MagicMock:
    """Return a mock position with the given instrument_id and acquisition_cost."""
    pos = MagicMock()
    pos.id = "pos-1"
    pos.instrument_id = instrument_id
    pos.acquisition_cost = acquisition_cost
    pos.instrument_class = MagicMock()
    pos.instrument_class.name = "HTM"
    return pos


def test_applies_on_maturity_date() -> None:
    """Rule should apply when the date matches the instrument's maturity date."""
    rule = MaturityRule()
    inst = _make_instrument(datetime.date(2024, 6, 15))
    assert rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 15))


def test_does_not_apply_before_maturity() -> None:
    """Rule should not apply before the maturity date."""
    rule = MaturityRule()
    inst = _make_instrument(datetime.date(2024, 6, 15))
    assert not rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 14))


def test_does_not_apply_if_no_maturity() -> None:
    """Rule should not apply when the instrument has no maturity date."""
    rule = MaturityRule()
    inst = _make_instrument(None)
    assert not rule.applies_to(inst, MagicMock(), MagicMock(), datetime.date(2024, 6, 15))


def test_generates_settlement_transaction() -> None:
    """Rule should generate a MATURITY_SETTLEMENT transaction with the correct fields."""
    rule = MaturityRule()
    inst = _make_instrument(datetime.date(2024, 6, 15))
    pos = _make_position()
    txs = rule.generate(inst, pos, MagicMock(), MagicMock(), datetime.date(2024, 6, 15))
    assert len(txs) >= 1
    assert txs[0].instrument_id == "bond-1"
    assert txs[0].position_id == "pos-1"
    assert txs[0].type == TransactionType.MATURITY_SETTLEMENT
    assert txs[0].amount == Decimal("1000000")
