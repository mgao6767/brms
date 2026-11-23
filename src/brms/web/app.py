"""FastAPI application: the JSON API over the lab and the static front end."""

from __future__ import annotations

import contextlib
import datetime
import json
import pickle
import signal
import threading
from collections import OrderedDict
from concurrent.futures import BrokenExecutor, CancelledError, Executor, Future, ProcessPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dateutil.relativedelta import relativedelta
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from brms.web import jobs
from brms.web.payloads import day_payload, valuations_long
from brms.web.workspace import DEMO_PREFIX, Workspace, default_data_dir, now

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

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
    deposit_runoff: float = Field(default=0.0, ge=0, le=10)
    withdrawal: float = Field(default=0.0, ge=0, lt=1)
    withdrawal_date: datetime.date | None = None
    sell_afs_on: datetime.date | None = None
    label: str | None = Field(default=None, max_length=120)


class CallReportRequest(BaseModel):
    """A bank to build from its Call Report."""

    cert: int = Field(gt=0)
    date: datetime.date
    ltv: float = Field(default=0.8, gt=0, le=1.5)
    aoci_filter: bool = True
    deposit_beta: float = Field(default=0.35, ge=0, le=1)
    core_deposits: bool = True
    afs: dict[str, float] | None = None


class BankFileRequest(BaseModel):
    """A bank to build from a point-in-time bank file (see ``brms.lab.bank_file``)."""

    bank: dict[str, Any]


class QuitRequest(BaseModel):
    """Stop the lab (sent by the Quit button)."""


@contextlib.contextmanager
def _no_interrupts() -> Iterator[None]:
    """Block Ctrl+C in this thread while it may start worker processes.

    Workers inherit the blocked signal, so a Ctrl+C in the terminal reaches only the server, even
    while a new worker is still importing. Threads the pool starts here inherit it too.
    """
    if not hasattr(signal, "pthread_sigmask"):  # Windows: jobs.ignore_interrupts covers it
        yield
        return
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


class JobManager:
    """Runs jobs in worker processes, one process per job, and records the outcome.

    A worker that dies abruptly (killed for memory, a crash in native code) breaks a process pool
    for good; the next submission replaces the pool with a fresh one from *factory*.
    """

    def __init__(self, factory: Callable[[], Executor]) -> None:
        """Create executors with *factory*."""
        self._factory = factory
        self._executor = factory()
        self._futures: dict[str, Future[Any]] = {}
        self._lock = threading.Lock()
        self._stopping = False

    def submit(
        self, key: str, fn: Callable[..., Any], args: tuple[Any, ...], on_done: Callable[[Future[Any]], None],
    ) -> None:
        """Run ``fn(*args)`` in a worker; call *on_done* with the future when it finishes."""
        with self._lock, _no_interrupts():
            try:
                future = self._executor.submit(fn, *args)
            except BrokenExecutor:
                # Its workers are gone; waiting is quick and avoids Python 3.11's race on the process list.
                self._executor.shutdown(wait=True, cancel_futures=True)
                self._executor = self._factory()
                future = self._executor.submit(fn, *args)
            self._futures[key] = future

        def finished(f: Future[Any]) -> None:
            with self._lock:
                self._futures.pop(key, None)
            on_done(f)

        future.add_done_callback(finished)

    @property
    def stopping(self) -> bool:
        """True once :meth:`shutdown` has begun: jobs ending now were stopped, not failed."""
        return self._stopping

    def running(self) -> int:
        """Return the number of jobs queued or running."""
        with self._lock:
            return len(self._futures)

    def shutdown(self) -> None:
        """Cancel queued jobs, stop running ones, and wait until the workers have gone."""
        self._stopping = True
        with self._lock:
            executor = self._executor
            pending = list(self._futures.values())
        for future in pending:
            future.cancel()  # jobs still queued
        # Stop the running workers (no public API before Python 3.14). The pool sees them die and fails
        # their jobs; shutdown(wait=False) instead races with Python 3.11's pool replacing a worker.
        for process in list((getattr(executor, "_processes", None) or {}).values()):
            process.terminate()
        executor.shutdown(wait=True, cancel_futures=True)


