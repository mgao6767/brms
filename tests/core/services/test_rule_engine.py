"""Tests for RuleEngine."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from unittest.mock import MagicMock

from brms.core.models.transaction import Transaction
from brms.core.rules.context import RuleContext
from brms.core.services.rule_engine import RuleEngine

EXPECTED_TWO = 2


class AlwaysRule:
    """Accounting rule that always applies and returns one transaction."""

    def applies_to(
        self,
        _instrument: object,
        _position: object,
        _context: RuleContext,
    ) -> bool:
        """Return True unconditionally."""
        return True

    def generate(
        self,
        _instrument: object,
        _position: object,
        _context: RuleContext,
    ) -> list[Transaction]:
        """Return a single mock transaction."""
        tx = MagicMock(spec=Transaction)
        return [tx]


class NeverRule:
    """Accounting rule that never applies and returns nothing."""

    def applies_to(
        self,
        _instrument: object,
        _position: object,
        _context: RuleContext,
    ) -> bool:
        """Return False unconditionally."""
        return False

    def generate(
        self,
        _instrument: object,
        _position: object,
        _context: RuleContext,
    ) -> list[Transaction]:
        """Return an empty list."""
        return []


def test_apply_returns_transactions() -> None:
    """RuleEngine collects transactions from rules that apply."""
    engine = RuleEngine()
    engine.register(AlwaysRule())
    engine.register(NeverRule())

    bank = MagicMock()
    pos = MagicMock()
    pos.id = "p1"
    pos.instrument_id = "i1"
    bank.positions.open_positions.return_value = [pos]
    bank.instruments.get.return_value = MagicMock()

    txs = engine.apply(bank, MagicMock(), MagicMock(), datetime.date(2024, 1, 1))
    assert len(txs) == 1


def test_empty_engine() -> None:
    """RuleEngine with no open positions returns an empty list."""
    engine = RuleEngine()

    bank = MagicMock()
    bank.positions.open_positions.return_value = []

    txs = engine.apply(bank, MagicMock(), MagicMock(), datetime.date(2024, 1, 1))
    assert txs == []


def test_no_rules_registered() -> None:
    """RuleEngine with rules registered but no positions returns an empty list."""
    engine = RuleEngine()
    engine.register(AlwaysRule())

    bank = MagicMock()
    bank.positions.open_positions.return_value = []

    txs = engine.apply(bank, MagicMock(), MagicMock(), datetime.date(2024, 1, 1))
    assert txs == []


def test_multiple_positions_accumulate_transactions() -> None:
    """RuleEngine accumulates transactions across multiple positions."""
    engine = RuleEngine()
    engine.register(AlwaysRule())

    bank = MagicMock()
    pos1, pos2 = MagicMock(), MagicMock()
    pos1.id = "p1"
    pos1.instrument_id = "i1"
    pos2.id = "p2"
    pos2.instrument_id = "i2"
    bank.positions.open_positions.return_value = [pos1, pos2]
    bank.instruments.get.return_value = MagicMock()

    txs = engine.apply(bank, MagicMock(), MagicMock(), datetime.date(2024, 1, 1))
    assert len(txs) == EXPECTED_TWO


def test_instrument_fetched_by_position_instrument_id() -> None:
    """RuleEngine calls bank.instruments.get with each position's instrument_id."""
    engine = RuleEngine()
    engine.register(NeverRule())

    bank = MagicMock()
    pos = MagicMock()
    pos.id = "p1"
    pos.instrument_id = "bond-42"
    bank.positions.open_positions.return_value = [pos]
    bank.instruments.get.return_value = MagicMock()

    engine.apply(bank, MagicMock(), MagicMock(), datetime.date(2024, 6, 1))
    bank.instruments.get.assert_called_once_with("bond-42")
