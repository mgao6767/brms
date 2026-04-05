"""Other off-balance-sheet and miscellaneous instrument classes for the core domain model."""

from brms.core.enums import InstrumentType
from brms.core.models.instruments.base import Instrument


class Commitment(Instrument):
    """A class to represent commitments."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize a commitment."""
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.instrument_type = InstrumentType.COMMITMENT

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        raise NotImplementedError


class LetterOfCredit(Instrument):
    """A class to represent letter of credit instruments."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize a letter of credit."""
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.instrument_type = InstrumentType.LETTER_OF_CREDIT

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        raise NotImplementedError


class StandByLetterOfCredit(LetterOfCredit):
    """A class to represent standby letter of credit instruments."""


class TradeLetterOfCredit(LetterOfCredit):
    """A class to represent trade letter of credit instruments."""


class RepurchaseAgreement(Instrument):
    """A class to represent repo instruments."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize a repurchase agreement."""
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.instrument_type = InstrumentType.REPURCHASE_AGREEMENT

    def accept(self, visitor: object) -> None:
        """Accept a visitor."""
        raise NotImplementedError
