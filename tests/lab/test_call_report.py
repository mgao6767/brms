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
    assert bank["regulatory"]["aoci_filter"] is True
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
    assert by_id["ib"]["beta"] == 0.35
    assert "beta" not in by_id["nib"]
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


def test_operating_flows_and_tax_rate(bank: dict, items: dict) -> None:
    assert bank["operating"] == {
        "noninterest_expense": items["NONIX"], "noninterest_income": items["NONII"],
        "tax_rate": pytest.approx(items["ITAX"] / items["IBEFTAX"]),
        "dividend_payout": pytest.approx(min(1.0, items.get("EQCDIV", 0) / items["NETINC"])),
    }
    june = bank_file_from_call_report({**items, "REPDTE": "20210630"}, prime=_PRIME)
    assert june["operating"]["noninterest_expense"] == pytest.approx(2 * items["NONIX"])


def test_tax_rate_falls_back_to_the_federal_rate_without_pretax_profit(items: dict) -> None:
    bank = bank_file_from_call_report({**items, "IBEFTAX": -5.0, "ITAX": 0.0}, prime=_PRIME)
    assert bank["operating"]["tax_rate"] == 0.21


def test_operational_rwa_from_the_business_indicator() -> None:
    from brms.lab.call_report import operational_rwa

    # BI = min(|NII|, 2.25% of earning assets) + non-interest income (USD thousands)
    #    = min(3,000,000, 0.0225 x 100,000,000) + 500,000 = 2,750,000 (USD 2.75bn)
    # BIC = 12% x 1bn + 15% x 1.75bn = 382,500; RWA = 12.5 x BIC
    rwa = operational_rwa(net_interest_income=3_000_000, earning_assets=100_000_000, noninterest_income=500_000,
                          unit=1000)
    assert rwa == pytest.approx(12.5 * (0.12 * 1_000_000 + 0.15 * 1_750_000))
    big = operational_rwa(net_interest_income=40_000_000, earning_assets=4_000_000_000, noninterest_income=0,
                          unit=1000)
    assert big == pytest.approx(12.5 * (0.12 * 1e6 + 0.15 * 29e6 + 0.18 * 10e6))


def test_call_report_bank_carries_an_operational_rwa_estimate(bank: dict) -> None:
    assert bank["regulatory"]["operational_rwa"] > 0


def test_other_assets_and_liabilities_close_the_gap_to_reported_equity(bank: dict, items: dict) -> None:
    securities = sum(p["fair_value"] if p["basis"] == "FVOCI" else p["amortized_cost"]
                     for p in bank["positions"] if p["id"].startswith(("nm-", "pt-", "omb-")))
    loans = sum(p["amortized_cost"] for p in bank["positions"] if p["id"].startswith(("ln-", "rs-")))
    deposits = sum(d["balance"] for d in bank["deposits"])
    equity = (bank["cash"] + securities + loans + bank["other_assets"] + bank["intangible_assets"] - deposits
              - bank["other_liabilities"])
    assert bank["intangible_assets"] == items["INTAN"]
    assert equity == pytest.approx(items["EQ"], rel=0.01)
    assert bank["other_assets"] >= 0
    assert bank["other_liabilities"] >= 0


def test_a_weekend_report_date_is_described_as_of_the_friday(items: dict) -> None:
    saturday = bank_file_from_call_report({**items, "REPDTE": "20221231"}, prime=_PRIME)
    assert saturday["as_of"] == "2022-12-30"
    assert saturday["source"]["report_date"] == "2022-12-31"
    assert {p["issue_date"] for p in saturday["positions"]} == {"2022-12-30"}


def test_deposit_beta_can_be_set(items: dict) -> None:
    bank = bank_file_from_call_report(items, prime=_PRIME, deposit_beta=0.6)
    assert next(d for d in bank["deposits"] if d["id"] == "ib")["beta"] == 0.6
    with pytest.raises(ValueError, match="deposit_beta"):
        bank_file_from_call_report(items, prime=_PRIME, deposit_beta=1.5)


def test_payout_is_capped_and_zero_without_profit(items: dict) -> None:
    rich = bank_file_from_call_report({**items, "EQCDIV": 3 * items["NETINC"]}, prime=_PRIME)
    assert rich["operating"]["dividend_payout"] == 1.0
    loss = bank_file_from_call_report({**items, "NETINC": -1.0, "EQCDIV": 10.0}, prime=_PRIME)
    assert loss["operating"]["dividend_payout"] == 0.0


def test_fetch_retries_when_the_api_is_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    import io
    import urllib.error

    import brms.lab.call_report as module

    calls: list[str] = []

    class Response(io.BytesIO):
        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def urlopen(request, timeout):  # noqa: ANN001, ANN202, ARG001
        calls.append("x")
        if len(calls) < 3:
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
        return Response(b"ok")

    monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
    waits: list[float] = []
    assert module._get("https://example.invalid", sleep=waits.append) == b"ok"  # noqa: SLF001
    assert waits == [2.0, 5.0]


def test_fetch_gives_up_with_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error

    import brms.lab.call_report as module

    def urlopen(request, timeout):  # noqa: ANN001, ANN202, ARG001
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
    with pytest.raises(ConnectionError, match="404"):
        module._get("https://example.invalid", sleep=lambda _s: None)  # noqa: SLF001


def test_core_deposits_follow_the_insured_share(items: dict) -> None:
    uninsured = 0.25
    sample = {**items, "DEPUNINS": uninsured * items["DEPDOM"]}
    by_id = {d["id"]: d for d in bank_file_from_call_report(sample, prime=_PRIME)["deposits"]}
    nib, ib = by_id["nib"], by_id["ib"]
    assert nib["core_share"] == pytest.approx(0.75 * 0.9 + 0.25 * 0.5)
    assert nib["core_maturity"] == pytest.approx((0.75 * 0.9 * 5 + 0.25 * 0.5 * 4) / nib["core_share"])
    assert ib["core_share"] == pytest.approx(0.75 * 0.7 + 0.25 * 0.5)
    assert "core_share" not in by_id["borrowings"]
    off = bank_file_from_call_report(sample, prime=_PRIME, core_deposits=False)
    assert all("core_share" not in d for d in off["deposits"])


def test_a_mostly_uninsured_bank_has_less_core_funding(items: dict) -> None:
    svb = {d["id"]: d for d in bank_file_from_call_report(items, prime=_PRIME)["deposits"]}
    assert items["DEPUNINS"] / items["DEPDOM"] > 0.8  # SVB's deposits were mostly uninsured
    assert svb["nib"]["core_share"] < 0.6
