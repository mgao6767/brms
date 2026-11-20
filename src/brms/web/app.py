"""FastAPI application: the JSON API over the lab and the static front end."""

from __future__ import annotations

import contextlib
import datetime
import json
import pickle
import threading
from collections import OrderedDict
from concurrent.futures import Executor, Future, ProcessPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from brms.web import jobs
from brms.web.payloads import day_payload
from brms.web.workspace import DEMO_PREFIX, Workspace, default_data_dir, now

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from brms.lab.runner import RunResult

STATIC = Path(__file__).with_name("static")


class RunRequest(BaseModel):
    """A scenario run of one bank."""

    bank_id: str
    kind: str = "historical"
    name: str | None = None
    bp: float | None = None
    points: list[list[float]] | None = None
    ramp_days: int = Field(default=0, ge=0, le=3650)
    months: int = Field(default=12, ge=1, le=jobs.MAX_MONTHS)
    aoci_filter: bool | None = None
    reinvest: bool = False
    label: str | None = Field(default=None, max_length=120)


class CallReportRequest(BaseModel):
    """A bank to build from its Call Report."""

    cert: int = Field(gt=0)
    date: datetime.date
    ltv: float = Field(default=0.8, gt=0, le=1.5)
    aoci_filter: bool = True
    afs: dict[str, float] | None = None


class BankFileRequest(BaseModel):
    """A bank to build from a point-in-time bank file (see ``brms.lab.bank_file``)."""

    bank: dict[str, Any]


class JobManager:
    """Runs jobs in worker processes, one process per job, and records the outcome."""

    def __init__(self, executor: Executor) -> None:
        """Use *executor* for every job."""
        self._executor = executor
        self._futures: dict[str, Future[Any]] = {}
        self._lock = threading.Lock()

    def submit(
        self, key: str, fn: Callable[..., Any], args: tuple[Any, ...], on_done: Callable[[Future[Any]], None],
    ) -> None:
        """Run ``fn(*args)`` in a worker; call *on_done* with the future when it finishes."""
        future = self._executor.submit(fn, *args)
        with self._lock:
            self._futures[key] = future

        def finished(f: Future[Any]) -> None:
            with self._lock:
                self._futures.pop(key, None)
            on_done(f)

        future.add_done_callback(finished)

    def running(self, key: str) -> bool:
        """Return True while the job *key* has started and not finished."""
        with self._lock:
            future = self._futures.get(key)
        return future is not None and future.running()

    def shutdown(self) -> None:
        """Stop accepting jobs and cancel queued ones."""
        self._executor.shutdown(wait=False, cancel_futures=True)


_MAX_ERROR = 2000


def _error_text(exc: BaseException) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text if len(text) < _MAX_ERROR else text[:_MAX_ERROR] + "..."


