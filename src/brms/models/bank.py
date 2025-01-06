"""Define the `Bank` class."""

from collections.abc import Generator

from brms.instruments.base import CompositeInstrument, Instrument
from brms.instruments.common_equity import CommonEquity
from brms.instruments.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor
from brms.models.base import BalanceSheetCategory, BookType
from brms.models.scenario import Scenario


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
        # A bank starts with some common equity
        self._common_equity = CommonEquity("Common Equity")
        self.equities.add(self._common_equity)

    @property
    def common_equity(self) -> float:
        """Get the value of common equity of the bank."""
        return self._common_equity.value

    @common_equity.setter
    def common_equity(self, value: float) -> None:
        self._common_equity.value = value

    def instruments(self, book_type: BookType, category: BalanceSheetCategory) -> Generator[Instrument, None, None]:
        """Yield instruments in the given book and balance sheet category."""
        match category:
            case BalanceSheetCategory.ASSET:
                instruments: CompositeInstrument = self.assets
            case BalanceSheetCategory.LIABILITY:
                instruments: CompositeInstrument = self.liabilities
            case BalanceSheetCategory.EQUITY:
                instruments: CompositeInstrument = self.equities
        for instrument in instruments:
            if instrument.book_type == book_type:
                yield instrument

    def valuation(self, scenario: Scenario) -> None:
        """Perform valuation on banking and trading book instruments."""
        assets_value = 0.0
        liabilities_value = 0.0
        banking_book_visitor = BankingBookValuationVisitor()
        trading_book_visitor = TradingBookValuationVisitor()

        for instrument in self.instruments(BookType.BANKING_BOOK, BalanceSheetCategory.ASSET):
            assets_value += instrument.accept(banking_book_visitor, scenario)
        for instrument in self.instruments(BookType.TRADING_BOOK, BalanceSheetCategory.ASSET):
            assets_value += instrument.accept(banking_book_visitor, scenario)
        for instrument in self.instruments(BookType.BANKING_BOOK, BalanceSheetCategory.LIABILITY):
            liabilities_value += instrument.accept(banking_book_visitor, scenario)
        for instrument in self.instruments(BookType.TRADING_BOOK, BalanceSheetCategory.LIABILITY):
            liabilities_value += instrument.accept(trading_book_visitor, scenario)

        self.common_equity = assets_value - liabilities_value
