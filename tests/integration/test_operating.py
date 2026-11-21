"""Operating costs, fee income and income tax: the parts of profit that are not interest or marks."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import MeasurementBasis
from brms.core.models.operating import OperatingConfig
from tests.support.engine import FUNDING, make_bond, make_position, run_bank, stepped_yields
from tests.support.reconcile import account_balance

_START = datetime.date(2021, 1, 4)
_YIELDS = stepped_yields(_START, datetime.date(2021, 7, 1), datetime.date(2022, 6, 30), 0.02, 0.05)


def _run(operating: OperatingConfig, until: datetime.date, *, with_bond: bool = False):  # noqa: ANN202
    instruments, positions = [], []
    if with_bond:
        bond = make_bond(id="L", coupon=0.02, maturity=datetime.date(2030, 7, 1))
        instruments.append(bond)
        positions.append(make_position(id="pos-L", instrument_id="L", basis=MeasurementBasis.FVTPL, acquired=_START,
                                       cost=Decimal(500_000)))  # about par at 2%
    return run_bank(instruments, positions, yields=_YIELDS, until=until, operating=operating)


def test_expenses_and_fee_income_flow_through_cash_daily() -> None:
    until = datetime.date(2021, 4, 13)
    days = (until - _START).days + 1  # every day from the funding day through *until*: 100
    sim = _run(OperatingConfig(noninterest_expense=Decimal(36_500), noninterest_income=Decimal(7_300)), until)
    assert float(account_balance(sim, "Operating Expense")) == pytest.approx(100 * days, abs=0.01)
    assert float(account_balance(sim, "Non-interest Income")) == pytest.approx(20 * days, abs=0.01)
    assert float(account_balance(sim, "Cash and Cash Equivalents")) == pytest.approx(float(FUNDING) - 80 * days,
                                                                                   abs=0.01)


def test_tax_is_the_rate_times_profit_to_date() -> None:
    until = datetime.date(2021, 4, 13)
    sim = _run(OperatingConfig(noninterest_income=Decimal(36_500), tax_rate=0.25), until)
    assert float(account_balance(sim, "Income Tax Expense")) == pytest.approx(0.25 * 100 * 100, abs=0.01)


def test_no_tax_on_losses_and_losses_reverse_earlier_tax() -> None:
    # The bond gains while yields sit at 2% and then loses when they jump to 5% on 1 July.
    operating = OperatingConfig(tax_rate=0.21)
    gains = _run(operating, datetime.date(2021, 6, 30), with_bond=True)
    taxed = float(account_balance(gains, "Income Tax Expense"))
    losses = _run(operating, datetime.date(2021, 7, 15), with_bond=True)
    pretax = (float(account_balance(losses, "Trading Income (FVTPL)"))
              + float(account_balance(losses, "Interest Income"))
              - float(account_balance(losses, "Interest Expense")))
    assert taxed > 0
    assert pretax < 0
    assert float(account_balance(losses, "Income Tax Expense")) == pytest.approx(0, abs=0.01)


def test_config_round_trips_through_json() -> None:
    config = OperatingConfig(noninterest_expense=Decimal("1.5"), noninterest_income=Decimal(2), tax_rate=0.21,
                             dividend_payout=0.3)
    assert OperatingConfig.from_json(config.to_json()) == config
    assert OperatingConfig.from_json(None) == OperatingConfig()


def test_tax_rate_must_be_a_fraction() -> None:
    with pytest.raises(ValueError, match="tax_rate"):
        OperatingConfig(tax_rate=21)


def test_dividends_pay_out_a_share_of_profit_after_tax() -> None:
    until = datetime.date(2021, 4, 13)  # 100 days of 100/day fee income
    sim = _run(OperatingConfig(noninterest_income=Decimal(36_500), tax_rate=0.2, dividend_payout=0.5), until)
    profit_after_tax = 10_000 * (1 - 0.2)
    assert float(account_balance(sim, "Dividends Paid")) == pytest.approx(0.5 * profit_after_tax, abs=0.01)
    assert float(account_balance(sim, "Cash and Cash Equivalents")) == pytest.approx(
        float(FUNDING) + 10_000 - 2_000 - 4_000, abs=0.01)


def test_dividends_already_paid_are_not_clawed_back() -> None:
    operating = OperatingConfig(dividend_payout=0.4)
    paid = float(account_balance(_run(operating, datetime.date(2021, 6, 30), with_bond=True), "Dividends Paid"))
    later = float(account_balance(_run(operating, datetime.date(2021, 7, 15), with_bond=True), "Dividends Paid"))
    assert paid > 0
    assert later == pytest.approx(paid, abs=0.01)


def test_payout_must_be_a_fraction() -> None:
    with pytest.raises(ValueError, match="dividend_payout"):
        OperatingConfig(dividend_payout=1.5)
