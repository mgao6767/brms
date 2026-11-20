"""AccountingService: maps Transaction dataclasses to journal entries and posts to the Ledger.

Supports reversal (counter-entries) for step-back simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from brms.core.enums import InterestSide, MeasurementBasis, TransactionType, TxMeta
from brms.core.exceptions import ValuationError
from brms.core.models.accounting.journal import CompoundEntry, SimpleEntry

if TYPE_CHECKING:
    from brms.core.models.accounting.accounts import TAccount
    from brms.core.models.accounting.journal import JournalEntry
    from brms.core.models.accounting.ledger import Ledger
    from brms.core.models.transaction import Transaction
    from brms.core.stores.position_store import PositionStore

_CENT = 0.01


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
        """Close positions on maturity, sale, or a loan's final principal payment."""
        if not tx.position_id:
            return
        closing = tx.type in (TransactionType.MATURITY_SETTLEMENT, TransactionType.SECURITY_SALE)
        if closing or dict(tx.metadata).get(TxMeta.FINAL_PAYMENT):
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
            case TransactionType.INTEREST_ACCRUAL:
                return self._interest_accrual(transaction, ledger)
            case TransactionType.INTEREST_SETTLEMENT:
                return self._interest_settlement(transaction, ledger)
            case TransactionType.MARK_TO_MARKET | TransactionType.REVALUATION:
                return self._mark_to_market(transaction, ledger)
            case TransactionType.PRINCIPAL_PAYMENT:
                return self._principal_payment(transaction, ledger)
            case TransactionType.AMORTIZATION:
                return self._amortization(transaction, ledger)
            case TransactionType.MATURITY_SETTLEMENT:
                return self._maturity_settlement(transaction, ledger)
            case TransactionType.PREMIUM_DISCOUNT_AMORTIZATION:
                return self._premium_discount_amortization(transaction, ledger)
            case TransactionType.OPENING_BALANCE:
                return []  # informational — ledger already updated by compound entry
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

    _MEASUREMENT_BASIS_TO_ACCOUNT: ClassVar[dict[MeasurementBasis, str]] = {
        MeasurementBasis.AMORTIZED_COST: "Investment Securities at Amortized Cost",
        MeasurementBasis.FVOCI: "Investment Securities at FVOCI",
        MeasurementBasis.FVTPL: "Assets at FVTPL",
    }

    def _resolve_investment_account(self, tx: Transaction, ledger: Ledger) -> TAccount:
        """Return the investment account for the measurement_basis in *tx* metadata."""
        measurement_basis = dict(tx.metadata).get(TxMeta.MEASUREMENT_BASIS)
        account_name = self._MEASUREMENT_BASIS_TO_ACCOUNT.get(measurement_basis)  # type: ignore[arg-type]
        if account_name is None:
            msg = f"Unknown measurement_basis '{measurement_basis}' in metadata for tx={tx.id}"
            raise ValueError(msg)
        return self._lookup(ledger, account_name)

    def _security_purchase(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """SECURITY_PURCHASE: debit Investment account, credit Cash.

        When ``accrued_interest`` metadata is present (bond bought between
        coupon dates), the dirty price is split::

            Dr  Investment Account              (clean price)
            Dr  Accrued Interest Receivable     (accrued interest purchased)
            Cr  Cash                            (dirty price = clean + accrued)

        This keeps the Receivable in sync with QuantLib's ``accruedAmount``
        so that coupon settlement clears the correct amount.
        """
        investment = self._resolve_investment_account(tx, ledger)
        return self._purchase_entries(tx, ledger, investment, "Security purchase")

    def _purchase_entries(self, tx: Transaction, ledger: Ledger, asset: TAccount, label: str) -> list[JournalEntry]:
        """Dr *asset* (clean cost), Dr Accrued Interest Receivable (accrued bought), Cr Cash (total paid)."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        accrued_str = dict(tx.metadata).get(TxMeta.ACCRUED_INTEREST)
        if accrued_str is not None:
            accrued = float(accrued_str)
            receivable = self._lookup(ledger, "Accrued Interest Receivable")
            return [CompoundEntry(
                debit_accounts={asset: float(tx.amount) - accrued, receivable: accrued},
                credit_accounts={cash: float(tx.amount)},
                date=tx.date,
                description=f"{label} with accrued interest (tx={tx.id})",
            )]
        return [SimpleEntry(
            debit_account=asset,
            credit_account=cash,
            value=float(tx.amount),
            date=tx.date,
            description=f"{label} (tx={tx.id})",
        )]

    def _security_sale(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """SECURITY_SALE at dirty fair value.

        Dr Cash (proceeds); Cr investment (carrying value); Cr Accrued Interest Receivable (accrued
        interest sold). For FVOCI, the position's unrealised gain or loss is then recycled from
        accumulated OCI to Realized OCI Gain / Loss, netting at account level like the marks.
        """
        meta = dict(tx.metadata)
        carrying = float(meta[TxMeta.CARRYING_VALUE])
        accrued = float(meta[TxMeta.ACCRUED_PORTION])
        credit_legs: dict[TAccount, float] = {self._resolve_investment_account(tx, ledger): carrying}
        if accrued:
            credit_legs[self._lookup(ledger, "Accrued Interest Receivable")] = accrued
        entries: list[JournalEntry] = [CompoundEntry(
            debit_accounts={self._lookup(ledger, "Cash and Cash Equivalents"): float(tx.amount)},
            credit_accounts=credit_legs,
            date=tx.date,
            description=f"Security sale (tx={tx.id})",
        )]
        recycled = float(meta.get(TxMeta.RECYCLED_OCI, 0.0))
        if recycled:
            entries.append(self._recycle_oci(tx, ledger, recycled))
        return entries

    def _recycle_oci(self, tx: Transaction, ledger: Ledger, unrealised: float) -> JournalEntry:
        """Move a sold FVOCI position's unrealised gain (+) or loss (-) from OCI to profit or loss."""
        gain = self._lookup(ledger, "Unrealized OCI Gain")
        loss = self._lookup(ledger, "Unrealized OCI Loss")
        size = abs(unrealised)
        if unrealised < 0:
            # Removing a loss raises AOCI: first reduce Unrealized OCI Loss, then credit Gain.
            reduce = min(size, max(loss.balance(), 0.0))
            debits = {self._lookup(ledger, "Realized OCI Loss"): size}
            credit_legs = {loss: reduce, gain: size - reduce}
        else:
            reduce = min(size, max(gain.balance(), 0.0))
            debits = {gain: reduce, loss: size - reduce}
            credit_legs = {self._lookup(ledger, "Realized OCI Gain"): size}
        return CompoundEntry(
            debit_accounts={k: v for k, v in debits.items() if v > 0},
            credit_accounts={k: v for k, v in credit_legs.items() if v > 0},
            date=tx.date,
            description=f"Recycle OCI on sale (tx={tx.id})",
        )

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
        """LOAN_DISBURSEMENT: Dr Loans (clean), Dr Accrued Interest Receivable (accrued bought), Cr Cash."""
        return self._purchase_entries(tx, ledger, self._lookup(ledger, "Loans and Advances"), "Loan disbursement")

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
        """MARK_TO_MARKET / REVALUATION: move the investment by the change in fair value.

        FVTPL: gains credit Unrealized Trading Gain, losses debit Unrealized Trading Loss.
        FVOCI: netted at account level, so at most one of Unrealized OCI Gain and Unrealized
        OCI Loss carries a balance. A loss first reduces Unrealized OCI Gain and only the
        remainder goes to Unrealized OCI Loss; a gain first reduces Unrealized OCI Loss.
        """
        basis = dict(tx.metadata).get(TxMeta.MEASUREMENT_BASIS)
        amount = float(tx.amount)
        if basis == MeasurementBasis.FVTPL:
            asset = self._lookup(ledger, "Assets at FVTPL")
            if amount >= 0:
                debit, credit = asset, self._lookup(ledger, "Unrealized Trading Gain")
            else:
                debit, credit = self._lookup(ledger, "Unrealized Trading Loss"), asset
            return [SimpleEntry(
                debit_account=debit,
                credit_account=credit,
                value=abs(amount),
                date=tx.date,
                description=f"Mark-to-market (tx={tx.id})",
            )]
        if basis == MeasurementBasis.FVOCI:
            return [self._fvoci_mark(tx, ledger, amount)]
        msg = f"Unknown measurement_basis {basis!r} for mark-to-market in tx={tx.id}"
        raise ValueError(msg)

    def _fvoci_mark(self, tx: Transaction, ledger: Ledger, amount: float) -> JournalEntry:
        asset = self._lookup(ledger, "Investment Securities at FVOCI")
        gain = self._lookup(ledger, "Unrealized OCI Gain")
        loss = self._lookup(ledger, "Unrealized OCI Loss")
        size = abs(amount)
        if amount >= 0:
            # Gain: Dr asset; Cr Unrealized OCI Loss (down to zero), then Cr Unrealized OCI Gain.
            reduce = min(size, max(loss.balance(), 0.0))
            debits: dict[TAccount, float] = {asset: size}
            credit_legs = {loss: reduce, gain: size - reduce}
        else:
            # Loss: Dr Unrealized OCI Gain (down to zero), then Dr Unrealized OCI Loss; Cr asset.
            reduce = min(size, max(gain.balance(), 0.0))
            debits = {gain: reduce, loss: size - reduce}
            credit_legs = {asset: size}
        return CompoundEntry(
            debit_accounts={k: v for k, v in debits.items() if v > 0},
            credit_accounts={k: v for k, v in credit_legs.items() if v > 0},
            date=tx.date,
            description=f"Mark-to-market (tx={tx.id})",
        )

    def _premium_discount_amortization(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """PREMIUM_DISCOUNT_AMORTIZATION: move the investment toward face through interest income.

        Discount (positive): Dr investment, Cr Interest Income.
        Premium (negative): Dr Interest Income, Cr investment.
        """
        investment = self._resolve_investment_account(tx, ledger)
        income = self._lookup(ledger, "Interest Income")
        amount = float(tx.amount)
        debit, credit = (investment, income) if amount > 0 else (income, investment)
        return [SimpleEntry(
            debit_account=debit,
            credit_account=credit,
            value=abs(amount),
            date=tx.date,
            description=f"Premium/discount amortisation (tx={tx.id})",
        )]

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
        """AMORTIZATION: debit Cash, credit Loans (or, for a security's paydown, its investment account)."""
        cash = self._lookup(ledger, "Cash and Cash Equivalents")
        if TxMeta.MEASUREMENT_BASIS in dict(tx.metadata):
            loans = self._resolve_investment_account(tx, ledger)
        else:
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
        """MATURITY_SETTLEMENT: Dr Cash face, Cr the position's investment account face.

        By the maturity date the position's carrying value has been brought to face value for
        every measurement basis (amortisation and the final mark), so no gain or loss arises.

        Raises:
            ValuationError: the carrying value in the transaction is not face value.

        """
        face = float(tx.amount)
        carrying_str = dict(tx.metadata).get(TxMeta.CARRYING_VALUE)
        if carrying_str is None or abs(float(carrying_str) - face) > _CENT:
            msg = (
                f"Position {tx.position_id} matures at face {face:.2f} but its carrying value is "
                f"{carrying_str} (tx={tx.id})"
            )
            raise ValuationError(msg)
        return [SimpleEntry(
            debit_account=self._lookup(ledger, "Cash and Cash Equivalents"),
            credit_account=self._resolve_investment_account(tx, ledger),
            value=face,
            date=tx.date,
            description=f"Maturity settlement (tx={tx.id})",
        )]

    def _interest_accrual(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """INTEREST_ACCRUAL: accrue interest without cash movement.

        side=income:  Dr Accrued Interest Receivable / Cr Interest Income
        side=expense: Dr Interest Expense / Cr Interest Payable
        """
        side = dict(tx.metadata).get(TxMeta.SIDE)
        if side == InterestSide.INCOME:
            debit = self._lookup(ledger, "Accrued Interest Receivable")
            credit = self._lookup(ledger, "Interest Income")
            desc = "Interest income accrual"
        elif side == InterestSide.EXPENSE:
            debit = self._lookup(ledger, "Interest Expense")
            credit = self._lookup(ledger, "Interest Payable")
            desc = "Interest expense accrual"
        else:
            msg = f"Unknown side '{side}' for INTEREST_ACCRUAL in tx={tx.id}"
            raise ValueError(msg)
        return [
            SimpleEntry(
                debit_account=debit,
                credit_account=credit,
                value=float(tx.amount),
                date=tx.date,
                description=f"{desc} (tx={tx.id})",
            ),
        ]

    def _interest_settlement(self, tx: Transaction, ledger: Ledger) -> list[JournalEntry]:
        """INTEREST_SETTLEMENT: settle accrued interest with cash movement.

        side=income (coupon received)::

            Dr  Cash                         coupon_amount
            Cr  Accrued Interest Receivable  accrued_portion
            Cr  Interest Income              catch_up (coupon - accrued)

        The catch-up accounts for day count convention differences between
        QL's accruedAmount and the contractual coupon payment.
        If accrued_portion is not provided, uses the full coupon amount
        (two-leg entry, no catch-up).

        side=expense (deposit interest paid)::

            Dr  Interest Payable             amount
            Cr  Cash                         amount
        """
        meta = dict(tx.metadata)
        side = meta.get(TxMeta.SIDE)
        cash = self._lookup(ledger, "Cash and Cash Equivalents")

        if side == InterestSide.EXPENSE:
            return [SimpleEntry(
                debit_account=self._lookup(ledger, "Interest Payable"),
                credit_account=cash,
                value=float(tx.amount),
                date=tx.date,
                description=f"Interest expense settlement (tx={tx.id})",
            )]

        if side == InterestSide.INCOME:
            receivable = self._lookup(ledger, "Accrued Interest Receivable")
            coupon_amount = float(tx.amount)

            accrued_str = meta.get(TxMeta.ACCRUED_PORTION)
            if accrued_str is None:
                msg = f"Income settlement tx={tx.id} carries no accrued portion to clear"
                raise ValueError(msg)
            accrued_portion = float(accrued_str)
            catch_up = coupon_amount - accrued_portion

            if catch_up == 0:
                return [SimpleEntry(
                    debit_account=cash,
                    credit_account=receivable,
                    value=coupon_amount,
                    date=tx.date,
                    description=f"Interest settlement (tx={tx.id})",
                )]

            # Three-leg compound entry
            interest_income = self._lookup(ledger, "Interest Income")
            debits: dict[TAccount, float] = {cash: coupon_amount}
            credit_legs: dict[TAccount, float] = {receivable: accrued_portion}
            if catch_up > 0:
                credit_legs[interest_income] = catch_up
            else:
                debits[interest_income] = -catch_up
            return [CompoundEntry(
                debit_accounts=debits,
                credit_accounts=credit_legs,
                date=tx.date,
                description=f"Interest settlement with day count catch-up (tx={tx.id})",
            )]

        msg = f"Unknown side '{side}' for INTEREST_SETTLEMENT in tx={tx.id}"
        raise ValueError(msg)
