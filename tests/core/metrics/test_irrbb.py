"""EVE under the Basel shocks, effective duration and 12-month NII sensitivity."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
import math
from decimal import Decimal
from pathlib import Path

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, MetricName, ValuationType
from brms.core.metrics.risk.interest_rate_risk.eve import Scenario, eve_scenarios, shock_bp
from brms.core.metrics.risk.interest_rate_risk.maturity_gap import MaturityGapModel
from brms.core.services import build_core_services
from brms.core.utils import pydate_to_qldate
from tests.support.engine import flat_yields, make_bond, make_position, run_bank

_START = datetime.date(2021, 1, 4)
_DAY = datetime.date(2021, 3, 15)
_YIELDS = flat_yields(_START, datetime.date(2021, 12, 31), 0.03)
_DATA = Path(__file__).resolve().parents[3] / "src" / "brms" / "data"


def _handle(sim):  # noqa: ANN001, ANN202
    return sim.valuation_service._yield_handle  # noqa: SLF001


@pytest.mark.parametrize(("scenario", "t", "expected"), [
    (Scenario.PARALLEL_UP, 5.0, 200.0),
    (Scenario.PARALLEL_DOWN, 5.0, -200.0),
    (Scenario.SHORT_UP, 0.0, 300.0),
    (Scenario.SHORT_UP, 4.0, 300.0 * math.exp(-1)),
    (Scenario.SHORT_DOWN, 4.0, -300.0 * math.exp(-1)),
    (Scenario.STEEPENER, 0.0, -0.65 * 300.0),
    (Scenario.STEEPENER, 4.0, -0.65 * 300.0 * math.exp(-1) + 0.9 * 150.0 * (1 - math.exp(-1))),
    (Scenario.FLATTENER, 4.0, 0.8 * 300.0 * math.exp(-1) - 0.6 * 150.0 * (1 - math.exp(-1))),
    (Scenario.STEEPENER, 100.0, 0.9 * 150.0),
])
def test_shock_shapes(scenario: Scenario, t: float, expected: float) -> None:
    assert shock_bp(scenario, t) == pytest.approx(expected, abs=1e-6)  # noqa: S101


def _bond_bank(until: datetime.date = _DAY):  # noqa: ANN202
    bond = make_bond(id="L", maturity=datetime.date(2030, 7, 1))
    pos = make_position(id="pos-L", instrument_id="L", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                        cost=Decimal(560_000))
    return bond, run_bank([bond], [pos], yields=_YIELDS, until=until, checks=frozenset())


def test_parallel_up_matches_independent_revaluation() -> None:
    bond, sim = _bond_bank()
    handle = _handle(sim)
    base = handle.currentLink()
    qd = pydate_to_qldate(_DAY)
    flows = bond.ql_instrument.cashflows()
    shifted = ql.ZeroSpreadedTermStructure(ql.YieldTermStructureHandle(base), ql.QuoteHandle(ql.SimpleQuote(0.02)))
    expected = ql.CashFlows.npv(flows, ql.YieldTermStructureHandle(shifted), False, qd, qd)  # noqa: FBT003
    expected -= ql.CashFlows.npv(flows, ql.YieldTermStructureHandle(base), False, qd, qd)  # noqa: FBT003
    result = eve_scenarios(sim.bank, handle, _DAY)
    assert float(result.delta(Scenario.PARALLEL_UP)) == pytest.approx(expected, rel=1e-4)  # noqa: S101
    assert result.delta(Scenario.PARALLEL_UP) < 0 < result.delta(Scenario.PARALLEL_DOWN)  # noqa: S101


def test_handle_is_restored() -> None:
    _bond, sim = _bond_bank()
    handle = _handle(sim)
    qd = pydate_to_qldate(_DAY + datetime.timedelta(days=365))
    before = handle.discount(qd)
    eve_scenarios(sim.bank, handle, _DAY)
    assert handle.discount(qd) == before  # noqa: S101


def test_effective_duration_close_to_modified_duration() -> None:
    bond, sim = _bond_bank()
    result = eve_scenarios(sim.bank, _handle(sim), _DAY)
    ql_bond = bond.ql_instrument
    qd = pydate_to_qldate(_DAY)
    price = ql.BondFunctions.dirtyPrice(ql_bond, _handle(sim).currentLink(), qd)
    yld = ql.BondFunctions.bondYield(ql_bond, ql.BondPrice(price, ql.BondPrice.Dirty), ql.Actual365Fixed(),
                                     ql.Continuous, ql.NoFrequency, qd)
    modified = ql.BondFunctions.duration(ql_bond, yld, ql.Actual365Fixed(), ql.Continuous, ql.NoFrequency,
                                         ql.Duration.Modified, qd)
    assert result.duration == pytest.approx(modified, rel=0.01)  # noqa: S101


def test_floating_loan_is_far_less_sensitive_than_fixed() -> None:
    services = build_core_services(simulation_zip=_DATA / "ci_loan_prime.zip")
    sim = services.simulation_service
    for _ in range(10):
        sim.advance()
    result = eve_scenarios(sim.bank, sim.valuation_service._yield_handle, sim.current_date)  # noqa: SLF001
    loan_pv = result.base_position_pv["pos-ci-loan"]
    # A 5-year fixed-rate loan loses about 9% of its value under +200bp. The floater reprices monthly;
    # only its fixed credit spread (an annuity) keeps some sensitivity.
    assert abs(result.position_delta(Scenario.PARALLEL_UP, "pos-ci-loan")) < Decimal("0.01") * loan_pv  # noqa: S101


def test_irrbb_metrics_recorded() -> None:
    _bond, sim = _bond_bank()
    for name in (MetricName.EVE, MetricName.DELTA_EVE_WORST, MetricName.DELTA_EVE_WORST_TO_TIER1,
                 MetricName.ASSET_DURATION, MetricName.NII_SENSITIVITY_UP, MetricName.NII_SENSITIVITY_DOWN):
        assert sim.metric_store.get(name, _DAY) is not None, name  # noqa: S101


def test_nii_sensitivity_weights_by_time_in_year() -> None:
    near = make_bond(id="N", issue=datetime.date(2020, 3, 15), maturity=datetime.date(2022, 1, 15))
    far = make_bond(id="F", issue=datetime.date(2020, 3, 15), maturity=datetime.date(2025, 3, 15))
    positions = [
        make_position(id="pos-N", instrument_id="N", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                      cost=Decimal(500_000)),
        make_position(id="pos-F", instrument_id="F", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                      cost=Decimal(500_000)),
    ]
    sim = run_bank([near, far], positions, yields=_YIELDS, until=_DAY, checks=frozenset())
    result = MaturityGapModel().compute(sim.bank, _DAY, sim.valuation_store)
    index = next(i for i, b in enumerate(result.buckets) if b.label.startswith("9M"))
    near_cv = float(sim.valuation_store.get("pos-N", _DAY, ValuationType.CARRYING_VALUE))
    assert result.delta_nii_up[index] == pytest.approx(near_cv * 0.02 * (1 - 0.875))  # noqa: S101
    assert all(v == 0 for b, v in zip(result.buckets, result.delta_nii_up, strict=True) if b.midpoint >= 1)  # noqa: S101
