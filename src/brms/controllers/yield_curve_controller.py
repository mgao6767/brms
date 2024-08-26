from datetime import date, datetime

import numpy as np
import QuantLib as ql
from dateutil.relativedelta import relativedelta
from PySide6.QtCore import QItemSelectionModel, Qt

from brms.models import YieldCurveModel
from brms.views import YieldCurveWidget


class YieldCurveController:

    def __init__(self, model: YieldCurveModel, view: YieldCurveWidget):
        self.model = model
        self.view = view

        self.view.set_model(self.model)

        # QuantLib yield curve
        self.yield_curve = None

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
        """
        Set the current selection of the table_view.

        :param row: The row index of the selection.
        :param column: The column index of the selection.
        """
        model_index = self.model.index(row, column)
        selection_model = self.view.table_view.selectionModel()
        selection_model.setCurrentIndex(
            model_index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )

    def get_all_dates(self):
        """
        Returns a list of all dates associated with the yields data.
        Returns:
            list: A list of dates.
        """
        return self.model.dates

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
        maturities = [
            model.headerData(col, Qt.Horizontal) for col in range(model.columnCount())
        ]

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

        # Filter out NaN values
        yields = np.array(yields)
        maturity_dates = np.array(maturity_dates)
        valid_indices = ~np.isnan(yields)

        return reference_date, maturity_dates[valid_indices], yields[valid_indices]

    def clear_plot(self):
        self.view.plot_widget.clear_plot()

    def update_plot(self):

        yield_curve = self.build_yield_curve()

        if yield_curve is None:
            return
        # Update only when the yield curve widget is visible?
        if not self.view.is_visible:
            return

        yield_data = self.get_yields_from_selection()
        if yield_data is None:
            return
        ref_date, dates, yields = yield_data
        calendar = ql.ActualActual(ql.ActualActual.ISDA)
        zero_rates = []

        # Generate T evenly spaced dates between ref_date and longest_maturity_date
        # Therefore the interpolated zero curve can have more obs
        longest_maturity_date = max(dates)
        n_date = 50  # Number of dates to generate
        date_range = np.linspace(0, (longest_maturity_date - ref_date).days, n_date)
        evenly_spaced_dates = [
            ref_date + relativedelta(days=int(days)) for days in date_range
        ]
        dates_zero_rates = []
        for maturity_date in evenly_spaced_dates:
            ql_maturity_date = ql.Date(
                maturity_date.day, maturity_date.month, maturity_date.year
            )
            # Annually compounded zero rates
            zero_rate = yield_curve.zeroRate(
                ql_maturity_date, calendar, ql.Compounded, ql.Annual
            ).rate()
            dates_zero_rates.append(maturity_date)
            zero_rates.append(zero_rate * 100)

        # Update the plot with the new x and y values
        date_str = ref_date.strftime("%B %d, %Y")  # Example: "January 01, 2023"
        title = f"Yield Curve as at {date_str}"
        rescale_y = self.view.plot_widget.rescale_checkbox.isChecked()
        show_grid = self.view.plot_widget.grid_checkbox.isChecked()
        self.view.plot_widget.update_plot(
            dates, yields, dates_zero_rates, zero_rates, title, rescale_y, show_grid
        )

    def build_yield_curve(self):
        # Here, the relinkable handle is relinked to new curve, which will trigger
        # revaluation of all assets whose pricing engine is based on this handle.
        yield_data = self.get_yields_from_selection()
        if yield_data is None:
            return
        ref_date, dates, yields = yield_data

        # Convert date to QuantLib Date
        ql_date = ql.Date(ref_date.day, ref_date.month, ref_date.year)
        ql.Settings.instance().evaluationDate = ql_date

        calendar = ql.UnitedStates(ql.UnitedStates.NYSE)
        business_convention = ql.Following
        end_of_month = False
        day_count = ql.ActualActual(ql.ActualActual.ISDA)

        # Maturity<=1yr
        zcb_data = []
        coupon_bond_data = []
        # Add another week to be sure
        one_year_later = ref_date + relativedelta(years=1) + relativedelta(weeks=1)
        for maturity_date, y in zip(dates, yields):
            if maturity_date <= one_year_later:
                zcb_data.append((maturity_date, float(y) / 100))
            else:
                # Assuming price is 100.0 for simplicity
                coupon_bond_data.append((maturity_date, float(y) / 100, 100.0))

        # Create zero-coupon bond helpers for the short end
        zcb_helpers = []
        for maturity_date, rate in zcb_data:
            maturity_period = ql.Period((maturity_date - ref_date).days, ql.Days)
            zcb_helpers.append(
                ql.DepositRateHelper(
                    ql.QuoteHandle(ql.SimpleQuote(rate)),
                    maturity_period,
                    0,  # settlement days
                    calendar,
                    business_convention,
                    end_of_month,
                    day_count,
                )
            )

        # Create fixed rate bond helpers for the long end
        bond_helpers = []
        for maturity_date, coupon_rate, price in coupon_bond_data:
            maturity_period = ql.Period((maturity_date - ref_date).days, ql.Days)
            schedule = ql.Schedule(
                ql_date,
                ql_date + maturity_period,
                ql.Period(ql.Semiannual),
                calendar,
                business_convention,
                business_convention,
                ql.DateGeneration.Backward,
                end_of_month,
            )
            bond_helpers.append(
                ql.FixedRateBondHelper(
                    ql.QuoteHandle(ql.SimpleQuote(price)),
                    0,  # settlement days
                    100.0,  # face value
                    schedule,
                    [coupon_rate],
                    day_count,
                )
            )

        # Combine the helpers
        rate_helpers = zcb_helpers + bond_helpers

        # Build the yield curve
        self.yield_curve = ql.PiecewiseLogCubicDiscount(
            ql_date, rate_helpers, day_count
        )
        self.yield_curve.enableExtrapolation()

        return self.yield_curve
