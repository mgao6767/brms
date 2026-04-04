# ruff: noqa: S101, PLR2004
"""Tests for AccountingService."""

import datetime
from decimal import Decimal

import pytest

from brms.core.models.accounting.accounts import (
    AccountType,
    BankChartOfAccounts,
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
    cash = TAccount("Cash and Cash Equivalents", AccountType.ASSET)
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


# ---------------------------------------------------------------------------
# Full-ledger helper (BankChartOfAccounts)
# ---------------------------------------------------------------------------


def _make_full_ledger() -> tuple[Ledger, BankChartOfAccounts]:
    """Create a Ledger backed by BankChartOfAccounts with a starting cash balance."""
    coa = BankChartOfAccounts()
    journal = Journal()
    ledger = Ledger(chart_of_accounts=coa, journal=journal)
    # Seed cash so purchases don't go negative
    coa.cash_account.debit(500_000.0)
    return ledger, coa


# ---------------------------------------------------------------------------
# EQUITY_ISSUANCE
# ---------------------------------------------------------------------------


def test_equity_issuance() -> None:
    """EQUITY_ISSUANCE debits Cash and credits Equity."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-eq-1",
        type=TransactionType.EQUITY_ISSUANCE,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("100000"),
    )
    service.post(tx, ledger)
    assert coa.cash_account.balance() == 600_000.0
    assert coa.equity_account.balance() == 100_000.0


# ---------------------------------------------------------------------------
# SECURITY_PURCHASE
# ---------------------------------------------------------------------------


def test_security_purchase_htm() -> None:
    """SECURITY_PURCHASE with HTM debits Investment HTM and credits Cash."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-sec-1",
        type=TransactionType.SECURITY_PURCHASE,
        date=datetime.date(2024, 2, 1),
        amount=Decimal("50000"),
        metadata=(("instrument_class", "HTM"),),
    )
    service.post(tx, ledger)
    assert coa.investment_htm_account.balance() == 50_000.0
    assert coa.cash_account.balance() == 450_000.0


def test_security_purchase_fvoci() -> None:
    """SECURITY_PURCHASE with FVOCI debits Investment FVOCI and credits Cash."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-sec-2",
        type=TransactionType.SECURITY_PURCHASE,
        date=datetime.date(2024, 2, 1),
        amount=Decimal("30000"),
        metadata=(("instrument_class", "FVOCI"),),
    )
    service.post(tx, ledger)
    assert coa.investment_fvoci_account.balance() == 30_000.0
    assert coa.cash_account.balance() == 470_000.0


def test_security_purchase_fvtpl() -> None:
    """SECURITY_PURCHASE with FVTPL debits Assets at FVTPL and credits Cash."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-sec-3",
        type=TransactionType.SECURITY_PURCHASE,
        date=datetime.date(2024, 2, 1),
        amount=Decimal("20000"),
        metadata=(("instrument_class", "FVTPL"),),
    )
    service.post(tx, ledger)
    assert coa.asset_fvtpl_account.balance() == 20_000.0
    assert coa.cash_account.balance() == 480_000.0


# ---------------------------------------------------------------------------
# SECURITY_SALE
# ---------------------------------------------------------------------------


def test_security_sale_htm() -> None:
    """Buy then sell HTM security; balances return to original."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    purchase_tx = Transaction(
        id="tx-buy-1",
        type=TransactionType.SECURITY_PURCHASE,
        date=datetime.date(2024, 3, 1),
        amount=Decimal("40000"),
        metadata=(("instrument_class", "HTM"),),
    )
    sale_tx = Transaction(
        id="tx-sell-1",
        type=TransactionType.SECURITY_SALE,
        date=datetime.date(2024, 3, 15),
        amount=Decimal("40000"),
        metadata=(("instrument_class", "HTM"),),
    )
    service.post(purchase_tx, ledger)
    service.post(sale_tx, ledger)
    assert coa.investment_htm_account.balance() == 0.0
    assert coa.cash_account.balance() == 500_000.0


# ---------------------------------------------------------------------------
# DEPOSIT_WITHDRAWAL
# ---------------------------------------------------------------------------


def test_deposit_withdrawal() -> None:
    """Deposit then withdraw; both cash and deposits return to original."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    deposit_tx = Transaction(
        id="tx-dep-1",
        type=TransactionType.DEPOSIT_RECEIVED,
        date=datetime.date(2024, 4, 1),
        amount=Decimal("25000"),
    )
    withdrawal_tx = Transaction(
        id="tx-wd-1",
        type=TransactionType.DEPOSIT_WITHDRAWAL,
        date=datetime.date(2024, 4, 5),
        amount=Decimal("25000"),
    )
    service.post(deposit_tx, ledger)
    service.post(withdrawal_tx, ledger)
    # After deposit then withdrawal, cash and deposits should be back to original
    assert coa.customer_deposits_account.balance() == 0.0
    assert coa.cash_account.balance() == 500_000.0
