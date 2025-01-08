import datetime

import pytest
import QuantLib as ql

from brms.instruments.fixed_rate_bond import FixedRateBond
from brms.instruments.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor
from brms.models.scenario import Scenario, ScenarioBuilder
from brms.utils import qldate_to_pydate


@pytest.fixture
def fixed_rate_bond():
    """Fixture to create a FixedRateBond instance."""
    face_value = 1000.0
    coupon_rate = 0.05
    issue_date = ql.Date(1, 1, 2020)
    maturity_date = ql.Date(1, 1, 2030)
    return FixedRateBond(
        face_value=face_value,
        coupon_rate=coupon_rate,
        issue_date=issue_date,
        maturity_date=maturity_date,
    )


def test_fixed_rate_bond_initialization(fixed_rate_bond):
    """Test the initialization of the FixedRateBond."""
    assert fixed_rate_bond.name == "5.00% 2030/1/1"
    assert fixed_rate_bond.instrument is not None


def test_fixed_rate_bond_notional(fixed_rate_bond):
    """Test the notional value calculation of the FixedRateBond."""
    date = datetime.date(2025, 1, 1)
    notional_value = fixed_rate_bond.notional(date)
    assert notional_value == 1000.0  # Assuming the bond has notional value of 1000 until maturity


def test_fixed_rate_bond_banking_book_valuation(fixed_rate_bond):
    """Test the valuation of the FixedRateBond using the BankingBookValuationVisitor."""
    visitor = BankingBookValuationVisitor()
    scenario = Scenario(date=datetime.date(2025, 1, 1))
    value = fixed_rate_bond.accept(visitor, scenario)
    assert value == 1000.0  # On banking book, value is the notional value

    scenario = Scenario(date=datetime.date(2030, 1, 1))
    value = fixed_rate_bond.accept(visitor, scenario)
    assert value == 0  # At maturity, value is 0


def test_fixed_rate_bond_trading_book_valuation_par(fixed_rate_bond):
    """Test the valuation of the FixedRateBond using the TradingBookValuationVisitor."""
    today = ql.Date(1, 1, 2020)
    day_counter = fixed_rate_bond.instrument.dayCounter()
    interest_rate = 0.05
    compounding = ql.Compounded
    compounding_frequency = ql.Semiannual
    flat_forward = ql.FlatForward(
        today,
        ql.QuoteHandle(ql.SimpleQuote(interest_rate)),
        day_counter,
        compounding,
        compounding_frequency,
    )
    term_structure = ql.YieldTermStructureHandle(flat_forward)

    scenario_builder = ScenarioBuilder(qldate_to_pydate(today))
    scenario_builder.with_term_structure(term_structure)
    scenario = scenario_builder.build()

    visitor = TradingBookValuationVisitor()
    value = fixed_rate_bond.accept(visitor, scenario)
    assert value == 1000.0  # At par when issued


def test_fixed_rate_bond_trading_book_valuation_not_par(fixed_rate_bond):
    """Test the valuation of the FixedRateBond using the TradingBookValuationVisitor.

    5 years to maturity. Yield curve is flat at 6% p.a. (semi-annually compounded).
    Coupon = 1000*0.05/2 = 25
    NPV = 25/0.03 * (1 - 1/(1+0.03)^10) + 1000/(1+0.03)^10 = 957.348985816
    """
    today = ql.Date(1, 1, 2025)
    day_counter = fixed_rate_bond.instrument.dayCounter()
    interest_rate = 0.06
    compounding = ql.Compounded
    compounding_frequency = ql.Semiannual
    flat_forward = ql.FlatForward(
        today,
        ql.QuoteHandle(ql.SimpleQuote(interest_rate)),
        day_counter,
        compounding,
        compounding_frequency,
    )
    term_structure = ql.YieldTermStructureHandle(flat_forward)

    scenario_builder = ScenarioBuilder(qldate_to_pydate(today))
    scenario_builder.with_term_structure(term_structure)
    scenario = scenario_builder.build()

    visitor = TradingBookValuationVisitor()
    value = fixed_rate_bond.accept(visitor, scenario)
    assert value == pytest.approx(957.348985816)


if __name__ == "__main__":
    pytest.main()
