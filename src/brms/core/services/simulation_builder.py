"""SimulationBuilder: runs the real engine to produce a consistent balance snapshot."""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType, MeasurementBasis, TransactionType, TxMeta, ValuationType
from brms.core.exceptions import UnsupportedPositionError
from brms.core.models.regulatory import RegulatoryConfig
from brms.core.models.transaction import Transaction
from brms.core.services.amortized_cost import AmortizedCostCalculator

if TYPE_CHECKING:
    from collections.abc import Callable

    import pandas as pd

    from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
    from brms.core.models.bank import Bank
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.services.simulation_service import SimulationService

_ZERO_THRESHOLD = 1e-10

# Snapshot valuation keys (balances.json "valuations") and the valuation types they hold.
_SNAPSHOT_VALUATIONS = {
    "carrying_value": ValuationType.CARRYING_VALUE,
    "fair_value": ValuationType.FAIR_VALUE,
    "amortized_cost": ValuationType.AMORTIZED_COST,
    "accrued_interest": ValuationType.ACCRUED_INTEREST,
}

_LOAN_TYPES = frozenset({
    InstrumentType.RESIDENTIAL_MORTGAGE,
    InstrumentType.COMMERCIAL_MORTGAGE,
    InstrumentType.MORTGAGE,
    InstrumentType.AMORTIZING_FIXED_RATE_LOAN,
    InstrumentType.VARIABLE_RATE_LOAN,
})


@dataclass
class BuildConfig:
    """Inputs to the simulation builder."""

    name: str
    start_date: datetime.date
    instruments: list[Instrument]
    positions: list[Position]
    market_frames: dict[str, pd.DataFrame]
    regulatory: RegulatoryConfig = field(default_factory=RegulatoryConfig)


@dataclass
class SimulationSnapshot:
    """Output of the simulation builder."""

    name: str
    start_date: datetime.date
    instruments: list[Instrument]
    positions: list[Position]
    balances: dict[str, float]
    valuations: dict[str, dict[str, float]] = field(default_factory=dict)
    market_frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    regulatory: RegulatoryConfig = field(default_factory=RegulatoryConfig)


