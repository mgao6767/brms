"""CouponPaymentRule: settles coupon payments on adjusted coupon dates.

At settlement, the coupon amount (from the payment schedule) may differ from
the total accrued interest (from QL's day count convention).  The transaction
carries an ``accrued_portion`` in metadata so the AccountingService can post
a three-leg entry:

    Dr  Cash                         (coupon amount)
    Cr  Accrued Interest Receivable  (what was actually accrued)
    Cr  Interest Income              (catch-up difference)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InterestSide, PositionSide, TxMeta
from brms.core.exceptions import ValuationError
from brms.core.models.transaction import Transaction, TransactionType
from brms.core.services.amortized_cost import scaled_accrued

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


class CouponPaymentRule:
    """Settle coupon payments on scheduled (business-day-adjusted) dates."""

    def applies_to(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True for LONG positions on a coupon date.

        Coupon settlement is income-side: Dr Cash / Cr AIR / Cr Interest
        Income.  SHORT positions (bond issuance) would require an expense-side
        rule, which is not implemented here.
        """
        if getattr(position, "side", None) != PositionSide.LONG:
            return False
        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            if isinstance(result, list):
                return any(d == context.date for d, _amount in result)
        coupon_dates = getattr(instrument, "coupon_dates", [])
        return any(d == context.date for d in coupon_dates)

    def generate(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate a settlement transaction with the accrued portion for three-leg posting."""
        coupon_amount: Decimal | None = None

        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            if isinstance(result, list):
                for d, amount in result:
                    if d == context.date:
                        coupon_amount = Decimal(str(amount))
                        break

        if coupon_amount is None:
            msg = f"Position {position.id} has no scheduled coupon on {context.date}"
            raise ValuationError(msg)

        # Compute accrued portion from QL for the three-leg settlement
        accrued_portion = self._compute_accrued_portion(instrument, position, context)

        metadata: tuple[tuple[TxMeta, object], ...] = ((TxMeta.SIDE, InterestSide.INCOME),)
        if accrued_portion is not None:
            metadata = (*metadata, (TxMeta.ACCRUED_PORTION, str(accrued_portion)))

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.INTEREST_SETTLEMENT,
                date=context.date,
                amount=coupon_amount,
                description="Coupon payment received",
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                metadata=metadata,
            ),
        ]

    @staticmethod
    def _compute_accrued_portion(instrument: Instrument, position: Position, context: RuleContext) -> Decimal | None:
        """Return the receivable to clear: the position's accrued interest at its previous date.

        Rules run before today's postings, so the receivable holds the accrued interest as of the
        previous date (floored at the acquisition date). Returns None without a QuantLib instrument.
        """
        ql_inst = getattr(instrument, "ql_instrument", None)
        if ql_inst is None or not hasattr(ql_inst, "accruedAmount"):
            return None
        return scaled_accrued(instrument, position, context.position_previous_date(position))
