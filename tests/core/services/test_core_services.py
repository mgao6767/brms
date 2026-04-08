"""Tests for CoreServices dataclass and factory."""
# ruff: noqa: S101

from brms.core.services import CoreServices, build_core_services


def test_core_services_is_frozen() -> None:
    services = build_core_services()
    assert isinstance(services, CoreServices)
    assert services.event_bus is not None
    assert services.simulation_service is not None
    assert services.bank is not None


def test_build_core_services_returns_wired_simulation_service() -> None:
    services = build_core_services()
    assert services.simulation_service.bank is services.bank
    assert services.simulation_service.event_bus is services.event_bus
