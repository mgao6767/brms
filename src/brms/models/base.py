from enum import Enum


class BookType(Enum):
    """Enumeration for different types of books.

    Before a bank can calculate RWA for credit risk and RWA for market risk, it must follow the requirements of RBC25 to
    identify the instruments that are in the trading book. The banking book comprises all instruments that are not in
    the trading book and all other assets of the bank.
    """

    BANKING_BOOK = "Banking Book"
    TRADING_BOOK = "Trading Book"


class InstrumentClass(Enum):
    HTM = "HTM"
    FVOCI = "FVOCI"
    FVTPL = "FVTPL"
    LOAN_AND_MORTGAGE = "Loan"
    NA = ""


class BalanceSheetCategory(Enum):
    """Enumeration for the category of the balance sheet an instrument is on."""

    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"


class ScenarioData(Enum):
    """Enumeration for raw scenario data loaded from sources."""

    TREASURY_YIELDS = "treasury_yields"


class ScenarioMetric(Enum):
    """Enumeration for metrics available in a given scenario."""

    YIELD_TERM_STRUCTURE = "Yield Term Structure"
