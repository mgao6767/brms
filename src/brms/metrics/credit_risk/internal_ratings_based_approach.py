"""The internal ratings-based (IRB) approach, set out in CRE30 to CRE36.

To calculate credit RWA for banking book exposures.
"""

import datetime

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class InternalRatingsBasedApproach(RWAApproach):
    """The internal ratings-based (IRB) approach for calculating credit RWA."""

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
