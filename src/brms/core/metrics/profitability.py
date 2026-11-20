"""Profitability over a trailing year, annualised: ROA, ROE, NIM, and interest-earning assets.

The window is the 365 days ending on the metric date, clipped to the first day with an ordinary
(NORMAL) journal entry; flows are the windowed income statement scaled by 365 / days in window.
With fewer than 30 days of history the metrics are undefined (None).
Denominators are averages of the day's recorded metrics over the window's market days, so
TOTAL_ASSETS, TOTAL_EQUITY and INTEREST_EARNING_ASSETS must be computed before these metrics.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from brms.core.enums import EntryKind, MeasurementBasis, MetricName, PositionSide, ValuationType

if TYPE_CHECKING:
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.models.market_data import MarketState
    from brms.core.services.reporting_service import ReportingService
    from brms.core.stores.metric_store import MetricStore
    from brms.core.stores.valuation_store import ValuationStore

_YEAR = 365
_MIN_DAYS = 30


class InterestEarningAssetsMetric:
    """Carrying value of open long bond and loan positions."""

    name = MetricName.INTEREST_EARNING_ASSETS

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,
        date: datetime.date | None = None,
    ) -> Decimal:
        """Sum the day's carrying values of interest-earning positions."""
        total = Decimal(0)
        for position in bank.positions.open_positions():
            if position.side != PositionSide.LONG:
                continue
            if position.measurement_basis == MeasurementBasis.NA:
                continue
            value = valuation_store.get(position.id, date, ValuationType.CARRYING_VALUE)  # type: ignore[arg-type]
            if value is not None:
                total += Decimal(value)
        return total


class _TrailingYearMetric:
    """Annualised windowed flow / windowed average of a recorded metric."""

    name: MetricName
    denominator: MetricName

    def __init__(self, reporting_service: ReportingService, metric_store: MetricStore) -> None:
        self._reporting = reporting_service
        self._metrics = metric_store
        self._first_entry: dict[int, datetime.date] = {}

    def _window_start(self, ledger: Ledger, date: datetime.date) -> datetime.date:
        first = self._first_entry.get(id(ledger))
        if first is None:
            dates = [e.date for e in ledger.journal.entries if e.kind == EntryKind.NORMAL and e.date is not None]
            first = min(dates, default=date)
            self._first_entry[id(ledger)] = first
        return max(first, date - datetime.timedelta(days=_YEAR - 1))

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,  # noqa: ARG002
        date: datetime.date | None = None,
    ) -> float | None:
        """Annualised flow over the trailing year divided by the window's average denominator."""
        start = self._window_start(bank.ledger, date)  # type: ignore[arg-type]
        if (date - start).days + 1 < _MIN_DAYS:  # type: ignore[operator]
            return None  # annualising a few days of marks is noise, not a return
        statement = self._reporting.income_statement(bank.ledger, start=start, end=date)
        flow = self.flow(statement) * Decimal(_YEAR) / Decimal((date - start).days + 1)  # type: ignore[operator]
        values = [Decimal(str(v)) for _d, v in self._metrics.series(self.denominator, start=start, end=date)]
        if not values:
            return None
        average = sum(values, Decimal(0)) / len(values)
        return None if average == 0 else float(flow / average)

    def flow(self, statement: dict[str, Any]) -> Decimal:
        """Return the numerator's flow from the windowed income statement."""
        raise NotImplementedError


class ROAMetric(_TrailingYearMetric):
    """Return on assets: annualised net income / average total assets."""

    name = MetricName.ROA
    denominator = MetricName.TOTAL_ASSETS

    def flow(self, statement: dict[str, Any]) -> Decimal:  # noqa: D102
        return Decimal(str(statement["net_income"]))


class ROEMetric(_TrailingYearMetric):
    """Return on equity: annualised net income / average total equity."""

    name = MetricName.ROE
    denominator = MetricName.TOTAL_EQUITY

    def flow(self, statement: dict[str, Any]) -> Decimal:  # noqa: D102
        return Decimal(str(statement["net_income"]))


class NetInterestMarginMetric(_TrailingYearMetric):
    """Net interest margin: annualised (interest income - interest expense) / average interest-earning assets."""

    name = MetricName.NET_INTEREST_MARGIN
    denominator = MetricName.INTEREST_EARNING_ASSETS

    def flow(self, statement: dict[str, Any]) -> Decimal:  # noqa: D102
        income = sum((r["balance"] for r in statement["income"] if r["account"] == "Interest Income"), 0.0)
        expense = sum((r["balance"] for r in statement["expenses"] if r["account"] == "Interest Expense"), 0.0)
        return Decimal(str(income)) - Decimal(str(expense))
