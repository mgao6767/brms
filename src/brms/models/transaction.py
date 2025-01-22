import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from brms.accounting.journal import CompoundEntry, JournalEntry, SimpleEntry
from brms.instruments.base import Instrument
from brms.instruments.cash import Cash
from brms.instruments.deposit import Deposit
from brms.instruments.visitors.valuation import ValuationVisitor
from brms.models.bank import Bank
from brms.models.bank_book import BookType, Position


class Action(Enum):
    ADD = "Add instrument to bank book"
    REMOVE = "Remove instrument from bank book"
    UPDATE = "Update instrument in the book"


GUIControllerInstruction = dict[Instrument, tuple[Action, BookType, Position]]


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
    SECURITY_PURCHASE_FVOCI = auto()
    SECURITY_SALE_FVOCI = auto()
    SECURITY_INTEREST_EARNED = auto()
    SECURITY_IMPAIRMENT_HTM = auto()

    # Reserve & Regulatory Requirements
    RESERVE_REQUIREMENT_DEPOSIT = auto()
    RESERVE_WITHDRAWAL = auto()

    # --- Trading Book Transactions ---
    # Buying & Selling Securities
    SECURITY_PURCHASE_TRADING = auto()
    SECURITY_SALE_TRADING = auto()
    SECURITY_MARK_TO_MARKET = auto()
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

    @abstractmethod
    def controller_actions(self) -> GUIControllerInstruction:
        """Return a mapping from instruments to actions, including book type and position.

        This instruction set is used by GUI's controllers to update views.
        In other uses it can be safely ignore.
        """


