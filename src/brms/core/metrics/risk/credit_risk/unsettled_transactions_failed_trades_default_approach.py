"""The default approach, set out in CRE70.

To calculate Credit RWA for risk posed by unsettled transactions and failed trades.
"""

import datetime
from typing import Any

from brms.core.metrics.risk.base import RWAApproach


class UnsettledTransactionsFailedTradesDefaultApproach(RWAApproach):
    """The default approach for calculating credit RWA for risk posed by unsettled transactions and failed trades."""

    def compute_rwa(self, bank: Any, date: datetime.date, scenario_manager: Any) -> float:  # noqa: ANN401
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
