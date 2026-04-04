"""Tests for DataService zip loading."""

from __future__ import annotations

import datetime
import json
import zipfile
from io import BytesIO
from pathlib import Path

from brms.core.models.bank import Bank
from brms.core.models.instruments.bonds import TreasuryNote
from brms.core.models.instruments.deposits import Cash, Deposit
from brms.core.models.instruments.equity import CommonEquity
from brms.core.models.instruments.loans import ResidentialMortgage
from brms.core.models.instruments.registry import InstrumentRegistry
from brms.core.models.market_data import MarketDataStore
from brms.core.services.data_service import DataService

EXPECTED_DATE_COUNT = 2

EXPECTED_BANKING_BOOK_COUNT = 18
EXPECTED_TRADING_BOOK_COUNT = 10


def _full_registry() -> InstrumentRegistry:
    """Build a registry with the types used in the default simulation zip."""
    registry = InstrumentRegistry()
    registry.register("cash", Cash)
    registry.register("deposit", Deposit)
    registry.register("common_equity", CommonEquity)
    registry.register("treasury_note", TreasuryNote)
    registry.register("residential_mortgage", ResidentialMortgage)
    return registry


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


def test_load_default_simulation_zip() -> None:
    """DataService can load the generated default_simulation.zip with QuantLib instruments."""
    zip_path = Path(__file__).resolve().parents[3] / "src" / "brms" / "data" / "default_simulation.zip"
    service = DataService(instrument_registry=_full_registry())
    bank, store = service.load_simulation(zip_path)

    assert bank.name == "Default Bank"  # noqa: S101
    assert len(store.available_dates()) > 0  # noqa: S101

    banking_instruments = list(bank.banking_book)
    trading_instruments = list(bank.trading_book)

    assert len(banking_instruments) == EXPECTED_BANKING_BOOK_COUNT  # noqa: S101
    assert len(trading_instruments) == EXPECTED_TRADING_BOOK_COUNT  # noqa: S101

    # Verify instrument types
    assert isinstance(banking_instruments[0], CommonEquity)  # noqa: S101
    assert isinstance(banking_instruments[1], Deposit)  # noqa: S101
    assert isinstance(banking_instruments[2], TreasuryNote)  # noqa: S101

    # Mortgages at indices 3-7
    for inst in banking_instruments[3:8]:
        assert isinstance(inst, ResidentialMortgage)  # noqa: S101

    # FVOCI treasury notes at indices 8-17 (10 notes)
    for inst in banking_instruments[8:]:
        assert isinstance(inst, TreasuryNote)  # noqa: S101

    # All trading book instruments are FVTPL treasury notes
    for inst in trading_instruments:
        assert isinstance(inst, TreasuryNote)  # noqa: S101


def test_convert_kwargs_handles_date_strings() -> None:
    """_convert_kwargs converts ISO date strings to ql.Date objects."""
    import QuantLib as ql  # noqa: N813

    from brms.core.services.data_service import _convert_kwargs

    kwargs: dict[str, object] = {"issue_date": "2020-01-15", "maturity_date": "2030-06-30"}
    _convert_kwargs(kwargs)

    assert isinstance(kwargs["issue_date"], ql.Date)  # noqa: S101
    assert isinstance(kwargs["maturity_date"], ql.Date)  # noqa: S101
    assert kwargs["issue_date"] == ql.Date(15, 1, 2020)  # noqa: S101
    assert kwargs["maturity_date"] == ql.Date(30, 6, 2030)  # noqa: S101


def test_convert_kwargs_handles_maturity_period() -> None:
    """_convert_kwargs converts period strings like '30Y' to ql.Period."""
    import QuantLib as ql  # noqa: N813

    from brms.core.services.data_service import _convert_kwargs

    kwargs: dict[str, object] = {"maturity": "30Y"}
    _convert_kwargs(kwargs)

    assert isinstance(kwargs["maturity"], ql.Period)  # noqa: S101
    assert kwargs["maturity"] == ql.Period(30, ql.Years)  # noqa: S101


def test_convert_kwargs_handles_enums() -> None:
    """_convert_kwargs converts string enum values to proper enum members."""
    from brms.core.models.instruments.base import BookType, InstrumentClass
    from brms.core.services.data_service import _convert_kwargs

    kwargs: dict[str, object] = {"instrument_class": "HTM", "book_type": "trading"}
    _convert_kwargs(kwargs)

    assert kwargs["instrument_class"] == InstrumentClass.HTM  # noqa: S101
    assert kwargs["book_type"] == BookType.TRADING  # noqa: S101