_MAX_ERROR = 2000


_STOPPED = "Stopped: the lab was closed while this was in progress"


def _outcome(future: Future[Any], manager: JobManager) -> BaseException | None:
    """Return the job's exception (None on success); a job ended by closing the lab says so."""
    if future.cancelled():
        return CancelledError(_STOPPED)
    exc = future.exception()
    if exc is not None and manager.stopping:
        return CancelledError(_STOPPED)
    return exc


def _error_text(exc: BaseException) -> str:
    if isinstance(exc, BrokenExecutor):
        return "The worker process stopped unexpectedly (out of memory or a crash); try again or a shorter horizon"
    text = str(exc).strip() or type(exc).__name__
    return text if len(text) < _MAX_ERROR else text[:_MAX_ERROR] + "..."


def _check_stress_dates(request: RunRequest, bank: dict[str, Any]) -> None:
    """Reject stress dates outside the run, and a withdrawal without a date."""
    if request.withdrawal and request.withdrawal_date is None:
        raise HTTPException(400, "A withdrawal needs a withdrawal date")
    if not bank.get("start_date"):
        return
    start = datetime.date.fromisoformat(bank["start_date"])
    end = start + relativedelta(months=request.months) - datetime.timedelta(days=1)
    for key in ("withdrawal_date", "sell_afs_on"):
        day = getattr(request, key)
        if day is not None and not start <= day <= end:
            label = key.replace("_", " ").capitalize()
            raise HTTPException(400, f"{label} {day} is outside the run ({start} to {end})")


