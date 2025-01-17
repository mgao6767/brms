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
        self.current_scenario: Scenario | None = None

    def run(self) -> None:
        """Run the simulation for the current scenario."""
        if not self.current_scenario:
            error_message = "No scenario is set for the simulation."
            raise ValueError(error_message)
        self.bank.valuation(self.current_scenario)

    def set_scenario(self, date: datetime.date) -> None:
        """Set the current scenario for the simulation."""
        scenario = self.scenario_manager.get_scenario(date)
        if not scenario:
            error_message = f"No scenario found for date: {date}"
            raise ValueError(error_message)
        self.current_scenario = scenario

    def reset(self) -> None:
        """Reset the simulation state."""
        self.current_scenario = None
