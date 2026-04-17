"""Generate ``diversified_bank.zip`` -- 2-3 instruments per major type.

Simulation start date: **2022-01-04**.

    Instrument                  Basis            Amount     Acquired     Side   Book
    ========================    ===============  =========  ==========   =====  =======
    Common Equity               NA               2,000,000  2021-01-04   SHORT  BANKING
    Retained Earnings           NA                 500,000  2021-01-04   SHORT  BANKING
    Demand Deposit (0%)         NA               3,000,000  2021-01-04   SHORT  BANKING
    Savings Deposit (0.5%)      NA               4,000,000  2021-01-04   SHORT  BANKING
    Term Deposit (2%)           NA               5,000,000  2021-01-04   SHORT  BANKING
    10Y Treasury 3.5% HTM       AMORTIZED_COST    (NPV)    2021-01-04   LONG   BANKING
    5Y Treasury 2.5% HTM        AMORTIZED_COST    (NPV)    2021-01-04   LONG   BANKING
    5Y Corp Bond 4.5% FVOCI     FVOCI             (NPV)    2021-06-01   LONG   BANKING
    3Y Corp Bond 3.5% FVTPL     FVTPL             (NPV)    2021-01-04   LONG   TRADING
    7Y Corp Bond 5.0% FVTPL     FVTPL             (NPV)    2021-01-04   LONG   TRADING
    30Y Res Mortgage 5%         AMORTIZED_COST  (outstand)  2021-01-04   LONG   BANKING
    15Y Res Mortgage 4%         AMORTIZED_COST  (outstand)  2021-06-01   LONG   BANKING
    Prime+250bp 5Y C&I Loan     AMORTIZED_COST   3,000,000  2021-06-01   LONG   BANKING
    Prime+175bp 3Y Revolver     AMORTIZED_COST   2,000,000  2021-06-01   LONG   BANKING

Bond acquisition costs are QuantLib NPV at acquisition date.
Mortgage/loan acquisition costs are QL outstanding balance at acquisition date.

Run::

    uv run python src/brms/data/create_diversified_bank.py [data_folder]

Where ``data_folder`` contains ``treasury_yields.csv`` and ``prime_rates.csv``.
If omitted, yields are extracted from ``htm_treasury.zip`` and prime rates
from ``temp/data/prime_rates.csv``.
"""

from __future__ import annotations

import contextlib
import copy
import json
import sys
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent
_OUT_PATH = _DATA_DIR / "diversified_bank.zip"
_START_DATE = "2022-01-04"
_PRIME_CSV_DEFAULT = Path(__file__).resolve().parents[3] / "temp" / "data" / "prime_rates.csv"

# -- Instrument & position definitions -----------------------------------------------

_ISSUER_GOV = {"name": "US Government", "issuer_type": "SOVEREIGN", "credit_rating": "AAA"}
_ISSUER_CORP = {"name": "Acme Corp", "issuer_type": "CORPORATE", "credit_rating": "A"}
_ISSUER_CORP_B = {"name": "Beta Industries", "issuer_type": "CORPORATE", "credit_rating": "BBB"}
_ISSUER_INDIVIDUAL = {"name": "Borrower A", "issuer_type": "INDIVIDUAL", "credit_rating": "UNRATED"}
_ISSUER_INDIVIDUAL_B = {"name": "Borrower B", "issuer_type": "INDIVIDUAL", "credit_rating": "UNRATED"}

