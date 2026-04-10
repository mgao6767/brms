# ruff: noqa: S101, PLR2004
"""Tests for AccountingService."""

import datetime
from decimal import Decimal

import pytest

from brms.core.models.accounting.accounts import (
    AccountType,
    TAccount,
)
from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.chart_of_accounts import ChartOfAccounts
from brms.core.models.accounting.journal import Journal
from brms.core.models.accounting.ledger import Ledger
from brms.core.services.accounting_service import AccountingService
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


def test_mark_to_market_unknown_measurement_basis_raises() -> None:
    """MARK_TO_MARKET with an unknown measurement_basis raises ValueError."""
    ledger, _cash, _deposits = _make_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-2",
        type=TransactionType.MARK_TO_MARKET,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("500"),
    )
    with pytest.raises(ValueError, match="Unknown measurement_basis"):
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
        metadata=(("measurement_basis", "HTM"),),
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
        metadata=(("measurement_basis", "FVOCI"),),
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
        metadata=(("measurement_basis", "FVTPL"),),
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
        metadata=(("measurement_basis", "HTM"),),
    )
    sale_tx = Transaction(
        id="tx-sell-1",
        type=TransactionType.SECURITY_SALE,
        date=datetime.date(2024, 3, 15),
        amount=Decimal("40000"),
        metadata=(("measurement_basis", "HTM"),),
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


# ---------------------------------------------------------------------------
# LOAN_DISBURSEMENT
# ---------------------------------------------------------------------------


def test_loan_disbursement() -> None:
    """LOAN_DISBURSEMENT debits Loans and credits Cash."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-loan-1",
        type=TransactionType.LOAN_DISBURSEMENT,
        date=datetime.date(2024, 5, 1),
        amount=Decimal("80000"),
    )
    service.post(tx, ledger)
    assert coa.loan_account.balance() == 80_000.0
    assert coa.cash_account.balance() == 420_000.0


# ---------------------------------------------------------------------------
# LOAN_REPAYMENT
# ---------------------------------------------------------------------------


def test_loan_repayment() -> None:
    """LOAN_REPAYMENT debits Cash and credits Loans."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    disburse_tx = Transaction(
        id="tx-loan-2",
        type=TransactionType.LOAN_DISBURSEMENT,
        date=datetime.date(2024, 5, 1),
        amount=Decimal("80000"),
    )
    repay_tx = Transaction(
        id="tx-loan-3",
        type=TransactionType.LOAN_REPAYMENT,
        date=datetime.date(2024, 6, 1),
        amount=Decimal("80000"),
    )
    service.post(disburse_tx, ledger)
    service.post(repay_tx, ledger)
    assert coa.loan_account.balance() == 0.0
    assert coa.cash_account.balance() == 500_000.0


# ---------------------------------------------------------------------------
# INTEREST_PAYMENT
# ---------------------------------------------------------------------------


def test_interest_payment() -> None:
    """INTEREST_PAYMENT debits Cash and credits Interest Income."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-int-1",
        type=TransactionType.INTEREST_PAYMENT,
        date=datetime.date(2024, 6, 1),
        amount=Decimal("3000"),
    )
    service.post(tx, ledger)
    assert coa.cash_account.balance() == 503_000.0
    assert coa.interest_income_account.balance() == 3_000.0


# ---------------------------------------------------------------------------
# COUPON_PAYMENT
# ---------------------------------------------------------------------------


def test_coupon_payment() -> None:
    """COUPON_PAYMENT debits Cash and credits Interest Income."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-cpn-1",
        type=TransactionType.COUPON_PAYMENT,
        date=datetime.date(2024, 6, 15),
        amount=Decimal("1500"),
    )
    service.post(tx, ledger)
    assert coa.cash_account.balance() == 501_500.0
    assert coa.interest_income_account.balance() == 1_500.0


# ---------------------------------------------------------------------------
# INTEREST_EXPENSE
# ---------------------------------------------------------------------------


def test_interest_expense() -> None:
    """INTEREST_EXPENSE debits Interest Expense and credits Cash."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-iexp-1",
        type=TransactionType.INTEREST_EXPENSE,
        date=datetime.date(2024, 7, 1),
        amount=Decimal("2000"),
    )
    service.post(tx, ledger)
    assert coa.interest_expense_account.balance() == 2_000.0
    assert coa.cash_account.balance() == 498_000.0


# ---------------------------------------------------------------------------
# MARK_TO_MARKET (FVTPL gain and loss)
# ---------------------------------------------------------------------------


def test_mark_to_market_fvtpl_gain() -> None:
    """MARK_TO_MARKET with FVTPL and positive amount debits Asset FVTPL, credits Trading Income."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-mtm-1",
        type=TransactionType.MARK_TO_MARKET,
        date=datetime.date(2024, 7, 1),
        amount=Decimal("5000"),
        metadata=(("measurement_basis", "FVTPL"),),
    )
    service.post(tx, ledger)
    assert coa.asset_fvtpl_account.balance() == 5_000.0
    assert coa.trading_income_account.balance() == 5_000.0


