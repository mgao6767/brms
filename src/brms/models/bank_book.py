"""Contains the BankBook class and its derivatives, BankingBook and TradingBook."""

from enum import Enum, auto

from brms.instruments.base import CompositeInstrument, Instrument
from brms.instruments.cash import Cash
from brms.instruments.visitors.base import Visitor
from brms.models.base import BookType


class Position(Enum):
    """Enumeration for position types (LONG or SHORT)."""

    LONG = auto()
    SHORT = auto()


class UnrealizedGainLossTracker:
    """A class to track unrealized gain/loss for FVOCI or FVTPL instruments."""

    def __init__(self) -> None:
        self.unrealized_pnl: dict[Instrument, float] = {}
        self.tracked: set[Instrument] = set()

    def set_unrealized_gain_loss(self, instrument: Instrument, unrealized_gain_loss: float) -> None:
        """Set the unrealized gain/loss for a given instrument."""
        self.unrealized_pnl[instrument] = unrealized_gain_loss
        self.tracked.add(instrument)

    def get_unrealized_gain_loss(self, instrument: Instrument) -> float:
        """Get the unrealized gain/loss for a given instrument."""
        return self.unrealized_pnl.get(instrument, 0.0)

    def add_instrument(self, instrument: Instrument) -> None:
        """Add an instrument to the tracker."""
        if instrument not in self.tracked:
            self.set_unrealized_gain_loss(instrument, unrealized_gain_loss=0.0)

    def remove_instrument(self, instrument: Instrument) -> None:
        """Remove an instrument from the tracker."""
        if instrument in self.unrealized_pnl:
            self.tracked.remove(instrument)


class UnrealizedOCIGainLossTracker(UnrealizedGainLossTracker):
    """A class to track unrealized OCI gain/loss for FVOCI instruments."""


class UnrealizedTradingGainLossTracker(UnrealizedGainLossTracker):
    """A class to track unrealized trading gain/loss for FVTPL instruments."""


class BankBook:
    """A class to represent a bank's banking or trading book."""

    def __init__(self, book_type: BookType) -> None:
        """Initialize a BankBook instance.

        :param book_type: The type of the book (banking or trading).
        """
        self.book_type = book_type
        self.long_exposure = CompositeInstrument("Exposure (Long)", book_type)
        self.short_exposure = CompositeInstrument("Exposure (Short)", book_type)

    def add_instrument(self, instrument: Instrument, position: Position) -> None:
        """Add an instrument to the bank book."""
        match position:
            case Position.LONG:
                self.long_exposure.add(instrument)
            case Position.SHORT:
                self.short_exposure.add(instrument)

    def remove_instrument(self, instrument: Instrument, position: Position) -> None:
        """Remove an instrument from the bank book."""
        match position:
            case Position.LONG:
                if instrument in self.long_exposure:
                    self.long_exposure.remove(instrument)
                else:
                    raise ValueError("Instrument to remove doesn't exist in long exposure.")
            case Position.SHORT:
                if instrument in self.short_exposure:
                    self.short_exposure.remove(instrument)
                else:
                    raise ValueError("Instrument to remove doesn't exist in short exposure.")

    def accept(self, visitor: Visitor) -> None:
        """Accept a visitor to process the instruments in the book."""
        for instrument in self.long_exposure:
            instrument.accept(visitor)
        for instrument in self.short_exposure:
            instrument.accept(visitor)


class BankingBook(BankBook):
    """A class to represent a banking book."""

    unrealized_oci_tracker = UnrealizedOCIGainLossTracker()

    def __init__(self) -> None:
        """Initialize a BankingBook instance."""
        super().__init__(book_type=BookType.BANKING_BOOK)

    def add_instrument(self, instrument: Instrument, position: Position) -> None:
        """Add an instrument to the bank book."""
        if isinstance(instrument, Cash):
            for existing_instrument in self.long_exposure:
                if isinstance(existing_instrument, Cash):
                    existing_instrument.value += instrument.value
                    return
        super().add_instrument(instrument, position)

    def remove_instrument(self, instrument: Instrument, position: Position) -> None:
        """Remove an instrument from the bank book."""
        if isinstance(instrument, Cash):
            for existing_instrument in self.long_exposure:
                if isinstance(existing_instrument, Cash):
                    existing_instrument.value -= instrument.value
                return
        super().remove_instrument(instrument, position)

    @property
    def cash(self) -> Cash:
        """Retrieve the Cash instrument from the long exposure.

        :return: The Cash instrument in the long exposure.
        :raises ValueError: If no Cash instrument is found.
        """
        for instrument in self.long_exposure:
            if isinstance(instrument, Cash):
                return instrument
        error_message = "No Cash instrument found in the long exposure."
        raise ValueError(error_message)


class TradingBook(BankBook):
    """A class to represent a trading book."""

    unrealized_pnl_tracker = UnrealizedTradingGainLossTracker()

    def __init__(self) -> None:
        """Initialize a TradingBook instance."""
        super().__init__(book_type=BookType.TRADING_BOOK)
