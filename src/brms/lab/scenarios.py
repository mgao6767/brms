"""Rate scenarios: each produces the market frames (yields, Prime) the engine consumes.

History before the scenario's start date is kept unchanged, so curves and fixings up to the
start date are real; from the start date on, every business day through the end date is supplied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from brms.core.metrics.risk.interest_rate_risk.eve import Scenario, shock_bp

if TYPE_CHECKING:
    import datetime
    from collections.abc import Callable

    from brms.core.models.market_data import MarketDataStore

_PRIME_TENOR_YEARS = 0.25  # Prime moves with the 3-month point of the shock
_PERCENT_PER_BP = 0.01


def tenor_years(label: str) -> float:
    """Return the maturity in years of a CMT column label such as ``"3 Mo"`` or ``"10 Yr"``."""
    match = re.fullmatch(r"(\d+)\s*(Mo|Yr)", label.strip())
    if match is None:
        msg = f"Unknown tenor label {label!r}"
        raise ValueError(msg)
    number = int(match[1])
    return number / 12 if match[2] == "Mo" else float(number)


@dataclass(frozen=True)
class Historical:
    """Replay the stored market data."""

    name: str = "historical"

    def frames(self, market_data: MarketDataStore, start: datetime.date, end: datetime.date) -> dict[str, pd.DataFrame]:  # noqa: ARG002
        """Return the stored frames unchanged."""
        return {name: market_data.get_frame(name) for name in market_data.frame_names()}


@dataclass(frozen=True)
class Shock:
    """Shift the base day's curve by *shape* from the start date, optionally ramping in.

    *shape* is a Basel :class:`Scenario` or a callable ``t_years -> bp``. Shifts apply to the CMT
    par yields by tenor, an approximation to a zero-rate shift. With ``ramp_days`` the shift grows
    linearly from zero at the start date to full size ``ramp_days`` later. ``floor`` (in percent)
    bounds shocked yields from below; by default yields may go negative.
    """

    shape: Scenario | Callable[[float], float]
    ramp_days: int = 0
    floor: float | None = None
    label: str | None = field(default=None, compare=False)

    @property
    def name(self) -> str:
        """Scenario name used in results and output folders."""
        if self.label is not None:
            return self.label
        return self.shape.name.lower() if isinstance(self.shape, Scenario) else "custom"

    def _shift_bp(self, t: float) -> float:
        if isinstance(self.shape, Scenario):
            return shock_bp(self.shape, t)
        return self.shape(t)

    def _ramp(self, day: pd.Timestamp, start: pd.Timestamp) -> float:
        if self.ramp_days <= 0:
            return 1.0
        return min(1.0, (day - start).days / self.ramp_days)

    def frames(self, market_data: MarketDataStore, start: datetime.date, end: datetime.date) -> dict[str, pd.DataFrame]:
        """Return history before *start* plus the shocked business days from *start* to *end*."""
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        frames: dict[str, pd.DataFrame] = {}
        yields = market_data.get_frame("yields")
        base = yields.loc[:start_ts].iloc[-1]
        days = pd.bdate_range(start_ts, end_ts, name="date")
        shifts = {label: self._shift_bp(tenor_years(label)) * _PERCENT_PER_BP for label in yields.columns}
        rows = [base + pd.Series(shifts) * self._ramp(day, start_ts) for day in days]
        path = pd.DataFrame(rows, index=days)[list(yields.columns)]
        if self.floor is not None:
            path = path.clip(lower=self.floor)
        frames["yields"] = pd.concat([yields.loc[: start_ts - pd.Timedelta(days=1)], path])
        if market_data.has_frame("benchmarks"):
            prime = market_data.get_frame("benchmarks")
            base_prime = prime.loc[:start_ts].iloc[-1]
            calendar = pd.date_range(start_ts, end_ts, name="date")
            shift = self._shift_bp(_PRIME_TENOR_YEARS) * _PERCENT_PER_BP
            prime_rows = [base_prime + shift * self._ramp(day, start_ts) for day in calendar]
            prime_path = pd.DataFrame(prime_rows, index=calendar)[list(prime.columns)]
            frames["benchmarks"] = pd.concat([prime.loc[: start_ts - pd.Timedelta(days=1)], prime_path])
        return frames


_NAMED = {
    "parallel+200": Scenario.PARALLEL_UP,
    "parallel-200": Scenario.PARALLEL_DOWN,
    "steepener": Scenario.STEEPENER,
    "flattener": Scenario.FLATTENER,
    "short+300": Scenario.SHORT_UP,
    "short-300": Scenario.SHORT_DOWN,
}


def _constant(bp: float) -> Callable[[float], float]:
    def shape(_t: float) -> float:
        return bp

    return shape


def parse_scenario(text: str) -> Historical | Shock:
    """Parse a CLI scenario name: ``historical``, a Basel name, or ``parallel+<bp>`` / ``parallel-<bp>``."""
    key = text.strip().lower()
    if key == "historical":
        return Historical()
    if key in _NAMED:
        return Shock(_NAMED[key])
    match = re.fullmatch(r"parallel([+-]\d+(?:\.\d+)?)", key)
    if match:
        bp = float(match[1])
        return Shock(_constant(bp), label=f"parallel{match[1]}bp")
    msg = f"Unknown scenario {text!r}; use historical, {', '.join(_NAMED)}, or parallel+<bp>"
    raise ValueError(msg)
