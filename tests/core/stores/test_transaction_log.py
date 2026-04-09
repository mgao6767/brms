"""Tests for TransactionLog."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from brms.core.enums import TransactionType
from brms.core.models.transaction import Transaction
from brms.core.stores.transaction_log import TransactionLog


@pytest.fixture
def log() -> TransactionLog:
    """Return a fresh TransactionLog."""
    return TransactionLog()


DATE_1 = datetime.date(2024, 1, 1)
DATE_2 = datetime.date(2024, 1, 2)


def _make_tx(
    tx_id: str,
    tx_type: TransactionType = TransactionType.INTEREST_PAYMENT,
    date: datetime.date = DATE_1,
    position_id: str | None = "pos-1",
    instrument_id: str | None = "inst-1",
) -> Transaction:
    return Transaction(
        id=tx_id,
        type=tx_type,
        date=date,
        amount=Decimal("100.00"),
        position_id=position_id,
        instrument_id=instrument_id,
    )


def test_record_and_all(log: TransactionLog) -> None:
    """A recorded transaction appears in all()."""
    tx = _make_tx("tx-1")
    log.record(tx)
    assert tx in log.all()  # noqa: S101


def test_all_returns_all_transactions(log: TransactionLog) -> None:
    """all() returns every recorded transaction."""
    tx1 = _make_tx("tx-1")
    tx2 = _make_tx("tx-2", date=DATE_2)
    log.record(tx1)
    log.record(tx2)
    result = log.all()
    assert len(result) == 2  # noqa: PLR2004, S101
    assert tx1 in result  # noqa: S101
    assert tx2 in result  # noqa: S101


def test_record_batch(log: TransactionLog) -> None:
    """record_batch() appends multiple transactions in order."""
    tx1 = _make_tx("tx-1")
    tx2 = _make_tx("tx-2")
    log.record_batch([tx1, tx2])
    result = log.all()
    assert tx1 in result  # noqa: S101
    assert tx2 in result  # noqa: S101


def test_by_instrument(log: TransactionLog) -> None:
    """by_instrument() returns only transactions for the specified instrument."""
    tx1 = _make_tx("tx-1", instrument_id="inst-A")
    tx2 = _make_tx("tx-2", instrument_id="inst-A")
    tx3 = _make_tx("tx-3", instrument_id="inst-B")
    log.record_batch([tx1, tx2, tx3])

    result = log.by_instrument("inst-A")
    assert tx1 in result  # noqa: S101
    assert tx2 in result  # noqa: S101
    assert tx3 not in result  # noqa: S101


def test_by_instrument_no_matches_returns_empty(log: TransactionLog) -> None:
    """by_instrument() returns an empty list when no transactions match."""
    tx = _make_tx("tx-1", instrument_id="inst-A")
    log.record(tx)
    assert log.by_instrument("inst-unknown") == []  # noqa: S101


def test_by_position(log: TransactionLog) -> None:
    """by_position() returns only transactions for the specified position."""
    tx1 = _make_tx("tx-1", position_id="pos-A")
    tx2 = _make_tx("tx-2", position_id="pos-A")
    tx3 = _make_tx("tx-3", position_id="pos-B")
    log.record_batch([tx1, tx2, tx3])

    result = log.by_position("pos-A")
    assert tx1 in result  # noqa: S101
    assert tx2 in result  # noqa: S101
    assert tx3 not in result  # noqa: S101


def test_by_position_none_not_included(log: TransactionLog) -> None:
    """Transactions with position_id=None do not appear in any by_position() result."""
    tx = _make_tx("tx-1", position_id=None)
    log.record(tx)
    assert log.by_position("pos-X") == []  # noqa: S101


def test_by_date(log: TransactionLog) -> None:
    """by_date() returns only transactions on the specified date."""
    tx1 = _make_tx("tx-1", date=DATE_1)
    tx2 = _make_tx("tx-2", date=DATE_1)
    tx3 = _make_tx("tx-3", date=DATE_2)
    log.record_batch([tx1, tx2, tx3])

    result = log.by_date(DATE_1)
    assert tx1 in result  # noqa: S101
    assert tx2 in result  # noqa: S101
    assert tx3 not in result  # noqa: S101


def test_by_type(log: TransactionLog) -> None:
    """by_type() returns only transactions of the specified type."""
    tx1 = _make_tx("tx-1", tx_type=TransactionType.INTEREST_PAYMENT)
    tx2 = _make_tx("tx-2", tx_type=TransactionType.INTEREST_PAYMENT)
    tx3 = _make_tx("tx-3", tx_type=TransactionType.MARK_TO_MARKET)
    log.record_batch([tx1, tx2, tx3])

    result = log.by_type(TransactionType.INTEREST_PAYMENT)
    assert tx1 in result  # noqa: S101
    assert tx2 in result  # noqa: S101
    assert tx3 not in result  # noqa: S101


def test_all_returns_empty_when_no_transactions(log: TransactionLog) -> None:
    """all() returns an empty list before any transactions are recorded."""
    assert log.all() == []  # noqa: S101


def test_append_only_ordering(log: TransactionLog) -> None:
    """all() returns transactions in insertion order."""
    tx1 = _make_tx("tx-1")
    tx2 = _make_tx("tx-2")
    tx3 = _make_tx("tx-3")
    log.record(tx1)
    log.record(tx2)
    log.record(tx3)

    result = log.all()
    assert result[0] is tx1  # noqa: S101
    assert result[1] is tx2  # noqa: S101
    assert result[2] is tx3  # noqa: S101
