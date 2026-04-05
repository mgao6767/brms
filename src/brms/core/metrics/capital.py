"""Concrete capital metric implementations for the BRMS bank simulation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from brms.core.enums import MetricName
from brms.core.models.accounting.accounts import AccountType

if TYPE_CHECKING:
    from brms.core.models.market_data import MarketState
    from brms.core.stores.valuation_store import ValuationStore


class TotalAssetsMetric:
    """Sum of all ASSET account balances."""

    name = MetricName.TOTAL_ASSETS

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
    ) -> float:
        """Sum of all ASSET account balances."""
        total = 0.0
        for account in bank.ledger.chart_of_accounts:
            if account.type == AccountType.ASSET:
                total += account.balance()
        return total


class TotalLiabilitiesMetric:
    """Sum of all LIABILITY account balances."""

    name = MetricName.TOTAL_LIABILITIES

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
    ) -> float:
        """Sum of all LIABILITY account balances."""
        total = 0.0
        for account in bank.ledger.chart_of_accounts:
            if account.type == AccountType.LIABILITY:
                total += account.balance()
        return total


class TotalEquityMetric:
    """Sum of all EQUITY account balances."""

    name = MetricName.TOTAL_EQUITY

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
    ) -> float:
        """Sum of all EQUITY account balances."""
        total = 0.0
        for account in bank.ledger.chart_of_accounts:
            if account.type == AccountType.EQUITY:
                total += account.balance()
        return total


class CET1RatioMetric:
    """CET1 capital ratio: equity / total assets (simplified)."""

    name = MetricName.CET1_RATIO

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
    ) -> float:
        """CET1 / Total Assets (simplified)."""
        equity = 0.0
        assets = 0.0
        for account in bank.ledger.chart_of_accounts:
            if account.type == AccountType.EQUITY:
                equity += account.balance()
            elif account.type == AccountType.ASSET:
                assets += account.balance()
        if assets == 0:
            return 0.0
        return equity / assets
