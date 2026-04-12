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

from brms.core.models.transaction import Transaction, TransactionType
from brms.core.rules.interest_accrual import scaled_accrued_amount
from brms.core.utils import pydate_to_qldate

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
        """Return True if an interest payment date matches the current date.

        Skips payment dates on or before the acquisition date — on the day
        the loan enters the bank there is no accrued interest to settle.
        """
        if context.date <= position.acquisition_date:
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

        accrued_portion = self._compute_accrued_portion(instrument, context)

        # Cap accrued_portion at interest_amount: the settlement cannot clear
        # more AIR than cash received.  Day count convention differences between
        # QL's accruedAmount and the scheduled interest can cause a small
        # overshoot; capping prevents the AIR from going negative.
        if accrued_portion is not None and accrued_portion > interest_amount:
            accrued_portion = interest_amount

        metadata: tuple[tuple[str, object], ...] = (("side", "income"),)
        if accrued_portion is not None:
            metadata = (*metadata, ("accrued_portion", str(accrued_portion)))

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
    def _compute_accrued_portion(instrument: Instrument, context: RuleContext) -> Decimal | None:
        """Compute accrued interest as of the previous simulation date.

        Uses :func:`scaled_accrued_amount` which correctly handles the
        date-varying notional of amortizing instruments.
        """
        ql_inst = getattr(instrument, "ql_instrument", None)
        if ql_inst is None or not hasattr(ql_inst, "accruedAmount"):
            return None

        if context.previous_date is not None:
            ql_prev = pydate_to_qldate(context.previous_date)
            try:
                return scaled_accrued_amount(ql_inst, ql_prev)
            except Exception:  # noqa: BLE001
                return None
        return None
