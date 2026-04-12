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
    import QuantLib as ql  # noqa: N813

    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext

_DAYS_PER_YEAR = Decimal("365")


def scaled_accrued_amount(ql_inst: ql.Bond, ql_date: ql.Date) -> Decimal:
    """Return the absolute accrued interest at *ql_date* in currency.

    QL's ``accruedAmount(d)`` returns per-100 of the **current notional** at
    *d*.  For fixed-notional bonds the current notional equals face value; for
    amortizing instruments it declines at each payment date.  In both cases,
    scaling by ``notional(d) / 100`` gives the correct dollar amount.
    """
    raw = Decimal(str(ql_inst.accruedAmount(ql_date)))
    notional = Decimal(str(ql_inst.notional(ql_date)))
    return raw * notional / Decimal("100")


class InterestIncomeAccrualRule:
    """Accrue interest income for LONG positions on coupon/interest-bearing instruments.

    Produces INTEREST_ACCRUAL transactions with ``("side", "income")`` metadata.
    Accounting: Dr Accrued Interest Receivable / Cr Interest Income.
    """

    def applies_to(
        self,
        _instrument: Instrument,
        position: Position,
        _context: RuleContext,
    ) -> bool:
        """Return True for LONG positions (runs every day)."""
        return getattr(position, "side", None) == PositionSide.LONG

    def generate(
        self,
        instrument: Instrument,
        position: Position,
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
        ql_inst: ql.Bond,
        instrument: Instrument,
        position: Position,
        context: RuleContext,
    ) -> list[Transaction]:
        """Compute accrual from the change in QL accruedAmount.

        ``accruedAmount(d)`` returns per-100 of face for fixed-notional bonds,
        but per-100 of **current notional** for amortizing instruments.  We
        scale each observation by ``notional(d) / 100`` when the instrument has
        a date-varying notional, or ``face_value / 100`` otherwise.

        When a coupon/payment date is crossed, accruedAmount resets to 0 and
        the change goes negative.  In that case we record only
        ``accruedAmount(today)`` — the new period's accrual.  The catch-up
        between total accrued and coupon/interest amount is handled at
        settlement.
        """
        ql_today = pydate_to_qldate(context.date)
        try:
            ai_today = scaled_accrued_amount(ql_inst, ql_today)
        except Exception:  # noqa: BLE001
            return self._generate_fallback(instrument, position, context)

        if context.previous_date is not None:
            ql_prev = pydate_to_qldate(context.previous_date)
            try:
                ai_prev = scaled_accrued_amount(ql_inst, ql_prev)
            except Exception:  # noqa: BLE001
                ai_prev = Decimal("0")
        else:
            # First advance: no prior accrual recorded yet
            ai_prev = Decimal("0")

        change = ai_today - ai_prev

        if change > 0:
            # Normal accrual: interest grew since last advance
            amount = change
        elif change < 0 and ai_today > 0:
            # Coupon date crossed (accruedAmount reset), new period started
            # Record only the new period's accrual portion
            amount = ai_today
        else:
            # No change (same day count) or coupon date (ai=0): nothing to record
            return []

        return self._make_tx(amount, context, position)

    # ------------------------------------------------------------------
    # Fallback for non-QL instruments
    # ------------------------------------------------------------------

    def _generate_fallback(
        self,
        instrument: Instrument,
        position: Position,
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
    def _make_tx(amount: Decimal, context: RuleContext, position: Position) -> list[Transaction]:
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
