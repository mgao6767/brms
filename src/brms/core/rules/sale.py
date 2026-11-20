"""SaleRule: sells a fair-value position on its scheduled sale date at fair value."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from brms.core.enums import MeasurementBasis, TransactionType, TxMeta, ValuationType
from brms.core.exceptions import UnsupportedPositionError, ValuationError
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext

_SELLABLE = frozenset({MeasurementBasis.FVOCI, MeasurementBasis.FVTPL})


class SaleRule:
    """Emit SECURITY_SALE on ``position.sale_date`` for the dirty fair value.

    Runs after the day's accrual, amortisation and mark, so the carrying value equals the clean
    fair value and the receivable holds the accrued interest being sold.
    """

    def applies_to(self, _instrument: Instrument, position: Position, context: RuleContext) -> bool:
        """Return True on the position's sale date."""
        return position.sale_date == context.date

    def generate(self, _instrument: Instrument, position: Position, context: RuleContext) -> list[Transaction]:
        """Sell the whole position at today's fair value plus accrued interest."""
        if position.measurement_basis not in _SELLABLE:
            msg = (
                f"Position {position.id} is held at {position.measurement_basis.name}; only FVOCI and FVTPL "
                "positions can be sold"
            )
            raise UnsupportedPositionError(msg)
        store = context.valuation_store
        fair = store.get(position.id, context.date, ValuationType.FAIR_VALUE)
        accrued = store.get(position.id, context.date, ValuationType.ACCRUED_INTEREST)
        if fair is None or accrued is None:
            msg = f"Position {position.id} has no fair value on its sale date {context.date} (not a market day?)"
            raise ValuationError(msg)
        metadata: tuple[tuple[TxMeta, object], ...] = (
            (TxMeta.MEASUREMENT_BASIS, position.measurement_basis),
            (TxMeta.CARRYING_VALUE, str(fair)),
            (TxMeta.ACCRUED_PORTION, str(accrued)),
        )
        if position.measurement_basis == MeasurementBasis.FVOCI:
            amortized = store.get(position.id, context.date, ValuationType.AMORTIZED_COST)
            metadata = (*metadata, (TxMeta.RECYCLED_OCI, str(fair - amortized)))
        return [Transaction(
            id=str(uuid.uuid4()), type=TransactionType.SECURITY_SALE, date=context.date, amount=fair + accrued,
            position_id=position.id, instrument_id=position.instrument_id, description="Security sold at fair value",
            metadata=metadata,
        )]
