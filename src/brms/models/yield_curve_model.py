from datetime import date

import QuantLib as ql
from dateutil.relativedelta import relativedelta
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


class YieldCurveModel(QAbstractTableModel):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._yield_curve: ql.YieldTermStructure | None = None
        self._yield_data: dict[date, list[tuple[str, float]]] = {}
        self._reference_dates: list[date] = []
        self._maturities: list[str] = []

    def reset(self) -> None:
        self.beginResetModel()
        self._yield_data.clear()
        self._reference_dates.clear()
        self._maturities.clear()
        self.endResetModel()

    def reference_dates(self):
        return self._reference_dates

    def yield_curve(self):
        return self._yield_curve

    def get_yield_data(self, query_date: date) -> list[tuple[str, float]]:
        """
        Given a date, return the yield data for various maturities.

        :param query_date: The date for which to fetch the yield data.
        :return: A list of tuples containing (maturity, yield).
        """
        return self._yield_data.get(query_date, [])

    def update_yield_data(
        self, new_yield_data: dict[date, list[tuple[str, float]]]
    ) -> None:
        """
        Update the yield data and notify the view that the data has changed.

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

    def build_yield_curve(self, yield_data):

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
        self._yield_curve = ql.PiecewiseLogCubicDiscount(
            ql_date, rate_helpers, day_count
        )
        self._yield_curve.enableExtrapolation()

        return self._yield_curve
