"""The as-if-closed balance sheet is built once per ledger state and date."""
# ruff: noqa: D103

from __future__ import annotations

import copy
import datetime
from decimal import Decimal

from brms.core.enums import MeasurementBasis
from brms.core.services import reporting_service as reporting_module
from tests.support.engine import flat_yields, make_bond, make_position, run_bank


def test_metrics_share_one_balance_sheet_per_day(monkeypatch) -> None:  # noqa: ANN001
    bond = make_bond(id="R")
    pos = make_position(
        id="pos-R", instrument_id="R", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=datetime.date(2021, 1, 4), cost=Decimal(520_000),
    )
    sim = run_bank([bond], [pos], yields=flat_yields(datetime.date(2021, 1, 4), datetime.date(2021, 3, 31)),
                   until=datetime.date(2021, 2, 1), checks=frozenset())
    calls = []
    real = copy.deepcopy

    def counting(obj, memo=None):  # noqa: ANN001, ANN202
        calls.append(type(obj).__name__)
        return real(obj, memo)

    monkeypatch.setattr(reporting_module.copy, "deepcopy", counting)
    sim.advance(datetime.date(2021, 2, 2))
    assert calls.count("Ledger") == 1  # noqa: S101
