"""Valuation strategy implementations for the strategy-based ValuationService."""

from __future__ import annotations

import datetime
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


def clean_acquisition_cost(position: Position, instrument: Instrument) -> Decimal:
    """Return the clean acquisition cost — the carrying value at initial recognition.

    When a coupon-bearing bond is purchased between coupon dates the buyer
    pays a *dirty price* that includes accrued interest since the last coupon.
    At initial recognition the accounting entry splits the dirty price::

        Dr  Investment account              (clean price)
        Dr  Accrued Interest Receivable     (accrued interest)
        Cr  Cash                            (dirty price = acquisition_cost)

    The carrying value of the investment equals the **clean price** — the
    amount actually debited to the Investment account.  This function computes
    ``acquisition_cost - accruedAmount(acquisition_date - 1) * face / 100``.

    We use ``acquisition_date - 1 day`` for consistency with the acquisition
    journal entry posted by :class:`SimulationBuilder` (see
    ``_compute_accrued_interest_at_acquisition`` for the detailed rationale).

    For instruments without QuantLib accrued-amount support (loans, deposits,
    equity) the full ``acquisition_cost`` is returned unchanged.
    """
    ql_inst = getattr(instrument, "ql_instrument", None)
    if ql_inst is None or not hasattr(ql_inst, "accruedAmount"):
        return Decimal(str(position.acquisition_cost))

    from brms.core.utils import pydate_to_qldate

    face_value = getattr(instrument, "face_value", None)
    scale = Decimal(str(face_value)) / Decimal("100") if face_value else Decimal("1")

    day_before = position.acquisition_date - datetime.timedelta(days=1)
    try:
        raw = ql_inst.accruedAmount(pydate_to_qldate(day_before))
        accrued = (Decimal(str(raw)) * scale).quantize(Decimal("0.01"))
    except RuntimeError:
        return Decimal(str(position.acquisition_cost))

    if accrued > 0:
        return Decimal(str(position.acquisition_cost)) - accrued
    return Decimal(str(position.acquisition_cost))


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


class CarryingValueStrategy:
    """Values positions at carrying value (clean acquisition cost).

    For amortized-cost instruments the carrying value equals the clean
    acquisition price — the amount actually debited to the Investment
    account at initial recognition.  See :func:`clean_acquisition_cost`.
    """

    def value_batch(
        self,
        positions: list[Position],
        instruments: InstrumentStore,
        context: ValuationContext,
        output: ValuationStore,
    ) -> None:
        """Record carrying value using the clean acquisition cost."""
        for pos in positions:
            inst = instruments.get(pos.instrument_id)
            val = clean_acquisition_cost(pos, inst)
            output.record(pos.id, context.date, ValuationType.CARRYING_VALUE, val)  # type: ignore[arg-type]


def default_valuation_strategies() -> dict:
    """Return the default MeasurementBasis → ValuationStrategy mapping."""
    from brms.core.enums import MeasurementBasis

    fair_value = FairValueStrategy()
    return {
        MeasurementBasis.AMORTIZED_COST: CarryingValueStrategy(),
        MeasurementBasis.FVOCI: fair_value,
        MeasurementBasis.FVTPL: fair_value,
    }
