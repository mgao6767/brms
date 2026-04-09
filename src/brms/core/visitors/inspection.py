"""Contain inspection visitor class for examining instrument attributes."""

import locale
from typing import TYPE_CHECKING, ClassVar

from brms.core.visitors.base import Visitor

if TYPE_CHECKING:
    from brms.core.models.instruments.base import Instrument
    from brms.core.models.instruments.bonds import CoveredBond, FixedRateBond
    from brms.core.models.instruments.deposits import Cash, Deposit
    from brms.core.models.instruments.equity import CommonEquity
    from brms.core.models.instruments.loans import AmortizingFixedRateLoan, CreditCard, PersonalLoan


class InspectionVisitor(Visitor):
    """A visitor for inspecting instruments."""

    result: ClassVar[dict[str, str | object]] = {}

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

    def visit_cash(self, instrument: "Cash") -> None:
        """Inspect cash."""
        self.result.clear()
        details = self._get_instrument_details(instrument)
        details["Credit Rating"] = "N/A"
        details["Issuer"] = "N/A"
        self.result.update(details)

    def visit_deposit(self, instrument: "Deposit") -> None:
        """Inspect deposit."""
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
        """Inspect an amortizing fixed rate loan."""
        self.result.clear()
        details = self._get_instrument_details(instrument)
        details["Issue Date"] = instrument.issue_date.strftime("%Y-%m-%d")
        details["Maturity Date"] = instrument.maturity_date.strftime("%Y-%m-%d")
        details["Interest Rate"] = f"{instrument.interest_rate * 100}%"
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
