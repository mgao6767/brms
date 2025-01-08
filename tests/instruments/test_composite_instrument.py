import datetime

import pytest

from brms.instruments.base import CompositeInstrument, Instrument
from brms.instruments.valuation import BankingBookValuationVisitor, ValuationVisitor
from brms.models.base import BookType
from brms.models.scenario import Scenario


class MockInstrument(Instrument):
    def __init__(self, name: str, book_type: BookType):
        super().__init__(name)
        self._book_type = book_type

    def accept(self, visitor: ValuationVisitor, scenario: Scenario):
        return 100.0  # Mock value for testing. Otherwise visitor.visit(self, scenario)

    @property
    def book_type(self):
        return self._book_type

    @book_type.setter
    def book_type(self, book_type):
        self._book_type = book_type


@pytest.fixture
def composite_instrument():
    return CompositeInstrument(name="Composite Instrument")


@pytest.fixture
def instrument_banking():
    return MockInstrument(name="Banking Instrument", book_type=BookType.BANKING_BOOK)


@pytest.fixture
def instrument_trading():
    return MockInstrument(name="Trading Instrument", book_type=BookType.TRADING_BOOK)


def test_add_instrument(composite_instrument, instrument_banking):
    """Test adding an instrument to the composite."""
    composite_instrument.add(instrument_banking)
    assert instrument_banking in composite_instrument._instruments


def test_remove_instrument(composite_instrument, instrument_banking):
    """Test removing an instrument from the composite."""
    composite_instrument.add(instrument_banking)
    composite_instrument.remove(instrument_banking)
    assert instrument_banking not in composite_instrument._instruments


def test_is_composite(composite_instrument):
    """Test the is_composite method."""
    assert composite_instrument.is_composite() is True


def test_accept(composite_instrument, instrument_banking, instrument_trading):
    """Test the accept method."""
    composite_instrument.add(instrument_banking)
    composite_instrument.add(instrument_banking)
    composite_instrument.add(instrument_trading)
    scenario = Scenario(date=datetime.date(2025, 1, 1))
    visitor = BankingBookValuationVisitor()
    total_value = composite_instrument.accept(visitor, scenario)
    assert total_value == 200.0  # 2 instruments on banking book, each valued at 100


def test_iter(composite_instrument, instrument_banking, instrument_trading):
    """Test the iterator method."""
    composite_instrument.add(instrument_banking)
    composite_instrument.add(instrument_trading)
    composite_instrument.add(instrument_trading)
    instruments = list(iter(composite_instrument))
    assert len(instruments) == 3
    assert instrument_banking in instruments
    assert instrument_trading in instruments


if __name__ == "__main__":
    pytest.main()
