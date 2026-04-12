"""DataService: loads a simulation from a zip archive."""

from __future__ import annotations

import datetime
import re
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentType, MeasurementBasis, TransactionType
from brms.core.models.instruments.base import BookType, CreditRating, Issuer, IssuerType
from brms.core.models.instruments.registry import InstrumentRegistry
from brms.core.models.transaction import Transaction

if TYPE_CHECKING:
    from brms.core.services.loaders import Loader, SimulationData
    from brms.core.services.simulation_service import SimulationService

_PERIOD_RE = re.compile(r"^(\d+)\s*(Y|M|W|D)$", re.IGNORECASE)

_PERIOD_UNIT_MAP: dict[str, int] = {
    "Y": ql.Years,
    "M": ql.Months,
    "W": ql.Weeks,
    "D": ql.Days,
}

def _convert_kwargs(kwargs: dict[str, object]) -> dict[str, object]:
    """Convert JSON-friendly values to QuantLib types expected by instrument constructors.

    * Fields ending with ``_date``: ISO date string -> ``ql.Date``.
    * Fields ``maturity``, ``frequency``: period string like ``"30Y"`` or ``"1M"``.
      ``maturity`` becomes ``ql.Period``; ``frequency`` becomes a QL ``Frequency``
      int (e.g. ``ql.Monthly``) via ``.frequency()``.
    * Field ``measurement_basis``: string -> ``MeasurementBasis`` enum.
    * Field ``book_type``: string -> ``BookType`` enum.
    * Field ``credit_rating``: string -> ``CreditRating`` enum.
    * Field ``issuer``: dict -> ``Issuer`` object.
    """
    for key, value in list(kwargs.items()):
        if isinstance(value, str) and key.endswith("_date"):
            d = datetime.date.fromisoformat(value)
            kwargs[key] = ql.Date(d.day, d.month, d.year)

        elif key in {"maturity", "frequency"} and isinstance(value, str):
            m = _PERIOD_RE.match(value)
            if m:
                period = ql.Period(int(m.group(1)), _PERIOD_UNIT_MAP[m.group(2).upper()])
                kwargs[key] = period.frequency() if key == "frequency" else period

        elif key == "measurement_basis" and isinstance(value, str):
            kwargs[key] = MeasurementBasis[value]

        elif key == "book_type" and isinstance(value, str):
            kwargs[key] = BookType(value)

        elif key == "credit_rating" and isinstance(value, str):
            kwargs[key] = CreditRating[value]

        elif key == "issuer" and isinstance(value, dict):
            issuer_type = IssuerType[value["issuer_type"]]
            cr = CreditRating[value["credit_rating"]] if "credit_rating" in value else None
            kwargs[key] = Issuer(name=value["name"], issuer_type=issuer_type, credit_rating=cr)

    return kwargs


class DataService:
    """Loads simulation state (Bank + MarketDataStore) from a zip archive."""

    def __init__(self, instrument_registry: InstrumentRegistry | None = None) -> None:
        """Initialise the service with an optional instrument registry."""
        self._instrument_registry = instrument_registry or InstrumentRegistry()

    def load_and_initialize(self, loader: Loader, simulation_service: SimulationService) -> None:
        """Populate stores from *loader* and establish initial ledger state.

        If the loaded data includes balance snapshots (new format), posts a single
        Opening Balance journal entry. Otherwise falls back to the legacy
        acquisition-transaction + replay approach for old zips.
        """
        data = loader.load()  # type: ignore[union-attr]

        # 1. Populate stores
        for inst in data.instruments:
            simulation_service.bank.instruments.add(inst)  # type: ignore[union-attr]
        for pos in data.positions:
            simulation_service.bank.positions.add(pos)  # type: ignore[union-attr]
        for name, df in data.market_frames.items():
            simulation_service.market_data.add_frame(name, df)  # type: ignore[union-attr]

        if data.balances:
            # New path: post Opening Balance journal entry
            self._post_opening_balances(data, simulation_service)
        else:
            # Legacy path: acquisition transactions + replay
            self._post_acquisition_transactions(data, simulation_service)
            if data.replay_from is not None:
                current = data.replay_from
                while current < data.start_date:
                    simulation_service.advance(current)  # type: ignore[union-attr]
                    current += datetime.timedelta(days=1)

        # Record the configured start date
        simulation_service.start_date = data.start_date  # type: ignore[union-attr]

    @staticmethod
    def _post_opening_balances(data: SimulationData, simulation_service: SimulationService) -> None:
        """Post a compound Opening Balance journal entry from snapshot balances."""
        from brms.core.models.accounting.accounts import AccountNormalBalance
        from brms.core.models.accounting.journal import CompoundEntry

        ledger = simulation_service.bank.ledger
        coa = ledger.chart_of_accounts

        # Build account name -> account lookup from the full chart
        account_lookup: dict[str, object] = {}
        for account in coa.all_accounts():
            account_lookup[account.name] = account

        obe = account_lookup.get("Opening Balance Equity")
        if obe is None:
            msg = "Opening Balance Equity account not found in chart of accounts"
            raise ValueError(msg)

        debit_accounts: dict = {}
        credit_accounts: dict = {}

        for account_name, balance in data.balances.items():
            account = account_lookup.get(account_name)
            if account is None:
                msg = f"Account '{account_name}' not found in chart of accounts"
                raise ValueError(msg)
            if balance == 0:
                continue

            if account.normal_balance == AccountNormalBalance.DEBIT_NORMAL:
                debit_accounts[account] = balance
                credit_accounts[obe] = credit_accounts.get(obe, 0) + balance
            else:
                credit_accounts[account] = balance
                debit_accounts[obe] = debit_accounts.get(obe, 0) + balance

        if debit_accounts and credit_accounts:
            entry = CompoundEntry(
                debit_accounts=debit_accounts,
                credit_accounts=credit_accounts,
                date=data.start_date,
                description="Opening Balance",
            )
            ledger.post(entry)

    @staticmethod
    def _post_acquisition_transactions(data: SimulationData, simulation_service: SimulationService) -> None:
        """Generate and post initial acquisition transactions for every loaded position."""
        transactions: list[Transaction] = []
        for pos in data.positions:  # type: ignore[union-attr]
            inst = simulation_service.bank.instruments.get(pos.instrument_id)  # type: ignore[union-attr]
            inst_type = getattr(inst, "instrument_type", None)
            basis = pos.measurement_basis

            if inst_type == InstrumentType.COMMON_EQUITY:
                tx_type = TransactionType.EQUITY_ISSUANCE
                metadata: tuple[tuple[str, object], ...] = ()
            elif inst_type == InstrumentType.DEPOSIT:
                tx_type = TransactionType.DEPOSIT_RECEIVED
                metadata = ()
            elif basis == MeasurementBasis.AMORTIZED_COST and inst_type in {
                InstrumentType.RESIDENTIAL_MORTGAGE,
                InstrumentType.COMMERCIAL_MORTGAGE,
                InstrumentType.MORTGAGE,
                InstrumentType.AMORTIZING_FIXED_RATE_LOAN,
                InstrumentType.PERSONAL_LOAN,
            }:
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

            desc = tx_type.name.replace("_", " ").title()

            transactions.append(
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
            )

        if transactions:
            simulation_service.accounting_service.post_all(  # type: ignore[union-attr]
                transactions,
                simulation_service.bank.ledger,  # type: ignore[union-attr]
                simulation_service.bank.positions,  # type: ignore[union-attr]
            )
            simulation_service.transaction_log.record_batch(transactions)  # type: ignore[union-attr]
