"""Define the Command and CompositeCommand classes."""

from abc import ABC, abstractmethod


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
