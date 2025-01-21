"""Contains the base controller for the BRMS application."""

from abc import ABC, abstractmethod


class BRMSController(ABC):
    """The base controller for the BRMS application."""

    @abstractmethod
    def connect_signals(self) -> None:
        """Connect signals and slots."""
