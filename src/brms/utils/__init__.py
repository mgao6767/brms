"""Module for utility functions and classes."""

import datetime
import time
from abc import ABC, abstractmethod
from functools import wraps

import QuantLib as ql
from PySide6.QtCore import QDate


class Observable:
    """Base class for observable components."""

    def __init__(self) -> None:
        """Initialize the Observable with an empty list of observers."""
        self._observers: list[Observer] = []

    def add_observer(self, observer: "Observer") -> None:
        """Add an observer to the list of observers."""
        self._observers.append(observer)

    def remove_observer(self, observer: "Observer") -> None:
        """Remove an observer from the list of observers."""
        self._observers.remove(observer)

    def notify_observers(self) -> None:
        """Notify all observers about a change."""
        for observer in self._observers:
            observer.update(self)


class Observer(ABC):
    """Base class for observers."""

    @abstractmethod
    def update(self, observable: Observable) -> None:
        """Update when a observable notifies of a change."""


def timeit(func):
    @wraps(func)
    def timed(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {(end_time - start_time)*1000:.4f} ms")
        return result

    return timed


def qdate_to_qldate(date: QDate) -> ql.Date:
    """Convert a QDate object to a ql.Date object.

    Args:
        date (QDate): The QDate object to be converted.

    Returns:
        ql.Date: The converted ql.Date object.

    """
    assert isinstance(date, QDate)
    return ql.Date(date.day(), date.month(), date.year())


def qldate_to_pydate(date: ql.Date) -> datetime.date:
    """Convert a QuantLib date to a Python date.

    Args:
        date (ql.Date): The QuantLib date to be converted.

    Returns:
        datetime.date: The equivalent Python date.

    """
    assert isinstance(date, ql.Date)
    return datetime.date(date.year(), date.month(), date.dayOfMonth())


def pydate_to_qldate(date: datetime.date) -> ql.Date:
    """Convert a Python date object to a QuantLib date object.

    Args:
        date (datetime.date): The Python date object to be converted.

    Returns:
        ql.Date: The corresponding QuantLib date object.

    """
    assert isinstance(date, datetime.date)
    return ql.Date(date.day, date.month, date.year)


def qldate_to_string(date: ql.Date) -> str:
    """Convert a QuantLib date to a string.

    Args:
        date (ql.Date): The QuantLib date to be converted.

    Returns:
        "YYYY/MM/DD"

    """
    assert isinstance(date, ql.Date)
    return f"{date.year()}/{date.month()}/{date.dayOfMonth()}"


def pydate_to_qdate(date: datetime.date) -> QDate:
    """Convert a Python date object to a QDate object.

    Args:
        date (datetime.date): The Python date object to be converted.

    Returns:
        QDate: The corresponding QDate object.

    """
    assert isinstance(date, datetime.date)
    return QDate(date.year, date.month, date.day)
