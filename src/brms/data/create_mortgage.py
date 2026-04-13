"""Generate ``mortgage.zip`` -- a single 30Y Residential Mortgage.

Simulation start date: **2022-01-04**.

    Instrument              Basis            Amount     Acquired     Side   Book
    ────────────────────    ───────────────  ─────────  ──────────   ─────  ───────
    Common Equity           NA               1,000,000  2021-01-04   SHORT  BANKING
    Customer Deposit (0%)   NA               6,000,000  2021-06-01   SHORT  BANKING
    30Y Mortgage 5%         AMORTIZED_COST  (outstand)  2021-09-01   LONG   BANKING

Mortgage: issued 2020-06-01, 30Y term, 5% fixed, monthly payments,
matures 2050-06-01.  Deposit carries 0% interest.  Mortgage acquisition
cost is the QL outstanding balance at acquisition date (the mortgage has
already amortized for 15 months since issuance).

Run::

    uv run python src/brms/data/create_mortgage.py <data_folder>

Where <data_folder> contains ``treasury_yields.csv``.
"""

from __future__ import annotations

import copy
import json
import sys
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent
_OUT_PATH = _DATA_DIR / "mortgage.zip"
_START_DATE = "2022-01-04"

# ── Instrument & position definitions ────────────────────────────────────

_ISSUER_INDIVIDUAL = {"name": "Borrower", "issuer_type": "INDIVIDUAL", "credit_rating": "UNRATED"}

INSTRUMENTS = [
    {"id": "equity-001", "type": "common_equity", "name": "Common Equity"},
    {"id": "deposit-001", "type": "deposit", "name": "Customer Deposit", "interest_rate": 0.0},
    {
        "id": "mortgage-30y",
        "type": "residential_mortgage",
        "name": "30Y Residential Mortgage 5%",
        "face_value": 400_000.0,
        "interest_rate": 0.05,
        "issue_date": "2020-06-01",
        "maturity": "30Y",
        "measurement_basis": "AMORTIZED_COST",
        "credit_rating": "UNRATED",
        "issuer": _ISSUER_INDIVIDUAL,
    },
]

POSITIONS = [
    {
        "id": "pos-equity",
        "instrument_id": "equity-001",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 1_000_000.0,
    },
    {
        "id": "pos-deposit",
        "instrument_id": "deposit-001",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-06-01",
        "acquisition_cost": 6_000_000.0,
    },
    {
        "id": "pos-mortgage-30y",
        "instrument_id": "mortgage-30y",
        "book_type": "BANKING",
        "measurement_basis": "AMORTIZED_COST",
        "side": "LONG",
        "acquisition_date": "2021-09-01",
        "acquisition_cost": 400_000.0,  # replaced by QL outstanding below
    },
]


_LOAN_INSTRUMENT_ID = "mortgage-30y"


def _set_loan_acquisition_costs(instruments: list, positions_data: list[dict]) -> None:
    """Replace acquisition_cost with QL outstanding balance at acquisition date.

    When a mortgage is acquired after issuance, the outstanding principal is
    less than face value.  The acquisition cost should reflect what the bank
    actually paid — the outstanding balance, not the original face.
    """
    import QuantLib as ql  # noqa: N813

    from brms.core.utils import pydate_to_qldate

    inst_lookup = {inst.id: inst for inst in instruments}
    for p in positions_data:
        inst = inst_lookup.get(p["instrument_id"])
        if inst is None:
            continue
        ql_inst = getattr(inst, "ql_instrument", None)
        if ql_inst is None or not isinstance(ql_inst, ql.AmortizingFixedRateBond):
            continue
        acq_date = date.fromisoformat(p["acquisition_date"])
        p["acquisition_cost"] = round(ql_inst.notional(pydate_to_qldate(acq_date)), 2)


def _build_objects(
    instruments_data: list[dict],
    positions_data: list[dict],
) -> tuple[list, list]:
    """Construct Instrument and Position objects from raw dicts."""
    from brms.core.enums import BookType, MeasurementBasis, PositionSide
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

    # Set loan acquisition costs to QL outstanding balance at acquisition date.
    # A mortgage acquired after issuance has already amortized — the bank pays
    # the outstanding principal, not the original face value.
    _set_loan_acquisition_costs(instruments, positions_data)

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


def create_mortgage_zip(data_folder: Path, out_path: Path | None = None) -> Path:
    """Write the mortgage simulation zip to *out_path* and return its path.

    *data_folder* must contain ``treasury_yields.csv``.
    """
    import pandas as pd

    from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder

    out_path = out_path or _OUT_PATH
    yields_csv = data_folder / "treasury_yields.csv"

    instruments_data = copy.deepcopy(INSTRUMENTS)
    positions_data = copy.deepcopy(POSITIONS)
    instruments, positions = _build_objects(instruments_data, positions_data)

    yields_df = pd.read_csv(yields_csv, index_col="date", parse_dates=True)
    snapshot = SimulationBuilder().build(
        BuildConfig(
            name="Mortgage Bank",
            start_date=date.fromisoformat(_START_DATE),
            instruments=instruments,
            positions=positions,
            market_frames={"yields": yields_df},
        ),
    )

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "config.json",
            json.dumps(
                {
                    "name": snapshot.name,
                    "start_date": snapshot.start_date.isoformat(),
                },
                indent=2,
            ),
        )
        zf.writestr("instruments.json", json.dumps(instruments_data, indent=2))
        zf.writestr("positions.json", json.dumps(positions_data, indent=2))
        zf.writestr(
            "balances.json",
            json.dumps(
                {
                    "snapshot_date": snapshot.start_date.isoformat(),
                    "balances": snapshot.balances,
                },
                indent=2,
            ),
        )
        if not yields_csv.exists():
            msg = f"Treasury yields CSV not found at {yields_csv}"
            raise FileNotFoundError(msg)
        zf.write(yields_csv, "yields.csv")

    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:  # noqa: PLR2004
        print("Usage: python create_mortgage.py <data_folder>", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    path = create_mortgage_zip(data_folder=Path(sys.argv[1]))
    print(f"Created {path}")  # noqa: T201
