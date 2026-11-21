"""The server survives crashed workers, failed summaries and racing deletes."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from brms.web import jobs  # noqa: E402
from brms.web.app import create_app  # noqa: E402
from brms.web.workspace import Workspace  # noqa: E402


def _die(*_args: Any) -> None:  # noqa: ANN401
    os._exit(1)  # a worker killed mid-run (out of memory, segfault)


def _hang(_zip: str, _spec: dict[str, Any], folder: str) -> None:
    jobs._mark_running(Path(folder))  # noqa: SLF001
    time.sleep(600)  # a long run


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


def test_stopping_the_server_stops_runs_in_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs, "run_scenario", _hang)
    with TestClient(create_app(tmp_path, workers=2)) as client:
        _wait(client, "/api/banks/demo-htm_treasury", lambda b: b["status"] == "ready")
        running = client.post("/api/runs", json={"bank_id": "demo-htm_treasury", "months": 1}).json()["id"]
        queued = [client.post("/api/runs", json={"bank_id": "demo-htm_treasury", "months": 1}).json()["id"]
                  for _ in range(2)]
        _wait(client, f"/api/runs/{running}", lambda r: r["meta"]["status"] == "running")
        started = time.monotonic()
    assert time.monotonic() - started < 15  # did not wait for the run to finish
    workspace = Workspace(tmp_path)
    for run_id in [running, *queued]:
        meta = workspace.run_meta(run_id)
        assert meta is not None
        assert meta["status"] == "failed"
        assert "stopped" in meta["error"].lower()


def test_quit_asks_the_command_to_stop(tmp_path: Path) -> None:
    calls: list[bool] = []
    with TestClient(create_app(tmp_path, on_quit=lambda: calls.append(True))) as client:
        assert client.post("/api/quit", content="x", headers={"Content-Type": "text/plain"}).status_code == 422
        assert calls == []  # a plain form post from another web site cannot stop the lab
        response = client.post("/api/quit", json={})
        assert response.status_code == 202
        assert calls == [True]


def test_quit_without_the_command_is_not_available(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path)) as client:
        assert client.post("/api/quit", json={}).status_code == 404