class SimulationBuilder:
    """Run the real simulation engine to produce a consistent snapshot."""

    def build(self, config: BuildConfig) -> SimulationSnapshot:
        """Build a simulation snapshot by replaying from earliest acquisition to start_date."""
        late = [p.id for p in config.positions if p.acquisition_date > config.start_date]
        if late:
            msg = f"Positions acquired after the start date {config.start_date} are not supported: {late}"
            raise UnsupportedPositionError(msg)
        snapshot_date = config.start_date - datetime.timedelta(days=1)
        sim, calculator = self._replay(config, snapshot_date, None)
        # Close the books so the snapshot holds only permanent accounts: the loaded
        # simulation's income statement then starts from zero on the start date.
        sim.bank.ledger.close_ledger(snapshot_date)
        self._add_positions_on(config.start_date, config, sim, calculator)
        coa = sim.bank.ledger.chart_of_accounts
        balances = self._extract_balances(coa)
        valuations = self._extract_valuations(sim, sim.bank, config.start_date)
        return SimulationSnapshot(
            name=config.name,
            start_date=config.start_date,
            instruments=config.instruments,
            positions=config.positions,
            balances=balances,
            valuations=valuations,
            market_frames=config.market_frames,
            regulatory=config.regulatory,
        )

    def replay(
        self,
        config: BuildConfig,
        until: datetime.date | None = None,
        *,
        on_advance: Callable[[SimulationService, datetime.date], None] | None = None,
    ) -> SimulationService:
        """Wire an engine and replay every calendar day from the earliest acquisition through *until*.

        Positions are added (with their acquisition transactions) on their acquisition date,
        before that day's advance. *until* defaults to the day before ``config.start_date``.
        *on_advance* is called after each day's advance.
        """
        sim, _calculator = self._replay(config, until or config.start_date - datetime.timedelta(days=1), on_advance)
        return sim

    def _replay(
        self,
        config: BuildConfig,
        until: datetime.date,
        on_advance: Callable[[SimulationService, datetime.date], None] | None,
    ) -> tuple[SimulationService, AmortizedCostCalculator]:
        sim, calculator = self._create_engine(config)
        earliest = min((p.acquisition_date for p in config.positions), default=until)
        current = earliest
        while current <= until:
            self._add_positions_on(current, config, sim, calculator)
            sim.advance(current)
            if on_advance is not None:
                on_advance(sim, current)
            current += datetime.timedelta(days=1)
        return sim, calculator

    def _add_positions_on(
        self,
        day: datetime.date,
        config: BuildConfig,
        sim: SimulationService,
        calculator: AmortizedCostCalculator,
    ) -> None:
        """Add the positions acquired on *day* and post their acquisition transactions."""
        for inst, pos in self._group_by_date(config).get(day, []):
            sim.bank.instruments.add(inst)
            sim.bank.positions.add(pos)
            txns = self._make_acquisition_transactions(inst, pos, calculator)
            sim.accounting_service.post_all(txns, sim.bank.ledger, sim.bank.positions)
            sim.transaction_log.record_batch(txns)

    @staticmethod
    def _create_engine(config: BuildConfig) -> tuple[SimulationService, AmortizedCostCalculator]:
        """Instantiate and wire the full simulation engine."""
        import QuantLib as ql  # noqa: N813

        from brms.core.events import EventBus
        from brms.core.metrics import default_metrics
        from brms.core.metrics.base import MetricRegistry
        from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
        from brms.core.models.accounting.journal import Journal
        from brms.core.models.accounting.ledger import Ledger
        from brms.core.models.bank import Bank
        from brms.core.models.market_data import MarketDataStore
        from brms.core.rules import default_rules
        from brms.core.services.accounting_service import AccountingService
        from brms.core.services.metrics_service import MetricsService
        from brms.core.services.reporting_service import ReportingService
        from brms.core.services.rule_engine import RuleEngine
        from brms.core.services.simulation_service import SimulationService
        from brms.core.services.valuation_service import ValuationService
        from brms.core.services.valuation_strategies import default_valuation_strategies
        from brms.core.stores.instrument_store import InstrumentStore
        from brms.core.stores.metric_store import MetricStore
        from brms.core.stores.position_store import PositionStore
        from brms.core.stores.transaction_log import TransactionLog
        from brms.core.stores.valuation_store import ValuationStore

        calculator = AmortizedCostCalculator()
        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa, journal=Journal())
        bank = Bank(
            name=config.name, instruments=InstrumentStore(), positions=PositionStore(), ledger=ledger,
            regulatory=config.regulatory,
        )
        market_data = MarketDataStore()
        accounting_service = AccountingService()

        for name, df in config.market_frames.items():
            market_data.add_frame(name, df)

        shared_yield_handle = ql.RelinkableYieldTermStructureHandle()
        benchmark_service = None
        if "benchmarks" in config.market_frames:
            from brms.core.services.benchmark_service import BenchmarkService

            benchmark_service = BenchmarkService(forwarding_handle=shared_yield_handle)

        sim = SimulationService(
            bank=bank,
            market_data=market_data,
            valuation_service=ValuationService(
                default_valuation_strategies(calculator),
                benchmark_service=benchmark_service,
                yield_handle=shared_yield_handle,
            ),
            rule_engine=RuleEngine(default_rules()),
            accounting_service=accounting_service,
            metrics_service=MetricsService(MetricRegistry(default_metrics(ReportingService()))),
            valuation_store=ValuationStore(),
            metric_store=MetricStore(),
            transaction_log=TransactionLog(),
            event_bus=EventBus(),
        )
        return sim, calculator

    @staticmethod
    def _group_by_date(config: BuildConfig) -> dict[datetime.date, list[tuple[Instrument, Position]]]:
        """Sort positions by acquisition date and group them."""
        inst_lookup = {inst.id: inst for inst in config.instruments}
        result: dict[datetime.date, list[tuple[Instrument, Position]]] = {}
        for pos in sorted(config.positions, key=lambda p: p.acquisition_date):
            bucket = result.setdefault(pos.acquisition_date, [])
            bucket.append((inst_lookup[pos.instrument_id], pos))
        return result

    @staticmethod
    def _extract_valuations(
        sim: SimulationService,
        bank: Bank,
        start_date: datetime.date,
    ) -> dict[str, dict[str, float]]:
        """Extract each open position's valuations at the snapshot date (start_date - 1).

        Returns ``{position_id: {"carrying_value", "fair_value", "amortized_cost",
        "accrued_interest"}}`` with the keys valuation recorded for that position.
        """
        snapshot_date = start_date - datetime.timedelta(days=1)
        result: dict[str, dict[str, float]] = {}
        for pos in bank.positions.open_positions():
            entry: dict[str, float] = {}
            for key, vtype in _SNAPSHOT_VALUATIONS.items():
                value = sim.valuation_store.get(pos.id, snapshot_date, vtype)
                if value is not None:
                    entry[key] = float(value)
            if entry:
                result[pos.id] = entry
        return result

    @staticmethod
    def _extract_balances(coa: BankChartOfAccounts) -> dict[str, float]:
        """Return non-zero non-temporary account balances from the chart of accounts.

        Excludes temporary accounts and aggregation-only composite accounts
        (those with sub-accounts that aggregate children).  Composites with
        **no** sub-accounts function as leaf posting accounts (e.g. Interest
        Income) and are included.
        """
        from brms.core.models.accounting.accounts import CompositeTAccount

        balances: dict[str, float] = {}
        for account in coa.all_accounts():
            if account.is_temporary_account:
                continue
            if isinstance(account, CompositeTAccount) and list(account.sub_accounts):
                continue
            bal = account.balance()
            if abs(bal) > _ZERO_THRESHOLD:
                balances[account.name] = bal
        return balances

    @staticmethod
    def _make_acquisition_transactions(
        inst: Instrument, pos: Position, calculator: AmortizedCostCalculator,
    ) -> list[Transaction]:
        """Generate the acquisition transaction for a single position.

        ``acquisition_cost`` is the total cash paid at close of business on the acquisition
        date. For bonds and loans the accrued interest bought with the position goes under
        ``TxMeta.ACCRUED_INTEREST`` so that the accounting service books the clean cost to the
        asset and the accrued interest to the receivable.

        Raises:
            UnsupportedPositionError: a loan whose clean cost is not its outstanding principal.

        """
        inst_type = getattr(inst, "instrument_type", None)
        basis = pos.measurement_basis
        metadata: tuple[tuple[TxMeta, object], ...] = ()

        if inst_type == InstrumentType.COMMON_EQUITY:
            tx_type = TransactionType.EQUITY_ISSUANCE
        elif inst_type == InstrumentType.DEPOSIT:
            tx_type = TransactionType.DEPOSIT_RECEIVED
        else:
            _check_acquired_before_final_payment(inst, pos)
            accrued = calculator.accrued_at_acquisition(inst, pos).quantize(Decimal("0.01"))
            if basis == MeasurementBasis.AMORTIZED_COST and inst_type in _LOAN_TYPES:
                tx_type = TransactionType.LOAN_DISBURSEMENT
                _check_loan_at_par(inst, pos, Decimal(str(pos.acquisition_cost)) - accrued)
            else:
                tx_type = TransactionType.SECURITY_PURCHASE
                metadata = ((TxMeta.MEASUREMENT_BASIS, basis),)
            if accrued > 0:
                metadata = (*metadata, (TxMeta.ACCRUED_INTEREST, str(accrued)))

        desc = tx_type.name.replace("_", " ").title()

        return [
            Transaction(
                id=str(uuid.uuid4()),
                type=tx_type,
                date=pos.acquisition_date,
                amount=Decimal(str(pos.acquisition_cost)),
                description=desc,
                position_id=pos.id,
                instrument_id=pos.instrument_id,
                metadata=metadata,
            ),
        ]


