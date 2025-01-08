"""Module defining the abstract base class and components for computing Risk-Weighted Assets (RWA)."""

import datetime
from abc import ABC, abstractmethod

from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class RWAApproach(ABC):
    """Abstract base class for computing Risk-Weighted Assets (RWA)."""

    @abstractmethod
    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank on a given date."""


class RWAComponent:
    """Class to represent the Risk-Weighted Assets (RWA) component."""

    def __init__(self, approach: RWAApproach | None = None) -> None:
        """Initialize the RWAComponent with a given approach."""
        if approach is not None:
            self._validate_approach(approach)
        self._approach = approach

    @property
    def approach(self) -> RWAApproach | None:
        """Get the RWA approach."""
        return self._approach

    @approach.setter
    def approach(self, approach: RWAApproach) -> None:
        self._validate_approach(approach)
        self._approach = approach

    def _validate_approach(self, approach: RWAApproach) -> None:
        """Validate the RWA approach."""
        if not isinstance(approach, tuple(self.allowed_approaches())):
            error_message = f"Invalid approach: {type(approach).__name__}"
            raise TypeError(error_message)

    @classmethod
    @abstractmethod
    def allowed_approaches(cls) -> list[type[RWAApproach]]:
        """Return a list of allowed RWA approaches."""

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank on a given date."""
        if self.approach is None:
            error_message = "RWA approach is not set."
            raise ValueError(error_message)
        return self.approach.compute_rwa(bank, date, scenario_manager)
