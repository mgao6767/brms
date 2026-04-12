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
    """Applies accounting rules declared by each instrument to open positions.

    Rules are keyed by their class.  Each instrument declares which rule
    classes apply to it via ``instrument.applicable_rules`` (a frozenset of
    rule classes).  The engine only runs rules that the instrument opts into.
    """

    def __init__(self, rules: dict[type, AccountingRule] | Iterable[AccountingRule] = ()) -> None:
        """Initialise the rule engine with a class-keyed dict or legacy iterable."""
        if isinstance(rules, dict):
            self._rules: dict[type, AccountingRule] = dict(rules)
        else:
            self._rules = {type(r): r for r in rules}

    def register(self, rule: AccountingRule) -> None:
        """Register an accounting rule with the engine."""
        self._rules[type(rule)] = rule

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
        """Apply instrument-declared rules to every open position.

        For each open position the engine reads ``instrument.applicable_rules``
        to determine which rules to evaluate.  Only rules whose ``applies_to``
        returns ``True`` produce transactions.
        """
        context = RuleContext(date, previous_date, market_state, valuation_store, has_market_data=has_market_data)
        transactions: list[Transaction] = []
        for position in bank.positions.open_positions():  # type: ignore[union-attr]
            instrument = bank.instruments.get(position.instrument_id)  # type: ignore[union-attr]
            for rule_class in getattr(instrument, "applicable_rules", frozenset()):
                rule = self._rules.get(rule_class)
                if rule is not None and rule.applies_to(instrument, position, context):
                    transactions.extend(
                        rule.generate(instrument, position, context),
                    )
        return transactions
