"""The default approach, set out in CRE54.

To calculate Credit RWA for exposures to central counterparties in the banking book and trading book.
"""

import datetime

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class CentralCounterpartyRiskDefaultApproach(RWAApproach):
    """The default approach for calculating credit RWA for exposures to central counterparties."""

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
