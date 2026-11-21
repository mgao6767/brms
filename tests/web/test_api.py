"""The web API end to end, with real worker processes and a temporary data folder."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from brms.web.app import create_app  # noqa: E402
from tests.lab.test_bank_file import _bank as bank_file  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_DEMO = "demo-htm_treasury"


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    app = create_app(tmp_path_factory.mktemp("web"), workers=2)
    with TestClient(app) as test_client:
        yield test_client


def wait(client: TestClient, url: str, done: Any, timeout: float = 240) -> dict[str, Any]:  # noqa: ANN401
    deadline = time.monotonic() + timeout
    while True:
        body = client.get(url).json()
        if done(body):
            return body
        if time.monotonic() > deadline:
            pytest.fail(f"Timed out waiting on {url}: {body}")
        time.sleep(0.25)


def ready_bank(client: TestClient, bank_id: str) -> dict[str, Any]:
    return wait(client, f"/api/banks/{bank_id}", lambda b: b["status"] in {"ready", "failed"})


def finished_run(client: TestClient, run_id: str) -> dict[str, Any]:
    return wait(client, f"/api/runs/{run_id}", lambda r: r["meta"]["status"] in {"done", "failed"})


def test_front_end_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "<title>" in response.text
    assert client.get("/static/vendor/echarts.min.js").status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    assert client.get("/static/js/main.js").headers["cache-control"] == "no-cache"


def test_demo_banks_are_listed_and_summarised(client: TestClient) -> None:
    ids = [b["id"] for b in client.get("/api/banks").json()]
    assert _DEMO in ids
    assert "demo-diversified_bank" in ids
    bank = ready_bank(client, _DEMO)
    assert bank["status"] == "ready"
    summary = bank["summary"]
    assert summary["start_date"] < summary["end_date"]
    assert summary["balance_sheet"]["total_assets"] > 0
    assert any(p["basis"] == "AMORTIZED_COST" for p in summary["positions"])
    listed = next(b for b in client.get("/api/banks").json() if b["id"] == _DEMO)
    assert listed["total_assets"] == pytest.approx(summary["balance_sheet"]["total_assets"])


def test_historical_run_end_to_end(client: TestClient) -> None:
    ready_bank(client, _DEMO)
    created = client.post("/api/runs", json={"bank_id": _DEMO, "kind": "historical", "months": 1})
    assert created.status_code == 202, created.text
    run_id = created.json()["id"]
    run = finished_run(client, run_id)
    assert run["meta"]["status"] == "done", run["meta"]["error"]
    assert run["meta"]["spec"]["description"] == "Historical rates"
    assert run["meta"]["unit"] == 1
    dates = run["dates"]
    assert len(dates) >= 18
    cet1 = run["metrics"]["CET1_RATIO"]
    assert len(cet1) == len(dates)
    assert all(v is None or 0 < v < 5 for v in cet1)
    assert set(run["composition"]) == {"assets", "liabilities", "equity"}
    assert "10 Yr" in run["yields"]["tenors"]
    assert run["positions"]
    assert "htm" in run["unrealised"]
    assert run["summary"]["scenario"] == "historical"

    day = client.get(f"/api/runs/{run_id}/day", params={"date": dates[5]}).json()
    assert day["statement_date"] == dates[5]
    totals = day["totals"]
    assert totals["total_assets"] == pytest.approx(totals["total_liabilities"] + totals["total_equity"], abs=0.01)
    assert day["journal"], "every market day posts accruals"
    assert any(entry["instrument"] for entry in day["journal"])
    for entry in day["journal"]:
        debit = sum(line["debit"] for line in entry["lines"])
        credit = sum(line["credit"] for line in entry["lines"])
        assert debit == pytest.approx(credit, abs=1e-6)
    assert day["valuations"]

    csv = client.get(f"/api/runs/{run_id}/metrics.csv")
    assert csv.status_code == 200
    assert csv.text.startswith("date,")
    for table, header in (("statements", "date,section,account,balance"),
                          ("journal", "date,entry,kind,description,position,account,debit,credit"),
                          ("valuations", "date,position,carrying_value,fair_value,amortized_cost")):
        response = client.get(f"/api/runs/{run_id}/{table}.csv")
        assert response.status_code == 200, table
        assert response.text.splitlines()[0] == header
        assert "attachment" in response.headers["content-disposition"]
    assert client.get(f"/api/runs/{run_id}/nonsense.csv").status_code == 404

    assert any(r["id"] == run_id for r in client.get("/api/runs").json())
    assert client.delete(f"/api/runs/{run_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404


@pytest.mark.parametrize(("body", "status", "message"), [
    ({"bank_id": "nope", "kind": "historical"}, 404, "No bank"),
    ({"bank_id": _DEMO, "kind": "basel", "name": "sideways"}, 400, "Unknown Basel scenario"),
    ({"bank_id": _DEMO, "kind": "key_rate", "points": []}, 400, "key-rate"),
    ({"bank_id": _DEMO, "kind": "warp"}, 400, "Unknown scenario kind"),
    ({"bank_id": _DEMO, "kind": "historical", "months": 0}, 422, ""),
    ({"bank_id": _DEMO, "kind": "historical", "months": 120}, 400, "at most"),
])
def test_bad_run_requests(client: TestClient, body: dict[str, Any], status: int, message: str) -> None:
    ready_bank(client, _DEMO)
    response = client.post("/api/runs", json=body)
    assert response.status_code == status, response.text
    assert message in response.text


def test_shock_run_on_an_uploaded_bank(client: TestClient) -> None:
    created = client.post("/api/banks", json={"bank": bank_file()})
    assert created.status_code == 202, created.text
    bank_id = created.json()["id"]
    bank = ready_bank(client, bank_id)
    assert bank["status"] == "ready", bank.get("error")
    assert bank["name"] == "Point-in-time Bank"
    assert bank["source"] == "bank_file"
    spec = {"bank_id": bank_id, "kind": "key_rate", "points": [[0.25, 50], [10, 150]], "ramp_days": 10, "months": 1,
            "aoci_filter": False, "label": "custom"}
    run = finished_run(client, client.post("/api/runs", json=spec).json()["id"])
    assert run["meta"]["status"] == "done", run["meta"]["error"]
    assert run["meta"]["spec"]["description"] == "Key rates (0.25Y +50, 10Y +150), phased in over 10 days"
    ten_year = run["yields"]["values"]["10 Yr"]
    assert ten_year[-1] - ten_year[0] == pytest.approx(1.5, abs=1e-9)  # no shift on the start day, 150bp after the ramp
    assert client.delete(f"/api/banks/{bank_id}").status_code == 204
    assert client.get(f"/api/banks/{bank_id}").status_code == 404


def test_failed_bank_build_reports_the_error(client: TestClient) -> None:
    bank_id = client.post("/api/banks", json={"bank": bank_file(cash=-5_000_000.0)}).json()["id"]
    bank = ready_bank(client, bank_id)
    assert bank["status"] == "failed"
    assert "equity" in bank["error"]
    response = client.post("/api/runs", json={"bank_id": bank_id})
    assert response.status_code == 409


def test_bank_requests_are_validated(client: TestClient) -> None:
    assert client.post("/api/banks", json={"bank": {"name": "x"}}).status_code == 400
    response = client.post("/api/banks/call-report", json={"cert": 24735, "date": "2021-12-30"})
    assert response.status_code == 400
    assert "quarter end" in response.text
    assert client.delete(f"/api/banks/{_DEMO}").status_code == 400
    assert client.get("/api/banks/..%2Fetc").status_code == 404


def test_interrupted_work_is_marked_failed_on_restart(tmp_path: Path) -> None:
    from brms.web.workspace import Workspace

    workspace = Workspace(tmp_path)
    run = workspace.create_run({"id": _DEMO, "name": "demo"}, {"kind": "historical"})
    bank = workspace.create_bank("half-built", "bank_file")
    app = create_app(tmp_path, workers=1)
    with TestClient(app) as test_client:
        assert test_client.get(f"/api/runs/{run['id']}").json()["meta"]["status"] == "failed"
        assert test_client.get(f"/api/banks/{bank['id']}").json()["status"] == "failed"


def test_stress_options_are_validated_and_described(client: TestClient) -> None:
    ready_bank(client, _DEMO)
    bad = client.post("/api/runs", json={"bank_id": _DEMO, "months": 1, "withdrawal": 0.2})
    assert bad.status_code == 400
    assert "withdrawal date" in bad.text
    late = client.post("/api/runs", json={"bank_id": _DEMO, "months": 1, "sell_afs_on": "2030-01-01"})
    assert late.status_code == 400
    assert "outside the run" in late.text
    ok = client.post("/api/runs", json={"bank_id": _DEMO, "months": 1, "deposit_runoff": 0.5, "withdrawal": 0.25,
                                        "withdrawal_date": "2022-01-20"})
    assert ok.status_code == 202, ok.text
    run = finished_run(client, ok.json()["id"])
    assert run["meta"]["status"] == "done", run["meta"]["error"]
    assert run["meta"]["spec"]["description"] == (
        "Historical rates; deposits run off 50% a year; 25% of deposits withdrawn on 2022-01-20")
