"""Regression tests for the capital-measures review findings."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import BookType, MeasurementBasis, MetricName
from brms.core.exceptions import UnsupportedPositionError
from brms.core.metrics.risk.credit_risk.exposures import classify
from brms.core.metrics.risk.credit_risk.standardised_approach import RiskWeightTableForCorporateExposures
from brms.core.metrics.risk.interest_rate_risk.eve import eve_scenarios
from brms.core.models.instruments.base import CreditRating, Issuer, IssuerType
from brms.core.models.regulatory import RegulatoryConfig
from brms.core.services import build_core_services
from tests.support.engine import flat_yields, make_bond, make_position, run_bank

_DATA = Path(__file__).resolve().parents[3] / "src" / "brms" / "data"
_START = datetime.date(2021, 1, 4)
_DAY = datetime.date(2021, 3, 15)


def _corp(rating: CreditRating) -> Issuer:
    return Issuer(name="Acme", issuer_type=IssuerType.CORPORATE, credit_rating=rating)


@pytest.mark.parametrize(("rating", "weight"), [(CreditRating.BB_MINUS, 1.0), (CreditRating.B_PLUS, 1.5),
                                                 (CreditRating.B_MINUS, 1.5)])
def test_corporate_below_bb_minus_is_150_percent(rating: CreditRating, weight: float) -> None:
    rated = SimpleNamespace(issuer=SimpleNamespace(credit_rating=rating), credit_rating=rating)
    assert RiskWeightTableForCorporateExposures.get_risk_weight(rated) == weight  # noqa: S101


def test_issue_rating_takes_precedence_over_issuer_rating() -> None:
    bond = make_bond(id="B", issuer=_corp(CreditRating.A))
    bond.credit_rating = CreditRating.BBB
    pos = make_position(id="pos-B", instrument_id="B", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                        cost=Decimal(500_000))
    assert classify(bond, pos)[1] == Decimal("0.75")  # noqa: S101


@pytest.mark.parametrize("ltv", [80.0, 0.0, -0.1])
def test_implausible_ltv_is_rejected(ltv: float) -> None:
    from brms.core.models.instruments.loans import ResidentialMortgage

    loan = ResidentialMortgage(face_value=1e5, interest_rate=0.05, issue_date=ql.Date(4, 1, 2021),
                               maturity=ql.Period(10, ql.Years), ltv=ltv)
    pos = make_position(id="pos-M", instrument_id="M", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                        cost=Decimal(100_000))
    with pytest.raises(UnsupportedPositionError, match="ltv"):
        classify(loan, pos)


def test_unclassifiable_position_is_rejected_before_any_day_is_processed() -> None:
    bond = make_bond(id="B", issuer=Issuer(name="X", issuer_type=IssuerType.BANK))
    pos = make_position(id="pos-B", instrument_id="B", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                        cost=Decimal(500_000))
    yields = flat_yields(datetime.date(2021, 2, 1), datetime.date(2021, 3, 31))  # no market data in January
    days: list[datetime.date] = []
    with pytest.raises(UnsupportedPositionError, match="pos-B"):
        run_bank([bond], [pos], yields=yields, until=_DAY, checks=frozenset(),
                 each_day=lambda _sim, day: days.append(day))
    assert days == []  # noqa: S101


def test_capital_reflects_a_changed_regulatory_config_on_the_same_day() -> None:
    bond = make_bond(id="B", issuer=_corp(CreditRating.A))
    pos = make_position(id="pos-B", instrument_id="B", basis=MeasurementBasis.FVOCI, acquired=_START,
                        cost=Decimal(520_000))
    sim = run_bank([bond], [pos], yields=flat_yields(_START, datetime.date(2021, 3, 31)), until=_DAY,
                   checks=frozenset())
    before = sim.metric_store.get(MetricName.TIER1_CAPITAL, _DAY)
    sim.bank.regulatory = RegulatoryConfig(additional_tier1=Decimal(100_000))
    sim.metrics_service.compute(sim.bank, sim.market_data.get_state(_DAY), _DAY, sim.metric_store, sim.valuation_store)
    assert sim.metric_store.get(MetricName.TIER1_CAPITAL, _DAY) == before + 100_000  # noqa: S101


def test_prime_forecasts_keep_the_prime_treasury_basis() -> None:
    services = build_core_services(simulation_zip=_DATA / "ci_loan_prime.zip")
    sim = services.simulation_service
    for _ in range(3):
        sim.advance()
    index = sim.valuation_service._context._benchmark_service.prime_index  # noqa: SLF001
    today_fixing = index.fixing(ql.Date(3, 1, 2022))
    forecast = index.fixing(ql.Date(1, 3, 2022))
    assert abs(forecast - today_fixing) < 0.005  # noqa: S101, PLR2004


def test_floater_reprices_at_its_next_scheduled_reset() -> None:
    services = build_core_services(simulation_zip=_DATA / "ci_loan_prime.zip")
    services.simulation_service.advance()  # link a curve so every coupon can be forecast
    loan = services.bank.instruments.get("ci-loan-001")
    resets = sorted(qd for qd in (d for d, _a in loan.payment_schedule()[0]))
    as_of = datetime.date(2022, 1, 20)
    assert loan.repricing_date(as_of) == next(d for d in resets if d > as_of)  # noqa: S101


def test_trading_book_is_outside_eve() -> None:
    banking = make_bond(id="BB", maturity=datetime.date(2030, 7, 1))
    trading = make_bond(id="TB", maturity=datetime.date(2030, 7, 1))
    positions = [
        make_position(id="pos-BB", instrument_id="BB", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                      cost=Decimal(560_000)),
        make_position(id="pos-TB", instrument_id="TB", basis=MeasurementBasis.FVTPL, acquired=_START,
                      cost=Decimal(560_000), book=BookType.TRADING),
    ]
    sim = run_bank([banking, trading], positions, yields=flat_yields(_START, datetime.date(2021, 3, 31)),
                   until=_DAY, checks=frozenset())
    result = eve_scenarios(sim.bank, sim.valuation_service._yield_handle, _DAY)  # noqa: SLF001
    assert set(result.base_position_pv) == {"pos-BB"}  # noqa: S101


def test_profitability_needs_a_month_of_history() -> None:
    bond = make_bond(id="B")
    pos = make_position(id="pos-B", instrument_id="B", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                        cost=Decimal(500_000))
    sim = run_bank([bond], [pos], yields=flat_yields(_START, datetime.date(2021, 3, 31)),
                   until=datetime.date(2021, 2, 10), checks=frozenset())
    assert sim.metric_store.get(MetricName.ROA, datetime.date(2021, 1, 15)) is None  # noqa: S101
    assert sim.metric_store.get(MetricName.ROA, datetime.date(2021, 2, 10)) is not None  # noqa: S101
