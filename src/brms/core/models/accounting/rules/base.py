"""AccountingRule Protocol and RuleRegistry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import datetime

    from brms.core.models.transaction import Transaction


@runtime_checkable
class AccountingRule(Protocol):
    """Protocol for accounting rules that generate transactions for instruments."""

    def applies_to(
        self,
        instrument: object,
        market_state: object,
        date: datetime.date,
    ) -> bool:
        """Return True if this rule applies to the given instrument on the given date."""
        ...

    def generate(
        self,
        instrument: object,
        market_state: object,
        date: datetime.date,
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
        market_state: object,
        date: datetime.date,
    ) -> list[Transaction]:
        """Apply all applicable rules and return the combined list of transactions."""
        transactions: list[Transaction] = []
        for rule in self._rules:
            if rule.applies_to(instrument, market_state, date):
                transactions.extend(rule.generate(instrument, market_state, date))
        return transactions