INSTRUMENTS = [
    # -- Equity (2) --
    {"id": "equity-001", "type": "common_equity", "name": "Common Equity"},
    {"id": "equity-002", "type": "common_equity", "name": "Retained Earnings"},
    # -- Deposits (3): non-interest-bearing + interest-bearing --
    {"id": "deposit-001", "type": "deposit", "name": "Demand Deposit (NIB)", "interest_rate": 0.0},
    {"id": "deposit-002", "type": "deposit", "name": "Savings Deposit 0.5%", "interest_rate": 0.005},
    {"id": "deposit-003", "type": "deposit", "name": "Term Deposit 2%", "interest_rate": 0.02},
    # -- Treasury Notes (2) --
    {
        "id": "tnote-10y",
        "type": "treasury_note",
        "name": "10Y Treasury 3.5% (HTM)",
        "face_value": 1_000_000.0,
        "coupon_rate": 0.035,
        "issue_date": "2020-01-01",
        "maturity_date": "2030-01-01",
        "measurement_basis": "AMORTIZED_COST",
        "credit_rating": "AAA",
        "issuer": _ISSUER_GOV,
    },
    {
        "id": "tnote-5y",
        "type": "treasury_note",
        "name": "5Y Treasury 2.5% (HTM)",
        "face_value": 500_000.0,
        "coupon_rate": 0.025,
        "issue_date": "2020-06-01",
        "maturity_date": "2025-06-01",
        "measurement_basis": "AMORTIZED_COST",
        "credit_rating": "AAA",
        "issuer": _ISSUER_GOV,
    },
    # -- Corporate Bonds (3) --
    {
        "id": "corp-bond-5y",
        "type": "fixed_rate_bond",
        "name": "5Y Corporate Bond 4.5% (FVOCI)",
        "face_value": 300_000.0,
        "coupon_rate": 0.045,
        "issue_date": "2021-06-01",
        "maturity_date": "2026-06-01",
        "measurement_basis": "FVOCI",
        "credit_rating": "A",
        "issuer": _ISSUER_CORP,
    },
    {
        "id": "fvtpl-3y",
        "type": "fixed_rate_bond",
        "name": "3Y Corporate Bond 3.5% (FVTPL)",
        "face_value": 200_000.0,
        "coupon_rate": 0.035,
        "issue_date": "2021-01-04",
        "maturity_date": "2024-01-04",
        "measurement_basis": "FVTPL",
        "credit_rating": "BBB",
        "issuer": _ISSUER_CORP,
    },
    {
        "id": "fvtpl-7y",
        "type": "fixed_rate_bond",
        "name": "7Y Corporate Bond 5.0% (FVTPL)",
        "face_value": 400_000.0,
        "coupon_rate": 0.05,
        "issue_date": "2021-01-04",
        "maturity_date": "2028-01-04",
        "measurement_basis": "FVTPL",
        "credit_rating": "BBB",
        "issuer": _ISSUER_CORP_B,
    },
    # -- Mortgages (2) --
    {
        "id": "mortgage-30y",
        "type": "residential_mortgage",
        "name": "30Y Residential Mortgage 5%",
        "face_value": 2_000_000.0,
        "interest_rate": 0.05,
        "issue_date": "2020-06-01",
        "maturity": "30Y",
        "measurement_basis": "AMORTIZED_COST",
        "credit_rating": "UNRATED",
        "issuer": _ISSUER_INDIVIDUAL,
    },
    {
        "id": "mortgage-15y",
        "type": "residential_mortgage",
        "name": "15Y Residential Mortgage 4%",
        "face_value": 1_500_000.0,
        "interest_rate": 0.04,
        "issue_date": "2021-06-01",
        "maturity": "15Y",
        "measurement_basis": "AMORTIZED_COST",
        "credit_rating": "UNRATED",
        "issuer": _ISSUER_INDIVIDUAL_B,
    },
    # -- Variable Rate Loans (2) --
    {
        "id": "ci-loan-001",
        "type": "variable_rate_loan",
        "name": "Prime+250bp 5Y C&I Loan",
        "face_value": 3_000_000.0,
        "spread": 0.025,
        "issue_date": "2021-06-01",
        "maturity": "5Y",
        "benchmark_family": "prime",
        "repricing_frequency": "1M",
        "payment_frequency": "1M",
        "principal_repayment_mode": "bullet",
        "measurement_basis": "AMORTIZED_COST",
        "credit_rating": "BBB",
        "issuer": _ISSUER_CORP_B,
    },
    {
        "id": "ci-loan-002",
        "type": "variable_rate_loan",
        "name": "Prime+175bp 3Y Revolver",
        "face_value": 2_000_000.0,
        "spread": 0.0175,
        "issue_date": "2021-06-01",
        "maturity": "3Y",
        "benchmark_family": "prime",
        "repricing_frequency": "3M",
        "payment_frequency": "3M",
        "principal_repayment_mode": "bullet",
        "measurement_basis": "AMORTIZED_COST",
        "credit_rating": "A",
        "issuer": _ISSUER_CORP,
    },
]

