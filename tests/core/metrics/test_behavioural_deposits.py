"""Core non-maturity deposits in EVE (SRP31) and deposit betas in NII sensitivity."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import MeasurementBasis, PositionSide
from brms.core.metrics.risk.interest_rate_risk.eve import Scenario, eve_scenarios
from brms.core.metrics.risk.interest_rate_risk.maturity_gap import MaturityGapModel
from brms.core.models.instruments.deposits import Deposit
from tests.support.engine import flat_yields, make_bond, make_position, run_bank
from tests.support.reconcile import Check

_START = datetime.date(2021, 1, 4)
_DAY = datetime.date(2021, 3, 15)
_YIELDS = flat_yields(_START, datetime.date(2021, 12, 31), 0.03)


def test_core_cash_flows_amortise_over_twice_the_average_life() -> None:
    deposit = Deposit(interest_rate=0.0, core_share=0.6, core_maturity=2.0)
    flows = deposit.core_cash_flows(1_000.0, _DAY)
    assert len(flows) == 48
    assert sum(a for _d, a in flows) == pytest.approx(600.0)
    life = sum((d - _DAY).days / 365.25 * a for d, a in flows) / 600.0
    assert life == pytest.approx(2.0, abs=0.005)
    assert Deposit(interest_rate=0.0).core_cash_flows(1_000.0, _DAY) == []


@pytest.mark.parametrize(("kwargs", "message"), [
    ({"core_share": 1.2, "core_maturity": 2.0}, "core_share"),
    ({"core_share": 0.5}, "core_maturity"),
    ({"core_share": 0.5, "core_maturity": -1.0}, "core_maturity"),
])
def test_core_inputs_are_validated(kwargs: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Deposit(interest_rate=0.0, **kwargs)


def _bank(core_share: float, beta: float = 0.0):  # noqa: ANN202
    bond = make_bond(id="L", maturity=datetime.date(2030, 7, 1))
    deposit = Deposit(name="Savings", interest_rate=0.01, beta=beta, core_share=core_share,
                      core_maturity=4.0 if core_share else 0.0)
    deposit.id = "D"
    positions = [
        make_position(id="pos-L", instrument_id="L", basis=MeasurementBasis.AMORTIZED_COST, acquired=_START,
                      cost=Decimal(560_000)),
        make_position(id="pos-D", instrument_id="D", basis=MeasurementBasis.NA, acquired=_START,
                      cost=Decimal(400_000), side=PositionSide.SHORT),
    ]
    return run_bank([bond, deposit], positions, yields=_YIELDS, until=_DAY, checks=frozenset({Check.BALANCE}))


def test_core_deposits_offset_asset_losses_when_rates_rise() -> None:
    overnight = _bank(core_share=0.0)
    core = _bank(core_share=0.8)
    loss_overnight = eve_scenarios(overnight.bank, overnight.valuation_service.yield_handle, _DAY).delta(
        Scenario.PARALLEL_UP)
    result = eve_scenarios(core.bank, core.valuation_service.yield_handle, _DAY)
    assert result.position_delta(Scenario.PARALLEL_UP, "pos-D") > 0  # the deposit liability is worth less
    assert result.delta(Scenario.PARALLEL_UP) > loss_overnight
    # Duration stays a measure of the assets.
    asset_only = eve_scenarios(overnight.bank, overnight.valuation_service.yield_handle, _DAY).duration
    assert result.duration == pytest.approx(asset_only)


def test_core_deposit_value_is_its_discounted_runoff() -> None:
    import QuantLib as ql  # noqa: N813

    sim = _bank(core_share=0.8)
    handle = sim.valuation_service.yield_handle
    deposit = sim.bank.instruments.get("D")
    flows = deposit.core_cash_flows(400_000.0, _DAY)
    expected = -sum(a * handle.discount(ql.Date(d.day, d.month, d.year)) for d, a in flows)
    expected /= handle.discount(ql.Date(_DAY.day, _DAY.month, _DAY.year))
    result = eve_scenarios(sim.bank, handle, _DAY)
    assert float(result.base_position_pv["pos-D"]) == pytest.approx(expected, rel=1e-6)


def test_nii_gap_reprices_deposits_by_their_beta() -> None:
    sim = _bank(core_share=0.0, beta=0.4)
    gap = MaturityGapModel().compute(sim.bank, _DAY, sim.valuation_store)
    assert gap.total_rsl == pytest.approx(0.4 * 400_000.0, rel=1e-9)
    fixed = _bank(core_share=0.0, beta=0.0)
    assert MaturityGapModel().compute(fixed.bank, _DAY, fixed.valuation_store).total_rsl == 0


def test_eve_level_counts_other_balances_at_book(tmp_path) -> None:  # noqa: ANN001
    import json

    from brms.core.services import build_core_services
    from brms.lab.bank_file import build_bank
    from tests.lab.test_bank_file import _bank as bank_file
    from tests.lab.test_bank_file import _yields

    eves = {}
    for name, extra in (("plain", {}), ("other", {"other_assets": 300_000.0, "other_liabilities": 100_000.0})):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({**bank_file(), **extra}))
        services = build_core_services(simulation_zip=build_bank(path, {"yields": _yields()}, tmp_path / f"{name}.zip"))
        sim = services.simulation_service
        sim.advance()
        eves[name] = eve_scenarios(services.bank, sim.valuation_service.yield_handle, sim.current_date).base
    assert float(eves["other"] - eves["plain"]) == pytest.approx(200_000, abs=0.01)
