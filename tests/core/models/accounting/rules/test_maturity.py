"""Tests for MaturityRule."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.rules.context import RuleContext
from brms.core.rules.maturity import MaturityRule
from brms.core.models.transaction import TransactionType


def _ctx(date: datetime.date, previous_date: datetime.date | None = None) -> RuleContext:
    """Build a minimal RuleContext for testing."""
    return RuleContext(date=date, previous_date=previous_date, market_state=MagicMock(), valuation_store=MagicMock())


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
    pos.measurement_basis = MagicMock()
    pos.measurement_basis.name = "AMORTIZED_COST"
    return pos


def test_applies_on_maturity_date() -> None:
    """Rule should apply when the date matches the instrument's maturity date."""
    rule = MaturityRule()
    inst = _make_instrument(datetime.date(2024, 6, 15))
    assert rule.applies_to(inst, MagicMock(), _ctx(datetime.date(2024, 6, 15)))


def test_does_not_apply_before_maturity() -> None:
    """Rule should not apply before the maturity date."""
    rule = MaturityRule()
    inst = _make_instrument(datetime.date(2024, 6, 15))
    assert not rule.applies_to(inst, MagicMock(), _ctx(datetime.date(2024, 6, 14)))


def test_does_not_apply_if_no_maturity() -> None:
    """Rule should not apply when the instrument has no maturity date."""
    rule = MaturityRule()
    inst = _make_instrument(None)
    assert not rule.applies_to(inst, MagicMock(), _ctx(datetime.date(2024, 6, 15)))


def test_generates_settlement_transaction() -> None:
    """Rule should generate a MATURITY_SETTLEMENT transaction with the correct fields."""
    rule = MaturityRule()
    inst = _make_instrument(datetime.date(2024, 6, 15))
    pos = _make_position()
    txs = rule.generate(inst, pos, _ctx(datetime.date(2024, 6, 15)))
    assert len(txs) >= 1
    assert txs[0].instrument_id == "bond-1"
    assert txs[0].position_id == "pos-1"
    assert txs[0].type == TransactionType.MATURITY_SETTLEMENT
    assert txs[0].amount == Decimal("1000000")


def test_applies_with_exact_match() -> None:
    """Rule should apply when maturity date matches the current date exactly."""
    rule = MaturityRule()
    inst = _make_instrument(datetime.date(2024, 6, 15))
    ctx = _ctx(datetime.date(2024, 6, 15), previous_date=datetime.date(2024, 6, 14))
    assert rule.applies_to(inst, MagicMock(), ctx)


def test_applies_when_already_matured() -> None:
    """Rule should apply when maturity date is before the current date (catch-up)."""
    rule = MaturityRule()
    inst = _make_instrument(datetime.date(2024, 6, 15))
    ctx = _ctx(datetime.date(2024, 6, 17), previous_date=datetime.date(2024, 6, 14))
    assert rule.applies_to(inst, MagicMock(), ctx)
