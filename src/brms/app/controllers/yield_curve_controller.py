from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import numpy as np
import QuantLib as ql
from dateutil.relativedelta import relativedelta
from PySide6.QtCore import QItemSelectionModel, Qt

from brms.app.controllers.base import BRMSController
from brms.app.views.yield_curve_widget import BRMSYieldCurveWidget
from brms.models.yield_curve_model import YieldCurve
from brms.services.yield_curve_service import YieldCurveService

if TYPE_CHECKING:
    import pandas as pd


class YieldCurveController(BRMSController):
    def __init__(self, view: BRMSYieldCurveWidget):
        super().__init__()
        self.model = YieldCurve()  # model inside controller because it's just a data container
        self.view = view

        self.view.set_model(self.model)

        # Connect the selection changed signal to the slot
        # fmt: off
        self.view.visibility_changed.connect(self.update_plot)
        self.view.table_view.selectionModel().selectionChanged.connect(self.update_plot)
        self.view.plot_widget.rescale_checkbox.stateChanged.connect(self.update_plot)
        self.view.plot_widget.grid_checkbox.stateChanged.connect(self.update_plot)
        # fmt: on

    def reset(self):
        self.model.reset()
        self.clear_plot()

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
            return
        row = indexes[0].row()
        model = self.model
        # Retrieve the date from the vertical header
        date_str = model.headerData(row, Qt.Vertical)
        return datetime.strptime(date_str, "%Y-%m-%d")

    def get_yields_from_selection(self):
        indexes = self.view.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        model = self.model

        # Retrieve the date from the vertical header
        date_str = model.headerData(row, Qt.Vertical)
        reference_date = datetime.strptime(date_str, "%Y-%m-%d")

        # Retrieve the maturities from the horizontal header
        maturities = [model.headerData(col, Qt.Horizontal) for col in range(model.columnCount())]

        # Maturity dates
        maturity_dates = []
        for m in maturities:
            match m:
                case "1M" | "1 Mo":
                    new_date = reference_date + relativedelta(months=1)
                case "2M" | "2 Mo":
                    new_date = reference_date + relativedelta(months=2)
                case "3M" | "3 Mo":
                    new_date = reference_date + relativedelta(months=3)
                case "4M" | "4 Mo":
                    new_date = reference_date + relativedelta(months=4)
                case "6M" | "6 Mo":
                    new_date = reference_date + relativedelta(months=6)
                case "1Y" | "1 Yr":
                    new_date = reference_date + relativedelta(years=1)
                case "2Y" | "2 Yr":
                    new_date = reference_date + relativedelta(years=2)
                case "3Y" | "3 Yr":
                    new_date = reference_date + relativedelta(years=3)
                case "5Y" | "5 Yr":
                    new_date = reference_date + relativedelta(years=5)
                case "7Y" | "7 Yr":
                    new_date = reference_date + relativedelta(years=7)
                case "10Y" | "10 Yr":
                    new_date = reference_date + relativedelta(years=10)
                case "20Y" | "20 Yr":
                    new_date = reference_date + relativedelta(years=20)
                case "30Y" | "30 Yr":
                    new_date = reference_date + relativedelta(years=30)
                case _:
                    new_date = date

            maturity_dates.append(new_date)

        # Retrieve the yields for the selected row
        yields = [model.index(row, col).data() for col in range(model.columnCount())]
        # Maturity labels liek "1 Mo", "30Y"
        maturity_labels = [self.model.headerData(col, Qt.Horizontal) for col in range(self.model.columnCount())]
        # Filter out NaN values
        yields = np.array(yields)
        maturity_dates = np.array(maturity_dates)
        maturity_labels = np.array(maturity_labels)
        valid_indices = ~np.isnan(yields)

        return reference_date, maturity_dates[valid_indices], maturity_labels[valid_indices], yields[valid_indices]

    def clear_plot(self):
        self.view.plot_widget.clear_plot()

    def update_plot(self):
        # Update only when the yield curve widget is visible?
        if not self.view.is_visible:
            return
        yield_data = self.get_yields_from_selection()
        if yield_data is None:
            return
        ref_date, _, maturity_labels, yields = yield_data
        yield_curve = YieldCurveService.build_yield_curve(ref_date, maturity_labels=maturity_labels, rates=yields)
        ref_date, dates, _, yields = yield_data
        calendar = ql.ActualActual(ql.ActualActual.ISDA)
        zero_rates = []

        # Generate T evenly spaced dates between ref_date and longest_maturity_date
        # Therefore the interpolated zero curve can have more obs
        longest_maturity_date = max(dates)
        n_date = 50  # Number of dates to generate
        date_range = np.linspace(0, (longest_maturity_date - ref_date).days, n_date)
        evenly_spaced_dates = [ref_date + relativedelta(days=int(days)) for days in date_range]
        dates_zero_rates = []
        for maturity_date in evenly_spaced_dates:
            ql_maturity_date = ql.Date(maturity_date.day, maturity_date.month, maturity_date.year)
            # Annually compounded zero rates
            zero_rate = yield_curve.zeroRate(ql_maturity_date, calendar, ql.Compounded, ql.Annual).rate()
            dates_zero_rates.append(maturity_date)
            zero_rates.append(zero_rate * 100)

        # Update the plot with the new x and y values
        date_str = ref_date.strftime("%B %d, %Y")  # Example: "January 01, 2023"
        title = f"Yield Curve as at {date_str}"
        rescale_y = self.view.plot_widget.rescale_checkbox.isChecked()
        show_grid = self.view.plot_widget.grid_checkbox.isChecked()
        self.view.plot_widget.update_plot(dates, yields, dates_zero_rates, zero_rates, title, rescale_y, show_grid)

    def init_from_dataframe(self, yields_df: pd.DataFrame) -> None:
        """Load treasury yields from a date-indexed DataFrame into the YieldCurve model.

        This is the core-layer replacement for :meth:`init`, which required a
        legacy ``ScenarioManager``.
        """
        new_yield_data: dict[date, list[tuple[str, float]]] = {}
        for idx, row in yields_df.iterrows():
            dt = idx.date() if hasattr(idx, "date") else idx
            rates = [(col, row[col]) for col in yields_df.columns]
            new_yield_data[dt] = rates
        self.model.update_yield_data(new_yield_data=new_yield_data)
        if self.model.rowCount() > 0:
            self.set_current_selection(0, 0)

