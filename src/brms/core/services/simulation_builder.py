"""SimulationBuilder: runs the real engine to produce a consistent balance snapshot."""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from brms.core.enums import InstrumentType, MeasurementBasis, TransactionType
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    import pandas as pd

    from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
    from brms.core.models.bank import Bank
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.position import Position
    from brms.core.services.accounting_service import AccountingService
    from brms.core.services.simulation_service import SimulationService

_ZERO_THRESHOLD = 1e-10

_LOAN_TYPES = frozenset({
    InstrumentType.RESIDENTIAL_MORTGAGE,
    InstrumentType.COMMERCIAL_MORTGAGE,
    InstrumentType.MORTGAGE,
    InstrumentType.AMORTIZING_FIXED_RATE_LOAN,
    InstrumentType.PERSONAL_LOAN,
})


@dataclass
class BuildConfig:
    """Inputs to the simulation builder."""

    name: str
    start_date: datetime.date
    instruments: list[Instrument]
    positions: list[Position]
    market_frames: dict[str, pd.DataFrame]


@dataclass
class SimulationSnapshot:
    """Output of the simulation builder."""

    name: str
    start_date: datetime.date
    instruments: list[Instrument]
    positions: list[Position]
    balances: dict[str, float]
    market_frames: dict[str, pd.DataFrame] = field(default_factory=dict)


