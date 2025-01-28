"""Module containing classes for managing financial scenarios."""

import datetime
from typing import Any

import pandas as pd
import QuantLib as ql  # noqa: N813

from brms.data.data_loader import DataLoaderFactory
from brms.models.base import ScenarioData, ScenarioMetric
from brms.services.yield_curve_service import YieldCurveService


class Scenario:
    """Represents a single scenario with financial data."""

    def __init__(self, date: datetime.date) -> None:
        """Initialize the Scenario with only the date."""
        self.date = date
        self.data: dict[ScenarioMetric, Any] = {}

    def add_term_structure(self, term_structure: ql.YieldTermStructure) -> None:
        """Add a term structure to the scenario."""
        self.data[ScenarioMetric.YIELD_TERM_STRUCTURE] = term_structure


class ScenarioBuilder:
    """Builder class for constructing a Scenario."""

    def __init__(self, date: datetime.date) -> None:
        """Initialize the builder with the required date."""
        self._scenario = Scenario(date)

    def build(self) -> Scenario:
        """Finalize the construction of the Scenario."""
        return self._scenario

    def with_term_structure(self, term_structure: ql.YieldTermStructure) -> "ScenarioBuilder":
        """Add a term structure to the Scenario."""
        self._scenario.add_term_structure(term_structure)
        return self


class ScenarioManager:
    """Manage scenarios with functionalities to add, clear, and retrieve scenarios."""

    def __init__(self) -> None:
        """Initialize the ScenarioManager with an empty dictionary of scenarios."""
        self.current_date = datetime.date(1900, 1, 1)
        self.current_scenario = Scenario(self.current_date)
        self.scenarios: dict[datetime.date, Scenario] = {}
        self.available_dates: list[datetime.date] = []
        # `self.data` contains all _raw_ data loaded, i.e., for all dates (scenarios).
        # When a particular scenario is requested, we build it from the data if the scenario is not yet cached.
        self._data: dict[ScenarioData, Any] = {}

    def has_scenario(self, date: datetime.date) -> bool:
        """Check if a scenario exists for a given date."""
        return date in self.available_dates

    def set_scenario(self, date: datetime.date) -> None:
        scenario = self.get_scenario(date)
        if not scenario:
            error_message = f"No scenario found for date: {date}"
            raise ValueError(error_message)
        self.current_scenario = scenario
        self.current_date = date

    def clear_scenarios(self) -> None:
        """Clear all scenarios."""
        self.scenarios.clear()

    def add_scenario(self, date: datetime.date, scenario: Scenario) -> None:
        """Add a scenario by date."""
        self.scenarios[date] = scenario

    def get_scenario(self, date: datetime.date) -> Scenario:
        """Retrieve a scenario by date."""
        assert self.has_scenario(date)
        scenario = self.scenarios.get(date)
        # Build scenario if not yet in the cache
        if scenario is None:
            yield_df = self._data.get(ScenarioData.TREASURY_YIELDS)
            term_structure = YieldCurveService.build_yield_curve_from_df(yield_df, date)
            builder = ScenarioBuilder(date).with_term_structure(term_structure)
            scenario = builder.build()
            self.add_scenario(date, scenario)
        return scenario

    def get_historical_scenarios(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> dict[datetime.date, Scenario]:
        """Retrieve historical scenarios in a date range."""
        return {date: scenario for date, scenario in self.scenarios.items() if start_date <= date <= end_date}

    def load_data(self, source_type: str, source_path: str) -> None:
        """Load data using DataLoader and build scenarios."""
        data_loader = DataLoaderFactory.get_loader(source_type, source_path)
        self._data = data_loader.load()
        self.available_dates = self.get_available_dates()

    def get_treasury_yields(self) -> pd.DataFrame:
        """Retrieve the raw treasury yields data as a DataFrame."""
        return self._data.get(ScenarioData.TREASURY_YIELDS, pd.DataFrame)

    def get_available_dates(self) -> list[datetime.date]:
        """Extract all dates from the treasury yields DataFrame."""
        yield_df = self._data.get(ScenarioData.TREASURY_YIELDS, pd.DataFrame())
        if yield_df.empty:
            return []
        return yield_df["date"].dt.date.to_list()
