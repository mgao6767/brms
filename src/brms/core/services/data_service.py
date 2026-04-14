"""DataService: loads a simulation from a zip archive."""

from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING

import QuantLib as ql  # noqa: N813

from brms.core.enums import MeasurementBasis
from brms.core.models.instruments.base import BookType, CreditRating, Issuer, IssuerType
from brms.core.models.instruments.registry import InstrumentRegistry

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
        """Populate stores from *loader* and post opening balances.

        The loaded zip must include ``balances.json`` with pre-computed ledger
        balances (produced by :class:`SimulationBuilder`).  A single Opening
        Balance journal entry is posted to establish the ledger state.
        """
        data = loader.load()  # type: ignore[union-attr]

        for inst in data.instruments:
            simulation_service.bank.instruments.add(inst)  # type: ignore[union-attr]
        for pos in data.positions:
            simulation_service.bank.positions.add(pos)  # type: ignore[union-attr]
        for name, df in data.market_frames.items():
            simulation_service.market_data.add_frame(name, df)  # type: ignore[union-attr]

        self._post_opening_balances(data, simulation_service)
        self._seed_valuations(data, simulation_service)
        simulation_service.initialize_from_snapshot(data.start_date, end_date=data.end_date)  # type: ignore[union-attr]

    @staticmethod
    def _post_opening_balances(data: SimulationData, simulation_service: SimulationService) -> None:
        """Post a compound Opening Balance journal entry from snapshot balances.

        Also records synthetic OPENING_BALANCE transactions in the transaction
        log so the transaction history widget can display the starting balances.
        """
        import uuid
        from decimal import Decimal

        from brms.core.enums import TransactionType
        from brms.core.models.accounting.accounts import AccountNormalBalance
        from brms.core.models.accounting.journal import CompoundEntry
        from brms.core.models.transaction import Transaction

        ledger = simulation_service.bank.ledger
        coa = ledger.chart_of_accounts
        snapshot_date = data.start_date - datetime.timedelta(days=1)

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
        opening_transactions: list[Transaction] = []

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

            opening_transactions.append(
                Transaction(
                    id=str(uuid.uuid4()),
                    type=TransactionType.OPENING_BALANCE,
                    date=snapshot_date,
                    amount=Decimal(str(balance)),
                    description=f"Opening balance: {account_name}",
                ),
            )

        if debit_accounts and credit_accounts:
            entry = CompoundEntry(
                debit_accounts=debit_accounts,
                credit_accounts=credit_accounts,
                date=data.start_date,
                description="Opening Balance",
            )
            ledger.post(entry)

        if opening_transactions:
            simulation_service.transaction_log.record_batch(opening_transactions)

    @staticmethod
    def _seed_valuations(data: SimulationData, simulation_service: SimulationService) -> None:
        """Seed the valuation store with per-position valuations from the snapshot.

        Valuations are recorded at ``start_date - 1`` (the snapshot date) so that
        the first advance computes the correct MTM delta against the replay state.
        """
        if not data.valuations:
            return

        from decimal import Decimal

        from brms.core.enums import ValuationType

        snapshot_date = data.start_date - datetime.timedelta(days=1)
        vs = simulation_service.valuation_store
        for pos_id, vals in data.valuations.items():
            if "fair_value" in vals:
                vs.record(pos_id, snapshot_date, ValuationType.FAIR_VALUE, Decimal(str(vals["fair_value"])))
            if "carrying_value" in vals:
                vs.record(pos_id, snapshot_date, ValuationType.CARRYING_VALUE, Decimal(str(vals["carrying_value"])))

