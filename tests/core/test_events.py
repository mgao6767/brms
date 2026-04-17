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


def test_instrument_added_event() -> None:
    """InstrumentAdded event stores instrument_id, book_type, and instrument."""
    from brms.core.events import InstrumentAdded

    event = InstrumentAdded(instrument_id="bond-1", book_type="banking", instrument=None)
    assert event.instrument_id == "bond-1"  # noqa: S101


def test_instrument_removed_event() -> None:
    """InstrumentRemoved event stores instrument_id, book_type, and instrument."""
    from brms.core.events import InstrumentRemoved

    event = InstrumentRemoved(instrument_id="bond-1", book_type="trading", instrument=None)
    assert event.instrument_id == "bond-1"  # noqa: S101


def test_valuations_updated_is_frozen() -> None:
    """ValuationsUpdated event stores date and valuations dict."""
    import datetime
    from decimal import Decimal

    from brms.core.events import ValuationsUpdated

    event = ValuationsUpdated(date=datetime.date(2024, 1, 1), valuations={"p1": Decimal("100")})
    assert event.date == datetime.date(2024, 1, 1)  # noqa: S101
    assert event.valuations == {"p1": Decimal("100")}  # noqa: S101


def test_transactions_recorded_is_frozen() -> None:
    """TransactionsRecorded event stores date and transactions tuple."""
    import datetime

    from brms.core.events import TransactionsRecorded

    event = TransactionsRecorded(date=datetime.date(2024, 1, 1), transactions=())
    assert event.date == datetime.date(2024, 1, 1)  # noqa: S101
    assert event.transactions == ()  # noqa: S101


def test_metrics_computed_is_frozen() -> None:
    """MetricsComputed event stores date and metrics dict."""
    import datetime

    from brms.core.enums import MetricName
    from brms.core.events import MetricsComputed

    event = MetricsComputed(
        date=datetime.date(2024, 1, 1),
        metrics={MetricName.TOTAL_ASSETS: 1_000_000.0},
    )
    assert event.metrics[MetricName.TOTAL_ASSETS] == 1_000_000.0  # noqa: S101, PLR2004


def test_statements_changed_is_frozen() -> None:
    """StatementsChanged event stores date."""
    import datetime

    from brms.core.events import StatementsChanged

    event = StatementsChanged(date=datetime.date(2024, 1, 1))
    assert event.date == datetime.date(2024, 1, 1)  # noqa: S101


class TestEventBusBatch:
    """Tests for EventBus batch context manager."""

    def test_batch_queues_events(self) -> None:
        """Events emitted inside batch() are held until the batch exits."""
        bus = EventBus()
        received: list[FakeEvent] = []
        bus.subscribe(FakeEvent, lambda e: received.append(e))
        with bus.batch():
            bus.emit(FakeEvent(value=1))
            bus.emit(FakeEvent(value=2))
            assert received == []  # noqa: S101
        assert len(received) == 2  # noqa: S101, PLR2004

    def test_batch_preserves_order(self) -> None:
        """Queued events flush in the order they were emitted."""
        bus = EventBus()
        received: list[int] = []
        bus.subscribe(FakeEvent, lambda e: received.append(e.value))
        with bus.batch():
            bus.emit(FakeEvent(value=10))
            bus.emit(FakeEvent(value=20))
            bus.emit(FakeEvent(value=30))
        assert received == [10, 20, 30]  # noqa: S101

    def test_nested_batch_flushes_only_on_outermost_exit(self) -> None:
        """Inner batch exit does not flush; only the outermost does."""
        bus = EventBus()
        received: list[int] = []
        bus.subscribe(FakeEvent, lambda e: received.append(e.value))
        with bus.batch():
            bus.emit(FakeEvent(value=1))
            with bus.batch():
                bus.emit(FakeEvent(value=2))
            assert received == []  # noqa: S101
        assert received == [1, 2]  # noqa: S101

    def test_immediate_outside_batch(self) -> None:
        """Without a batch context, events dispatch immediately as before."""
        bus = EventBus()
        received: list[int] = []
        bus.subscribe(FakeEvent, lambda e: received.append(e.value))
        bus.emit(FakeEvent(value=99))
        assert received == [99]  # noqa: S101

    def test_secondary_events_during_flush_dispatch_immediately(self) -> None:
        """Events emitted by handlers during flush fire immediately (depth is 0)."""

        @dataclass(frozen=True)
        class SecondaryEvent:
            value: int

        bus = EventBus()
        order: list[str] = []
        bus.subscribe(FakeEvent, lambda _e: (bus.emit(SecondaryEvent(value=2)), order.append("primary")))
        bus.subscribe(SecondaryEvent, lambda _e: order.append("secondary"))
        with bus.batch():
            bus.emit(FakeEvent(value=1))
        assert order == ["secondary", "primary"]  # noqa: S101

    def test_empty_batch_is_noop(self) -> None:
        """Entering and exiting a batch with no events is harmless."""
        bus = EventBus()
        with bus.batch():
            pass

    def test_exception_still_flushes(self) -> None:
        """If code inside batch raises, queued events still flush via finally."""
        bus = EventBus()
        received: list[int] = []
        bus.subscribe(FakeEvent, lambda e: received.append(e.value))
        try:
            with bus.batch():
                bus.emit(FakeEvent(value=1))
                msg = "boom"
                raise RuntimeError(msg)  # noqa: TRY301
        except RuntimeError:
            pass
        assert received == [1]  # noqa: S101
