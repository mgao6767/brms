"""DataService: loads a simulation from a zip archive."""

from __future__ import annotations

import datetime
import json
import re
import uuid
import zipfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
import QuantLib as ql  # noqa: N813

from brms.core.enums import InstrumentClass as CoreInstrumentClass
from brms.core.enums import InstrumentType, TransactionType
from brms.core.exceptions import DataLoadError
from brms.core.models.bank import Bank
from brms.core.models.instruments.base import BookType, CreditRating, Instrument, InstrumentClass, Issuer, IssuerType
from brms.core.models.instruments.registry import InstrumentRegistry
from brms.core.models.market_data import MarketDataStore
from brms.core.models.transaction import Transaction

# ---------------------------------------------------------------------------
# Lightweight v1 book containers (inlined; books.py has been removed)
# ---------------------------------------------------------------------------


class BankingBook:
    """Holds instruments assigned to the banking book (v1 legacy container)."""

    book_type: BookType = BookType.BANKING

    def __init__(self) -> None:
        """Initialise an empty banking book."""
        self._instruments: list[Instrument] = []

    def add(self, instrument: Instrument) -> None:
        """Append *instrument* to the book."""
        self._instruments.append(instrument)

    def remove(self, instrument_id: str) -> None:
        """Remove the instrument with *instrument_id*; raise InstrumentNotFoundError if absent."""
        from brms.core.exceptions import InstrumentNotFoundError

        for i, inst in enumerate(self._instruments):
            if inst.id == instrument_id:
                self._instruments.pop(i)
                return
        raise InstrumentNotFoundError(instrument_id)

    def get_instrument_by_id(self, instrument_id: str) -> Instrument | None:
        """Return the instrument with *instrument_id*, or ``None`` if absent."""
        return next((i for i in self._instruments if i.id == instrument_id), None)

    def __iter__(self):  # noqa: ANN204
        """Iterate over instruments."""
        return iter(self._instruments)

    def __len__(self) -> int:
        """Return the number of instruments."""
        return len(self._instruments)


