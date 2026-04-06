"""AccountingService: maps Transaction dataclasses to journal entries and posts to the Ledger.

Supports reversal (counter-entries) for step-back simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from brms.core.enums import TransactionType
from brms.core.models.accounting.journal import SimpleEntry

if TYPE_CHECKING:
    from brms.core.models.accounting.accounts import TAccount
    from brms.core.models.accounting.journal import JournalEntry
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.models.transaction import Transaction
    from brms.core.stores.position_store import PositionStore


class AccountingService:
    """Maps Transaction records to journal entries and posts them to a Ledger.

    The service looks up named accounts from the ledger's chart of accounts so
    that callers do not need to pass account references explicitly.
    """

    def post_all(self, transactions: list[Transaction], ledger: Ledger, position_store: PositionStore) -> None:
        """Post all transactions to ledger and update positions as needed."""
        for tx in transactions:
            self._post_to_ledger(tx, ledger)
            self._update_positions(tx, position_store)

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

    def _post_to_ledger(self, tx: Transaction, ledger: Ledger) -> None:
        """Post a single transaction to the ledger."""
        entries = self._map_to_entries(tx, ledger)
        for entry in entries:
            ledger.post(entry)

    def _update_positions(self, tx: Transaction, position_store: PositionStore) -> None:
        """Close positions on maturity or sale transactions."""
        if tx.type in (TransactionType.MATURITY_SETTLEMENT, TransactionType.SECURITY_SALE) and tx.position_id:
            position_store.close(tx.position_id)

    def _map_to_entries(self, transaction: Transaction, ledger: Ledger) -> list[JournalEntry]:  # noqa: C901, PLR0911, PLR0912
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
            case TransactionType.LOAN_DISBURSEMENT:
                return self._loan_disbursement(transaction, ledger)
            case TransactionType.LOAN_REPAYMENT:
                return self._loan_repayment(transaction, ledger)
            case TransactionType.INTEREST_PAYMENT | TransactionType.COUPON_PAYMENT:
                return self._interest_payment(transaction, ledger)
            case TransactionType.INTEREST_EXPENSE:
                return self._interest_expense(transaction, ledger)
            case TransactionType.MARK_TO_MARKET | TransactionType.REVALUATION:
                return self._mark_to_market(transaction, ledger)
            case TransactionType.PRINCIPAL_PAYMENT:
                return self._principal_payment(transaction, ledger)
            case TransactionType.AMORTIZATION:
                return self._amortization(transaction, ledger)
            case TransactionType.MATURITY_SETTLEMENT:
                return self._maturity_settlement(transaction, ledger)
            case _:
                msg = f"No accounting rule defined for TransactionType.{transaction.type.name}"
                raise NotImplementedError(msg)

    def _lookup(self, ledger: Ledger, name: str) -> TAccount:
        """Look up a TAccount by name, searching all accounts including sub-accounts.

        Raises:
            KeyError: if no account with *name* exists in the chart.
        """
        for account in ledger.chart_of_accounts.all_accounts():
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

    def _loan_disbursement(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """LOAN_DISBURSEMENT: debit Loans, credit Cash."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        loans = self._lookup(ledger, "Loans and Advances")
        entry = SimpleEntry(
            debit_account=loans,
            credit_account=cash,
            value=float(tx.amount),
            date=tx.date,
            description=f"Loan disbursement (tx={tx.id})",
        )
        return [entry]

    def _loan_repayment(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """LOAN_REPAYMENT: debit Cash, credit Loans."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        loans = self._lookup(ledger, "Loans and Advances")
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=loans,
            value=float(tx.amount),
            date=tx.date,
            description=f"Loan repayment (tx={tx.id})",
        )
        return [entry]

    def _interest_payment(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """INTEREST_PAYMENT / COUPON_PAYMENT: debit Cash, credit Interest Income."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        interest_income = self._lookup(ledger, "Interest Income")
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=interest_income,
            value=float(tx.amount),
            date=tx.date,
            description=f"Interest/coupon payment received (tx={tx.id})",
        )
        return [entry]

    def _interest_expense(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """INTEREST_EXPENSE: debit Interest Expense, credit Cash."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        interest_expense = self._lookup(ledger, "Interest Expense")
        entry = SimpleEntry(
            debit_account=interest_expense,
            credit_account=cash,
            value=float(tx.amount),
            date=tx.date,
            description=f"Interest expense (tx={tx.id})",
        )
        return [entry]

    def _mark_to_market(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """MARK_TO_MARKET / REVALUATION: debit/credit asset vs income account.

        FVTPL: asset is 'Assets at FVTPL'; gain uses 'Unrealized Trading Gain',
        loss uses 'Unrealized Trading Loss'.
        FVOCI: asset is 'Investment Securities at FVOCI'; gain uses 'Unrealized OCI Gain',
        loss uses 'Unrealized OCI Loss'.

        A positive amount represents a gain (debit asset, credit income/equity).
        A negative amount represents a loss (debit expense/contra-equity, credit asset).
        """
        meta = dict(tx.metadata)
        instrument_class = meta.get("instrument_class", "")
        amount = float(tx.amount)
        if instrument_class == "FVTPL":
            asset = self._lookup(ledger, "Assets at FVTPL")
            if amount >= 0:
                debit_account = asset
                credit_account = self._lookup(ledger, "Unrealized Trading Gain")
                value = amount
            else:
                debit_account = self._lookup(ledger, "Unrealized Trading Loss")
                credit_account = asset
                value = -amount
        elif instrument_class == "FVOCI":
            asset = self._lookup(ledger, "Investment Securities at FVOCI")
            if amount >= 0:
                debit_account = asset
                credit_account = self._lookup(ledger, "Unrealized OCI Gain")
                value = amount
            else:
                debit_account = self._lookup(ledger, "Unrealized OCI Loss")
                credit_account = asset
                value = -amount
        else:
            msg = f"Unknown instrument_class '{instrument_class}' for mark-to-market in tx={tx.id}"
            raise ValueError(msg)
        entry = SimpleEntry(
            debit_account=debit_account,
            credit_account=credit_account,
            value=value,
            date=tx.date,
            description=f"Mark-to-market / revaluation (tx={tx.id})",
        )
        return [entry]

    def _principal_payment(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """PRINCIPAL_PAYMENT: debit Cash, credit Loans."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        loans = self._lookup(ledger, "Loans and Advances")
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=loans,
            value=float(tx.amount),
            date=tx.date,
            description=f"Principal payment (tx={tx.id})",
        )
        return [entry]

    def _amortization(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """AMORTIZATION: debit Cash, credit Loans."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        loans = self._lookup(ledger, "Loans and Advances")
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=loans,
            value=float(tx.amount),
            date=tx.date,
            description=f"Amortization (tx={tx.id})",
        )
        return [entry]

    def _maturity_settlement(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """MATURITY_SETTLEMENT: debit Cash, credit Investment account (based on metadata)."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        investment = self._resolve_investment_account(tx, ledger)
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=investment,
            value=float(tx.amount),
            date=tx.date,
            description=f"Maturity settlement (tx={tx.id})",
        )
        return [entry]
