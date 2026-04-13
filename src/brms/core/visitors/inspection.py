"""Inspection visitors for examining instrument and transaction attributes."""

from __future__ import annotations

import locale
from typing import TYPE_CHECKING, Any

from brms.core.visitors.base import Visitor

if TYPE_CHECKING:
    from brms.core.models.accounting.journal import Journal
    from brms.core.models.bank import Bank
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.instruments.bonds import CoveredBond, FixedRateBond
    from brms.core.models.instruments.deposits import Cash, Deposit
    from brms.core.models.instruments.equity import CommonEquity
    from brms.core.models.instruments.loans import AmortizingFixedRateLoan, CreditCard, PersonalLoan
    from brms.core.models.transaction import Transaction


class InspectionVisitor:
    """Base class for inspection visitors. Owns the result dict and shared helpers."""

    def __init__(self) -> None:
        """Initialize with an empty result dict."""
        self._result: dict[str, Any] = {}

    def get_result(self) -> dict[str, Any]:
        """Return the result of the inspection."""
        return dict(self._result)

    @staticmethod
    def _get_instrument_details(instrument: Instrument) -> dict[str, Any]:
        """Return a dictionary of the instrument's common attributes."""
        return {
            "ID": str(instrument.id),
            "Name": instrument.name,
            "Book Type": None if instrument.book_type is None else instrument.book_type.value,
            "Credit Rating": instrument.credit_rating.to_str(),
            "Class": instrument.measurement_basis.name,
            "Issuer": {
                "Name": instrument.issuer.name,
                "Issuer Type": instrument.issuer.issuer_type.to_str(),
                "Credit Rating": instrument.issuer.credit_rating.to_str(),
            },
        }


class InstrumentInspectionVisitor(InspectionVisitor, Visitor):
    """Visitor for inspecting instrument attributes."""

    def visit_cash(self, instrument: Cash) -> None:
        """Inspect cash."""
        self._result.clear()
        details = self._get_instrument_details(instrument)
        details["Credit Rating"] = "N/A"
        details["Issuer"] = "N/A"
        self._result.update(details)

    def visit_deposit(self, instrument: Deposit) -> None:
        """Inspect deposit."""
        self._result.clear()
        details = self._get_instrument_details(instrument)
        details["Credit Rating"] = "N/A"
        details["Issuer"] = "Bank Customer"
        self._result.update(details)

    def visit_common_equity(self, instrument: CommonEquity) -> None:
        """Inspect common equity."""
        self._result.clear()
        details = self._get_instrument_details(instrument)
        self._result.update(details)

    def visit_fixed_rate_bond(self, instrument: FixedRateBond) -> None:
        """Inspect a fixed rate bond."""
        self._result.clear()
        details = self._get_instrument_details(instrument)
        details["Issue Date"] = instrument.issue_date.strftime("%Y-%m-%d")
        details["Maturity Date"] = instrument.maturity_date.strftime("%Y-%m-%d")
        self._result.update(details)

    def visit_amortizing_fixed_rate_loan(self, instrument: AmortizingFixedRateLoan) -> None:
        """Inspect an amortizing fixed rate loan."""
        self._result.clear()
        details = self._get_instrument_details(instrument)
        details["Issue Date"] = instrument.issue_date.strftime("%Y-%m-%d")
        details["Maturity Date"] = instrument.maturity_date.strftime("%Y-%m-%d")
        details["Interest Rate"] = f"{instrument.interest_rate * 100}%"
        details["Face Value"] = locale.currency(instrument.face_value, grouping=True)
        self._result.update(details)

    def visit_covered_bond(self, instrument: CoveredBond) -> None:
        """Inspect a covered bond."""
        raise NotImplementedError

    def visit_personal_loan(self, instrument: PersonalLoan) -> None:
        """Inspect a personal loan."""
        raise NotImplementedError

    def visit_credit_card(self, instrument: CreditCard) -> None:
        """Inspect a credit card."""
        raise NotImplementedError


class TransactionInspectionVisitor(InspectionVisitor):
    """Visitor for inspecting transaction details, including related position, instrument, and journal entries."""

    def __init__(self, bank: Bank, journal: Journal) -> None:
        """Initialize with bank and journal for resolving related objects."""
        super().__init__()
        self._bank = bank
        self._journal = journal
        self._instrument_inspector = InstrumentInspectionVisitor()

    def visit_transaction(self, transaction: Transaction) -> None:
        """Inspect a transaction and its related objects."""
        self._result.clear()
        self._result["Transaction"] = self._inspect_tx_fields(transaction)
        if transaction.position_id:
            self._result["Position"] = self._inspect_position(transaction.position_id)
        if transaction.instrument_id:
            self._result["Instrument"] = self._inspect_instrument(transaction.instrument_id)
        je = self._inspect_journal_entries(transaction.id)
        if je:
            self._result["Journal Entry"] = je

    def _inspect_tx_fields(self, transaction: Transaction) -> dict[str, Any]:
        """Extract core transaction fields."""
        details: dict[str, Any] = {
            "ID": transaction.id,
            "Type": transaction.type.name.replace("_", " ").title(),
            "Date": str(transaction.date),
            "Amount": f"{transaction.amount:,.2f}",
        }
        if transaction.description:
            details["Description"] = transaction.description
        if transaction.metadata:
            details["Metadata"] = {k: str(v) for k, v in transaction.metadata}
        return details

    def _inspect_position(self, position_id: str) -> dict[str, Any]:
        """Look up and format position details."""
        try:
            position = self._bank.positions.get(position_id)
        except KeyError:
            return {"ID": position_id, "Status": "Not Found"}
        return {
            "ID": position.id,
            "Book Type": position.book_type.value,
            "Measurement Basis": position.measurement_basis.name,
            "Side": position.side.name,
            "Acquisition Date": str(position.acquisition_date),
            "Acquisition Cost": f"{position.acquisition_cost:,.2f}",
            "Status": position.status.name,
        }

    def _inspect_instrument(self, instrument_id: str) -> dict[str, Any]:
        """Look up instrument and delegate to InstrumentInspectionVisitor."""
        try:
            instrument = self._bank.instruments.get(instrument_id)
        except KeyError:
            return {"ID": instrument_id, "Status": "Not Found"}
        instrument.accept(self._instrument_inspector)
        return self._instrument_inspector.get_result()

    def _inspect_journal_entries(self, tx_id: str) -> dict[str, Any]:
        """Find and format journal entries linked to a transaction."""
        marker = f"tx={tx_id}"
        entries = [e for e in self._journal.entries if marker in e.description]
        if not entries:
            return {}
        je_details: dict[str, Any] = {}
        for i, entry in enumerate(entries):
            entry_key = f"Entry {i + 1}" if len(entries) > 1 else "Entry"
            desc = entry.description.split(" (tx=")[0] if " (tx=" in entry.description else entry.description
            entry_dict: dict[str, Any] = {"Description": desc}
            if entry.date:
                entry_dict["Date"] = str(entry.date)
            for acct, amt in entry.debit_account_value_pairs():
                entry_dict[f"Dr {acct.name}"] = f"{amt:,.2f}"
            for acct, amt in entry.credit_account_value_pairs():
                entry_dict[f"Cr {acct.name}"] = f"{amt:,.2f}"
            je_details[entry_key] = entry_dict
        return je_details
