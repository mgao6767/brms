"""Regression tests for the whole-branch review's Important findings."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
import io
import zipfile
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from brms.core.enums import MeasurementBasis
from brms.core.exceptions import SimulationDataError, UnsupportedPositionError
from brms.core.services import build_core_services
from tests.support.engine import flat_yields, make_bond, make_position, run_bank
from tests.support.reconcile import assert_books_reconcile

_DATA = Path(__file__).resolve().parents[2] / "src" / "brms" / "data"


def _rewrite_zip(src: Path, dst: Path, *, drop: str | None = None, edit: dict[str, bytes] | None = None) -> Path:
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in zin.namelist():
            if name == drop:
                continue
            zout.writestr(name, (edit or {}).get(name, zin.read(name)))
    return dst


def test_zip_without_balances_is_rejected(tmp_path: Path) -> None:
    broken = _rewrite_zip(_DATA / "mortgage.zip", tmp_path / "mortgage.zip", drop="balances.json")
    with pytest.raises(SimulationDataError, match=r"balances\.json"):
        build_core_services(simulation_zip=broken)


@pytest.mark.parametrize("basis", [MeasurementBasis.AMORTIZED_COST, MeasurementBasis.FVOCI, MeasurementBasis.FVTPL])
def test_bond_acquired_on_redemption_date_is_rejected(basis: MeasurementBasis) -> None:
    bond = make_bond(id="R")
    pos = make_position(
        id="pos-R", instrument_id="R", basis=basis, acquired=datetime.date(2022, 7, 1), cost=Decimal(500_900),
    )
    yields = flat_yields(datetime.date(2021, 1, 4), datetime.date(2022, 7, 15))
    with pytest.raises(UnsupportedPositionError, match="pos-R"):
        run_bank([bond], [pos], yields=yields, until=datetime.date(2022, 7, 15))


def test_floating_loan_survives_a_reset_date_without_yields(tmp_path: Path) -> None:
    src = _DATA / "ci_loan_prime.zip"
    with zipfile.ZipFile(src) as zf:
        yields = pd.read_csv(io.BytesIO(zf.read("yields.csv")), index_col="date", parse_dates=True)
    yields = yields.drop(pd.Timestamp("2022-04-01"))
    csv = yields.to_csv(index_label="date", date_format="%Y-%m-%d").encode()
    sparse = _rewrite_zip(src, tmp_path / "ci.zip", edit={"yields.csv": csv})
    sim = build_core_services(simulation_zip=sparse).simulation_service
    day = sim.start_date
    while day <= datetime.date(2022, 4, 10):
        sim.advance(day)
        assert_books_reconcile(sim, day)
        day += datetime.timedelta(days=1)
