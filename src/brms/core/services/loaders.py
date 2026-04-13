"""Loader protocol and ZipLoader for decoupled simulation data loading."""

from __future__ import annotations

import datetime
import json
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import pandas as pd

from brms.core.enums import BookType, MeasurementBasis, PositionSide
from brms.core.models.position import Position
from brms.core.services.data_service import _convert_kwargs

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.instruments.registry import InstrumentRegistry


@dataclass
class SimulationData:
    """Container for all data loaded by a loader."""

    name: str
    start_date: datetime.date
    instruments: list[Instrument]
    positions: list[Position]
    market_frames: dict[str, pd.DataFrame]
    balances: dict[str, float] = field(default_factory=dict)


@runtime_checkable
class Loader(Protocol):
    """Protocol for loading simulation data from any source."""

    def load(self) -> SimulationData:
        """Load and return simulation data."""
        ...


@dataclass
class ZipLoaderConfig:
    """Configuration for file names within a zip archive."""

    config_file: str = "config.json"
    instruments_file: str = "instruments.json"
    positions_file: str = "positions.json"
    market_data_mapping: dict[str, str] = field(default_factory=lambda: {"yields": "yields.csv"})


class ZipLoader:
    """Loads simulation data from a zip archive (file path or in-memory buffer)."""

    def __init__(
        self,
        *,
        path: Path | str | None = None,
        buffer: BytesIO | None = None,
        instrument_registry: InstrumentRegistry,
        config: ZipLoaderConfig | None = None,
    ) -> None:
        """Initialise with a file path or buffer and an instrument registry.

        Args:
            path: Path to a zip file on disk. Mutually exclusive with *buffer*.
            buffer: In-memory zip data. Mutually exclusive with *path*.
            instrument_registry: Registry used to construct instrument instances.
            config: Optional file-name configuration for the archive layout.

        """
        if path is None and buffer is None:
            msg = "Either 'path' or 'buffer' must be provided"
            raise ValueError(msg)
        self._path = Path(path) if path is not None else None
        self._buffer = buffer
        self._registry = instrument_registry
        self._config = config or ZipLoaderConfig()

    def load(self) -> SimulationData:
        """Read the zip archive and return a populated SimulationData."""
        source: Path | BytesIO = self._path if self._path is not None else self._buffer  # type: ignore[assignment]
        with zipfile.ZipFile(source, "r") as zf:
            return self._load_from_zip(zf)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_from_zip(self, zf: zipfile.ZipFile) -> SimulationData:
        cfg = json.loads(zf.read(self._config.config_file))
        instruments = self._load_instruments(zf)
        positions = self._load_positions(zf)
        market_frames = self._load_market_data(zf)

        balances: dict[str, float] = {}
        if "balances.json" in zf.namelist():
            bal_data = json.loads(zf.read("balances.json"))
            balances = bal_data.get("balances", {})

        return SimulationData(
            name=cfg["name"],
            start_date=datetime.date.fromisoformat(cfg["start_date"]),
            instruments=instruments,
            positions=positions,
            market_frames=market_frames,
            balances=balances,
        )

    def _load_instruments(self, zf: zipfile.ZipFile) -> list[Instrument]:
        raw = json.loads(zf.read(self._config.instruments_file))
        instruments: list[Instrument] = []
        for item in raw:
            item = dict(item)  # noqa: PLW2901
            type_id = item.pop("type")
            instrument_id = item.pop("id", None)
            instrument_name = item.pop("name", None)
            item.pop("value", None)  # v1 field not used by constructors
            _convert_kwargs(item)
            inst = self._registry.create(type_id, **item)
            if instrument_id is not None:
                inst.id = instrument_id
            if instrument_name is not None:
                inst.name = instrument_name
            instruments.append(inst)
        return instruments

    def _load_positions(self, zf: zipfile.ZipFile) -> list[Position]:
        raw = json.loads(zf.read(self._config.positions_file))
        return [
            Position(
                id=p["id"],
                instrument_id=p["instrument_id"],
                book_type=BookType[p["book_type"]],
                measurement_basis=MeasurementBasis[p["measurement_basis"]],
                side=PositionSide[p["side"]],
                acquisition_date=datetime.date.fromisoformat(p["acquisition_date"]),
                acquisition_cost=Decimal(str(p["acquisition_cost"])),
            )
            for p in raw
        ]

    def _load_market_data(self, zf: zipfile.ZipFile) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        for frame_name, filename in self._config.market_data_mapping.items():
            frames[frame_name] = pd.read_csv(BytesIO(zf.read(filename)), index_col="date", parse_dates=True)
        return frames