POSITIONS = [
    # Equity
    {
        "id": "pos-equity",
        "instrument_id": "equity-001",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 2_000_000.0,
    },
    {
        "id": "pos-retained",
        "instrument_id": "equity-002",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 500_000.0,
    },
    # Deposits
    {
        "id": "pos-demand",
        "instrument_id": "deposit-001",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 3_000_000.0,
    },
    {
        "id": "pos-savings",
        "instrument_id": "deposit-002",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 4_000_000.0,
    },
    {
        "id": "pos-term",
        "instrument_id": "deposit-003",
        "book_type": "BANKING",
        "measurement_basis": "NA",
        "side": "SHORT",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 5_000_000.0,
    },
    # Treasury notes
    {
        "id": "pos-tnote-10y",
        "instrument_id": "tnote-10y",
        "book_type": "BANKING",
        "measurement_basis": "AMORTIZED_COST",
        "side": "LONG",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 500_000.0,  # replaced by NPV
    },
    {
        "id": "pos-tnote-5y",
        "instrument_id": "tnote-5y",
        "book_type": "BANKING",
        "measurement_basis": "AMORTIZED_COST",
        "side": "LONG",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 250_000.0,  # replaced by NPV
    },
    # Corporate bonds
    {
        "id": "pos-corp-bond",
        "instrument_id": "corp-bond-5y",
        "book_type": "BANKING",
        "measurement_basis": "FVOCI",
        "side": "LONG",
        "acquisition_date": "2021-06-01",
        "acquisition_cost": 300_000.0,  # replaced by NPV
    },
    {
        "id": "pos-fvtpl-3y",
        "instrument_id": "fvtpl-3y",
        "book_type": "TRADING",
        "measurement_basis": "FVTPL",
        "side": "LONG",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 200_000.0,  # replaced by NPV
    },
    {
        "id": "pos-fvtpl-7y",
        "instrument_id": "fvtpl-7y",
        "book_type": "TRADING",
        "measurement_basis": "FVTPL",
        "side": "LONG",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 400_000.0,  # replaced by NPV
    },
    # Mortgages
    {
        "id": "pos-mortgage-30y",
        "instrument_id": "mortgage-30y",
        "book_type": "BANKING",
        "measurement_basis": "AMORTIZED_COST",
        "side": "LONG",
        "acquisition_date": "2021-01-04",
        "acquisition_cost": 400_000.0,  # replaced by QL outstanding
    },
    {
        "id": "pos-mortgage-15y",
        "instrument_id": "mortgage-15y",
        "book_type": "BANKING",
        "measurement_basis": "AMORTIZED_COST",
        "side": "LONG",
        "acquisition_date": "2021-06-01",
        "acquisition_cost": 300_000.0,  # replaced by QL outstanding
    },
    # Variable rate loans
    {
        "id": "pos-ci-loan-1",
        "instrument_id": "ci-loan-001",
        "book_type": "BANKING",
        "measurement_basis": "AMORTIZED_COST",
        "side": "LONG",
        "acquisition_date": "2021-06-01",
        "acquisition_cost": 3_000_000.0,
    },
    {
        "id": "pos-ci-loan-2",
        "instrument_id": "ci-loan-002",
        "book_type": "BANKING",
        "measurement_basis": "AMORTIZED_COST",
        "side": "LONG",
        "acquisition_date": "2021-06-01",
        "acquisition_cost": 2_000_000.0,
    },
]

_BOND_IDS = frozenset({"tnote-10y", "tnote-5y", "corp-bond-5y", "fvtpl-3y", "fvtpl-7y"})


