# ruff: noqa: S101, PLR2004, D102
"""Comprehensive tests for the accounting module.

Covers T-accounts, composite accounts, journal entries, ledger posting/closing,
chart of accounts, and the bank-specific chart of accounts.
"""

from __future__ import annotations

import datetime

import pytest

from brms.core.models.accounting.accounts import (
    AccountBalances,
    AccountNormalBalance,
    AccountType,
    CompositeTAccount,
    TAccount,
)
from brms.core.models.accounting.bank_accounts import BankChartOfAccounts
from brms.core.models.accounting.chart_of_accounts import (
    ChartOfAccounts,
    ChartOfAccountsBuilder,
    IncomeSummaryAccount,
    RetainedEarningsAccount,
)
from brms.core.models.accounting.journal import CompoundEntry, Journal, SimpleEntry
from brms.core.models.accounting.ledger import Ledger

# ---------------------------------------------------------------------------
# AccountType and normal balances
# ---------------------------------------------------------------------------


class TestAccountType:
    """Tests for AccountType enum and normal balance mapping."""

    def test_asset_has_debit_normal(self) -> None:
        nb = AccountType.get_normal_balance(AccountType.ASSET)
        assert nb == AccountNormalBalance.DEBIT_NORMAL

    def test_expense_has_debit_normal(self) -> None:
        nb = AccountType.get_normal_balance(AccountType.EXPENSE)
        assert nb == AccountNormalBalance.DEBIT_NORMAL

    def test_liability_has_credit_normal(self) -> None:
        nb = AccountType.get_normal_balance(AccountType.LIABILITY)
        assert nb == AccountNormalBalance.CREDIT_NORMAL

    def test_equity_has_credit_normal(self) -> None:
        nb = AccountType.get_normal_balance(AccountType.EQUITY)
        assert nb == AccountNormalBalance.CREDIT_NORMAL

    def test_income_has_credit_normal(self) -> None:
        nb = AccountType.get_normal_balance(AccountType.INCOME)
        assert nb == AccountNormalBalance.CREDIT_NORMAL

    def test_contra_asset_has_credit_normal(self) -> None:
        nb = AccountType.get_normal_balance(AccountType.ASSET, contra_account=True)
        assert nb == AccountNormalBalance.CREDIT_NORMAL

    def test_contra_liability_has_debit_normal(self) -> None:
        nb = AccountType.get_normal_balance(AccountType.LIABILITY, contra_account=True)
        assert nb == AccountNormalBalance.DEBIT_NORMAL


# ---------------------------------------------------------------------------
# TAccount
# ---------------------------------------------------------------------------


class TestTAccount:
    """Tests for TAccount debit, credit, and balance."""

    def test_asset_debit_increases_balance(self) -> None:
        cash = TAccount("Cash", AccountType.ASSET)
        cash.debit(1000)
        assert cash.balance() == 1000

    def test_asset_credit_decreases_balance(self) -> None:
        cash = TAccount("Cash", AccountType.ASSET)
        cash.debit(1000)
        cash.credit(200)
        assert cash.balance() == 800

    def test_liability_credit_increases_balance(self) -> None:
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        deposits.credit(5000)
        assert deposits.balance() == 5000

    def test_liability_debit_decreases_balance(self) -> None:
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        deposits.credit(5000)
        deposits.debit(200)
        assert deposits.balance() == 4800

    def test_equity_credit_increases_balance(self) -> None:
        equity = TAccount("Equity", AccountType.EQUITY)
        equity.credit(10000)
        assert equity.balance() == 10000

    def test_income_credit_increases_balance(self) -> None:
        income = TAccount("Revenue", AccountType.INCOME)
        income.credit(3000)
        assert income.balance() == 3000

    def test_expense_debit_increases_balance(self) -> None:
        expense = TAccount("Rent", AccountType.EXPENSE)
        expense.debit(1500)
        assert expense.balance() == 1500

    def test_is_not_composite(self) -> None:
        account = TAccount("Test", AccountType.ASSET)
        assert not list(account.sub_accounts)  # simple account has no children

    def test_contra_account(self) -> None:
        main = TAccount("Revenue", AccountType.INCOME)
        contra = TAccount("Sales Returns", AccountType.INCOME, is_contra_account=True)
        main.contra_accounts = [contra]
        assert main.has_contra_account()
        assert contra.normal_balance == AccountNormalBalance.DEBIT_NORMAL


