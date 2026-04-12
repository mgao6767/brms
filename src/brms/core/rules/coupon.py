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

from brms.core.models.transaction import Transaction, TransactionType
from brms.core.rules.interest_accrual import scaled_accrued_amount
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


class CouponPaymentRule:
    """Settle coupon payments on scheduled (business-day-adjusted) dates."""

    def applies_to(
        self,
        instrument: Instrument,
        _position: Position,
        context: RuleContext,
    ) -> bool:
        """Return True if a coupon date matches the current date exactly."""
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
            face_value = Decimal(str(getattr(instrument, "face_value", "0")))
            coupon_rate = Decimal(str(getattr(instrument, "coupon_rate", "0")))
            coupon_amount = face_value * coupon_rate

        # Compute accrued portion from QL for the three-leg settlement
        accrued_portion = self._compute_accrued_portion(instrument, context)

        metadata: tuple[tuple[str, object], ...] = (("side", "income"),)
        if accrued_portion is not None:
            metadata = (*metadata, ("accrued_portion", str(accrued_portion)))

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
    def _compute_accrued_portion(instrument: Instrument, context: RuleContext) -> Decimal | None:
        """Compute the accrued interest as of the previous simulation date.

        This is what's currently sitting in the Accrued Interest Receivable
        account — the amount to clear at settlement.  The difference between
        the coupon amount and this value is the catch-up.

        Uses :func:`scaled_accrued_amount` for correct notional scaling.
        Returns None if QL accrued amount is unavailable.
        """
        ql_inst = getattr(instrument, "ql_instrument", None)
        if ql_inst is None or not hasattr(ql_inst, "accruedAmount"):
            return None

        # Use previous_date because the accrual rule for today hasn't posted yet
        # (rules run before posting), so the receivable = accruedAmount(previous_date)
        if context.previous_date is not None:
            ql_prev = pydate_to_qldate(context.previous_date)
            try:
                return scaled_accrued_amount(ql_inst, ql_prev)
            except Exception:  # noqa: BLE001
                return None
        return None
