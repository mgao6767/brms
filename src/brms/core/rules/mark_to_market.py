"""MarkToMarketRule: moves an FVOCI or FVTPL position's carrying value to its clean fair value.

The amount is ``FAIR_VALUE(today) - CARRYING_VALUE(previous record) - change in AMORTIZED_COST today``.
The last term is zero for FVTPL; for FVOCI it has already been booked to interest income by
the EffectiveInterestRule, so the mark carries only the change in unrealised gain or loss.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import MeasurementBasis, TxMeta, ValuationType
from brms.core.exceptions import ValuationError
from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext

_MTM_BASES = frozenset({MeasurementBasis.FVTPL, MeasurementBasis.FVOCI})


class MarkToMarketRule:
    """Generates a MARK_TO_MARKET transaction for FVTPL and FVOCI positions with a fair value today."""

    def applies_to(self, _instrument: Instrument, position: Position, context: RuleContext) -> bool:
        """Return True when the position is at fair value and valuation recorded one today."""
        if position.measurement_basis not in _MTM_BASES:
            return False
        return context.valuation_store.get(position.id, context.date, ValuationType.FAIR_VALUE) is not None

    def generate(self, _instrument: Instrument, position: Position, context: RuleContext) -> list[Transaction]:
        """Generate the mark from today's fair value and the previous carrying value."""
        store = context.valuation_store
        fair = store.get(position.id, context.date, ValuationType.FAIR_VALUE)
        previous = store.get_previous(position.id, context.date, ValuationType.CARRYING_VALUE)
        if fair is None or previous is None:
            msg = f"Position {position.id} has no fair value on {context.date} or carrying value before it"
            raise ValuationError(msg)
        amortization = Decimal(0)
        if position.measurement_basis == MeasurementBasis.FVOCI:
            today_ac = store.get(position.id, context.date, ValuationType.AMORTIZED_COST)
            previous_ac = store.get_previous(position.id, context.date, ValuationType.AMORTIZED_COST)
            if today_ac is None or previous_ac is None:
                msg = f"Position {position.id} has no amortised cost on or before {context.date}"
                raise ValuationError(msg)
            amortization = today_ac - previous_ac
        change = fair - previous - amortization
        if change == 0:
            return []
        direction = "gain" if change > 0 else "loss"
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.MARK_TO_MARKET,
                date=context.date,
                amount=change,
                position_id=position.id,
                instrument_id=position.instrument_id,
                description=f"Mark-to-market {direction} ({position.measurement_basis.name})",
                metadata=(
                    (TxMeta.MEASUREMENT_BASIS, position.measurement_basis),
                    (TxMeta.DIRECTION, direction),
                ),
            ),
        ]
