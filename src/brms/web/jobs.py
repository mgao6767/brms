"""Work done in worker processes: building banks, summarising them and running scenarios.

Every function here is module-level (picklable), takes plain data and writes its output to disk,
so the server never imports QuantLib state into its own process. The engine is imported inside the
functions: the server imports this module at start, and on a fresh install the first import of
pandas or QuantLib takes many seconds.
"""

from __future__ import annotations

import datetime
import json
import pickle
import signal
from pathlib import Path
from typing import Any

BASEL_LABELS = {
    "parallel_up": "Parallel up (+200bp)",
    "parallel_down": "Parallel down (-200bp)",
    "steepener": "Steepener",
    "flattener": "Flattener",
    "short_up": "Short rates up (+300bp)",
    "short_down": "Short rates down (-300bp)",
}
MAX_MONTHS = 120


def ignore_interrupts() -> None:
    """Worker initialiser: leave Ctrl+C to the server, which stops the workers itself."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


class SpecError(ValueError):
    """A run specification that cannot be run."""


def scenario_from_spec(spec: dict[str, Any]) -> Any:  # noqa: ANN401
    """Return the lab scenario a run specification describes.

    ``kind``: ``historical``; ``basel`` with ``name`` (a key of :data:`BASEL_LABELS`); ``parallel`` with
    ``bp``; ``key_rate`` with ``points`` ``[[t_years, bp], ...]``. Shocks take ``ramp_days``.
    """
    from brms.core.metrics.risk.interest_rate_risk.eve import Scenario
    from brms.lab.scenarios import Historical, KeyRateShift, Shock

    kind = spec.get("kind", "historical")
    ramp = int(spec.get("ramp_days") or 0)
    if ramp < 0:
        msg = "ramp_days must be zero or positive"
        raise SpecError(msg)
    if kind == "historical":
        return Historical()
    if kind == "basel":
        name = spec.get("name")
        if name not in BASEL_LABELS:
            msg = f"Unknown Basel scenario {name!r}; use one of {', '.join(BASEL_LABELS)}"
            raise SpecError(msg)
        return Shock(Scenario[name.upper()], ramp_days=ramp, label=name)
    if kind == "parallel":
        bp = float(spec.get("bp", 0))
        return Shock(KeyRateShift(((0.0, bp),)), ramp_days=ramp, label=f"parallel{bp:+g}bp")
    if kind == "key_rate":
        try:
            points = tuple((float(t), float(bp)) for t, bp in spec.get("points") or ())
            shape = KeyRateShift(points)
        except (TypeError, ValueError) as exc:
            msg = f"Invalid key-rate points: {exc}"
            raise SpecError(msg) from exc
        return Shock(shape, ramp_days=ramp, label="key-rate")
    msg = f"Unknown scenario kind {kind!r}; use historical, basel, parallel or key_rate"
    raise SpecError(msg)


def _date(value: Any) -> datetime.date | None:  # noqa: ANN401
    return None if value in (None, "") else datetime.date.fromisoformat(str(value))


def stress_notes(spec: dict[str, Any]) -> list[str]:
    """Return short notes on a run specification's liquidity stress, for display."""
    notes = []
    if spec.get("deposit_runoff"):
        notes.append(f"deposits run off {float(spec['deposit_runoff']):.0%} a year")
    if spec.get("withdrawal"):
        notes.append(f"{float(spec['withdrawal']):.0%} of deposits withdrawn on {spec.get('withdrawal_date')}")
    if spec.get("sell_afs_on"):
        notes.append(f"AFS book sold on {spec['sell_afs_on']}")
    return notes


def describe(spec: dict[str, Any]) -> str:
    """Return a short human label for a run specification."""
    base = _describe_rates(spec)
    notes = stress_notes(spec)
    return f"{base}; {'; '.join(notes)}" if notes else base


