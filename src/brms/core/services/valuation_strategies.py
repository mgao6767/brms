"""Valuation strategy implementations for the strategy-based ValuationService."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from brms.core.enums import ValuationType

if TYPE_CHECKING:
    from brms.core.services.valuation_context import ValuationContext
    from brms.core.stores.valuation_store import ValuationStore


@runtime_checkable
class ValuationStrategy(Protocol):
    """Protocol that all valuation strategies must satisfy."""

    def value_batch(
        self,
        positions: list[object],
        instruments: object,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Value *positions* in bulk and record results into *output*."""
        ...


class FairValueStrategy:
    """Values positions at fair value (NPV from QuantLib, or face_value fallback)."""

    def value_batch(
        self,
        positions: list[object],
        instruments: object,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Compute fair value for each position and record it as FAIR_VALUE."""
        for pos in positions:
            inst = instruments.get(pos.instrument_id)  # type: ignore[union-attr]
            if inst.ql_instrument is not None:
                val = Decimal(str(inst.ql_instrument.NPV()))
            else:
                val = Decimal(str(inst.face_value))
            output.record(pos.id, context.date, ValuationType.FAIR_VALUE, val)  # type: ignore[arg-type]


class AmortizedCostStrategy:
    """Values positions at amortized cost, recording the carrying (book) value."""

    def value_batch(
        self,
        positions: list[object],
        instruments: object,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Record the carrying value for each position using face_value as the amortized cost proxy."""
        for pos in positions:
            inst = instruments.get(pos.instrument_id)  # type: ignore[union-attr]
            val = Decimal(str(inst.face_value))
            output.record(pos.id, context.date, ValuationType.CARRYING_VALUE, val)  # type: ignore[arg-type]


class OutstandingBalanceStrategy:
    """Values loan positions at their outstanding balance (carrying value)."""

    def value_batch(
        self,
        positions: list[object],
        instruments: object,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Record the outstanding balance for each loan position as CARRYING_VALUE."""
        for pos in positions:
            inst = instruments.get(pos.instrument_id)  # type: ignore[union-attr]
            val = Decimal(str(inst.face_value))
            output.record(pos.id, context.date, ValuationType.CARRYING_VALUE, val)  # type: ignore[arg-type]
