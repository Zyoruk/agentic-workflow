"""Communication system for multi-agent coordination.

This module provides infrastructure for agents to communicate, share insights,
and coordinate activities across the workflow system.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.memory.interfaces import MemoryType

logger = get_logger(__name__)


class Message(BaseModel):
    """Base message structure for agent communication."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    recipient_id: Optional[str] = None  # None for broadcast messages
    message_type: str
    content: Dict[str, Any]
    priority: int = Field(ge=1, le=5, default=3)  # 1=Low, 5=Critical
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: Optional[str] = None


class InsightMessage(Message):
    """Specialized message for sharing insights between agents."""

    message_type: str = "insight"
    insight_type: str  # "reasoning", "performance", "discovery", etc.
    confidence: float = Field(ge=0.0, le=1.0)
    tags: List[str] = []


class CoordinationMessage(Message):
    """Specialized message for agent coordination."""

    message_type: str = "coordination"
    action_type: str  # "request", "acknowledge", "complete", "error"
    task_id: Optional[str] = None
    dependencies: List[str] = []


class NotificationMessage(Message):
    """Specialized message for system notifications."""

    message_type: str = "notification"
    notification_type: str  # "alert", "info", "warning", "error"
    context: Dict[str, Any] = {}


class CommunicationChannel(ABC):
    """Abstract base class for communication channels."""

    @abstractmethod
    async def send_message(self, message: Message) -> bool:
        """Send a message through this channel."""
        pass

    @abstractmethod
    async def receive_messages(self, agent_id: str) -> List[Message]:
        """Receive messages for a specific agent."""
        pass

    @abstractmethod
    async def broadcast_message(self, message: Message) -> bool:
        """Broadcast a message to all agents."""
        pass


