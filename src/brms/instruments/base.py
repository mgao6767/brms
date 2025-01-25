"""Define the base classes and enumerations for financial instruments."""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterator
from enum import Enum, Flag, auto
from typing import Optional

from brms.instruments.visitors.base import Visitor
from brms.models.base import BookType, InstrumentClass


class Instrument(ABC):
    """Base class for financial instruments."""

    def __init__(
        self,
        name: str,
        book_type: BookType | None = None,
        credit_rating: Optional["CreditRating"] = None,
        issuer: Optional["Issuer"] = None,
        parent: Optional["Instrument"] = None,
        instrument_class: Optional["InstrumentClass"] = None,
    ) -> None:
        """Initialize a financial instrument."""
        self.id = uuid.uuid4()
        self.name = name
        self._parent = parent
        self._value: float = 0.0
        self._credit_rating = credit_rating or CreditRating.UNRATED
        self._book_type = book_type or BookType.BANKING_BOOK  # Defaults to banking book.
        self._issuer = issuer or Issuer("unknown", IssuerType.UNSPECIFIED)
        self.instrument_class = instrument_class or InstrumentClass.NA

    @property
    def parent(self) -> Optional["Instrument"]:
        """Get the parent instrument."""
        return self._parent

    @parent.setter
    def parent(self, parent: Optional["Instrument"]) -> None:
        self._parent = parent

    @property
    def book_type(self) -> Optional["BookType"]:
        """Get the book type of the instrument."""
        return self._book_type

    @book_type.setter
    def book_type(self, book_type: "BookType") -> None:
        self._book_type = book_type

    @property
    def value(self) -> float:
        """Get the instrument's value."""
        return self._value

    @value.setter
    def value(self, value: float) -> None:
        self._value = value

    @property
    def credit_rating(self) -> "CreditRating":
        """Get the instrument's credit rating."""
        return self._credit_rating

    @credit_rating.setter
    def credit_rating(self, credit_rating: "CreditRating") -> None:
        self._credit_rating = credit_rating

    @property
    def issuer(self) -> "Issuer":
        """Get the instrument's issuer."""
        return self._issuer

    @issuer.setter
    def issuer(self, issuer: "Issuer") -> None:
        self._issuer = issuer

    def is_composite(self) -> bool:
        """Check if the instrument is composite."""
        return False

    @abstractmethod
    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""


