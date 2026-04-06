"""Tests for MarketDataStore and MarketState."""

# ruff: noqa: S101, SLF001

import datetime

import pandas as pd

from brms.core.models.market_data import MarketDataStore, MarketState

_YIELD_1Y = 0.03
_YIELD_5Y = 0.04
_YIELD_1Y_D2 = 0.035
_SPX_D1 = 4800.0


def _make_store() -> MarketDataStore:
    store = MarketDataStore()
    yields_df = pd.DataFrame(
        {"1Y": [_YIELD_1Y, _YIELD_1Y_D2], "5Y": [_YIELD_5Y, 0.045]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    yields_df.index.name = "date"
    store.add_frame("treasury_yields", yields_df)

    equities_df = pd.DataFrame(
        {"SPX": [_SPX_D1, 4850.0]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    equities_df.index.name = "date"
    store.add_frame("equities", equities_df)
    return store


def test_get_state_returns_market_state() -> None:
    """get_state returns a MarketState with the correct date."""
    store = _make_store()
    state = store.get_state(datetime.date(2024, 1, 1))
    assert isinstance(state, MarketState)
    assert state.date == datetime.date(2024, 1, 1)


def test_yields_returns_series_view() -> None:
    """Yields property returns a Series with correct values."""
    store = _make_store()
    state = store.get_state(datetime.date(2024, 1, 1))
    yields = state.yields
    assert yields["1Y"] == _YIELD_1Y
    assert yields["5Y"] == _YIELD_5Y


def test_equity_prices_returns_series_view() -> None:
    """equity_prices property returns a Series with correct values."""
    store = _make_store()
    state = store.get_state(datetime.date(2024, 1, 1))
    assert state.equity_prices["SPX"] == _SPX_D1


def test_get_generic_accessor() -> None:
    """get() returns the correct row for the state's date."""
    store = _make_store()
    state = store.get_state(datetime.date(2024, 1, 2))
    row = state.get("treasury_yields")
    assert row["1Y"] == _YIELD_1Y_D2


def test_available_dates() -> None:
    """available_dates returns all dates common to every registered frame."""
    store = _make_store()
    dates = store.available_dates()
    assert datetime.date(2024, 1, 1) in dates
    assert datetime.date(2024, 1, 2) in dates


def test_market_state_is_zero_copy() -> None:
    """Two MarketState objects for the same date share the same store reference."""
    store = _make_store()
    s1 = store.get_state(datetime.date(2024, 1, 1))
    s2 = store.get_state(datetime.date(2024, 1, 1))
    assert s1._store is s2._store
