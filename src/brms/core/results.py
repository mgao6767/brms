"""Simulation results as pandas DataFrames, for notebooks and scripts."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from brms.core.enums import MetricName

if TYPE_CHECKING:
    from brms.core.enums import ValuationType
    from brms.core.stores.metric_store import MetricStore
    from brms.core.stores.valuation_store import ValuationStore


def _frame(columns: dict[str, dict]) -> pd.DataFrame:
    frame = pd.DataFrame(columns, dtype="float64").sort_index()
    frame.index.name = "date"
    return frame


def metrics_frame(metric_store: MetricStore) -> pd.DataFrame:
    """One row per metric date, one float column per metric (``MetricName`` names); undefined is NaN."""
    columns: dict[str, dict] = {}
    for name in MetricName:
        series = metric_store.series(name)
        if series:
            columns[name.name] = {d: (float("nan") if v is None else float(v)) for d, v in series}
    return _frame(columns)


def valuations_frame(valuation_store: ValuationStore, valuation_type: ValuationType) -> pd.DataFrame:
    """One row per date, one float column per position, for one valuation type."""
    columns: dict[str, dict] = {}
    for position_id in valuation_store.position_ids():
        series = valuation_store.series(position_id, valuation_type)
        if series:
            columns[position_id] = {d: float(v) for d, v in series}
    return _frame(columns)
