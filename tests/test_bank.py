import datetime

import pytest

from brms.instruments.base import Instrument
from brms.models.bank import Bank
from brms.models.base import BookType
from brms.models.scenario import Scenario


class MockInstrument(Instrument):
    def __init__(self, name: str, book_type: BookType):
        super().__init__(name)
        self._book_type = book_type

    def accept(self, visitor, scenario):
        pass

    @property
    def book_type(self):
        return self._book_type

    @book_type.setter
    def book_type(self, book_type):
        self._book_type = book_type


@pytest.fixture
def bank():
    return Bank()


@pytest.fixture
def instrument_banking():
    return MockInstrument(name="Banking Instrument", book_type=BookType.BANKING_BOOK)


@pytest.fixture
def instrument_trading():
    return MockInstrument(name="Trading Instrument", book_type=BookType.TRADING_BOOK)


def test_add_instrument_to_assets(bank, instrument_banking):
    """Test adding an instrument to the bank's assets."""
    bank.assets.add(instrument_banking)
    assert instrument_banking in bank.assets._instruments


def test_add_instrument_to_liabilities(bank, instrument_trading):
    """Test adding an instrument to the bank's liabilities."""
    bank.liabilities.add(instrument_trading)
    assert instrument_trading in bank.liabilities._instruments


def test_instruments_by_book_type(bank, instrument_banking, instrument_trading):
    """Test retrieving instruments by book type."""
    bank.assets.add(instrument_banking)
    bank.liabilities.add(instrument_trading)

    banking_instruments = list(bank.instruments(BookType.BANKING_BOOK))
    trading_instruments = list(bank.instruments(BookType.TRADING_BOOK))

    assert instrument_banking in banking_instruments
    assert instrument_trading in trading_instruments


@pytest.mark.skip("Not yet implemented")
def test_valuation(bank, instrument_banking, instrument_trading):
    """Test the valuation method."""
    bank.assets.add(instrument_banking)
    bank.liabilities.add(instrument_trading)

    scenario = Scenario(date=datetime.date(2025, 1, 1))
    bank.valuation(scenario)

    assert True


if __name__ == "__main__":
    pytest.main()
