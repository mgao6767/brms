"""Turn a :class:`~brms.lab.runner.RunResult` into the JSON the front end draws.

Series are aligned on the run's market days (``dates``); missing values are ``null``.
"""

from __future__ import annotations

import datetime
import math
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from brms.lab.runner import RunResult

LOAN_TYPES = frozenset({
    "RESIDENTIAL_MORTGAGE", "COMMERCIAL_MORTGAGE", "MORTGAGE", "AMORTIZING_FIXED_RATE_LOAN", "VARIABLE_RATE_LOAN",
})
_SECTIONS = ("assets", "liabilities", "equity")
_HALF_CENT = 0.005
_NOISE = 1e-9


def _clean(value: Any) -> Any:  # noqa: ANN401
    """Return a JSON-safe scalar (NaN and infinities become None)."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp | datetime.date):
        return value.isoformat()[:10]
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if math.isnan(number) or math.isinf(number):
        return None
    # Amounts that cancel to within rounding noise (an emptied receivable at -1e-11) are zero; a
    # negative speck would otherwise be stacked on the wrong side of a chart's axis.
    return 0.0 if abs(number) < _NOISE else number


def _series(frame: pd.DataFrame | pd.Series, index: pd.DatetimeIndex) -> list[Any]:
    return [_clean(v) for v in frame.reindex(index).tolist()]


def book_of(position: dict[str, Any]) -> str | None:
    """Return the unrealised-gain group of a position: loans, htm, afs, or None (not reported)."""
    if position["side"] != "LONG":
        return None
    if position["type"] in LOAN_TYPES:
        return "loans"
    return {"AMORTIZED_COST": "htm", "FVOCI": "afs"}.get(position["basis"])


def unrealised_by_book(result: RunResult, index: pd.DatetimeIndex) -> dict[str, list[Any]]:
    """Fair value less amortised cost, summed per book on each market day (positions held that day)."""
    out: dict[str, list[Any]] = {}
    gap = (result.fair_value - result.amortized_cost).reindex(index)
    for book in ("htm", "afs", "loans"):
        ids = [p["id"] for p in result.positions.to_dict("records") if book_of(p) == book and p["id"] in gap]
        if ids:
            out[book] = _series(gap[ids].sum(axis=1, min_count=1), index)
    return out


def _composition(statements: pd.DataFrame, index: pd.DatetimeIndex) -> dict[str, dict[str, list[Any]]]:
    out: dict[str, dict[str, list[Any]]] = {}
    for section in _SECTIONS:
        rows = statements[statements["section"] == section]
        wide = rows.pivot_table(index="date", columns="account", values="balance", aggfunc="sum")
        wide.index = pd.DatetimeIndex(wide.index)
        wide = wide.loc[:, (wide.abs() > _HALF_CENT).any()]
        out[section] = {account: _series(wide[account], index) for account in wide.columns}
    return out


def _positions_at_end(result: RunResult) -> list[dict[str, Any]]:
    rows = []
    for position in result.positions.to_dict("records"):
        pid = position["id"]

        def last(frame: pd.DataFrame, pid: str = pid) -> tuple[Any, Any]:
            if pid not in frame:
                return None, None
            series = frame[pid].dropna()
            return (None, None) if series.empty else (_clean(series.index[-1]), _clean(series.iloc[-1]))

        carrying_date, carrying = last(result.carrying_value)
        _fair_date, fair = last(result.fair_value)
        _cost_date, amortized = last(result.amortized_cost)
        both = (result.fair_value.get(pid, pd.Series(dtype=float))
                - result.amortized_cost.get(pid, pd.Series(dtype=float))).dropna()
        rows.append({
            **position, "group": book_of(position), "carrying": carrying, "fair": fair, "amortized": amortized,
            "unrealised": _clean(both.iloc[-1]) if not both.empty else None, "as_of": carrying_date,
        })
    return rows


def run_payload(result: RunResult) -> dict[str, Any]:
    """Return the run's charts and tables as JSON-ready data."""
    metrics = result.metrics.copy()
    metrics.index = pd.DatetimeIndex(metrics.index)
    index = metrics.index
    unrealised = unrealised_by_book(result, index)
    summary = {
        **{k: _clean(v) if not isinstance(v, str) else v for k, v in result.summary.items()},
        "unrealised_end": {book: next((v for v in reversed(values) if v is not None), None)
                           for book, values in unrealised.items()},
        "days": len(index),
    }
    yields = result.yields.copy()
    yields.index = pd.DatetimeIndex(yields.index)
    return {
        "summary": summary,
        "dates": [d.date().isoformat() for d in index],
        "metrics": {column: _series(metrics[column], index) for column in metrics.columns},
        "unrealised": unrealised,
        "composition": _composition(result.statements, index),
        "yields": {
            "dates": [d.date().isoformat() for d in yields.index],
            "tenors": list(yields.columns),
            "values": {tenor: [_clean(v) for v in yields[tenor].tolist()] for tenor in yields.columns},
        },
        "positions": _positions_at_end(result),
    }


def day_payload(result: RunResult, day: datetime.date) -> dict[str, Any]:
    """Return statements on the last market day on or before *day*, and the journal and valuations of *day*."""
    statements = result.statements
    days = sorted(statements["date"].unique())
    on = [d for d in days if d <= day]
    statement_day = on[-1] if on else (days[0] if days else None)
    rows = statements[statements["date"] == statement_day]

    def section(name: str) -> list[dict[str, Any]]:
        part = rows[rows["section"] == name]
        return [{"account": a, "balance": _clean(b)} for a, b in zip(part["account"], part["balance"], strict=True)]

    totals = {a: _clean(b) for a, b in zip(rows[rows["section"] == "totals"]["account"],
                                            rows[rows["section"] == "totals"]["balance"], strict=True)}
    journal = result.journal[result.journal["date"] == day]
    names = dict(zip(result.positions["id"], result.positions["name"], strict=True))
    entries = []
    for number, lines in journal.groupby("entry", sort=True):
        first = lines.iloc[0]
        position = first.get("position")
        position = position if isinstance(position, str) else None
        entries.append({
            "entry": int(number), "kind": first["kind"], "description": first["description"],
            "position": position, "instrument": names.get(position) if position else None,
            "lines": [{"account": a, "debit": _clean(d), "credit": _clean(c)}
                      for a, d, c in zip(lines["account"], lines["debit"], lines["credit"], strict=True)],
        })
    stamp = pd.Timestamp(day)
    valuations = []
    for pid in result.positions["id"]:
        def at(frame: pd.DataFrame, pid: str = pid) -> Any:  # noqa: ANN401
            return _clean(frame[pid].get(stamp)) if pid in frame else None

        carrying = at(result.carrying_value)
        if carrying is not None:
            valuations.append({"id": pid, "carrying": carrying, "fair": at(result.fair_value),
                               "amortized": at(result.amortized_cost)})
    return {
        "date": day.isoformat(),
        "statement_date": statement_day.isoformat() if statement_day else None,
        "balance_sheet": {name: section(name) for name in _SECTIONS},
        "income_statement": {"income": section("income"), "expenses": section("expenses")},
        "totals": totals,
        "journal": entries,
        "valuations": valuations,
    }
