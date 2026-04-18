"""Profitability metrics that delegate to ReportingService."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from brms.core.enums import MetricName

if TYPE_CHECKING:
    import datetime

    from brms.core.models.market_data import MarketState
    from brms.core.services.reporting_service import ReportingService
    from brms.core.stores.valuation_store import ValuationStore


class ROAMetric:
    """Return on Assets = Net Income / Total Assets."""

    name = MetricName.ROA

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
        """Net income / total assets from the closed balance sheet."""
        bs = self._reporting.balance_sheet(bank.ledger, date=date)
        total_assets = bs["total_assets"]
        if total_assets == 0:
            return 0.0
        net_income = self._reporting.income_statement(bank.ledger)["net_income"]
        return net_income / total_assets


class ROEMetric:
    """Return on Equity = Net Income / Total Equity."""

    name = MetricName.ROE

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
        """Net income / total equity from the closed balance sheet."""
        bs = self._reporting.balance_sheet(bank.ledger, date=date)
        total_equity = bs["total_equity"]
        if total_equity == 0:
            return 0.0
        net_income = self._reporting.income_statement(bank.ledger)["net_income"]
        return net_income / total_equity
