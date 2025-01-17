"""Define the `Bank` class."""

from typing import TYPE_CHECKING

import brms.accounting.preset as act  # The preset accounts
from brms.accounting.account import AccountBalances, ChartOfAccounts
from brms.accounting.ledger import Ledger
from brms.instruments.cash import Cash
from brms.instruments.visitors.valuation import BankingBookValuationVisitor, TradingBookValuationVisitor
from brms.models.accountant import Accountant
from brms.models.bank_book import BankingBook, TradingBook

if TYPE_CHECKING:
    from brms.models.scenario import Scenario
    from brms.models.transaction import Transaction


class Bank:
    """Class representing a bank."""

    def __init__(self) -> None:
        """Initialize the Bank."""
        self.banking_book = BankingBook()
        self.trading_book = TradingBook()
        self.ledger = Ledger()
        self.accountant = Accountant(self, self.ledger)

    def initialize(
        self,
        chart_of_accounts: ChartOfAccounts | None = None,
        account_balances: AccountBalances | None = None,
    ) -> None:
        """Initialize the bank with a chart of accounts and account balances."""
        if chart_of_accounts is None:
            chart_of_accounts = act.chart_of_accounts
        if account_balances is None:
            account_balances = AccountBalances()
        self.ledger.add_accounts_from_chart(chart_of_accounts, account_balances)
        # After initiating the leger, init the bank's banking and trading books with instruments
        # TODO: init all instruments other than cash
        cash = Cash("Cash")
        cash.value = account_balances[act.cash_account]
        self.banking_book.add_instrument(cash)

    def valuation(self, scenario: "Scenario") -> None:
        """Perform valuation on banking and trading book instruments."""
        self.banking_book.accept(BankingBookValuationVisitor(scenario))
        self.trading_book.accept(TradingBookValuationVisitor(scenario))

    def process_transaction(self, transaction: "Transaction") -> None:
        """Ask the accountant to process the transaction."""
        self.accountant.process_transaction(transaction)


if __name__ == "__main__":
    import datetime

    import QuantLib as ql

    from brms.accounting.report import Report
    from brms.accounting.statement_viewer import HTMLStatementViewer
    from brms.instruments.base import BookType
    from brms.instruments.fixed_rate_bond import FixedRateBond
    from brms.models.transaction import Transaction, TransactionType
    from brms.models.scenario import Scenario

    balances = AccountBalances(
        {
            act.cash_account: 12500,
            act.equity_account: 30000,
            act.ppe_account: 20000,
            act.chart_of_accounts.retained_earnings_account: 2500,
        },
    )

    bank = Bank()
    bank.initialize(act.chart_of_accounts, balances)

    face_value = 10000.0
    coupon_rate = 0.05
    issue_date = ql.Date(1, 1, 2020)
    maturity_date = ql.Date(1, 1, 2030)
    bond = FixedRateBond(
        face_value=face_value,
        coupon_rate=coupon_rate,
        issue_date=issue_date,
        maturity_date=maturity_date,
        book_type=BookType.BANKING_BOOK,
    )

    transaction_date = datetime.date(2020, 1, 1)
    transaction = Transaction(
        transaction_type=TransactionType.BUY_INSTRUMENT,
        instrument=bond,
        account=act.loan_account,
        value=face_value,
        date=transaction_date,
    )
    bank.process_transaction(transaction)

    report = Report(ledger=bank.ledger, viewer=HTMLStatementViewer(), date=datetime.date(2021, 1, 1))

    html_trial_balance = report.print_trial_balance()
    html_income_statement = report.print_income_statement()
    html_balance_sheet = report.print_balance_sheet()

    print(html_trial_balance)
    print(html_income_statement)
    print(html_balance_sheet)
