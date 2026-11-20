"""Credit RWA under the standardised approach, from per-position exposures."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, ValuationType
from brms.core.exceptions import UnsupportedPositionError
from brms.core.metrics.risk.credit_risk.exposures import ExposureClass, credit_rwa
from brms.core.models.instruments.base import CreditRating, Issuer, IssuerType
from brms.core.models.instruments.loans import CommercialMortgage, Mortgage, ResidentialMortgage
from brms.core.services.simulation_builder import outstanding_principal
from tests.support.engine import flat_yields, make_bond, make_position, run_bank

_START = datetime.date(2021, 1, 4)
_DAY = datetime.date(2021, 3, 15)
_YIELDS = flat_yields(_START, datetime.date(2021, 6, 30))


def _issuer(kind: IssuerType, rating: CreditRating = CreditRating.UNRATED) -> Issuer:
    return Issuer(name=kind.name, issuer_type=kind, credit_rating=rating)


def _mortgage(iid: str, cls: type = ResidentialMortgage, ltv: float | None = 0.7) -> object:
    loan = cls(
        face_value=300_000.0, interest_rate=0.05, issue_date=ql.Date(4, 1, 2021), maturity=ql.Period(10, ql.Years),
        issuer=_issuer(IssuerType.INDIVIDUAL), ltv=ltv,
    )
    loan.id = iid
    return loan


def _bank(*specs: tuple[str, object]):  # noqa: ANN202
    instruments, positions = [], []
    for pid, inst in specs:
        instruments.append(inst)
        is_loan = isinstance(inst, Mortgage)
        cost = outstanding_principal(inst, _START) if is_loan else Decimal(500_000)
        positions.append(make_position(
            id=pid, instrument_id=inst.id, basis=MeasurementBasis.AMORTIZED_COST, acquired=_START, cost=cost,
        ))
    return run_bank(instruments, positions, yields=_YIELDS, until=_DAY, checks=frozenset())


def _exposure(sim, pid: str) -> Decimal:  # noqa: ANN001
    store = sim.valuation_store
    return store.get(pid, _DAY, ValuationType.CARRYING_VALUE) + store.get(pid, _DAY, ValuationType.ACCRUED_INTEREST)


@pytest.mark.parametrize(
    ("issuer", "expected_class", "weight"),
    [
        (_issuer(IssuerType.SOVEREIGN, CreditRating.AAA), ExposureClass.SOVEREIGN, Decimal("0")),
        (_issuer(IssuerType.SOVEREIGN, CreditRating.BBB), ExposureClass.SOVEREIGN, Decimal("0.5")),
        (_issuer(IssuerType.BANK, CreditRating.A), ExposureClass.BANK, Decimal("0.3")),
        (_issuer(IssuerType.CORPORATE, CreditRating.A), ExposureClass.CORPORATE, Decimal("0.5")),
        (_issuer(IssuerType.CORPORATE), ExposureClass.CORPORATE, Decimal("1")),
    ],
)
def test_bond_risk_weights(issuer: Issuer, expected_class: ExposureClass, weight: Decimal) -> None:
    bond = make_bond(id="B", issuer=issuer)
    sim = _bank(("pos-B", bond))
    result = credit_rwa(sim.bank, sim.valuation_store, _DAY)
    line = next(item for item in result.items if item.key == "pos-B")
    assert line.exposure_class == expected_class  # noqa: S101
    assert line.risk_weight == weight  # noqa: S101
    assert abs(line.exposure - _exposure(sim, "pos-B")) <= Decimal("0.01")  # noqa: S101
    assert abs(line.rwa - line.exposure * weight) <= Decimal("0.01")  # noqa: S101


@pytest.mark.parametrize(("cls", "ltv", "weight"), [
    (ResidentialMortgage, 0.45, Decimal("0.2")),
    (ResidentialMortgage, 0.75, Decimal("0.3")),
    (ResidentialMortgage, 0.95, Decimal("0.5")),
    (CommercialMortgage, 0.55, Decimal("0.6")),
])
def test_mortgage_risk_weight_by_ltv(cls: type, ltv: float, weight: Decimal) -> None:
    sim = _bank(("pos-M", _mortgage("M", cls, ltv)))
    line = next(item for item in credit_rwa(sim.bank, sim.valuation_store, _DAY).items if item.key == "pos-M")
    assert line.risk_weight == weight  # noqa: S101


def test_cash_carries_no_risk_weight_and_total_sums_lines() -> None:
    sim = _bank(("pos-B", make_bond(id="B", issuer=_issuer(IssuerType.CORPORATE))))
    result = credit_rwa(sim.bank, sim.valuation_store, _DAY)
    cash = next(item for item in result.items if item.key == "Cash and Cash Equivalents")
    assert cash.risk_weight == 0  # noqa: S101
    assert cash.exposure > 0  # noqa: S101
    assert result.total == sum((item.rwa for item in result.items), Decimal(0))  # noqa: S101


def test_bond_without_issuer_is_rejected() -> None:
    """Credit RWA is a daily metric, so an unclassifiable exposure stops the run on its first market day."""
    with pytest.raises(UnsupportedPositionError, match="pos-B"):
        _bank(("pos-B", make_bond(id="B", issuer=None)))


def test_mortgage_without_ltv_is_rejected() -> None:
    with pytest.raises(UnsupportedPositionError, match="pos-M"):
        _bank(("pos-M", _mortgage("M", ltv=None)))


def test_unrated_bank_is_rejected() -> None:
    with pytest.raises(UnsupportedPositionError, match="pos-B"):
        _bank(("pos-B", make_bond(id="B", issuer=_issuer(IssuerType.BANK))))
