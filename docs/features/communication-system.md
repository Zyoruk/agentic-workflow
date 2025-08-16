# Multi-Agent Communication System

The agentic workflow system includes a comprehensive communication infrastructure that enables sophisticated agent coordination, insight sharing, and task management across distributed agent networks.

## Overview

The communication system provides:

- **Multi-channel messaging**: Support for various communication channels
- **Message type specialization**: Insights, coordination, and notifications
- **Agent subscription management**: Selective message filtering
- **Automatic lifecycle management**: Message expiration and cleanup
- **Integration with reasoning**: Seamless RAISE pattern support

## Architecture

### Core Components

```python
from agentic_workflow.core.communication import (
    CommunicationManager,
    Message,
    InsightMessage,
    CoordinationMessage,
    NotificationMessage,
    InMemoryChannel
)
```

### CommunicationManager

The central orchestrator for all agent communication:

```python
# Initialize communication manager
comm_manager = CommunicationManager()

# Setup agent communication
await setup_agent_communication("agent1", comm_manager, ["insight", "coordination"])
```

## Message Types

### InsightMessage

For sharing discoveries and learnings between agents:

```python
insight = InsightMessage(
    sender_id="analyzer_agent",
    content={"discovery": "Optimal caching strategy identified"},
    insight_type="performance",
    confidence=0.92,
    tags=["optimization", "caching", "performance"]
)
```

### CoordinationMessage

For task coordination and dependency management:

```python
coordination = CoordinationMessage(
    sender_id="coordinator",
    recipient_id="executor",
    content={"task_details": "Deploy microservices"},
    action_type="execute",
    task_id="deployment_task_123",
    dependencies=["build_complete", "tests_passed"]
)
```

### NotificationMessage

For system alerts and status updates:

```python
notification = NotificationMessage(
    sender_id="monitor_agent",
    content={"alert": "High CPU usage detected", "threshold": "85%"},
    notification_type="warning",
    priority=4,
    context={"service": "user-service", "region": "us-east-1"}
)
```

## Communication Channels

### InMemoryChannel

High-performance local communication for single-node deployments:

```python
channel = InMemoryChannel()
comm_manager.add_channel("local", channel)
```

### Extensible Architecture

The system supports custom channels for distributed deployments:

```python
# Custom Redis channel (implementation example)
class RedisChannel(CommunicationChannel):
    async def send_message(self, message: Message) -> bool:
        # Redis-based message delivery
        pass
    
    async def receive_messages(self, agent_id: str) -> List[Message]:
        # Redis-based message retrieval
        pass

# Add custom channel
comm_manager.add_channel("distributed", RedisChannel())
```

## Usage Examples

### Basic Communication Setup

```python
import asyncio
from agentic_workflow.core.communication import CommunicationManager, setup_agent_communication

async def setup_agent_network():
    # Create communication manager
    comm_manager = CommunicationManager()
    
    # Setup multiple agents
    agents = ["coordinator", "worker1", "worker2", "monitor"]
    
    for agent_id in agents:
        await setup_agent_communication(agent_id, comm_manager)
    
    return comm_manager
```

### Insight Sharing

```python
async def share_insights():
    comm_manager = await setup_agent_network()
    
    # Agent shares discovery
    await comm_manager.broadcast_insight({
        "agent_id": "research_agent",
        "confidence": 0.88,
        "insight": "New optimization algorithm reduces latency by 40%",
        "tags": ["optimization", "performance", "algorithms"]
    })
    
    # Other agents receive the insight
    for agent_id in ["optimizer", "architect", "developer"]:
        messages = await comm_manager.receive_messages(agent_id)
        for msg in messages:
            if msg.message_type == "insight":
                print(f"{agent_id} received insight with {msg.confidence:.1%} confidence")
```

### Task Coordination

```python
async def coordinate_deployment():
    comm_manager = await setup_agent_network()
    
    # Coordinator assigns tasks
    tasks = [
        ("builder", "build_services"),
        ("tester", "run_integration_tests"),
        ("deployer", "deploy_to_staging")
    ]
    
    for agent_id, task_id in tasks:
        await comm_manager.send_coordination_request(
            sender_id="coordinator",
            task_id=task_id,
            action_type="execute",
            recipient_id=agent_id,
            dependencies=["previous_task_complete"]
        )
    
    # Agents acknowledge tasks
    for agent_id, task_id in tasks:
        messages = await comm_manager.receive_messages(agent_id)
        for msg in messages:
            if msg.message_type == "coordination":
                print(f"{agent_id} received task: {msg.task_id}")
                
                # Send acknowledgment
                await comm_manager.send_coordination_request(
                    sender_id=agent_id,
                    task_id=task_id,
                    action_type="acknowledge",
                    recipient_id="coordinator"
                )
```

