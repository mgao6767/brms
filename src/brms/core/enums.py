"""Enums for the BRMS core module."""

from enum import Enum, auto


class InstrumentType(Enum):
    """Types of financial instruments."""

    CASH = auto()
    DEPOSIT = auto()
    COMMON_EQUITY = auto()
    FIXED_RATE_BOND = auto()
    TREASURY_NOTE = auto()
    TREASURY_BOND = auto()
    COVERED_BOND = auto()
    MORTGAGE = auto()
    RESIDENTIAL_MORTGAGE = auto()
    COMMERCIAL_MORTGAGE = auto()
    AMORTIZING_FIXED_RATE_LOAN = auto()
    PERSONAL_LOAN = auto()
    CREDIT_CARD = auto()
    COMMITMENT = auto()
    REPURCHASE_AGREEMENT = auto()
    LETTER_OF_CREDIT = auto()


class BookType(Enum):
    """Types of books for position classification."""

    BANKING = auto()
    TRADING = auto()


class PositionSide(Enum):
    """Sides of a position."""

    LONG = auto()
    SHORT = auto()


class PositionStatus(Enum):
    """Status of a position."""

    OPEN = auto()
    CLOSED = auto()


class MeasurementBasis(Enum):
    """IFRS 9 measurement category for financial instruments."""

    AMORTIZED_COST = auto()
    FVOCI = auto()
    FVTPL = auto()
    NA = auto()  # deposits, equity, cash — not classified


class ValuationType(Enum):
    """Types of valuation metrics."""

    FAIR_VALUE = auto()
    CARRYING_VALUE = auto()
    ACCRUED_INTEREST = auto()
    NOTIONAL = auto()


class TransactionType(Enum):
    """Types of transactions."""

    INTEREST_PAYMENT = auto()
    MARK_TO_MARKET = auto()
    MATURITY_SETTLEMENT = auto()
    COUPON_PAYMENT = auto()
    LOAN_DISBURSEMENT = auto()
    LOAN_REPAYMENT = auto()
    DEPOSIT_RECEIVED = auto()
    DEPOSIT_WITHDRAWAL = auto()
    EQUITY_ISSUANCE = auto()
    SECURITY_PURCHASE = auto()
    SECURITY_SALE = auto()
    AMORTIZATION = auto()
    INTEREST_EXPENSE = auto()
    PRINCIPAL_PAYMENT = auto()
    REVALUATION = auto()
    INTEREST_ACCRUAL = auto()
    INTEREST_SETTLEMENT = auto()
    OPENING_BALANCE = auto()


class MetricName(Enum):
    """Names of financial metrics."""

    TOTAL_ASSETS = auto()
    TOTAL_LIABILITIES = auto()
    TOTAL_EQUITY = auto()
    CET1_CAPITAL = auto()
    CET1_RATIO = auto()
    CREDIT_RWA = auto()
    OPERATIONAL_RWA = auto()
    LEVERAGE_RATIO = auto()
    NET_INTEREST_MARGIN = auto()
    ROA = auto()
    ROE = auto()