def outstanding_principal(instrument: Instrument, date: datetime.date) -> Decimal:
    """Return a loan's scheduled principal outstanding at close of business on *date*."""
    _interest, principal, _outstanding = instrument.payment_schedule()  # type: ignore[attr-defined]
    paid = sum((Decimal(str(amount)) for d, amount in principal if d <= date), Decimal(0))
    return Decimal(str(instrument.face_value)) - paid  # type: ignore[attr-defined]


def _check_loan_at_par(instrument: Instrument, position: Position, clean_cost: Decimal) -> None:
    outstanding = outstanding_principal(instrument, position.acquisition_date)
    if abs(clean_cost - outstanding) > Decimal("0.01"):
        msg = (
            f"Position {position.id}: loans bought at a premium or discount are not supported yet "
            f"(clean cost {clean_cost:.2f}, outstanding principal {outstanding:.2f} on {position.acquisition_date})"
        )
        raise UnsupportedPositionError(msg)


def _check_acquired_before_final_payment(instrument: Instrument, position: Position) -> None:
    """Reject a position acquired on or after its instrument's last scheduled cash flow.

    Such a position would never receive the redemption (no rule fires on the acquisition date),
    so it would sit in the books forever.
    """
    schedule = instrument.payment_schedule() if callable(getattr(instrument, "payment_schedule", None)) else None
    if not schedule:
        return
    flows = schedule[1] if isinstance(schedule, tuple) else schedule  # loans: (interest, principal, outstanding)
    if flows and position.acquisition_date >= flows[-1][0]:
        msg = (
            f"Position {position.id} is acquired on {position.acquisition_date}, on or after the last "
            f"scheduled payment of {instrument.id} ({flows[-1][0]})"
        )
        raise UnsupportedPositionError(msg)

