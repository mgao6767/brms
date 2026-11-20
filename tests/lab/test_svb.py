"""SVB acceptance case: 2022 unrealised losses from the end-2021 balance sheet.

This pins the documented outcome (docs/svb.md): the AFS loss rate is matched to within 1.5
percentage points; the HTM loss is understated because the engine has no prepayment model (the
reported HTM duration extended from 4.1 to 6.2 years) and agency MBS spreads widened in 2022.
"""
# ruff: noqa: D103

from __future__ import annotations

import pytest

from brms.lab.examples.svb import DURATION_2021, DURATION_2022, REPORTED_LOSS_RATE_2022, run_case


@pytest.fixture(scope="module")
def outcomes(tmp_path_factory: pytest.TempPathFactory) -> tuple:
    tmp = tmp_path_factory.mktemp("svb")
    return run_case("start", DURATION_2021, tmp), run_case("end", DURATION_2022, tmp)


def test_afs_loss_rate_matches_reported(outcomes: tuple) -> None:
    for outcome in outcomes:
        assert abs(outcome.afs_rate - REPORTED_LOSS_RATE_2022["afs"]) < 0.015  # noqa: S101, PLR2004


def test_htm_loss_is_understated_and_closer_with_extended_duration(outcomes: tuple) -> None:
    start, end = outcomes
    reported = REPORTED_LOSS_RATE_2022["htm"]
    assert reported < end.htm_rate < start.htm_rate < 0  # noqa: S101
    assert end.htm_rate - reported < 0.05  # noqa: S101, PLR2004


def test_bank_file_figures() -> None:
    from brms.lab.examples.svb import bank_file

    data = bank_file(4.1, 3.5)
    assets = data["cash"] + sum(p["fair_value"] if p["basis"] == "FVOCI" else p["amortized_cost"]
                                for p in data["positions"])
    deposits = sum(d["balance"] for d in data["deposits"])
    # 10-K FY2021: total equity 16,609; the plug differs by items not modelled (other assets/liabilities).
    assert abs((assets - deposits) - 16_609) < 100  # noqa: S101, PLR2004
