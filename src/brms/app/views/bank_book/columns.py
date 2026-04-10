"""Column definitions for bank book views."""

from enum import IntEnum


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


CLASS_DISPLAY_NAMES: dict[str, str] = {
    "HTM": "Held-to-Maturity",
    "FVOCI": "Fair Value through OCI",
    "FVTPL": "Fair Value through P&L",
    "LOAN_AND_MORTGAGE": "Loans & Mortgages",
}

# Legacy aliases kept for backward compatibility
AssetColumns = BookColumns
LiabilityColumns = BookColumns
