"""Event system for the agentic workflow platform.

This module provides MQTT-based event publishing and subscription capabilities
for inter-agent communication and system-wide event handling.
"""

from typing import Dict, Any, List, Optional, Callable, Union
import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from enum import Enum

try:
    from asyncio_mqtt import Client as MQTTClient
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

from agentic_workflow.core.config import get_config
from agentic_workflow.core.logging_config import get_logger


logger = get_logger(__name__)


class EventType(Enum):
    """Standard event types for the system."""
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    MEMORY_UPDATED = "memory.updated"
    TOOL_EXECUTED = "tool.executed"
    COMMUNICATION_SENT = "communication.sent"
    REASONING_COMPLETED = "reasoning.completed"
    SYSTEM_HEALTH = "system.health"
    CUSTOM = "custom"


@dataclass
class Event:
    """Represents a system event."""
    
    event_type: str
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        return cls(**data)


class EventBus:
    """In-memory event bus for local event handling."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Event] = []
        self.logger = get_logger(f"{__name__}.EventBus")
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        self.logger.info(f"Subscribed to {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Unsubscribe from events."""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            self.logger.info(f"Unsubscribed from {event_type}")
    
    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        self._event_history.append(event)
        
        # Notify subscribers for specific event type
        if event.event_type in self._subscribers:
            for handler in self._subscribers[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}")
        
        # Notify wildcard subscribers
        if "*" in self._subscribers:
            for handler in self._subscribers["*"]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    self.logger.error(f"Error in wildcard event handler: {e}")
    
    def get_events(self, event_type: Optional[str] = None, limit: Optional[int] = None) -> List[Event]:
        """Get event history with optional filtering."""
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if limit:
            events = events[-limit:]
        
        return events


