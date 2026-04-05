import pytest

from brms.core.metrics.risk.operational_risk import StandardisedApproach


def test_compute_bic():
    """Test BIC computation using the example given in footnote 2 of OPE25.7.

    For example, given a BI = 35bn, the BIC = (1 x 12%) + (30-1) x 15% + (35-30) x 18% = 5.37bn.
    """
    billion = 1_000_000_000
    bi = 35 * billion
    bic = StandardisedApproach()._compute_business_indicator_component(bi)
    assert bic == 5.37 * billion


if __name__ == "__main__":
    pytest.main([__file__])
