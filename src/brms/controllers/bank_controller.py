from brms.controllers.bank_book_controller import BankingBookController, TradingBookController
from brms.controllers.base import BRMSController
from brms.controllers.inspector_controller import InspectorController
from brms.instruments.base import Instrument
from brms.models.bank import Bank
from brms.models.bank_book import Position
from brms.views.bank_book_widget import BRMSBankingBookWidget, BRMSTradingBookWidget


class BankController(BRMSController):
    """Controller for managing bank operations, including banking and trading books."""

    def __init__(
        self,
        bank: Bank,
        banking_book_view: BRMSBankingBookWidget,
        trading_book_view: BRMSTradingBookWidget,
        inspector_ctrl: InspectorController,
    ) -> None:
        super().__init__()
        self.bank = bank
        self.banking_book_view = banking_book_view
        self.trading_book_view = trading_book_view
        # Controllers passed in
        self.inspector_ctrl = inspector_ctrl
        # Sub controllers
        # fmt: off
        self.banking_book_ctrl = BankingBookController(self.bank.banking_book, self.banking_book_view, self.inspector_ctrl)
        self.trading_book_ctrl = TradingBookController(self.bank.trading_book, self.trading_book_view, self.inspector_ctrl)
        # fmt: on
        # Connect signals
        self.connect_signals()

    def add_instrument_to_banking_book(self, instrument: Instrument, position: Position) -> None:
        """Add an instrument to banking book based on position."""
        self.banking_book_ctrl.add_instrument(instrument, position)

    def add_instrument_to_trading_book(self, instrument: Instrument, position: Position) -> None:
        """Add an instrument to trading book based on position."""
        self.trading_book_ctrl.add_instrument(instrument, position)

    def remove_instrument_from_banking_book(self, instrument: Instrument, position: Position) -> None:
        """Remove an instrument from banking book based on position."""
        self.banking_book_ctrl.remove_instrument(instrument, position)

    def remove_instrument_from_trading_book(self, instrument: Instrument, position: Position) -> None:
        """Remove an instrument from trading book based on position."""
        self.trading_book_ctrl.remove_instrument(instrument, position)

    def connect_signals(self) -> None:
        """Connect signals to their respective slots."""
        pass
