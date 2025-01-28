"""Contain valuation visitor classes for banking and trading books."""

from typing import TYPE_CHECKING

from brms.accounting.statement_viewer import locale
from brms.instruments.visitors import Visitor

if TYPE_CHECKING:
    from brms.instruments.amortizing_fixed_rate_loan import AmortizingFixedRateLoan
    from brms.instruments.base import Instrument
    from brms.instruments.cash import Cash
    from brms.instruments.common_equity import CommonEquity
    from brms.instruments.covered_bond import CoveredBond
    from brms.instruments.credit_card import CreditCard
    from brms.instruments.deposit import Deposit
    from brms.instruments.fixed_rate_bond import FixedRateBond
    from brms.instruments.mock import MockInstrument
    from brms.instruments.personal_loan import PersonalLoan


class InspectionVisitor(Visitor):
    """A visitor for inspecting instruments."""

    result: dict[str, str | object] = {}

    def get_result(self) -> dict[str, str | object]:
        """Return the result of the inspection."""
        return self.result

    @staticmethod
    def _get_instrument_details(instrument: "Instrument") -> dict:
        """Return a dictionary of the instrument's attributes."""
        return {
            "ID": str(instrument.id),
            "Name": instrument.name,
            "Book Type": None if instrument.book_type is None else instrument.book_type.value,
            "Credit Rating": instrument.credit_rating.to_str(),
            "Class": instrument.instrument_class.value,
            "Issuer": {
                "Name": instrument.issuer.name,
                "Issuer Type": instrument.issuer.issuer_type.to_str(),
                "Credit Rating": instrument.issuer.credit_rating.to_str(),
            },
        }

    def visit_mock_instrument(self, instrument: "MockInstrument") -> None:
        """Inspect mock instrument."""
        self.result.clear()
        details = self._get_instrument_details(instrument)
        details["Credit Rating"] = "N/A"
        details["Issuer"] = "N/A"
        self.result.update(details)

    def visit_cash(self, instrument: "Cash") -> None:
        """Inspect cash."""
        self.result.clear()
        details = self._get_instrument_details(instrument)
        details["Credit Rating"] = "N/A"
        details["Issuer"] = "N/A"
        self.result.update(details)

    def visit_deposit(self, instrument: "Deposit") -> None:
        """Visit deposit."""
        self.result.clear()
        details = self._get_instrument_details(instrument)
        details["Credit Rating"] = "N/A"
        details["Issuer"] = "Bank Customer"
        self.result.update(details)

    def visit_common_equity(self, instrument: "CommonEquity") -> None:
        """Inspect common equity."""
        self.result.clear()
        details = self._get_instrument_details(instrument)
        self.result.update(details)

    def visit_fixed_rate_bond(self, instrument: "FixedRateBond") -> None:
        """Inspect a fixed rate bond."""
        self.result.clear()
        details = self._get_instrument_details(instrument)
        details["Issue Date"] = instrument.issue_date.strftime("%Y-%m-%d")
        details["Maturity Date"] = instrument.maturity_date.strftime("%Y-%m-%d")
        self.result.update(details)

    def visit_amortizing_fixed_rate_loan(self, instrument: "AmortizingFixedRateLoan") -> None:
        """Inspect an amortizing fixed rate bond."""
        self.result.clear()
        details = self._get_instrument_details(instrument)
        details["Issue Date"] = instrument.issue_date.strftime("%Y-%m-%d")
        details["Maturity Date"] = instrument.maturity_date.strftime("%Y-%m-%d")
        details["Interest Rate"] = f"{instrument.interest_rate*100}%"
        details["Face Value"] = locale.currency(instrument.face_value, grouping=True)
        self.result.update(details)

    def visit_covered_bond(self, instrument: "CoveredBond") -> None:
        """Inspect a covered bond."""
        raise NotImplementedError

    def visit_personal_loan(self, instrument: "PersonalLoan") -> None:
        """Inspect a personal loan."""
        raise NotImplementedError

    def visit_credit_card(self, instrument: "CreditCard") -> None:
        """Inspect a credit card."""
        raise NotImplementedError
