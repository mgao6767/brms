"""Tests for ZipLoader and DataService.load_and_initialize."""

from __future__ import annotations

import datetime
import json
import zipfile
from io import BytesIO
from unittest.mock import MagicMock, call

from brms.core.models.instruments.deposits import Cash
from brms.core.models.instruments.registry import InstrumentRegistry
from brms.core.services.loaders import SimulationData, ZipLoader


def _make_zip() -> BytesIO:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "config.json",
            json.dumps({
                "name": "Test Bank",
                "replay_from": "2024-01-01",
                "start_date": "2024-01-05",
            }),
        )
        zf.writestr(
            "instruments.json",
            json.dumps([
                {"id": "cash-1", "type": "cash"},
            ]),
        )
        zf.writestr(
            "positions.json",
            json.dumps([
                {
                    "id": "pos-1",
                    "instrument_id": "cash-1",
                    "book_type": "BANKING",
                    "instrument_class": "HTM",
                    "side": "LONG",
                    "acquisition_date": "2024-01-01",
                    "acquisition_cost": 1000000,
                },
            ]),
        )
        zf.writestr(
            "yields.csv",
            "date,1Y,5Y\n" + "\n".join(f"2024-01-{i:02d},0.04,0.045" for i in range(1, 6)),
        )
    buf.seek(0)
    return buf


def _make_registry() -> InstrumentRegistry:
    registry = InstrumentRegistry()
    registry.register("cash", Cash)
    return registry


class TestZipLoader:
    """Tests for ZipLoader."""

    def test_returns_simulation_data(self) -> None:  # noqa: D102
        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()

        assert isinstance(data, SimulationData)  # noqa: S101
        assert data.name == "Test Bank"  # noqa: S101
        assert len(data.instruments) == 1  # noqa: S101
        assert len(data.positions) == 1  # noqa: S101
        assert "yields" in data.market_frames  # noqa: S101

    def test_instrument_id_set_from_json(self) -> None:  # noqa: D102
        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()

        assert data.instruments[0].id == "cash-1"  # noqa: S101

    def test_position_enums_parsed(self) -> None:  # noqa: D102
        from brms.core.enums import BookType, InstrumentClass, PositionSide

        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()
        pos = data.positions[0]

        assert pos.book_type == BookType.BANKING  # noqa: S101
        assert pos.instrument_class == InstrumentClass.HTM  # noqa: S101
        assert pos.side == PositionSide.LONG  # noqa: S101

    def test_dates_parsed(self) -> None:  # noqa: D102
        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()

        assert data.replay_from == datetime.date(2024, 1, 1)  # noqa: S101
        assert data.start_date == datetime.date(2024, 1, 5)  # noqa: S101

    def test_market_frame_shape(self) -> None:  # noqa: D102
        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()

        yields_frame = data.market_frames["yields"]
        assert len(yields_frame) == 5  # noqa: PLR2004, S101
        assert list(yields_frame.columns) == ["1Y", "5Y"]  # noqa: S101


class TestDataServiceLoadAndInitialize:
    """Tests for DataService.load_and_initialize."""

    def test_populates_stores_and_replays(self) -> None:  # noqa: D102
        from brms.core.services.data_service import DataService

        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())

        sim = MagicMock()
        sim.market_data.available_dates.return_value = [
            datetime.date(2024, 1, 1),
            datetime.date(2024, 1, 2),
            datetime.date(2024, 1, 3),
            datetime.date(2024, 1, 4),
            datetime.date(2024, 1, 5),
        ]

        ds = DataService()
        ds.load_and_initialize(loader, sim)

        sim.bank.instruments.add.assert_called_once()
        sim.bank.positions.add.assert_called_once()

        sim.market_data.add_frame.assert_called_once()
        frame_call_args = sim.market_data.add_frame.call_args
        assert frame_call_args[0][0] == "yields"  # noqa: S101

    def test_replay_calls_advance_for_correct_dates(self) -> None:  # noqa: D102
        from brms.core.services.data_service import DataService

        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())

        sim = MagicMock()
        sim.market_data.available_dates.return_value = [
            datetime.date(2024, 1, 1),
            datetime.date(2024, 1, 2),
            datetime.date(2024, 1, 3),
            datetime.date(2024, 1, 4),
            datetime.date(2024, 1, 5),
        ]

        ds = DataService()
        ds.load_and_initialize(loader, sim)

        expected = [
            call(datetime.date(2024, 1, 1)),
            call(datetime.date(2024, 1, 2)),
            call(datetime.date(2024, 1, 3)),
            call(datetime.date(2024, 1, 4)),
        ]
        assert sim.advance.call_args_list == expected  # noqa: S101
