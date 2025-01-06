import datetime

import pytest
import QuantLib as ql

from brms.instruments.fixed_rate_bond import FixedRateBond
from brms.instruments.valuation import ValuationVisitor, BankingBookValuationVisitor
from brms.models.scenario import Scenario


class MockValuationVisitor(ValuationVisitor):
    def value_fixed_rate_bond(self, instrument, scenario):
        return 100.0  # Mock value for testing


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


def test_fixed_rate_bond_accept_valuation_visitor(fixed_rate_bond):
    """Test the accept method of the FixedRateBond."""
    visitor = MockValuationVisitor()
    scenario = Scenario(date=datetime.date(2025, 1, 1))
    value = fixed_rate_bond.accept(visitor, scenario)
    assert value == 100.0  # Mock value returned by the visitor


def test_fixed_rate_bond_banking_book_valuation(fixed_rate_bond):
    """Test the valuation of the FixedRateBond using the BankingBookValuationVisitor."""
    visitor = BankingBookValuationVisitor()
    scenario = Scenario(date=datetime.date(2025, 1, 1))
    value = fixed_rate_bond.accept(visitor, scenario)
    assert value == 1000.0  # On banking book, value is the notional value

    scenario = Scenario(date=datetime.date(2030, 1, 1))
    value = fixed_rate_bond.accept(visitor, scenario)
    assert value == 0  # At maturity, value is 0


@pytest.mark.skip(reason="Test not yet implemented")
def test_fixed_rate_bond_trading_book_valuation(fixed_rate_bond):
    """Test the valuation of the FixedRateBond using the TradingBookValuationVisitor."""


if __name__ == "__main__":
    pytest.main()
