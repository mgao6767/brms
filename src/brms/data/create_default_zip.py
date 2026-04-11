"""Generate the default simulation zip archive (v2 format).

This script builds ``default_simulation.zip`` containing:

* ``config.json``       -- simulation configuration.
* ``instruments.json``  -- instrument definitions with constructor kwargs.
* ``positions.json``    -- one position per instrument.
* ``yields.csv``        -- historical yield curve data.

Run with::

    uv run python src/brms/data/create_default_zip.py /path/to/data/folder

"""

from __future__ import annotations

import contextlib
import json
import random
import sys
import uuid
import zipfile
from datetime import date
from pathlib import Path

from dateutil.relativedelta import relativedelta

# Seed for reproducibility -- same as the old default/__init__.py
random.seed(42)

_DATA_DIR = Path(__file__).resolve().parent
_OUT_PATH = _DATA_DIR / "default_simulation.zip"

_START_DATE = "2022-01-03"


def _issuer_dict(name: str, issuer_type: str, credit_rating: str = "UNRATED") -> dict:
    return {"name": name, "issuer_type": issuer_type, "credit_rating": credit_rating}


def _build_instruments_and_positions() -> tuple[list[dict], list[dict]]:
    """Build the instruments.json and positions.json structures."""
    instruments: list[dict] = []
    positions: list[dict] = []

    def _add(
        inst: dict, book_type: str, measurement_basis: str, acquisition_cost: float,
        side: str = "LONG",
    ) -> None:
        inst_id = str(uuid.uuid4())
        inst["id"] = inst_id
        instruments.append(inst)
        positions.append({
            "id": str(uuid.uuid4()),
            "instrument_id": inst_id,
            "book_type": book_type,
            "measurement_basis": measurement_basis,
            "side": side,
            "acquisition_date": _START_DATE,
            "acquisition_cost": acquisition_cost,
        })

    # 1. CommonEquity (1,000,000) — liability side (SHORT)
    _add(
        {"type": "common_equity", "name": "Common Equity"},
        book_type="BANKING",
        measurement_basis="NA",
        acquisition_cost=1_000_000,
        side="SHORT",
    )

    # 2. Deposit (6,000,000) — liability side (SHORT)
    _add(
        {"type": "deposit", "name": "Deposit"},
        book_type="BANKING",
        measurement_basis="NA",
        acquisition_cost=6_000_000,
        side="SHORT",
    )

    # 3. HTM TreasuryNote (10,000 face, 5% coupon)
    _add(
        {
            "type": "treasury_note",
            "face_value": 10_000.0,
            "coupon_rate": 0.05,
            "issue_date": "2020-01-01",
            "maturity_date": "2030-01-01",
            "measurement_basis": "AMORTIZED_COST",
            "credit_rating": "AAA",
            "issuer": _issuer_dict("Government", "SOVEREIGN", "AAA"),
        },
        book_type="BANKING",
        measurement_basis="AMORTIZED_COST",
        acquisition_cost=10_000.0,
    )

    # 4. Five residential mortgages (200k-500k, random rates/terms)
    for _i in range(5):
        face_value = 200_000 + 100_000 * random.randint(1, 3)  # noqa: S311
        interest_rate = 0.05 + 0.01 * random.randint(0, 3)  # noqa: S311
        months_offset = random.randint(0, 24)  # noqa: S311
        issue = date(2020, 10, 1) + relativedelta(months=months_offset)
        maturity_years = random.choice([10, 20, 30])  # noqa: S311

        _add(
            {
                "type": "residential_mortgage",
                "face_value": float(face_value),
                "interest_rate": interest_rate,
                "issue_date": issue.isoformat(),
                "maturity": f"{maturity_years}Y",
                "measurement_basis": "AMORTIZED_COST",
                "credit_rating": "UNRATED",
                "issuer": _issuer_dict("Residential Mortgage Issuer", "INDIVIDUAL"),
            },
            book_type="BANKING",
            measurement_basis="AMORTIZED_COST",
            acquisition_cost=float(face_value),
        )

    # 5. Ten FVOCI TreasuryNotes (100k each)
    for _i in range(10):
        coupon_rate = 0.0125 * random.randint(1, 5)  # noqa: S311
        years = random.choice([3, 5, 7, 10])  # noqa: S311
        mat = date(2020, 1, 1) + relativedelta(years=years)
        _add(
            {
                "type": "treasury_note",
                "face_value": 100_000.0,
                "coupon_rate": coupon_rate,
                "issue_date": "2020-01-01",
                "maturity_date": mat.isoformat(),
                "measurement_basis": "FVOCI",
                "credit_rating": "AAA",
                "issuer": _issuer_dict("Government", "SOVEREIGN", "AAA"),
            },
            book_type="BANKING",
            measurement_basis="FVOCI",
            acquisition_cost=100_000.0,
        )

    # 6. Ten FVTPL TreasuryNotes (100k each, trading book)
    for _i in range(10):
        coupon_rate = 0.0125 * random.randint(1, 5)  # noqa: S311
        years = random.choice([3, 5, 7, 10])  # noqa: S311
        mat = date(2020, 1, 1) + relativedelta(years=years)
        _add(
            {
                "type": "treasury_note",
                "face_value": 100_000.0,
                "coupon_rate": coupon_rate,
                "issue_date": "2020-01-01",
                "maturity_date": mat.isoformat(),
                "measurement_basis": "FVTPL",
                "book_type": "trading",
                "credit_rating": "AAA",
                "issuer": _issuer_dict("Government", "SOVEREIGN", "AAA"),
            },
            book_type="TRADING",
            measurement_basis="FVTPL",
            acquisition_cost=100_000.0,
        )

    return instruments, positions