# ---------------------------------------------------------------------------
# CompositeTAccount
# ---------------------------------------------------------------------------


class TestCompositeTAccount:
    """Tests for composite T-accounts with sub-accounts."""

    def test_add_sub_account(self) -> None:
        parent = CompositeTAccount("Investment", AccountType.ASSET)
        child = TAccount("HTM", AccountType.ASSET)
        parent.add_sub_account(child)
        assert list(parent.sub_accounts)  # has children
        assert child.parent is parent

    def test_balance_aggregates_children(self) -> None:
        parent = CompositeTAccount("Investment", AccountType.ASSET)
        child1 = TAccount("HTM", AccountType.ASSET)
        child2 = TAccount("FVOCI", AccountType.ASSET)
        parent.add_sub_account(child1)
        parent.add_sub_account(child2)

        child1.debit(5000)
        child2.debit(3000)
        assert parent.balance() == 8000

    def test_remove_sub_account(self) -> None:
        parent = CompositeTAccount("Investment", AccountType.ASSET)
        child = TAccount("HTM", AccountType.ASSET)
        parent.add_sub_account(child)
        child.debit(5000)
        assert parent.balance() == 5000

        parent.remove_sub_account(child)
        assert parent.balance() == 0
        assert child.parent is None

    def test_cannot_set_value_directly_with_children(self) -> None:
        parent = CompositeTAccount("Investment", AccountType.ASSET)
        child = TAccount("HTM", AccountType.ASSET)
        parent.add_sub_account(child)

        with pytest.raises(ValueError, match="Cannot post directly"):
            parent.debit_value = 100

    def test_can_set_value_when_no_children(self) -> None:
        parent = CompositeTAccount("Investment", AccountType.ASSET)
        parent.debit_value = 100
        assert parent.balance() == 100

    def test_nested_composite_propagation(self) -> None:
        grandparent = CompositeTAccount("All Assets", AccountType.ASSET)
        parent = CompositeTAccount("Investment", AccountType.ASSET)
        child = TAccount("HTM", AccountType.ASSET)

        grandparent.add_sub_account(parent)
        parent.add_sub_account(child)

        child.debit(1000)
        assert parent.balance() == 1000
        assert grandparent.balance() == 1000

    def test_sub_accounts_iterator(self) -> None:
        parent = CompositeTAccount("Investment", AccountType.ASSET)
        child1 = TAccount("HTM", AccountType.ASSET)
        child2 = TAccount("FVOCI", AccountType.ASSET)
        parent.add_sub_account(child1)
        parent.add_sub_account(child2)

        subs = list(parent.sub_accounts)
        assert len(subs) == 2
        assert child1 in subs
        assert child2 in subs


# ---------------------------------------------------------------------------
# AccountBalances
# ---------------------------------------------------------------------------


class TestAccountBalances:
    """Tests for AccountBalances."""

    def test_from_accounts(self) -> None:
        cash = TAccount("Cash", AccountType.ASSET)
        cash.debit(500)
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        deposits.credit(500)

        balances = AccountBalances.from_accounts([cash, deposits])
        assert balances[cash] == 500
        assert balances[deposits] == 500


# ---------------------------------------------------------------------------
# SimpleEntry
# ---------------------------------------------------------------------------


class TestSimpleEntry:
    """Tests for SimpleEntry journal entry."""

    def test_simple_entry_posts_correctly(self) -> None:
        cash = TAccount("Cash", AccountType.ASSET)
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        entry = SimpleEntry(debit_account=cash, credit_account=deposits, value=10000)

        assert entry.debit_accounts == {cash: 10000}
        assert entry.credit_accounts == {deposits: 10000}

    def test_involves_account(self) -> None:
        cash = TAccount("Cash", AccountType.ASSET)
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        entry = SimpleEntry(debit_account=cash, credit_account=deposits, value=10000)

        assert entry.involves_account(cash)
        assert entry.involves_account(deposits)
        assert not entry.involves_account(TAccount("Other", AccountType.ASSET))

    def test_reversed_swaps_accounts(self) -> None:
        cash = TAccount("Cash", AccountType.ASSET)
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=deposits,
            value=10000,
            description="Original",
        )

        reversed_entry = entry.reversed()
        assert reversed_entry.debit_account is deposits
        assert reversed_entry.credit_account is cash
        assert reversed_entry.value == 10000
        assert "Reversal" in reversed_entry.description


