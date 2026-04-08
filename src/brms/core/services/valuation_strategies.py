"""Valuation strategy implementations for the strategy-based ValuationService."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from brms.core.enums import ValuationType

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.services.valuation_context import ValuationContext
    from brms.core.stores.instrument_store import InstrumentStore
    from brms.core.stores.valuation_store import ValuationStore


def _face_value(instrument: Instrument) -> Decimal:
    """Safely get face value from an instrument, trying multiple accessors."""
    # Direct attribute (simple instruments like Cash, Deposit)
    fv = getattr(instrument, "face_value", None)
    if fv is not None:
        return Decimal(str(fv))
    # QL-backed instruments store it in the QL object
    ql_inst = getattr(instrument, "ql_instrument", None)
    if ql_inst is not None:
        try:
            return Decimal(str(ql_inst.notional()))
        except Exception:  # noqa: BLE001
            pass
    return Decimal("0")


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


class FairValueStrategy:
    """Values positions at fair value (NPV from QuantLib, or face_value fallback)."""

    def __init__(self) -> None:
        self._engines_set: set[str] = set()  # instrument IDs that have engines

    def value_batch(
        self,
        positions: list[Position],
        instruments: InstrumentStore,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Compute fair value for each position and record it."""
        import QuantLib as ql  # noqa: N813

        for pos in positions:
            inst = instruments.get(pos.instrument_id)
            if inst.ql_instrument is not None:
                # Set pricing engine on first encounter
                if inst.id not in self._engines_set:
                    engine = ql.DiscountingBondEngine(context._yield_handle)  # noqa: SLF001
                    inst.ql_instrument.setPricingEngine(engine)
                    self._engines_set.add(inst.id)
                try:
                    val = Decimal(str(inst.ql_instrument.NPV()))
                except Exception:  # noqa: BLE001
                    val = _face_value(inst)
            else:
                val = _face_value(inst)
            output.record(pos.id, context.date, ValuationType.FAIR_VALUE, val)  # type: ignore[arg-type]


class AmortizedCostStrategy:
    """Values positions at amortized cost (carrying/book value)."""

    def value_batch(
        self,
        positions: list[Position],
        instruments: InstrumentStore,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Record carrying value using face value or QL notional."""
        for pos in positions:
            inst = instruments.get(pos.instrument_id)
            val = _face_value(inst)
            output.record(pos.id, context.date, ValuationType.CARRYING_VALUE, val)  # type: ignore[arg-type]


class OutstandingBalanceStrategy:
    """Values loan positions at their outstanding balance."""

    def value_batch(
        self,
        positions: list[Position],
        instruments: InstrumentStore,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Record outstanding balance as carrying value."""
        for pos in positions:
            inst = instruments.get(pos.instrument_id)
            val = _face_value(inst)
            output.record(pos.id, context.date, ValuationType.CARRYING_VALUE, val)  # type: ignore[arg-type]


def default_valuation_strategies() -> dict:
    """Return the default InstrumentClass → ValuationStrategy mapping."""
    from brms.core.enums import InstrumentClass

    fair_value = FairValueStrategy()
    return {
        InstrumentClass.HTM: AmortizedCostStrategy(),
        InstrumentClass.FVOCI: fair_value,
        InstrumentClass.FVTPL: fair_value,
        InstrumentClass.LOAN_AND_MORTGAGE: OutstandingBalanceStrategy(),
    }
