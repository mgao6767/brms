"""Tests for MarkToMarketRule."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.enums import InstrumentClass as CoreInstrumentClass
from brms.core.enums import ValuationType
from brms.core.rules.mark_to_market import MarkToMarketRule
from brms.core.models.instruments.base import InstrumentClass
from brms.core.models.transaction import TransactionType
from brms.core.stores.valuation_store import ValuationStore


def _make_instrument(
    instrument_class: InstrumentClass,
    face_value: Decimal = Decimal("1000000"),
    value: float = 950000.0,
) -> MagicMock:
    """Return a mock instrument with a given instrument_class, face_value, and value."""
    inst = MagicMock()
    inst.id = "bond-2"
    inst.instrument_class = instrument_class
    inst.face_value = face_value
    inst.value = value
    return inst


def _make_position(
    instrument_class: CoreInstrumentClass = CoreInstrumentClass.FVTPL,
    acquisition_cost: Decimal = Decimal("1000000"),
) -> MagicMock:
    """Return a mock position with the given instrument_class."""
    pos = MagicMock()
    pos.id = "pos-1"
    pos.instrument_id = "bond-2"
    pos.instrument_class = instrument_class
    pos.acquisition_cost = acquisition_cost
    return pos


def test_applies_to_fvtpl() -> None:
    """Rule should apply when the position is classified as FVTPL."""
    rule = MarkToMarketRule()
    inst = _make_instrument(InstrumentClass.FVTPL)
    pos = _make_position(CoreInstrumentClass.FVTPL)
    assert rule.applies_to(inst, pos, MagicMock(), datetime.date(2024, 6, 15))


def test_applies_to_fvoci() -> None:
    """Rule should apply when the position is classified as FVOCI."""
    rule = MarkToMarketRule()
    inst = _make_instrument(InstrumentClass.FVOCI)
    pos = _make_position(CoreInstrumentClass.FVOCI)
    assert rule.applies_to(inst, pos, MagicMock(), datetime.date(2024, 6, 15))


def test_does_not_apply_to_htm() -> None:
    """Rule should not apply when the position is classified as HTM."""
    rule = MarkToMarketRule()
    inst = _make_instrument(InstrumentClass.HTM)
    pos = _make_position(CoreInstrumentClass.HTM)
    assert not rule.applies_to(inst, pos, MagicMock(), datetime.date(2024, 6, 15))


def test_does_not_apply_when_no_instrument_class() -> None:
    """Rule should not apply when the position has no instrument_class attribute."""
    rule = MarkToMarketRule()
    inst = MagicMock(spec=[])
    pos = MagicMock(spec=[])
    assert not rule.applies_to(inst, pos, MagicMock(), datetime.date(2024, 6, 15))


def test_generates_mark_to_market_transaction() -> None:
    """Rule should generate a MARK_TO_MARKET transaction based on valuation store data."""
    rule = MarkToMarketRule()
    date = datetime.date(2024, 6, 15)
    current_value = Decimal("950000")
    acquisition_cost = Decimal("1000000")
    pos = _make_position(CoreInstrumentClass.FVTPL, acquisition_cost=acquisition_cost)
    inst = _make_instrument(InstrumentClass.FVTPL)

    vs = ValuationStore()
    vs.record(pos.id, date, ValuationType.FAIR_VALUE, current_value)

    txs = rule.generate(inst, pos, vs, MagicMock(), date)
    assert len(txs) >= 1
    assert txs[0].type == TransactionType.MARK_TO_MARKET
    assert txs[0].instrument_id == "bond-2"
    expected_amount = current_value - acquisition_cost
    assert txs[0].amount == expected_amount


def test_generate_includes_instrument_class_in_metadata() -> None:
    """Rule should include instrument_class name in transaction metadata."""
    rule = MarkToMarketRule()
    date = datetime.date(2024, 6, 15)
    pos = _make_position(CoreInstrumentClass.FVOCI, acquisition_cost=Decimal("100000"))
    inst = _make_instrument(InstrumentClass.FVOCI)

    vs = ValuationStore()
    vs.record(pos.id, date, ValuationType.FAIR_VALUE, Decimal("110000"))

    txs = rule.generate(inst, pos, vs, MagicMock(), date)
    assert len(txs) >= 1
    metadata_dict = dict(txs[0].metadata)
    assert metadata_dict.get("instrument_class") == "FVOCI"
