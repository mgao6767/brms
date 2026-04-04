"""Tests for EventBus and domain events."""

from dataclasses import dataclass

from brms.core.events import EventBus


@dataclass(frozen=True)
class FakeEvent:
    """A fake event for testing."""

    value: int


def test_subscribe_and_emit() -> None:
    """Emitting an event delivers it to all subscribers for that type."""
    bus = EventBus()
    received: list[FakeEvent] = []
    bus.subscribe(FakeEvent, lambda e: received.append(e))
    bus.emit(FakeEvent(value=42))
    assert received == [FakeEvent(value=42)]  # noqa: S101


def test_multiple_subscribers() -> None:
    """Multiple subscribers for the same event type each receive the event."""
    bus = EventBus()
    a: list[FakeEvent] = []
    b: list[FakeEvent] = []
    bus.subscribe(FakeEvent, lambda e: a.append(e))
    bus.subscribe(FakeEvent, lambda e: b.append(e))
    bus.emit(FakeEvent(value=1))
    assert len(a) == 1  # noqa: S101
    assert len(b) == 1  # noqa: S101


def test_no_cross_event_delivery() -> None:
    """Subscribing to one event type does not receive events of another type."""

    @dataclass(frozen=True)
    class OtherEvent:
        """Another fake event."""

        x: str

    bus = EventBus()
    received: list[OtherEvent] = []
    bus.subscribe(OtherEvent, lambda e: received.append(e))
    bus.emit(FakeEvent(value=1))
    assert received == []  # noqa: S101


def test_unsubscribe() -> None:
    """Unsubscribing a handler prevents it from receiving further events."""
    bus = EventBus()
    received: list[FakeEvent] = []

    def handler(e: FakeEvent) -> None:
        received.append(e)

    bus.subscribe(FakeEvent, handler)
    bus.unsubscribe(FakeEvent, handler)
    bus.emit(FakeEvent(value=1))
    assert received == []  # noqa: S101
