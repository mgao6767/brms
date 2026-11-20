"""LoanInterestSettlementRule: settles interest on amortizing loan payment dates.

On each scheduled interest payment date, the borrower remits the interest
portion of the monthly payment.  The accounting entry clears the Accrued
Interest Receivable built up by daily ``InterestIncomeAccrualRule`` postings:

    Dr  Cash                         (scheduled interest amount)
    Cr  Accrued Interest Receivable  (what was actually accrued)
    Cr  Interest Income              (catch-up difference)

This follows the same three-leg settlement pattern as ``CouponPaymentRule``
for bonds — the ``AccountingService`` handles the metadata identically.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InterestSide, PositionSide, TxMeta
from brms.core.models.transaction import Transaction, TransactionType
from brms.core.services.amortized_cost import scaled_accrued

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


class LoanInterestSettlementRule:
    """Settle interest payments on amortizing loan payment dates.

    Reads interest payment dates and amounts from ``payment_schedule()[0]``
    (the interest_pmt list of the 3-element loan schedule tuple).
    """

    def applies_to(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True for LONG positions on a scheduled interest payment date.

        Income-side settlement: Dr Cash / Cr AIR / Cr Interest Income.
        """
        if getattr(position, "side", None) != PositionSide.LONG:
            return False
        schedule = getattr(instrument, "payment_schedule", None)
        if not callable(schedule):
            return False
        result = schedule()
        if not (isinstance(result, tuple) and len(result) == 3):  # noqa: PLR2004
            return False
        interest_pmt, _principal_pmt, _outstanding = result
        return any(d == context.date for d, _amount in interest_pmt)

    def generate(
        self,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate an interest settlement transaction for the scheduled amount."""
        interest_amount: Decimal | None = None

        schedule = getattr(instrument, "payment_schedule", None)
        if callable(schedule):
            result = schedule()
            if isinstance(result, tuple) and len(result) == 3:  # noqa: PLR2004
                interest_pmt, _principal_pmt, _outstanding = result
                for d, amount in interest_pmt:
                    if d == context.date:
                        interest_amount = Decimal(str(amount))
                        break

        if interest_amount is None:
            return []

        accrued_portion = self._compute_accrued_portion(instrument, position, context)

        metadata: tuple[tuple[TxMeta, object], ...] = ((TxMeta.SIDE, InterestSide.INCOME),)
        if accrued_portion is not None:
            metadata = (*metadata, (TxMeta.ACCRUED_PORTION, str(accrued_portion)))

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.INTEREST_SETTLEMENT,
                date=context.date,
                amount=interest_amount,
                description="Loan interest payment received",
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                metadata=metadata,
            ),
        ]

    @staticmethod
    def _compute_accrued_portion(instrument: Instrument, position: Position, context: RuleContext) -> Decimal | None:
        """Return the receivable to clear: the position's accrued interest at its previous date."""
        ql_inst = getattr(instrument, "ql_instrument", None)
        if ql_inst is None or not hasattr(ql_inst, "accruedAmount"):
            return None
        return scaled_accrued(instrument, position, context.position_previous_date(position))
