"""JSON payload helpers."""
# ruff: noqa: D103, S101, PLR2004

from __future__ import annotations

import math

from brms.web.payloads import _clean


def test_floating_point_noise_becomes_zero() -> None:
    assert _clean(-1.0913936421275139e-11) == 0.0
    assert _clean(1e-10) == 0.0
    assert _clean(0.0012) == 0.0012


def test_non_finite_values_become_null() -> None:
    assert _clean(math.nan) is None
    assert _clean(math.inf) is None
    assert _clean(None) is None
