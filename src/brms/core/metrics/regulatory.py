"""Regulatory capital, RWA, capital ratios and the leverage ratio.

All figures for a day come from one :class:`CapitalCalculator` pass over the as-if-closed
balance sheet and the day's valuations, shared by every metric in this module.

- CET1 = total equity - (accumulated OCI if the AOCI filter is on) - intangible assets.
- Tier 1 = CET1 + AT1; Total capital = Tier 1 + Tier 2 (AT1 and Tier 2 are inputs).
- Total RWA = credit RWA (standardised approach) + operational RWA (an input).
- Leverage exposure = total assets - intangible assets (on-balance-sheet only).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from brms.core.enums import MetricName
from brms.core.metrics.risk.credit_risk.exposures import credit_rwa

if TYPE_CHECKING:
    import datetime

    from brms.core.models.bank import Bank
    from brms.core.models.market_data import MarketState
    from brms.core.services.reporting_service import ReportingService
    from brms.core.stores.valuation_store import ValuationStore


@dataclass(frozen=True)
class CapitalFigures:
    """The day's regulatory capital and risk figures."""

    cet1: Decimal
    tier1: Decimal
    total_capital: Decimal
    credit_rwa: Decimal
    operational_rwa: Decimal
    total_rwa: Decimal
    leverage_exposure: Decimal


class CapitalCalculator:
    """Computes :class:`CapitalFigures`, memoised per (ledger, date, journal length, regulatory inputs)."""

    def __init__(self, reporting_service: ReportingService) -> None:
        """Use *reporting_service* for the as-if-closed balance sheet."""
        self._reporting = reporting_service
        self._key: tuple[object, ...] | None = None
        self._figures: CapitalFigures | None = None

    def figures(self, bank: Bank, valuation_store: ValuationStore, date: datetime.date) -> CapitalFigures:
        """Return the capital figures of *bank* on *date*."""
        key = (id(bank.ledger), date, len(bank.ledger.journal.entries), bank.regulatory)
        if key == self._key and self._figures is not None:
            return self._figures
        bs = self._reporting.balance_sheet(bank.ledger, date=date)
        rows = {row["account"]: Decimal(str(row["balance"])) for row in bs["assets"] + bs["equity"]}
        intangibles = rows.get("Intangible Assets", Decimal(0))
        aoci = rows.get("Accumulated OCI", Decimal(0))
        regulatory = bank.regulatory
        cet1 = Decimal(str(bs["total_equity"])) - intangibles - (aoci if regulatory.aoci_filter else Decimal(0))
        tier1 = cet1 + regulatory.additional_tier1
        credit = credit_rwa(bank, valuation_store, date, bs).total
        figures = CapitalFigures(
            cet1=cet1,
            tier1=tier1,
            total_capital=tier1 + regulatory.tier2,
            credit_rwa=credit,
            operational_rwa=regulatory.operational_rwa,
            total_rwa=credit + regulatory.operational_rwa,
            leverage_exposure=Decimal(str(bs["total_assets"])) - intangibles,
        )
        self._key, self._figures = key, figures
        return figures


class _CapitalMetric:
    """Base for metrics read off :class:`CapitalFigures`."""

    name: MetricName

    def __init__(self, calculator: CapitalCalculator) -> None:
        self._calculator = calculator

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,
        date: datetime.date | None = None,
    ) -> Decimal | float | None:
        """Compute the metric for *date*."""
        return self.value(self._calculator.figures(bank, valuation_store, date))  # type: ignore[arg-type]

    def value(self, figures: CapitalFigures) -> Decimal | float | None:
        """Pick or derive this metric from the day's figures."""
        raise NotImplementedError


def _ratio(numerator: Decimal, denominator: Decimal) -> float | None:
    return None if denominator == 0 else float(numerator / denominator)


class CET1CapitalMetric(_CapitalMetric):
    """Common Equity Tier 1 capital."""

    name = MetricName.CET1_CAPITAL

    def value(self, figures: CapitalFigures) -> Decimal:  # noqa: D102
        return figures.cet1


class Tier1CapitalMetric(_CapitalMetric):
    """Tier 1 capital."""

    name = MetricName.TIER1_CAPITAL

    def value(self, figures: CapitalFigures) -> Decimal:  # noqa: D102
        return figures.tier1


class TotalCapitalMetric(_CapitalMetric):
    """Total capital (Tier 1 + Tier 2)."""

    name = MetricName.TOTAL_CAPITAL

    def value(self, figures: CapitalFigures) -> Decimal:  # noqa: D102
        return figures.total_capital


class CreditRWAMetric(_CapitalMetric):
    """Credit RWA, standardised approach."""

    name = MetricName.CREDIT_RWA

    def value(self, figures: CapitalFigures) -> Decimal:  # noqa: D102
        return figures.credit_rwa


class OperationalRWAMetric(_CapitalMetric):
    """Operational RWA (an input)."""

    name = MetricName.OPERATIONAL_RWA

    def value(self, figures: CapitalFigures) -> Decimal:  # noqa: D102
        return figures.operational_rwa


class TotalRWAMetric(_CapitalMetric):
    """Total RWA."""

    name = MetricName.TOTAL_RWA

    def value(self, figures: CapitalFigures) -> Decimal:  # noqa: D102
        return figures.total_rwa


class CET1RatioMetric(_CapitalMetric):
    """CET1 capital / total RWA (None when there is no RWA)."""

    name = MetricName.CET1_RATIO

    def value(self, figures: CapitalFigures) -> float | None:  # noqa: D102
        return _ratio(figures.cet1, figures.total_rwa)


class Tier1RatioMetric(_CapitalMetric):
    """Tier 1 capital / total RWA."""

    name = MetricName.TIER1_RATIO

    def value(self, figures: CapitalFigures) -> float | None:  # noqa: D102
        return _ratio(figures.tier1, figures.total_rwa)


class TotalCapitalRatioMetric(_CapitalMetric):
    """Total capital / total RWA."""

    name = MetricName.TOTAL_CAPITAL_RATIO

    def value(self, figures: CapitalFigures) -> float | None:  # noqa: D102
        return _ratio(figures.total_capital, figures.total_rwa)


class LeverageRatioMetric(_CapitalMetric):
    """Tier 1 capital / leverage exposure measure."""

    name = MetricName.LEVERAGE_RATIO

    def value(self, figures: CapitalFigures) -> float | None:  # noqa: D102
        return _ratio(figures.tier1, figures.leverage_exposure)


def regulatory_metrics(reporting_service: ReportingService) -> tuple[_CapitalMetric, ...]:
    """Return the regulatory metrics, sharing one calculator."""
    calculator = CapitalCalculator(reporting_service)
    return tuple(
        cls(calculator)
        for cls in (
            CET1CapitalMetric,
            Tier1CapitalMetric,
            TotalCapitalMetric,
            CreditRWAMetric,
            OperationalRWAMetric,
            TotalRWAMetric,
            CET1RatioMetric,
            Tier1RatioMetric,
            TotalCapitalRatioMetric,
            LeverageRatioMetric,
        )
    )
