"""RiskService: delegates RWA computation to strategy objects."""

from __future__ import annotations

from typing import Any


class RiskService:
    """Pure computation. Delegates to strategy objects for different risk approaches."""

    def compute_rwa(
        self,
        bank: Any,  # noqa: ANN401
        market_state: Any,  # noqa: ANN401
        approach: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """Compute risk-weighted assets by delegating to the given approach strategy."""
        return approach.compute_rwa(bank, market_state)
