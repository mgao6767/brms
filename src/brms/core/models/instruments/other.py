"""Other off-balance-sheet and miscellaneous instrument classes for the core domain model."""

from brms.core.models.instruments.base import Instrument


class Commitment(Instrument):
    """A class to represent commitments."""

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        raise NotImplementedError


class LetterOfCredit(Instrument):
    """A class to represent letter of credit instruments."""

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        raise NotImplementedError


class StandByLetterOfCredit(Instrument):
    """A class to represent standby letter of credit instruments."""

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        raise NotImplementedError


class TradeLetterOfCredit(Instrument):
    """A class to represent trade letter of credit instruments."""

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        raise NotImplementedError


class RepurchaseAgreement(Instrument):
    """A class to represent repo instruments."""

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        raise NotImplementedError
