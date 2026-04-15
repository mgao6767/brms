# ruff: noqa: RUF001
"""Basel IRRBB time buckets per SRP 31.98 Table 3."""

from __future__ import annotations

import math
from typing import NamedTuple


class TimeBucket(NamedTuple):
    """A single IRRBB repricing time bucket."""

    label: str
    lower: float  # years, inclusive
    upper: float  # years, exclusive (inf for last bucket)
    midpoint: float  # years


IRRBB_BUCKETS: tuple[TimeBucket, ...] = (
    TimeBucket("Overnight", 0.0, 1 / 365.25, 0.0028),
    TimeBucket("O/N – 1M", 1 / 365.25, 1 / 12, 0.0417),
    TimeBucket("1M – 3M", 1 / 12, 3 / 12, 0.1667),
    TimeBucket("3M – 6M", 3 / 12, 6 / 12, 0.375),
    TimeBucket("6M – 9M", 6 / 12, 9 / 12, 0.625),
    TimeBucket("9M – 12M", 9 / 12, 1.0, 0.875),
    TimeBucket("1Y – 1.5Y", 1.0, 1.5, 1.25),
    TimeBucket("1.5Y – 2Y", 1.5, 2.0, 1.75),
    TimeBucket("2Y – 3Y", 2.0, 3.0, 2.5),
    TimeBucket("3Y – 4Y", 3.0, 4.0, 3.5),
    TimeBucket("4Y – 5Y", 4.0, 5.0, 4.5),
    TimeBucket("5Y – 6Y", 5.0, 6.0, 5.5),
    TimeBucket("6Y – 7Y", 6.0, 7.0, 6.5),
    TimeBucket("7Y – 8Y", 7.0, 8.0, 7.5),
    TimeBucket("8Y – 9Y", 8.0, 9.0, 8.5),
    TimeBucket("9Y – 10Y", 9.0, 10.0, 9.5),
    TimeBucket("10Y – 15Y", 10.0, 15.0, 12.5),
    TimeBucket("15Y – 20Y", 15.0, 20.0, 17.5),
    TimeBucket("20Y+", 20.0, math.inf, 25.0),
)


def assign_bucket(remaining_years: float) -> int:
    """Return the index of the IRRBB bucket for the given remaining years to repricing.

    Buckets use half-open intervals (lower, upper] so that boundary values such as
    exactly 8.0 years fall into the 7Y-8Y bucket rather than 8Y-9Y.  The overnight
    bucket (index 0) is a special case: it captures zero and any value below its upper
    bound (i.e. [0, upper)).

    Negative or zero values are assigned to the overnight bucket (index 0).
    """
    if remaining_years <= 0:
        return 0
    # Overnight bucket: [0, upper)
    if remaining_years < IRRBB_BUCKETS[0].upper:
        return 0
    # Remaining buckets: (lower, upper]
    for i in range(1, len(IRRBB_BUCKETS)):
        bucket = IRRBB_BUCKETS[i]
        if bucket.lower < remaining_years <= bucket.upper:
            return i
    return len(IRRBB_BUCKETS) - 1  # fallback to last bucket (upper == inf)
