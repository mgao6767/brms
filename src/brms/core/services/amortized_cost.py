"""AmortizedCostCalculator: clean cost, purchased accrued interest and amortised cost of a position.

One instance belongs to one engine; anything it memoises lives on the instance.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentType
from brms.core.exceptions import ValuationError
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    import datetime

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


LOAN_TYPES: frozenset[InstrumentType] = frozenset({
    InstrumentType.RESIDENTIAL_MORTGAGE,
    InstrumentType.COMMERCIAL_MORTGAGE,
    InstrumentType.MORTGAGE,
    InstrumentType.AMORTIZING_FIXED_RATE_LOAN,
    InstrumentType.VARIABLE_RATE_LOAN,
})


def is_loan(instrument: Instrument) -> bool:
    """Return True for loan instruments (held at outstanding principal)."""
    return getattr(instrument, "instrument_type", None) in LOAN_TYPES


def is_mbs(instrument: Instrument) -> bool:
    """Return True for mortgage-backed securities (pass-throughs)."""
    return getattr(instrument, "instrument_type", None) == InstrumentType.MORTGAGE_BACKED_SECURITY


def repays_on_schedule(instrument: Instrument) -> bool:
    """Return True for instruments repaid in instalments and bought at par: loans and MBS.

    Their amortised cost is clean cost less the scheduled principal received since acquisition.
    """
    return is_loan(instrument) or is_mbs(instrument)


class AmortizedCostCalculator:
    """Computes acquisition-related values and amortised cost of a position.

    Bonds are amortised at the effective interest rate: the yield, compounded at the bond's
    coupon frequency on its own day counter, that prices the remaining cash flows at the
    position's clean cost on the acquisition date. Amortised cost on a date is the clean
    price at that yield, so amortised cost plus accrued interest is the present value of
    the remaining cash flows at the effective rate.
    """

    def __init__(self) -> None:
        """Start with no memoised effective rates."""
        self._rates: dict[str, float] = {}

    def accrued_at_acquisition(self, instrument: Instrument, position: Position) -> Decimal:
        """Return the accrued interest bought with the position (zero without a QuantLib instrument)."""
        ql_inst = getattr(instrument, "ql_instrument", None)
        if ql_inst is None or not hasattr(ql_inst, "accruedAmount"):
            return Decimal(0)
        return scaled_accrued(instrument, position, position.acquisition_date)

    def clean_cost(self, instrument: Instrument, position: Position) -> Decimal:
        """Return the acquisition cost less the accrued interest bought with it."""
        return Decimal(str(position.acquisition_cost)) - self.accrued_at_acquisition(instrument, position)

    def effective_rate(self, instrument: Instrument, position: Position) -> float:
        """Return the effective interest rate of a bond position (memoised per position id)."""
        rate = self._rates.get(position.id)
        if rate is None:
            rate = self._solve_rate(instrument, position)
            self._rates[position.id] = rate
        return rate

    def amortized_cost(self, instrument: Instrument, position: Position, date: datetime.date) -> Decimal:
        """Return the amortised cost of *position* at close of business on *date*.

        Loans and MBS: clean cost less scheduled principal paid after acquisition through *date*.
        Bonds: clean price at the effective rate; face value on and after maturity.
        """
        if repays_on_schedule(instrument):
            _interest, principal, _outstanding = instrument.payment_schedule()  # type: ignore[attr-defined]
            repaid = sum(
                (Decimal(str(a)) for d, a in principal if position.acquisition_date < d <= date), Decimal(0),
            )
            return self.clean_cost(instrument, position) - repaid
        face = Decimal(str(instrument.face_value))  # type: ignore[attr-defined]
        if date >= instrument.maturity_date:  # type: ignore[attr-defined]
            return face
        if date == position.acquisition_date:
            return self.clean_cost(instrument, position)
        bond = instrument.ql_instrument  # type: ignore[attr-defined]
        try:
            price = ql.BondFunctions.cleanPrice(
                bond,
                self.effective_rate(instrument, position),
                bond.dayCounter(),
                ql.Compounded,
                bond.frequency(),
                pydate_to_qldate(date),
            )
        except RuntimeError as exc:
            msg = f"Cannot compute amortised cost for position {position.id} on {date}: {exc}"
            raise ValuationError(msg) from exc
        return Decimal(str(price)) * face / Decimal(100)

    def _solve_rate(self, instrument: Instrument, position: Position) -> float:
        bond = instrument.ql_instrument  # type: ignore[attr-defined]
        face = Decimal(str(instrument.face_value))  # type: ignore[attr-defined]
        clean_price = float(self.clean_cost(instrument, position) / face * Decimal(100))
        try:
            return ql.BondFunctions.bondYield(
                bond,
                ql.BondPrice(clean_price, ql.BondPrice.Clean),
                bond.dayCounter(),
                ql.Compounded,
                bond.frequency(),
                pydate_to_qldate(position.acquisition_date),
                1.0e-12,
                500,
                0.05,
            )
        except RuntimeError as exc:
            msg = f"Cannot solve the effective interest rate for position {position.id}: {exc}"
            raise ValuationError(msg) from exc

