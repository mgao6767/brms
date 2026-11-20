"""MaturityRule: generates a settlement transaction when an instrument reaches maturity."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import TxMeta
from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


class MaturityRule:
    """Generates a MATURITY_SETTLEMENT transaction on the instrument's maturity date."""

    def applies_to(
        self,
        instrument: Instrument,
        _position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True if the instrument has matured on or before the current date."""
        maturity = getattr(instrument, "maturity_date", None)
        if maturity is None:
            return False
        return maturity <= context.date

    def generate(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate a single maturity settlement transaction for the face value."""
        # At maturity, the bond pays back face value, not acquisition cost
        face_value = getattr(instrument, "face_value", None)
        amount = Decimal(str(face_value)) if face_value is not None else position.acquisition_cost
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.MATURITY_SETTLEMENT,
                date=context.date,
                amount=amount,
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                description="Instrument matured — settlement",
                metadata=((TxMeta.MEASUREMENT_BASIS, position.measurement_basis),),
            ),
        ]
