"""Tests for benchmark enums and PrimeIndex."""

from __future__ import annotations

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentType
from brms.core.models.benchmarks import BenchmarkFamily, PrimeIndex, PrincipalRepaymentMode


class TestBenchmarkEnums:
    def test_benchmark_family_prime_value(self) -> None:
        assert BenchmarkFamily.PRIME.value == "prime"

    def test_benchmark_family_roundtrip(self) -> None:
        assert BenchmarkFamily("prime") is BenchmarkFamily.PRIME

    def test_principal_repayment_mode_values(self) -> None:
        assert PrincipalRepaymentMode.BULLET.value == "bullet"
        assert PrincipalRepaymentMode.SINKING.value == "sinking"

    def test_variable_rate_loan_instrument_type_exists(self) -> None:
        assert hasattr(InstrumentType, "VARIABLE_RATE_LOAN")


class TestPrimeIndex:
    def test_prime_index_name(self) -> None:
        idx = PrimeIndex()
        assert idx.familyName() == "USDPrime"

    def test_prime_index_fixing_days(self) -> None:
        idx = PrimeIndex()
        assert idx.fixingDays() == 0

    def test_prime_index_day_counter(self) -> None:
        idx = PrimeIndex()
        assert idx.dayCounter().name() == "Actual/365 (Fixed)"

    def test_prime_index_default_tenor(self) -> None:
        idx = PrimeIndex()
        assert idx.tenor() == ql.Period(1, ql.Months)

    def test_prime_index_custom_tenor(self) -> None:
        idx = PrimeIndex(tenor=ql.Period(3, ql.Months))
        assert idx.tenor() == ql.Period(3, ql.Months)

    def test_prime_index_add_and_read_fixing(self) -> None:
        idx = PrimeIndex()
        fixing_date = ql.Date(2, 1, 2024)
        idx.addFixing(fixing_date, 0.085)
        ql.Settings.instance().evaluationDate = ql.Date(3, 1, 2024)
        assert idx.fixing(fixing_date) == 0.085
        ql.IndexManager.instance().clearHistory(idx.name())
