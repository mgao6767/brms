"""MaturityRule: settles a bond at face value on the date its redemption is paid."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import TxMeta, ValuationType
from brms.core.exceptions import ValuationError
from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    import datetime

    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


def redemption_date(instrument: Instrument) -> datetime.date | None:
    """Return the date the bond's redemption is paid (the last date in its cash-flow schedule)."""
    schedule = instrument.payment_schedule()  # type: ignore[attr-defined]
    return schedule[-1][0] if schedule else None


class MaturityRule:
    """Generates a MATURITY_SETTLEMENT transaction on the redemption payment date."""

    def applies_to(self, instrument: Instrument, _position: Position, context: RuleContext) -> bool:
        """Return True on the date the redemption cash flow is paid."""
        return redemption_date(instrument) == context.date

    def generate(self, instrument: Instrument, position: Position, context: RuleContext) -> list[Transaction]:
        """Settle at face value, carrying the position's carrying value for the accounting check."""
        carrying = context.valuation_store.get(position.id, context.date, ValuationType.CARRYING_VALUE)
        if carrying is None:
            msg = f"Position {position.id} has no carrying value on its maturity date {context.date}"
            raise ValuationError(msg)
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.MATURITY_SETTLEMENT,
                date=context.date,
                amount=Decimal(str(instrument.face_value)),  # type: ignore[attr-defined]
                position_id=position.id,
                instrument_id=position.instrument_id,
                description="Instrument matured - settlement",
                metadata=(
                    (TxMeta.MEASUREMENT_BASIS, position.measurement_basis),
                    (TxMeta.CARRYING_VALUE, str(carrying)),
                ),
            ),
        ]
