"""Work done in worker processes: building banks, summarising them and running scenarios.

Every function here is module-level (picklable), takes plain data and writes its output to disk,
so the server never imports QuantLib state into its own process.
"""

from __future__ import annotations

import datetime
import json
import pickle
from pathlib import Path
from typing import Any

from brms.core.metrics.risk.interest_rate_risk.eve import Scenario

BASEL = {
    "parallel_up": Scenario.PARALLEL_UP,
    "parallel_down": Scenario.PARALLEL_DOWN,
    "steepener": Scenario.STEEPENER,
    "flattener": Scenario.FLATTENER,
    "short_up": Scenario.SHORT_UP,
    "short_down": Scenario.SHORT_DOWN,
}
BASEL_LABELS = {
    "parallel_up": "Parallel up (+200bp)",
    "parallel_down": "Parallel down (-200bp)",
    "steepener": "Steepener",
    "flattener": "Flattener",
    "short_up": "Short rates up (+300bp)",
    "short_down": "Short rates down (-300bp)",
}
MAX_MONTHS = 120


class SpecError(ValueError):
    """A run specification that cannot be run."""


def scenario_from_spec(spec: dict[str, Any]) -> Any:  # noqa: ANN401
    """Return the lab scenario a run specification describes.

    ``kind``: ``historical``; ``basel`` with ``name`` (a key of :data:`BASEL`); ``parallel`` with
    ``bp``; ``key_rate`` with ``points`` ``[[t_years, bp], ...]``. Shocks take ``ramp_days``.
    """
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
        if name not in BASEL:
            msg = f"Unknown Basel scenario {name!r}; use one of {', '.join(BASEL)}"
            raise SpecError(msg)
        return Shock(BASEL[name], ramp_days=ramp, label=name)
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


def describe(spec: dict[str, Any]) -> str:
    """Return a short human label for a run specification."""
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


def summarise_bank(zip_path: str, out: str, unit: float = 1.0) -> dict[str, Any]:
    """Write ``summary.json`` for a simulation zip: dates, balance sheet and positions at the start.

    *unit* is the currency amount one unit of the bank's figures stands for (1000 for a Call Report).
    """
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
        "name": _zip_name(zip_path),
        "unit": unit,
        "start_date": sim.start_date.isoformat(),
        "end_date": sim.end_date.isoformat() if sim.end_date else None,
        "balance_sheet": services.reporting_service.balance_sheet(services.bank.ledger, date=snapshot),
        "positions": positions,
        "regulatory": {"aoci_filter": regulatory.aoci_filter, "operational_rwa": float(regulatory.operational_rwa)},
    }
    Path(out).write_text(json.dumps(summary, default=str))
    return summary


def _zip_name(zip_path: str) -> str:
    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        config = json.loads(archive.read("config.json"))
    return str(config.get("name") or Path(zip_path).stem)


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
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(meta, indent=1, default=str))
        tmp.replace(path)


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
    result = run(Path(zip_path), scenario, months=int(spec.get("months") or 12), regulatory=regulatory,
                 reinvest_maturities=bool(spec.get("reinvest")))
    out = Path(folder)
    with (out / "result.pkl").open("wb") as handle:
        pickle.dump(result, handle, protocol=pickle.HIGHEST_PROTOCOL)
    payload = run_payload(result)
    (out / "payload.json").write_text(json.dumps(payload, allow_nan=False, default=str))
    return payload["summary"]
