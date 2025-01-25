"""Module containing the Simulation class for representing a simulation."""

import datetime

from brms.models.bank import Bank
from brms.models.scenario import Scenario, ScenarioManager


class Simulation:
    """A class to represent a simulation."""

    def __init__(self, bank: Bank | None = None, scenario_manager: ScenarioManager | None = None) -> None:
        """Initialize the simulation with a bank and a scenario manager."""
        self.bank = bank or Bank()
        self.scenario_manager = scenario_manager or ScenarioManager()

    def set_scenario(self, date: datetime.date) -> None:
        """Set the current scenario for the simulation."""
        scenario = self.scenario_manager.get_scenario(date)
        if not scenario:
            error_message = f"No scenario found for date: {date}"
            raise ValueError(error_message)
        self.scenario_manager.current_scenario = scenario

    def reset(self) -> None:
        """Reset the simulation state."""

    @property
    def current_scenario(self) -> Scenario:
        """Get the current scenario."""
        return self.scenario_manager.current_scenario
