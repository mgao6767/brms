"""Maturity Gap (Repricing) Model for IRRBB."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from brms.core.enums import BookType, InstrumentType, MeasurementBasis
from brms.core.exceptions import ValuationError
from brms.core.metrics.risk.interest_rate_risk.buckets import IRRBB_BUCKETS, TimeBucket, assign_bucket

if TYPE_CHECKING:
    import datetime

    from brms.core.models.bank import Bank
    from brms.core.stores.valuation_store import ValuationStore

_NON_RATE_SENSITIVE = frozenset({InstrumentType.CASH, InstrumentType.COMMON_EQUITY})
_PARALLEL_SHOCK_BP = 200
_PARALLEL_SHOCK = _PARALLEL_SHOCK_BP / 10_000  # 0.02


@dataclass(frozen=True)
class MaturityGapResult:
    """Output of the maturity gap model."""

    buckets: tuple[TimeBucket, ...] = field(default_factory=lambda: IRRBB_BUCKETS)
    rsa: list[float] = field(default_factory=lambda: [0.0] * len(IRRBB_BUCKETS))
    rsl: list[float] = field(default_factory=lambda: [0.0] * len(IRRBB_BUCKETS))
    gap: list[float] = field(default_factory=lambda: [0.0] * len(IRRBB_BUCKETS))
    cumulative_gap: list[float] = field(default_factory=lambda: [0.0] * len(IRRBB_BUCKETS))
    delta_nii_up: list[float] = field(default_factory=lambda: [0.0] * len(IRRBB_BUCKETS))
    delta_nii_down: list[float] = field(default_factory=lambda: [0.0] * len(IRRBB_BUCKETS))
    total_rsa: float = 0.0
    total_rsl: float = 0.0
    total_gap: float = 0.0
    total_delta_nii_up: float = 0.0
    total_delta_nii_down: float = 0.0


def _repricing_amount(position: object, instrument: object, date: datetime.date, store: ValuationStore) -> float:
    """Return the amount of *position* that reprices: carrying value, or beta x balance for a deposit."""
    from brms.core.enums import ValuationType

    carrying = store.get(position.id, date, ValuationType.CARRYING_VALUE)  # type: ignore[attr-defined]
    if position.measurement_basis != MeasurementBasis.NA:  # type: ignore[attr-defined]
        if carrying is None:
            msg = f"Position {position.id} has no carrying value on {date}"  # type: ignore[attr-defined]
            raise ValuationError(msg)
        return float(carrying)
    # Deposits and other unvalued holdings sit at their balance.
    value = float(carrying if carrying is not None else position.acquisition_cost)  # type: ignore[attr-defined]
    if instrument.instrument_type == InstrumentType.DEPOSIT:  # type: ignore[attr-defined]
        value *= instrument.beta  # the rate moves by beta x the market move: only that share reprices
    return value


class MaturityGapModel:
    """Computes the maturity gap for banking book positions across 19 Basel IRRBB buckets."""

    def compute(
        self,
        bank: Bank,
        date: datetime.date,
        valuation_store: ValuationStore,
    ) -> MaturityGapResult:
        """Classify banking book positions into buckets and compute gap/ΔNII."""
        from brms.core.enums import PositionSide

        rsa = [0.0] * len(IRRBB_BUCKETS)
        rsl = [0.0] * len(IRRBB_BUCKETS)

        for position in bank.positions.open_positions():
            if position.book_type != BookType.BANKING:
                continue
            instrument = bank.instruments.get(position.instrument_id)
            if instrument.instrument_type in _NON_RATE_SENSITIVE:
                continue

            # Determine repricing horizon
            repricing = instrument.repricing_date(date)
            if repricing is not None:
                remaining_years = (repricing - date).days / 365.25
            elif hasattr(instrument, "maturity_date") and instrument.maturity_date is not None:
                remaining_years = (instrument.maturity_date - date).days / 365.25
            else:
                remaining_years = 0.0  # demand deposits → overnight

            bucket_idx = assign_bucket(remaining_years)

            value = _repricing_amount(position, instrument, date, valuation_store)

            if position.side == PositionSide.LONG:
                rsa[bucket_idx] += value
            else:
                rsl[bucket_idx] += value

        # Compute derived columns
        gap = [rsa[i] - rsl[i] for i in range(len(IRRBB_BUCKETS))]
        cumulative_gap: list[float] = []
        running = 0.0
        for g in gap:
            running += g
            cumulative_gap.append(running)
        # A gap repricing at the bucket midpoint m earns the shock for the rest of the year, (1 - m);
        # buckets repricing after one year do not affect 12-month NII.
        exposure = [max(0.0, 1.0 - b.midpoint) for b in IRRBB_BUCKETS]
        delta_nii_up = [g * _PARALLEL_SHOCK * w for g, w in zip(gap, exposure, strict=True)]
        delta_nii_down = [g * -_PARALLEL_SHOCK * w for g, w in zip(gap, exposure, strict=True)]

        return MaturityGapResult(
            rsa=rsa,
            rsl=rsl,
            gap=gap,
            cumulative_gap=cumulative_gap,
            delta_nii_up=delta_nii_up,
            delta_nii_down=delta_nii_down,
            total_rsa=sum(rsa),
            total_rsl=sum(rsl),
            total_gap=sum(gap),
            total_delta_nii_up=sum(delta_nii_up),
            total_delta_nii_down=sum(delta_nii_down),
        )
