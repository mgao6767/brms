import datetime
import math
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
import pandas as pd
import QuantLib as ql
from dateutil.relativedelta import relativedelta

_LABEL_TO_RELATIVEDELTA: dict[str, relativedelta] = {
    "1M": relativedelta(months=1), "1 Mo": relativedelta(months=1),
    "2M": relativedelta(months=2), "2 Mo": relativedelta(months=2),
    "3M": relativedelta(months=3), "3 Mo": relativedelta(months=3),
    "4M": relativedelta(months=4), "4 Mo": relativedelta(months=4),
    "6M": relativedelta(months=6), "6 Mo": relativedelta(months=6),
    "1Y": relativedelta(years=1), "1 Yr": relativedelta(years=1),
    "2Y": relativedelta(years=2), "2 Yr": relativedelta(years=2),
    "3Y": relativedelta(years=3), "3 Yr": relativedelta(years=3),
    "5Y": relativedelta(years=5), "5 Yr": relativedelta(years=5),
    "7Y": relativedelta(years=7), "7 Yr": relativedelta(years=7),
    "10Y": relativedelta(years=10), "10 Yr": relativedelta(years=10),
    "20Y": relativedelta(years=20), "20 Yr": relativedelta(years=20),
    "30Y": relativedelta(years=30), "30 Yr": relativedelta(years=30),
}


@dataclass(frozen=True)
class YieldCurvePlotData:
    """Plot-ready yield curve data."""

    par_dates: list[datetime.datetime]
    par_rates: list[float]
    zero_dates: list[datetime.datetime]
    zero_rates: list[float]
    title: str


