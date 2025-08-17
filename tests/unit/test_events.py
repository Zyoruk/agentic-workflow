"""Test the event system functionality."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from agentic_workflow.events import (
    Event,
    EventBus,
    EventManager,
    EventType,
    emit_agent_started,
    emit_event,
    event_manager,
    subscribe_to_events,
)


class TestEvent:
    """Test Event dataclass."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            event_type="test.event",
            source="test_source",
            timestamp=datetime.now(UTC),
            data={"key": "value"},
        )

        assert event.event_type == "test.event"
        assert event.source == "test_source"
        assert event.data == {"key": "value"}

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = Event(
            event_type="test.event",
            source="test_source",
            timestamp=datetime.now(UTC),
            data={"key": "value"},
        )

        result = event.to_dict()
        assert isinstance(result, dict)
        assert result["event_type"] == "test.event"
        assert result["source"] == "test_source"
        assert "timestamp" in result
        assert result["data"] == {"key": "value"}

    def test_event_from_dict(self):
        """Test creating event from dictionary."""
        data = {
            "event_type": "test.event",
            "source": "test_source",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {"key": "value"},
        }

        event = Event.from_dict(data)
        assert event.event_type == "test.event"
        assert event.source == "test_source"
        assert isinstance(event.timestamp, datetime)


class TestEventBus:
    """Test EventBus functionality."""

    def test_subscribe_and_unsubscribe(self):
        """Test subscribing and unsubscribing."""
        bus = EventBus()
        handler = Mock()

        bus.subscribe("test.event", handler)
        assert "test.event" in bus._subscribers
        assert handler in bus._subscribers["test.event"]

        bus.unsubscribe("test.event", handler)
        assert handler not in bus._subscribers["test.event"]

    @pytest.mark.asyncio
    async def test_publish_event(self):
        """Test publishing an event."""
        bus = EventBus()
        handler = Mock()

        bus.subscribe("test.event", handler)

        event = Event(
            event_type="test.event",
            source="test_source",
            timestamp=datetime.now(UTC),
            data={"test": True},
        )

        await bus.publish(event)

        handler.assert_called_once_with(event)
        assert len(bus._event_history) == 1
        assert bus._event_history[0] == event

    @pytest.mark.asyncio
    async def test_async_handler(self):
        """Test async event handler."""
        bus = EventBus()
        handler = AsyncMock()

        bus.subscribe("test.event", handler)

        event = Event(
            event_type="test.event",
            source="test_source",
            timestamp=datetime.now(UTC),
            data={"test": True},
        )

        await bus.publish(event)

        handler.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self):
        """Test wildcard event subscription."""
        bus = EventBus()
        handler = Mock()

        bus.subscribe("*", handler)

        event = Event(
            event_type="any.event",
            source="test_source",
            timestamp=datetime.now(UTC),
            data={"test": True},
        )

        await bus.publish(event)

        handler.assert_called_once_with(event)

    def test_get_events(self):
        """Test getting event history."""
        bus = EventBus()

        # Add some events
        event1 = Event("type1", "source1", datetime.now(UTC), {})
        event2 = Event("type2", "source2", datetime.now(UTC), {})
        event3 = Event("type1", "source3", datetime.now(UTC), {})

        bus._event_history.extend([event1, event2, event3])

        # Get all events
        all_events = bus.get_events()
        assert len(all_events) == 3

        # Get events by type
        type1_events = bus.get_events(event_type="type1")
        assert len(type1_events) == 2
        assert all(e.event_type == "type1" for e in type1_events)

        # Get limited events
        limited_events = bus.get_events(limit=2)
        assert len(limited_events) == 2


class TestEventManager:
    """Test EventManager functionality."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test starting and stopping event manager."""
        manager = EventManager()

        await manager.start()
        # Should not raise exception

        await manager.stop()
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """Test emitting an event."""
        manager = EventManager()
        handler = Mock()

        manager.subscribe("test.event", handler)

        await manager.emit("test.event", "test_source", {"key": "value"})

        handler.assert_called_once()
        call_args = handler.call_args[0][0]  # First positional argument (Event)
        assert call_args.event_type == "test.event"
        assert call_args.source == "test_source"
        assert call_args.data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_emit_with_enum(self):
        """Test emitting event with EventType enum."""
        manager = EventManager()
        handler = Mock()

        manager.subscribe(EventType.AGENT_STARTED.value, handler)

        await manager.emit(EventType.AGENT_STARTED, "test_agent", {"type": "test"})

        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args.event_type == EventType.AGENT_STARTED.value


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_emit_event_function(self):
        """Test the emit_event convenience function."""
        handler = Mock()
        subscribe_to_events("test.event", handler)

        await emit_event("test.event", "test_source", {"test": True})

        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_agent_started(self):
        """Test agent started event emission."""
        handler = Mock()
        subscribe_to_events(EventType.AGENT_STARTED.value, handler)

        await emit_agent_started("test_agent", "test_type", extra="data")

        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args.event_type == EventType.AGENT_STARTED.value
        assert call_args.source == "test_agent"
        assert call_args.data["agent_type"] == "test_type"
        assert call_args.data["extra"] == "data"


class TestEventTypes:
    """Test EventType enum."""

    def test_event_types_exist(self):
        """Test that expected event types exist."""
        expected_types = [
            "agent.started",
            "agent.stopped",
            "task.started",
            "task.completed",
            "task.failed",
            "tool.executed",
            "system.health",
        ]

        for expected_type in expected_types:
            assert any(event_type.value == expected_type for event_type in EventType)


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_multi_subscriber_scenario(self):
        """Test multiple subscribers to same event."""
        manager = EventManager()
        handler1 = Mock()
        handler2 = Mock()

        manager.subscribe("multi.event", handler1)
        manager.subscribe("multi.event", handler2)

        await manager.emit("multi.event", "source", {"data": "test"})

        handler1.assert_called_once()
        handler2.assert_called_once()

    @pytest.mark.asyncio
    async def test_correlation_id_scenario(self):
        """Test event correlation."""
        manager = EventManager()
        handler = Mock()

        manager.subscribe("correlated.event", handler)

        correlation_id = "test-correlation-123"
        await manager.emit(
            "correlated.event", "source", {"data": "test"}, correlation_id
        )

        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_event_history_scenario(self):
        """Test event history functionality."""
        manager = EventManager()

        # Emit multiple events
        await manager.emit("type1", "source1", {"count": 1})
        await manager.emit("type2", "source2", {"count": 2})
        await manager.emit("type1", "source3", {"count": 3})

        # Check history
        all_events = manager.get_event_history()
        assert len(all_events) == 3

        type1_events = manager.get_event_history("type1")
        assert len(type1_events) == 2

        limited_events = manager.get_event_history(limit=2)
        assert len(limited_events) == 2
