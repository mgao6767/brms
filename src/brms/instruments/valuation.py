"""Contain valuation visitor classes for banking and trading books."""

from abc import ABC, abstractmethod


class ValuationVisitor(ABC):
    """Abstract base class for valuation visitors."""


class BankingBookValuationVisitor(ValuationVisitor):
    """A visitor for banking book valuation."""


class TradingBookValuationVistor(ValuationVisitor):
    """A visitor for trading book valuation."""
