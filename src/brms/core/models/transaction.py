"""Immutable transaction record."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from brms.core.enums import TransactionType

if TYPE_CHECKING:
    import datetime
    from decimal import Decimal


__all__ = ["Transaction", "TransactionType"]


@dataclass(frozen=True, slots=True)
class Transaction:
    """Lightweight, immutable record of an economic event."""

    id: str
    type: TransactionType
    date: datetime.date
    amount: Decimal
    position_id: str | None = None
    instrument_id: str | None = None
    metadata: tuple[tuple[str, Any], ...] = ()
