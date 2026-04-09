"""Position-aware RuleEngine: applies accounting rules to open positions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from brms.core.rules.context import RuleContext

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

    from brms.core.models.bank import Bank
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.market_data import MarketState
    from brms.core.models.position import Position
    from brms.core.models.transaction import Transaction
    from brms.core.stores.valuation_store import ValuationStore


@runtime_checkable
class AccountingRule(Protocol):
    """Protocol for position-aware accounting rules."""

    def applies_to(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True if this rule applies to the given instrument and position."""
        ...

    def generate(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate transactions for the given instrument and position."""
        ...


class RuleEngine:
    """Applies registered accounting rules across all open positions of a bank."""

    def __init__(self, rules: Iterable[AccountingRule] = ()) -> None:
        """Initialise the rule engine, optionally with initial rules."""
        self._rules: list[AccountingRule] = list(rules)

    def register(self, rule: AccountingRule) -> None:
        """Register an accounting rule with the engine."""
        self._rules.append(rule)

    def apply(
        self,
        bank: Bank,
        valuation_store: ValuationStore,
        market_state: MarketState | None,
        date: datetime.date,
        previous_date: datetime.date | None = None,
        *,
        has_market_data: bool = True,
    ) -> list[Transaction]:
        """Apply all rules to every open position and return aggregated transactions.

        For each open position the engine resolves the associated instrument via
        ``bank.instruments.get(position.instrument_id)``, then iterates registered
        rules.  Rules whose ``applies_to`` returns ``True`` are asked to
        ``generate`` transactions, which are collected and returned as a flat list.
        """
        context = RuleContext(date, previous_date, market_state, valuation_store, has_market_data=has_market_data)
        transactions: list[Transaction] = []
        for position in bank.positions.open_positions():  # type: ignore[union-attr]
            instrument = bank.instruments.get(position.instrument_id)  # type: ignore[union-attr]
            for rule in self._rules:
                if rule.applies_to(instrument, position, context):
                    transactions.extend(
                        rule.generate(instrument, position, context),
                    )
        return transactions
