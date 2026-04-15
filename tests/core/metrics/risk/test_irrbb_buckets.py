# ruff: noqa: S101, PLR2004
"""Tests for IRRBB time bucket definitions and assignment."""

import math

from brms.core.metrics.risk.interest_rate_risk.buckets import IRRBB_BUCKETS, assign_bucket


def test_19_buckets_defined() -> None:
    """There are exactly 19 Basel IRRBB buckets."""
    assert len(IRRBB_BUCKETS) == 19


def test_bucket_boundaries_are_contiguous() -> None:
    """Each bucket's upper bound equals the next bucket's lower bound."""
    for i in range(len(IRRBB_BUCKETS) - 1):
        assert IRRBB_BUCKETS[i].upper == IRRBB_BUCKETS[i + 1].lower


def test_last_bucket_upper_is_infinity() -> None:
    """The 20Y+ bucket has no upper bound."""
    assert math.isinf(IRRBB_BUCKETS[-1].upper)


def test_assign_overnight() -> None:
    """0 days remaining → overnight bucket (index 0)."""
    assert assign_bucket(0.0) == 0


def test_assign_2_months() -> None:
    """2 months (0.167 years) → 1M-3M bucket (index 2)."""
    assert assign_bucket(0.167) == 2


def test_assign_8_years() -> None:
    """8 years → 7Y-8Y bucket (index 13)."""
    assert assign_bucket(8.0) == 13


def test_assign_25_years() -> None:
    """25 years → 20Y+ bucket (index 18)."""
    assert assign_bucket(25.0) == 18


def test_assign_negative_returns_overnight() -> None:
    """Negative remaining years (past maturity) → overnight bucket."""
    assert assign_bucket(-0.5) == 0


def test_assign_exact_boundary_between_buckets() -> None:
    """Exact boundary values are assigned consistently (no gaps)."""
    # Overnight upper bound → should go to overnight, not fall through
    assert assign_bucket(1 / 365.25) == 0