def _set_bond_fair_values(
    instruments: list,
    positions_data: list[dict],
    yields_csv: Path,
) -> None:
    """Replace acquisition_cost with QuantLib NPV for bond positions."""
    import pandas as pd
    import QuantLib as ql  # noqa: N813

    from brms.core.models.market_data import MarketDataStore
    from brms.core.services.valuation_context import ValuationContext

    inst_lookup = {inst.id: inst for inst in instruments}
    yields_df = pd.read_csv(yields_csv, index_col="date", parse_dates=True)
    market_data = MarketDataStore()
    market_data.add_frame("yields", yields_df)

    yield_handle = ql.RelinkableYieldTermStructureHandle()
    context = ValuationContext(yield_handle)

    for p in positions_data:
        if p["instrument_id"] not in _BOND_IDS:
            continue
        acq_date = date.fromisoformat(p["acquisition_date"])
        context.update(acq_date, market_data)
        inst = inst_lookup[p["instrument_id"]]
        ql_inst = getattr(inst, "ql_instrument", None)
        if ql_inst is None:
            continue
        ql_inst.setPricingEngine(ql.DiscountingBondEngine(yield_handle))
        with contextlib.suppress(RuntimeError):
            p["acquisition_cost"] = round(ql_inst.NPV(), 2)


def _set_loan_acquisition_costs(instruments: list, positions_data: list[dict]) -> None:
    """Replace acquisition_cost with QL outstanding balance at acquisition date."""
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
    yields_csv: Path,
    prime_csv: Path,
) -> tuple[list, list]:
    """Construct Instrument and Position objects from raw dicts."""
    import pandas as pd
    import QuantLib as ql  # noqa: N813

    from brms.core.enums import BookType, MeasurementBasis, PositionSide
    from brms.core.models.instruments.bonds import FixedRateBond, TreasuryNote
    from brms.core.models.instruments.deposits import Cash, Deposit
    from brms.core.models.instruments.equity import CommonEquity
    from brms.core.models.instruments.loans import ResidentialMortgage, VariableRateLoan
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
    registry.register("cash", Cash)
    registry.register("deposit", Deposit)
    registry.register("common_equity", CommonEquity)
    registry.register("treasury_note", TreasuryNote)
    registry.register("fixed_rate_bond", FixedRateBond)
    registry.register("residential_mortgage", ResidentialMortgage)
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

    _set_bond_fair_values(instruments, positions_data, yields_csv)
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


def create_diversified_zip(data_folder: Path, out_path: Path | None = None) -> Path:
    """Write the diversified simulation zip to *out_path* and return its path.

    *data_folder* must contain ``treasury_yields.csv`` and ``prime_rates.csv``.
    """
    import pandas as pd

    from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder

    out_path = out_path or _OUT_PATH
    yields_csv = data_folder / "treasury_yields.csv"
    prime_csv = data_folder / "prime_rates.csv"

    if not prime_csv.exists():
        prime_csv = _PRIME_CSV_DEFAULT
    if not prime_csv.exists():
        msg = f"Prime rate CSV not found at {prime_csv}"
        raise FileNotFoundError(msg)

    instruments_data = copy.deepcopy(INSTRUMENTS)
    positions_data = copy.deepcopy(POSITIONS)
    instruments, positions = _build_objects(instruments_data, positions_data, yields_csv, prime_csv)

    yields_df = pd.read_csv(yields_csv, index_col="date", parse_dates=True)
    prime_df = pd.read_csv(prime_csv, index_col="date", parse_dates=True)

    snapshot = SimulationBuilder().build(
        BuildConfig(
            name="Diversified Bank",
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
                    "end_date": "2025-12-31",
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
        if not yields_csv.exists():
            msg = f"Treasury yields CSV not found at {yields_csv}"
            raise FileNotFoundError(msg)
        zf.write(yields_csv, "yields.csv")
        zf.writestr("benchmarks.csv", prime_df.to_csv())

    return out_path


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


if __name__ == "__main__":
    if len(sys.argv) >= 2:  # noqa: PLR2004
        folder = Path(sys.argv[1])
    else:
        folder = _extract_yields_from_existing_zip()
        print(f"Extracted yields from htm_treasury.zip to {folder}")  # noqa: T201
    path = create_diversified_zip(data_folder=folder)
    print(f"Created {path}")  # noqa: T201
