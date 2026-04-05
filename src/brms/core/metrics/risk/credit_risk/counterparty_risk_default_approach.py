"""The default approach, set out in CRE51.

To calculate Credit RWA for counterparty credit risk arising from banking book exposures and from trading book instruments.
"""

import datetime
from typing import Any

from brms.core.metrics.risk.base import RWAApproach


class CounterpartyRiskDefaultApproach(RWAApproach):
    """The default approach for calculating credit RWA for counterparty risk."""

    def compute_rwa(self, bank: Any, date: datetime.date, scenario_manager: Any) -> float:  # noqa: ANN401
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