def test_mark_to_market_fvtpl_loss() -> None:
    """MARK_TO_MARKET with FVTPL and negative amount debits Trading Income, credits Asset FVTPL."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-mtm-2",
        type=TransactionType.MARK_TO_MARKET,
        date=datetime.date(2024, 7, 2),
        amount=Decimal("-2000"),
        metadata=(("measurement_basis", "FVTPL"),),
    )
    service.post(tx, ledger)
    assert coa.asset_fvtpl_account.balance() == -2_000.0
    assert coa.trading_income_account.balance() == -2_000.0


# ---------------------------------------------------------------------------
# MARK_TO_MARKET (FVOCI gain and loss)
# ---------------------------------------------------------------------------


def test_mark_to_market_fvoci_gain() -> None:
    """MARK_TO_MARKET with FVOCI and positive amount debits Investment FVOCI, credits Accumulated OCI."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-mtm-3",
        type=TransactionType.MARK_TO_MARKET,
        date=datetime.date(2024, 7, 3),
        amount=Decimal("4000"),
        metadata=(("measurement_basis", "FVOCI"),),
    )
    service.post(tx, ledger)
    assert coa.investment_fvoci_account.balance() == 4_000.0
    assert coa.accumulated_oci_account.balance() == 4_000.0


def test_mark_to_market_fvoci_loss() -> None:
    """MARK_TO_MARKET with FVOCI and negative amount debits Accumulated OCI, credits Investment FVOCI."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-mtm-4",
        type=TransactionType.MARK_TO_MARKET,
        date=datetime.date(2024, 7, 4),
        amount=Decimal("-1000"),
        metadata=(("measurement_basis", "FVOCI"),),
    )
    service.post(tx, ledger)
    assert coa.investment_fvoci_account.balance() == -1_000.0
    assert coa.accumulated_oci_account.balance() == -1_000.0


# ---------------------------------------------------------------------------
# REVALUATION (same logic as MARK_TO_MARKET)
# ---------------------------------------------------------------------------


def test_revaluation_fvtpl() -> None:
    """REVALUATION with FVTPL debits Asset FVTPL and credits Trading Income."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    tx = Transaction(
        id="tx-rev-1",
        type=TransactionType.REVALUATION,
        date=datetime.date(2024, 8, 1),
        amount=Decimal("3000"),
        metadata=(("measurement_basis", "FVTPL"),),
    )
    service.post(tx, ledger)
    assert coa.asset_fvtpl_account.balance() == 3_000.0
    assert coa.trading_income_account.balance() == 3_000.0


# ---------------------------------------------------------------------------
# PRINCIPAL_PAYMENT
# ---------------------------------------------------------------------------


def test_principal_payment() -> None:
    """PRINCIPAL_PAYMENT debits Cash and credits Loans."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    disburse_tx = Transaction(
        id="tx-pp-1",
        type=TransactionType.LOAN_DISBURSEMENT,
        date=datetime.date(2024, 5, 1),
        amount=Decimal("60000"),
    )
    principal_tx = Transaction(
        id="tx-pp-2",
        type=TransactionType.PRINCIPAL_PAYMENT,
        date=datetime.date(2024, 6, 1),
        amount=Decimal("10000"),
    )
    service.post(disburse_tx, ledger)
    service.post(principal_tx, ledger)
    assert coa.loan_account.balance() == 50_000.0
    assert coa.cash_account.balance() == 450_000.0


# ---------------------------------------------------------------------------
# AMORTIZATION
# ---------------------------------------------------------------------------


def test_amortization() -> None:
    """AMORTIZATION debits Cash and credits Loans."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    disburse_tx = Transaction(
        id="tx-am-1",
        type=TransactionType.LOAN_DISBURSEMENT,
        date=datetime.date(2024, 5, 1),
        amount=Decimal("50000"),
    )
    amort_tx = Transaction(
        id="tx-am-2",
        type=TransactionType.AMORTIZATION,
        date=datetime.date(2024, 6, 1),
        amount=Decimal("5000"),
    )
    service.post(disburse_tx, ledger)
    service.post(amort_tx, ledger)
    assert coa.loan_account.balance() == 45_000.0
    assert coa.cash_account.balance() == 455_000.0


# ---------------------------------------------------------------------------
# MATURITY_SETTLEMENT
# ---------------------------------------------------------------------------


