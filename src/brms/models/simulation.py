"""Module containing the Simulation class for representing a simulation."""

import datetime

from brms.models.bank import Bank
from brms.models.bank_engine import BankEngine
from brms.models.scenario import Scenario, ScenarioManager


class Simulation:
    """A class to represent a simulation."""

    def __init__(self, bank: Bank | None = None, scenario_manager: ScenarioManager | None = None) -> None:
        """Initialize the simulation with a bank and a scenario manager."""
        self.bank = bank or Bank()
        self.scenario_manager = scenario_manager or ScenarioManager()
        self.bank_engine = BankEngine(self.bank, self.scenario_manager)
        self.start_date: datetime.date

    def set_scenario(self, date: datetime.date) -> None:
        """Set the current scenario for the simulation."""
        self.scenario_manager.set_scenario(date)

    def reset(self) -> None:
        """Reset the simulation state."""

    @property
    def current_scenario(self) -> Scenario:
        """Get the current scenario."""
        return self.scenario_manager.current_scenario

    @property
    def end_date(self) -> datetime.date:
        """Get the end date of the available scenarios."""
        return max(self.scenario_manager.available_dates)
