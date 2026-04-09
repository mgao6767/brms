"""Tests for YieldCurveService.compute_plot_data."""
# ruff: noqa: S101

import datetime

from brms.core.services.yield_curve_service import YieldCurvePlotData, YieldCurveService


def test_compute_plot_data_returns_dataclass() -> None:
    ref_date = datetime.date(2024, 1, 2)
    labels = ["1 Mo", "3 Mo", "6 Mo", "1 Yr", "2 Yr", "5 Yr", "10 Yr", "30 Yr"]
    rates = [5.53, 5.46, 5.36, 4.79, 4.39, 3.98, 3.97, 4.12]
    result = YieldCurveService.compute_plot_data(ref_date, labels, rates)
    assert isinstance(result, YieldCurvePlotData)
    assert len(result.par_dates) == len(labels)
    assert len(result.par_rates) == len(rates)
    assert len(result.zero_dates) > 0
    assert len(result.zero_rates) > 0
    assert "January" in result.title


def test_compute_plot_data_filters_nan() -> None:
    ref_date = datetime.date(2024, 1, 2)
    labels = ["1 Mo", "3 Mo"]
    rates = [5.53, float("nan")]
    result = YieldCurveService.compute_plot_data(ref_date, labels, rates)
    assert len(result.par_dates) == 1
    assert len(result.par_rates) == 1
