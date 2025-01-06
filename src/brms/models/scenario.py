"""Module containing classes for managing financial scenarios."""

import datetime
from typing import Any

import QuantLib as ql  # noqa: N813

from brms.models.base import ScenarioData


class Scenario:
    """Represents a single scenario with financial data."""

    def __init__(self, date: datetime.date) -> None:
        """Initialize the Scenario with only the date."""
        self.date = date
        self.data: dict[ScenarioData, Any] = {}

    def add_term_structure(self, term_structure: ql.YieldTermStructureHandle) -> None:
        """Add a term structure to the scenario."""
        self.data[ScenarioData.YIELD_TERM_STRUCTURE] = term_structure


class ScenarioBuilder:
    """Builder class for constructing a Scenario."""

    def __init__(self, date: datetime.date) -> None:
        """Initialize the builder with the required date."""
        self._scenario = Scenario(date)

    def build(self) -> Scenario:
        """Finalize the construction of the Scenario."""
        return self._scenario

    def with_term_structure(self, term_structure: ql.YieldTermStructureHandle) -> "ScenarioBuilder":
        """Add a term structure to the Scenario."""
        self._scenario.add_term_structure(term_structure)
        return self


class ScenarioManager:
    """Manage scenarios with functionalities to add, clear, and retrieve scenarios."""

    def __init__(self) -> None:
        """Initialize the ScenarioManager with an empty dictionary of scenarios."""
        self.scenarios: dict[datetime.date, Scenario] = {}

    def clear_scenarios(self) -> None:
        """Clear all scenarios."""
        self.scenarios.clear()

    def add_scenario(self, date: datetime.date, scenario: Scenario) -> None:
        """Add a scenario by date."""
        self.scenarios[date] = scenario

    def get_scenario(self, date: datetime.date) -> Scenario | None:
        """Retrieve a scenario by date."""
        return self.scenarios.get(date)

    def get_historical_scenarios(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> dict[datetime.date, Scenario]:
        """Retrieve historical scenarios in a date range."""
        return {date: scenario for date, scenario in self.scenarios.items() if start_date <= date <= end_date}
