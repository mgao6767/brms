"""Metrics package for BRMS bank simulation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.core.metrics.capital import (
    CET1RatioMetric,
    TotalAssetsMetric,
    TotalEquityMetric,
    TotalLiabilitiesMetric,
)
from brms.core.metrics.profitability import ROAMetric, ROEMetric

if TYPE_CHECKING:
    from brms.core.services.reporting_service import ReportingService


def default_metrics(reporting_service: ReportingService) -> tuple:
    """Return a tuple of all default metric instances."""
    return (
        TotalAssetsMetric(reporting_service),
        TotalLiabilitiesMetric(reporting_service),
        TotalEquityMetric(reporting_service),
        CET1RatioMetric(reporting_service),
        ROAMetric(reporting_service),
        ROEMetric(reporting_service),
    )