def create_app(  # noqa: C901, PLR0915 (one factory registers every route as a closure over its state)
    data_dir: Path | None = None, *, workers: int = 2, executor: Executor | None = None,
    on_quit: Callable[[], None] | None = None,
) -> FastAPI:
    """Return the web application storing its banks and runs under *data_dir*.

    *on_quit* stops the server; without it, ``POST /api/quit`` is not available.
    """
    workspace = Workspace(data_dir or default_data_dir())
    workspace.recover()
    manager = JobManager((lambda: executor) if executor is not None
                         else (lambda: ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=1,
                                                         initializer=jobs.ignore_interrupts)))
    results: OrderedDict[str, RunResult] = OrderedDict()
    results_lock = threading.Lock()
    summarising: set[str] = set()
    summarising_lock = threading.Lock()

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        manager.shutdown()

    app = FastAPI(title="BRMS Stress Lab", version="1", lifespan=lifespan)
    app.state.workspace = workspace
    app.state.jobs = manager

    # -- helpers ---------------------------------------------------------------------------

    def ensure_demo_summary(bank_id: str) -> None:
        with summarising_lock:
            if workspace.bank_summary(bank_id) is not None or workspace.demo_error(bank_id) or bank_id in summarising:
                return
            summarising.add(bank_id)
        zip_path = workspace.bank_zip(bank_id)
        out = workspace.bank_dir(bank_id) / "summary.json"

        def done(f: Future[Any]) -> None:
            exc = _outcome(f, manager)
            if exc is not None and not manager.stopping:  # a stopped summary is retried at the next start
                workspace.set_demo_error(bank_id, _error_text(exc))
            with summarising_lock:
                summarising.discard(bank_id)

        try:
            manager.submit(f"summary:{bank_id}", jobs.summarise_bank, (str(zip_path), str(out)), done)
        except Exception as exc:  # noqa: BLE001 (any failure to start is recorded, not raised into a page poll)
            workspace.set_demo_error(bank_id, _error_text(exc))
            with summarising_lock:
                summarising.discard(bank_id)

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
            exc = _outcome(f, manager)
            if exc is not None:
                workspace.update_bank(meta["id"], status="failed", error=_error_text(exc))
                return
            summary = f.result()
            workspace.update_bank(meta["id"], status="ready", name=summary.get("name", meta["name"]),
                                  start_date=summary.get("start_date"))

        try:
            manager.submit(f"bank:{meta['id']}", fn, (payload, str(folder)), done)
        except Exception as exc:
            workspace.update_bank(meta["id"], status="failed", error=_error_text(exc))
            raise HTTPException(503, f"Could not start the build: {_error_text(exc)}") from exc

    def bank_view(meta: dict[str, Any]) -> dict[str, Any]:
        summary = workspace.bank_summary(meta["id"]) if meta.get("status") in {"ready", "pending"} else None
        if meta["id"].startswith(DEMO_PREFIX) and summary is None:
            ensure_demo_summary(meta["id"])
        view = {**meta}
        if summary:
            sheet = summary["balance_sheet"]
            view.update(status="ready", name=summary["name"], start_date=summary["start_date"],
                        unit=summary.get("unit", 1),
                        end_date=summary["end_date"], total_assets=sheet["total_assets"],
                        total_equity=sheet["total_equity"], story=summary.get("story"),
                        positions=sum(1 for p in summary["positions"] if p["side"] == "LONG" and p["basis"] != "NA"))
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
        if (workspace.bank_meta(bank_id) or {}).get("status") == "building":
            raise HTTPException(409, "The bank is still being built")
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
        spec = request.model_dump(mode="json", exclude={"bank_id"}, exclude_none=True)
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
        _check_stress_dates(request, bank)
        spec = request.model_dump(mode="json", exclude={"bank_id"}, exclude_none=True)
        spec["description"] = jobs.describe(spec)
        meta = workspace.create_run(bank, spec)
        run_id = meta["id"]

        def done(f: Future[Any]) -> None:
            exc = _outcome(f, manager)
            if exc is not None:
                workspace.update_run(run_id, status="failed", error=_error_text(exc), finished=now())
            else:
                workspace.update_run(run_id, status="done", summary=f.result(), finished=now())

        try:
            args = (str(zip_path), spec, str(workspace.run_dir(run_id)))
            manager.submit(f"run:{run_id}", jobs.run_scenario, args, done)
        except Exception as exc:
            workspace.update_run(run_id, status="failed", error=_error_text(exc), finished=now())
            raise HTTPException(503, f"Could not start the run: {_error_text(exc)}") from exc
        return workspace.run_meta(run_id) or meta

    @app.post("/api/quit", status_code=202)
    def quit_lab(_confirm: QuitRequest) -> dict[str, int]:
        # The JSON body makes a browser send a preflight first, so no other web site can stop the lab.
        if on_quit is None:
            raise HTTPException(404, "Quit is available when the lab is started with brms")
        in_progress = manager.running()
        on_quit()
        return {"stopped": in_progress}

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        return workspace.runs()

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        meta = run_or_404(run_id)
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

    @app.get("/api/runs/{run_id}/{table}.csv", response_class=PlainTextResponse)
    def table_csv(run_id: str, table: str) -> PlainTextResponse:
        run_or_404(run_id)
        if table not in {"statements", "journal", "valuations"}:
            raise HTTPException(404, f"No table {table!r}; use statements, journal, valuations or metrics")
        result = load_result(run_id)
        frame = valuations_long(result) if table == "valuations" else getattr(result, table)
        headers = {"Content-Disposition": f'attachment; filename="{run_id}-{table}.csv"'}
        return PlainTextResponse(frame.to_csv(index=False), media_type="text/csv", headers=headers)

    @app.delete("/api/runs/{run_id}", status_code=204)
    def delete_run(run_id: str) -> None:
        meta = run_or_404(run_id)
        if meta.get("status") in {"queued", "running"}:
            raise HTTPException(409, "The run is still in progress")
        with results_lock:
            results.pop(run_id, None)
        workspace.delete_run(run_id)

    # -- front end ---------------------------------------------------------------------------

    @app.middleware("http")
    async def revalidate_front_end(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Browsers must revalidate (ETag, cheap 304) so an upgraded package never runs stale scripts.
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    return app
