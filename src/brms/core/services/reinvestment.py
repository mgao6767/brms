"""Reinvest maturing bonds: replace each with a new par bond of the same term at the day's rate.

Used when ``Bank.reinvest_maturities`` is set (the static-balance-sheet assumption of supervisory
stress tests). The new bond has the matured bond's face, term (in months), issuer, rating,
measurement basis, book and credit spread; its coupon is the par rate on the day's curve plus that
spread, so it is bought at face with no accrued interest. Loans are not rolled over.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta

from brms.core.enums import TransactionType, TxMeta
from brms.core.models.position import Position
from brms.core.models.transaction import Transaction
from brms.core.services.amortized_cost import is_loan
from brms.core.services.spreads import dirty_value, spreaded_handle
from brms.core.utils import pydate_to_qldate

if TYPE_CHECKING:
    import datetime

    import QuantLib as ql  # noqa: N813

    from brms.core.models.bank import Bank
    from brms.core.models.instruments.base import Instrument

_TRIAL_COUPON = 0.01


def _term_months(instrument: Instrument) -> int:
    issue, maturity = instrument.issue_date, instrument.maturity_date  # type: ignore[attr-defined]
    return (maturity.year - issue.year) * 12 + (maturity.month - issue.month)


def _new_bond(old: Instrument, coupon: float, date: datetime.date) -> Instrument:
    maturity = date + relativedelta(months=_term_months(old))
    return type(old)(  # type: ignore[call-arg]
        face_value=old.face_value,  # type: ignore[attr-defined]
        coupon_rate=coupon,
        issue_date=pydate_to_qldate(date),
        maturity_date=pydate_to_qldate(maturity),
        issuer=old.issuer,
        credit_rating=old.credit_rating,
    )


def par_coupon(old: Instrument, handle: ql.YieldTermStructureHandle, date: datetime.date) -> float:
    """Return the coupon at which a new bond like *old*, issued on *date*, is worth its face on *handle*."""
    face = float(old.face_value)  # type: ignore[attr-defined]
    zero = dirty_value(_new_bond(old, 0.0, date).ql_instrument.cashflows(), handle, date)  # type: ignore[attr-defined]
    trial = dirty_value(_new_bond(old, _TRIAL_COUPON, date).ql_instrument.cashflows(), handle, date)  # type: ignore[attr-defined]
    return _TRIAL_COUPON * (face - zero) / (trial - zero)


def reinvest(
    bank: Bank, transactions: list[Transaction], handle: ql.YieldTermStructureHandle, date: datetime.date,
) -> list[Transaction]:
    """Buy a replacement for each bond matured in *transactions*; return the purchase transactions."""
    purchases: list[Transaction] = []
    for tx in transactions:
        if tx.type != TransactionType.MATURITY_SETTLEMENT or tx.position_id is None:
            continue
        old_position = bank.positions.get(tx.position_id)
        old = bank.instruments.get(old_position.instrument_id)
        if is_loan(old):
            continue
        curve = handle if old_position.spread is None else spreaded_handle(handle, old_position.spread)
        bond = _new_bond(old, par_coupon(old, curve, date), date)
        bond.id = f"{old.id}@{date.isoformat()}"
        bond.name = old.name
        position = Position(
            id=f"{old_position.id}@{date.isoformat()}",
            instrument_id=bond.id,
            book_type=old_position.book_type,
            measurement_basis=old_position.measurement_basis,
            side=old_position.side,
            acquisition_date=date,
            acquisition_cost=Decimal(str(bond.face_value)),
            spread=old_position.spread,
        )
        bank.instruments.add(bond)
        bank.positions.add(position)
        purchases.append(Transaction(
            id=str(uuid.uuid4()), type=TransactionType.SECURITY_PURCHASE, date=date,
            amount=position.acquisition_cost, position_id=position.id, instrument_id=bond.id,
            description="Reinvestment of a matured bond",
            metadata=((TxMeta.MEASUREMENT_BASIS, position.measurement_basis),),
        ))
    return purchases
