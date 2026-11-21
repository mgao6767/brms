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
    VARIABLE_RATE_LOAN = auto()
    MORTGAGE_BACKED_SECURITY = auto()


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
    AMORTIZED_COST = auto()


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
    PREMIUM_DISCOUNT_AMORTIZATION = auto()
    OPERATING_EXPENSE = auto()
    NONINTEREST_INCOME = auto()
    INCOME_TAX = auto()
    OTHER_ASSETS = auto()
    OTHER_LIABILITIES = auto()
    DIVIDEND = auto()
    INTANGIBLE_ASSETS = auto()


class MetricName(Enum):
    """Names of financial metrics."""

    TOTAL_ASSETS = auto()
    TOTAL_LIABILITIES = auto()
    TOTAL_EQUITY = auto()
    EQUITY_TO_ASSETS = auto()
    INTEREST_EARNING_ASSETS = auto()
    CET1_CAPITAL = auto()
    TIER1_CAPITAL = auto()
    TOTAL_CAPITAL = auto()
    CREDIT_RWA = auto()
    OPERATIONAL_RWA = auto()
    TOTAL_RWA = auto()
    CET1_RATIO = auto()
    TIER1_RATIO = auto()
    TOTAL_CAPITAL_RATIO = auto()
    LEVERAGE_RATIO = auto()
    NET_INTEREST_MARGIN = auto()
    ROA = auto()
    ROE = auto()
    EVE = auto()
    DELTA_EVE_WORST = auto()
    DELTA_EVE_WORST_TO_TIER1 = auto()
    ASSET_DURATION = auto()
    NII_SENSITIVITY_UP = auto()
    NII_SENSITIVITY_DOWN = auto()


class TxMeta(Enum):
    """Keys of the metadata pairs carried by a Transaction."""

    MEASUREMENT_BASIS = auto()  # value: MeasurementBasis
    SIDE = auto()  # value: InterestSide
    ACCRUED_INTEREST = auto()  # value: str(Decimal), accrued interest bought with a position
    ACCRUED_PORTION = auto()  # value: str(Decimal), receivable cleared by a settlement
    DIRECTION = auto()  # value: "gain" | "loss"
    CARRYING_VALUE = auto()  # value: str(Decimal), carrying value of a maturing position
    FINAL_PAYMENT = auto()  # value: bool, last scheduled principal payment of a loan
    RECYCLED_OCI = auto()  # value: str(Decimal), unrealised gain (+) or loss (-) moved from OCI to profit


class InterestSide(Enum):
    """Whether an interest transaction is income to the bank or an expense."""

    INCOME = auto()
    EXPENSE = auto()


class EntryKind(Enum):
    """Why a journal entry was posted: ordinary business, opening balances, or period-end closing."""

    NORMAL = auto()
    OPENING = auto()
    CLOSING = auto()
