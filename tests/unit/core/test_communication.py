"""Tests for communication system in agentic workflow."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from agentic_workflow.core.communication import (
    CommunicationManager,
    CoordinationMessage,
    InMemoryChannel,
    InsightMessage,
    Message,
    NotificationMessage,
    create_communication_manager,
    setup_agent_communication,
)


class TestMessage:
    """Test base Message model."""

    def test_message_creation(self):
        """Test basic message creation."""
        message = Message(
            sender_id="agent1",
            recipient_id="agent2",
            message_type="test",
            content={"data": "test data"},
        )

        assert message.sender_id == "agent1"
        assert message.recipient_id == "agent2"
        assert message.message_type == "test"
        assert message.content == {"data": "test data"}
        assert message.priority == 3  # default
        assert message.message_id is not None
        assert message.created_at is not None

    def test_message_with_priority(self):
        """Test message creation with custom priority."""
        message = Message(
            sender_id="agent1", message_type="urgent", content={}, priority=5
        )

        assert message.priority == 5

    def test_message_with_expiration(self):
        """Test message with expiration time."""
        expire_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        message = Message(
            sender_id="agent1",
            message_type="temporary",
            content={},
            expires_at=expire_time,
        )

        assert message.expires_at == expire_time


class TestInsightMessage:
    """Test InsightMessage specialization."""

    def test_insight_message_creation(self):
        """Test insight message creation."""
        message = InsightMessage(
            sender_id="agent1",
            content={"insight": "discovered pattern"},
            insight_type="reasoning",
            confidence=0.85,
            tags=["pattern", "discovery"],
        )

        assert message.message_type == "insight"
        assert message.insight_type == "reasoning"
        assert message.confidence == 0.85
        assert message.tags == ["pattern", "discovery"]


class TestCoordinationMessage:
    """Test CoordinationMessage specialization."""

    def test_coordination_message_creation(self):
        """Test coordination message creation."""
        message = CoordinationMessage(
            sender_id="agent1",
            recipient_id="agent2",
            content={"action": "start_task"},
            action_type="request",
            task_id="task123",
            dependencies=["task121", "task122"],
        )

        assert message.message_type == "coordination"
        assert message.action_type == "request"
        assert message.task_id == "task123"
        assert message.dependencies == ["task121", "task122"]


class TestNotificationMessage:
    """Test NotificationMessage specialization."""

    def test_notification_message_creation(self):
        """Test notification message creation."""
        message = NotificationMessage(
            sender_id="system",
            content={"alert": "high memory usage"},
            notification_type="warning",
            priority=4,
            context={"memory_usage": "85%"},
        )

        assert message.message_type == "notification"
        assert message.notification_type == "warning"
        assert message.priority == 4
        assert message.context == {"memory_usage": "85%"}


class TestInMemoryChannel:
    """Test InMemoryChannel implementation."""

    @pytest.mark.asyncio
    async def test_send_and_receive_message(self):
        """Test sending and receiving messages."""
        channel = InMemoryChannel()

        message = Message(
            sender_id="agent1",
            recipient_id="agent2",
            message_type="test",
            content={"data": "test"},
        )

        # Send message
        success = await channel.send_message(message)
        assert success

        # Receive messages
        messages = await channel.receive_messages("agent2")
        assert len(messages) == 1
        assert messages[0].sender_id == "agent1"
        assert messages[0].content == {"data": "test"}

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """Test broadcasting messages."""
        channel = InMemoryChannel()

        message = Message(
            sender_id="system",
            message_type="broadcast",
            content={"announcement": "system update"},
        )

        # Broadcast message
        success = await channel.broadcast_message(message)
        assert success

        # Any agent should receive the broadcast
        messages = await channel.receive_messages("agent1")
        assert len(messages) == 1
        assert messages[0].content == {"announcement": "system update"}

    @pytest.mark.asyncio
    async def test_message_expiration(self):
        """Test message expiration functionality."""
        channel = InMemoryChannel()

        # Create expired message
        past_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        expired_message = Message(
            sender_id="agent1",
            recipient_id="agent2",
            message_type="expired",
            content={},
            expires_at=past_time,
        )

        # Create valid message
        future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        valid_message = Message(
            sender_id="agent1",
            recipient_id="agent2",
            message_type="valid",
            content={},
            expires_at=future_time,
        )

        await channel.send_message(expired_message)
        await channel.send_message(valid_message)

        # Should only receive valid message
        messages = await channel.receive_messages("agent2")
        assert len(messages) == 1
        assert messages[0].message_type == "valid"

    @pytest.mark.asyncio
    async def test_message_limit(self):
        """Test message limit per agent."""
        channel = InMemoryChannel()
        channel.max_messages_per_agent = 3

        # Send more messages than limit
        for i in range(5):
            message = Message(
                sender_id="sender",
                recipient_id="agent1",
                message_type="test",
                content={"number": i},
            )
            await channel.send_message(message)

        # Should only keep the last 3 messages
        assert len(channel.messages["agent1"]) == 3
        assert channel.messages["agent1"][0].content["number"] == 2  # oldest kept
        assert channel.messages["agent1"][-1].content["number"] == 4  # newest


class TestCommunicationManager:
    """Test CommunicationManager functionality."""

    @pytest.mark.asyncio
    async def test_communication_manager_creation(self):
        """Test communication manager creation."""
        manager = CommunicationManager()

        assert "default" in manager.channels
        assert isinstance(manager.channels["default"], InMemoryChannel)
        assert len(manager.subscriptions) == 0

    def test_add_channel(self):
        """Test adding communication channels."""
        manager = CommunicationManager()
        custom_channel = InMemoryChannel()

        manager.add_channel("custom", custom_channel)

        assert "custom" in manager.channels
        assert manager.channels["custom"] == custom_channel

    def test_subscribe_agent(self):
        """Test agent subscription to message types."""
        manager = CommunicationManager()

        manager.subscribe_agent("agent1", ["insight", "coordination"])

        assert "agent1" in manager.subscriptions
        assert "insight" in manager.subscriptions["agent1"]
        assert "coordination" in manager.subscriptions["agent1"]
        assert len(manager.subscriptions["agent1"]) == 2

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending messages through manager."""
        manager = CommunicationManager()

        message = Message(
            sender_id="agent1",
            recipient_id="agent2",
            message_type="test",
            content={"data": "test"},
        )

        success = await manager.send_message(message)
        assert success

        # Verify message was sent
        messages = await manager.receive_messages("agent2")
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_message_filtering_by_subscription(self):
        """Test message filtering based on subscriptions."""
        manager = CommunicationManager()

        # Subscribe agent to only "insight" messages
        manager.subscribe_agent("agent1", ["insight"])

        # Send different types of messages
        insight_msg = InsightMessage(
            sender_id="sender",
            content={"insight": "test"},
            insight_type="reasoning",
            confidence=0.8,
        )

        coord_msg = CoordinationMessage(
            sender_id="sender", content={"action": "test"}, action_type="request"
        )

        await manager.broadcast_message(insight_msg)
        await manager.broadcast_message(coord_msg)

        # Agent should only receive insight message
        messages = await manager.receive_messages("agent1")
        assert len(messages) == 1
        assert messages[0].message_type == "insight"

    @pytest.mark.asyncio
    async def test_broadcast_insight(self):
        """Test broadcasting insights."""
        manager = CommunicationManager()

        insight_data = {
            "agent_id": "agent1",
            "confidence": 0.9,
            "cycle": 2,
            "insight": "discovered optimization",
        }

        success = await manager.broadcast_insight(insight_data)
        assert success

        # Any agent should receive the insight
        messages = await manager.receive_messages("agent2")
        assert len(messages) == 1
        assert messages[0].message_type == "insight"
        assert messages[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_send_coordination_request(self):
        """Test sending coordination requests."""
        manager = CommunicationManager()

        success = await manager.send_coordination_request(
            sender_id="agent1",
            task_id="task123",
            action_type="start",
            recipient_id="agent2",
            dependencies=["task121"],
        )
        assert success

        messages = await manager.receive_messages("agent2")
        assert len(messages) == 1
        assert messages[0].message_type == "coordination"
        assert messages[0].task_id == "task123"
        assert messages[0].action_type == "start"

    @pytest.mark.asyncio
    async def test_send_notification(self):
        """Test sending notifications."""
        manager = CommunicationManager()

        success = await manager.send_notification(
            sender_id="system",
            notification_type="alert",
            content={"message": "system maintenance"},
            recipient_id="agent1",
            priority=5,
        )
        assert success

        messages = await manager.receive_messages("agent1")
        assert len(messages) == 1
        assert messages[0].message_type == "notification"
        assert messages[0].notification_type == "alert"
        assert messages[0].priority == 5

    def test_get_communication_stats(self):
        """Test getting communication statistics."""
        manager = CommunicationManager()
        manager.subscribe_agent("agent1", ["insight"])
        manager.subscribe_agent("agent2", ["coordination", "notification"])

        stats = manager.get_communication_stats()

        assert "channels" in stats
        assert "default" in stats["channels"]
        assert stats["subscribed_agents"] == 2
        assert "agent1" in stats["subscription_details"]
        assert stats["subscription_details"]["agent1"] == ["insight"]
        assert set(stats["subscription_details"]["agent2"]) == {
            "coordination",
            "notification",
        }

    def test_get_message_history_without_memory(self):
        """Test getting message history without memory manager."""
        manager = CommunicationManager()

        history = manager.get_message_history("agent1")
        assert history == []

    def test_get_message_history_with_memory(self):
        """Test getting message history with memory manager."""
        mock_memory = Mock()
        mock_memory.search.return_value = [
            {"sender_id": "agent1", "content": {"data": "test1"}},
            {"sender_id": "agent2", "content": {"data": "test2"}},
        ]

        manager = CommunicationManager(mock_memory)

        history = manager.get_message_history("agent1")
        assert len(history) == 2
        mock_memory.search.assert_called_once()


class TestCommunicationUtilities:
    """Test communication utility functions."""

    @pytest.mark.asyncio
    async def test_create_communication_manager(self):
        """Test communication manager creation utility."""
        manager = await create_communication_manager()

        assert isinstance(manager, CommunicationManager)
        assert "default" in manager.channels

    @pytest.mark.asyncio
    async def test_setup_agent_communication(self):
        """Test agent communication setup utility."""
        manager = CommunicationManager()

        await setup_agent_communication("agent1", manager)

        # Should be subscribed to default message types
        assert "agent1" in manager.subscriptions
        expected_types = {"insight", "coordination", "notification"}
        assert manager.subscriptions["agent1"] == expected_types

    @pytest.mark.asyncio
    async def test_setup_agent_communication_custom_types(self):
        """Test agent communication setup with custom message types."""
        manager = CommunicationManager()

        await setup_agent_communication("agent1", manager, ["custom", "special"])

        assert "agent1" in manager.subscriptions
        assert manager.subscriptions["agent1"] == {"custom", "special"}


class TestCommunicationIntegration:
    """Test communication system integration scenarios."""

    @pytest.mark.asyncio
    async def test_multi_agent_coordination_scenario(self):
        """Test multi-agent coordination scenario."""
        manager = CommunicationManager()

        # Setup agents
        await setup_agent_communication("coordinator", manager)
        await setup_agent_communication("worker1", manager, ["coordination"])
        await setup_agent_communication("worker2", manager, ["coordination"])

        # Coordinator sends task to workers
        await manager.send_coordination_request(
            sender_id="coordinator",
            task_id="task123",
            action_type="execute",
            dependencies=[],
        )

        # Workers receive the task
        worker1_messages = await manager.receive_messages("worker1")
        worker2_messages = await manager.receive_messages("worker2")

        assert len(worker1_messages) == 1
        assert len(worker2_messages) == 1
        assert worker1_messages[0].task_id == "task123"
        assert worker2_messages[0].task_id == "task123"

    @pytest.mark.asyncio
    async def test_insight_sharing_scenario(self):
        """Test insight sharing between agents."""
        manager = CommunicationManager()

        # Setup agents interested in insights
        await setup_agent_communication("discoverer", manager)
        await setup_agent_communication("learner1", manager, ["insight"])
        await setup_agent_communication("learner2", manager, ["insight"])

        # Share insight
        await manager.broadcast_insight(
            {
                "agent_id": "discoverer",
                "confidence": 0.9,
                "insight": "New optimization pattern discovered",
            }
        )

        # Learners receive the insight
        learner1_messages = await manager.receive_messages("learner1")
        learner2_messages = await manager.receive_messages("learner2")

        assert len(learner1_messages) == 1
        assert len(learner2_messages) == 1
        assert learner1_messages[0].confidence == 0.9
        assert "optimization pattern" in learner1_messages[0].content["insight"]
