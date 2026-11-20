"""EffectiveInterestRule: amortises bond premium or discount into interest income daily.

The amount is the day's change in the position's amortised cost (recorded by valuation at
the effective interest rate). Together with the coupon accrual it makes daily interest
income equal to the effective yield on the position.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from brms.core.enums import MeasurementBasis, TransactionType, TxMeta, ValuationType
from brms.core.exceptions import ValuationError
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext

_AMORTIZED_BASES = frozenset({MeasurementBasis.AMORTIZED_COST, MeasurementBasis.FVOCI})


class EffectiveInterestRule:
    """Emit PREMIUM_DISCOUNT_AMORTIZATION for bonds held at amortised cost or FVOCI."""

    def applies_to(self, _instrument: Instrument, position: Position, _context: RuleContext) -> bool:
        """Return True for positions whose measurement basis carries an amortised cost."""
        return position.measurement_basis in _AMORTIZED_BASES

    def generate(self, _instrument: Instrument, position: Position, context: RuleContext) -> list[Transaction]:
        """Generate the day's amortisation from the change in recorded amortised cost."""
        store = context.valuation_store
        today = store.get(position.id, context.date, ValuationType.AMORTIZED_COST)
        previous = store.get_previous(position.id, context.date, ValuationType.AMORTIZED_COST)
        if today is None or previous is None:
            msg = f"Position {position.id} has no amortised cost on or before {context.date}"
            raise ValuationError(msg)
        amount = today - previous
        if amount == 0:
            return []
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.PREMIUM_DISCOUNT_AMORTIZATION,
                date=context.date,
                amount=amount,
                description="Discount accretion" if amount > 0 else "Premium amortisation",
                position_id=position.id,
                instrument_id=position.instrument_id,
                metadata=((TxMeta.MEASUREMENT_BASIS, position.measurement_basis),),
            ),
        ]
