"""Valuation records accrued interest, amortised cost, clean fair value and carrying value daily."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, ValuationType
from brms.core.exceptions import ValuationError
from brms.core.models.instruments.loans import ResidentialMortgage
from brms.core.services.simulation_builder import outstanding_principal
from tests.support.engine import flat_yields, make_bond, make_position, run_bank
from tests.support.reconcile import Check

_YIELDS = flat_yields(datetime.date(2021, 1, 4), datetime.date(2022, 7, 29))
_START = datetime.date(2021, 1, 4)
_CENT = Decimal("0.01")
_V = ValuationType


def _bond_bank(basis: MeasurementBasis, until: datetime.date, clean: Decimal = Decimal(520_000)):  # noqa: ANN202
    bond = make_bond(id="R")
    pos = make_position(id="pos-R", instrument_id="R", basis=basis, acquired=_START, cost=clean)
    return bond, run_bank([bond], [pos], yields=_YIELDS, until=until, checks=frozenset({Check.BALANCE}))


def _days(start: datetime.date, end: datetime.date) -> list[datetime.date]:
    return [start + datetime.timedelta(days=i) for i in range((end - start).days + 1)]


@pytest.mark.parametrize("basis", [MeasurementBasis.AMORTIZED_COST, MeasurementBasis.FVOCI, MeasurementBasis.FVTPL])
def test_all_four_values_recorded_every_calendar_day(basis: MeasurementBasis) -> None:
    end = datetime.date(2021, 3, 31)
    _bond, sim = _bond_bank(basis, end)
    store = sim.valuation_store
    market_days = {d.date() for d in _YIELDS.index}
    for day in _days(_START, end):
        assert store.get("pos-R", day, _V.ACCRUED_INTEREST) is not None, day  # noqa: S101
        assert store.get("pos-R", day, _V.CARRYING_VALUE) is not None, day  # noqa: S101
        has_ac = store.get("pos-R", day, _V.AMORTIZED_COST) is not None
        assert has_ac == (basis != MeasurementBasis.FVTPL), day  # noqa: S101
        assert (store.get("pos-R", day, _V.FAIR_VALUE) is not None) == (day in market_days), day  # noqa: S101


def test_fair_value_is_clean() -> None:
    day = datetime.date(2021, 3, 15)
    bond, sim = _bond_bank(MeasurementBasis.FVTPL, day)
    store = sim.valuation_store
    npv = Decimal(str(bond.ql_instrument.NPV()))
    clean_plus_accrued = store.get("pos-R", day, _V.FAIR_VALUE) + store.get("pos-R", day, _V.ACCRUED_INTEREST)
    assert abs(clean_plus_accrued - npv) <= _CENT  # noqa: S101


def test_amortized_cost_position_has_fair_value() -> None:
    day = datetime.date(2021, 3, 15)
    _bond, sim = _bond_bank(MeasurementBasis.AMORTIZED_COST, day)
    assert sim.valuation_store.get("pos-R", day, _V.FAIR_VALUE) is not None  # noqa: S101


def test_fair_value_is_face_on_maturity_date() -> None:
    day = datetime.date(2022, 7, 1)
    _bond, sim = _bond_bank(MeasurementBasis.FVTPL, day)
    assert sim.valuation_store.get("pos-R", day, _V.FAIR_VALUE) == Decimal(500_000)  # noqa: S101


def test_weekend_carrying_for_fvoci_moves_with_amortized_cost() -> None:
    friday, saturday = datetime.date(2021, 2, 5), datetime.date(2021, 2, 6)
    _bond, sim = _bond_bank(MeasurementBasis.FVOCI, saturday)
    store = sim.valuation_store
    d_cv = store.get("pos-R", saturday, _V.CARRYING_VALUE) - store.get("pos-R", friday, _V.CARRYING_VALUE)
    d_ac = store.get("pos-R", saturday, _V.AMORTIZED_COST) - store.get("pos-R", friday, _V.AMORTIZED_COST)
    assert d_ac != 0  # noqa: S101
    assert abs(d_cv - d_ac) <= _CENT  # noqa: S101


def test_loan_has_no_fair_value() -> None:
    loan = ResidentialMortgage(
        face_value=300_000.0, interest_rate=0.06, issue_date=ql.Date(15, 12, 2020), maturity=ql.Period(1, ql.Years),
    )
    loan.id = "M"
    pos = make_position(
        id="pos-M", instrument_id="M", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=datetime.date(2020, 12, 15), cost=outstanding_principal(loan, datetime.date(2020, 12, 15)),
    )
    end = datetime.date(2021, 2, 26)
    sim = run_bank([loan], [pos], yields=_YIELDS, until=end, checks=frozenset({Check.BALANCE, Check.LOANS}))
    assert sim.valuation_store.series("pos-M", _V.FAIR_VALUE) == []  # noqa: S101
    assert sim.valuation_store.get("pos-M", end, _V.AMORTIZED_COST) is not None  # noqa: S101


def test_npv_failure_raises_valuation_error() -> None:
    bond = make_bond(id="R")

    def broken() -> float:
        msg = "pricing failed"
        raise RuntimeError(msg)

    bond.ql_instrument.NPV = broken
    pos = make_position(
        id="pos-R", instrument_id="R", basis=MeasurementBasis.FVTPL, acquired=_START, cost=Decimal(520_000),
    )
    with pytest.raises(ValuationError, match="pos-R"):
        run_bank([bond], [pos], yields=_YIELDS, until=datetime.date(2021, 1, 8), checks=frozenset())