# ---------------------------------------------------------------------------
# CompoundEntry
# ---------------------------------------------------------------------------


class TestCompoundEntry:
    """Tests for CompoundEntry journal entry."""

    def test_balanced_compound_entry(self) -> None:
        a1 = TAccount("A1", AccountType.ASSET)
        a2 = TAccount("A2", AccountType.ASSET)
        l1 = TAccount("L1", AccountType.LIABILITY)

        entry = CompoundEntry(
            debit_accounts={a1: 3000, a2: 2000},
            credit_accounts={l1: 5000},
        )
        assert entry.total_debits() == 5000
        assert entry.total_credits() == 5000
        assert entry.is_balanced()

    def test_unbalanced_compound_entry_raises(self) -> None:
        a1 = TAccount("A1", AccountType.ASSET)
        l1 = TAccount("L1", AccountType.LIABILITY)

        with pytest.raises(ValueError, match="not balanced"):
            CompoundEntry(
                debit_accounts={a1: 3000},
                credit_accounts={l1: 5000},
            )

    def test_compound_reversed(self) -> None:
        a1 = TAccount("A1", AccountType.INCOME)
        l1 = TAccount("L1", AccountType.INCOME)

        entry = CompoundEntry(
            debit_accounts={a1: 5000},
            credit_accounts={l1: 5000},
            description="Close income",
        )

        reversed_entry = entry.reversed()
        assert reversed_entry.debit_accounts == {l1: 5000}
        assert reversed_entry.credit_accounts == {a1: 5000}
        assert "Reversal" in reversed_entry.description

    def test_involves_account(self) -> None:
        a1 = TAccount("A1", AccountType.ASSET)
        l1 = TAccount("L1", AccountType.LIABILITY)
        entry = CompoundEntry(
            debit_accounts={a1: 5000},
            credit_accounts={l1: 5000},
        )
        assert entry.involves_account(a1)
        assert entry.involves_account(l1)
        assert not entry.involves_account(TAccount("Other", AccountType.ASSET))


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------


class TestJournal:
    """Tests for Journal."""

    def test_add_and_retrieve_entries(self) -> None:
        journal = Journal()
        cash = TAccount("Cash", AccountType.ASSET)
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        entry = SimpleEntry(
            debit_account=cash,
            credit_account=deposits,
            value=1000,
            date=datetime.date(2024, 1, 15),
        )
        journal.add_entry(entry)
        assert len(journal.entries) == 1
        assert journal.get_entries_by_date(datetime.date(2024, 1, 15)) == [entry]
        assert journal.get_entries_by_account(cash) == [entry]

    def test_entries_within_date_range(self) -> None:
        journal = Journal()
        cash = TAccount("Cash", AccountType.ASSET)
        deposits = TAccount("Deposits", AccountType.LIABILITY)

        e1 = SimpleEntry(debit_account=cash, credit_account=deposits, value=100, date=datetime.date(2024, 1, 1))
        e2 = SimpleEntry(debit_account=cash, credit_account=deposits, value=200, date=datetime.date(2024, 1, 15))
        e3 = SimpleEntry(debit_account=cash, credit_account=deposits, value=300, date=datetime.date(2024, 2, 1))
        journal.add_entry(e1)
        journal.add_entry(e2)
        journal.add_entry(e3)

        result = journal.get_entries_within_date_range(datetime.date(2024, 1, 10), datetime.date(2024, 1, 31))
        assert result == [e2]


# ---------------------------------------------------------------------------
# Ledger posting
# ---------------------------------------------------------------------------


