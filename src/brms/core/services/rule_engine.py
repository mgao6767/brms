"""Position-aware RuleEngine: applies accounting rules to open positions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import datetime

    from brms.core.models.transaction import Transaction


@runtime_checkable
class AccountingRule(Protocol):
    """Protocol for position-aware accounting rules."""

    def applies_to(
        self,
        instrument: object,
        position: object,
        market_state: object,
        date: datetime.date,
    ) -> bool:
        """Return True if this rule applies to the given instrument and position."""
        ...

    def generate(
        self,
        instrument: object,
        position: object,
        valuation_store: object,
        market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Generate transactions for the given instrument and position."""
        ...


class RuleEngine:
    """Applies registered accounting rules across all open positions of a bank."""

    def __init__(self) -> None:
        """Initialise an empty rule engine."""
        self._rules: list[AccountingRule] = []

    def register(self, rule: AccountingRule) -> None:
        """Register an accounting rule with the engine."""
        self._rules.append(rule)

    def apply(
        self,
        bank: object,
        valuation_store: object,
        market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Apply all rules to every open position and return aggregated transactions.

        For each open position the engine resolves the associated instrument via
        ``bank.instruments.get(position.instrument_id)``, then iterates registered
        rules.  Rules whose ``applies_to`` returns ``True`` are asked to
        ``generate`` transactions, which are collected and returned as a flat list.
        """
        transactions: list[Transaction] = []
        for position in bank.positions.open_positions():  # type: ignore[union-attr]
            instrument = bank.instruments.get(position.instrument_id)  # type: ignore[union-attr]
            for rule in self._rules:
                if rule.applies_to(instrument, position, market_state, date):
                    transactions.extend(
                        rule.generate(instrument, position, valuation_store, market_state, date),
                    )
        return transactions
