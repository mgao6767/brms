"""Define the `Bank` class."""

from brms.instruments.base import CompositeInstrument


class AssetComposite(CompositeInstrument):
    """Composite class for assets."""


class LiabilityComposite(CompositeInstrument):
    """Composite class for liabilities."""


class EquityComposite(CompositeInstrument):
    """Composite class for equities."""


class Bank:
    """Class representing a bank with assets, liabilities, and equities."""

    def __init__(self) -> None:
        """Initialize the Bank with assets, liabilities, and equities."""
        self.assets = AssetComposite(name="Assets")
        self.liabilities = LiabilityComposite(name="Liabilities")
        self.equities = EquityComposite(name="Equities")
