"""AmortizationRule: generates an amortization transaction on scheduled payment dates."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType, PositionSide, TxMeta
from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


class AmortizationRule:
    """Generates an AMORTIZATION transaction on each scheduled payment date."""

    def applies_to(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True for LONG positions on a principal payment date.

        LONG: bank receives principal (Dr Cash / Cr Loans).
        """
        if getattr(position, "side", None) != PositionSide.LONG:
            return False
        return any(d == context.date for d, _amount in _principal_payments(instrument))

    def generate(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate an amortization transaction for the scheduled principal payment on this date."""
        principal = _principal_payments(instrument)
        amount = next(Decimal(str(a)) for d, a in principal if d == context.date)
        metadata: tuple[tuple[TxMeta, object], ...] = ()
        if getattr(instrument, "instrument_type", None) == InstrumentType.MORTGAGE_BACKED_SECURITY:
            # A security's paydown reduces its investment account, not Loans and Advances.
            metadata = ((TxMeta.MEASUREMENT_BASIS, position.measurement_basis),)
        if principal[-1][0] == context.date:
            metadata = (*metadata, (TxMeta.FINAL_PAYMENT, True))
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.AMORTIZATION,
                date=context.date,
                amount=amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                metadata=metadata,
            ),
        ]


def _principal_payments(instrument: Instrument) -> list[tuple[object, float]]:
    """Return the loan's scheduled principal payments ``[(date, amount), ...]``."""
    _interest, principal, _outstanding = instrument.payment_schedule()  # type: ignore[attr-defined]
    return principal
