"""Define the `Bank` class."""

from collections.abc import Generator
from typing import Any

from brms.instruments.base import CompositeInstrument, Instrument
from brms.instruments.common_equity import CommonEquity
from brms.instruments.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor
from brms.models.base import BookType
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

    def banking_book_assets(self) -> Generator[Instrument, Any, None]:
        """Yield all banking book assets."""
        for instrument in self.assets:
            if instrument.book_type == BookType.BANKING_BOOK:
                yield instrument

    def trading_book_assets(self) -> Generator[Instrument, Any, None]:
        """Yield all trading book assets."""
        for instrument in self.assets:
            if instrument.book_type == BookType.TRADING_BOOK:
                yield instrument

    def valuation(self, scenario: Scenario) -> None:
        """Perform valuation on banking and trading book instruments."""
        banking_book_visitor = BankingBookValuationVisitor(scenario)
        trading_book_visitor = TradingBookValuationVisitor(scenario)

        assets_value = 0.0
        liabilities_value = 0.0
        assets_value += self.assets.accept(banking_book_visitor)
        assets_value += self.assets.accept(trading_book_visitor)
        liabilities_value += self.liabilities.accept(banking_book_visitor)
        liabilities_value += self.liabilities.accept(trading_book_visitor)

        # Store the computed the value
        self.assets.value = assets_value
        self.liabilities.value = liabilities_value
        # FIXME: EquityComposite's value is not updated
        self.common_equity = self.assets.value - self.liabilities.value
