"""Capital metrics that delegate to ReportingService for closed-ledger values."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from brms.core.enums import MetricName

if TYPE_CHECKING:
    import datetime

    from brms.core.models.market_data import MarketState
    from brms.core.services.reporting_service import ReportingService
    from brms.core.stores.valuation_store import ValuationStore


class TotalAssetsMetric:
    """Total assets from the closed balance sheet."""

    name = MetricName.TOTAL_ASSETS

    def __init__(self, reporting_service: ReportingService) -> None:
        """Initialize with a ReportingService reference."""
        self._reporting = reporting_service

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
        date: datetime.date | None = None,
    ) -> float:
        """Total assets from the closed balance sheet."""
        bs = self._reporting.balance_sheet(bank.ledger, date=date)
        return bs["total_assets"]


class TotalLiabilitiesMetric:
    """Total liabilities from the closed balance sheet."""

    name = MetricName.TOTAL_LIABILITIES

    def __init__(self, reporting_service: ReportingService) -> None:
        """Initialize with a ReportingService reference."""
        self._reporting = reporting_service

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
        date: datetime.date | None = None,
    ) -> float:
        """Total liabilities from the closed balance sheet."""
        bs = self._reporting.balance_sheet(bank.ledger, date=date)
        return bs["total_liabilities"]


class TotalEquityMetric:
    """Total equity from the closed balance sheet (includes net income)."""

    name = MetricName.TOTAL_EQUITY

    def __init__(self, reporting_service: ReportingService) -> None:
        """Initialize with a ReportingService reference."""
        self._reporting = reporting_service

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
        date: datetime.date | None = None,
    ) -> float:
        """Total equity from the closed balance sheet."""
        bs = self._reporting.balance_sheet(bank.ledger, date=date)
        return bs["total_equity"]


class CET1RatioMetric:
    """CET1 capital ratio from the closed balance sheet (simplified)."""

    name = MetricName.CET1_RATIO

    def __init__(self, reporting_service: ReportingService) -> None:
        """Initialize with a ReportingService reference."""
        self._reporting = reporting_service

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
        date: datetime.date | None = None,
    ) -> float:
        """CET1 (equity) / total assets from the closed balance sheet."""
        bs = self._reporting.balance_sheet(bank.ledger, date=date)
        assets = bs["total_assets"]
        if assets == 0:
            return 0.0
        return bs["total_equity"] / assets
