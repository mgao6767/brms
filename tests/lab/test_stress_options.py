"""Liquidity stress options of a run: deposit run-off, a one-off withdrawal, selling the AFS book."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING

import pytest

from brms.lab import Historical, run
from brms.lab.runner import DepositStress
from tests.lab.test_bank_file import _bank as bank_file
from tests.lab.test_bank_file import _write, _yields

if TYPE_CHECKING:
    from pathlib import Path

_START = datetime.date(2021, 7, 1)


@pytest.fixture(scope="module")
def simulation(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from brms.lab.bank_file import build_bank

    folder = tmp_path_factory.mktemp("stress")
    bank = bank_file()
    bank["deposits"].append({"id": "fhlb", "name": "FHLB advances", "balance": 100_000.0, "interest_rate": 0.002,
                             "beta": 1.0, "borrowing": True})
    return build_bank(_write(folder, bank), {"yields": _yields()}, folder / "bank.zip")


def _line(result, day: datetime.date, account: str) -> float:  # noqa: ANN001
    s = result.statements
    return float(s[(s["date"] == day) & (s["account"] == account)]["balance"].iloc[0])


def test_withdrawal_takes_a_share_of_deposits_but_not_borrowings(simulation: Path) -> None:
    day = datetime.date(2021, 8, 2)
    result = run(simulation, Historical(), end=datetime.date(2021, 8, 31),
                 deposit_stress=DepositStress(withdrawal=0.4, withdrawal_date=day))
    before = _line(result, day - datetime.timedelta(days=3), "Deposits and Other Public Borrowings")
    after = _line(result, day, "Deposits and Other Public Borrowings")
    assert before - after == pytest.approx(0.4 * 2_500_000.0, rel=1e-6)  # the FHLB advance stays


def test_runoff_starts_on_the_start_date(simulation: Path) -> None:
    stress = DepositStress(runoff_rate=0.5)
    result = run(simulation, Historical(), end=datetime.date(2021, 12, 31), deposit_stress=stress)
    import math

    first = _line(result, datetime.date(2021, 7, 1), "Deposits and Other Public Borrowings")
    assert first == pytest.approx(2_500_000.0 * math.exp(-0.5 / 365) + 100_000.0, rel=1e-6)  # one day of run-off
    last = _line(result, datetime.date(2021, 12, 31), "Deposits and Other Public Borrowings")
    years = (datetime.date(2021, 12, 31) - datetime.date(2021, 6, 30)).days / 365
    assert last == pytest.approx(2_500_000.0 * math.exp(-0.5 * years) + 100_000.0, rel=1e-6)


def test_selling_the_afs_book_on_a_weekend_sells_on_the_next_market_day(simulation: Path) -> None:
    result = run(simulation, Historical(), end=datetime.date(2021, 8, 31), sell_afs_on=datetime.date(2021, 8, 7))
    position = result.positions.set_index("id").loc["pos-ust-afs"]
    assert position["status"] == "CLOSED"
    assert result.carrying_value["pos-ust-afs"].dropna().index[-1].date() == datetime.date(2021, 8, 9)


def test_stress_inputs_are_validated() -> None:
    with pytest.raises(ValueError, match="withdrawal"):
        DepositStress(withdrawal=1.5, withdrawal_date=_START)
    with pytest.raises(ValueError, match="withdrawal_date"):
        DepositStress(withdrawal=0.2)
    with pytest.raises(ValueError, match="runoff_rate"):
        DepositStress(runoff_rate=-0.1)


def test_borrowing_flag_reaches_the_bank_file_spec(simulation: Path) -> None:
    import zipfile

    specs = json.loads(zipfile.ZipFile(simulation).read("instruments.json"))
    assert next(s for s in specs if s["id"] == "fhlb")["borrowing"] is True


def test_cli_stress_flags(simulation: Path, tmp_path: Path) -> None:
    from brms.lab.__main__ import main

    code = main(["run", str(simulation), "--scenario", "historical", "--months", "2", "--withdrawal", "0.3",
                 "--withdrawal-date", "2021-08-02", "--sell-afs-on", "2021-08-07", "--out", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "historical" / "summary.json").exists()
