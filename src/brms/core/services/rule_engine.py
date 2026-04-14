"""Position-aware RuleEngine: applies accounting rules to open positions.

Rules are executed in a defined priority order to ensure logical consistency:

1. **Accruals** — recognize earned/owed amounts (no cash movement)
2. **Mark-to-market** — revalue positions to fair value
3. **Cash flows** — coupon payments, interest settlements, amortization
4. **Maturity** — settle and close positions (must be last)
"""

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


# Priority order: lower number runs first.
# Rules not listed here get a default priority of 50 (between mark-to-market and cash flows).
_RULE_PRIORITY: dict[str, int] = {
    "InterestIncomeAccrualRule": 10,
    "DepositInterestAccrualRule": 10,
    "MarkToMarketRule": 20,
    "CouponPaymentRule": 60,
    "InterestPaymentRule": 60,
    "LoanInterestSettlementRule": 60,
    "DepositInterestSettlementRule": 60,
    "AmortizationRule": 60,
    "MaturityRule": 90,
}

_DEFAULT_PRIORITY = 50


class RuleEngine:
    """Applies accounting rules declared by each instrument to open positions.

    Rules are keyed by their class.  Each instrument declares which rule
    classes apply to it via ``instrument.applicable_rules`` (a frozenset of
    rule classes).  The engine only runs rules that the instrument opts into.

    Rules are executed in priority order (accruals → mark-to-market →
    cash flows → maturity) to ensure logical consistency.
    """

    def __init__(self, rules: dict[type, AccountingRule] | Iterable[AccountingRule] = ()) -> None:
        """Initialise the rule engine with a class-keyed dict or legacy iterable."""
        if isinstance(rules, dict):
            self._rules: dict[type, AccountingRule] = dict(rules)
        else:
            self._rules = {type(r): r for r in rules}
        self._sorted_keys = self._build_sorted_keys()

    def register(self, rule: AccountingRule) -> None:
        """Register an accounting rule with the engine."""
        self._rules[type(rule)] = rule
        self._sorted_keys = self._build_sorted_keys()

    def _build_sorted_keys(self) -> list[type]:
        """Return rule classes sorted by execution priority (cached)."""
        return sorted(self._rules, key=lambda cls: _RULE_PRIORITY.get(cls.__name__, _DEFAULT_PRIORITY))

    def apply(  # noqa: PLR0913
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
        returns ``True`` produce transactions.  Rules are sorted by priority
        so that accruals run before mark-to-market, cash flows, and maturity.
        """
        context = RuleContext(date, previous_date, market_state, valuation_store, has_market_data=has_market_data)
        transactions: list[Transaction] = []
        for position in bank.positions.open_positions():  # type: ignore[union-attr]
            instrument = bank.instruments.get(position.instrument_id)  # type: ignore[union-attr]
            applicable = getattr(instrument, "applicable_rules", frozenset())
            for rule_class in self._sorted_keys:
                if rule_class not in applicable:
                    continue
                rule = self._rules[rule_class]
                if rule.applies_to(instrument, position, context):
                    transactions.extend(
                        rule.generate(instrument, position, context),
                    )
        return transactions
