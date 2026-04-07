"""InterestIncomeAccrualRule: accrues interest income using QuantLib conventions.

For QL-backed bonds, uses ``bond.accruedAmount(date)`` which correctly handles
day count conventions (e.g., Thirty360), business day adjustments, and coupon
period boundaries.  The accrual is the change in QL's accrued interest between
the previous simulation date and today.

Any difference between the sum of daily accruals and the coupon payment amount
is handled as a "catch-up" at settlement by the CouponPaymentRule.

For non-QL instruments, falls back to face_value * rate / 365.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import PositionSide, TransactionType
from brms.core.models.transaction import Transaction
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    from brms.core.rules.context import RuleContext

_DAYS_PER_YEAR = Decimal("365")


class InterestIncomeAccrualRule:
    """Accrue interest income for LONG positions on coupon/interest-bearing instruments.

    Produces INTEREST_ACCRUAL transactions with ``("side", "income")`` metadata.
    Accounting: Dr Accrued Interest Receivable / Cr Interest Income.
    """

    def applies_to(
        self,
        instrument: object,
        position: object,
        _context: RuleContext,
    ) -> bool:
        """Return True if the instrument has an interest rate and position is LONG."""
        side = getattr(position, "side", None)
        if side != PositionSide.LONG:
            return False
        return (
            getattr(instrument, "coupon_rate", None) is not None
            or getattr(instrument, "interest_rate", None) is not None
        )

    def generate(
        self,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Generate an accrual transaction based on the change in accrued interest."""
        ql_inst = getattr(instrument, "ql_instrument", None)
        if ql_inst is not None and hasattr(ql_inst, "accruedAmount"):
            return self._generate_ql(ql_inst, instrument, position, context)
        return self._generate_fallback(instrument, position, context)

    # ------------------------------------------------------------------
    # QL-based accrual
    # ------------------------------------------------------------------

    def _generate_ql(
        self,
        ql_inst: object,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Compute accrual from the change in QL accruedAmount.

        accruedAmount returns per-100 face value, so we scale by face/100.

        When a coupon date is crossed, accruedAmount resets to 0 and the change
        goes negative.  In that case we record only accruedAmount(today) — the
        new period's accrual (often 0 on the coupon date itself).  The catch-up
        between total accrued and coupon amount is handled at settlement.
        """
        face_value = getattr(instrument, "face_value", None)
        scale = Decimal(str(face_value)) / Decimal("100") if face_value else Decimal("1")

        ql_today = pydate_to_qldate(context.date)
        try:
            ai_today = Decimal(str(ql_inst.accruedAmount(ql_today))) * scale
        except Exception:  # noqa: BLE001
            return self._generate_fallback(instrument, position, context)

        if context.previous_date is not None:
            ql_prev = pydate_to_qldate(context.previous_date)
            try:
                ai_prev = Decimal(str(ql_inst.accruedAmount(ql_prev))) * scale
            except Exception:  # noqa: BLE001
                ai_prev = Decimal("0")
        else:
            # First advance: no prior accrual recorded yet
            ai_prev = Decimal("0")

        change = ai_today - ai_prev

        if change > 0:
            # Normal accrual: interest grew since last advance
            amount = change
        elif ai_today > 0:
            # Coupon date crossed, but we're past it into a new period
            # Record only the new period's accrual
            amount = ai_today
        else:
            # On the coupon date itself: accruedAmount = 0, nothing to record
            return []

        return self._make_tx(amount, context, position)

    # ------------------------------------------------------------------
    # Fallback for non-QL instruments
    # ------------------------------------------------------------------

    def _generate_fallback(
        self,
        instrument: object,
        position: object,
        context: RuleContext,
    ) -> list[Transaction]:
        """Compute accrual using simple rate / 365 for non-QL instruments.

        Since the simulation advances one calendar day at a time, the accrual
        is always exactly 1 day (notional * rate / 365).
        """
        rate = getattr(instrument, "coupon_rate", None) or getattr(instrument, "interest_rate", None)
        if rate is None:
            return []

        face_value = getattr(instrument, "face_value", None)
        notional = Decimal(str(face_value)) if face_value else Decimal(str(getattr(position, "acquisition_cost", "0")))
        amount = notional * Decimal(str(rate)) / _DAYS_PER_YEAR

        if amount <= 0:
            return []
        return self._make_tx(amount, context, position)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _make_tx(amount: Decimal, context: RuleContext, position: object) -> list[Transaction]:
        """Create an INTEREST_ACCRUAL transaction."""
        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=TransactionType.INTEREST_ACCRUAL,
                date=context.date,
                amount=amount,
                description="Interest income accrual",
                position_id=getattr(position, "id", None),
                instrument_id=getattr(position, "instrument_id", None),
                metadata=(("side", "income"),),
            ),
        ]