def test_maturity_settlement_htm() -> None:
    """MATURITY_SETTLEMENT with HTM debits Cash and credits Investment HTM."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    purchase_tx = Transaction(
        id="tx-mat-1",
        type=TransactionType.SECURITY_PURCHASE,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("100000"),
        metadata=(("measurement_basis", "HTM"),),
    )
    maturity_tx = Transaction(
        id="tx-mat-2",
        type=TransactionType.MATURITY_SETTLEMENT,
        date=datetime.date(2025, 1, 1),
        amount=Decimal("100000"),
        metadata=(("measurement_basis", "HTM"),),
    )
    service.post(purchase_tx, ledger)
    service.post(maturity_tx, ledger)
    assert coa.investment_htm_account.balance() == 0.0
    assert coa.cash_account.balance() == 500_000.0


def test_maturity_settlement_fvoci() -> None:
    """MATURITY_SETTLEMENT with FVOCI debits Cash and credits Investment FVOCI."""
    ledger, coa = _make_full_ledger()
    service = AccountingService()
    purchase_tx = Transaction(
        id="tx-mat-3",
        type=TransactionType.SECURITY_PURCHASE,
        date=datetime.date(2024, 1, 1),
        amount=Decimal("70000"),
        metadata=(("measurement_basis", "FVOCI"),),
    )
    maturity_tx = Transaction(
        id="tx-mat-4",
        type=TransactionType.MATURITY_SETTLEMENT,
        date=datetime.date(2025, 1, 1),
        amount=Decimal("70000"),
        metadata=(("measurement_basis", "FVOCI"),),
    )
    service.post(purchase_tx, ledger)
    service.post(maturity_tx, ledger)
    assert coa.investment_fvoci_account.balance() == 0.0
    assert coa.cash_account.balance() == 500_000.0


# ---------------------------------------------------------------------------
# Reversal round-trip parametrized tests
# ---------------------------------------------------------------------------


def _make_fresh_ledger() -> tuple[Ledger, BankChartOfAccounts]:
    """Create a Ledger backed by BankChartOfAccounts with no initial balances."""
    coa = BankChartOfAccounts()
    journal = Journal()
    ledger = Ledger(chart_of_accounts=coa, journal=journal)
    return ledger, coa


ROUND_TRIP_CASES = [
    ("equity", TransactionType.EQUITY_ISSUANCE, Decimal("1000000"), ()),
    ("deposit", TransactionType.DEPOSIT_RECEIVED, Decimal("50000"), ()),
    ("withdrawal", TransactionType.DEPOSIT_WITHDRAWAL, Decimal("50000"), ()),
    ("loan_disburse", TransactionType.LOAN_DISBURSEMENT, Decimal("200000"), ()),
    ("loan_repay", TransactionType.LOAN_REPAYMENT, Decimal("10000"), ()),
    ("interest", TransactionType.INTEREST_PAYMENT, Decimal("500"), ()),
    ("coupon", TransactionType.COUPON_PAYMENT, Decimal("2500"), ()),
    ("interest_exp", TransactionType.INTEREST_EXPENSE, Decimal("300"), ()),
    ("sec_buy_htm", TransactionType.SECURITY_PURCHASE, Decimal("10000"), (("measurement_basis", "HTM"),)),
    ("sec_buy_fvoci", TransactionType.SECURITY_PURCHASE, Decimal("10000"), (("measurement_basis", "FVOCI"),)),
    ("sec_buy_fvtpl", TransactionType.SECURITY_PURCHASE, Decimal("10000"), (("measurement_basis", "FVTPL"),)),
    ("principal", TransactionType.PRINCIPAL_PAYMENT, Decimal("5000"), ()),
    ("amortization", TransactionType.AMORTIZATION, Decimal("3000"), ()),
    ("maturity_htm", TransactionType.MATURITY_SETTLEMENT, Decimal("100000"), (("measurement_basis", "HTM"),)),
]


ROUND_TRIP_IDS = [c[0] for c in ROUND_TRIP_CASES]


@pytest.mark.parametrize(("name", "tx_type", "amount", "metadata"), ROUND_TRIP_CASES, ids=ROUND_TRIP_IDS)
def test_post_then_reverse_zeroes_balances(
    name: str, tx_type: TransactionType, amount: Decimal, metadata: tuple,
) -> None:
    """Posting then reversing any transaction type leaves all account balances at zero."""
    ledger, coa = _make_fresh_ledger()
    service = AccountingService()
    tx = Transaction(
        id=f"rt-{name}",
        type=tx_type,
        date=datetime.date(2024, 1, 1),
        amount=amount,
        metadata=metadata,
    )
    service.post(tx, ledger)
    service.reverse(tx, ledger)
    for account in coa:
        assert account.balance() == 0.0, f"Account {account.name} has non-zero balance after reversal of {name}"
