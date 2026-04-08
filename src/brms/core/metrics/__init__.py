"""Metrics package for BRMS bank simulation."""

from brms.core.metrics.capital import TotalAssetsMetric, TotalEquityMetric, TotalLiabilitiesMetric


def default_metrics() -> tuple:
    """Return a tuple of all default metric instances."""
    return (
        TotalAssetsMetric(),
        TotalLiabilitiesMetric(),
        TotalEquityMetric(),
    )
