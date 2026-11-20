"""Scenarios produce the market frames the engine consumes."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
import math

import pandas as pd
import pytest

from brms.core.metrics.risk.interest_rate_risk.eve import Scenario
from brms.core.models.market_data import MarketDataStore
from brms.lab.scenarios import Historical, Shock, parse_scenario
from tests.support.engine import flat_yields

_START = datetime.date(2021, 6, 1)
_END = datetime.date(2021, 9, 30)


def _store(*, with_prime: bool = True) -> MarketDataStore:
    store = MarketDataStore()
    store.add_frame("yields", flat_yields(datetime.date(2021, 1, 4), datetime.date(2021, 12, 31), 0.03))
    if with_prime:
        days = pd.date_range("2021-01-01", "2021-12-31", name="date")
        store.add_frame("benchmarks", pd.DataFrame({"DPRIME": 3.25}, index=days))
    return store


def test_historical_returns_the_stored_frames() -> None:
    store = _store()
    frames = Historical().frames(store, _START, _END)
    pd.testing.assert_frame_equal(frames["yields"], store.get_frame("yields"))


def test_parallel_shock_shifts_every_tenor_from_the_start() -> None:
    store = _store()
    yields = Shock(Scenario.PARALLEL_UP).frames(store, _START, _END)["yields"]
    before = yields.loc[: pd.Timestamp(_START) - pd.Timedelta(days=1)]
    after = yields.loc[pd.Timestamp(_START) :]
    pd.testing.assert_frame_equal(before, store.get_frame("yields").loc[before.index])
    assert after.to_numpy().flatten().tolist() == pytest.approx([5.0] * after.size)  # noqa: S101


def test_ramp_reaches_half_the_shift_halfway() -> None:
    yields = Shock(Scenario.PARALLEL_UP, ramp_days=60).frames(_store(), _START, _END)["yields"]
    assert yields.loc[pd.Timestamp(_START) + pd.Timedelta(days=30), "10 Yr"] == pytest.approx(4.0)  # noqa: S101


def test_shock_moves_prime_by_the_three_month_shift() -> None:
    frames = Shock(Scenario.SHORT_UP).frames(_store(), _START, _END)
    expected = 3.25 + 300 * math.exp(-0.25 / 4) / 100
    prime = frames["benchmarks"].loc[pd.Timestamp(_START) + pd.Timedelta(days=10), "DPRIME"]
    assert prime == pytest.approx(expected)  # noqa: S101


def test_frames_cover_every_market_day_of_the_horizon() -> None:
    store = _store()
    frames = Shock(Scenario.STEEPENER).frames(store, _START, _END)
    for day in pd.bdate_range(_START, _END):
        assert day in frames["yields"].index  # noqa: S101
        assert day in frames["benchmarks"].index  # noqa: S101


def test_custom_shape_and_floor() -> None:
    yields = Shock(lambda _t: -500.0, floor=0.0).frames(_store(with_prime=False), _START, _END)["yields"]
    assert yields.loc[pd.Timestamp(_START):].min().min() == 0.0  # noqa: S101


@pytest.mark.parametrize(("text", "expected"), [
    ("historical", "historical"),
    ("parallel+200", "parallel_up"),
    ("parallel-200", "parallel_down"),
    ("steepener", "steepener"),
    ("parallel+350", "parallel+350bp"),
])
def test_parse_scenario(text: str, expected: str) -> None:
    assert parse_scenario(text).name == expected  # noqa: S101


def test_key_rate_shift_interpolates_and_is_flat_beyond_the_ends() -> None:
    import pickle

    from brms.lab.scenarios import KeyRateShift

    shape = KeyRateShift(((0.25, 100.0), (10.0, 300.0)))
    assert shape(0.25) == 100.0  # noqa: S101, PLR2004
    assert shape(5.125) == pytest.approx(200.0)  # noqa: S101
    assert shape(0.0) == 100.0  # noqa: S101, PLR2004
    assert shape(30.0) == 300.0  # noqa: S101, PLR2004
    assert pickle.loads(pickle.dumps(shape))(10.0) == 300.0  # noqa: S101, S301, PLR2004
    assert Shock(shape, label="custom").name == "custom"  # noqa: S101


def test_key_rate_shift_needs_points() -> None:
    from brms.lab.scenarios import KeyRateShift

    with pytest.raises(ValueError, match="at least one"):
        KeyRateShift(())


@pytest.mark.parametrize("text", ["parallel+150", "parallel-25"])
def test_parsed_parallel_shocks_pickle(text: str) -> None:
    import pickle

    scenario = parse_scenario(text)
    assert pickle.loads(pickle.dumps(scenario)).name == scenario.name  # noqa: S101, S301
