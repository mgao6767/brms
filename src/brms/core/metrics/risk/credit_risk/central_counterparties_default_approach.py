"""The default approach, set out in CRE54.

To calculate Credit RWA for exposures to central counterparties in the banking book and trading book.
"""

import datetime
from typing import Any

from brms.core.metrics.risk.base import RWAApproach


class CentralCounterpartyRiskDefaultApproach(RWAApproach):
    """The default approach for calculating credit RWA for exposures to central counterparties."""

    def compute_rwa(self, bank: Any, date: datetime.date, scenario_manager: Any) -> float:  # noqa: ANN401
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
