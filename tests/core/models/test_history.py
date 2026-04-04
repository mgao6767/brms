"""Tests for SimulationHistory and DayRecord stack."""

# ruff: noqa: S101

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from brms.core.models.history import DayRecord, InstrumentChange, SimulationHistory
from brms.core.models.transaction import Transaction, TransactionType

_TX_AMOUNT = Decimal("100")
_EXPECTED_SERIES_LEN = 2


def _tx(tx_id: str, date: datetime.date) -> Transaction:
    return Transaction(id=tx_id, type=TransactionType.INTEREST_PAYMENT, date=date, amount=_TX_AMOUNT)


def _day(date: datetime.date) -> DayRecord:
    market_state = MagicMock()
    market_state.date = date
    return DayRecord(date=date, market_state=market_state)


def test_push_and_current_day() -> None:
    """push_day stores the record and current_day returns it."""
    h = SimulationHistory()
    assert h.current_day is None
    d = _day(datetime.date(2024, 1, 1))
    h.push_day(d)
    assert h.current_day is d


def test_pop_day() -> None:
    """pop_day removes the most recent record and restores the previous one."""
    h = SimulationHistory()
    d1 = _day(datetime.date(2024, 1, 1))
    d2 = _day(datetime.date(2024, 1, 2))
    h.push_day(d1)
    h.push_day(d2)
    popped = h.pop_day()
    assert popped is d2
    assert h.current_day is d1


def test_dates_property() -> None:
    """Dates returns an ordered list of all recorded dates."""
    h = SimulationHistory()
    h.push_day(_day(datetime.date(2024, 1, 1)))
    h.push_day(_day(datetime.date(2024, 1, 2)))
    assert h.dates == [datetime.date(2024, 1, 1), datetime.date(2024, 1, 2)]


def test_get_series() -> None:
    """get_series returns (date, value) tuples for a named metric across all days."""
    h = SimulationHistory()
    d1 = _day(datetime.date(2024, 1, 1))
    d1.metrics = {"total_assets": 1000}
    d2 = _day(datetime.date(2024, 1, 2))
    d2.metrics = {"total_assets": 1100}
    h.push_day(d1)
    h.push_day(d2)
    series = h.get_series("total_assets")
    assert series == [(datetime.date(2024, 1, 1), 1000), (datetime.date(2024, 1, 2), 1100)]


def test_get_series_with_date_range() -> None:
    """get_series respects start/end filters, returning only matching days."""
    h = SimulationHistory()
    for i in range(1, 4):
        d = _day(datetime.date(2024, 1, i))
        d.metrics = {"x": i * 10}
        h.push_day(d)
    series = h.get_series("x", start=datetime.date(2024, 1, 2))
    assert len(series) == _EXPECTED_SERIES_LEN
    assert series[0] == (datetime.date(2024, 1, 2), 20)


def test_get_transactions() -> None:
    """get_transactions aggregates transactions from all days."""
    h = SimulationHistory()
    d = _day(datetime.date(2024, 1, 1))
    tx = _tx("tx-1", datetime.date(2024, 1, 1))
    d.transactions.append(tx)
    h.push_day(d)
    txs = h.get_transactions()
    assert txs == [tx]


def test_get_snapshot() -> None:
    """get_snapshot returns the metrics dict for the given date, or None."""
    h = SimulationHistory()
    d = _day(datetime.date(2024, 1, 1))
    d.metrics = {"total_assets": 5000}
    h.push_day(d)
    snap = h.get_snapshot(datetime.date(2024, 1, 1))
    assert snap == {"total_assets": 5000}
    assert h.get_snapshot(datetime.date(2099, 1, 1)) is None


def test_day_record_instrument_changes() -> None:
    """InstrumentChange entries are stored on the DayRecord."""
    d = _day(datetime.date(2024, 1, 1))
    mock_instrument = MagicMock()
    change = InstrumentChange(instrument=mock_instrument, book_type="banking", action="added")
    d.instrument_changes.append(change)
    assert len(d.instrument_changes) == 1
