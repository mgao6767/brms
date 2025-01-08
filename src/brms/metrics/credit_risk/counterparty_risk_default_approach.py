"""The default approach, set out in CRE51.

To calculate Credit RWA for counterparty credit risk arising from banking book exposures and from trading book instruments.
"""

import datetime

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class CounterpartyRiskDefaultApproach(RWAApproach):
    """The default approach for calculating credit RWA for counterparty risk."""

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
