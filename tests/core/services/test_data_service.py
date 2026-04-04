"""Tests for DataService zip loading."""

from __future__ import annotations

import datetime
import json
import zipfile
from io import BytesIO

from brms.core.models.bank import Bank
from brms.core.models.market_data import MarketDataStore
from brms.core.services.data_service import DataService

EXPECTED_DATE_COUNT = 2


def _create_test_zip() -> BytesIO:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        bank_data = {
            "name": "Test Bank",
            "as_of_date": "2024-01-01",
            "banking_book": [],
            "trading_book": [],
            "initial_accounts": {"cash": 5000000},
        }
        zf.writestr("bank.json", json.dumps(bank_data))
        zf.writestr("yields.csv", "date,1Y,5Y\n2024-01-01,0.04,0.045\n2024-01-02,0.041,0.046\n")
    buf.seek(0)
    return buf


def test_load_simulation_returns_bank_and_store() -> None:
    """load_simulation_from_buffer returns a Bank and a MarketDataStore."""
    service = DataService()
    bank, store = service.load_simulation_from_buffer(_create_test_zip())
    assert isinstance(bank, Bank)  # noqa: S101
    assert isinstance(store, MarketDataStore)  # noqa: S101


def test_loaded_bank_has_name() -> None:
    """Bank loaded from zip carries the name specified in bank.json."""
    service = DataService()
    bank, _ = service.load_simulation_from_buffer(_create_test_zip())
    assert bank.name == "Test Bank"  # noqa: S101


def test_loaded_store_has_dates() -> None:
    """MarketDataStore loaded from zip exposes dates from the CSV."""
    service = DataService()
    _, store = service.load_simulation_from_buffer(_create_test_zip())
    dates = store.available_dates()
    assert len(dates) == EXPECTED_DATE_COUNT  # noqa: S101
    assert datetime.date(2024, 1, 1) in dates  # noqa: S101


def test_load_zip_with_cash_instrument() -> None:
    """DataService can deserialise a Cash instrument via InstrumentRegistry."""
    import json
    import zipfile
    from io import BytesIO

    from brms.core.models.instruments.deposits import Cash
    from brms.core.models.instruments.registry import InstrumentRegistry
    from brms.core.services.data_service import DataService

    registry = InstrumentRegistry()
    registry.register("cash", Cash)

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "bank.json",
            json.dumps({
                "name": "Test",
                "as_of_date": "2024-01-01",
                "banking_book": [{"type": "cash", "value": 1000000}],
                "trading_book": [],
                "initial_accounts": {},
            }),
        )
        zf.writestr("yields.csv", "date,1Y\n2024-01-01,0.04\n")
    buf.seek(0)

    service = DataService(instrument_registry=registry)
    bank, _ = service.load_simulation_from_buffer(buf)
    instruments = list(bank.banking_book)
    assert len(instruments) == 1  # noqa: S101
    assert isinstance(instruments[0], Cash)  # noqa: S101