def create_app(  # noqa: C901, PLR0915 (one factory registers every route as a closure over its state)
    data_dir: Path | None = None, *, workers: int = 2, executor: Executor | None = None,
) -> FastAPI:
    """Return the web application storing its banks and runs under *data_dir*."""
    workspace = Workspace(data_dir or default_data_dir())
    workspace.recover()
    manager = JobManager(executor or ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=1))
    results: OrderedDict[str, RunResult] = OrderedDict()
    results_lock = threading.Lock()
    summarising: set[str] = set()

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        manager.shutdown()

    app = FastAPI(title="BRMS Stress Lab", version="1", lifespan=lifespan)
    app.state.workspace = workspace
    app.state.jobs = manager

    # -- helpers ---------------------------------------------------------------------------

    def ensure_demo_summary(bank_id: str) -> None:
        if workspace.bank_summary(bank_id) is not None or bank_id in summarising:
            return
        summarising.add(bank_id)
        zip_path = workspace.bank_zip(bank_id)
        out = workspace.bank_dir(bank_id) / "summary.json"

        def done(_f: Future[Any]) -> None:
            summarising.discard(bank_id)

        manager.submit(f"summary:{bank_id}", jobs.summarise_bank, (str(zip_path), str(out)), done)

    def bank_or_404(bank_id: str) -> dict[str, Any]:
        meta = workspace.bank_meta(bank_id)
        if meta is None:
            raise HTTPException(404, f"No bank {bank_id!r}")
        return meta

    def run_or_404(run_id: str) -> dict[str, Any]:
        meta = workspace.run_meta(run_id)
        if meta is None:
            raise HTTPException(404, f"No run {run_id!r}")
        return meta

    def load_result(run_id: str) -> RunResult:
        with results_lock:
            if run_id in results:
                results.move_to_end(run_id)
                return results[run_id]
        path = workspace.run_dir(run_id) / "result.pkl"
        if not path.exists():
            raise HTTPException(409, f"Run {run_id!r} has no results yet")
        with path.open("rb") as handle:
            result = pickle.load(handle)  # noqa: S301 (written by this app's own workers)
        with results_lock:
            results[run_id] = result
            while len(results) > 4:  # noqa: PLR2004
                results.popitem(last=False)
        return result

    def build_bank(meta: dict[str, Any], fn: Callable[..., Any], payload: dict[str, Any]) -> None:
        folder = workspace.bank_dir(meta["id"])

        def done(f: Future[Any]) -> None:
            exc = f.exception()
            if exc is not None:
                workspace.update_bank(meta["id"], status="failed", error=_error_text(exc))
                return
            summary = f.result()
            workspace.update_bank(meta["id"], status="ready", name=summary.get("name", meta["name"]),
                                  start_date=summary.get("start_date"))

        manager.submit(f"bank:{meta['id']}", fn, (payload, str(folder)), done)

    def bank_view(meta: dict[str, Any]) -> dict[str, Any]:
        summary = workspace.bank_summary(meta["id"]) if meta.get("status") in {"ready", "pending"} else None
        if meta["id"].startswith(DEMO_PREFIX) and summary is None:
            ensure_demo_summary(meta["id"])
        view = {**meta}
        if summary:
            sheet = summary["balance_sheet"]
            view.update(status="ready", name=summary["name"], start_date=summary["start_date"],
                        end_date=summary["end_date"], total_assets=sheet["total_assets"],
                        total_equity=sheet["total_equity"], positions=len(summary["positions"]))
        return view

    # -- banks -----------------------------------------------------------------------------

    @app.get("/api/banks")
    def list_banks() -> list[dict[str, Any]]:
        return [bank_view(m) for m in workspace.banks()]

    @app.get("/api/banks/{bank_id}")
    def get_bank(bank_id: str) -> dict[str, Any]:
        meta = bank_or_404(bank_id)
        view = bank_view(meta)
        view["summary"] = workspace.bank_summary(bank_id) if view.get("status") == "ready" else None
        return view

    @app.post("/api/banks", status_code=202)
    def create_bank(request: BankFileRequest) -> dict[str, Any]:
        bank = request.bank
        missing = [k for k in ("as_of", "cash") if k not in bank]
        if missing:
            raise HTTPException(400, f"The bank file needs {', '.join(missing)}")
        meta = workspace.create_bank(str(bank.get("name") or "Uploaded bank"), "bank_file")
        build_bank(meta, jobs.build_from_bank_file, bank)
        return meta

    @app.post("/api/banks/call-report", status_code=202)
    def create_bank_from_call_report(request: CallReportRequest) -> dict[str, Any]:
        quarter_ends = {(3, 31), (6, 30), (9, 30), (12, 31)}
        if (request.date.month, request.date.day) not in quarter_ends:
            raise HTTPException(400, "The report date must be a quarter end (Mar 31, Jun 30, Sep 30 or Dec 31)")
        payload = request.model_dump(mode="json")
        meta = workspace.create_bank(f"FDIC #{request.cert} ({request.date})", "call_report",
                                     {"cert": request.cert, "report_date": request.date.isoformat()})
        build_bank(meta, jobs.build_from_call_report, payload)
        return meta

    @app.delete("/api/banks/{bank_id}", status_code=204)
    def delete_bank(bank_id: str) -> None:
        bank_or_404(bank_id)
        if bank_id.startswith(DEMO_PREFIX):
            raise HTTPException(400, "Demo banks cannot be deleted")
        if not workspace.delete_bank(bank_id):
            raise HTTPException(404, f"No bank {bank_id!r}")

    # -- scenarios and runs ------------------------------------------------------------------

    @app.get("/api/scenarios")
    def scenarios() -> dict[str, Any]:
        return {
            "kinds": ["historical", "basel", "parallel", "key_rate"],
            "basel": [{"name": k, "label": v} for k, v in jobs.BASEL_LABELS.items()],
            "max_months": jobs.MAX_MONTHS,
        }

    @app.post("/api/runs", status_code=202)
    def create_run(request: RunRequest) -> dict[str, Any]:
        bank = bank_view(bank_or_404(request.bank_id))
        zip_path = workspace.bank_zip(request.bank_id)
        if bank.get("status") != "ready" and not request.bank_id.startswith(DEMO_PREFIX):
            raise HTTPException(409, f"Bank {request.bank_id!r} is not ready ({bank.get('status')})")
        if zip_path is None:
            raise HTTPException(409, f"Bank {request.bank_id!r} has no simulation yet")
        spec = request.model_dump(exclude={"bank_id"}, exclude_none=True)
        try:
            jobs.scenario_from_spec(spec)
        except jobs.SpecError as exc:
            raise HTTPException(400, str(exc)) from exc
        if spec.get("kind", "historical") == "historical" and bank.get("end_date"):
            start = datetime.date.fromisoformat(bank["start_date"])
            last = datetime.date.fromisoformat(bank["end_date"])
            months_available = (last.year - start.year) * 12 + last.month - start.month + 1
            if request.months > months_available:
                raise HTTPException(400, f"Historical rates for this bank run to {last}: at most "
                                         f"{months_available} months; use a shock scenario to go further")
        spec["description"] = jobs.describe(spec)
        meta = workspace.create_run(bank, spec)
        run_id = meta["id"]

        def done(f: Future[Any]) -> None:
            exc = f.exception()
            if exc is not None:
                workspace.update_run(run_id, status="failed", error=_error_text(exc), finished=now())
            else:
                workspace.update_run(run_id, status="done", summary=f.result(), finished=now())

        manager.submit(f"run:{run_id}", jobs.run_scenario, (str(zip_path), spec, str(workspace.run_dir(run_id))), done)
        return workspace.run_meta(run_id) or meta

    def live(meta: dict[str, Any]) -> dict[str, Any]:
        if meta.get("status") == "queued" and manager.running(f"run:{meta['id']}"):
            return {**meta, "status": "running"}
        return meta

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        return [live(m) for m in workspace.runs()]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        meta = live(run_or_404(run_id))
        out: dict[str, Any] = {"meta": meta}
        payload_path = workspace.run_dir(run_id) / "payload.json"
        if meta.get("status") == "done" and payload_path.exists():
            out.update(json.loads(payload_path.read_text()))
        return out

    @app.get("/api/runs/{run_id}/day")
    def get_day(run_id: str, date: datetime.date) -> dict[str, Any]:
        run_or_404(run_id)
        return day_payload(load_result(run_id), date)

    @app.get("/api/runs/{run_id}/metrics.csv", response_class=PlainTextResponse)
    def metrics_csv(run_id: str) -> PlainTextResponse:
        run_or_404(run_id)
        csv = load_result(run_id).metrics.to_csv(index_label="date")
        headers = {"Content-Disposition": f'attachment; filename="{run_id}-metrics.csv"'}
        return PlainTextResponse(csv, media_type="text/csv", headers=headers)

    @app.delete("/api/runs/{run_id}", status_code=204)
    def delete_run(run_id: str) -> None:
        meta = run_or_404(run_id)
        if meta.get("status") in {"queued", "running"}:
            raise HTTPException(409, "The run is still in progress")
        with results_lock:
            results.pop(run_id, None)
        workspace.delete_run(run_id)

    # -- front end ---------------------------------------------------------------------------

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    return app