def _describe_rates(spec: dict[str, Any]) -> str:
    kind = spec.get("kind", "historical")
    ramp = int(spec.get("ramp_days") or 0)
    suffix = f", phased in over {ramp} days" if ramp else ""
    if kind == "historical":
        return "Historical rates"
    if kind == "basel":
        return BASEL_LABELS.get(spec.get("name", ""), str(spec.get("name"))) + suffix
    if kind == "parallel":
        return f"Parallel {float(spec.get('bp', 0)):+g}bp{suffix}"
    points = ", ".join(f"{t:g}Y {bp:+g}" for t, bp in spec.get("points") or ())
    return f"Key rates ({points}){suffix}"


# -- bank jobs -------------------------------------------------------------------------------------


def summarise_bank(zip_path: str, out: str, unit: float | None = None) -> dict[str, Any]:
    """Write ``summary.json`` for a simulation zip: dates, balance sheet and positions at the start.

    *unit* is the currency amount one unit of the bank's figures stands for (1000 for a Call
    Report); by default it is read from the zip's ``info`` (1 if absent), as is its ``story``.
    """
    config = _zip_config(zip_path)
    info = config.get("info") or {}
    unit = float(unit if unit is not None else info.get("unit", 1))
    from brms.core.enums import ValuationType
    from brms.core.services import build_core_services

    services = build_core_services(simulation_zip=Path(zip_path))
    sim = services.simulation_service
    snapshot = sim.start_date - datetime.timedelta(days=1)
    store = services.valuation_store
    positions = []
    for position in services.bank.positions.query():
        instrument = services.bank.instruments.get(position.instrument_id)
        kind = getattr(instrument, "instrument_type", None)

        def value(vtype: ValuationType, pid: str = position.id) -> float | None:
            v = store.get(pid, snapshot, vtype)
            return None if v is None else float(v)

        positions.append({
            "id": position.id, "name": instrument.name, "type": kind.name if kind else "",
            "basis": position.measurement_basis.name, "book": position.book_type.name, "side": position.side.name,
            "carrying": value(ValuationType.CARRYING_VALUE), "fair": value(ValuationType.FAIR_VALUE),
            "amortized": value(ValuationType.AMORTIZED_COST), "accrued": value(ValuationType.ACCRUED_INTEREST),
            "maturity": str(getattr(instrument, "maturity_date", "") or ""),
        })
    regulatory = services.bank.regulatory
    summary = {
        "name": str(config.get("name") or Path(zip_path).stem),
        "unit": unit,
        "story": info.get("story"),
        "reported": info.get("reported"),
        "start_date": sim.start_date.isoformat(),
        "end_date": sim.end_date.isoformat() if sim.end_date else None,
        "balance_sheet": services.reporting_service.balance_sheet(services.bank.ledger, date=snapshot),
        "positions": positions,
        "regulatory": {"aoci_filter": regulatory.aoci_filter, "operational_rwa": float(regulatory.operational_rwa)},
        "operating": services.bank.operating.to_json(),
    }
    summary["first_day"] = _first_market_day(services)
    _atomic_write(Path(out), json.dumps(summary, default=str))
    return summary


def _first_market_day(services: Any) -> dict[str, Any] | None:  # noqa: ANN401
    """Advance to the first market day and return its headline figures (after the first fair-value marks).

    The snapshot holds AFS securities at cost on the as-of date; their fair value, and so equity as
    reported, appears with the first mark. This is what to compare with a filing.
    """
    from brms.core.enums import MetricName

    sim = services.simulation_service
    for _ in range(10):
        sim.advance()
        day = sim.current_date
        if services.metric_store.get(MetricName.TOTAL_ASSETS, day) is None:
            continue

        def metric(name: MetricName, day: Any = day) -> float | None:  # noqa: ANN401
            value = services.metric_store.get(name, day)
            return None if value is None else float(value)

        return {
            "date": day.isoformat(), "total_assets": metric(MetricName.TOTAL_ASSETS),
            "total_equity": metric(MetricName.TOTAL_EQUITY), "cet1_capital": metric(MetricName.CET1_CAPITAL),
            "total_rwa": metric(MetricName.TOTAL_RWA), "cet1_ratio": metric(MetricName.CET1_RATIO),
            "leverage_ratio": metric(MetricName.LEVERAGE_RATIO),
        }
    return None