class MQTTEventManager:
    """MQTT-based event manager for distributed event handling."""
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883, 
                 client_id: str = "agentic_workflow"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.mqtt_client = None
        self._subscribers: Dict[str, List[Callable]] = {}
        self.logger = get_logger(f"{__name__}.MQTTEventManager")
        self.connected = False
    
    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        if not MQTT_AVAILABLE:
            self.logger.warning("MQTT client not available - event system will use local bus only")
            return False
        
        try:
            self.mqtt_client = MQTTClient(
                hostname=self.broker_host,
                port=self.broker_port,
                client_id=self.client_id
            )
            await self.mqtt_client.__aenter__()
            self.connected = True
            self.logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.mqtt_client and self.connected:
            try:
                await self.mqtt_client.__aexit__(None, None, None)
                self.connected = False
                self.logger.info("Disconnected from MQTT broker")
            except Exception as e:
                self.logger.error(f"Error disconnecting from MQTT: {e}")
    
    async def publish_event(self, event: Event, topic: Optional[str] = None) -> None:
        """Publish event to MQTT topic."""
        if not self.connected or not self.mqtt_client:
            self.logger.warning("MQTT not connected - cannot publish event")
            return
        
        if topic is None:
            topic = f"agentic/{event.event_type.replace('.', '/')}"
        
        try:
            payload = json.dumps(event.to_dict())
            await self.mqtt_client.publish(topic, payload)
            self.logger.debug(f"Published event {event.event_type} to topic {topic}")
        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
    
    async def subscribe_to_topic(self, topic: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to MQTT topic."""
        if not self.connected or not self.mqtt_client:
            self.logger.warning("MQTT not connected - cannot subscribe")
            return
        
        try:
            await self.mqtt_client.subscribe(topic)
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(handler)
            self.logger.info(f"Subscribed to MQTT topic: {topic}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to topic {topic}: {e}")


class EventManager:
    """Central event management system combining local and MQTT capabilities."""
    
    def __init__(self):
        self.config = get_config()
        self.local_bus = EventBus()
        self.mqtt_manager = None
        self.logger = get_logger(__name__)
        
        # Initialize MQTT if configured
        if hasattr(self.config, 'mqtt') and MQTT_AVAILABLE:
            mqtt_config = self.config.mqtt
            self.mqtt_manager = MQTTEventManager(
                broker_host=getattr(mqtt_config, 'host', 'localhost'),
                broker_port=getattr(mqtt_config, 'port', 1883),
                client_id=getattr(mqtt_config, 'client_id', 'agentic_workflow')
            )
    
    async def start(self) -> None:
        """Start the event manager."""
        if self.mqtt_manager:
            await self.mqtt_manager.connect()
        self.logger.info("Event manager started")
    
    async def stop(self) -> None:
        """Stop the event manager."""
        if self.mqtt_manager:
            await self.mqtt_manager.disconnect()
        self.logger.info("Event manager stopped")
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to events (local bus)."""
        self.local_bus.subscribe(event_type, handler)
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Unsubscribe from events (local bus)."""
        self.local_bus.unsubscribe(event_type, handler)
    
    async def publish(self, event: Event, mqtt_topic: Optional[str] = None) -> None:
        """Publish event to both local and MQTT systems."""
        # Publish to local bus
        await self.local_bus.publish(event)
        
        # Publish to MQTT if available
        if self.mqtt_manager and self.mqtt_manager.connected:
            await self.mqtt_manager.publish_event(event, mqtt_topic)
    
    async def emit(self, event_type: Union[str, EventType], source: str, 
                   data: Dict[str, Any], correlation_id: Optional[str] = None) -> None:
        """Convenience method to create and publish an event."""
        if isinstance(event_type, EventType):
            event_type = event_type.value
        
        event = Event(
            event_type=event_type,
            source=source,
            timestamp=datetime.now(UTC),
            data=data,
            correlation_id=correlation_id
        )
        
        await self.publish(event)
    
    def get_event_history(self, event_type: Optional[str] = None, limit: Optional[int] = None) -> List[Event]:
        """Get event history from local bus."""
        return self.local_bus.get_events(event_type, limit)


# Global event manager instance
event_manager = EventManager()


# Convenience functions
async def emit_event(event_type: Union[str, EventType], source: str, 
                     data: Dict[str, Any], correlation_id: Optional[str] = None) -> None:
    """Emit an event using the global event manager."""
    await event_manager.emit(event_type, source, data, correlation_id)


def subscribe_to_events(event_type: str, handler: Callable[[Event], None]) -> None:
    """Subscribe to events using the global event manager."""
    event_manager.subscribe(event_type, handler)


def unsubscribe_from_events(event_type: str, handler: Callable[[Event], None]) -> None:
    """Unsubscribe from events using the global event manager."""
    event_manager.unsubscribe(event_type, handler)


# Agent lifecycle events
async def emit_agent_started(agent_id: str, agent_type: str, **kwargs) -> None:
    """Emit agent started event."""
    await emit_event(
        EventType.AGENT_STARTED,
        agent_id,
        {"agent_type": agent_type, **kwargs}
    )


async def emit_agent_stopped(agent_id: str, agent_type: str, **kwargs) -> None:
    """Emit agent stopped event."""
    await emit_event(
        EventType.AGENT_STOPPED,
        agent_id,
        {"agent_type": agent_type, **kwargs}
    )


# Task lifecycle events
async def emit_task_started(agent_id: str, task_id: str, task_type: str, **kwargs) -> None:
    """Emit task started event."""
    await emit_event(
        EventType.TASK_STARTED,
        agent_id,
        {"task_id": task_id, "task_type": task_type, **kwargs},
        correlation_id=task_id
    )


async def emit_task_completed(agent_id: str, task_id: str, result: Dict[str, Any], **kwargs) -> None:
    """Emit task completed event."""
    await emit_event(
        EventType.TASK_COMPLETED,
        agent_id,
        {"task_id": task_id, "result": result, **kwargs},
        correlation_id=task_id
    )


async def emit_task_failed(agent_id: str, task_id: str, error: str, **kwargs) -> None:
    """Emit task failed event."""
    await emit_event(
        EventType.TASK_FAILED,
        agent_id,
        {"task_id": task_id, "error": error, **kwargs},
        correlation_id=task_id
    )


# Tool execution events
async def emit_tool_executed(agent_id: str, tool_id: str, duration: float, 
                             success: bool, **kwargs) -> None:
    """Emit tool execution event."""
    await emit_event(
        EventType.TOOL_EXECUTED,
        agent_id,
        {
            "tool_id": tool_id,
            "duration": duration,
            "success": success,
            **kwargs
        }
    )


# System health events
async def emit_health_status(component: str, status: str, details: Dict[str, Any]) -> None:
    """Emit system health status event."""
    await emit_event(
        EventType.SYSTEM_HEALTH,
        f"health_checker.{component}",
        {"component": component, "status": status, "details": details}
    )


__all__ = [
    'Event',
    'EventType',
    'EventBus',
    'MQTTEventManager', 
    'EventManager',
    'event_manager',
    'emit_event',
    'subscribe_to_events',
    'unsubscribe_from_events',
    'emit_agent_started',
    'emit_agent_stopped',
    'emit_task_started',
    'emit_task_completed',
    'emit_task_failed',
    'emit_tool_executed',
    'emit_health_status',
]