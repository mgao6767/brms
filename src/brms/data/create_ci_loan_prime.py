"""Generate ``ci_loan_prime.zip`` -- Prime-indexed variable-rate C&I loan.

Simulation start date: **2022-01-04**.

    Instrument              Basis            Amount     Acquired     Side   Book
    --------------------    ---------------  ---------  ----------   -----  -------
    Common Equity           NA               2,000,000  2021-06-01   SHORT  BANKING
    Term Deposit 2%         NA               3,000,000  2021-06-01   SHORT  BANKING
    Prime+250bp 5Y CI Loan  AMORTIZED_COST   5,000,000  2021-06-01   LONG   BANKING

The C&I loan is a bullet (no amortization) variable-rate loan indexed to
U.S. Bank Prime Rate plus 250 basis points, repricing monthly.  The
simulation window catches the 2022 Fed tightening cycle where Prime rose
from 3.25% to 7.50%.

Run::

    uv run python src/brms/data/create_ci_loan_prime.py

Yields are extracted from the existing ``htm_treasury.zip``.
Prime rate history is loaded from ``temp/data/prime_rates.csv``.
"""

from __future__ import annotations

import copy
import json
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent
_OUT_PATH = _DATA_DIR / "ci_loan_prime.zip"
_START_DATE = "2022-01-04"
_END_DATE = "2025-12-31"
_PRIME_CSV = Path(__file__).resolve().parents[3] / "temp" / "data" / "prime_rates.csv"

_ISSUER_CORP = {"name": "Acme Manufacturing", "issuer_type": "CORPORATE", "credit_rating": "BBB"}

INSTRUMENTS = [
    {"id": "equity-001", "type": "common_equity", "name": "Common Equity"},
    {"id": "deposit-001", "type": "deposit", "name": "Term Deposit 2%", "interest_rate": 0.02},
    {
        "id": "ci-loan-001",
        "type": "variable_rate_loan",
        "name": "Prime+250bp 5Y C&I Loan",
        "face_value": 5_000_000.0,
        "spread": 0.025,
        "issue_date": "2021-06-01",
        "maturity": "5Y",
        "benchmark_family": "prime",
        "repricing_frequency": "1M",
        "payment_frequency": "1M",
        "principal_repayment_mode": "bullet",
        "measurement_basis": "AMORTIZED_COST",
        "credit_rating": "BBB",
        "issuer": _ISSUER_CORP,
    },
]

POSITIONS = [
    {
        "id": "pos-equity",
        "instrument_id": "equity-001",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-06-01",
        "acquisition_cost": 2_000_000.0,
    },
    {
        "id": "pos-deposit",
        "instrument_id": "deposit-001",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-06-01",
        "acquisition_cost": 3_000_000.0,
    },
    {
        "id": "pos-ci-loan",
        "instrument_id": "ci-loan-001",
        "book_type": "BANKING",
        "measurement_basis": "AMORTIZED_COST",
        "side": "LONG",
        "acquisition_date": "2021-06-01",
        "acquisition_cost": 5_000_000.0,
    },
]


def _build_objects(
    instruments_data: list[dict],
    positions_data: list[dict],
    prime_csv: Path,
) -> tuple[list, list]:
    """Construct Instrument and Position objects from raw dicts."""
    import pandas as pd
    import QuantLib as ql  # noqa: N813

    from brms.core.enums import BookType, MeasurementBasis, PositionSide
    from brms.core.models.instruments.deposits import Deposit
    from brms.core.models.instruments.equity import CommonEquity
    from brms.core.models.instruments.loans import VariableRateLoan
    from brms.core.models.instruments.registry import InstrumentRegistry
    from brms.core.models.market_data import MarketDataStore
    from brms.core.models.position import Position
    from brms.core.services.benchmark_service import BenchmarkService
    from brms.core.services.data_service import _convert_kwargs

    shared_yield_handle = ql.RelinkableYieldTermStructureHandle()
    benchmark_service = BenchmarkService(forwarding_handle=shared_yield_handle)

    prime_df = pd.read_csv(prime_csv, index_col="date", parse_dates=True)
    temp_store = MarketDataStore()
    temp_store.add_frame("benchmarks", prime_df)
    benchmark_service.sync_up_to(date(2030, 1, 1), temp_store)

    registry = InstrumentRegistry()
    registry.register("common_equity", CommonEquity)
    registry.register("deposit", Deposit)
    registry.register(
        "variable_rate_loan",
        lambda **kw: VariableRateLoan(ibor_index=benchmark_service.prime_index, **kw),
    )

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


def _extract_yields_from_existing_zip() -> Path:
    """Extract yields.csv from htm_treasury.zip to a temp dir and return the folder path."""
    import tempfile

    existing = _DATA_DIR / "htm_treasury.zip"
    if not existing.exists():
        msg = f"Cannot find {existing} -- needed for yield curve data"
        raise FileNotFoundError(msg)
    tmp_dir = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(existing) as zf:
        zf.extract("yields.csv", tmp_dir)
    (tmp_dir / "yields.csv").rename(tmp_dir / "treasury_yields.csv")
    return tmp_dir


def create_ci_loan_prime_zip(out_path: Path | None = None) -> Path:
    """Write the CI loan simulation zip to *out_path* and return its path."""
    import pandas as pd

    from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder

    out_path = out_path or _OUT_PATH

    if not _PRIME_CSV.exists():
        msg = f"Prime rate CSV not found at {_PRIME_CSV}"
        raise FileNotFoundError(msg)

    yields_folder = _extract_yields_from_existing_zip()
    yields_csv = yields_folder / "treasury_yields.csv"

    instruments_data = copy.deepcopy(INSTRUMENTS)
    positions_data = copy.deepcopy(POSITIONS)
    instruments, positions = _build_objects(instruments_data, positions_data, _PRIME_CSV)

    yields_df = pd.read_csv(yields_csv, index_col="date", parse_dates=True)
    prime_df = pd.read_csv(_PRIME_CSV, index_col="date", parse_dates=True)

    snapshot = SimulationBuilder().build(
        BuildConfig(
            name="C&I Loan (Prime)",
            start_date=date.fromisoformat(_START_DATE),
            instruments=instruments,
            positions=positions,
            market_frames={"yields": yields_df, "benchmarks": prime_df},
        ),
    )

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "config.json",
            json.dumps(
                {
                    "name": snapshot.name,
                    "start_date": snapshot.start_date.isoformat(),
                    "end_date": _END_DATE,
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
                    "valuations": snapshot.valuations,
                },
                indent=2,
            ),
        )
        zf.write(yields_csv, "yields.csv")
        zf.writestr("benchmarks.csv", prime_df.to_csv())

    return out_path


if __name__ == "__main__":
    path = create_ci_loan_prime_zip()
    print(f"Created {path}")  # noqa: T201
