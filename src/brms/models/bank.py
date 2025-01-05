"""Define the `Bank` class."""

from collections.abc import Generator

from brms.instruments.base import CompositeInstrument, Instrument
from brms.instruments.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor
from brms.models.base import BookType


class AssetComposite(CompositeInstrument):
    """Composite class for assets."""


class LiabilityComposite(CompositeInstrument):
    """Composite class for liabilities."""


class EquityComposite(CompositeInstrument):
    """Composite class for equities."""


class Bank:
    """Class representing a bank with assets, liabilities, and equities."""

    def __init__(self) -> None:
        """Initialize the Bank with assets, liabilities, and equities."""
        self.assets = AssetComposite(name="Assets")
        self.liabilities = LiabilityComposite(name="Liabilities")
        self.equities = EquityComposite(name="Equities")

    def banking_book_instruments(self) -> Generator[Instrument, None, None]:
        """Yield instruments in the banking book."""
        for instrument in self.assets:
            if instrument.book_type == BookType.BANKING_BOOK:
                yield instrument
        for instrument in self.liabilities:
            if instrument.book_type == BookType.BANKING_BOOK:
                yield instrument

    def trading_book_instruments(self) -> Generator[Instrument, None, None]:
        """Yield instruments in the trading book."""
        for instrument in self.assets:
            if instrument.book_type == BookType.TRADING_BOOK:
                yield instrument
        for instrument in self.liabilities:
            if instrument.book_type == BookType.TRADING_BOOK:
                yield instrument

    def valuation(self, scenario: dict) -> None:
        """Perform valuation on banking and trading book instruments."""
        # TODO: Equities' valuation

        banking_book_visitor = BankingBookValuationVisitor()
        trading_book_visitor = TradingBookValuationVisitor()

        for instrument in self.banking_book_instruments():
            instrument.accept(banking_book_visitor, scenario)
        for instrument in self.trading_book_instruments():
            instrument.accept(trading_book_visitor, scenario)
