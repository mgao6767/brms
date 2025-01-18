import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from brms.accounting.journal import JournalEntry, CompoundEntry, SimpleEntry
from brms.instruments.base import Instrument
from brms.instruments.cash import Cash
from brms.models.bank import Bank


class TransactionType(Enum):
    """Enumeration of different types of transactions."""

    # --- Banking Book Transactions ---
    # Deposits & Withdrawals
    DEPOSIT_RECEIVED = auto()
    DEPOSIT_WITHDRAWAL = auto()
    INTEREST_PAID_ON_DEPOSIT = auto()
    INTEREST_EARNED_ON_DEPOSIT = auto()

    # Loans & Credit Facilities
    LOAN_DISBURSEMENT = auto()
    LOAN_REPAYMENT = auto()
    LOAN_CHARGE_OFF = auto()
    LOAN_RESCHEDULING = auto()
    LOAN_INTEREST_ACCRUAL = auto()
    LOAN_INTEREST_PAYMENT = auto()
    LOAN_FEE_INCOME = auto()
    LOAN_IMPAIRMENT_PROVISION = auto()

    # Securities Held-to-Maturity (HTM) & FVOCI (Banking Book)
    SECURITY_PURCHASE_HTM = auto()
    SECURITY_SALE_HTM = auto()
    SECURITY_INTEREST_EARNED = auto()
    SECURITY_IMPAIRMENT_HTM = auto()

    # Reserve & Regulatory Requirements
    RESERVE_REQUIREMENT_DEPOSIT = auto()
    RESERVE_WITHDRAWAL = auto()

    # --- Trading Book Transactions ---
    # Buying & Selling Securities
    SECURITY_PURCHASE_TRADING = auto()
    SECURITY_SALE_TRADING = auto()
    SECURITY_MARK_TO_MARKET_ADJUSTMENT = auto()
    SECURITY_DIVIDEND_RECEIVED = auto()

    # Derivatives Transactions
    DERIVATIVE_CONTRACT_INITIATED = auto()
    DERIVATIVE_CONTRACT_SETTLED = auto()
    DERIVATIVE_MARK_TO_MARKET_ADJUSTMENT = auto()
    DERIVATIVE_MARGIN_CALL = auto()

    # Foreign Exchange Transactions
    FOREX_SPOT_TRADE = auto()
    FOREX_FORWARD_CONTRACT = auto()
    FOREX_SWAP_CONTRACT = auto()
    FOREX_OPTION_TRADE = auto()

    # --- Payment Transactions ---
    WIRE_TRANSFER_SENT = auto()
    WIRE_TRANSFER_RECEIVED = auto()
    ACH_TRANSFER_SENT = auto()
    ACH_TRANSFER_RECEIVED = auto()
    CARD_TRANSACTION = auto()

    # --- Capital & Funding Transactions ---
    EQUITY_ISSUANCE = auto()
    DEBT_ISSUANCE = auto()
    DIVIDEND_PAYMENT = auto()
    SHARE_REPURCHASE = auto()
    INTEREST_PAYMENT_ON_DEBT = auto()

    # --- Fees & Charges ---
    ACCOUNT_MAINTENANCE_FEE = auto()
    OVERDRAFT_FEE = auto()
    WIRE_TRANSFER_FEE = auto()
    LATE_PAYMENT_FEE = auto()
    LOAN_ORIGINATION_FEE = auto()

    # --- Other Adjustments ---
    TAX_PAYMENT = auto()
    TAX_REFUND = auto()
    WRITE_OFF_BAD_DEBT = auto()
    PROVISION_FOR_LOSSES = auto()
    INTERNAL_FUNDS_TRANSFER = auto()

    # --- Liquidity & Collateral Transactions ---
    REPO_TRANSACTION = auto()
    REVERSE_REPO_TRANSACTION = auto()
    COLLATERAL_POSTED = auto()
    COLLATERAL_RECEIVED = auto()

    # --- Miscellaneous Transactions ---
    CUSTOMER_CASH_DEPOSIT = auto()
    CUSTOMER_CASH_WITHDRAWAL = auto()
    INTEREST_ON_RESERVE_BALANCES = auto()
    BANK_SERVICE_CHARGE = auto()


@dataclass
class Transaction(ABC):
    """Abstract Command class for transactions."""

    bank: Bank
    instrument: Instrument
    value: float
    transaction_type: TransactionType
    description: str = ""
    transaction_date: datetime.date | None = None

    @abstractmethod
    def execute(self) -> None:
        """Execute the transaction and posts entries to the ledger."""

    @abstractmethod
    def undo(self) -> None:
        """Reverse the transaction (rollback)."""

    @property
    @abstractmethod
    def journal_entry(self) -> JournalEntry:
        """Return the journal entry for the transaction."""

    @property
    @abstractmethod
    def reverse_journal_entry(self) -> JournalEntry:
        """Return the reverse journal entry to undo the transaction."""


class DepositTransaction(Transaction):
    """Class representing a deposit transaction."""

    def __init__(self, bank: Bank, value: float, date: datetime.date | None = None, description: str = "") -> None:
        (cash := Cash("Cash")).value = value
        super().__init__(
            bank=bank,
            instrument=cash,
            value=value,
            transaction_type=TransactionType.DEPOSIT_RECEIVED,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.customer_deposits_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.customer_deposits_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class DepositWithdrawTransaction(Transaction):
    """Class representing a deposit withdrawal transaction."""

    def __init__(self, bank: Bank, value: float, date: datetime.date | None = None, description: str = "") -> None:
        (cash := Cash("Cash")).value = value
        super().__init__(
            bank=bank,
            instrument=cash,
            value=value,
            transaction_type=TransactionType.DEPOSIT_WITHDRAWAL,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.customer_deposits_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.customer_deposits_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class InterestPaidOnDepositTransaction(Transaction):
    """Class representing an interest paid on deposit transaction."""

    def __init__(self, bank: Bank, value: float, date: datetime.date | None = None, description: str = "") -> None:
        (cash := Cash("Cash")).value = value
        super().__init__(
            bank=bank,
            instrument=cash,
            value=value,
            transaction_type=TransactionType.INTEREST_PAID_ON_DEPOSIT,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.interest_expense_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.interest_expense_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


if __name__ == "__main__":
    from brms.accounting.account import AccountBalances
    from brms.accounting.report import Report
    from brms.accounting.statement_viewer import HTMLStatementViewer

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

    date = datetime.date(2024, 12, 31)

    bank.process_transaction(DepositTransaction(bank, 1000000000, date))
    bank.undo_last_transaction()
    bank.process_transaction(DepositWithdrawTransaction(bank, 12500, date))
    bank.undo_last_transaction()

    report = Report(ledger=bank.ledger, viewer=HTMLStatementViewer(), date=date)

    html_trial_balance = report.print_trial_balance()
    html_income_statement = report.print_income_statement()
    html_balance_sheet = report.print_balance_sheet()

    print(html_trial_balance)
    print(html_income_statement)
    print(html_balance_sheet)
