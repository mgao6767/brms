"""InterestIncomeAccrualRule: accrues interest income using QuantLib conventions.

For QL-backed bonds, uses ``bond.accruedAmount(date)`` which correctly handles
day count conventions (e.g., Thirty360), business day adjustments, and coupon
period boundaries.  The accrual is the change in QL's accrued interest between
the previous simulation date and today.

Any difference between the sum of daily accruals and the coupon payment amount
is handled as a "catch-up" at settlement by the CouponPaymentRule.

Instruments without a QuantLib object are not supported and raise.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InterestSide, PositionSide, TransactionType, TxMeta
from brms.core.exceptions import UnsupportedPositionError, ValuationError
from brms.core.models.transaction import Transaction
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    import datetime

    import QuantLib as ql  # noqa: N813

    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.rules.context import RuleContext


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
            return self._generate_ql(ql_inst, position, context)
        msg = f"Position {position.id} has no QuantLib instrument to accrue interest from"
        raise UnsupportedPositionError(msg)

    # ------------------------------------------------------------------
    # QL-based accrual
    # ------------------------------------------------------------------

    def _generate_ql(
        self,
        ql_inst: ql.Bond,
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
        ai_today = self._accrued(ql_inst, position, context.date)
        ai_prev = self._accrued(ql_inst, position, context.position_previous_date(position))

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

    @staticmethod
    def _accrued(ql_inst: ql.Bond, position: Position, day: datetime.date) -> Decimal:
        try:
            return scaled_accrued_amount(ql_inst, pydate_to_qldate(day))
        except RuntimeError as exc:
            msg = f"Cannot compute accrued interest for position {position.id} on {day}: {exc}"
            raise ValuationError(msg) from exc

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
                metadata=((TxMeta.SIDE, InterestSide.INCOME),),
            ),
        ]