class TestLedgerPosting:
    """Tests for ledger posting."""

    def test_post_simple_entry(self) -> None:
        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa)

        entry = SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.customer_deposits_account,
            value=10000,
        )
        ledger.post(entry)

        assert coa.cash_account.balance() == 10000
        assert coa.customer_deposits_account.balance() == 10000
        # Composite parent should reflect child
        assert coa.deposit_account.balance() == 10000

    def test_post_compound_entry(self) -> None:
        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa)

        entry = CompoundEntry(
            debit_accounts={coa.cash_account: 7000, coa.loan_account: 3000},
            credit_accounts={coa.equity_account: 10000},
        )
        ledger.post(entry)

        assert coa.cash_account.balance() == 7000
        assert coa.loan_account.balance() == 3000
        assert coa.equity_account.balance() == 10000

    def test_journal_records_entries(self) -> None:
        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa)

        entry = SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.equity_account,
            value=5000,
            date=datetime.date(2024, 1, 1),
        )
        ledger.post(entry)
        assert len(ledger.journal.entries) == 1

    def test_set_and_get_account_balances(self) -> None:
        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa)

        balances = AccountBalances({coa.cash_account: 5000.0, coa.equity_account: 5000.0})
        ledger.set_account_balances(balances)

        assert coa.cash_account.balance() == 5000
        assert coa.equity_account.balance() == 5000


# ---------------------------------------------------------------------------
# Ledger closing
# ---------------------------------------------------------------------------


class TestLedgerClosing:
    """Tests for ledger period-end closing."""

    def test_close_income_to_retained_earnings(self) -> None:
        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa)

        # Post interest income
        entry = SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.interest_income_account,
            value=1000,
        )
        ledger.post(entry)
        assert coa.interest_income_account.balance() == 1000

        # Close the ledger
        ledger.close_ledger(datetime.date(2024, 12, 31))

        # Income should be zero, retained earnings should have the profit
        assert coa.interest_income_account.balance() == 0
        assert coa.retained_earnings_account.balance() == 1000

    def test_close_expense_to_retained_earnings(self) -> None:
        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa)

        # Post interest expense
        entry = SimpleEntry(
            debit_account=coa.interest_expense_account,
            credit_account=coa.cash_account,
            value=500,
        )
        ledger.post(entry)

        ledger.close_ledger(datetime.date(2024, 12, 31))

        assert coa.interest_expense_account.balance() == 0
        assert coa.retained_earnings_account.balance() == -500  # net loss

    def test_close_with_income_and_expense(self) -> None:
        coa = BankChartOfAccounts()
        ledger = Ledger(chart_of_accounts=coa)

        # Income of 3000
        ledger.post(SimpleEntry(
            debit_account=coa.cash_account,
            credit_account=coa.interest_income_account,
            value=3000,
        ))
        # Expense of 1000
        ledger.post(SimpleEntry(
            debit_account=coa.interest_expense_account,
            credit_account=coa.cash_account,
            value=1000,
        ))

        ledger.close_ledger(datetime.date(2024, 12, 31))

        # Net profit = 3000 - 1000 = 2000
        assert coa.retained_earnings_account.balance() == 2000


# ---------------------------------------------------------------------------
# ChartOfAccounts iteration
# ---------------------------------------------------------------------------


class TestChartOfAccounts:
    """Tests for ChartOfAccounts and builder."""

    def test_iter_yields_all_accounts(self) -> None:
        cash = TAccount("Cash", AccountType.ASSET)
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        equity = TAccount("Equity", AccountType.EQUITY)

        coa = ChartOfAccounts(
            assets=[cash],
            liabilities=[deposits],
            equities=[equity],
        )

        accounts = list(coa)
        # Should include cash, deposits, equity, income_summary, retained_earnings
        assert cash in accounts
        assert deposits in accounts
        assert equity in accounts
        assert coa.income_summary_account in accounts
        assert coa.retained_earnings_account in accounts

    def test_iter_includes_contra_accounts(self) -> None:
        main = TAccount("Revenue", AccountType.INCOME)
        contra = TAccount("Sales Returns", AccountType.INCOME, is_contra_account=True)
        main.contra_accounts = [contra]

        coa = ChartOfAccounts(income=[main])
        accounts = list(coa)
        assert contra in accounts

    def test_builder_validates_account_type(self) -> None:
        builder = ChartOfAccountsBuilder()
        with pytest.raises(ValueError, match="mismatch"):
            builder.add_asset_account(TAccount("Wrong", AccountType.LIABILITY))

    def test_builder_builds_correctly(self) -> None:
        cash = TAccount("Cash", AccountType.ASSET)
        deposits = TAccount("Deposits", AccountType.LIABILITY)
        equity = TAccount("Equity", AccountType.EQUITY)
        income = TAccount("Revenue", AccountType.INCOME)
        expense = TAccount("Rent", AccountType.EXPENSE)

        coa = (
            ChartOfAccountsBuilder()
            .add_asset_account(cash)
            .add_liability_account(deposits)
            .add_equity_account(equity)
            .add_income_account(income)
            .add_expense_account(expense)
            .build()
        )

        assert cash in coa.assets
        assert deposits in coa.liabilities
        assert equity in coa.equities
        assert income in coa.income
        assert expense in coa.expenses


