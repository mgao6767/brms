"""Domain exception hierarchy for BRMS."""


class BRMSError(Exception):
    """Base exception for all BRMS domain errors."""


class DataLoadError(BRMSError):
    """Failed to load simulation data (zip, CSV, JSON)."""


class InvalidTransactionError(BRMSError):
    """Transaction violates business rules."""


class InsufficientBalanceError(BRMSError):
    """Account balance insufficient for operation."""


class InstrumentNotFoundError(BRMSError):
    """Referenced instrument does not exist in any book."""


class ScenarioNotAvailableError(BRMSError):
    """No market data available for the requested date."""
