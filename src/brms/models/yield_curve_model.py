import datetime

import QuantLib as ql
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class YieldCurve(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._yield_curve: ql.YieldTermStructure | None = None
        self._yield_data: dict[datetime.date, list[tuple[str, float]]] = {}
        self._reference_dates: list[datetime.date] = []
        self._maturities: list[str] = []

    def reset(self) -> None:
        self.beginResetModel()
        # TODO
        self.endResetModel()

    def reference_dates(self):
        return self._reference_dates

    def yield_curve(self) -> ql.YieldTermStructure:
        return self._yield_curve

    def get_yield_data(self, query_date: datetime.date) -> list[tuple[str, float]]:
        """Given a date, return the yield data for various maturities.

        :param query_date: The date for which to fetch the yield data.
        :return: A list of tuples containing (maturity, yield).
        """
        return self._yield_data.get(query_date, [])

    def update_yield_data(self, new_yield_data: dict[datetime.date, list[tuple[str, float]]]) -> None:
        """Update the yield data and notify the view that the data has changed.

        An example key-value pair of the `new_yield_data` dict is:
        `date(2023, 1, 1): [("1M", 0.5), ("2M", 0.55), ...]`

        :param new_yield_data: The new yield data to update.
        :type new_yield_data: dict
        """
        self.beginResetModel()
        self._yield_data = new_yield_data
        self._reference_dates = list(new_yield_data.keys())
        if new_yield_data:
            self._maturities = [mat for mat, _ in next(iter(new_yield_data.values()))]
        else:
            self._maturities = []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._reference_dates)

    def columnCount(self, parent=QModelIndex()):
        return len(self._maturities)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            query_date = self._reference_dates[index.row()]
            yield_data = self._yield_data.get(query_date)
            _, rate = yield_data[index.column()]
            return rate
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._maturities[section]
            elif orientation == Qt.Vertical:
                return self._reference_dates[section].strftime("%Y-%m-%d")
        return None
