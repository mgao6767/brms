"""A run keeps what a front end needs: daily statements, the journal, positions and the rate path."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

from pathlib import Path

import pytest

from brms.lab import Historical, run

_ZIP = Path(__file__).resolve().parents[2] / "src" / "brms" / "data" / "diversified_bank.zip"


@pytest.fixture(scope="module")
def result():  # noqa: ANN201
    return run(_ZIP, Historical(), months=1)


def test_daily_statements_on_market_days(result) -> None:  # noqa: ANN001
    sheets = result.statements
    assert list(sheets.columns) == ["date", "section", "account", "balance"]
    assert set(sheets["section"]) == {"assets", "liabilities", "equity", "income", "expenses", "totals"}
    days = sorted(sheets["date"].unique())
    assert result.start <= days[0]
    assert days[-1] <= result.end
    assert len(days) >= 18  # about a month of market days
    for day in (days[0], days[-1]):
        totals = sheets[(sheets["date"] == day) & (sheets["section"] == "totals")].set_index("account")["balance"]
        assert totals["total_assets"] == pytest.approx(totals["total_liabilities"] + totals["total_equity"], abs=0.01)
        assert totals["net_income"] == pytest.approx(totals["total_income"] - totals["total_expenses"], abs=0.01)
    assert days[-1] == result.end  # this run ends on a market day
    last = sheets[(sheets["date"] == days[-1]) & (sheets["section"] == "totals")].set_index("account")["balance"]
    assert last["net_income"] == pytest.approx(result.income_statement["net_income"], abs=0.01)


def test_journal_lines_balance_per_entry(result) -> None:  # noqa: ANN001
    journal = result.journal
    assert {"date", "entry", "kind", "description", "account", "debit", "credit", "position"} <= set(journal.columns)
    assert "tx=" not in " ".join(journal["description"])
    known = set(result.positions["id"])
    assert set(journal["position"].dropna()) <= known
    assert journal["position"].notna().mean() > 0.9  # nearly every entry comes from a position's transaction
    by_entry = journal.groupby("entry")[["debit", "credit"]].sum()
    assert (by_entry["debit"] - by_entry["credit"]).abs().max() < 1e-6
    assert journal["date"].min() >= result.start


def test_positions_and_yields(result) -> None:  # noqa: ANN001
    positions = result.positions
    assert {"id", "name", "type", "basis", "book", "side"} <= set(positions.columns)
    assert len(positions) > 3
    assert {"3 Mo", "10 Yr"} <= set(result.yields.columns)
    assert result.yields.index.min().date() >= result.start


def test_summary_has_unrealised_totals_by_book(result) -> None:  # noqa: ANN001
    totals = result.summary["unrealised_end"]
    assert set(totals) <= {"htm", "afs", "loans"}
    assert "htm" in totals
    gap = (result.fair_value - result.amortized_cost).dropna(how="all").iloc[-1]
    held = result.positions[(result.positions["basis"] == "AMORTIZED_COST")
                            & ~result.positions["type"].isin(["RESIDENTIAL_MORTGAGE", "COMMERCIAL_MORTGAGE", "MORTGAGE",
                                                              "AMORTIZING_FIXED_RATE_LOAN", "VARIABLE_RATE_LOAN"])
                            & (result.positions["side"] == "LONG")]
    assert totals["htm"] == pytest.approx(float(gap[held["id"]].dropna().sum()))