### System Monitoring

```python
async def monitor_system():
    comm_manager = await setup_agent_network()
    
    # Monitor sends alerts
    alerts = [
        ("High memory usage", "warning", 3),
        ("Service unavailable", "error", 5),
        ("Deployment complete", "info", 2)
    ]
    
    for message, alert_type, priority in alerts:
        await comm_manager.send_notification(
            sender_id="monitor",
            notification_type=alert_type,
            content={"message": message, "timestamp": "2025-01-16T09:00:00Z"},
            priority=priority
        )
    
    # Agents receive relevant notifications
    for agent_id in ["admin", "developer", "operator"]:
        messages = await comm_manager.receive_messages(agent_id)
        for msg in messages:
            if msg.message_type == "notification":
                print(f"{agent_id} received {msg.notification_type}: {msg.content['message']}")
```

## Integration with RAISE Pattern

The communication system is integrated with the RAISE reasoning pattern for collaborative problem-solving:

```python
async def raise_with_communication():
    # Setup communication
    comm_manager = CommunicationManager()
    await setup_agent_communication("strategic_agent", comm_manager)
    
    # Create reasoning engine with communication
    from agentic_workflow.core.reasoning import ReasoningEngine
    
    reasoning_engine = ReasoningEngine(
        agent_id="strategic_agent",
        communication_manager=comm_manager
    )
    
    # Execute RAISE pattern with automatic insight sharing
    result = reasoning_engine.reason(
        objective="Design resilient microservices architecture",
        pattern="raise",
        context={"team_size": 4, "timeline": "6_weeks"}
    )
    
    # Insights automatically shared during RAISE Share phase
    print(f"RAISE reasoning completed with {result.confidence:.1%} confidence")
    print(f"Insights shared across agent network during {len(result.steps)} steps")
```

## Performance and Monitoring

### Communication Statistics

```python
# Get communication metrics
stats = comm_manager.get_communication_stats()

print(f"Active channels: {len(stats['channels'])}")
print(f"Connected agents: {stats['subscribed_agents']}")
print(f"Message distribution:")

for agent_id, types in stats['subscription_details'].items():
    print(f"  {agent_id}: {', '.join(types)}")
```

### Message History

```python
# Retrieve message history (requires memory manager)
history = comm_manager.get_message_history("agent1", limit=10)

for msg in history:
    print(f"{msg['sender_id']} -> {msg.get('recipient_id', 'ALL')}: {msg['message_type']}")
```

## Best Practices

### Agent Subscription Strategy

1. **Selective Subscriptions**: Only subscribe to relevant message types
2. **Role-based Filtering**: Different agent roles need different message types
3. **Priority Management**: High-priority agents for critical notifications

### Message Design

1. **Clear Content**: Include all necessary information in message content
2. **Appropriate Priority**: Use priority levels effectively
3. **Expiration Policy**: Set expiration for time-sensitive messages
4. **Rich Metadata**: Include tags and context for better filtering

### Scalability Considerations

1. **Channel Selection**: Choose appropriate channels for deployment scale
2. **Message Limits**: Configure message limits based on system capacity
3. **Cleanup Policies**: Regular cleanup of expired messages
4. **Load Balancing**: Distribute communication load across channels

## Error Handling

The communication system includes comprehensive error handling:

```python
try:
    success = await comm_manager.send_message(message)
    if not success:
        print("Message delivery failed")
        
except Exception as e:
    print(f"Communication error: {e}")
    # Implement retry logic or fallback communication
```

## Security Considerations

1. **Message Validation**: All messages are validated before processing
2. **Agent Authentication**: Verify agent identity for secure communication
3. **Content Filtering**: Sanitize message content for security
4. **Audit Logging**: Track communication for security auditing

The multi-agent communication system provides a robust foundation for sophisticated agent coordination, enabling the implementation of advanced collaborative reasoning patterns like RAISE and supporting complex multi-agent workflows.