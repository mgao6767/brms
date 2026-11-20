"""Interest-rate risk in the banking book metrics: EVE, worst ΔEVE, duration and 12-month NII sensitivity."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from brms.core.enums import MetricName
from brms.core.metrics.risk.interest_rate_risk.eve import EVEResult, eve_scenarios
from brms.core.metrics.risk.interest_rate_risk.maturity_gap import MaturityGapModel, MaturityGapResult

if TYPE_CHECKING:
    import datetime

    import QuantLib as ql  # noqa: N813

    from brms.core.models.bank import Bank
    from brms.core.models.market_data import MarketState
    from brms.core.stores.metric_store import MetricStore
    from brms.core.stores.valuation_store import ValuationStore


class IRRBBCalculator:
    """Runs the EVE scenarios and the repricing gap once per (ledger, date, journal length)."""

    def __init__(self, yield_handle: ql.RelinkableYieldTermStructureHandle) -> None:
        """Use the engine's shared discount and forwarding handle."""
        self._handle = yield_handle
        self._key: tuple[int, datetime.date, int] | None = None
        self._result: tuple[EVEResult, MaturityGapResult] | None = None

    def results(
        self, bank: Bank, valuation_store: ValuationStore, date: datetime.date,
    ) -> tuple[EVEResult, MaturityGapResult]:
        """Return the day's EVE scenarios and repricing gap."""
        key = (id(bank.ledger), date, len(bank.ledger.journal.entries))
        if key != self._key or self._result is None:
            self._result = (
                eve_scenarios(bank, self._handle, date),
                MaturityGapModel().compute(bank, date, valuation_store),
            )
            self._key = key
        return self._result


class _IRRBBMetric:
    name: MetricName

    def __init__(self, calculator: IRRBBCalculator, metric_store: MetricStore) -> None:
        self._calculator = calculator
        self._metrics = metric_store

    def compute(
        self,
        bank: Any,  # noqa: ANN401
        market_state: MarketState,  # noqa: ARG002
        valuation_store: ValuationStore,
        date: datetime.date | None = None,
    ) -> Decimal | float | None:
        """Compute the metric for *date*."""
        eve, gap = self._calculator.results(bank, valuation_store, date)  # type: ignore[arg-type]
        return self.value(eve, gap, date)  # type: ignore[arg-type]

    def value(self, eve: EVEResult, gap: MaturityGapResult, date: datetime.date) -> Decimal | float | None:
        """Pick or derive the metric."""
        raise NotImplementedError


class EVEMetric(_IRRBBMetric):
    """Economic value of equity on the day's curve."""

    name = MetricName.EVE

    def value(self, eve: EVEResult, gap: MaturityGapResult, date: datetime.date) -> Decimal:  # noqa: ARG002, D102
        return eve.base


class WorstDeltaEVEMetric(_IRRBBMetric):
    """Most negative ΔEVE across the six standardised shocks."""

    name = MetricName.DELTA_EVE_WORST

    def value(self, eve: EVEResult, gap: MaturityGapResult, date: datetime.date) -> Decimal:  # noqa: ARG002, D102
        return eve.worst_delta


class WorstDeltaEVEToTier1Metric(_IRRBBMetric):
    """Worst ΔEVE / Tier 1 capital (the supervisory outlier test flags below -15%)."""

    name = MetricName.DELTA_EVE_WORST_TO_TIER1

    def value(self, eve: EVEResult, gap: MaturityGapResult, date: datetime.date) -> float | None:  # noqa: ARG002, D102
        tier1 = self._metrics.get(MetricName.TIER1_CAPITAL, date)
        return None if not tier1 else float(eve.worst_delta / Decimal(tier1))


class AssetDurationMetric(_IRRBBMetric):
    """Effective duration (years) of the bond and loan book."""

    name = MetricName.ASSET_DURATION

    def value(self, eve: EVEResult, gap: MaturityGapResult, date: datetime.date) -> float:  # noqa: ARG002, D102
        return eve.duration


class NIISensitivityUpMetric(_IRRBBMetric):
    """12-month ΔNII under a +200bp parallel shock."""

    name = MetricName.NII_SENSITIVITY_UP

    def value(self, eve: EVEResult, gap: MaturityGapResult, date: datetime.date) -> float:  # noqa: ARG002, D102
        return gap.total_delta_nii_up


class NIISensitivityDownMetric(_IRRBBMetric):
    """12-month ΔNII under a -200bp parallel shock."""

    name = MetricName.NII_SENSITIVITY_DOWN

    def value(self, eve: EVEResult, gap: MaturityGapResult, date: datetime.date) -> float:  # noqa: ARG002, D102
        return gap.total_delta_nii_down


def irrbb_metrics(
    yield_handle: ql.RelinkableYieldTermStructureHandle, metric_store: MetricStore,
) -> tuple[_IRRBBMetric, ...]:
    """Return the IRRBB metrics, sharing one calculator (compute after TIER1_CAPITAL)."""
    calculator = IRRBBCalculator(yield_handle)
    return tuple(
        cls(calculator, metric_store)
        for cls in (
            EVEMetric,
            WorstDeltaEVEMetric,
            WorstDeltaEVEToTier1Metric,
            AssetDurationMetric,
            NIISensitivityUpMetric,
            NIISensitivityDownMetric,
        )
    )
