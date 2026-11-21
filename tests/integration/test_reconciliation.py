"""Every shipped simulation reconciles every day over its full horizon."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from brms.core.services import build_core_services
from tests.support.reconcile import account_balance, assert_books_reconcile

_DATA = Path(__file__).resolve().parents[2] / "src" / "brms" / "data"
_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_SHIPPED = ["htm_treasury", "fvtpl_bond", "mortgage", "ci_loan_prime", "diversified_bank"]


def _run_to_end(path: Path) -> None:
    services = build_core_services(simulation_zip=path)
    sim = services.simulation_service
    day = sim.start_date
    while day <= sim.end_date:
        sim.advance(day)
        assert_books_reconcile(sim, day)
        assert account_balance(sim, "Accrued Interest Receivable") >= -0.01  # noqa: S101, PLR2004
        day += datetime.timedelta(days=1)


@pytest.mark.parametrize("name", _SHIPPED)
def test_shipped_simulation_reconciles_every_day(name: str) -> None:
    _run_to_end(_DATA / f"{name}.zip")


@pytest.mark.parametrize("path", sorted(_FIXTURES.glob("*.zip")), ids=lambda p: p.name)
def test_fixture_simulations_reconcile_every_day(path: Path) -> None:
    _run_to_end(path)


@pytest.mark.parametrize("slug", ["svb_2021", "svb_2022", "signature_2021", "first_republic_2021",
                                  "jpmorgan_chase_2021"])
def test_case_study_reconciles_every_day_for_six_months(slug: str) -> None:
    services = build_core_services(simulation_zip=_DATA / f"case_{slug}.zip")
    sim = services.simulation_service
    day = sim.start_date
    end = sim.start_date + datetime.timedelta(days=182)
    while day <= end:
        sim.advance(day)
        assert_books_reconcile(sim, day)
        day += datetime.timedelta(days=1)
    assert account_balance(sim, "Operating Expense") > 0  # noqa: S101
