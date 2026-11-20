"""Simulation results as pandas DataFrames."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import pandas as pd

from brms.core.enums import MeasurementBasis, MetricName, ValuationType
from brms.core.results import metrics_frame, valuations_frame
from tests.support.engine import flat_yields, make_bond, make_position, run_bank


def _sim():  # noqa: ANN202
    bond = make_bond(id="R")
    pos = make_position(id="pos-R", instrument_id="R", basis=MeasurementBasis.FVTPL,
                        acquired=datetime.date(2021, 1, 4), cost=Decimal(520_000))
    return run_bank([bond], [pos], yields=flat_yields(datetime.date(2021, 1, 4), datetime.date(2021, 3, 31)),
                    until=datetime.date(2021, 1, 31))


def test_metrics_frame() -> None:
    sim = _sim()
    frame = metrics_frame(sim.metric_store)
    assert frame.index.name == "date"  # noqa: S101
    assert "CET1_RATIO" in frame.columns  # noqa: S101
    day = datetime.date(2021, 1, 29)
    assert frame.loc[pd.Timestamp(day), "TOTAL_ASSETS"] == float(sim.metric_store.get(MetricName.TOTAL_ASSETS, day))  # noqa: S101
    assert frame.dtypes.map(lambda t: t.kind).isin(["f"]).all()  # noqa: S101


def test_valuations_frame() -> None:
    sim = _sim()
    frame = valuations_frame(sim.valuation_store, ValuationType.CARRYING_VALUE)
    assert list(frame.columns) == ["pos-R"]  # noqa: S101
    day = datetime.date(2021, 1, 10)
    expected = float(sim.valuation_store.get("pos-R", day, ValuationType.CARRYING_VALUE))
    assert frame.loc[pd.Timestamp(day), "pos-R"] == expected  # noqa: S101
