"""Metrics package for BRMS bank simulation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.core.metrics.capital import (
    EquityToAssetsMetric,
    TotalAssetsMetric,
    TotalEquityMetric,
    TotalLiabilitiesMetric,
)
from brms.core.metrics.irrbb import irrbb_metrics
from brms.core.metrics.profitability import (
    InterestEarningAssetsMetric,
    NetInterestMarginMetric,
    ROAMetric,
    ROEMetric,
)
from brms.core.metrics.regulatory import regulatory_metrics

if TYPE_CHECKING:
    import QuantLib as ql  # noqa: N813

    from brms.core.services.reporting_service import ReportingService
    from brms.core.stores.metric_store import MetricStore


def default_metrics(
    reporting_service: ReportingService,
    metric_store: MetricStore,
    yield_handle: ql.RelinkableYieldTermStructureHandle | None = None,
) -> tuple:
    """Return the default metrics, in computation order.

    Balance-sheet totals and interest-earning assets come first: the trailing-year
    profitability metrics average them from *metric_store*, including today's values.
    The interest-rate-risk metrics need the engine's shared *yield_handle* and are left
    out without it.
    """
    irrbb = irrbb_metrics(yield_handle, metric_store) if yield_handle is not None else ()
    return (
        TotalAssetsMetric(reporting_service),
        TotalLiabilitiesMetric(reporting_service),
        TotalEquityMetric(reporting_service),
        EquityToAssetsMetric(reporting_service),
        InterestEarningAssetsMetric(),
        *regulatory_metrics(reporting_service),
        ROAMetric(reporting_service, metric_store),
        ROEMetric(reporting_service, metric_store),
        NetInterestMarginMetric(reporting_service, metric_store),
        *irrbb,
    )
