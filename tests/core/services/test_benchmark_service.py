"""Tests for BenchmarkService — MarketDataStore → QL IndexManager sync."""

from __future__ import annotations

import datetime

import pandas as pd
import QuantLib as ql  # noqa: N813
import pytest

from brms.core.models.market_data import MarketDataStore
from brms.core.services.benchmark_service import BenchmarkService


@pytest.fixture
def benchmark_service():
    svc = BenchmarkService()
    yield svc
    svc.reset()


@pytest.fixture
def market_data_with_prime():
    store = MarketDataStore()
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    df = pd.DataFrame({"DPRIME": [8.50, 8.50, 8.75, 8.75]}, index=dates)
    df.index.name = "date"
    store.add_frame("benchmarks", df)
    return store


class TestBenchmarkServiceSync:
    def test_sync_populates_index(self, benchmark_service, market_data_with_prime) -> None:
        benchmark_service.sync_up_to(datetime.date(2024, 1, 5), market_data_with_prime)
        idx = benchmark_service.prime_index
        ql.Settings.instance().evaluationDate = ql.Date(6, 1, 2024)
        assert idx.fixing(ql.Date(2, 1, 2024)) == pytest.approx(0.085)

    def test_sync_converts_percent_to_decimal(self, benchmark_service, market_data_with_prime) -> None:
        benchmark_service.sync_up_to(datetime.date(2024, 1, 5), market_data_with_prime)
        idx = benchmark_service.prime_index
        ql.Settings.instance().evaluationDate = ql.Date(6, 1, 2024)
        assert idx.fixing(ql.Date(4, 1, 2024)) == pytest.approx(0.0875)

    def test_sync_is_incremental(self, benchmark_service, market_data_with_prime) -> None:
        benchmark_service.sync_up_to(datetime.date(2024, 1, 3), market_data_with_prime)
        benchmark_service.sync_up_to(datetime.date(2024, 1, 5), market_data_with_prime)
        idx = benchmark_service.prime_index
        ql.Settings.instance().evaluationDate = ql.Date(6, 1, 2024)
        assert idx.fixing(ql.Date(5, 1, 2024)) == pytest.approx(0.0875)

    def test_sync_missing_benchmarks_frame_is_noop(self, benchmark_service) -> None:
        empty_store = MarketDataStore()
        benchmark_service.sync_up_to(datetime.date(2024, 1, 5), empty_store)

    def test_sync_missing_dprime_column_is_noop(self, benchmark_service) -> None:
        store = MarketDataStore()
        dates = pd.to_datetime(["2024-01-02"])
        store.add_frame("benchmarks", pd.DataFrame({"OTHER": [1.0]}, index=dates))
        benchmark_service.sync_up_to(datetime.date(2024, 1, 5), store)

    def test_reset_clears_history(self, benchmark_service, market_data_with_prime) -> None:
        benchmark_service.sync_up_to(datetime.date(2024, 1, 5), market_data_with_prime)
        benchmark_service.reset()
        assert benchmark_service._last_synced_date is None