class YieldCurveService:
    """Service to convert par yields into zero yield curves using QuantLib."""

    MATURITY_MAPPING: ClassVar[dict] = {
        "1 Mo": ql.Period(1, ql.Months),
        "2 Mo": ql.Period(2, ql.Months),
        "3 Mo": ql.Period(3, ql.Months),
        "4 Mo": ql.Period(4, ql.Months),
        "6 Mo": ql.Period(6, ql.Months),
        "1 Yr": ql.Period(1, ql.Years),
        "2 Yr": ql.Period(2, ql.Years),
        "3 Yr": ql.Period(3, ql.Years),
        "5 Yr": ql.Period(5, ql.Years),
        "7 Yr": ql.Period(7, ql.Years),
        "10 Yr": ql.Period(10, ql.Years),
        "20 Yr": ql.Period(20, ql.Years),
        "30 Yr": ql.Period(30, ql.Years),
    }

    @staticmethod
    def build_yield_curve(ref_date: datetime.date, maturity_labels: list, rates: list) -> ql.YieldTermStructure:
        """Construct a QuantLib yield curve from provided maturity labels and rates.

        :param ref_date: Reference date (Python `datetime.date`)
        :param maturity_labels: List of column names corresponding to maturities (e.g., ["1 Mo", "2 Yr"])
        :param rates: List of yield values corresponding to the maturities (in percentage, e.g., [2.5, 3.0, 3.5])
        :return: QuantLib Piecewise Log-Cubic Discount yield curve
        """
        if len(maturity_labels) == 0 or len(rates) == 0:
            return None

        # Convert reference date to QuantLib Date
        ql_ref_date = ql.Date(ref_date.day, ref_date.month, ref_date.year)
        ql.Settings.instance().evaluationDate = ql_ref_date

        calendar = ql.UnitedStates(ql.UnitedStates.NYSE)
        business_convention = ql.Following
        end_of_month = False
        day_count = ql.ActualActual(ql.ActualActual.ISDA)

        # Separate short-term zero-coupon bonds from long-term coupon bonds
        zcb_data = []  # Zero-coupon bond data (≤1 year)
        coupon_bond_data = []  # Coupon bond data (>1 year)

        # Define threshold for ZCBs (1 year + 1 week)
        one_year_later = ref_date + relativedelta(years=1, weeks=1)

        for label, rate in zip(maturity_labels, rates, strict=True):
            if label not in YieldCurveService.MATURITY_MAPPING:
                raise ValueError(f"Unknown maturity label: {label}")

            if rate is None or np.isnan(rate):  # Skip missing rates
                continue

            # Convert rate from percentage to decimal (e.g., 2.5% → 0.025)
            rate = float(rate) / 100.0

            # Compute maturity date
            maturity_period = YieldCurveService.MATURITY_MAPPING[label]
            maturity_date = ql_ref_date + maturity_period

            if maturity_date < ql.Date(one_year_later.day, one_year_later.month, one_year_later.year):
                zcb_data.append((maturity_date, rate))
            else:
                coupon_bond_data.append((maturity_date, rate, 100.0))  # Assuming price 100

        # Create deposit rate helpers for short-term zero-coupon bonds
        zcb_helpers = [
            ql.DepositRateHelper(
                ql.QuoteHandle(ql.SimpleQuote(rate)),
                ql.Period(maturity_date - ql_ref_date, ql.Days),
                0,  # settlement days
                calendar,
                business_convention,
                end_of_month,
                day_count,
            )
            for maturity_date, rate in zcb_data
        ]

        # Create fixed-rate bond helpers for long-term coupon bonds
        bond_helpers = []
        for maturity_date, coupon_rate, price in coupon_bond_data:
            schedule = ql.Schedule(
                ql_ref_date,
                maturity_date,
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
                ),
            )

        # Combine rate helpers
        rate_helpers = zcb_helpers + bond_helpers

        # Build the yield curve using a Piecewise Log-Cubic Discount
        yield_curve = ql.PiecewiseLogCubicDiscount(ql_ref_date, rate_helpers, day_count)
        yield_curve.enableExtrapolation()

        return yield_curve

    @classmethod
    def build_yield_curve_from_df(cls, df: pd.DataFrame, date: datetime.date) -> ql.YieldTermStructure:
        """Construct a QuantLib yield curve from a DataFrame and a specific date.

        :param df: DataFrame containing yield data with a 'date' column and maturity columns
        :param date: Specific date to extract the yield data
        :return: QuantLib YieldTermStructure
        """
        row = df[df["date"].dt.date == date]
        if row.empty:
            raise ValueError(f"No data available for the date: {date}")

        maturity_labels = [col for col in df.columns if col != "date"]
        rates = [row.iloc[0][col] for col in maturity_labels]
        return cls.build_yield_curve(date, maturity_labels, rates)

    @classmethod
    def compute_plot_data(
        cls,
        reference_date: datetime.date,
        maturity_labels: list[str],
        rates: list[float],
        n_interpolation_points: int = 50,
    ) -> YieldCurvePlotData:
        """Compute plot-ready yield curve data with par rates and interpolated zero rates."""
        # Filter out NaN rates
        filtered_labels: list[str] = []
        filtered_rates: list[float] = []
        for label, rate in zip(maturity_labels, rates, strict=True):
            if not math.isnan(rate):
                filtered_labels.append(label)
                filtered_rates.append(rate)

        # Convert labels to datetime for par curve
        par_dates = [
            datetime.datetime(  # noqa: DTZ001
                *(reference_date + _LABEL_TO_RELATIVEDELTA[label]).timetuple()[:3],
            )
            for label in filtered_labels
        ]

        # Build QL yield curve
        yield_curve = cls.build_yield_curve(reference_date, filtered_labels, filtered_rates)

        # Generate interpolated zero rates
        day_count = ql.ActualActual(ql.ActualActual.ISDA)
        max_date = max(par_dates)
        ref_dt = datetime.datetime(reference_date.year, reference_date.month, reference_date.day)  # noqa: DTZ001
        total_days = (max_date - ref_dt).days
        zero_dates: list[datetime.datetime] = []
        zero_rates: list[float] = []
        for i in range(n_interpolation_points):
            days = int(total_days * (i + 1) / n_interpolation_points)
            dt = ref_dt + datetime.timedelta(days=days)
            ql_dt = ql.Date(dt.day, dt.month, dt.year)
            zero_rate = yield_curve.zeroRate(ql_dt, day_count, ql.Compounded, ql.Annual).rate() * 100
            zero_dates.append(dt)
            zero_rates.append(zero_rate)

        title = f"Yield Curve — {reference_date.strftime('%B %d, %Y')}"

        return YieldCurvePlotData(
            par_dates=par_dates,
            par_rates=filtered_rates,
            zero_dates=zero_dates,
            zero_rates=zero_rates,
            title=title,
        )
