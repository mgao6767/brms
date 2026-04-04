"""Tests for RuleRegistry."""

# ruff: noqa: S101
from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.models.accounting.rules.base import RuleRegistry
from brms.core.models.transaction import Transaction, TransactionType


class AlwaysRule:
    """A rule that always applies and returns a fixed transaction."""

    def applies_to(self, instrument: object, market_state: object, date: datetime.date) -> bool:  # noqa: ARG002
        """Return True unconditionally."""
        return True

    def generate(self, instrument: object, market_state: object, date: datetime.date) -> list[Transaction]:  # noqa: ARG002
        """Return a single fixed transaction."""
        return [Transaction(id="r1", type=TransactionType.INTEREST_PAYMENT, date=date, amount=Decimal("100"))]


class NeverRule:
    """A rule that never applies."""

    def applies_to(self, instrument: object, market_state: object, date: datetime.date) -> bool:  # noqa: ARG002
        """Return False unconditionally."""
        return False

    def generate(self, instrument: object, market_state: object, date: datetime.date) -> list[Transaction]:  # noqa: ARG002
        """Return an empty list."""
        return []


def test_registry_apply_all() -> None:
    """Registry should collect transactions only from rules that apply."""
    registry = RuleRegistry()
    registry.register(AlwaysRule())
    registry.register(NeverRule())
    txs = registry.apply_all(MagicMock(), MagicMock(), datetime.date(2024, 1, 1))
    assert len(txs) == 1
    assert txs[0].id == "r1"


def test_empty_registry() -> None:
    """Empty registry should return an empty list."""
    registry = RuleRegistry()
    txs = registry.apply_all(MagicMock(), MagicMock(), datetime.date(2024, 1, 1))
    assert txs == []