class DepositTransaction(Transaction):
    """Class representing a deposit transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Deposit,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_add = Cash(value=instrument.value)
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.DEPOSIT_RECEIVED,
            transaction_date=date,
            description=description,
        )

    def controller_actions(self) -> GUIControllerInstruction:
        return {
            self.cash_to_add: (Action.ADD, BookType.BANKING_BOOK, Position.LONG),
            self.instrument: (Action.ADD, BookType.BANKING_BOOK, Position.SHORT),
        }

    def execute(self) -> None:
        self.bank.banking_book.add_instrument(self.cash_to_add, Position.LONG)
        self.bank.banking_book.add_instrument(self.instrument, Position.SHORT)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.remove_instrument(self.cash_to_add, Position.LONG)
        self.bank.banking_book.remove_instrument(self.instrument, Position.SHORT)
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

    def __init__(
        self,
        bank: Bank,
        instrument: Deposit,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_pay = Cash(value=instrument.value)
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.DEPOSIT_WITHDRAWAL,
            transaction_date=date,
            description=description,
        )

    def controller_actions(self) -> GUIControllerInstruction:
        return {
            self.cash_to_pay: (Action.REMOVE, BookType.BANKING_BOOK, Position.LONG),
            self.instrument: (Action.REMOVE, BookType.BANKING_BOOK, Position.SHORT),
        }

    def execute(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument, Position.SHORT)
        self.bank.banking_book.add_instrument(self.cash_to_pay, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument, Position.SHORT)
        self.bank.banking_book.remove_instrument(self.cash_to_pay, Position.LONG)
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
        super().__init__(
            bank=bank,
            instrument=Cash(value=value),
            value=value,
            transaction_type=TransactionType.INTEREST_PAID_ON_DEPOSIT,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument, Position.LONG)
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


class LoanDisbursementTransaction(Transaction):
    """Class representing a loan disbursement transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,  # TODO: specify all instrument types that can be a loan?
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_disburse = Cash(value=instrument.value)
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.LOAN_DISBURSEMENT,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.remove_instrument(self.cash_to_disburse, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.add_instrument(self.cash_to_disburse, Position.LONG)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.loan_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.loan_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class LoanRepaymentTransaction(Transaction):
    """Class representing a matured loan repayment transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,  # TODO: specify all instrument types that can be a loan?
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_receive = Cash(value=instrument.value)
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.LOAN_REPAYMENT,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.add_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.remove_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.loan_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.loan_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class LoanInterestPaymentTransaction(Transaction):
    """Class representing a loan interest payment transaction."""

    def __init__(
        self,
        bank: Bank,
        value: float,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_receive = Cash(value=value)
        super().__init__(
            bank=bank,
            instrument=self.cash_to_receive,
            value=value,
            transaction_type=TransactionType.LOAN_INTEREST_PAYMENT,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.add_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.remove_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.interest_income_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.interest_income_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class SecurityPurchaseHTMTransaction(Transaction):
    """Class representing a security purchase held-to-maturity (HTM) transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_pay = Cash(value=instrument.value)
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.SECURITY_PURCHASE_HTM,
            transaction_date=date,
            description=description,
        )

    def controller_actions(self) -> GUIControllerInstruction:
        return {
            self.cash_to_pay: (Action.REMOVE, BookType.BANKING_BOOK, Position.LONG),
            self.instrument: (Action.ADD, BookType.BANKING_BOOK, Position.LONG),
        }

    def execute(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.remove_instrument(self.cash_to_pay, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.add_instrument(self.cash_to_pay, Position.LONG)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.investment_htm_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.investment_htm_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class SecuritySaleHTMTransaction(Transaction):
    """Class representing a security sale held-to-maturity (HTM) transaction.

    HTM securities should not be sold before maturity!
    This should be interpreted as the HTM security matures and removed from banking book.
    """

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_receive = Cash(value=instrument.value)
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.SECURITY_SALE_HTM,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.add_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.remove_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.investment_htm_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.investment_htm_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class SecurityPurchaseFVOCITransaction(Transaction):
    """Class representing a security purchase FVOCI (Fair Value through Other Comprehensive Income) transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_pay = Cash(value=instrument.value)
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.SECURITY_PURCHASE_FVOCI,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.remove_instrument(self.cash_to_pay, Position.LONG)
        self.bank.banking_book.unrealized_oci_tracker.add_instrument(self.instrument)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.add_instrument(self.cash_to_pay, Position.LONG)
        self.bank.banking_book.unrealized_oci_tracker.remove_instrument(self.instrument)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.investment_fvoci_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.investment_fvoci_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class SecuritySaleFVOCITransaction(Transaction):
    """Class representing a security sale FVOCI (Fair Value through Other Comprehensive Income) transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_receive = Cash(value=instrument.value)
        self.old_unrealized_oci_gain = 0.0
        self.old_unrealized_oci_loss = 0.0
        self.tracker = bank.banking_book.unrealized_oci_tracker
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.SECURITY_SALE_FVOCI,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.add_instrument(self.cash_to_receive, Position.LONG)
        self.old_unrealized_oci_gain = self.tracker.get_unrealized_gain(self.instrument)
        self.old_unrealized_oci_loss = self.tracker.get_unrealized_loss(self.instrument)
        self.bank.banking_book.unrealized_oci_tracker.remove_instrument(self.instrument)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.add_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.remove_instrument(self.cash_to_receive, Position.LONG)
        self.tracker.set_unrealized_gain(self.instrument, self.old_unrealized_oci_gain)
        self.tracker.set_unrealized_loss(self.instrument, self.old_unrealized_oci_loss)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        # This is the unrealized OCI associated with this specific instrument
        unrealized_oci_gain = self.tracker.get_unrealized_gain(self.instrument)
        unrealized_oci_loss = self.tracker.get_unrealized_loss(self.instrument)
        net_gain = unrealized_oci_gain - unrealized_oci_loss
        if net_gain >= 0:  # selling FVOCI at a gain
            return CompoundEntry(
                debit_accounts={
                    # 1. record cash received and remove security
                    self.bank.chart_of_accounts.cash_account: self.value,
                    # 2. transfer AOCI unrealized gain to net income (realized OCI gain)
                    self.bank.chart_of_accounts.unrealized_oci_gain_account: unrealized_oci_gain,
                    # 3. reverse previously recorded unrealized loss
                    self.bank.chart_of_accounts.realized_oci_loss_account: unrealized_oci_loss,
                },
                credit_accounts={
                    self.bank.chart_of_accounts.investment_fvoci_account: self.value,
                    self.bank.chart_of_accounts.realized_oci_gain_account: unrealized_oci_gain,
                    self.bank.chart_of_accounts.unrealized_oci_loss_account: unrealized_oci_loss,
                },
                date=self.transaction_date,
                description=self.description,
            )
        else:  # selling FVOCI at a loss
            return CompoundEntry(
                debit_accounts={
                    self.bank.chart_of_accounts.cash_account: self.value,
                    self.bank.chart_of_accounts.realized_oci_loss_account: unrealized_oci_loss,
                    self.bank.chart_of_accounts.unrealized_oci_gain_account: unrealized_oci_gain,
                },
                credit_accounts={
                    self.bank.chart_of_accounts.investment_fvoci_account: self.value,
                    self.bank.chart_of_accounts.unrealized_oci_loss_account: unrealized_oci_loss,
                    self.bank.chart_of_accounts.realized_oci_gain_account: unrealized_oci_gain,
                },
                date=self.transaction_date,
                description=self.description,
            )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        unrealized_oci_gain = self.tracker.get_unrealized_gain(self.instrument)
        unrealized_oci_loss = self.tracker.get_unrealized_loss(self.instrument)
        net_gain = unrealized_oci_gain - unrealized_oci_loss
        if net_gain >= 0:  # selling FVOCI at a gain
            return CompoundEntry(
                debit_accounts={
                    self.bank.chart_of_accounts.investment_fvoci_account: self.value,
                    self.bank.chart_of_accounts.realized_oci_gain_account: unrealized_oci_gain,
                    self.bank.chart_of_accounts.unrealized_oci_loss_account: unrealized_oci_loss,
                },
                credit_accounts={
                    self.bank.chart_of_accounts.cash_account: self.value,
                    self.bank.chart_of_accounts.unrealized_oci_gain_account: unrealized_oci_gain,
                    self.bank.chart_of_accounts.realized_oci_loss_account: unrealized_oci_loss,
                },
                date=self.transaction_date,
                description=self.description,
            )
        else:  # selling FVOCI at a loss
            return CompoundEntry(
                debit_accounts={
                    self.bank.chart_of_accounts.investment_fvoci_account: self.value,
                    self.bank.chart_of_accounts.unrealized_oci_loss_account: unrealized_oci_loss,
                    self.bank.chart_of_accounts.realized_oci_gain_account: unrealized_oci_gain,
                },
                credit_accounts={
                    self.bank.chart_of_accounts.cash_account: self.value,
                    self.bank.chart_of_accounts.realized_oci_loss_account: unrealized_oci_loss,
                    self.bank.chart_of_accounts.unrealized_oci_gain_account: unrealized_oci_gain,
                },
                date=self.transaction_date,
                description=self.description,
            )


class SecurityPurchaseFVTPLTransaction(Transaction):
    """Class representing a security purchase FVTPL (Fair Value through Profit or Loss) transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_pay = Cash(value=instrument.value)
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.SECURITY_PURCHASE_TRADING,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.trading_book.add_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.remove_instrument(self.cash_to_pay, Position.LONG)
        self.bank.trading_book.unrealized_pnl_tracker.add_instrument(self.instrument)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.trading_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.add_instrument(self.cash_to_pay, Position.LONG)
        self.bank.trading_book.unrealized_pnl_tracker.remove_instrument(self.instrument)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.asset_fvtpl_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.asset_fvtpl_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )


class SecuritySaleFVTPLTransaction(Transaction):
    """Class representing a security sale FVTPL (Fair Value through Profit or Loss) transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_receive = Cash(value=instrument.value)
        self.tracker = bank.trading_book.unrealized_pnl_tracker
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,
            transaction_type=TransactionType.SECURITY_SALE_TRADING,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.trading_book.remove_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.add_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.trading_book.add_instrument(self.instrument, Position.LONG)
        self.bank.banking_book.remove_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        unrealized_gain = self.tracker.get_unrealized_gain(self.instrument)
        unrealized_loss = self.tracker.get_unrealized_loss(self.instrument)
        net_gain = unrealized_gain - unrealized_loss
        if net_gain >= 0:  # selling FVTPL at a gain
            return CompoundEntry(
                debit_accounts={
                    # 1. record cash received and remove security
                    self.bank.chart_of_accounts.cash_account: self.value,
                    # 2. transfer unrealized gain to realized
                    self.bank.chart_of_accounts.unrealized_trading_gain_account: unrealized_gain,
                    # 3. reverse previously recorded unrealized loss
                    self.bank.chart_of_accounts.realized_trading_loss_account: unrealized_loss,
                },
                credit_accounts={
                    self.bank.chart_of_accounts.asset_fvtpl_account: self.value,  # 1
                    self.bank.chart_of_accounts.realized_trading_gain_account: unrealized_gain,  # 2
                    self.bank.chart_of_accounts.unrealized_trading_loss_account: unrealized_loss,  # 3
                },
                date=self.transaction_date,
                description=self.description,
            )
        else:  # selling FVTPL at a loss
            return CompoundEntry(
                debit_accounts={
                    # 1. record cash received and remove security
                    self.bank.chart_of_accounts.cash_account: self.value,
                    # 2. transfer unrealized loss to realized
                    self.bank.chart_of_accounts.realized_trading_loss_account: unrealized_loss,
                    # 3. reverse previously recorded unrealized gain
                    self.bank.chart_of_accounts.unrealized_trading_gain_account: unrealized_gain,
                },
                credit_accounts={
                    self.bank.chart_of_accounts.asset_fvtpl_account: self.value,  # 1
                    self.bank.chart_of_accounts.unrealized_trading_loss_account: unrealized_loss,  # 2
                    self.bank.chart_of_accounts.realized_trading_gain_account: unrealized_gain,  # 3
                },
                date=self.transaction_date,
                description=self.description,
            )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        unrealized_gain = self.tracker.get_unrealized_gain(self.instrument)
        unrealized_loss = self.tracker.get_unrealized_loss(self.instrument)
        net_gain = unrealized_gain - unrealized_loss
        if net_gain >= 0:  # selling FVTPL at a gain
            return CompoundEntry(
                debit_accounts={
                    self.bank.chart_of_accounts.asset_fvtpl_account: self.value,
                    self.bank.chart_of_accounts.realized_trading_gain_account: unrealized_gain,
                    self.bank.chart_of_accounts.unrealized_trading_loss_account: unrealized_loss,
                },
                credit_accounts={
                    self.bank.chart_of_accounts.cash_account: self.value,
                    self.bank.chart_of_accounts.unrealized_trading_gain_account: unrealized_gain,
                    self.bank.chart_of_accounts.realized_trading_loss_account: unrealized_loss,
                },
                date=self.transaction_date,
                description=self.description,
            )
        else:  # selling FVTPL at a loss
            return CompoundEntry(
                debit_accounts={
                    self.bank.chart_of_accounts.asset_fvtpl_account: self.value,
                    self.bank.chart_of_accounts.unrealized_trading_loss_account: unrealized_loss,
                    self.bank.chart_of_accounts.realized_trading_gain_account: unrealized_gain,
                },
                credit_accounts={
                    self.bank.chart_of_accounts.cash_account: self.value,
                    self.bank.chart_of_accounts.realized_trading_loss_account: unrealized_loss,
                    self.bank.chart_of_accounts.unrealized_trading_gain_account: unrealized_gain,
                },
                date=self.transaction_date,
                description=self.description,
            )


class SecurityMarkToMarketFVTPLTransaction(Transaction):
    """Class representing a security mark-to-market adjustment for FVTPL transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,
        valuation_visitor: ValuationVisitor,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.valuation_visitor = valuation_visitor
        self.old_value = instrument.value
        self.new_value = instrument.value  # will be set to new value after execution
        self.tracker = bank.trading_book.unrealized_pnl_tracker
        self.old_unrealized_trading_gain = self.tracker.get_unrealized_gain(instrument)
        self.new_unrealized_trading_gain = 0.0  # will be set to new value after execution
        self.old_unrealized_trading_loss = self.tracker.get_unrealized_loss(instrument)
        self.new_unrealized_trading_loss = 0.0  # will be set to new value after execution
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,  # no effect
            transaction_type=TransactionType.SECURITY_MARK_TO_MARKET,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.instrument.accept(self.valuation_visitor)
        self.new_value = self.instrument.value
        if (pnl_this_period := self.new_value - self.old_value) >= 0:
            self.new_unrealized_trading_gain = self.old_unrealized_trading_gain + pnl_this_period
            self.tracker.set_unrealized_gain(self.instrument, self.new_unrealized_trading_gain)
        else:
            self.new_unrealized_trading_loss = self.old_unrealized_trading_loss - pnl_this_period
            self.tracker.set_unrealized_loss(self.instrument, self.new_unrealized_trading_loss)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.instrument.value = self.old_value
        self.tracker.set_unrealized_gain(self.instrument, self.old_unrealized_trading_gain)
        self.tracker.set_unrealized_loss(self.instrument, self.old_unrealized_trading_loss)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        # Gain
        if self.new_value >= self.old_value:
            return SimpleEntry(
                debit_account=self.bank.chart_of_accounts.asset_fvtpl_account,
                credit_account=self.bank.chart_of_accounts.unrealized_trading_gain_account,
                value=self.new_value - self.old_value,
                date=self.transaction_date,
                description=self.description,
            )
        # Loss
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.unrealized_trading_loss_account,
            credit_account=self.bank.chart_of_accounts.asset_fvtpl_account,
            value=abs(self.new_value - self.old_value),
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        # Reverse gain
        if self.new_value >= self.old_value:
            return SimpleEntry(
                debit_account=self.bank.chart_of_accounts.unrealized_trading_gain_account,
                credit_account=self.bank.chart_of_accounts.asset_fvtpl_account,
                value=self.new_value - self.old_value,
                date=self.transaction_date,
                description=self.description,
            )
        # Reverse loss
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.asset_fvtpl_account,
            credit_account=self.bank.chart_of_accounts.unrealized_trading_loss_account,
            value=abs(self.new_value - self.old_value),
            date=self.transaction_date,
            description=self.description,
        )


class SecurityMarkToMarketFVOCITransaction(Transaction):
    """Class representing a security mark-to-market adjustment for FVOCI transaction."""

    def __init__(
        self,
        bank: Bank,
        instrument: Instrument,
        valuation_visitor: ValuationVisitor,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.valuation_visitor = valuation_visitor
        self.old_value = instrument.value
        self.new_value = instrument.value  # will be set to new value after execution
        self.tracker = bank.banking_book.unrealized_oci_tracker
        self.old_unrealized_oci_gain = self.tracker.get_unrealized_gain(instrument)
        self.new_unrealized_oci_gain = 0.0  # will be set to new value after execution
        self.old_unrealized_oci_loss = self.tracker.get_unrealized_loss(instrument)
        self.new_unrealized_oci_loss = 0.0  # will be set to new value after execution
        super().__init__(
            bank=bank,
            instrument=instrument,
            value=instrument.value,  # no effect
            transaction_type=TransactionType.SECURITY_MARK_TO_MARKET,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.instrument.accept(self.valuation_visitor)
        self.new_value = self.instrument.value
        if (pnl_this_period := self.new_value - self.old_value) >= 0:
            self.new_unrealized_oci_gain = self.old_unrealized_oci_gain + pnl_this_period
            self.tracker.set_unrealized_gain(self.instrument, self.new_unrealized_oci_gain)
        else:
            self.new_unrealized_oci_loss = self.old_unrealized_oci_loss - pnl_this_period
            self.tracker.set_unrealized_loss(self.instrument, self.new_unrealized_oci_loss)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.instrument.value = self.old_value
        self.tracker.set_unrealized_gain(self.instrument, self.old_unrealized_oci_gain)
        self.tracker.set_unrealized_loss(self.instrument, self.old_unrealized_oci_loss)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        # Gain
        if self.new_value >= self.old_value:
            return SimpleEntry(
                debit_account=self.bank.chart_of_accounts.investment_fvoci_account,
                credit_account=self.bank.chart_of_accounts.unrealized_oci_gain_account,
                value=self.new_value - self.old_value,
                date=self.transaction_date,
                description=self.description,
            )
        # Loss
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.unrealized_oci_loss_account,
            credit_account=self.bank.chart_of_accounts.investment_fvoci_account,
            value=abs(self.new_value - self.old_value),
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        # Reverse gain
        if self.new_value >= self.old_value:
            return SimpleEntry(
                debit_account=self.bank.chart_of_accounts.unrealized_oci_gain_account,
                credit_account=self.bank.chart_of_accounts.investment_fvoci_account,
                value=self.new_value - self.old_value,
                date=self.transaction_date,
                description=self.description,
            )
        # Reverse loss
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.investment_fvoci_account,
            credit_account=self.bank.chart_of_accounts.unrealized_oci_loss_account,
            value=abs(self.new_value - self.old_value),
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

    deposit_by_a_customer = Deposit(value=999999)
    bank.process_transaction(DepositTransaction(bank, deposit_by_a_customer, date))
    bank.process_transaction(DepositWithdrawTransaction(bank, deposit_by_a_customer, date))
    bank.undo_last_transaction()

    bank.process_transaction(InterestPaidOnDepositTransaction(bank, 12312, date))
    report = Report(ledger=bank.ledger, viewer=HTMLStatementViewer(), date=date)

    html_trial_balance = report.print_trial_balance()
    html_income_statement = report.print_income_statement()
    html_balance_sheet = report.print_balance_sheet()

    print(html_trial_balance)
    print(html_income_statement)
    print(html_balance_sheet)


class SecurityInterestEarnedTransaction(Transaction):
    """Class representing a banking book security (HTM or FVOCI) interest earned transaction."""

    def __init__(
        self,
        bank: Bank,
        value: float,
        date: datetime.date | None = None,
        description: str = "",
    ) -> None:
        self.cash_to_receive = Cash(value=value)
        super().__init__(
            bank=bank,
            instrument=self.cash_to_receive,
            value=value,
            transaction_type=TransactionType.SECURITY_INTEREST_EARNED,
            transaction_date=date,
            description=description,
        )

    def execute(self) -> None:
        self.bank.banking_book.add_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.journal_entry)

    def undo(self) -> None:
        self.bank.banking_book.remove_instrument(self.cash_to_receive, Position.LONG)
        self.bank.ledger.post(self.reverse_journal_entry)

    @property
    def journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.cash_account,
            credit_account=self.bank.chart_of_accounts.interest_income_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )

    @property
    def reverse_journal_entry(self) -> JournalEntry:
        return SimpleEntry(
            debit_account=self.bank.chart_of_accounts.interest_income_account,
            credit_account=self.bank.chart_of_accounts.cash_account,
            value=self.value,
            date=self.transaction_date,
            description=self.description,
        )
