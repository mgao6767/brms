from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QItemSelectionModel, Qt

from brms.app.controllers.base import BRMSController
from brms.app.models.yield_curve_model import YieldCurve
from brms.core.events import DateAdvanced
from brms.core.services.yield_curve_service import YieldCurveService

if TYPE_CHECKING:
    import pandas as pd

    from brms.app.views.yield_curve import BRMSYieldCurveWidget
    from brms.core.events import EventBus
    from brms.core.stores.market_data_store import MarketDataStore


class YieldCurveController(BRMSController):
    def __init__(self, view: BRMSYieldCurveWidget, event_bus: EventBus, market_data: MarketDataStore) -> None:
        super().__init__()
        self.model = YieldCurve()  # model inside controller because it's just a data container
        self.view = view
        self._event_bus = event_bus
        self._market_data = market_data

        self.view.set_model(self.model)

        # Connect the selection changed signal to the slot
        # fmt: off
        self.view.visibility_changed.connect(self.update_plot)
        self.view.table_view.selectionModel().selectionChanged.connect(self.update_plot)
        self.view.plot_widget.rescale_checkbox.stateChanged.connect(self.update_plot)
        self.view.plot_widget.grid_checkbox.stateChanged.connect(self.update_plot)
        # fmt: on

        self._event_bus.subscribe(DateAdvanced, self._on_date_advanced)

    def reset(self):
        self.model.reset()
        self.clear_plot()

    def init(self) -> None:
        """Initialize yield curve data from market data store."""
        if self._market_data.has_frame("yields"):
            self.init_from_dataframe(self._market_data.get_frame("yields"))
            # Hide all rows initially — they are revealed as the simulation advances
            self._hide_future_rows(None)

    def set_current_selection(self, row: int, column: int):
        """Set the current selection of the table_view.

        :param row: The row index of the selection.
        :param column: The column index of the selection.
        """
        model_index = self.model.index(row, column)
        selection_model = self.view.table_view.selectionModel()
        selection_model.setCurrentIndex(
            model_index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
        )

    def get_all_dates(self) -> list[datetime.date]:
        """Return a list of all dates associated with the yields data."""
        return self.model.reference_dates()

    def get_date_from_selection(self):
        indexes = self.view.table_view.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        model = self.model
        # Retrieve the date from the vertical header
        date_str = model.headerData(row, Qt.Vertical)
        return datetime.datetime.strptime(date_str, "%Y-%m-%d")

    def get_yields_from_selection(self):
        indexes = self.view.table_view.selectionModel().selectedRows()
        if not indexes:
            return None

        row = indexes[0].row()
        model = self.model

        # Retrieve the date from the vertical header
        date_str = model.headerData(row, Qt.Vertical)
        reference_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")

        # Retrieve the maturities from the horizontal header
        maturity_labels = np.array([model.headerData(col, Qt.Horizontal) for col in range(model.columnCount())])

        # Retrieve the yields for the selected row
        yields = np.array([model.index(row, col).data() for col in range(model.columnCount())])

        # Filter out NaN values
        valid_indices = ~np.isnan(yields)

        return reference_date, maturity_labels[valid_indices], yields[valid_indices]

    def clear_plot(self):
        self.view.plot_widget.clear_plot()

    def update_plot(self):
        # Update only when the yield curve widget is visible
        if not self.view.is_visible:
            return
        yield_data = self.get_yields_from_selection()
        if yield_data is None:
            return
        ref_date, maturity_labels, yields = yield_data

        plot_data = YieldCurveService.compute_plot_data(ref_date.date(), maturity_labels.tolist(), yields.tolist())

        rescale_y = self.view.plot_widget.rescale_checkbox.isChecked()
        show_grid = self.view.plot_widget.grid_checkbox.isChecked()
        self.view.plot_widget.update_plot(
            plot_data.par_dates, plot_data.par_rates, plot_data.zero_dates, plot_data.zero_rates,
            plot_data.title, rescale_y, show_grid,
        )

    def init_from_dataframe(self, yields_df: pd.DataFrame) -> None:
        """Load treasury yields from a date-indexed DataFrame into the YieldCurve model."""
        from datetime import date

        new_yield_data: dict[date, list[tuple[str, float]]] = {}
        for idx, row in yields_df.iterrows():
            dt = idx.date() if hasattr(idx, "date") else idx
            rates = [(col, row[col]) for col in yields_df.columns]
            new_yield_data[dt] = rates
        self.model.update_yield_data(new_yield_data=new_yield_data)
        if self.model.rowCount() > 0:
            self.set_current_selection(0, 0)

    def _on_date_advanced(self, event: DateAdvanced) -> None:
        """Select the row matching the advanced date and reveal it."""
        self._hide_future_rows(event.date)
        dates = self.model.reference_dates()
        for i, d in enumerate(dates):
            if d == event.date:
                self.set_current_selection(i, 0)
                return

    def _hide_future_rows(self, current_date: datetime.date | None) -> None:
        """Hide table rows for dates beyond *current_date*. Hide all if None."""
        dates = self.model.reference_dates()
        for i, d in enumerate(dates):
            hidden = current_date is None or d > current_date
            self.view.table_view.setRowHidden(i, hidden)