class TradingBook:
    """Holds instruments assigned to the trading book (v1 legacy container)."""

    book_type: BookType = BookType.TRADING

    def __init__(self) -> None:
        """Initialise an empty trading book."""
        self._instruments: list[Instrument] = []

    def add(self, instrument: Instrument) -> None:
        """Append *instrument* to the book."""
        self._instruments.append(instrument)

    def remove(self, instrument_id: str) -> None:
        """Remove the instrument with *instrument_id*; raise InstrumentNotFoundError if absent."""
        from brms.core.exceptions import InstrumentNotFoundError

        for i, inst in enumerate(self._instruments):
            if inst.id == instrument_id:
                self._instruments.pop(i)
                return
        raise InstrumentNotFoundError(instrument_id)

    def get_instrument_by_id(self, instrument_id: str) -> Instrument | None:
        """Return the instrument with *instrument_id*, or ``None`` if absent."""
        return next((i for i in self._instruments if i.id == instrument_id), None)

    def __iter__(self):  # noqa: ANN204
        """Iterate over instruments."""
        return iter(self._instruments)

    def __len__(self) -> int:
        """Return the number of instruments."""
        return len(self._instruments)

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
    * Field ``instrument_class``: string -> ``InstrumentClass`` enum.
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

        elif key == "instrument_class" and isinstance(value, str):
            kwargs[key] = InstrumentClass(value)

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

    def load_and_initialize(self, loader: object, simulation_service: object) -> None:
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

        # 3. Replay advance() from replay_from to start_date
        available = simulation_service.market_data.available_dates()  # type: ignore[union-attr]
        for date in available:
            if date < data.replay_from:
                continue
            if date >= data.start_date:
                break
            simulation_service.advance(date)  # type: ignore[union-attr]

    @staticmethod
    def _post_acquisition_transactions(data: object, simulation_service: object) -> None:
        """Generate and post initial acquisition transactions for every loaded position.

        Equity positions produce EQUITY_ISSUANCE, deposit positions produce DEPOSIT_RECEIVED,
        and bond/loan positions produce SECURITY_PURCHASE.
        """
        transactions: list[Transaction] = []
        for pos in data.positions:  # type: ignore[union-attr]
            inst = simulation_service.bank.instruments.get(pos.instrument_id)  # type: ignore[union-attr]
            inst_type = getattr(inst, "instrument_type", None)
            instrument_class = pos.instrument_class

            if inst_type == InstrumentType.COMMON_EQUITY:
                tx_type = TransactionType.EQUITY_ISSUANCE
                metadata: tuple[tuple[str, object], ...] = ()
            elif inst_type == InstrumentType.DEPOSIT:
                tx_type = TransactionType.DEPOSIT_RECEIVED
                metadata = ()
            elif instrument_class in {CoreInstrumentClass.LOAN_AND_MORTGAGE}:
                tx_type = TransactionType.LOAN_DISBURSEMENT
                metadata = ()
            else:
                tx_type = TransactionType.SECURITY_PURCHASE
                # Map instrument_class to account name used by AccountingService
                class_name = ""
                if instrument_class in {CoreInstrumentClass.HTM}:
                    class_name = "HTM"
                elif instrument_class in {CoreInstrumentClass.FVOCI}:
                    class_name = "FVOCI"
                elif instrument_class in {CoreInstrumentClass.FVTPL}:
                    class_name = "FVTPL"
                metadata = (("instrument_class", class_name),)

            transactions.append(
                Transaction(
                    id=str(uuid.uuid4()),
                    type=tx_type,
                    date=pos.acquisition_date,
                    amount=Decimal(str(pos.acquisition_cost)),
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

    def load_simulation(self, zip_path: Path) -> tuple[Bank, MarketDataStore]:
        """Load a simulation from the zip file at *zip_path*.

        Args:
            zip_path: Path to the zip archive on disk.

        Returns:
            A ``(Bank, MarketDataStore)`` tuple.

        Raises:
            DataLoadError: If the archive is missing required files or is malformed.

        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                return self._load_from_zip(zf)
        except (KeyError, json.JSONDecodeError, pd.errors.ParserError) as exc:
            msg = f"Failed to load simulation from {zip_path}: {exc}"
            raise DataLoadError(msg) from exc

    def load_simulation_from_buffer(self, buf: BytesIO) -> tuple[Bank, MarketDataStore]:
        """Load a simulation from an in-memory zip buffer.

        Args:
            buf: A ``BytesIO`` object containing zip-formatted data.

        Returns:
            A ``(Bank, MarketDataStore)`` tuple.

        Raises:
            DataLoadError: If the buffer is missing required files or is malformed.

        """
        try:
            with zipfile.ZipFile(buf, "r") as zf:
                return self._load_from_zip(zf)
        except (KeyError, json.JSONDecodeError, pd.errors.ParserError) as exc:
            msg = f"Failed to load simulation from buffer: {exc}"
            raise DataLoadError(msg) from exc

    def _load_from_zip(self, zf: zipfile.ZipFile) -> tuple[Bank, MarketDataStore]:
        bank = self._load_bank(zf)
        store = self._load_market_data(zf)
        return bank, store

    def _load_bank(self, zf: zipfile.ZipFile) -> Bank:
        from brms.core.stores.instrument_store import InstrumentStore
        from brms.core.stores.position_store import PositionStore

        bank_data = json.loads(zf.read("bank.json"))
        instrument_store = InstrumentStore()
        for book_key in ("banking_book", "trading_book"):
            for item in bank_data.get(book_key, []):
                item = dict(item)  # noqa: PLW2901
                type_id = item.pop("type")
                _convert_kwargs(item)
                item.pop("value", None)  # value is no longer an instrument field
                inst = self._instrument_registry.create(type_id, **item)
                instrument_store.add(inst)
        # ledger is wired separately by the simulation layer
        return Bank(name=bank_data["name"], instruments=instrument_store, positions=PositionStore(), ledger=None)

    def _load_market_data(self, zf: zipfile.ZipFile) -> MarketDataStore:
        store = MarketDataStore()
        for name in zf.namelist():
            if name.endswith(".csv"):
                frame_name = Path(name).stem
                frame = pd.read_csv(BytesIO(zf.read(name)), index_col="date", parse_dates=True)
                store.add_frame(frame_name, frame)
        return store
