"""Per-position credit spreads: calibration, fair value, persistence and EVE."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, TransactionType, ValuationType
from brms.core.metrics.risk.interest_rate_risk.eve import eve_scenarios
from brms.core.models.instruments.base import CreditRating, Issuer, IssuerType
from brms.core.models.instruments.loans import ResidentialMortgage
from brms.core.services import build_core_services
from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder, outstanding_principal
from brms.core.services.snapshot_writer import save_snapshot
from brms.core.services.spreads import calibrate_spread
from brms.core.utils import pydate_to_qldate
from tests.support.engine import flat_yields, funding, make_bond, make_position

if TYPE_CHECKING:
    from pathlib import Path

_START = datetime.date(2021, 1, 4)
_YIELDS = flat_yields(_START, datetime.date(2021, 12, 31), 0.03)
_CORP = Issuer(name="Acme", issuer_type=IssuerType.CORPORATE, credit_rating=CreditRating.BBB)


def _config(positions, instruments, *, calibrate: bool, start=datetime.date(2021, 3, 1)) -> BuildConfig:  # noqa: ANN001
    eq_i, eq_p = funding()
    return BuildConfig(
        name="spreads", start_date=start, instruments=[*eq_i, *instruments], positions=[*eq_p, *positions],
        market_frames={"yields": _YIELDS}, calibrate_spreads=calibrate,
    )


def _corporate(basis: MeasurementBasis = MeasurementBasis.FVTPL):  # noqa: ANN202
    bond = make_bond(id="C", issuer=_CORP, maturity=datetime.date(2028, 7, 1))
    pos = make_position(id="pos-C", instrument_id="C", basis=basis, acquired=_START, cost=Decimal(480_000))
    return bond, pos


def test_calibrated_spread_reprices_to_the_target() -> None:
    bond, _pos = _corporate()
    curve = ql.FlatForward(pydate_to_qldate(_START), 0.03, ql.Actual365Fixed())
    handle = ql.YieldTermStructureHandle(curve)
    spread = calibrate_spread(bond.ql_instrument.cashflows(), handle, _START, Decimal(480_000))
    assert spread > 0  # noqa: S101
    shifted = ql.ZeroSpreadedTermStructure(handle, ql.QuoteHandle(ql.SimpleQuote(float(spread))))
    qd = pydate_to_qldate(_START)
    pv = ql.CashFlows.npv(bond.ql_instrument.cashflows(), ql.YieldTermStructureHandle(shifted), False, qd, qd)  # noqa: FBT003
    assert pv == pytest.approx(480_000, rel=1e-8)  # noqa: S101


@pytest.mark.parametrize(("calibrate", "small"), [(True, True), (False, False)])
def test_calibration_removes_the_day_one_jump(calibrate: bool, small: bool) -> None:  # noqa: FBT001
    bond, pos = _corporate()
    sim = SimulationBuilder().replay(_config([pos], [bond], calibrate=calibrate), until=datetime.date(2021, 1, 6))
    marks = [t.amount for t in sim.transaction_log.by_position("pos-C") if t.type == TransactionType.MARK_TO_MARKET]
    assert (abs(marks[0]) < 500) is small, marks  # noqa: S101, PLR2004


def test_fair_value_uses_the_spread() -> None:
    bond, pos = _corporate()
    day = datetime.date(2021, 2, 10)
    sim = SimulationBuilder().replay(_config([pos], [bond], calibrate=True), until=day)
    spread = sim.bank.positions.get("pos-C").spread
    handle = sim.valuation_service._yield_handle  # noqa: SLF001
    shifted = ql.ZeroSpreadedTermStructure(handle, ql.QuoteHandle(ql.SimpleQuote(float(spread))))
    qd = pydate_to_qldate(day)
    dirty = ql.CashFlows.npv(bond.ql_instrument.cashflows(), ql.YieldTermStructureHandle(shifted), False, qd, qd)  # noqa: FBT003
    store = sim.valuation_store
    clean = store.get("pos-C", day, ValuationType.FAIR_VALUE)
    assert float(clean + store.get("pos-C", day, ValuationType.ACCRUED_INTEREST)) == pytest.approx(dirty)  # noqa: S101


def test_loan_with_a_spread_has_a_fair_value() -> None:
    loan = ResidentialMortgage(face_value=300_000.0, interest_rate=0.06, issue_date=ql.Date(4, 1, 2021),
                               maturity=ql.Period(10, ql.Years), ltv=0.7)
    loan.id = "M"
    pos = make_position(id="pos-M", instrument_id="M", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                        cost=outstanding_principal(loan, _START))
    day = datetime.date(2021, 2, 10)
    sim = SimulationBuilder().replay(_config([pos], [loan], calibrate=True), until=day)
    assert sim.valuation_store.get("pos-M", day, ValuationType.FAIR_VALUE) is not None  # noqa: S101


def test_spread_survives_save_and_load(tmp_path: Path) -> None:
    bond, pos = _corporate()
    snapshot = SimulationBuilder().build(_config([pos], [bond], calibrate=True))
    path = tmp_path / "s.zip"
    specs = [
        {"id": "equity", "type": "common_equity", "name": "Test equity"},
        {"id": "C", "type": "treasury_note", "face_value": 500_000.0, "coupon_rate": 0.05,
         "issue_date": "2020-07-01", "maturity_date": "2028-07-01",
         "issuer": {"name": "Acme", "issuer_type": "CORPORATE", "credit_rating": "BBB"}},
    ]
    save_snapshot(snapshot, specs, path)
    loaded = build_core_services(simulation_zip=path).bank.positions.get("pos-C")
    assert loaded.spread == snapshot.positions[-1].spread  # noqa: S101
    assert loaded.spread is not None  # noqa: S101


def test_eve_discounts_with_the_spread() -> None:
    bond, pos = _corporate(MeasurementBasis.AMORTIZED_COST)
    day = datetime.date(2021, 2, 10)
    sim = SimulationBuilder().replay(_config([pos], [bond], calibrate=True), until=day)
    result = eve_scenarios(sim.bank, sim.valuation_service._yield_handle, day)  # noqa: SLF001
    store = sim.valuation_store
    dirty_fv = store.get("pos-C", day, ValuationType.FAIR_VALUE)
    dirty_fv += store.get("pos-C", day, ValuationType.ACCRUED_INTEREST)
    assert float(result.base_position_pv["pos-C"]) == pytest.approx(float(dirty_fv), rel=1e-9)  # noqa: S101
