"""The server survives crashed workers, failed summaries and racing deletes."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from brms.web import jobs  # noqa: E402
from brms.web.app import create_app  # noqa: E402
from brms.web.workspace import Workspace  # noqa: E402

if TYPE_CHECKING:
    from pathlib import Path


def _die(*_args: Any) -> None:  # noqa: ANN401
    os._exit(1)  # a worker killed mid-run (out of memory, segfault)


def _wait(client: TestClient, url: str, done: Any, timeout: float = 120) -> dict[str, Any]:  # noqa: ANN401
    deadline = time.monotonic() + timeout
    while True:
        body = client.get(url).json()
        if done(body):
            return body
        if time.monotonic() > deadline:
            pytest.fail(f"Timed out on {url}: {body}")
        time.sleep(0.2)


def test_a_crashed_worker_fails_its_run_and_the_pool_recovers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = jobs.run_scenario
    monkeypatch.setattr(jobs, "run_scenario", _die)
    with TestClient(create_app(tmp_path, workers=1)) as client:
        _wait(client, "/api/banks/demo-htm_treasury", lambda b: b["status"] == "ready")
        crashed = client.post("/api/runs", json={"bank_id": "demo-htm_treasury", "months": 1}).json()["id"]
        run = _wait(client, f"/api/runs/{crashed}", lambda r: r["meta"]["status"] != "queued"
                    and r["meta"]["status"] != "running")
        assert run["meta"]["status"] == "failed"
        assert "worker" in run["meta"]["error"].lower()
        monkeypatch.setattr(jobs, "run_scenario", real)
        response = client.post("/api/runs", json={"bank_id": "demo-htm_treasury", "months": 1})
        assert response.status_code == 202, response.text
        run = _wait(client, f"/api/runs/{response.json()['id']}", lambda r: r["meta"]["status"] in {"done", "failed"})
        assert run["meta"]["status"] == "done", run["meta"]["error"]


def test_a_failed_demo_summary_is_reported_not_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def broken(zip_path: str, _out: str) -> None:
        calls.append(zip_path)
        msg = "stale simulation: regenerate it"
        raise ValueError(msg)

    monkeypatch.setattr(jobs, "summarise_bank", broken)
    from concurrent.futures import ThreadPoolExecutor

    with TestClient(create_app(tmp_path, executor=ThreadPoolExecutor(1))) as client:
        bank = _wait(client, "/api/banks/demo-mortgage", lambda b: b["status"] == "failed")
        assert "regenerate" in bank["error"]
        for _ in range(3):
            client.get("/api/banks/demo-mortgage")
        assert len([c for c in calls if c.endswith("mortgage.zip")]) == 1


def test_a_building_bank_cannot_be_deleted(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    bank = workspace.create_bank("building", "bank_file")
    with TestClient(create_app(tmp_path, workers=1)) as client:
        # the restart marked it failed; put it back into "building" as if a build were running
        workspace.update_bank(bank["id"], status="building")
        assert client.delete(f"/api/banks/{bank['id']}").status_code == 409


def test_updates_to_deleted_items_are_ignored(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    bank = workspace.create_bank("gone", "bank_file")
    run = workspace.create_run({"id": bank["id"], "name": "gone"}, {"kind": "historical"})
    workspace.delete_bank(bank["id"])
    workspace.delete_run(run["id"])
    assert workspace.update_bank(bank["id"], status="ready") is None
    assert workspace.update_run(run["id"], status="done") is None
    assert workspace.banks() == [b for b in workspace.banks() if b.get("id")]
    assert not (tmp_path / "banks" / bank["id"]).exists()
