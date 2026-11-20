"""Per-position credit spreads over the discount curve.

A spread is a constant continuously compounded zero-rate spread (a decimal, 0.01 = 100bp) added to
the day's curve when valuing one position. Calibrating it on the acquisition (or as-of) date to the
price actually paid isolates rate risk: from then on, fair value moves only with the curve, and
non-Treasury bonds and loans no longer jump on their first mark.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.exceptions import ValuationError
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    import datetime

_LOW, _HIGH = -0.5, 2.0  # spread search interval (decimal)
_TOLERANCE = 1e-12
_MAX_ITERATIONS = 200


def spreaded_handle(base: ql.YieldTermStructureHandle, spread: Decimal | float) -> ql.YieldTermStructureHandle:
    """Return a handle to *base* shifted by a constant continuous zero-rate *spread*."""
    curve = ql.ZeroSpreadedTermStructure(base, ql.QuoteHandle(ql.SimpleQuote(float(spread))))
    curve.enableExtrapolation()
    return ql.YieldTermStructureHandle(curve)


def dirty_value(leg: object, handle: ql.YieldTermStructureHandle, date: datetime.date) -> float:
    """Present value on *date* of the cash flows of *leg* paid after *date*."""
    qd = pydate_to_qldate(date)
    return ql.CashFlows.npv(leg, handle, False, qd, qd)  # noqa: FBT003


def calibrate_spread(
    leg: object, base: ql.YieldTermStructureHandle, date: datetime.date, target_dirty: Decimal,
) -> Decimal:
    """Return the spread at which *leg* is worth *target_dirty* on *date* (bisection on PV).

    Raises:
        ValuationError: no spread in [-50%, 200%] reprices the leg to the target.

    """
    quote = ql.SimpleQuote(0.0)
    curve = ql.ZeroSpreadedTermStructure(base, ql.QuoteHandle(quote))
    curve.enableExtrapolation()
    handle = ql.YieldTermStructureHandle(curve)
    target = float(target_dirty)

    def excess(spread: float) -> float:
        quote.setValue(spread)
        return dirty_value(leg, handle, date) - target

    low, high = _LOW, _HIGH
    f_low = excess(low)
    if f_low * excess(high) > 0:
        msg = f"No spread in [{_LOW:.0%}, {_HIGH:.0%}] prices the cash flows at {target:,.2f} on {date}"
        raise ValuationError(msg)
    for _ in range(_MAX_ITERATIONS):
        mid = (low + high) / 2
        f_mid = excess(mid)
        if abs(f_mid) <= _TOLERANCE * max(1.0, abs(target)) or high - low < _TOLERANCE:
            return Decimal(str(mid))
        if (f_mid > 0) == (f_low > 0):
            low, f_low = mid, f_mid
        else:
            high = mid
    return Decimal(str((low + high) / 2))
