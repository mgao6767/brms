"""AmortizedCostCalculator: clean cost, purchased accrued interest and amortised cost of a position.

One instance belongs to one engine; anything it memoises lives on the instance.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.exceptions import ValuationError
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position


def scaled_accrued(instrument: Instrument, position: Position, date: object) -> Decimal:
    """Return the accrued interest of *instrument* on *date* in currency, naming *position* on failure."""
    from brms.core.rules.interest_accrual import scaled_accrued_amount

    try:
        return scaled_accrued_amount(instrument.ql_instrument, pydate_to_qldate(date))  # type: ignore[arg-type]
    except RuntimeError as exc:
        msg = f"Cannot compute accrued interest for position {position.id} on {date}: {exc}"
        raise ValuationError(msg) from exc


class AmortizedCostCalculator:
    """Computes acquisition-related values of a position."""

    def accrued_at_acquisition(self, instrument: Instrument, position: Position) -> Decimal:
        """Return the accrued interest bought with the position (zero without a QuantLib instrument)."""
        ql_inst = getattr(instrument, "ql_instrument", None)
        if ql_inst is None or not hasattr(ql_inst, "accruedAmount"):
            return Decimal(0)
        return scaled_accrued(instrument, position, position.acquisition_date)

    def clean_cost(self, instrument: Instrument, position: Position) -> Decimal:
        """Return the acquisition cost less the accrued interest bought with it."""
        return Decimal(str(position.acquisition_cost)) - self.accrued_at_acquisition(instrument, position)
