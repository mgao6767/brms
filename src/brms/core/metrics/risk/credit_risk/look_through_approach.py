"""The look-through approach, set out in CRE60.

To calculate Credit RWA for equity investments in funds that are held in the banking book.
"""

import datetime
from typing import Any

from brms.core.metrics.risk.base import RWAApproach


class LookThroughApproach(RWAApproach):
    """The look-through approach for calculating credit RWA."""

    def compute_rwa(self, bank: Any, date: datetime.date, scenario_manager: Any) -> float:  # noqa: ANN401
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
