"""AccountingService: maps Transaction dataclasses to journal entries and posts to the Ledger.

Supports reversal (counter-entries) for step-back simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from brms.core.models.accounting.journal import SimpleEntry
from brms.core.models.transaction import TransactionType

if TYPE_CHECKING:
    from brms.core.models.accounting.accounts import TAccount
    from brms.core.models.accounting.journal import JournalEntry
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.models.transaction import Transaction


class AccountingService:
    """Maps Transaction records to journal entries and posts them to a Ledger.

    The service looks up named accounts from the ledger's chart of accounts so
    that callers do not need to pass account references explicitly.
    """

    def post(self, transaction: Transaction, ledger: Ledger) -> None:
        """Map *transaction* to journal entries and post each one to *ledger*."""
        entries = self._map_to_entries(transaction, ledger)
        for entry in entries:
            ledger.post(entry)

    def reverse(self, transaction: Transaction, ledger: Ledger) -> None:
        """Post the reversal (counter-entries) of *transaction* to *ledger*.

        This undoes the effect of a prior :meth:`post` call for the same
        transaction, restoring account balances to their pre-post state.
        """
        entries = self._map_to_entries(transaction, ledger)
        for entry in entries:
            ledger.post(entry.reversed())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _map_to_entries(self, transaction: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """Return the list of JournalEntry objects that represent *transaction*.

        Raises:
            NotImplementedError: when the TransactionType has no mapping defined.

        """
        match transaction.type:
            case TransactionType.DEPOSIT_RECEIVED:
                return self._deposit_received(transaction, ledger)
            case _:
                msg = f"No accounting rule defined for TransactionType.{transaction.type.name}"
                raise NotImplementedError(msg)

    def _lookup(self, ledger: Ledger, name: str) -> TAccount:
        """Look up a TAccount by name from the ledger's chart of accounts.

        Raises:
            KeyError: if no account with *name* exists in the chart.

        """
        for account in ledger.chart_of_accounts:
            if account.name == name:
                return account
        msg = f"Account '{name}' not found in chart of accounts"
        raise KeyError(msg)

    # ------------------------------------------------------------------
    # Transaction-type handlers
    # Each handler returns list[JournalEntry] for the given transaction.
    # ------------------------------------------------------------------

    def _deposit_received(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """DEPOSIT_RECEIVED: debit Cash, credit Deposits."""
        cash = self._lookup(ledger, "Cash")
        deposits = self._lookup(ledger, "Deposits")
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=deposits,
            value=float(tx.amount),
            date=tx.date,
            description=f"Deposit received (tx={tx.id})",
        )
        return [entry]
