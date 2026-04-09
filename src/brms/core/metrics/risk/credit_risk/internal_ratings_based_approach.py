"""The internal ratings-based (IRB) approach, set out in CRE30 to CRE36.

To calculate credit RWA for banking book exposures.
"""

import datetime
from typing import Any

from brms.core.metrics.risk.base import RWAApproach


class InternalRatingsBasedApproach(RWAApproach):
    """The internal ratings-based (IRB) approach for calculating credit RWA."""

    def compute_rwa(self, bank: Any, date: datetime.date, scenario_manager: Any) -> float:  # noqa: ANN401
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