class SimulationBuilder:
    """Run the real simulation engine to produce a consistent snapshot."""

    def build(self, config: BuildConfig) -> SimulationSnapshot:
        """Build a simulation snapshot by replaying from earliest acquisition to start_date."""
        coa, sim, bank, accounting_service = self._create_engine(config)
        self._replay(config, sim, bank, accounting_service)
        balances = self._extract_balances(coa)
        return SimulationSnapshot(
            name=config.name,
            start_date=config.start_date,
            instruments=config.instruments,
            positions=config.positions,
            balances=balances,
            market_frames=config.market_frames,
        )

    @staticmethod
    def _create_engine(
        config: BuildConfig,
    ) -> tuple[BankChartOfAccounts, SimulationService, Bank, AccountingService]:
        """Instantiate and wire the full simulation engine."""
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
        from brms.core.services.rule_engine import RuleEngine
        from brms.core.services.simulation_service import SimulationService
        from brms.core.services.valuation_service import ValuationService
        from brms.core.services.valuation_strategies import default_valuation_strategies
        from brms.core.stores.instrument_store import InstrumentStore
        from brms.core.stores.metric_store import MetricStore
        from brms.core.stores.position_store import PositionStore
        from brms.core.stores.transaction_log import TransactionLog
        from brms.core.stores.valuation_store import ValuationStore

        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa, journal=Journal())
        bank = Bank(name=config.name, instruments=InstrumentStore(), positions=PositionStore(), ledger=ledger)
        market_data = MarketDataStore()
        accounting_service = AccountingService()

        for name, df in config.market_frames.items():
            market_data.add_frame(name, df)

        sim = SimulationService(
            bank=bank,
            market_data=market_data,
            valuation_service=ValuationService(default_valuation_strategies()),
            rule_engine=RuleEngine(default_rules()),
            accounting_service=accounting_service,
            metrics_service=MetricsService(MetricRegistry(default_metrics())),
            valuation_store=ValuationStore(),
            metric_store=MetricStore(),
            transaction_log=TransactionLog(),
            event_bus=EventBus(),
        )
        return coa, sim, bank, accounting_service

    def _replay(
        self,
        config: BuildConfig,
        sim: SimulationService,
        bank: Bank,
        accounting_service: AccountingService,
    ) -> None:
        """Walk calendar days from earliest acquisition to start_date.

        Positions are added (with acquisition transactions) on their acquisition date,
        up to and including start_date. The advance() loop runs only up to start_date - 1
        (exclusive) so the first user-visible advance at start_date is not double-counted.
        """
        positions_by_date = self._group_by_date(config)
        earliest = config.start_date if not config.positions else min(p.acquisition_date for p in config.positions)

        has_prior_advance = False
        current = earliest
        while current <= config.start_date:
            if current in positions_by_date:
                self._add_positions(
                    positions_by_date[current], sim, bank, accounting_service,
                    has_prior_advance=has_prior_advance,
                )
            if current < config.start_date:
                sim.advance(current)
                has_prior_advance = True
            current += datetime.timedelta(days=1)

    @staticmethod
    def _group_by_date(config: BuildConfig) -> dict[datetime.date, list[tuple[Instrument, Position]]]:
        """Sort positions by acquisition date and group them."""
        inst_lookup = {inst.id: inst for inst in config.instruments}
        result: dict[datetime.date, list[tuple[Instrument, Position]]] = {}
        for pos in sorted(config.positions, key=lambda p: p.acquisition_date):
            bucket = result.setdefault(pos.acquisition_date, [])
            bucket.append((inst_lookup[pos.instrument_id], pos))
        return result

    def _add_positions(
        self,
        entries: list[tuple[Instrument, Position]],
        sim: SimulationService,
        bank: Bank,
        accounting_service: AccountingService,
        *,
        has_prior_advance: bool,
    ) -> None:
        """Add positions to the bank and post their acquisition transactions."""
        for inst, pos in entries:
            bank.instruments.add(inst)
            bank.positions.add(pos)
            txns = self._make_acquisition_transactions(inst, pos, has_prior_advance=has_prior_advance)
            accounting_service.post_all(txns, bank.ledger, bank.positions)
            sim.transaction_log.record_batch(txns)

    @staticmethod
    def _extract_balances(coa: BankChartOfAccounts) -> dict[str, float]:
        """Return non-zero non-temporary account balances from the chart of accounts.

        Excludes composite accounts (which aggregate children) and temporary accounts.
        Only leaf accounts with non-zero balances are included.
        """
        from brms.core.models.accounting.accounts import CompositeTAccount

        balances: dict[str, float] = {}
        for account in coa.all_accounts():
            if account.is_temporary_account:
                continue
            if isinstance(account, CompositeTAccount):
                continue
            bal = account.balance()
            if abs(bal) > _ZERO_THRESHOLD:
                balances[account.name] = bal
        return balances

    def _make_acquisition_transactions(
        self, inst: Instrument, pos: Position, *, has_prior_advance: bool,
    ) -> list[Transaction]:
        """Generate the acquisition transaction for a single position.

        For bond purchases, includes ``accrued_interest`` metadata so the
        accounting service can split the entry into a clean-price investment
        debit and an Accrued Interest Receivable debit.  See
        :meth:`_compute_accrued_interest_at_acquisition` for details.
        """
        inst_type = getattr(inst, "instrument_type", None)
        basis = pos.measurement_basis

        if inst_type == InstrumentType.COMMON_EQUITY:
            tx_type = TransactionType.EQUITY_ISSUANCE
            metadata: tuple[tuple[str, object], ...] = ()
        elif inst_type == InstrumentType.DEPOSIT:
            tx_type = TransactionType.DEPOSIT_RECEIVED
            metadata = ()
        elif basis == MeasurementBasis.AMORTIZED_COST and inst_type in _LOAN_TYPES:
            tx_type = TransactionType.LOAN_DISBURSEMENT
            metadata = ()
        else:
            tx_type = TransactionType.SECURITY_PURCHASE
            class_name = ""
            if basis == MeasurementBasis.AMORTIZED_COST:
                class_name = "HTM"
            elif basis == MeasurementBasis.FVOCI:
                class_name = "FVOCI"
            elif basis == MeasurementBasis.FVTPL:
                class_name = "FVTPL"
            metadata = (("measurement_basis", class_name),)

            accrued = self._compute_accrued_interest_at_acquisition(
                inst, pos, has_prior_advance=has_prior_advance,
            )
            if accrued > 0:
                metadata = (*metadata, ("accrued_interest", str(accrued)))

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

    @staticmethod
    def _compute_accrued_interest_at_acquisition(
        inst: Instrument, pos: Position, *, has_prior_advance: bool,
    ) -> Decimal:
        """Return pre-acquisition accrued interest to book at purchase.

        When a bond is bought between coupon dates, the buyer pays the seller
        for accrued interest since the last coupon (the "dirty price" includes
        this).  We split this out so the Accrued Interest Receivable account
        stays in sync with QuantLib's ``accruedAmount`` from day one.

        We use ``accruedAmount(acquisition_date - 1 day)`` because:

        * On the acquisition date, ``_add_positions`` posts the acquisition
          transaction **before** ``sim.advance()`` runs.
        * ``advance()`` then runs the ``InterestIncomeAccrualRule``, which
          computes: ``accruedAmount(today) - accruedAmount(previous_date)``.
        * ``previous_date`` equals the last advance date = acquisition_date - 1
          (since advance runs every calendar day).
        * So after both the acquisition entry and the first accrual, the
          Receivable balance equals:
          ``accruedAmount(acq-1) + [accruedAmount(acq) - accruedAmount(acq-1)]``
          = ``accruedAmount(acq)``, which is exactly what QuantLib tracks.

        **Edge case — no prior advance (bond is the earliest position):**

        When no ``advance()`` has run before the bond is added, the accrual
        rule sees ``previous_date = None`` and falls back to ``ai_prev = 0``.
        That means the first accrual posts the full ``accruedAmount(today)``
        — effectively booking all pre-acquisition accrual in one go.  If we
        *also* booked accrued interest at acquisition, the Receivable would
        be double-counted.  So we return 0 in this case and let the accrual
        rule handle it.
        """
        if not has_prior_advance:
            return Decimal("0")

        ql_inst = getattr(inst, "ql_instrument", None)
        if ql_inst is None or not hasattr(ql_inst, "accruedAmount"):
            return Decimal("0")

        from brms.core.utils import pydate_to_qldate

        face_value = getattr(inst, "face_value", None)
        scale = Decimal(str(face_value)) / Decimal("100") if face_value else Decimal("1")

        day_before = pos.acquisition_date - datetime.timedelta(days=1)
        try:
            raw = ql_inst.accruedAmount(pydate_to_qldate(day_before))
        except RuntimeError:
            return Decimal("0")

        return (Decimal(str(raw)) * scale).quantize(Decimal("0.01"))
