"""Column definitions for bank book views."""

from enum import IntEnum


class ColumnOrder(IntEnum):
    """Base class for column order enumerations.

    IntEnum is used to enable sorting.
    """


class AssetColumns(ColumnOrder):
    ID = 0
    Asset = 1
    Class = 2
    Value = 3


class LiabilityColumns(ColumnOrder):
    ID = 0
    Liability = 1
    Class = 2
    Value = 3


BANKING_BOOK_ASSET_COLUMNS = [col.name for col in AssetColumns]
BANKING_BOOK_LIABILITY_COLUMNS = [col.name for col in LiabilityColumns]
TRADING_BOOK_ASSET_COLUMNS = [col.name for col in AssetColumns]
TRADING_BOOK_LIABILITY_COLUMNS = [col.name for col in LiabilityColumns]
