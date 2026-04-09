"""Tests for RiskService delegation to approach strategies."""

from __future__ import annotations

from unittest.mock import MagicMock

from brms.core.services.risk_service import RiskService

EXPECTED_RWA = 42000


def test_compute_rwa_delegates_to_approach() -> None:
    """compute_rwa delegates to the approach strategy and returns its result."""
    service = RiskService()
    bank = MagicMock()
    market_state = MagicMock()
    approach = MagicMock()
    approach.compute_rwa.return_value = EXPECTED_RWA
    result = service.compute_rwa(bank, market_state, approach)
    assert result == EXPECTED_RWA  # noqa: S101
    approach.compute_rwa.assert_called_once_with(bank, market_state)
