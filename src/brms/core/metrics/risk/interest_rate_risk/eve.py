"""Economic value of equity under the Basel standardised interest-rate shocks (SRP31).

Each open long bond or loan position is revalued by discounting its remaining cash flows on the
day's curve shifted by the scenario's zero-rate shock. Floating-rate coupons are forecast from the
engine's shared forwarding handle, which is relinked to the shocked curve for the scenario and
restored afterwards. Only banking-book positions count (SRP31). Cash, deposits and interest
payable count at book value: deposits are treated as repricing overnight, so they carry no
duration, which makes rising-rate scenarios look worse than a behavioural deposit model would.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.enums import BookType, MeasurementBasis, PositionSide
from brms.core.exceptions import ValuationError
from brms.core.services.spreads import spreaded_handle
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    import datetime
    from collections.abc import Callable

    from brms.core.models.bank import Bank

_PARALLEL, _SHORT, _LONG = 200.0, 300.0, 150.0  # USD shock sizes in bp (SRP31.90 Annex)
_DECAY_YEARS = 4.0
_NODES = (0.0, 1 / 12, 0.25, 0.5, *range(1, 21), 25.0, 30.0, 40.0)
_BP = 1e-4


class Scenario(Enum):
    """The six standardised interest-rate shock scenarios."""

    PARALLEL_UP = auto()
    PARALLEL_DOWN = auto()
    STEEPENER = auto()
    FLATTENER = auto()
    SHORT_UP = auto()
    SHORT_DOWN = auto()


def _short(t: float) -> float:
    return _SHORT * math.exp(-t / _DECAY_YEARS)


def _long(t: float) -> float:
    return _LONG * (1 - math.exp(-t / _DECAY_YEARS))


_SHAPES: dict[Scenario, Callable[[float], float]] = {
    Scenario.PARALLEL_UP: lambda _t: _PARALLEL,
    Scenario.PARALLEL_DOWN: lambda _t: -_PARALLEL,
    Scenario.SHORT_UP: _short,
    Scenario.SHORT_DOWN: lambda t: -_short(t),
    Scenario.STEEPENER: lambda t: -0.65 * _short(t) + 0.9 * _long(t),
    Scenario.FLATTENER: lambda t: 0.8 * _short(t) - 0.6 * _long(t),
}


def shock_bp(scenario: Scenario, t: float) -> float:
    """Return the scenario's zero-rate shift in basis points at maturity *t* years."""
    return _SHAPES[scenario](t)


@dataclass(frozen=True)
class EVEResult:
    """EVE on the base curve and under each scenario, with per-position present values."""

    base: Decimal
    by_scenario: dict[Scenario, Decimal]
    base_position_pv: dict[str, Decimal]
    scenario_position_pv: dict[Scenario, dict[str, Decimal]]
    duration: float

    def delta(self, scenario: Scenario) -> Decimal:
        """ΔEVE under *scenario*."""
        return self.by_scenario[scenario] - self.base

    def position_delta(self, scenario: Scenario, position_id: str) -> Decimal:
        """ΔPV of one position under *scenario*."""
        return self.scenario_position_pv[scenario][position_id] - self.base_position_pv[position_id]

    @property
    def worst_delta(self) -> Decimal:
        """The most negative ΔEVE across the six scenarios."""
        return min(self.delta(s) for s in Scenario)


def _spreaded(
    base: ql.YieldTermStructureHandle, date: ql.Date, shift: Callable[[float], float],
) -> ql.YieldTermStructure:
    dates = [date + ql.Period(round(t * 365), ql.Days) for t in _NODES]
    quotes = [ql.QuoteHandle(ql.SimpleQuote(shift(t))) for t in _NODES]
    curve = ql.PiecewiseZeroSpreadedTermStructure(base, quotes, dates)
    curve.enableExtrapolation()
    return curve


def eve_scenarios(bank: Bank, yield_handle: ql.RelinkableYieldTermStructureHandle, date: datetime.date) -> EVEResult:
    """Revalue the bank under the base curve, the six shocks and ±1bp, on *date*.

    *yield_handle* is the engine's shared discount and forwarding handle, linked to the day's
    curve. It is relinked for each scenario and restored before returning.
    """
    try:
        base_curve = yield_handle.currentLink()
    except RuntimeError as exc:
        msg = f"No discount curve is linked on {date}; EVE needs a market-data day"
        raise ValuationError(msg) from exc
    base = ql.YieldTermStructureHandle(base_curve)
    qd = pydate_to_qldate(date)
    legs = _position_legs(bank)
    spreads = {p.id: p.spread for p in bank.positions.open_positions() if p.spread is not None}
    other = _cash_less_deposits(bank)

    def revalue(shift: Callable[[float], float] | None) -> dict[str, Decimal]:
        curve = base_curve if shift is None else _spreaded(base, qd, shift)
        yield_handle.linkTo(curve)
        discount = ql.YieldTermStructureHandle(curve)
        values = {}
        for position_id, leg in legs.items():
            spread = spreads.get(position_id)
            handle = discount if spread is None else spreaded_handle(discount, spread)
            try:
                values[position_id] = Decimal(str(ql.CashFlows.npv(leg(), handle, False, qd, qd)))  # noqa: FBT003
            except RuntimeError as exc:
                msg = f"Cannot revalue position {position_id} on {date}: {exc}"
                raise ValuationError(msg) from exc
        return values

    try:
        base_pv = revalue(None)
        scenario_pv = {s: revalue(lambda t, s=s: shock_bp(s, t) * _BP) for s in Scenario}
        up = revalue(lambda _t: _BP)
        down = revalue(lambda _t: -_BP)
    finally:
        yield_handle.linkTo(base_curve)

    total = sum(base_pv.values(), Decimal(0))
    duration = 0.0 if total == 0 else float(
        (sum(down.values(), Decimal(0)) - sum(up.values(), Decimal(0))) / (2 * total * Decimal(str(_BP))),
    )
    return EVEResult(
        base=total + other,
        by_scenario={s: sum(pv.values(), Decimal(0)) + other for s, pv in scenario_pv.items()},
        base_position_pv=base_pv,
        scenario_position_pv=scenario_pv,
        duration=duration,
    )


def _position_legs(bank: Bank) -> dict[str, Callable[[], object]]:
    """Return a cash-flow leg getter per open long bond or loan position (re-read per scenario)."""
    legs: dict[str, Callable[[], object]] = {}
    for position in bank.positions.open_positions():
        if position.side != PositionSide.LONG or position.measurement_basis == MeasurementBasis.NA:
            continue
        if position.book_type != BookType.BANKING:
            continue  # IRRBB covers the banking book (SRP31)
        instrument = bank.instruments.get(position.instrument_id)
        legs[position.id] = instrument.ql_instrument.cashflows  # type: ignore[attr-defined]
    return legs


def _cash_less_deposits(bank: Bank) -> Decimal:
    """Cash less deposits and interest payable, at book value (treated as repricing overnight)."""
    accounts = {a.name: Decimal(str(a.balance())) for a in bank.ledger.chart_of_accounts.all_accounts()}
    return accounts["Cash and Cash Equivalents"] - accounts["Deposits"] - accounts["Interest Payable"]