def _atomic_write(path: Path, text: str) -> None:
    """Write *text* so that a concurrent reader sees the old file or the new one, never half of it."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def _zip_config(zip_path: str) -> dict[str, Any]:
    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        return json.loads(archive.read("config.json"))


def build_from_bank_file(bank: dict[str, Any], folder: str) -> dict[str, Any]:
    """Build ``bank.zip`` from a bank file and summarise it (with the file's ``unit``, default 1)."""
    from brms.lab.bank_file import build_bank, default_market_frames

    out = Path(folder)
    (out / "bank.json").write_text(json.dumps(bank, indent=1))
    build_bank(out / "bank.json", default_market_frames(), out / "bank.zip")
    return summarise_bank(str(out / "bank.zip"), str(out / "summary.json"), unit=float(bank.get("unit") or 1))


def build_from_call_report(request: dict[str, Any], folder: str) -> dict[str, Any]:
    """Fetch a Call Report, turn it into a bank file, build and summarise it."""
    from brms.lab.bank_file import default_market_frames, prime_on
    from brms.lab.call_report import bank_file_from_call_report, fetch_call_report

    items = fetch_call_report(int(request["cert"]), request["date"])
    as_of = datetime.datetime.strptime(str(items["REPDTE"]), "%Y%m%d").date()  # noqa: DTZ007
    bank = bank_file_from_call_report(
        items, prime=prime_on(default_market_frames(), as_of), ltv=float(request.get("ltv", 0.8)),
        aoci_filter=bool(request.get("aoci_filter", True)), afs=request.get("afs") or None,
        deposit_beta=float(request.get("deposit_beta", 0.35)),
        core_deposits=bool(request.get("core_deposits", True)),
    )
    return build_from_bank_file(bank, folder)


# -- runs --------------------------------------------------------------------------------------------


def _mark_running(folder: Path) -> None:
    """Record in the run's metadata that a worker has started it (the server records the outcome)."""
    path = folder / "meta.json"
    try:
        meta = json.loads(path.read_text())
    except (OSError, ValueError):
        return
    if meta.get("status") == "queued":
        meta["status"] = "running"
        _atomic_write(path, json.dumps(meta, indent=1, default=str))


def run_scenario(zip_path: str, spec: dict[str, Any], folder: str) -> dict[str, Any]:
    """Run a scenario; write ``result.pkl`` and ``payload.json``; return the run summary."""
    _mark_running(Path(folder))
    import dataclasses

    from brms.lab.runner import run
    from brms.web.payloads import run_payload

    scenario = scenario_from_spec(spec)
    regulatory = None
    if spec.get("aoci_filter") is not None:
        from brms.core.services import build_core_services

        current = build_core_services(simulation_zip=Path(zip_path)).bank.regulatory
        regulatory = dataclasses.replace(current, aoci_filter=bool(spec["aoci_filter"]))
    from brms.lab.runner import DepositStress

    stress = None
    if spec.get("deposit_runoff") or spec.get("withdrawal"):
        stress = DepositStress(
            runoff_rate=float(spec.get("deposit_runoff") or 0), withdrawal=float(spec.get("withdrawal") or 0),
            withdrawal_date=_date(spec.get("withdrawal_date")),
        )
    result = run(Path(zip_path), scenario, months=int(spec.get("months") or 12), regulatory=regulatory,
                 reinvest_maturities=bool(spec.get("reinvest")), deposit_stress=stress,
                 sell_afs_on=_date(spec.get("sell_afs_on")))
    out = Path(folder)
    with (out / "result.pkl").open("wb") as handle:
        pickle.dump(result, handle, protocol=pickle.HIGHEST_PROTOCOL)
    payload = run_payload(result)
    _atomic_write(out / "payload.json", json.dumps(payload, allow_nan=False, default=str))
    return payload["summary"]
