"""TransactionLog: append-only transaction history with fast lookup indices."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime


class TransactionLog:
    """Append-only log of Transaction records with secondary index support."""

    def __init__(self) -> None:
        """Initialize an empty transaction log with secondary indices."""
        self._log: list[Any] = []
        self._by_instrument: dict[str, list[int]] = defaultdict(list)
        self._by_position: dict[str, list[int]] = defaultdict(list)
        self._by_date: dict[datetime.date, list[int]] = defaultdict(list)
        self._by_type: dict[Any, list[int]] = defaultdict(list)

    def _append(self, transaction: Any) -> None:  # noqa: ANN401
        """Append *transaction* to the log and update all indices."""
        idx = len(self._log)
        self._log.append(transaction)
        if transaction.instrument_id is not None:
            self._by_instrument[transaction.instrument_id].append(idx)
        if transaction.position_id is not None:
            self._by_position[transaction.position_id].append(idx)
        self._by_date[transaction.date].append(idx)
        self._by_type[transaction.type].append(idx)

    def record(self, transaction: Any) -> None:  # noqa: ANN401
        """Append a single transaction to the log."""
        self._append(transaction)

    def record_batch(self, transactions: Any) -> None:  # noqa: ANN401
        """Append multiple transactions to the log in order."""
        for tx in transactions:
            self._append(tx)

    def _resolve(self, indices: list[int]) -> list[Any]:
        return [self._log[i] for i in indices]

    def by_instrument(self, instrument_id: str) -> list[Any]:
        """Return all transactions for *instrument_id*."""
        return self._resolve(self._by_instrument.get(instrument_id, []))

    def by_position(self, position_id: str) -> list[Any]:
        """Return all transactions for *position_id*."""
        return self._resolve(self._by_position.get(position_id, []))

    def by_date(self, date: datetime.date) -> list[Any]:
        """Return all transactions on *date*."""
        return self._resolve(self._by_date.get(date, []))

    def by_type(self, tx_type: Any) -> list[Any]:  # noqa: ANN401
        """Return all transactions of *tx_type*."""
        return self._resolve(self._by_type.get(tx_type, []))

    def all(self) -> list[Any]:
        """Return all transactions in insertion order."""
        return list(self._log)
