"""Define the `Bank` class."""

from enum import Enum

from brms.instruments.base import CompositeInstrument


class BookType(Enum):
    """Enumeration for different types of books.

    Before a bank can calculate RWA for credit risk and RWA for market risk, it must follow the requirements of RBC25 to
    identify the instruments that are in the trading book. The banking book comprises all instruments that are not in
    the trading book and all other assets of the bank.
    """

    BANKING_BOOK = "Banking Book"
    TRADING_BOOK = "Trading Book"


class BalanceSheetCategory(Enum):
    """Enumeration for the category of the balance sheet an instrument is on."""

    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"


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
