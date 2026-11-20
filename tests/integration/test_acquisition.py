"""Acquisition convention: positions are acquired at close of business on their acquisition date.

The acquisition cost is the total cash paid (clean price plus accrued interest). The
buyer gets no cash flow dated on the acquisition date and earns nothing for that day.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, TransactionType, TxMeta
from brms.core.exceptions import UnsupportedPositionError
from brms.core.models.instruments.loans import ResidentialMortgage
from brms.core.rules.interest_accrual import scaled_accrued_amount
from brms.core.utils import pydate_to_qldate
from tests.support.engine import flat_yields, make_bond, make_position, run_bank
from tests.support.reconcile import Check, account_balance

_YIELDS = flat_yields(datetime.date(2021, 1, 4), datetime.date(2022, 7, 29))
_CHECKS = frozenset({Check.BALANCE, Check.ACCRUED_INTEREST, Check.LOANS})
_CENT = Decimal("0.01")
_CASH_FLOW_TYPES = {TransactionType.INTEREST_SETTLEMENT, TransactionType.INTEREST_ACCRUAL}


def _accrued(instrument, day: datetime.date) -> Decimal:  # noqa: ANN001
    return scaled_accrued_amount(instrument.ql_instrument, pydate_to_qldate(day))


def _txs(sim, position_id: str, day: datetime.date) -> list:  # noqa: ANN001
    return [t for t in sim.transaction_log.by_position(position_id) if t.date == day]


def test_bond_bought_on_coupon_date_collects_no_coupon_that_day() -> None:
    """Bought on the (adjusted) coupon date 2021-01-04: that coupon belongs to the seller."""
    bond = make_bond(id="R")
    pos = make_position(
        id="pos-R", instrument_id="R", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=datetime.date(2021, 1, 4), cost=Decimal(500_000),
    )
    seen: dict[datetime.date, Decimal] = {}

    def record(sim, day: datetime.date) -> None:  # noqa: ANN001
        seen[day] = account_balance(sim, "Accrued Interest Receivable")

    sim = run_bank([bond], [pos], yields=_YIELDS, until=datetime.date(2021, 1, 5), checks=_CHECKS, each_day=record)

    assert not [t for t in _txs(sim, "pos-R", datetime.date(2021, 1, 4)) if t.type in _CASH_FLOW_TYPES]  # noqa: S101
    assert seen[datetime.date(2021, 1, 4)] == 0  # noqa: S101
    accruals = [t for t in _txs(sim, "pos-R", datetime.date(2021, 1, 5)) if t.type == TransactionType.INTEREST_ACCRUAL]
    assert len(accruals) == 1  # noqa: S101
    assert abs(accruals[0].amount - _accrued(bond, datetime.date(2021, 1, 5))) <= _CENT  # noqa: S101


def test_bond_bought_between_coupons_splits_accrued() -> None:
    """The purchase debits the investment at clean cost and the receivable with purchased accrued."""
    bond = make_bond(id="R")
    acquired = datetime.date(2021, 3, 15)
    accrued = _accrued(bond, acquired)
    pos = make_position(
        id="pos-R", instrument_id="R", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=acquired, cost=Decimal(510_000) + accrued,
    )
    balances: dict[datetime.date, tuple[Decimal, Decimal]] = {}

    def record(sim, day: datetime.date) -> None:  # noqa: ANN001
        balances[day] = (
            account_balance(sim, "Investment Securities at Amortized Cost"),
            account_balance(sim, "Accrued Interest Receivable"),
        )

    sim = run_bank([bond], [pos], yields=_YIELDS, until=datetime.date(2021, 6, 30), checks=_CHECKS, each_day=record)

    purchase = next(t for t in sim.transaction_log.by_position("pos-R") if t.type == TransactionType.SECURITY_PURCHASE)
    assert abs(Decimal(str(dict(purchase.metadata)[TxMeta.ACCRUED_INTEREST])) - accrued) <= _CENT  # noqa: S101
    investment, receivable = balances[acquired]
    assert abs(investment - Decimal(510_000)) <= _CENT  # noqa: S101
    assert abs(receivable - accrued) <= _CENT  # noqa: S101


def test_positions_acquired_on_first_day_and_on_a_saturday() -> None:
    """No rule fires on an acquisition date, weekend or not; books reconcile from the next day."""
    bond_a = make_bond(id="A")
    bond_b = make_bond(id="B")
    first = datetime.date(2021, 1, 4)
    saturday = datetime.date(2021, 1, 9)
    pos_a = make_position(
        id="pos-A", instrument_id="A", basis=MeasurementBasis.FVTPL, acquired=first, cost=Decimal(505_000),
    )
    pos_b = make_position(
        id="pos-B", instrument_id="B", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=saturday, cost=Decimal(505_000) + _accrued(bond_b, saturday),
    )
    sim = run_bank(
        [bond_a, bond_b], [pos_a, pos_b], yields=_YIELDS, until=datetime.date(2021, 2, 26),
        checks=frozenset({Check.BALANCE, Check.ACCRUED_INTEREST}),
    )
    for pid, day in (("pos-A", first), ("pos-B", saturday)):
        rule_txs = [t for t in _txs(sim, pid, day) if t.type != TransactionType.SECURITY_PURCHASE]
        assert not rule_txs, rule_txs  # noqa: S101


def _mortgage() -> ResidentialMortgage:
    loan = ResidentialMortgage(
        face_value=300_000.0,
        interest_rate=0.06,
        issue_date=ql.Date(15, 12, 2020),
        maturity=ql.Period(1, ql.Years),
        ltv=0.7,
    )
    loan.id = "M"
    return loan


def _outstanding(loan: ResidentialMortgage, day: datetime.date) -> Decimal:
    _interest, principal, _out = loan.payment_schedule()
    paid = sum((Decimal(str(a)) for d, a in principal if d <= day), Decimal(0))
    return Decimal(str(loan.face_value)) - paid


def test_loan_bought_mid_period_with_accrued_reconciles() -> None:
    """A loan bought between payment dates, paying for accrued interest, reconciles from day one."""
    loan = _mortgage()
    acquired = datetime.date(2021, 1, 20)
    pos = make_position(
        id="pos-M", instrument_id="M", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=acquired, cost=_outstanding(loan, acquired) + _accrued(loan, acquired),
    )
    receivable_after_payment: list[Decimal] = []

    def record(sim, day: datetime.date) -> None:  # noqa: ANN001
        if day.day == 15 and day > acquired:  # noqa: PLR2004
            receivable_after_payment.append(account_balance(sim, "Accrued Interest Receivable"))

    run_bank([loan], [pos], yields=_YIELDS, until=datetime.date(2021, 3, 20), checks=_CHECKS, each_day=record)
    assert len(receivable_after_payment) == 2  # noqa: S101, PLR2004
    assert all(abs(r) <= _CENT for r in receivable_after_payment), receivable_after_payment  # noqa: S101


def test_loan_bought_at_discount_is_rejected() -> None:
    """A loan whose clean cost is not its outstanding principal is not supported yet."""
    loan = _mortgage()
    acquired = datetime.date(2021, 1, 20)
    pos = make_position(
        id="pos-M", instrument_id="M", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=acquired, cost=_outstanding(loan, acquired),
    )
    with pytest.raises(UnsupportedPositionError, match="premium or discount"):
        run_bank([loan], [pos], yields=_YIELDS, until=datetime.date(2021, 2, 1), checks=_CHECKS)
