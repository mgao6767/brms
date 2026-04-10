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
    * Field ``maturity``: period string like ``"30Y"`` -> ``ql.Period``.
    * Field ``measurement_basis``: string -> ``MeasurementBasis`` enum.
    * Field ``book_type``: string -> ``BookType`` enum.
    * Field ``credit_rating``: string -> ``CreditRating`` enum.
    * Field ``issuer``: dict -> ``Issuer`` object.
    """
    for key, value in list(kwargs.items()):
        if isinstance(value, str) and key.endswith("_date"):
            d = datetime.date.fromisoformat(value)
            kwargs[key] = ql.Date(d.day, d.month, d.year)

        elif key == "maturity" and isinstance(value, str):
            m = _PERIOD_RE.match(value)
            if m:
                kwargs[key] = ql.Period(int(m.group(1)), _PERIOD_UNIT_MAP[m.group(2).upper()])

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
        """Populate stores from *loader* and replay advance() to derive initial state.

        Args:
            loader: Any object implementing the ``Loader`` protocol (must have a ``load()`` method
                returning :class:`~brms.core.services.loaders.SimulationData`).
            simulation_service: The simulation service whose bank stores and market data will be
                populated, and whose ``advance()`` method will be called for replay dates.

        """
        data = loader.load()  # type: ignore[union-attr]

        # 1. Populate stores
        for inst in data.instruments:
            simulation_service.bank.instruments.add(inst)  # type: ignore[union-attr]
        for pos in data.positions:
            simulation_service.bank.positions.add(pos)  # type: ignore[union-attr]
        for name, df in data.market_frames.items():
            simulation_service.market_data.add_frame(name, df)  # type: ignore[union-attr]

        # 2. Post acquisition transactions to establish initial ledger balances
        self._post_acquisition_transactions(data, simulation_service)

        # 3. Replay advance() from replay_from to start_date (calendar-day)
        current = data.replay_from
        while current < data.start_date:
            simulation_service.advance(current)  # type: ignore[union-attr]
            current += datetime.timedelta(days=1)

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
