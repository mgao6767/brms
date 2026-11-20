"""Tests for MarkToMarketRule."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from brms.core.enums import MeasurementBasis, TxMeta, ValuationType
from brms.core.exceptions import ValuationError
from brms.core.rules.context import RuleContext
from brms.core.rules.mark_to_market import MarkToMarketRule
from brms.core.models.transaction import TransactionType
from brms.core.stores.valuation_store import ValuationStore


def _ctx(date: datetime.date, valuation_store: object | None = None) -> RuleContext:
    """Build a minimal RuleContext for testing."""
    return RuleContext(
        date=date,
        previous_date=None,
        market_state=MagicMock(),
        valuation_store=valuation_store or MagicMock(),
    )


def _make_instrument(
    measurement_basis: MeasurementBasis,
    face_value: Decimal = Decimal("1000000"),
    value: float = 950000.0,
) -> MagicMock:
    """Return a mock instrument with a given measurement_basis, face_value, and value."""
    inst = MagicMock()
    inst.id = "bond-2"
    inst.measurement_basis = measurement_basis
    inst.face_value = face_value
    inst.value = value
    return inst


def _make_position(
    measurement_basis: MeasurementBasis = MeasurementBasis.FVTPL,
    acquisition_cost: Decimal = Decimal("1000000"),
) -> MagicMock:
    """Return a mock position with the given measurement_basis."""
    pos = MagicMock()
    pos.id = "pos-1"
    pos.instrument_id = "bond-2"
    pos.measurement_basis = measurement_basis
    pos.acquisition_cost = acquisition_cost
    return pos


def test_applies_to_fvtpl() -> None:
    """Rule should apply when the position is classified as FVTPL."""
    rule = MarkToMarketRule()
    inst = _make_instrument(MeasurementBasis.FVTPL)
    pos = _make_position(MeasurementBasis.FVTPL)
    assert rule.applies_to(inst, pos, _ctx(datetime.date(2024, 6, 15)))


def test_applies_to_fvoci() -> None:
    """Rule should apply when the position is classified as FVOCI."""
    rule = MarkToMarketRule()
    inst = _make_instrument(MeasurementBasis.FVOCI)
    pos = _make_position(MeasurementBasis.FVOCI)
    assert rule.applies_to(inst, pos, _ctx(datetime.date(2024, 6, 15)))


def test_does_not_apply_to_amortized_cost() -> None:
    """Rule should not apply when the position is classified as AMORTIZED_COST."""
    rule = MarkToMarketRule()
    inst = _make_instrument(MeasurementBasis.AMORTIZED_COST)
    pos = _make_position(MeasurementBasis.AMORTIZED_COST)
    assert not rule.applies_to(inst, pos, _ctx(datetime.date(2024, 6, 15)))


def test_generates_mark_to_market_transaction() -> None:
    """Rule should generate a MARK_TO_MARKET transaction based on valuation store data."""
    rule = MarkToMarketRule()
    date = datetime.date(2024, 6, 15)
    current_value = Decimal("950000")
    acquisition_cost = Decimal("1000000")
    pos = _make_position(MeasurementBasis.FVTPL, acquisition_cost=acquisition_cost)
    inst = _make_instrument(MeasurementBasis.FVTPL)

    previous_carrying = Decimal("990000")
    vs = ValuationStore()
    vs.record(pos.id, date - datetime.timedelta(days=1), ValuationType.CARRYING_VALUE, previous_carrying)
    vs.record(pos.id, date, ValuationType.FAIR_VALUE, current_value)

    txs = rule.generate(inst, pos, _ctx(date, valuation_store=vs))
    assert len(txs) >= 1
    assert txs[0].type == TransactionType.MARK_TO_MARKET
    assert txs[0].instrument_id == "bond-2"
    assert txs[0].amount == current_value - previous_carrying


def test_generate_without_previous_carrying_value_raises() -> None:
    """A missing previous carrying value is an error, never a fallback to acquisition cost."""
    rule = MarkToMarketRule()
    date = datetime.date(2024, 6, 15)
    pos = _make_position(MeasurementBasis.FVTPL)
    vs = ValuationStore()
    vs.record(pos.id, date, ValuationType.FAIR_VALUE, Decimal("950000"))
    with pytest.raises(ValuationError, match="pos-1"):
        rule.generate(_make_instrument(MeasurementBasis.FVTPL), pos, _ctx(date, valuation_store=vs))


def test_generate_includes_measurement_basis_in_metadata() -> None:
    """Rule should include measurement_basis name in transaction metadata."""
    rule = MarkToMarketRule()
    date = datetime.date(2024, 6, 15)
    pos = _make_position(MeasurementBasis.FVOCI, acquisition_cost=Decimal("100000"))
    inst = _make_instrument(MeasurementBasis.FVOCI)

    vs = ValuationStore()
    previous = date - datetime.timedelta(days=1)
    vs.record(pos.id, previous, ValuationType.CARRYING_VALUE, Decimal("100000"))
    vs.record(pos.id, previous, ValuationType.AMORTIZED_COST, Decimal("100000"))
    vs.record(pos.id, date, ValuationType.AMORTIZED_COST, Decimal("100000"))
    vs.record(pos.id, date, ValuationType.FAIR_VALUE, Decimal("110000"))

    txs = rule.generate(inst, pos, _ctx(date, valuation_store=vs))
    assert len(txs) >= 1
    metadata_dict = dict(txs[0].metadata)
    assert metadata_dict.get(TxMeta.MEASUREMENT_BASIS) == MeasurementBasis.FVOCI
