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


class MockInstrumentOnAssets(MockInstrument):
    def accept(self, visitor, scenario):
        return 200


class MockInstrumentOnLiabilities(MockInstrument):
    def accept(self, visitor, scenario):
        return 100


@pytest.fixture
def bank():
    return Bank()


@pytest.fixture
def instrument_banking():
    return MockInstrument(name="Banking Instrument", book_type=BookType.BANKING_BOOK)


@pytest.fixture
def instrument_trading():
    return MockInstrument(name="Trading Instrument", book_type=BookType.TRADING_BOOK)


@pytest.fixture
def instrument_assets():
    return MockInstrumentOnAssets(name="Instrument as Assets", book_type=BookType.BANKING_BOOK)


@pytest.fixture
def instrument_liabilities():
    return MockInstrumentOnLiabilities(name="Instrument as Liabilities", book_type=BookType.BANKING_BOOK)


def test_add_instrument_to_assets(bank, instrument_banking):
    """Test adding an instrument to the bank's assets."""
    bank.assets.add(instrument_banking)
    assert instrument_banking in bank.assets._instruments


def test_add_instrument_to_liabilities(bank, instrument_trading):
    """Test adding an instrument to the bank's liabilities."""
    bank.liabilities.add(instrument_trading)
    assert instrument_trading in bank.liabilities._instruments


def test_valuation(bank, instrument_assets, instrument_liabilities):
    """Test the valuation method."""
    bank.assets.add(instrument_assets)  # Assume a value of 200
    bank.assets.add(instrument_assets)  # Assume a value of 200
    bank.liabilities.add(instrument_liabilities)  # Assume a value of 100

    scenario = Scenario(date=datetime.date(2025, 1, 1))
    bank.valuation(scenario)

    assert bank.assets.value == 400
    assert bank.liabilities.value == 100
    assert bank.common_equity == 300


def test_banking_book_assets(bank, instrument_banking, instrument_trading):
    """Test the banking_book_assets method."""
    bank.assets.add(instrument_banking)
    bank.assets.add(instrument_trading)

    banking_book_assets = list(bank.banking_book_assets())
    assert instrument_banking in banking_book_assets
    assert instrument_trading not in banking_book_assets


def test_trading_book_assets(bank, instrument_banking, instrument_trading):
    """Test the trading_book_assets method."""
    bank.assets.add(instrument_banking)
    bank.assets.add(instrument_trading)

    trading_book_assets = list(bank.trading_book_assets())
    assert instrument_trading in trading_book_assets
    assert instrument_banking not in trading_book_assets


if __name__ == "__main__":
    pytest.main()
