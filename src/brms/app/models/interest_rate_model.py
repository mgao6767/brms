"""Table model for benchmark interest rates (single-column for Prime, extensible)."""

from __future__ import annotations

import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class InterestRateModel(QAbstractTableModel):
    """Rows = dates, columns = benchmark rate names (e.g. 'Prime')."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dates: list[datetime.date] = []
        self._columns: list[str] = []
        self._data: dict[datetime.date, list[float]] = {}

    def reset(self) -> None:
        self.beginResetModel()
        self._dates.clear()
        self._columns.clear()
        self._data.clear()
        self.endResetModel()

    def reference_dates(self) -> list[datetime.date]:
        return list(self._dates)

    def update_from_dataframe(self, benchmarks_df) -> None:
        """Load from a date-indexed DataFrame (columns like 'DPRIME')."""
        self.beginResetModel()
        self._columns = list(benchmarks_df.columns)
        self._dates = [idx.date() if hasattr(idx, "date") else idx for idx in benchmarks_df.index]
        self._data = {}
        for idx, row in benchmarks_df.iterrows():
            dt = idx.date() if hasattr(idx, "date") else idx
            self._data[dt] = [row[c] for c in self._columns]
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return len(self._dates)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return len(self._columns)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            dt = self._dates[index.row()]
            values = self._data.get(dt, [])
            if index.column() < len(values):
                return values[index.column()]
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                label = self._columns[section] if section < len(self._columns) else ""
                return label.replace("DPRIME", "Prime (%)")
            if orientation == Qt.Vertical:
                return self._dates[section].strftime("%Y-%m-%d")
        return None
