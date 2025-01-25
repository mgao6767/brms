"""The Accountant class as a command manager responsible for managing bank and ledger."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from brms.accounting.ledger import Ledger
    from brms.models.bank import Bank
    from brms.models.transaction import Transaction


class Accountant:
    """Accountant class responsible for managing bank and ledger."""

    def __init__(self, bank: "Bank", ledger: "Ledger") -> None:
        """Initialize an accountant."""
        self.bank = bank
        self.ledger = ledger
        self.history: list[Transaction] = []

    def process_transaction(self, transaction: "Transaction") -> bool:
        """Execute the transaction and records it in history."""
        executed = transaction.execute()
        if executed:
            self.history.append(transaction)
        return executed

    def undo_last_transaction(self) -> None:
        """Reverse the last transaction."""
        if not self.history:
            return
        last_transaction = self.history.pop()
        last_transaction.undo()
