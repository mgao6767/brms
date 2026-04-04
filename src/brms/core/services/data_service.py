"""DataService: loads a simulation from a zip archive."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd

from brms.core.exceptions import DataLoadError
from brms.core.models.bank import Bank
from brms.core.models.books import BankingBook, TradingBook
from brms.core.models.instruments.registry import InstrumentRegistry
from brms.core.models.market_data import MarketDataStore


class DataService:
    """Loads simulation state (Bank + MarketDataStore) from a zip archive."""

    def __init__(self, instrument_registry: InstrumentRegistry | None = None) -> None:
        """Initialise the service with an optional instrument registry."""
        self._instrument_registry = instrument_registry or InstrumentRegistry()

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
        bank_data = json.loads(zf.read("bank.json"))
        banking_book = BankingBook()
        for item in bank_data.get("banking_book", []):
            item = dict(item)  # noqa: PLW2901
            type_id = item.pop("type")
            inst = self._instrument_registry.create(type_id, **item)
            banking_book.add(inst)
        trading_book = TradingBook()
        for item in bank_data.get("trading_book", []):
            item = dict(item)  # noqa: PLW2901
            type_id = item.pop("type")
            inst = self._instrument_registry.create(type_id, **item)
            trading_book.add(inst)
        # ledger is wired separately by the simulation layer
        return Bank(name=bank_data["name"], banking_book=banking_book, trading_book=trading_book, ledger=None)

    def _load_market_data(self, zf: zipfile.ZipFile) -> MarketDataStore:
        store = MarketDataStore()
        for name in zf.namelist():
            if name.endswith(".csv"):
                frame_name = Path(name).stem
                frame = pd.read_csv(BytesIO(zf.read(name)), index_col="date", parse_dates=True)
                store.add_frame(frame_name, frame)
        return store
