"""Define the Command and CompositeCommand classes."""

from abc import ABC, abstractmethod

from brms.instruments.base import Instrument
from brms.models.bank import BalanceSheetCategory, Bank


class Command(ABC):
    """Abstract base class for commands."""

    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""

    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""


class CompositeCommand(Command):
    """A composite command that can execute and undo multiple commands."""

    def __init__(self) -> None:
        """Initialize the composite command."""
        self.commands: list[Command] = []

    def add_command(self, command: Command) -> None:
        """Add a command to the composite command."""
        self.commands.append(command)

    def execute(self) -> None:
        """Execute all commands."""
        for command in self.commands:
            command.execute()

    def undo(self) -> None:
        """Undo all commands in reverse order."""
        for command in reversed(self.commands):
            command.undo()


class AddInstrumentCommand(Command):
    """Command to add an instrument to a bank."""

    def __init__(self, bank: Bank, instrument: Instrument, category: BalanceSheetCategory) -> None:
        """Initialize the AddInstrumentCommand with a bank, instrument, and category."""
        self.bank = bank
        self.instrument = instrument
        self.category = category

    def execute(self) -> None:
        """Add the instrument to the bank."""
        match self.category:
            case BalanceSheetCategory.ASSET:
                self.bank.assets.add(self.instrument)
            case BalanceSheetCategory.LIABILITY:
                self.bank.liabilities.add(self.instrument)
            case BalanceSheetCategory.EQUITY:
                self.bank.equities.add(self.instrument)

    def undo(self) -> None:
        """Remove the instrument from the bank."""
        match self.category:
            case BalanceSheetCategory.ASSET:
                self.bank.assets.remove(self.instrument)
            case BalanceSheetCategory.LIABILITY:
                self.bank.liabilities.remove(self.instrument)
            case BalanceSheetCategory.EQUITY:
                self.bank.equities.remove(self.instrument)


class RemoveInstrumentCommand(Command):
    """Command to remove an instrument to a bank."""

    def __init__(self, bank: Bank, instrument: Instrument, category: BalanceSheetCategory) -> None:
        """Initialize the RemoveInstrumentCommand with a bank, instrument, and category."""
        self.bank = bank
        self.instrument = instrument
        self.category = category

    def execute(self) -> None:
        """Remove the instrument from the bank."""
        match self.category:
            case BalanceSheetCategory.ASSET:
                self.bank.assets.remove(self.instrument)
            case BalanceSheetCategory.LIABILITY:
                self.bank.liabilities.remove(self.instrument)
            case BalanceSheetCategory.EQUITY:
                self.bank.equities.remove(self.instrument)

    def undo(self) -> None:
        """Add the instrument back to the bank."""
        match self.category:
            case BalanceSheetCategory.ASSET:
                self.bank.assets.add(self.instrument)
            case BalanceSheetCategory.LIABILITY:
                self.bank.liabilities.add(self.instrument)
            case BalanceSheetCategory.EQUITY:
                self.bank.equities.add(self.instrument)
