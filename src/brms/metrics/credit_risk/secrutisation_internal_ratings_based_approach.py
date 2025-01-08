"""The Securitisation Internal Ratings-Based Approach (SEC-IRBA), set out in CRE40 to CRE45.

To calculate Credit RWA for securitisation exposures held in the banking book.
"""

import datetime

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class SecuritisationInternalRatingsBasedApproach(RWAApproach):
    """SEC-IRBA for calculating credit RWA."""

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
