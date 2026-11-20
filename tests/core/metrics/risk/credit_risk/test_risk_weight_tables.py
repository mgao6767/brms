"""CRE20 risk-weight tables, against values read from the Basel framework."""
# ruff: noqa: D103

from __future__ import annotations

from types import SimpleNamespace

import pytest

from brms.core.metrics.risk.credit_risk.standardised_approach import (
    RiskWeightTableForCorporateExposures,
    RiskWeightTableForExposuresToBanks,
    RiskWeightTableForRatedCoveredBondExposures,
    RiskWeightTableForResidentialRealEstateNotDependentOnCashFlows,
    RiskWeightTableForSovereignExposures,
)
from brms.core.models.instruments.base import CreditRating as R


def _rated(rating: R) -> SimpleNamespace:
    return SimpleNamespace(issuer=SimpleNamespace(credit_rating=rating), credit_rating=rating)


@pytest.mark.parametrize(("table", "rating", "weight"), [
    (RiskWeightTableForSovereignExposures, R.AA_MINUS, 0.0),
    (RiskWeightTableForSovereignExposures, R.A_PLUS, 0.2),
    (RiskWeightTableForSovereignExposures, R.BBB_MINUS, 0.5),
    (RiskWeightTableForSovereignExposures, R.B_MINUS, 1.0),
    (RiskWeightTableForSovereignExposures, R.CCC, 1.5),
    (RiskWeightTableForSovereignExposures, R.UNRATED, 1.0),
    (RiskWeightTableForExposuresToBanks, R.AAA, 0.2),
    (RiskWeightTableForExposuresToBanks, R.A_MINUS, 0.3),
    (RiskWeightTableForExposuresToBanks, R.BBB, 0.5),
    (RiskWeightTableForCorporateExposures, R.AA, 0.2),
    (RiskWeightTableForCorporateExposures, R.A, 0.5),
    (RiskWeightTableForCorporateExposures, R.BBB_PLUS, 0.75),
    (RiskWeightTableForCorporateExposures, R.BB, 1.0),
    (RiskWeightTableForCorporateExposures, R.CCC, 1.5),
    (RiskWeightTableForCorporateExposures, R.UNRATED, 1.0),
    (RiskWeightTableForRatedCoveredBondExposures, R.AAA, 0.1),
    (RiskWeightTableForRatedCoveredBondExposures, R.BBB, 0.2),
])
def test_rating_tables(table: type, rating: R, weight: float) -> None:
    assert table.get_risk_weight(_rated(rating)) == weight  # noqa: S101


@pytest.mark.parametrize(("ltv", "weight"), [(0.5, 0.2), (0.6, 0.25), (0.8, 0.3), (0.9, 0.4), (1.0, 0.5), (1.1, 0.7)])
def test_residential_real_estate_by_ltv(ltv: float, weight: float) -> None:
    table = RiskWeightTableForResidentialRealEstateNotDependentOnCashFlows
    assert table.get_risk_weight(SimpleNamespace(ltv=ltv)) == weight  # noqa: S101
