"""Tests for RuleRegistry."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.rules.base import RuleRegistry
from brms.core.rules.context import RuleContext
from brms.core.models.transaction import Transaction, TransactionType


def _ctx(date: datetime.date) -> RuleContext:
    """Build a minimal RuleContext for testing."""
    return RuleContext(date=date, previous_date=None, market_state=MagicMock(), valuation_store=MagicMock())


class AlwaysRule:
    """A rule that always applies and returns a fixed transaction."""

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
        """Return a single fixed transaction."""
        return [Transaction(id="r1", type=TransactionType.INTEREST_PAYMENT, date=_context.date, amount=Decimal("100"))]


class NeverRule:
    """A rule that never applies."""

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


def test_registry_apply_all() -> None:
    """Registry should collect transactions only from rules that apply."""
    registry = RuleRegistry()
    registry.register(AlwaysRule())
    registry.register(NeverRule())
    txs = registry.apply_all(MagicMock(), MagicMock(), MagicMock(), MagicMock(), datetime.date(2024, 1, 1))
    assert len(txs) == 1
    assert txs[0].id == "r1"


def test_empty_registry() -> None:
    """Empty registry should return an empty list."""
    registry = RuleRegistry()
    txs = registry.apply_all(MagicMock(), MagicMock(), MagicMock(), MagicMock(), datetime.date(2024, 1, 1))
    assert txs == []
