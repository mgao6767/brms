"""A loan closes once its final scheduled principal payment is received."""
# ruff: noqa: D103

from __future__ import annotations

import datetime
from decimal import Decimal

import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis, PositionStatus
from brms.core.models.instruments.loans import ResidentialMortgage
from brms.core.rules.interest_accrual import scaled_accrued_amount
from brms.core.services.simulation_builder import outstanding_principal
from brms.core.utils import pydate_to_qldate
from tests.support.engine import flat_yields, make_position, run_bank
from tests.support.reconcile import account_balance


def test_loan_closes_after_final_payment() -> None:
    loan = ResidentialMortgage(
        face_value=300_000.0, interest_rate=0.06, issue_date=ql.Date(15, 12, 2020), ltv=0.7,
        maturity=ql.Period(1, ql.Years),
    )
    loan.id = "M"
    acquired = datetime.date(2021, 1, 4)
    accrued = scaled_accrued_amount(loan.ql_instrument, pydate_to_qldate(acquired))
    pos = make_position(
        id="pos-M", instrument_id="M", basis=MeasurementBasis.AMORTIZED_COST,
        acquired=acquired, cost=outstanding_principal(loan, acquired) + accrued,
    )
    last_payment = loan.payment_schedule()[1][-1][0]
    closed_on: list[datetime.date] = []

    def watch(sim, day: datetime.date) -> None:  # noqa: ANN001
        if not closed_on and sim.bank.positions.get("pos-M").status == PositionStatus.CLOSED:
            closed_on.append(day)

    end = datetime.date(2022, 1, 31)
    sim = run_bank([loan], [pos], yields=flat_yields(acquired, end), until=end, each_day=watch)
    assert closed_on == [last_payment]  # noqa: S101
    assert abs(account_balance(sim, "Loans and Advances")) <= Decimal("0.01")  # noqa: S101
    assert abs(account_balance(sim, "Accrued Interest Receivable")) <= Decimal("0.01")  # noqa: S101
