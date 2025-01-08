"""The default approach, set out in CRE70.

To calculate Credit RWA for risk posed by unsettled transactions and failed trades.
"""

import datetime

from brms.metrics.base import RWAApproach
from brms.models.bank import Bank
from brms.models.scenario import ScenarioManager


class UnsettledTransactionsFailedTradesDefaultApproach(RWAApproach):
    """The default approach for calculating credit RWA for risk posed by unsettled transactions and failed trades."""

    def compute_rwa(self, bank: Bank, date: datetime.date, scenario_manager: ScenarioManager) -> float:
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
