"""SimulationService guards: no reprocessing a day, no half-processed days."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import MeasurementBasis
from brms.core.exceptions import ValuationError
from tests.support.engine import flat_yields, make_bond, make_position, run_bank

_START = datetime.date(2021, 1, 4)
_UNTIL = datetime.date(2021, 2, 1)


def _engine():  # noqa: ANN202
    bond = make_bond(id="R")
    pos = make_position(
        id="pos-R", instrument_id="R", basis=MeasurementBasis.FVTPL, acquired=_START, cost=Decimal(520_000),
    )
    return run_bank([bond], [pos], yields=flat_yields(_START, datetime.date(2021, 6, 30)), until=_UNTIL)


@pytest.mark.parametrize("day", [_UNTIL, _UNTIL - datetime.timedelta(days=3)])
def test_advance_to_a_processed_day_raises(day: datetime.date) -> None:
    sim = _engine()
    with pytest.raises(ValueError, match="already processed"):
        sim.advance(day)


def test_failed_day_leaves_the_date_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    sim = _engine()

    def broken(*_args: object, **_kwargs: object) -> None:
        msg = "boom"
        raise ValuationError(msg)

    monkeypatch.setattr(sim.valuation_service, "value_all", broken)
    with pytest.raises(ValuationError):
        sim.advance()
    assert sim.current_date == _UNTIL  # noqa: S101
