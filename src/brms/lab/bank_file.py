"""Build a simulation from a point-in-time bank file: positions as of one date, no acquisition history.

``bank.json``::

    {
      "name": "...", "as_of": "2021-12-31",
      "regulatory": {"aoci_filter": false, "operational_rwa": "...", ...},   # optional
      "cash": 1000000,
      "deposits": [{"id": "dep", "name": "Savings", "balance": 2500000, "interest_rate": 0.001}],
      "positions": [
        {"id": "ust", "type": "treasury_note", <instrument terms>, "issuer": {...},
         "basis": "AMORTIZED_COST" | "FVOCI" | "FVTPL", "book": "BANKING" | "TRADING",
         "amortized_cost": 980000, "fair_value": 950000}
      ]
    }

Values are clean (excluding accrued interest). ``amortized_cost`` is required at amortised cost and
FVOCI; ``fair_value`` is required at FVOCI and FVTPL and optional at amortised cost. Each position is
treated as bought at close of business on the as-of date at its amortised cost (its fair value for
FVTPL), so its effective interest rate is solved from the book value; its credit spread is
calibrated to the reported fair value, or to the book value if none is given. Equity is the
balancing figure. An FVOCI position's reported unrealised gain or loss enters accumulated OCI with
the first day's mark.
"""

from __future__ import annotations

import datetime
import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import QuantLib as ql  # noqa: N813

from brms.core.enums import BookType, MeasurementBasis, PositionSide
from brms.core.exceptions import SimulationDataError
from brms.core.models.instruments import default_instrument_registry
from brms.core.models.instruments.deposits import Deposit
from brms.core.models.instruments.equity import CommonEquity
from brms.core.models.position import Position
from brms.core.models.regulatory import RegulatoryConfig
from brms.core.services.amortized_cost import AmortizedCostCalculator
from brms.core.services.data_service import _convert_kwargs
from brms.core.services.simulation_builder import BuildConfig, SimulationBuilder
from brms.core.services.snapshot_writer import save_snapshot

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

_POSITION_KEYS = frozenset({"id", "basis", "book", "amortized_cost", "fair_value", "side"})


def _require(entry: dict[str, Any], key: str) -> Decimal:
    if entry.get(key) is None:
        msg = f"Position {entry.get('id')!r} ({entry.get('basis')}) needs {key!r}"
        raise SimulationDataError(msg)
    return Decimal(str(entry[key]))


def _registry(market_frames: dict[str, pd.DataFrame], needs_prime: bool) -> tuple[Any, Any]:  # noqa: FBT001
    registry = default_instrument_registry()
    if not needs_prime:
        return registry, None
    from brms.core.models.instruments.loans import VariableRateLoan
    from brms.core.models.market_data import MarketDataStore
    from brms.core.services.benchmark_service import BenchmarkService

    if "benchmarks" not in market_frames:
        msg = "Variable-rate loans need a 'benchmarks' market frame with DPRIME"
        raise SimulationDataError(msg)
    service = BenchmarkService(forwarding_handle=ql.RelinkableYieldTermStructureHandle())
    store = MarketDataStore()
    store.add_frame("benchmarks", market_frames["benchmarks"])
    service.sync_up_to(market_frames["benchmarks"].index.max().date(), store)
    registry.register("variable_rate_loan", lambda **kw: VariableRateLoan(ibor_index=service.prime_index, **kw))
    return registry, service


def build_bank(bank_file: Path, market_frames: dict[str, pd.DataFrame], out: Path) -> Path:
    """Read *bank_file*, build its snapshot with *market_frames* and write the simulation zip to *out*."""
    data = json.loads(bank_file.read_text())
    as_of = datetime.date.fromisoformat(data["as_of"])
    entries = data.get("positions", [])
    registry, benchmark_service = _registry(market_frames, any(e["type"] == "variable_rate_loan" for e in entries))
    calculator = AmortizedCostCalculator()

    instruments, positions, specs = [], [], []
    targets: dict[str, Decimal] = {}
    total_cost = Decimal(0)
    for entry in entries:
        basis = MeasurementBasis[entry.get("basis", "AMORTIZED_COST")]
        spec = {k: v for k, v in entry.items() if k not in _POSITION_KEYS}
        kwargs = {k: v for k, v in spec.items() if k not in {"type", "name"}}
        instrument = registry.create(spec["type"], **_convert_kwargs(dict(kwargs)))
        instrument.id = entry["id"]
        if "name" in spec:
            instrument.name = spec["name"]
        book_key = "fair_value" if basis == MeasurementBasis.FVTPL else "amortized_cost"
        book_value = _require(entry, book_key)
        if basis == MeasurementBasis.FVOCI:
            _require(entry, "fair_value")
        position = Position(
            id=f"pos-{entry['id']}", instrument_id=entry["id"], book_type=BookType[entry.get("book", "BANKING")],
            measurement_basis=basis, side=PositionSide.LONG, acquisition_date=as_of, acquisition_cost=book_value,
        )
        accrued = calculator.accrued_at_acquisition(instrument, position).quantize(Decimal("0.01"))
        position.acquisition_cost = book_value + accrued
        if entry.get("fair_value") is not None:
            targets[position.id] = Decimal(str(entry["fair_value"])) + accrued
        total_cost += position.acquisition_cost
        instruments.append(instrument)
        positions.append(position)
        specs.append({"id": entry["id"], **spec})

    deposits_total = Decimal(0)
    for dep in data.get("deposits", []):
        instrument = Deposit(name=dep.get("name", "Deposit"), interest_rate=dep["interest_rate"])
        instrument.id = dep["id"]
        balance = Decimal(str(dep["balance"]))
        deposits_total += balance
        instruments.append(instrument)
        positions.append(Position(
            id=f"pos-{dep['id']}", instrument_id=dep["id"], book_type=BookType.BANKING,
            measurement_basis=MeasurementBasis.NA, side=PositionSide.SHORT, acquisition_date=as_of,
            acquisition_cost=balance,
        ))
        specs.append(
            {"id": dep["id"], "type": "deposit", "name": instrument.name, "interest_rate": dep["interest_rate"]},
        )

    equity = Decimal(str(data["cash"])) + total_cost - deposits_total
    if equity <= 0:
        msg = f"The bank file implies non-positive equity ({equity:,.2f}): assets must exceed deposits"
        raise SimulationDataError(msg)
    equity_instrument = CommonEquity(name="Common Equity")
    equity_instrument.id = "equity"
    instruments.insert(0, equity_instrument)
    positions.insert(0, Position(
        id="pos-equity", instrument_id="equity", book_type=BookType.BANKING, measurement_basis=MeasurementBasis.NA,
        side=PositionSide.SHORT, acquisition_date=as_of, acquisition_cost=equity,
    ))
    specs.insert(0, {"id": "equity", "type": "common_equity", "name": "Common Equity"})

    config = BuildConfig(
        name=data.get("name", bank_file.stem),
        start_date=as_of + datetime.timedelta(days=1),
        instruments=instruments,
        positions=positions,
        market_frames=market_frames,
        regulatory=RegulatoryConfig.from_json(data.get("regulatory")),
        benchmark_service=benchmark_service,
        calibrate_spreads=True,
        spread_targets=targets,
    )
    end = market_frames["yields"].index.max().date()
    save_snapshot(SimulationBuilder().build(config), specs, out, end_date=end)
    return out
