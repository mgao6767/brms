"""Create the small sample simulation zip used in tests (synthetic flat yields, no external data)."""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from brms.core.enums import BookType, MeasurementBasis, PositionSide
from brms.core.models.instruments import default_instrument_registry
from brms.core.models.position import Position
from brms.core.services.data_service import _convert_kwargs
from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder
from brms.core.services.snapshot_writer import save_snapshot

TENORS = ("1 Mo", "2 Mo", "3 Mo", "4 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr")

_GOV = {"name": "US Government", "issuer_type": "SOVEREIGN", "credit_rating": "AAA"}

INSTRUMENTS: list[dict[str, object]] = [
    {"id": "equity", "type": "common_equity", "name": "Common Equity"},
    {"id": "deposit", "type": "deposit", "name": "Savings Deposit", "interest_rate": 0.01},
    {
        "id": "note-htm", "type": "treasury_note", "face_value": 1_000_000.0, "coupon_rate": 0.04,
        "issue_date": "2022-07-15", "maturity_date": "2025-07-15", "issuer": _GOV,
    },
    {
        "id": "note-oci", "type": "treasury_note", "face_value": 500_000.0, "coupon_rate": 0.03,
        "issue_date": "2022-03-15", "maturity_date": "2024-03-15", "issuer": _GOV,
    },
]

# (id, instrument, basis, side, acquired, total cash paid)
POSITIONS = [
    ("pos-equity", "equity", MeasurementBasis.NA, PositionSide.SHORT, "2023-11-01", "5000000"),
    ("pos-deposit", "deposit", MeasurementBasis.NA, PositionSide.SHORT, "2023-11-01", "3000000"),
    ("pos-htm", "note-htm", MeasurementBasis.AMORTIZED_COST, PositionSide.LONG, "2023-11-01", "1001000"),
    ("pos-oci", "note-oci", MeasurementBasis.FVOCI, PositionSide.LONG, "2023-11-01", "496000"),
]


def _yields() -> pd.DataFrame:
    index = pd.bdate_range("2023-11-01", "2024-01-31", name="date")
    return pd.DataFrame({t: 4.5 for t in TENORS}, index=index)


def create_sample_zip(output_path: Path) -> None:
    """Build the sample bank with the real engine and write it as a simulation zip."""
    registry = default_instrument_registry()
    instruments = []
    for spec in INSTRUMENTS:
        kwargs = dict(spec)
        type_id, iid, name = kwargs.pop("type"), kwargs.pop("id"), kwargs.pop("name", None)
        inst = registry.create(type_id, **_convert_kwargs(kwargs))
        inst.id = iid
        if name:
            inst.name = name
        instruments.append(inst)
    positions = [
        Position(
            id=pid, instrument_id=iid, book_type=BookType.BANKING, measurement_basis=basis, side=side,
            acquisition_date=datetime.date.fromisoformat(acquired), acquisition_cost=Decimal(cost),
        )
        for pid, iid, basis, side, acquired, cost in POSITIONS
    ]
    config = BuildConfig(
        name="Sample Bank",
        start_date=datetime.date(2024, 1, 2),
        instruments=instruments,
        positions=positions,
        market_frames={"yields": _yields()},
    )
    save_snapshot(SimulationBuilder().build(config), INSTRUMENTS, output_path, end_date=datetime.date(2024, 1, 31))


if __name__ == "__main__":
    create_sample_zip(Path(__file__).parent / "sample_simulation.zip")
