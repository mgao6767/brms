"""MarkToMarketRule: generates a mark-to-market transaction for FVTPL and FVOCI instruments."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentClass as CoreInstrumentClass
from brms.core.enums import ValuationType
from brms.core.models.instruments.base import InstrumentClass as BaseInstrumentClass
from brms.core.models.transaction import Transaction, TransactionType

if TYPE_CHECKING:
    from brms.core.rules.context import RuleContext

_MTM_CLASSES = {
    BaseInstrumentClass.FVTPL,
    BaseInstrumentClass.FVOCI,
    CoreInstrumentClass.FVTPL,
    CoreInstrumentClass.FVOCI,
}


class MarkToMarketRule:
    """Generates a MARK_TO_MARKET transaction for instruments classified as FVTPL or FVOCI."""

    def applies_to(
        self,
        _instrument: object,
        position: object,
        context: RuleContext,
    ) -> bool:
        """Return True if market data is available and the position is FVTPL or FVOCI."""
        if not context.has_market_data:
            return False
        instrument_class = getattr(position, "instrument_class", None)
        if instrument_class is None:
            return False
        return instrument_class in _MTM_CLASSES

    def generate(
        self,
        _instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate a mark-to-market transaction based on fair value change from valuation store."""
        position_id = getattr(position, "id", None)
        instrument_id = getattr(position, "instrument_id", None)
        acquisition_cost = Decimal(str(getattr(position, "acquisition_cost", "0")))

        # Get current fair value from valuation store
        current_fv = context.valuation_store.get(position_id, context.date, ValuationType.FAIR_VALUE)
        if current_fv is None:
            return []

        # Find the most recent prior fair value, or fall back to acquisition cost
        previous_fv = context.valuation_store.get_previous(position_id, context.date, ValuationType.FAIR_VALUE)
        if previous_fv is None:
            previous_fv = acquisition_cost

        fair_value_change = current_fv - previous_fv
        if fair_value_change == 0:
            return []

        instrument_class = getattr(position, "instrument_class", None)
        if instrument_class in {BaseInstrumentClass.FVTPL, CoreInstrumentClass.FVTPL}:
            class_name = "FVTPL"
        elif instrument_class in {BaseInstrumentClass.FVOCI, CoreInstrumentClass.FVOCI}:
            class_name = "FVOCI"
        else:
            class_name = ""

        direction = "gain" if fair_value_change > 0 else "loss"

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.MARK_TO_MARKET,
                date=context.date,
                amount=fair_value_change,
                position_id=position_id,
                instrument_id=instrument_id,
                description=f"Mark-to-market {direction} ({class_name})",
                metadata=(
                    ("instrument_class", class_name),
                    ("direction", direction),
                ),
            ),
        ]
