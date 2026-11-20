"""Valuation strategies: record the per-position values the ledger is reconciled against.

For every open bond or loan position, on every calendar day from its acquisition date:

* ``ACCRUED_INTEREST`` — coupon interest earned since the last coupon date (currency).
* ``AMORTIZED_COST`` — clean acquisition cost rolled forward at the effective interest rate
  (bonds) or clean cost less scheduled principal (loans). Not recorded for FVTPL positions.
* ``FAIR_VALUE`` — clean fair value: NPV on the day's curve less accrued interest. Bonds
  only, on market-data days and on and after the maturity date (where it is face value).
* ``CARRYING_VALUE`` — what the investment or loan account holds for the position.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, ValuationType
from brms.core.exceptions import ValuationError
from brms.core.services.amortized_cost import is_loan, scaled_accrued
from brms.core.services.spreads import dirty_value, spreaded_handle

if TYPE_CHECKING:
    import datetime

    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.services.amortized_cost import AmortizedCostCalculator
    from brms.core.services.valuation_context import ValuationContext
    from brms.core.stores.instrument_store import InstrumentStore
    from brms.core.stores.valuation_store import ValuationStore


@runtime_checkable
class ValuationStrategy(Protocol):
    """Protocol that all valuation strategies must satisfy."""

    def value_batch(
        self,
        positions: list[Position],
        instruments: InstrumentStore,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Value *positions* in bulk and record results into *output*."""
        ...


def _has_ql(instrument: Instrument) -> bool:
    ql_inst = getattr(instrument, "ql_instrument", None)
    return ql_inst is not None and hasattr(ql_inst, "accruedAmount")


class _BaseStrategy:
    """Shared machinery: accrued interest and clean fair value."""

    def __init__(self, calculator: AmortizedCostCalculator) -> None:
        self._calculator = calculator
        self._engines_set: set[str] = set()
        self._spread_handles: dict[str, tuple[Decimal, ql.YieldTermStructureHandle]] = {}

    def _spread_handle(self, pos: Position, context: ValuationContext) -> ql.YieldTermStructureHandle:
        cached = self._spread_handles.get(pos.id)
        if cached is None or cached[0] != pos.spread:
            cached = (pos.spread, spreaded_handle(context.yield_handle, pos.spread))  # type: ignore[arg-type]
            self._spread_handles[pos.id] = cached
        return cached[1]

    def _fair_value(
        self, inst: Instrument, pos: Position, context: ValuationContext, accrued: Decimal,
    ) -> Decimal | None:
        """Return the clean fair value, or None when it is not defined today.

        Positions with a credit spread are discounted on the curve plus that spread (loans get a
        fair value only then); others are priced on the curve itself (bonds only).
        """
        if is_loan(inst) and pos.spread is None:
            return None
        date = context.date
        if not is_loan(inst) and date >= inst.maturity_date:  # type: ignore[attr-defined]
            return Decimal(str(inst.face_value))  # type: ignore[attr-defined]
        if not context.has_market_data:
            return None
        if pos.spread is not None:
            try:
                dirty = dirty_value(inst.ql_instrument.cashflows(), self._spread_handle(pos, context), date)  # type: ignore[attr-defined]
            except RuntimeError as exc:
                msg = f"Cannot price position {pos.id} on {date}: {exc}"
                raise ValuationError(msg) from exc
            return Decimal(str(dirty)) - accrued
        if inst.id not in self._engines_set:
            engine = ql.DiscountingBondEngine(context.yield_handle)
            inst.ql_instrument.setPricingEngine(engine)  # type: ignore[attr-defined]
            self._engines_set.add(inst.id)
        try:
            npv = Decimal(str(inst.ql_instrument.NPV()))  # type: ignore[attr-defined]
        except RuntimeError as exc:
            msg = f"Cannot price position {pos.id} on {date}: {exc}"
            raise ValuationError(msg) from exc
        return npv - accrued


class CarryingValueStrategy(_BaseStrategy):
    """Amortised-cost positions: carrying value is amortised cost; bonds also get a fair value."""

    def value_batch(
        self,
        positions: list[Position],
        instruments: InstrumentStore,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Record accrued interest, amortised cost, fair value and carrying value."""
        date = context.date
        for pos in positions:
            inst = instruments.get(pos.instrument_id)
            if not _has_ql(inst):
                msg = f"Position {pos.id} ({pos.measurement_basis.name}) has no QuantLib instrument to value"
                raise ValuationError(msg)
            accrued = scaled_accrued(inst, pos, date)
            amortized = self._calculator.amortized_cost(inst, pos, date)
            output.record(pos.id, date, ValuationType.ACCRUED_INTEREST, accrued)
            output.record(pos.id, date, ValuationType.AMORTIZED_COST, amortized)
            output.record(pos.id, date, ValuationType.CARRYING_VALUE, amortized)
            fair = self._fair_value(inst, pos, context, accrued)
            if fair is not None:
                output.record(pos.id, date, ValuationType.FAIR_VALUE, fair)


class FairValueStrategy(_BaseStrategy):
    """FVOCI and FVTPL positions: carrying value follows clean fair value."""

    def value_batch(
        self,
        positions: list[Position],
        instruments: InstrumentStore,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Record accrued interest, amortised cost (FVOCI), fair value and carrying value."""
        date = context.date
        for pos in positions:
            inst = instruments.get(pos.instrument_id)
            if not _has_ql(inst):
                msg = f"Position {pos.id} ({pos.measurement_basis.name}) has no QuantLib instrument to value"
                raise ValuationError(msg)
            accrued = scaled_accrued(inst, pos, date)
            output.record(pos.id, date, ValuationType.ACCRUED_INTEREST, accrued)
            amortized: Decimal | None = None
            if pos.measurement_basis == MeasurementBasis.FVOCI:
                amortized = self._calculator.amortized_cost(inst, pos, date)
                output.record(pos.id, date, ValuationType.AMORTIZED_COST, amortized)
            fair = self._fair_value(inst, pos, context, accrued)
            if fair is not None:
                output.record(pos.id, date, ValuationType.FAIR_VALUE, fair)
            carrying = self._carrying(inst, pos, date, fair, amortized, output)
            output.record(pos.id, date, ValuationType.CARRYING_VALUE, carrying)

    def _carrying(  # noqa: PLR0913
        self,
        inst: Instrument,
        pos: Position,
        date: datetime.date,
        fair: Decimal | None,
        amortized: Decimal | None,
        output: ValuationStore,
    ) -> Decimal:
        if date == pos.acquisition_date:
            return self._calculator.clean_cost(inst, pos)
        if fair is not None:
            return fair
        previous = output.get_previous(pos.id, date, ValuationType.CARRYING_VALUE)
        if previous is None:
            msg = f"Position {pos.id} has no carrying value before {date}"
            raise ValuationError(msg)
        if amortized is None:  # FVTPL: unchanged until the next mark
            return previous
        previous_amortized = output.get_previous(pos.id, date, ValuationType.AMORTIZED_COST)
        if previous_amortized is None:
            msg = f"Position {pos.id} has no amortised cost before {date}"
            raise ValuationError(msg)
        return previous + (amortized - previous_amortized)


def default_valuation_strategies(calculator: AmortizedCostCalculator) -> dict[MeasurementBasis, ValuationStrategy]:
    """Return the default MeasurementBasis → ValuationStrategy mapping."""
    fair_value = FairValueStrategy(calculator)
    return {
        MeasurementBasis.AMORTIZED_COST: CarryingValueStrategy(calculator),
        MeasurementBasis.FVOCI: fair_value,
        MeasurementBasis.FVTPL: fair_value,
    }
