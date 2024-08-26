from datetime import date
from typing import List, Tuple

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class YieldCurveModel(QAbstractTableModel):
    # The allowed maturities

    # fmt: off
    # MATURITIES = ["1M", "2M", "3M", "4M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
    MATURITIES = ["1 Mo", "2 Mo", "3 Mo", "4 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]

    def __init__(self, parent=None):
        self.yield_data = {}
        # Example data: {date: [(maturity, yield), ...]}
        # self.yield_data = {
        #     date(2023, 1, 1): [("1M", 0.5), ("2M", 0.55), ("3M", 0.6), ("4M", 0.65), ("6M", 0.7), 
        #                        ("1Y", 0.75), ("2Y", 0.8), ("3Y", 0.85), ("5Y", 0.9), ("7Y", 0.95), 
        #                        ("10Y", 1.0), ("20Y", 1.1), ("30Y", 1.2)],
        #     date(2023, 2, 1): [("1M", 0.6), ("2M", 0.65), ("3M", 0.7), ("4M", 0.75), ("6M", 0.8), 
        #                        ("1Y", 0.85), ("2Y", 0.9), ("3Y", 0.95), ("5Y", 1.0), ("7Y", 1.05), 
        #                        ("10Y", 1.1), ("20Y", 1.2), ("30Y", 1.3)],
        # }
        super().__init__(parent)

        self.dates = list(self.yield_data.keys())
        self.maturities = self.MATURITIES

    def reset(self):
        self.yield_data.clear()
        self.dates.clear()
        # To trigger update of view
        self.update_yield_data(self.yield_data)

    def get_yield_data(self, query_date: date) -> List[Tuple[str, float]]:
        """
        Given a date, return the yield data for various maturities.
        
        :param query_date: The date for which to fetch the yield data.
        :return: A list of tuples containing (maturity, yield).
        """
        return self.yield_data.get(query_date, [])

    def update_yield_data(self, new_yield_data: dict):
        """
        Update the yield data and notify the view that the data has changed.
        
        :param new_yield_data: The new yield data to update.
        """
        self.beginResetModel()
        self.yield_data = new_yield_data
        self.dates = list(self.yield_data.keys())
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.dates)

    def columnCount(self, parent=QModelIndex()):
        return len(self.maturities)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            query_date = self.dates[index.row()]
            maturity = self.maturities[index.column()]
            yield_data = self.get_yield_data(query_date)
            for mat, yld in yield_data:
                if mat == maturity:
                    return yld
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.maturities[section]
            elif orientation == Qt.Vertical:
                return self.dates[section].strftime("%Y-%m-%d")
        return None
