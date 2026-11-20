"""Module defining the abstract base class and components for computing Risk-Weighted Assets (RWA)."""

import datetime
from abc import ABC, abstractmethod
from typing import Any


class RWAApproach(ABC):
    """Abstract base class for computing Risk-Weighted Assets (RWA)."""

    @abstractmethod
    def compute_rwa(self, bank: Any, date: datetime.date, scenario_manager: Any) -> float:  # noqa: ANN401
        """Compute the Risk-Weighted Assets (RWA) for a given bank on a given date."""

