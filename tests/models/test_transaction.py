import datetime

import pytest

from brms.accounting.account import AccountBalances
from brms.instruments.cash import Cash
from brms.instruments.deposit import Deposit
from brms.instruments.visitors.valuation import ValuationVisitor
from brms.models.bank import Bank
from brms.models.scenario import Scenario
from brms.models.transaction import (
    DepositTransaction,
    DepositWithdrawTransaction,
    InterestPaidOnDepositTransaction,
    LoanDisbursementTransaction,
    LoanRepaymentTransaction,
    SecurityMarkToMarketFVTPLTransaction,
    SecurityPurchaseFVOCITransaction,
    SecurityPurchaseFVTPLTransaction,
    SecurityPurchaseHTMTransaction,
    SecuritySaleHTMTransaction,
)


class MockValuationVisitor(ValuationVisitor):
    """Mock valuation visitor to value cash to 1000."""

    def __init__(self, scenario: "Scenario") -> None:
        self.scenario = scenario

    def visit_cash(self, cash: Cash) -> None:
        cash.value = 1000

    def visit_amortizing_fixed_rate_loan(self, loan) -> None:
        pass

    def visit_covered_bond(self, bond) -> None:
        pass

    def visit_credit_card(self, card) -> None:
        pass

    def visit_fixed_rate_bond(self, bond) -> None:
        pass

    def visit_personal_loan(self, loan) -> None:
        pass


@pytest.fixture
def bank():
    bank = Bank()
    account_balances = AccountBalances(
        {
            bank.chart_of_accounts.cash_account: 12500,
            bank.chart_of_accounts.equity_account: 30000,
            bank.chart_of_accounts.ppe_account: 20000,
            bank.chart_of_accounts.retained_earnings_account: 2500,
        },
    )
    bank.initialize(account_balances)
    return bank


@pytest.fixture
def date():
    return datetime.date(2024, 12, 31)


