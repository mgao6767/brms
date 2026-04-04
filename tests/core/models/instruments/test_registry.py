"""Tests for InstrumentRegistry."""

# ruff: noqa: S101

import pytest

from brms.core.models.instruments.base import Instrument
from brms.core.models.instruments.registry import InstrumentRegistry


class StubInstrument(Instrument):
    """Minimal concrete instrument used for registry tests."""

    def __init__(self, **kwargs: object) -> None:
        """Store kwargs without calling the ABC __init__."""
        self._data = kwargs

    def accept(self, visitor: object) -> None:
        """No-op visitor acceptance for stub purposes."""


def test_register_and_create() -> None:
    """Registered instrument type can be instantiated via create()."""
    registry = InstrumentRegistry()
    registry.register("stub", StubInstrument)
    inst = registry.create("stub", id="s1", name="test")
    assert isinstance(inst, StubInstrument)


def test_create_unknown_type_raises() -> None:
    """create() raises KeyError for an unregistered type identifier."""
    registry = InstrumentRegistry()
    with pytest.raises(KeyError):
        registry.create("nonexistent")
