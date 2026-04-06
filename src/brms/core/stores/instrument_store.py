"""InstrumentStore: in-memory registry of financial instruments."""

from __future__ import annotations

import contextlib
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brms.core.enums import InstrumentType


class InstrumentStore:
    """Stores instruments indexed by id and by type for O(1) / O(k) access."""

    def __init__(self) -> None:
        """Initialize empty id and type indices."""
        self._by_id: dict[str, object] = {}
        self._by_type: dict[InstrumentType, list[object]] = defaultdict(list)

    def add(self, instrument: object) -> None:
        """Register an instrument. Overwrites any existing entry with the same id."""
        existing = self._by_id.get(instrument.id)  # type: ignore[union-attr]
        if existing is not None:
            old_type = existing.instrument_type  # type: ignore[union-attr]
            with contextlib.suppress(ValueError):
                self._by_type[old_type].remove(existing)
        self._by_id[instrument.id] = instrument  # type: ignore[union-attr]
        self._by_type[instrument.instrument_type].append(instrument)  # type: ignore[union-attr]

    def get(self, instrument_id: str) -> object:
        """Return the instrument for *instrument_id*; raise KeyError if absent."""
        try:
            return self._by_id[instrument_id]
        except KeyError:
            msg = f"Instrument '{instrument_id}' not found"
            raise KeyError(msg) from None

    def by_type(self, instrument_type: InstrumentType) -> list[object]:
        """Return all instruments of *instrument_type* (empty list if none)."""
        return list(self._by_type[instrument_type])

    def all(self) -> list[object]:
        """Return all registered instruments."""
        return list(self._by_id.values())

    def __iter__(self):  # noqa: ANN204
        """Iterate over all registered instruments."""
        return iter(self._by_id.values())

    def __len__(self) -> int:
        """Return the number of registered instruments."""
        return len(self._by_id)
