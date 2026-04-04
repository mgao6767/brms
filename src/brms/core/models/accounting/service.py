"""AccountingService: maps Transaction dataclasses to journal entries and posts to the Ledger.

Supports reversal (counter-entries) for step-back simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

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
            case TransactionType.EQUITY_ISSUANCE:
                return self._equity_issuance(transaction, ledger)
            case TransactionType.SECURITY_PURCHASE:
                return self._security_purchase(transaction, ledger)
            case TransactionType.SECURITY_SALE:
                return self._security_sale(transaction, ledger)
            case TransactionType.DEPOSIT_WITHDRAWAL:
                return self._deposit_withdrawal(transaction, ledger)
            case _:
                msg = f"No accounting rule defined for TransactionType.{transaction.type.name}"
                raise NotImplementedError(msg)

    def _lookup(self, ledger: Ledger, name: str) -> TAccount:
        """Look up a TAccount by name from the ledger's chart of accounts.

        Searches top-level accounts, their contra-accounts, and sub-accounts of
        composite accounts recursively.

        Raises:
            KeyError: if no account with *name* exists in the chart.

        """
        def _search(account: TAccount) -> TAccount | None:
            if account.name == name:
                return account
            for sub in account.sub_accounts:
                found = _search(sub)
                if found is not None:
                    return found
            return None

        for account in ledger.chart_of_accounts:
            found = _search(account)
            if found is not None:
                return found
        msg = f"Account '{name}' not found in chart of accounts"
        raise KeyError(msg)

    # ------------------------------------------------------------------
    # Transaction-type handlers
    # Each handler returns list[JournalEntry] for the given transaction.
    # ------------------------------------------------------------------

    def _deposit_received(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """DEPOSIT_RECEIVED: debit Cash, credit Deposits."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        deposits = self._lookup(ledger, "Deposits")
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=deposits,
            value=float(tx.amount),
            date=tx.date,
            description=f"Deposit received (tx={tx.id})",
        )
        return [entry]

    def _equity_issuance(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """EQUITY_ISSUANCE: debit Cash, credit Equity."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        equity = self._lookup(ledger, "Shareholders' Equity")
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=equity,
            value=float(tx.amount),
            date=tx.date,
            description=f"Equity issuance (tx={tx.id})",
        )
        return [entry]

    _INSTRUMENT_CLASS_TO_ACCOUNT: ClassVar[dict[str, str]] = {
        "HTM": "Investment Securities at Amortized Cost",
        "FVOCI": "Investment Securities at FVOCI",
        "FVTPL": "Assets at FVTPL",
    }

    def _resolve_investment_account(self, tx: Transaction, ledger: Ledger) -> TAccount:
        """Return the investment account for the instrument_class in *tx* metadata."""
        meta = dict(tx.metadata)
        instrument_class = meta.get("instrument_class", "")
        account_name = self._INSTRUMENT_CLASS_TO_ACCOUNT.get(instrument_class)
        if account_name is None:
            msg = f"Unknown instrument_class '{instrument_class}' in metadata for tx={tx.id}"
            raise ValueError(msg)
        return self._lookup(ledger, account_name)

    def _security_purchase(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """SECURITY_PURCHASE: debit Investment account, credit Cash."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        investment = self._resolve_investment_account(tx, ledger)
        entry = SimpleEntry(
            debit_account=investment,
            credit_account=cash,
            value=float(tx.amount),
            date=tx.date,
            description=f"Security purchase (tx={tx.id})",
        )
        return [entry]

    def _security_sale(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """SECURITY_SALE: debit Cash, credit Investment account."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        investment = self._resolve_investment_account(tx, ledger)
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=investment,
            value=float(tx.amount),
            date=tx.date,
            description=f"Security sale (tx={tx.id})",
        )
        return [entry]

    def _deposit_withdrawal(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """DEPOSIT_WITHDRAWAL: debit Deposits, credit Cash."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        deposits = self._lookup(ledger, "Deposits")
        entry = SimpleEntry(
            debit_account=deposits,
            credit_account=cash,
            value=float(tx.amount),
            date=tx.date,
            description=f"Deposit withdrawal (tx={tx.id})",
        )
        return [entry]
