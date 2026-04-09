"""Tests for PositionStore."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from brms.core.enums import BookType, InstrumentClass, InstrumentType, PositionSide, PositionStatus
from brms.core.stores.position_store import PositionStore


@pytest.fixture
def store() -> PositionStore:
    """Return a fresh PositionStore."""
    return PositionStore()


def _make_position(  # noqa: PLR0913
    position_id: str,
    instrument_id: str = "inst-1",
    book_type: BookType = BookType.BANKING,
    side: PositionSide = PositionSide.LONG,
    status: PositionStatus = PositionStatus.OPEN,
    instrument_type: InstrumentType = InstrumentType.FIXED_RATE_BOND,
    instrument_class: InstrumentClass = InstrumentClass.HTM,
) -> MagicMock:
    pos = MagicMock()
    pos.id = position_id
    pos.instrument_id = instrument_id
    pos.book_type = book_type
    pos.side = side
    pos.status = status
    pos.instrument_type = instrument_type
    pos.instrument_class = instrument_class
    return pos


def test_add_and_get(store: PositionStore) -> None:
    """An added position is retrievable by id."""
    pos = _make_position("pos-1")
    store.add(pos)
    assert store.get("pos-1") is pos  # noqa: S101


def test_get_missing_raises_key_error(store: PositionStore) -> None:
    """get() raises KeyError for an unknown id."""
    with pytest.raises(KeyError):
        store.get("nonexistent")


def test_close_sets_status_closed(store: PositionStore) -> None:
    """close() sets position status to CLOSED."""
    pos = _make_position("pos-1")
    store.add(pos)
    store.close("pos-1")
    assert pos.status == PositionStatus.CLOSED  # noqa: S101


def test_close_missing_raises_key_error(store: PositionStore) -> None:
    """close() raises KeyError for an unknown id."""
    with pytest.raises(KeyError):
        store.close("nonexistent")


def test_by_book(store: PositionStore) -> None:
    """by_book() returns only positions in the specified book."""
    banking = _make_position("pos-1", book_type=BookType.BANKING)
    trading = _make_position("pos-2", book_type=BookType.TRADING)
    store.add(banking)
    store.add(trading)

    banking_positions = store.by_book(BookType.BANKING)
    assert banking in banking_positions  # noqa: S101
    assert trading not in banking_positions  # noqa: S101


def test_by_instrument(store: PositionStore) -> None:
    """by_instrument() returns only positions for the specified instrument."""
    pos1 = _make_position("pos-1", instrument_id="inst-A")
    pos2 = _make_position("pos-2", instrument_id="inst-A")
    pos3 = _make_position("pos-3", instrument_id="inst-B")
    store.add(pos1)
    store.add(pos2)
    store.add(pos3)

    result = store.by_instrument("inst-A")
    assert pos1 in result  # noqa: S101
    assert pos2 in result  # noqa: S101
    assert pos3 not in result  # noqa: S101


def test_by_side(store: PositionStore) -> None:
    """by_side() returns only positions with the specified side."""
    long_pos = _make_position("pos-1", side=PositionSide.LONG)
    short_pos = _make_position("pos-2", side=PositionSide.SHORT)
    store.add(long_pos)
    store.add(short_pos)

    longs = store.by_side(PositionSide.LONG)
    assert long_pos in longs  # noqa: S101
    assert short_pos not in longs  # noqa: S101


def test_by_status(store: PositionStore) -> None:
    """by_status() returns only positions with the specified status."""
    open_pos = _make_position("pos-1", status=PositionStatus.OPEN)
    closed_pos = _make_position("pos-2", status=PositionStatus.CLOSED)
    store.add(open_pos)
    store.add(closed_pos)

    open_positions = store.by_status(PositionStatus.OPEN)
    assert open_pos in open_positions  # noqa: S101
    assert closed_pos not in open_positions  # noqa: S101


def test_open_positions(store: PositionStore) -> None:
    """open_positions() returns only OPEN positions."""
    open_pos = _make_position("pos-1", status=PositionStatus.OPEN)
    closed_pos = _make_position("pos-2", status=PositionStatus.CLOSED)
    store.add(open_pos)
    store.add(closed_pos)

    result = store.open_positions()
    assert open_pos in result  # noqa: S101
    assert closed_pos not in result  # noqa: S101


def test_close_updates_open_positions(store: PositionStore) -> None:
    """A closed position no longer appears in open_positions()."""
    pos = _make_position("pos-1", status=PositionStatus.OPEN)
    store.add(pos)
    assert pos in store.open_positions()  # noqa: S101

    store.close("pos-1")
    assert pos not in store.open_positions()  # noqa: S101


def test_query_by_book_type(store: PositionStore) -> None:
    """query(book_type=...) filters by book type."""
    banking = _make_position("pos-1", book_type=BookType.BANKING)
    trading = _make_position("pos-2", book_type=BookType.TRADING)
    store.add(banking)
    store.add(trading)

    result = store.query(book_type=BookType.BANKING)
    assert banking in result  # noqa: S101
    assert trading not in result  # noqa: S101


def test_query_by_side(store: PositionStore) -> None:
    """query(side=...) filters by position side."""
    long_pos = _make_position("pos-1", side=PositionSide.LONG)
    short_pos = _make_position("pos-2", side=PositionSide.SHORT)
    store.add(long_pos)
    store.add(short_pos)

    result = store.query(side=PositionSide.LONG)
    assert long_pos in result  # noqa: S101
    assert short_pos not in result  # noqa: S101


def test_query_by_status(store: PositionStore) -> None:
    """query(status=...) filters by position status."""
    open_pos = _make_position("pos-1", status=PositionStatus.OPEN)
    closed_pos = _make_position("pos-2", status=PositionStatus.CLOSED)
    store.add(open_pos)
    store.add(closed_pos)

    result = store.query(status=PositionStatus.OPEN)
    assert open_pos in result  # noqa: S101
    assert closed_pos not in result  # noqa: S101


def test_query_by_instrument_class(store: PositionStore) -> None:
    """query(instrument_class=...) filters by accounting classification."""
    htm = _make_position("pos-1", instrument_class=InstrumentClass.HTM)
    fvtpl = _make_position("pos-2", instrument_class=InstrumentClass.FVTPL)
    store.add(htm)
    store.add(fvtpl)

    result = store.query(instrument_class=InstrumentClass.HTM)
    assert htm in result  # noqa: S101
    assert fvtpl not in result  # noqa: S101


def test_query_combined_filters(store: PositionStore) -> None:
    """query() with multiple filters applies all constraints simultaneously."""
    pos1 = _make_position(
        "pos-1",
        book_type=BookType.BANKING,
        side=PositionSide.LONG,
        status=PositionStatus.OPEN,
    )
    pos2 = _make_position(
        "pos-2",
        book_type=BookType.BANKING,
        side=PositionSide.SHORT,
        status=PositionStatus.OPEN,
    )
    pos3 = _make_position(
        "pos-3",
        book_type=BookType.TRADING,
        side=PositionSide.LONG,
        status=PositionStatus.OPEN,
    )
    store.add(pos1)
    store.add(pos2)
    store.add(pos3)

    result = store.query(book_type=BookType.BANKING, side=PositionSide.LONG)
    assert pos1 in result  # noqa: S101
    assert pos2 not in result  # noqa: S101
    assert pos3 not in result  # noqa: S101


def test_query_no_filters_returns_all(store: PositionStore) -> None:
    """query() with no filters returns all positions."""
    pos1 = _make_position("pos-1")
    pos2 = _make_position("pos-2")
    store.add(pos1)
    store.add(pos2)

    result = store.query()
    assert pos1 in result  # noqa: S101
    assert pos2 in result  # noqa: S101
