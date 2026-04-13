"""Tests for ZipLoader and DataService.load_and_initialize."""

from __future__ import annotations

import datetime
import json
import zipfile
from io import BytesIO
from unittest.mock import MagicMock

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
                "start_date": "2024-01-05",
            }),
        )
        zf.writestr(
            "instruments.json",
            json.dumps([{"id": "cash-1", "type": "cash"}]),
        )
        zf.writestr(
            "positions.json",
            json.dumps([
                {
                    "id": "pos-1",
                    "instrument_id": "cash-1",
                    "book_type": "BANKING",
                    "measurement_basis": "AMORTIZED_COST",
                    "side": "LONG",
                    "acquisition_date": "2024-01-01",
                    "acquisition_cost": 1000000,
                },
            ]),
        )
        zf.writestr(
            "balances.json",
            json.dumps({
                "snapshot_date": "2024-01-05",
                "balances": {
                    "Cash and Cash Equivalents": 950000.0,
                    "Deposits": 800000.0,
                    "Shareholders' Equity": 100000.0,
                    "Retained Earnings": 50000.0,
                },
            }),
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
        from brms.core.enums import BookType, MeasurementBasis, PositionSide

        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()
        pos = data.positions[0]

        assert pos.book_type == BookType.BANKING  # noqa: S101
        assert pos.measurement_basis == MeasurementBasis.AMORTIZED_COST  # noqa: S101
        assert pos.side == PositionSide.LONG  # noqa: S101

    def test_dates_parsed(self) -> None:  # noqa: D102
        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()

        assert data.start_date == datetime.date(2024, 1, 5)  # noqa: S101

    def test_market_frame_shape(self) -> None:  # noqa: D102
        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()

        yields_frame = data.market_frames["yields"]
        assert len(yields_frame) == 5  # noqa: PLR2004, S101
        assert list(yields_frame.columns) == ["1Y", "5Y"]  # noqa: S101

    def test_loads_balances_from_zip(self) -> None:  # noqa: D102
        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())
        data = loader.load()

        assert data.balances == {  # noqa: S101
            "Cash and Cash Equivalents": 950000.0,
            "Deposits": 800000.0,
            "Shareholders' Equity": 100000.0,
            "Retained Earnings": 50000.0,
        }


class TestDataServiceLoadAndInitialize:
    """Tests for DataService.load_and_initialize."""

    def test_populates_stores(self) -> None:
        """DataService adds instruments, positions, and market data to stores."""
        from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
        from brms.core.models.accounting.journal import Journal
        from brms.core.models.accounting.ledger import Ledger
        from brms.core.services.data_service import DataService

        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa, journal=Journal())

        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())

        sim = MagicMock()
        sim.bank.instruments = MagicMock()
        sim.bank.positions = MagicMock()
        sim.bank.ledger = ledger
        sim.market_data = MagicMock()

        ds = DataService()
        ds.load_and_initialize(loader, sim)

        sim.bank.instruments.add.assert_called_once()
        sim.bank.positions.add.assert_called_once()
        sim.market_data.add_frame.assert_called_once()
        assert sim.market_data.add_frame.call_args[0][0] == "yields"  # noqa: S101

    def test_posts_opening_balance_entry(self) -> None:
        """DataService posts a CompoundEntry when balances are provided."""
        from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
        from brms.core.models.accounting.journal import Journal
        from brms.core.models.accounting.ledger import Ledger
        from brms.core.services.data_service import DataService

        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa, journal=Journal())

        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())

        sim = MagicMock()
        sim.bank.instruments = MagicMock()
        sim.bank.positions = MagicMock()
        sim.bank.ledger = ledger
        sim.market_data = MagicMock()

        ds = DataService()
        ds.load_and_initialize(loader, sim)

        assert abs(coa.cash_account.balance() - 950000.0) < 1e-6  # noqa: S101, PLR2004
        assert abs(coa.customer_deposits_account.balance() - 800000.0) < 1e-6  # noqa: S101, PLR2004
        assert abs(coa.equity_account.balance() - 100000.0) < 1e-6  # noqa: S101, PLR2004
        assert abs(coa.opening_balance_equity.balance()) < 1e-6  # noqa: S101

    def test_calls_initialize_from_snapshot(self) -> None:
        """DataService calls initialize_from_snapshot with start_date."""
        from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
        from brms.core.models.accounting.journal import Journal
        from brms.core.models.accounting.ledger import Ledger
        from brms.core.services.data_service import DataService

        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa, journal=Journal())

        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())

        sim = MagicMock()
        sim.bank.ledger = ledger
        sim.market_data = MagicMock()

        ds = DataService()
        ds.load_and_initialize(loader, sim)

        sim.initialize_from_snapshot.assert_called_once_with(datetime.date(2024, 1, 5))

    def test_no_advance_called(self) -> None:
        """DataService does not call advance() — snapshot provides ledger state."""
        from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
        from brms.core.models.accounting.journal import Journal
        from brms.core.models.accounting.ledger import Ledger
        from brms.core.services.data_service import DataService

        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa, journal=Journal())

        loader = ZipLoader(buffer=_make_zip(), instrument_registry=_make_registry())

        sim = MagicMock()
        sim.bank.ledger = ledger
        sim.market_data = MagicMock()

        ds = DataService()
        ds.load_and_initialize(loader, sim)

        sim.advance.assert_not_called()
