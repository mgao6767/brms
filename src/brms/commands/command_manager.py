"""Provide the CommandManager class to manage command execution, undo, and redo."""

from .command import Command


class CommandManager:
    """Manage the execution, undo, and redo of commands."""

    def __init__(self) -> None:
        """Initialize the CommandManager with empty history and redo stack."""
        self.history: list[Command] = []
        self.redo_stack: list[Command] = []

    def execute_command(self, command: Command) -> None:
        """Execute a command and add it to the history."""
        command.execute()
        self.history.append(command)
        self.redo_stack.clear()

    def undo(self) -> None:
        """Undo the last command."""
        if self.history:
            command = self.history.pop()
            command.undo()
            self.redo_stack.append(command)

    def redo(self) -> None:
        """Redo the last undone command."""
        if self.redo_stack:
            command = self.redo_stack.pop()
            command.execute()
            self.history.append(command)
