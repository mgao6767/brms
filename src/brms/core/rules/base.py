"""AccountingRule Protocol and RuleRegistry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from brms.core.rules.context import RuleContext

if TYPE_CHECKING:
    import datetime

    from brms.core.models.transaction import Transaction


@runtime_checkable
class AccountingRule(Protocol):
    """Protocol for accounting rules that generate transactions for instruments."""

    def applies_to(
        self,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> bool:
        """Return True if this rule applies to the given instrument on the given date."""
        ...

    def generate(
        self,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate the transactions for the given instrument on the given date."""
        ...


class RuleRegistry:
    """Registry of accounting rules applied to instruments."""

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._rules: list[AccountingRule] = []

    def register(self, rule: AccountingRule) -> None:
        """Register a rule with the registry."""
        self._rules.append(rule)

    def apply_all(
        self,
        instrument: object,
        position: object,
        valuation_store: object,
        market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Apply all applicable rules and return the combined list of transactions."""
        context = RuleContext(date=date, previous_date=None, market_state=market_state, valuation_store=valuation_store)
        transactions: list[Transaction] = []
        for rule in self._rules:
            if rule.applies_to(instrument, position, context):
                transactions.extend(rule.generate(instrument, position, context))
        return transactions
