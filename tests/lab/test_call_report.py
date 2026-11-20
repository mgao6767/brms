"""Call Report (FDIC BankFind) items become a bank file."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import json
from pathlib import Path

import pytest

from brms.lab.call_report import FIELDS, bank_file_from_call_report, fetch_call_report

_FIXTURE = Path(__file__).resolve().parents[2] / "src" / "brms" / "lab" / "examples" / "svb_call_report_20211231.json"
_PRIME = 0.0325


@pytest.fixture(scope="module")
def items() -> dict:
    return json.loads(_FIXTURE.read_text())


@pytest.fixture(scope="module")
def bank(items: dict) -> dict:
    return bank_file_from_call_report(items, prime=_PRIME)


def _securities(bank: dict) -> list[dict]:
    return [p for p in bank["positions"] if p["basis"] in {"AMORTIZED_COST", "FVOCI"} and "ltv" not in p
            and p["type"] in {"fixed_rate_bond", "treasury_note", "mortgage_backed_security"}]


def test_header(bank: dict, items: dict) -> None:
    assert bank["as_of"] == "2021-12-31"
    assert "SILICON VALLEY BANK" in bank["name"]
    assert bank["cash"] == items["CHBAL"] + items["FREPO"]
    assert bank["reported"]["EQ"] == items["EQ"]
    assert bank["regulatory"] == {"aoci_filter": True}
    assert bank["unit"] == 1000


def test_securities_reproduce_the_reported_book_and_fair_values(bank: dict, items: dict) -> None:
    held = [p for p in _securities(bank) if p["basis"] == "AMORTIZED_COST"]
    afs = [p for p in _securities(bank) if p["basis"] == "FVOCI"]
    scale = (items["SCHA"] + items["SCAF"]) / sum(
        items[k] for k in items if k.startswith(("SCNM", "SCPT")) or k in {"SCO3YLES", "SCOOV3Y"})
    assert sum(p["amortized_cost"] for p in held) * scale == pytest.approx(items["SCHA"], rel=1e-6)
    assert sum(p["fair_value"] for p in held) * scale == pytest.approx(items["SCHF"], rel=1e-6)
    assert sum(p["fair_value"] for p in afs) * scale == pytest.approx(items["SCAF"], rel=1e-6)
    assert sum(p["amortized_cost"] for p in afs) * scale == pytest.approx(items["SCAA"], rel=1e-6)


def test_long_pass_throughs_are_mbs_pools(bank: dict, items: dict) -> None:
    pools = [p for p in bank["positions"] if p["id"].startswith("pt-ov15")]
    assert {p["type"] for p in pools} == {"mortgage_backed_security"}
    assert {p["maturity"] for p in pools} == {"25Y"}
    assert {p["issuer"]["issuer_type"] for p in pools} == {"PSE"}
    expected_yield = items["ISC"] / items["SC5"]
    assert pools[0]["coupon_rate"] == pytest.approx(expected_yield)


def test_treasury_share_of_non_mortgage_debt_is_sovereign(bank: dict, items: dict) -> None:
    nm = [p for p in bank["positions"] if p["id"].startswith("nm-")]
    sovereign = sum(p.get("fair_value", 0) if p["basis"] == "FVOCI" else p["amortized_cost"]
                    for p in nm if p["issuer"]["issuer_type"] == "SOVEREIGN")
    total = sum(p.get("fair_value", 0) if p["basis"] == "FVOCI" else p["amortized_cost"] for p in nm)
    nm_total = sum(items[k] for k in items if k.startswith("SCNM"))
    assert sovereign / total == pytest.approx(min(1.0, items["SCUST"] / nm_total), rel=1e-6)


def test_loans_sum_to_net_loans_and_short_buckets_float(bank: dict, items: dict) -> None:
    loans = [p for p in bank["positions"] if p["id"].startswith(("ln-", "rs-"))]
    assert sum(p["amortized_cost"] for p in loans) == pytest.approx(items["LNLSNET"], rel=1e-9)
    floating = [p for p in loans if p["type"] == "variable_rate_loan"]
    assert {p["id"] for p in floating} == {"ln-3les", "rs-3les"}
    loan_yield = items["ILNLS"] / items["LNLSGR5"]
    assert floating[0]["spread"] == pytest.approx(loan_yield - _PRIME)
    mortgages = [p for p in loans if p["type"] == "residential_mortgage"]
    assert all(p["ltv"] == 0.8 for p in mortgages)


def test_deposits_and_borrowings(bank: dict, items: dict) -> None:
    by_id = {d["id"]: d for d in bank["deposits"]}
    assert by_id["nib"]["balance"] == items["DEPNIDOM"]
    assert by_id["nib"]["interest_rate"] == 0.0
    assert by_id["ib"]["balance"] == items["DEP"] - items["DEPNIDOM"]
    assert by_id["ib"]["interest_rate"] == pytest.approx(items["EDEP"] / (items["DEP"] - items["DEPNIDOM"]))
    borrowed = items["OTHBRF"] + items["FREPP"] + items["SUBND"]
    assert by_id["borrowings"]["balance"] == borrowed
    assert by_id["borrowings"]["beta"] == 1.0


def test_income_is_annualised_for_interim_quarters(items: dict) -> None:
    june = {**items, "REPDTE": "20210630"}
    bank = bank_file_from_call_report(june, prime=_PRIME)
    pool = next(p for p in bank["positions"] if p["type"] == "mortgage_backed_security")
    assert pool["coupon_rate"] == pytest.approx(2 * items["ISC"] / items["SC5"])


def test_fetch_parses_the_api_response() -> None:
    seen: list[str] = []

    def get(url: str) -> bytes:
        seen.append(url)
        return json.dumps({"data": [{"data": {"CERT": 1, "REPDTE": "20211231", "ASSET": 5}}]}).encode()

    items = fetch_call_report(1, "2021-12-31", get=get)
    assert items["ASSET"] == 5
    assert "CERT:1" in seen[0].replace("%3A", ":")
    assert "REPDTE:20211231" in seen[0].replace("%3A", ":")
    assert all(f in seen[0] for f in FIELDS)


def test_fetch_without_a_filing_raises() -> None:
    with pytest.raises(LookupError, match="24735"):
        fetch_call_report(24735, "2021-12-30", get=lambda _url: b'{"data": []}')


def test_built_bank_reconciles(bank: dict, tmp_path: Path) -> None:
    from brms.core.services import build_core_services
    from brms.lab.bank_file import build_bank, default_market_frames
    from tests.support.reconcile import assert_books_reconcile

    path = tmp_path / "bank.json"
    path.write_text(json.dumps(bank))
    out = build_bank(path, default_market_frames(), tmp_path / "bank.zip")
    sim = build_core_services(simulation_zip=out).simulation_service
    for _ in range(10):
        sim.advance()
        assert_books_reconcile(sim, sim.current_date)


def test_cli_writes_a_bank_file(items: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import brms.lab.call_report as module
    from brms.lab.__main__ import main

    monkeypatch.setattr(module, "fetch_call_report", lambda cert, _date: {**items, "CERT": cert})
    out = tmp_path / "svb.json"
    assert main(["call-report", "--cert", "24735", "--date", "2021-12-31", "--out", str(out)]) == 0
    bank = json.loads(out.read_text())
    assert bank["source"]["cert"] == 24735
    ib_loan = next(p for p in bank["positions"] if p["id"] == "ln-3les")
    assert ib_loan["spread"] == pytest.approx(items["ILNLS"] / items["LNLSGR5"] - 0.0325)  # Prime 3.25% at end-2021


def test_afs_composition_moves_classes_between_books(items: dict) -> None:
    # Everything AFS is Treasuries: no pass-through pool is AFS, and the Treasury pieces are all AFS.
    nm_total = sum(items[k] for k in items if k.startswith("SCNM"))
    treasuries = min(1.0, items["SCUST"] / nm_total) * nm_total
    bank = bank_file_from_call_report(items, prime=_PRIME, afs={"treasury": treasuries})
    afs = [p for p in bank["positions"] if p["basis"] == "FVOCI"]
    assert {p["id"].split("-")[2] for p in afs} == {"ust"}
    assert sum(p["fair_value"] for p in afs) == pytest.approx(treasuries, rel=1e-9)
    held = [p for p in bank["positions"] if p["id"].startswith("pt-")]
    assert {p["basis"] for p in held} == {"AMORTIZED_COST"}


def test_afs_composition_is_scaled_to_the_reported_afs_total(items: dict) -> None:
    bank = bank_file_from_call_report(items, prime=_PRIME, afs={"treasury": 1.0, "pass_through": 1.0})
    afs = [p for p in bank["positions"] if p["basis"] == "FVOCI"]
    assert sum(p["fair_value"] for p in afs) == pytest.approx(items["SCAF"], rel=1e-6)


def test_unknown_afs_class_is_rejected(items: dict) -> None:
    with pytest.raises(ValueError, match="munis"):
        bank_file_from_call_report(items, prime=_PRIME, afs={"munis": 1.0})
