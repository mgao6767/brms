"""The look-through approach, set out in CRE60.

To calculate Credit RWA for equity investments in funds that are held in the banking book.
"""

import datetime

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class LookThroughApproach(RWAApproach):
    """The look-through approach for calculating credit RWA."""

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
