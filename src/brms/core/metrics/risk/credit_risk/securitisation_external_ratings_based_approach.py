"""The Securitisation External Ratings-Based Approach (SEC-ERBA), set out in CRE40 to CRE45.

To calculate Credit RWA for securitisation exposures held in the banking book.
"""

import datetime
from typing import Any

from brms.core.metrics.risk.base import RWAApproach


class SecuritisationExternalRatingsBasedApproach(RWAApproach):
    """SEC-ERBA for calculating credit RWA."""

    def compute_rwa(self, bank: Any, date: datetime.date, scenario_manager: Any) -> float:  # noqa: ANN401
        """Compute the Risk-Weighted Assets (RWA) for a given bank and scenario."""
        raise NotImplementedError
