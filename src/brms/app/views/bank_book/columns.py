"""Column definitions for bank book views."""

from enum import IntEnum

from brms.core.enums import InstrumentType, MeasurementBasis


class ColumnOrder(IntEnum):
    """Base class for column order enumerations.

    IntEnum is used to enable sorting.
    """


class BookColumns(ColumnOrder):
    """Unified columns for bank book trees (assets and liabilities share a tree)."""

    ID = 0
    Name = 1
    Class = 2
    Value = 3


BOOK_COLUMN_HEADERS = [col.name for col in BookColumns]


MEASUREMENT_BASIS_DISPLAY: dict[MeasurementBasis, str] = {
    MeasurementBasis.AMORTIZED_COST: "Amortized Cost",
    MeasurementBasis.FVOCI: "Fair Value through OCI",
    MeasurementBasis.FVTPL: "Fair Value through P&L",
}

AMORTIZED_COST_SUB_GROUPS: dict[InstrumentType, str] = {
    InstrumentType.TREASURY_NOTE: "Held-to-Maturity",
    InstrumentType.TREASURY_BOND: "Held-to-Maturity",
    InstrumentType.FIXED_RATE_BOND: "Held-to-Maturity",
    InstrumentType.COVERED_BOND: "Held-to-Maturity",
    InstrumentType.RESIDENTIAL_MORTGAGE: "Loans & Mortgages",
    InstrumentType.COMMERCIAL_MORTGAGE: "Loans & Mortgages",
    InstrumentType.MORTGAGE: "Loans & Mortgages",
    InstrumentType.AMORTIZING_FIXED_RATE_LOAN: "Loans & Mortgages",
    InstrumentType.PERSONAL_LOAN: "Loans & Mortgages",
}

# Legacy aliases kept for backward compatibility
AssetColumns = BookColumns
LiabilityColumns = BookColumns