class CompositeInstrument(Instrument):
    """Composite class for financial instruments.

    This class allows for the aggregation of multiple financial instruments into a single composite instrument.
    It can be used to represent a collection of assets, liabilities, or equities for a bank.
    """

    def __init__(
        self,
        name: str,
        book_type: BookType | None = None,
        credit_rating: Optional["CreditRating"] = None,
        issuer: Optional["Issuer"] = None,
        parent: Optional["Instrument"] = None,
    ) -> None:
        """Initialize a composite instrument with an empty list of instruments."""
        super().__init__(name, book_type, credit_rating, issuer, parent)
        self._instruments: list[Instrument] = []

    @property
    def value(self) -> float:
        """Get the instrument's value."""
        return sum(instrument.value for instrument in self._instruments)

    @value.setter
    def value(self, value: float) -> None:
        raise AttributeError("Cannot set value on a composite instrument")

    def add(self, instrument: Instrument) -> None:
        """Add an instrument to the composite."""
        instrument.parent = self
        self._instruments.append(instrument)

    def remove(self, instrument: Instrument) -> None:
        """Remove an instrument from the composite."""
        instrument.parent = None
        self._instruments.remove(instrument)

    def is_composite(self) -> bool:
        """Check if the instrument is composite."""
        return True

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor."""
        for instrument in self._instruments:
            instrument.accept(visitor)

    def __iter__(self) -> Iterator[Instrument]:
        """Return an iterator over the instruments in the composite."""
        return iter(self._instruments)


class CreditRating(Enum):
    """Enumeration of S&P credit ratings."""

    AAA = 1
    AA_PLUS = 2
    AA = 3
    AA_MINUS = 4
    A_PLUS = 5
    A = 6
    A_MINUS = 7
    BBB_PLUS = 8
    BBB = 9
    BBB_MINUS = 10
    BB_PLUS = 11
    BB = 12
    BB_MINUS = 13
    B_PLUS = 14
    B = 15
    B_MINUS = 16
    CCC_PLUS = 17
    CCC = 18
    CCC_MINUS = 19
    CC = 20
    C = 21
    D = 22
    UNRATED = 23

    def __lt__(self, other: "CreditRating") -> bool:
        """Compare if this credit rating is worse than another."""
        if isinstance(other, CreditRating):
            return self.value > other.value
        return NotImplemented

    def __le__(self, other: "CreditRating") -> bool:
        """Compare if this credit rating is worse than or equal to another."""
        if isinstance(other, CreditRating):
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other: "CreditRating") -> bool:
        """Compare if this credit rating is better than another."""
        if isinstance(other, CreditRating):
            return self.value < other.value
        return NotImplemented

    def __ge__(self, other: "CreditRating") -> bool:
        """Compare if this credit rating is better than or equal to another."""
        if isinstance(other, CreditRating):
            return self.value <= other.value
        return NotImplemented

    def is_investment_grade(self) -> bool:
        """Check if the credit rating is investment grade."""
        return self >= CreditRating.BBB_MINUS

    def to_str(self) -> str:
        """Get a custom string representation of the credit rating."""
        return self.name.replace("_PLUS", "+").replace("_MINUS", "-").replace("UNRATED", "Unrated")


class IssuerType(Flag):
    """Enumeration of issuer types."""

    SOVEREIGN = auto()
    PSE = auto()
    MDB = auto()
    BANK = auto()
    CORPORATE = auto()
    SME = auto()
    SECURITIES_FIRM = auto()
    FINANCIAL_INSTITUTION = auto()
    INSURANCE_COMPANY = auto()
    MUTUAL_FUND = auto()
    HEDGE_FUND = auto()
    SUPRANATIONAL = auto()
    MUNICIPAL = auto()
    INDIVIDUAL = auto()
    UNSPECIFIED = auto()

    def to_str(self) -> str:
        """Get a custom string representation of the issuer type."""
        result = []
        if self & IssuerType.SOVEREIGN:
            result.append("Sovereign")
        if self & IssuerType.PSE:
            result.append("Public Sector Entity (PSE)")
        if self & IssuerType.MDB:
            result.append("Multilateral Development Bank (MDB)")
        if self & IssuerType.BANK:
            result.append("Bank")
        if self & IssuerType.CORPORATE:
            result.append("Corporate")
        if self & IssuerType.SME:
            result.append("Small and Medium Enterprise (SME)")
        if self & IssuerType.SECURITIES_FIRM:
            result.append("Securities Firm")
        if self & IssuerType.FINANCIAL_INSTITUTION:
            result.append("Financial Institution")
        if self & IssuerType.INSURANCE_COMPANY:
            result.append("Insurance Company")
        if self & IssuerType.MUTUAL_FUND:
            result.append("Mutual Fund")
        if self & IssuerType.HEDGE_FUND:
            result.append("Hedge Fund")
        if self & IssuerType.SUPRANATIONAL:
            result.append("Supranational")
        if self & IssuerType.MUNICIPAL:
            result.append("Municipal")
        if self & IssuerType.INDIVIDUAL:
            result.append("Individual")
        if self & IssuerType.UNSPECIFIED:
            result.append("Unspecified")
        return "; ".join(result) if result else "Unknown"


class Issuer:
    """Class representing an issuer of financial instruments."""

    def __init__(self, name: str, issuer_type: IssuerType, credit_rating: CreditRating | None = None) -> None:
        """Initialize an issuer with a name and type."""
        self.name = name
        self.issuer_type = issuer_type
        self._credit_rating = credit_rating or CreditRating.UNRATED

    @property
    def credit_rating(self) -> CreditRating:
        """Get the issuer's credit rating."""
        return self._credit_rating

    @credit_rating.setter
    def credit_rating(self, credit_rating: CreditRating) -> None:
        self._credit_rating = credit_rating

    def is_sovereign(self) -> bool:
        """Check if the issuer is sovereign."""
        return self.issuer_type == IssuerType.SOVEREIGN

    def is_PSE(self) -> bool:
        """Check if the issuer is public sector entity (PSE)."""
        return self.issuer_type == IssuerType.PSE

    def is_MDB(self) -> bool:
        """Check if the issuer is multilateral development bank (MDB)."""
        return self.issuer_type == IssuerType.MDB

    def is_bank(self) -> bool:
        """Check if the issuer is depositary institution or bank."""
        return self.issuer_type == IssuerType.BANK

    def is_securities_firm(self) -> bool:
        """Check if the issuer is securities firm."""
        return self.issuer_type == IssuerType.SECURITIES_FIRM

    def is_corporate(self) -> bool:
        """Check if the issuer is corporate."""
        return IssuerType.CORPORATE in self.issuer_type

    def is_SME(self) -> bool:
        """Check if the issuer is SME corporate."""
        return self.is_corporate() and (IssuerType.SME in self.issuer_type)

    def is_individual(self) -> bool:
        """Check if the issuer is individual."""
        return self.issuer_type == IssuerType.INDIVIDUAL
