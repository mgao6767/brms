import pytest

from brms.commands.command import (
    AddInstrumentCommand,
    CompositeCommand,
    RemoveInstrumentCommand,
    SetInstrumentBookTypeCommand,
)
from brms.instruments.base import Instrument
from brms.instruments.visitors import Visitor
from brms.models.bank import Bank
from brms.models.base import BalanceSheetCategory, BookType


class MockInstrument(Instrument):
    def __init__(self, name: str):
        super().__init__(name)
        self._book_type = None

    def accept(self, visitor: Visitor):
        pass


@pytest.fixture
def bank():
    return Bank()


@pytest.fixture
def instrument():
    return MockInstrument(name="Test Instrument")


def test_set_instrument_book_type_command(instrument):
    """Test the SetInstrumentBookTypeCommand."""
    command = SetInstrumentBookTypeCommand(instrument, BookType.BANKING_BOOK)
    command.execute()
    assert instrument.book_type == BookType.BANKING_BOOK
    command.undo()
    assert instrument.book_type is None


def test_add_instrument_command(bank, instrument):
    """Test the AddInstrumentCommand."""
    command = AddInstrumentCommand(bank, instrument, BalanceSheetCategory.ASSET)
    command.execute()
    assert instrument in bank.assets._instruments
    command.undo()
    assert instrument not in bank.assets._instruments


def test_remove_instrument_command(bank, instrument):
    """Test the RemoveInstrumentCommand."""
    add_command = AddInstrumentCommand(bank, instrument, BalanceSheetCategory.ASSET)
    add_command.execute()
    assert instrument in bank.assets._instruments

    remove_command = RemoveInstrumentCommand(bank, instrument, BalanceSheetCategory.ASSET)
    remove_command.execute()
    assert instrument not in bank.assets._instruments
    remove_command.undo()
    assert instrument in bank.assets._instruments


def test_composite_command(bank, instrument):
    """Test the CompositeCommand with SetInstrumentBookTypeCommand and AddInstrumentCommand."""
    composite_command = CompositeCommand()

    set_book_type_command = SetInstrumentBookTypeCommand(instrument, BookType.TRADING_BOOK)
    add_instrument_command = AddInstrumentCommand(bank, instrument, BalanceSheetCategory.ASSET)

    composite_command.add_command(set_book_type_command)
    composite_command.add_command(add_instrument_command)

    composite_command.execute()
    assert instrument.book_type == BookType.TRADING_BOOK
    assert instrument in bank.assets._instruments

    composite_command.undo()
    assert instrument.book_type is None
    assert instrument not in bank.assets._instruments


if __name__ == "__main__":
    pytest.main([__file__])
