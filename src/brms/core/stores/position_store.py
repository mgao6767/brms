"""PositionStore: in-memory store with indexed position access."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from brms.core.enums import PositionStatus

if TYPE_CHECKING:
    from brms.core.enums import BookType, InstrumentClass, InstrumentType, PositionSide
    from brms.core.models.position import Position


class PositionStore:
    """Maintains positions with pre-built indices for filtered access."""

    def __init__(self) -> None:
        """Initialize empty position store with secondary indices."""
        self._by_id: dict[str, Position] = {}
        self._by_book: dict[Any, set[str]] = defaultdict(set)
        self._by_instrument: dict[str, set[str]] = defaultdict(set)
        self._by_side: dict[Any, set[str]] = defaultdict(set)
        self._by_status: dict[Any, set[str]] = defaultdict(set)
        self._by_instrument_type: dict[Any, set[str]] = defaultdict(set)
        self._by_instrument_class: dict[Any, set[str]] = defaultdict(set)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _index(self, position: Position) -> None:
        """Add *position* to all secondary indices."""
        pid = position.id
        self._by_book[position.book_type].add(pid)
        self._by_instrument[position.instrument_id].add(pid)
        self._by_side[position.side].add(pid)
        self._by_status[position.status].add(pid)
        if hasattr(position, "instrument_type"):
            self._by_instrument_type[position.instrument_type].add(pid)
        if hasattr(position, "instrument_class"):
            self._by_instrument_class[position.instrument_class].add(pid)

    def _deindex(self, position: Position) -> None:
        """Remove *position* from all secondary indices."""
        pid = position.id
        self._by_book[position.book_type].discard(pid)
        self._by_instrument[position.instrument_id].discard(pid)
        self._by_side[position.side].discard(pid)
        self._by_status[position.status].discard(pid)
        if hasattr(position, "instrument_type"):
            self._by_instrument_type[position.instrument_type].discard(pid)
        if hasattr(position, "instrument_class"):
            self._by_instrument_class[position.instrument_class].discard(pid)

    def _ids_to_positions(self, ids: set[str]) -> list[Position]:
        """Resolve a set of position ids to position objects."""
        return [self._by_id[pid] for pid in ids if pid in self._by_id]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, position: Position) -> None:
        """Register a position and build secondary indices."""
        self._by_id[position.id] = position
        self._index(position)

    def get(self, position_id: str) -> Position:
        """Return the position for *position_id*; raise KeyError if absent."""
        try:
            return self._by_id[position_id]
        except KeyError:
            msg = f"Position '{position_id}' not found"
            raise KeyError(msg) from None

    def close(self, position_id: str) -> None:
        """Set position status to CLOSED and rebuild its index entries."""
        position = self.get(position_id)
        self._deindex(position)
        position.status = PositionStatus.CLOSED  # type: ignore[union-attr]
        self._index(position)

    def by_book(self, book_type: BookType) -> list[Position]:
        """Return all positions in *book_type*."""
        return self._ids_to_positions(self._by_book[book_type])

    def by_instrument(self, instrument_id: str) -> list[Position]:
        """Return all positions for *instrument_id*."""
        return self._ids_to_positions(self._by_instrument[instrument_id])

    def by_side(self, side: PositionSide) -> list[Position]:
        """Return all positions with *side*."""
        return self._ids_to_positions(self._by_side[side])

    def by_status(self, status: PositionStatus) -> list[Position]:
        """Return all positions with *status*."""
        return self._ids_to_positions(self._by_status[status])

    def open_positions(self) -> list[Position]:
        """Shortcut for by_status(PositionStatus.OPEN)."""
        return self.by_status(PositionStatus.OPEN)

    def query(
        self,
        *,
        book_type: BookType | None = None,
        side: PositionSide | None = None,
        status: PositionStatus | None = None,
        instrument_type: InstrumentType | None = None,
        instrument_class: InstrumentClass | None = None,
    ) -> list[Position]:
        """Return positions matching all non-None filter parameters."""
        result_ids: set[str] | None = None

        def intersect(ids: set[str]) -> set[str]:
            if result_ids is None:
                return set(ids)
            return result_ids & ids

        if book_type is not None:
            result_ids = intersect(self._by_book[book_type])
        if side is not None:
            result_ids = intersect(self._by_side[side])
        if status is not None:
            result_ids = intersect(self._by_status[status])
        if instrument_type is not None:
            result_ids = intersect(self._by_instrument_type[instrument_type])
        if instrument_class is not None:
            result_ids = intersect(self._by_instrument_class[instrument_class])

        if result_ids is None:
            return list(self._by_id.values())
        return self._ids_to_positions(result_ids)
