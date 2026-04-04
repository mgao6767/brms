# ruff: noqa: S101, PLR2004
"""Tests for AccountingService."""

import datetime
from decimal import Decimal

import pytest

from brms.core.models.accounting.accounts import (
    AccountType,
    ChartOfAccounts,
    TAccount,
)
from brms.core.models.accounting.journal import Journal
from brms.core.models.accounting.ledger import Ledger
from brms.core.models.accounting.service import AccountingService
from brms.core.models.transaction import Transaction, TransactionType


def _make_ledger() -> tuple[Ledger, TAccount, TAccount]:
    """Create a simple ledger with cash and deposit accounts."""
    journal = Journal()
    cash = TAccount("Cash", AccountType.ASSET)
    deposits = TAccount("Deposits", AccountType.LIABILITY)
    coa = ChartOfAccounts(
        assets=[cash],
        liabilities=[deposits],
    )
    ledger = Ledger(chart_of_accounts=coa, journal=journal)
    # Give cash an initial balance (TAccount uses float internally)
    cash.debit(100000.0)
    return ledger, cash, deposits


def test_post_deposit_received() -> None:
    """Posting DEPOSIT_RECEIVED debits Cash and credits Deposits."""
    ledger, cash, deposits = _make_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-1",
        type=TransactionType.DEPOSIT_RECEIVED,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("10000"),
    )
    service.post(tx, ledger)
    # Deposit received: debit Cash, credit Deposits
    assert cash.balance() == 110000.0
    assert deposits.balance() == 10000.0


def test_reverse_undoes_post() -> None:
    """Reversing a posted transaction restores original balances."""
    ledger, cash, deposits = _make_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-1",
        type=TransactionType.DEPOSIT_RECEIVED,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("10000"),
    )
    service.post(tx, ledger)
    service.reverse(tx, ledger)
    # After reversal, balances should be back to original
    assert cash.balance() == 100000.0
    assert deposits.balance() == 0.0


def test_post_unknown_transaction_type_raises() -> None:
    """Posting an unsupported transaction type raises NotImplementedError."""
    ledger, _cash, _deposits = _make_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-2",
        type=TransactionType.MARK_TO_MARKET,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("500"),
    )
    with pytest.raises(NotImplementedError):
        service.post(tx, ledger)


def test_post_records_entry_in_journal() -> None:
    """Posting a transaction adds an entry to the ledger journal."""
    ledger, _cash, _deposits = _make_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-3",
        type=TransactionType.DEPOSIT_RECEIVED,
        date=datetime.date(2024, 2, 1),
        amount=Decimal("5000"),
    )
    assert len(ledger.journal.entries) == 0
    service.post(tx, ledger)
    assert len(ledger.journal.entries) == 1


def test_reverse_records_reversal_entry_in_journal() -> None:
    """Reversing a transaction adds a reversal entry to the ledger journal."""
    ledger, _cash, _deposits = _make_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-4",
        type=TransactionType.DEPOSIT_RECEIVED,
        date=datetime.date(2024, 3, 1),
        amount=Decimal("2000"),
    )
    service.post(tx, ledger)
    service.reverse(tx, ledger)
    assert len(ledger.journal.entries) == 2
    assert "Reversal" in ledger.journal.entries[1].description