def test_deposit_and_withdraw_transaction(bank, date):
    deposit_value = 1000
    deposit = Deposit(value=deposit_value)
    old_balance = bank.chart_of_accounts.deposit_account.balance()
    transaction = DepositTransaction(bank, deposit, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.deposit_account.balance()
    assert bank.ledger.journal.entries[-1].value == deposit_value
    assert new_balance - old_balance == deposit_value
    transaction.undo()
    assert old_balance == bank.chart_of_accounts.deposit_account.balance()


def test_deposit_withdraw_transaction(bank, date):
    old_balance = bank.chart_of_accounts.deposit_account.balance()
    deposit = Deposit(value=1000)
    DepositTransaction(bank, deposit, date).execute()
    transaction = DepositWithdrawTransaction(bank, deposit, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.deposit_account.balance()
    assert new_balance == old_balance


def test_interest_paid_on_deposit_transaction(bank, date):
    expense = 500
    old_balance = bank.chart_of_accounts.interest_expense_account.balance()
    transaction = InterestPaidOnDepositTransaction(bank, expense, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.interest_expense_account.balance()
    assert new_balance - old_balance == expense
    transaction.undo()
    new_balance = bank.chart_of_accounts.interest_expense_account.balance()
    assert new_balance == old_balance


def test_loan_disbursement_transaction(bank, date):
    loan_value = 2000
    loan = Cash(value=loan_value)  # Mock loan
    old_balance = bank.chart_of_accounts.loan_account.balance()
    old_cash_balance = bank.chart_of_accounts.cash_account.balance()
    transaction = LoanDisbursementTransaction(bank, loan, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.loan_account.balance()
    new_cash_balance = bank.chart_of_accounts.cash_account.balance()
    assert bank.ledger.journal.entries[-1].value == loan_value
    assert new_balance - old_balance == loan_value
    assert old_cash_balance - new_cash_balance == loan_value
    transaction.undo()
    assert old_balance == bank.chart_of_accounts.loan_account.balance()
    assert old_cash_balance == bank.chart_of_accounts.cash_account.balance()


def test_loan_repayment_transaction(bank, date):
    loan_value = 2000
    loan = Cash(value=loan_value)
    old_balance = bank.chart_of_accounts.loan_account.balance()
    transaction = LoanRepaymentTransaction(bank, loan, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.loan_account.balance()
    assert bank.ledger.journal.entries[-1].value == loan_value
    assert new_balance - old_balance == -loan_value
    transaction.undo()
    assert old_balance == bank.chart_of_accounts.loan_account.balance()


def test_security_purchase_htm_transaction(bank, date):
    security_value = 1500
    security = Cash(value=security_value)
    old_balance = bank.chart_of_accounts.investment_htm_account.balance()
    transaction = SecurityPurchaseHTMTransaction(bank, security, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.investment_htm_account.balance()
    assert bank.ledger.journal.entries[-1].value == security_value
    assert new_balance - old_balance == security_value
    transaction.undo()
    assert old_balance == bank.chart_of_accounts.investment_htm_account.balance()


def test_security_sale_htm_transaction(bank, date):
    security_value = 1500
    security = Cash(value=security_value)
    SecurityPurchaseHTMTransaction(bank, security, date).execute()
    old_balance = bank.chart_of_accounts.investment_htm_account.balance()
    transaction = SecuritySaleHTMTransaction(bank, security, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.investment_htm_account.balance()
    assert bank.ledger.journal.entries[-1].value == security_value
    assert new_balance - old_balance == -security_value
    transaction.undo()
    assert old_balance == bank.chart_of_accounts.investment_htm_account.balance()


def test_security_purchase_fvoci_transaction(bank, date):
    security_value = 1529
    security = Cash(value=security_value)
    old_balance = bank.chart_of_accounts.investment_fvoci_account.balance()
    transaction = SecurityPurchaseFVOCITransaction(bank, security, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.investment_fvoci_account.balance()
    assert bank.ledger.journal.entries[-1].value == security_value
    assert new_balance - old_balance == security_value
    transaction.undo()
    assert old_balance == bank.chart_of_accounts.investment_fvoci_account.balance()


def test_security_purchase_fvtpl_transaction(bank, date):
    security_value = 23
    security = Cash(value=security_value)
    old_balance = bank.chart_of_accounts.asset_fvtpl_account.balance()
    transaction = SecurityPurchaseFVTPLTransaction(bank, security, date)
    transaction.execute()
    new_balance = bank.chart_of_accounts.asset_fvtpl_account.balance()
    assert bank.ledger.journal.entries[-1].value == security_value
    assert new_balance - old_balance == security_value
    transaction.undo()
    assert old_balance == bank.chart_of_accounts.asset_fvtpl_account.balance()


def test_security_mark_to_market_fvtpl_gain_transaction(bank, date):
    security_value = 600
    security = Cash(value=security_value)
    SecurityPurchaseFVTPLTransaction(bank, security, date).execute()
    valuation_visitor = MockValuationVisitor(None)
    # Revalue the security to 1000
    transaction = SecurityMarkToMarketFVTPLTransaction(bank, security, valuation_visitor, date)
    transaction.execute()
    assert bank.chart_of_accounts.unrealized_trading_gain_account.balance() == 400
    transaction.undo()


def test_security_mark_to_market_fvtpl_loss_transaction(bank, date):
    security_value = 1200
    security = Cash(value=security_value)
    SecurityPurchaseFVTPLTransaction(bank, security, date).execute()
    valuation_visitor = MockValuationVisitor(None)
    # Revalue the security to 1000
    transaction = SecurityMarkToMarketFVTPLTransaction(bank, security, valuation_visitor, date)
    transaction.execute()
    assert bank.chart_of_accounts.unrealized_trading_loss_account.balance() == 200


if __name__ == "__main__":
    pytest.main([__file__])