def _compute_fair_values(instruments: list, positions_data: list[dict], yields_csv: Path) -> None:
    """Set acquisition_cost to QuantLib NPV for FVOCI/FVTPL bond positions.

    Mutates *positions_data* in place. Only FVOCI and FVTPL positions are
    updated — HTM, mortgages, deposits, and equity keep their original cost.
    """
    import QuantLib as ql  # noqa: N813

    from brms.core.models.market_data import MarketDataStore
    from brms.core.services.valuation_context import ValuationContext

    inst_lookup = {inst.id: inst for inst in instruments}

    # Load market data for yield curve construction
    import pandas as pd

    yields_df = pd.read_csv(yields_csv, index_col="date", parse_dates=True)
    market_data = MarketDataStore()
    market_data.add_frame("yields", yields_df)

    yield_handle = ql.RelinkableYieldTermStructureHandle()
    context = ValuationContext(yield_handle)

    # Group FVOCI/FVTPL positions by acquisition date to minimise context rebuilds
    date_groups: dict[date, list[dict]] = {}
    for p in positions_data:
        if p["measurement_basis"] in ("FVOCI", "FVTPL"):
            acq = date.fromisoformat(p["acquisition_date"])
            date_groups.setdefault(acq, []).append(p)

    for acq_date, pos_dicts in date_groups.items():
        context.update(acq_date, market_data)
        for p in pos_dicts:
            inst = inst_lookup[p["instrument_id"]]
            ql_inst = getattr(inst, "ql_instrument", None)
            if ql_inst is None:
                continue
            engine = ql.DiscountingBondEngine(yield_handle)
            ql_inst.setPricingEngine(engine)
            with contextlib.suppress(RuntimeError):
                p["acquisition_cost"] = round(ql_inst.NPV(), 2)


def _build_objects(instruments_data: list[dict], positions_data: list[dict], yields_csv: Path) -> tuple[list, list]:
    """Construct Instrument and Position objects from raw dicts."""
    from decimal import Decimal

    from brms.core.enums import BookType, MeasurementBasis, PositionSide
    from brms.core.models.instruments.bonds import TreasuryNote
    from brms.core.models.instruments.deposits import Cash, Deposit
    from brms.core.models.instruments.equity import CommonEquity
    from brms.core.models.instruments.loans import ResidentialMortgage
    from brms.core.models.instruments.registry import InstrumentRegistry
    from brms.core.models.position import Position
    from brms.core.services.data_service import _convert_kwargs

    registry = InstrumentRegistry()
    registry.register("cash", Cash)
    registry.register("deposit", Deposit)
    registry.register("common_equity", CommonEquity)
    registry.register("treasury_note", TreasuryNote)
    registry.register("residential_mortgage", ResidentialMortgage)

    instruments = []
    for item in instruments_data:
        item_copy = dict(item)
        type_id = item_copy.pop("type")
        instrument_id = item_copy.pop("id", None)
        instrument_name = item_copy.pop("name", None)
        item_copy.pop("value", None)
        item_copy.pop("book_type", None)
        _convert_kwargs(item_copy)
        inst = registry.create(type_id, **item_copy)
        if instrument_id is not None:
            inst.id = instrument_id
        if instrument_name is not None:
            inst.name = instrument_name
        instruments.append(inst)

    # Compute fair-value acquisition costs for FVOCI/FVTPL bonds
    _compute_fair_values(instruments, positions_data, yields_csv)

    positions = [
        Position(
            id=p["id"],
            instrument_id=p["instrument_id"],
            book_type=BookType[p["book_type"]],
            measurement_basis=MeasurementBasis[p["measurement_basis"]],
            side=PositionSide[p["side"]],
            acquisition_date=date.fromisoformat(p["acquisition_date"]),
            acquisition_cost=Decimal(str(p["acquisition_cost"])),
        )
        for p in positions_data
    ]

    return instruments, positions


def create_default_zip(data_folder: Path, out_path: Path | None = None) -> Path:
    """Write the default simulation zip to *out_path* and return its path.

    *data_folder* must contain ``treasury_yields.csv``.
    """
    import pandas as pd

    from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder

    out_path = out_path or _OUT_PATH
    yields_csv = data_folder / "treasury_yields.csv"
    instruments_data, positions_data = _build_instruments_and_positions()
    instruments, positions = _build_objects(instruments_data, positions_data, yields_csv)

    # Load market data
    yields_df = pd.read_csv(yields_csv, index_col="date", parse_dates=True)

    # Build snapshot
    config = BuildConfig(
        name="Default Bank",
        start_date=date.fromisoformat(_START_DATE),
        instruments=instruments,
        positions=positions,
        market_frames={"yields": yields_df},
    )
    snapshot = SimulationBuilder().build(config)

    # Write zip
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        config_dict = {
            "name": snapshot.name,
            "start_date": snapshot.start_date.isoformat(),
        }
        zf.writestr("config.json", json.dumps(config_dict, indent=2))
        zf.writestr("instruments.json", json.dumps(instruments_data, indent=2))
        zf.writestr("positions.json", json.dumps(positions_data, indent=2))

        balances_dict = {
            "snapshot_date": snapshot.start_date.isoformat(),
            "balances": snapshot.balances,
        }
        zf.writestr("balances.json", json.dumps(balances_dict, indent=2))

        if yields_csv.exists():
            zf.write(yields_csv, "yields.csv")
        else:
            msg = f"Treasury yields CSV not found at {yields_csv}"
            raise FileNotFoundError(msg)

    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:  # noqa: PLR2004
        print("Usage: python create_default_zip.py <data_folder>", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    path = create_default_zip(data_folder=Path(sys.argv[1]))
    print(f"Created {path}")  # noqa: T201