class InMemoryChannel(CommunicationChannel):
    """In-memory communication channel for local agent coordination."""

    def __init__(self) -> None:
        self.messages: Dict[str, List[Message]] = {}  # agent_id -> messages
        self.broadcast_messages: List[Message] = []
        self.max_messages_per_agent = 1000

    async def send_message(self, message: Message) -> bool:
        """Send a message to a specific agent."""
        try:
            if message.recipient_id:
                if message.recipient_id not in self.messages:
                    self.messages[message.recipient_id] = []

                # Maintain message limit per agent
                if (
                    len(self.messages[message.recipient_id])
                    >= self.max_messages_per_agent
                ):
                    self.messages[message.recipient_id].pop(0)  # Remove oldest

                self.messages[message.recipient_id].append(message)
                logger.debug(
                    f"Message sent from {message.sender_id} to {message.recipient_id}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def receive_messages(self, agent_id: str) -> List[Message]:
        """Receive messages for a specific agent."""
        try:
            agent_messages = self.messages.get(agent_id, []).copy()
            broadcast_messages = self.broadcast_messages.copy()

            # Filter out expired messages
            current_time = datetime.now(UTC)
            all_messages = agent_messages + broadcast_messages

            valid_messages = []
            for msg in all_messages:
                if msg.expires_at:
                    expire_time = datetime.fromisoformat(
                        msg.expires_at.replace("Z", "+00:00")
                    )
                    if current_time < expire_time:
                        valid_messages.append(msg)
                else:
                    valid_messages.append(msg)

            # Clear received messages for this agent
            self.messages[agent_id] = []

            return valid_messages
        except Exception as e:
            logger.error(f"Failed to receive messages for {agent_id}: {e}")
            return []

    async def broadcast_message(self, message: Message) -> bool:
        """Broadcast a message to all agents."""
        try:
            # Maintain broadcast message limit
            if len(self.broadcast_messages) >= self.max_messages_per_agent:
                self.broadcast_messages.pop(0)

            self.broadcast_messages.append(message)
            logger.debug(f"Message broadcast from {message.sender_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")
            return False


class CommunicationManager:
    """Central manager for agent communication and coordination."""

    def __init__(self, memory_manager=None) -> None:
        self.memory_manager = memory_manager
        self.channels: Dict[str, CommunicationChannel] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # agent_id -> message_types
        self.logger = get_logger(__name__)

        # Initialize default in-memory channel
        self.add_channel("default", InMemoryChannel())

    def add_channel(self, channel_name: str, channel: CommunicationChannel) -> None:
        """Add a communication channel."""
        self.channels[channel_name] = channel
        self.logger.info(f"Added communication channel: {channel_name}")

    def subscribe_agent(self, agent_id: str, message_types: List[str]) -> None:
        """Subscribe an agent to specific message types."""
        if agent_id not in self.subscriptions:
            self.subscriptions[agent_id] = set()
        self.subscriptions[agent_id].update(message_types)
        self.logger.debug(f"Agent {agent_id} subscribed to: {message_types}")

    async def send_message(
        self, message: Message, channel_name: str = "default"
    ) -> bool:
        """Send a message through a specific channel."""
        if channel_name not in self.channels:
            self.logger.error(f"Unknown channel: {channel_name}")
            return False

        success = await self.channels[channel_name].send_message(message)

        # Store in memory for persistence if available
        if success and self.memory_manager:
            try:
                self.memory_manager.store(
                    key=f"message_{message.message_id}",
                    data=message.model_dump(),
                    memory_type=MemoryType.SHORT_TERM,
                    metadata={
                        "sender_id": message.sender_id,
                        "recipient_id": message.recipient_id,
                        "message_type": message.message_type,
                    },
                )
            except Exception as e:
                self.logger.warning(f"Failed to store message in memory: {e}")

        return success

    async def receive_messages(
        self, agent_id: str, channel_name: str = "default"
    ) -> List[Message]:
        """Receive messages for an agent from a specific channel."""
        if channel_name not in self.channels:
            self.logger.error(f"Unknown channel: {channel_name}")
            return []

        messages = await self.channels[channel_name].receive_messages(agent_id)

        # Filter messages based on subscriptions
        if agent_id in self.subscriptions:
            subscribed_types = self.subscriptions[agent_id]
            messages = [msg for msg in messages if msg.message_type in subscribed_types]

        return messages

    async def broadcast_insight(
        self, insight_data: Dict[str, Any], channel_name: str = "default"
    ) -> bool:
        """Broadcast an insight to all agents."""
        insight_message = InsightMessage(
            sender_id=insight_data.get("agent_id", "unknown"),
            content=insight_data,
            insight_type="reasoning",
            confidence=insight_data.get("confidence", 0.8),
            tags=insight_data.get("tags", []),
        )

        return await self.broadcast_message(insight_message, channel_name)

    async def broadcast_message(
        self, message: Message, channel_name: str = "default"
    ) -> bool:
        """Broadcast a message to all agents."""
        if channel_name not in self.channels:
            self.logger.error(f"Unknown channel: {channel_name}")
            return False

        return await self.channels[channel_name].broadcast_message(message)

    async def send_coordination_request(
        self,
        sender_id: str,
        task_id: str,
        action_type: str,
        recipient_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> bool:
        """Send a coordination request to one or all agents."""
        coordination_message = CoordinationMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content={
                "task_id": task_id,
                "action_type": action_type,
                "dependencies": dependencies or [],
            },
            action_type=action_type,
            task_id=task_id,
            dependencies=dependencies or [],
        )

        if recipient_id:
            return await self.send_message(coordination_message)
        else:
            return await self.broadcast_message(coordination_message)

    async def send_notification(
        self,
        sender_id: str,
        notification_type: str,
        content: Dict[str, Any],
        recipient_id: Optional[str] = None,
        priority: int = 3,
    ) -> bool:
        """Send a notification message."""
        notification_message = NotificationMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
            notification_type=notification_type,
            priority=priority,
            context=content.get("context", {}),
        )

        if recipient_id:
            return await self.send_message(notification_message)
        else:
            return await self.broadcast_message(notification_message)

    def get_message_history(
        self, agent_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve message history for an agent from memory."""
        if not self.memory_manager:
            return []

        try:
            results = self.memory_manager.search(
                query=f"sender_id:{agent_id} OR recipient_id:{agent_id}",
                memory_type=MemoryType.SHORT_TERM,
                limit=limit,
                filters={"type": "message"},
            )
            return results
        except Exception as e:
            self.logger.error(f"Failed to retrieve message history: {e}")
            return []

    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics."""
        stats = {
            "channels": list(self.channels.keys()),
            "subscribed_agents": len(self.subscriptions),
            "subscription_details": {
                agent_id: list(message_types)
                for agent_id, message_types in self.subscriptions.items()
            },
        }

        # Add channel-specific stats for in-memory channels
        for channel_name, channel in self.channels.items():
            if isinstance(channel, InMemoryChannel):
                stats[f"{channel_name}_channel_stats"] = {
                    "agents_with_messages": len(channel.messages),
                    "total_agent_messages": sum(
                        len(msgs) for msgs in channel.messages.values()
                    ),
                    "broadcast_messages": len(channel.broadcast_messages),
                }

        return stats


# Convenience functions for common communication patterns
async def create_communication_manager(memory_manager=None) -> CommunicationManager:
    """Create and configure a communication manager."""
    manager = CommunicationManager(memory_manager)
    return manager


async def setup_agent_communication(
    agent_id: str,
    communication_manager: CommunicationManager,
    message_types: List[str] = None,
) -> None:
    """Set up communication for an agent."""
    default_types = ["insight", "coordination", "notification"]
    subscription_types = message_types or default_types

    communication_manager.subscribe_agent(agent_id, subscription_types)
