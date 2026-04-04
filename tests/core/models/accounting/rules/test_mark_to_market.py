"""Tests for MarkToMarketRule."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.models.accounting.rules.mark_to_market import MarkToMarketRule
from brms.core.models.instruments.base import InstrumentClass
from brms.core.models.transaction import TransactionType


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


def test_applies_to_fvtpl() -> None:
    """Rule should apply when the instrument is classified as FVTPL."""
    rule = MarkToMarketRule()
    inst = _make_instrument(InstrumentClass.FVTPL)
    assert rule.applies_to(inst, MagicMock(), datetime.date(2024, 6, 15))


def test_applies_to_fvoci() -> None:
    """Rule should apply when the instrument is classified as FVOCI."""
    rule = MarkToMarketRule()
    inst = _make_instrument(InstrumentClass.FVOCI)
    assert rule.applies_to(inst, MagicMock(), datetime.date(2024, 6, 15))


def test_does_not_apply_to_htm() -> None:
    """Rule should not apply when the instrument is classified as HTM."""
    rule = MarkToMarketRule()
    inst = _make_instrument(InstrumentClass.HTM)
    assert not rule.applies_to(inst, MagicMock(), datetime.date(2024, 6, 15))


def test_does_not_apply_when_no_instrument_class() -> None:
    """Rule should not apply when the instrument has no instrument_class attribute."""
    rule = MarkToMarketRule()
    inst = MagicMock(spec=[])
    assert not rule.applies_to(inst, MagicMock(), datetime.date(2024, 6, 15))


def test_generates_mark_to_market_transaction() -> None:
    """Rule should generate a MARK_TO_MARKET transaction with face_value vs current value as proxy."""
    rule = MarkToMarketRule()
    face_value = Decimal("1000000")
    current_value = 950000.0
    inst = _make_instrument(InstrumentClass.FVTPL, face_value=face_value, value=current_value)
    txs = rule.generate(inst, MagicMock(), datetime.date(2024, 6, 15))
    assert len(txs) >= 1
    assert txs[0].type == TransactionType.MARK_TO_MARKET
    assert txs[0].instrument_id == "bond-2"
    expected_amount = Decimal(str(current_value)) - face_value
    assert txs[0].amount == expected_amount


def test_generate_includes_instrument_class_in_metadata() -> None:
    """Rule should include instrument_class name in transaction metadata."""
    rule = MarkToMarketRule()
    inst = _make_instrument(InstrumentClass.FVOCI)
    txs = rule.generate(inst, MagicMock(), datetime.date(2024, 6, 15))
    assert len(txs) >= 1
    metadata_dict = dict(txs[0].metadata)
    assert metadata_dict.get("instrument_class") == InstrumentClass.FVOCI.name
