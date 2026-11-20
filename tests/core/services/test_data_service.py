"""Tests for DataService zip loading."""

from __future__ import annotations

from pathlib import Path

from brms.core.models.instruments.bonds import TreasuryNote
from brms.core.models.instruments.deposits import Cash, Deposit
from brms.core.models.instruments.equity import CommonEquity
from brms.core.models.instruments.loans import ResidentialMortgage
from brms.core.models.instruments.registry import InstrumentRegistry

# Minimal bank: equity, deposit, HTM bond
EXPECTED_TOTAL_INSTRUMENT_COUNT = 3


def _full_registry() -> InstrumentRegistry:
    """Build a registry with the types used in the default simulation zip."""
    registry = InstrumentRegistry()
    registry.register("cash", Cash)
    registry.register("deposit", Deposit)
    registry.register("common_equity", CommonEquity)
    registry.register("treasury_note", TreasuryNote)
    registry.register("residential_mortgage", ResidentialMortgage)
    return registry


def test_load_htm_treasury_zip() -> None:
    """ZipLoader can load htm_treasury.zip with QuantLib instruments."""
    from brms.core.services.loaders import ZipLoader

    zip_path = Path(__file__).resolve().parents[3] / "src" / "brms" / "data" / "htm_treasury.zip"
    loader = ZipLoader(path=zip_path, instrument_registry=_full_registry())
    data = loader.load()

    assert data.name == "HTM Treasury Bank"  # noqa: S101
    assert len(data.instruments) == EXPECTED_TOTAL_INSTRUMENT_COUNT  # noqa: S101
    assert len(data.balances) > 0  # noqa: S101


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
    from brms.core.enums import MeasurementBasis
    from brms.core.models.instruments.base import BookType
    from brms.core.services.data_service import _convert_kwargs

    kwargs: dict[str, object] = {"measurement_basis": "AMORTIZED_COST", "book_type": "trading"}
    _convert_kwargs(kwargs)

    assert kwargs["measurement_basis"] == MeasurementBasis.AMORTIZED_COST  # noqa: S101
    assert kwargs["book_type"] == BookType.TRADING  # noqa: S101