# ---------------------------------------------------------------------------
# BankChartOfAccounts structure
# ---------------------------------------------------------------------------


class TestBankChartOfAccounts:
    """Tests for BankChartOfAccounts wiring."""

    def test_asset_accounts_populated(self) -> None:
        coa = BankChartOfAccounts()
        assert len(coa.assets) == 8
        assert coa.cash_account in coa.assets
        assert coa.loan_account in coa.assets
        assert coa.investment_securities_account in coa.assets

    def test_liability_accounts_populated(self) -> None:
        coa = BankChartOfAccounts()
        assert len(coa.liabilities) == 4
        assert coa.deposit_account in coa.liabilities

    def test_equity_accounts_populated(self) -> None:
        coa = BankChartOfAccounts()
        assert len(coa.equities) == 3  # noqa: PLR2004
        assert coa.equity_account in coa.equities
        assert coa.accumulated_oci_account in coa.equities
        assert coa.opening_balance_equity in coa.equities

    def test_income_accounts_populated(self) -> None:
        coa = BankChartOfAccounts()
        assert len(coa.income) == 3
        assert coa.interest_income_account in coa.income
        assert coa.trading_income_account in coa.income

    def test_expense_accounts_populated(self) -> None:
        coa = BankChartOfAccounts()
        assert len(coa.expenses) == 2

    def test_composite_sub_account_shortcuts(self) -> None:
        coa = BankChartOfAccounts()
        # Investment securities sub-accounts are children of the composite
        inv_subs = list(coa.investment_securities_account.sub_accounts)
        assert coa.investment_htm_account in inv_subs
        assert coa.investment_fvoci_account in inv_subs
        # Deposit sub-accounts are children of the composite
        dep_subs = list(coa.deposit_account.sub_accounts)
        assert coa.customer_deposits_account in dep_subs
        assert coa.public_borrowings_account in dep_subs

    def test_trading_income_sub_accounts(self) -> None:
        coa = BankChartOfAccounts()
        subs = list(coa.trading_income_account.sub_accounts)
        assert len(subs) == 4
        assert coa.unrealized_trading_gain_account in subs
        assert coa.realized_trading_gain_account in subs
        assert coa.unrealized_trading_loss_account in subs
        assert coa.realized_trading_loss_account in subs

    def test_accumulated_oci_sub_accounts(self) -> None:
        coa = BankChartOfAccounts()
        subs = list(coa.accumulated_oci_account.sub_accounts)
        assert len(subs) == 2
        assert coa.unrealized_oci_gain_account in subs
        assert coa.unrealized_oci_loss_account in subs

    def test_oci_gain_has_loss_as_contra(self) -> None:
        coa = BankChartOfAccounts()
        assert coa.unrealized_oci_loss_account in coa.unrealized_oci_gain_account.contra_accounts


# ---------------------------------------------------------------------------
# IncomeSummaryAccount and RetainedEarningsAccount
# ---------------------------------------------------------------------------


class TestSpecialAccounts:
    """Tests for IncomeSummaryAccount and RetainedEarningsAccount."""

    def test_income_summary_is_temporary(self) -> None:
        isa = IncomeSummaryAccount()
        assert isa.is_temporary_account
        assert isa.type == AccountType.INCOME

    def test_retained_earnings_is_equity(self) -> None:
        re = RetainedEarningsAccount()
        assert re.type == AccountType.EQUITY
        assert not re.is_temporary_account
