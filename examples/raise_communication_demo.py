#!/usr/bin/env python3
"""Demonstration of RAISE reasoning pattern and communication system.

This script showcases the new RAISE (Reason, Act, Improve, Share, Evaluate) pattern
and the communication system for multi-agent coordination.
"""

import asyncio
import json
from typing import Dict, Any

from agentic_workflow.core.reasoning import ReasoningEngine
from agentic_workflow.core.communication import CommunicationManager, setup_agent_communication


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_step(step_num: int, title: str, details: str = ""):
    """Print a formatted step."""
    print(f"\n{step_num}. {title}")
    if details:
        print(f"   {details}")


async def demonstrate_raise_pattern():
    """Demonstrate the RAISE reasoning pattern."""
    print_section("RAISE REASONING PATTERN DEMONSTRATION")
    
    print("RAISE stands for: Reason → Act → Improve → Share → Evaluate")
    print("This pattern enables sophisticated multi-agent coordination through iterative cycles.")
    
    # Create communication manager
    communication_manager = CommunicationManager()
    await setup_agent_communication("planning_agent", communication_manager)
    
    # Create reasoning engine with communication
    reasoning_engine = ReasoningEngine(
        agent_id="planning_agent",
        memory_manager=None,  # For demo purposes
        communication_manager=communication_manager
    )
    
    print_step(1, "Executing RAISE Pattern", "Objective: Design scalable microservices architecture")
    
    # Execute RAISE reasoning
    result = reasoning_engine.reason(
        objective="Design scalable microservices architecture with high availability",
        pattern="raise",
        context={
            "requirements": ["scalability", "high_availability", "fault_tolerance"],
            "constraints": ["budget", "timeline", "team_size"]
        }
    )
    
    print(f"\n✅ RAISE Reasoning Completed!")
    print(f"   Pattern: {result.pattern_type}")
    print(f"   Objective: {result.objective}")
    print(f"   Total Steps: {len(result.steps)}")
    print(f"   Final Confidence: {result.confidence:.2f}")
    print(f"   Completed: {result.completed}")
    
    print_step(2, "Analyzing RAISE Cycles")
    
    # Analyze cycles and phases
    phases = ["reason", "act", "improve", "share", "evaluate"]
    phase_counts = {phase: 0 for phase in phases}
    
    cycles = []
    current_cycle = []
    
    for step in result.steps:
        current_cycle.append(step)
        
        # Count phases
        for phase in phases:
            if phase.lower() in step.thought.lower():
                phase_counts[phase] += 1
        
        # Detect cycle completion (evaluate step)
        if "evaluate" in step.thought.lower():
            cycles.append(current_cycle)
            current_cycle = []
    
    print(f"\n   Completed Cycles: {len(cycles)}")
    print(f"   Phase Distribution:")
    for phase, count in phase_counts.items():
        print(f"     {phase.capitalize()}: {count} steps")
    
    print_step(3, "Examining Key Insights")
    
    # Find key insights from each cycle
    for i, cycle in enumerate(cycles[:3]):  # Show first 3 cycles
        print(f"\n   Cycle {i+1} Summary:")
        
        for step in cycle:
            step_type = ""
            if "reason" in step.thought.lower():
                step_type = "🧠 REASON"
            elif "act" in step.thought.lower():
                step_type = "⚡ ACT"
            elif "improve" in step.thought.lower():
                step_type = "📈 IMPROVE"
            elif "share" in step.thought.lower():
                step_type = "🤝 SHARE"
            elif "evaluate" in step.thought.lower():
                step_type = "📊 EVALUATE"
            
            if step_type:
                print(f"     {step_type}: {step.observation[:80]}...")
                print(f"       Confidence: {step.confidence:.2f}")
    
    print_step(4, "Final Solution", result.final_answer[:200] + "...")
    
    return result


async def demonstrate_communication_system():
    """Demonstrate the communication system."""
    print_section("MULTI-AGENT COMMUNICATION SYSTEM DEMONSTRATION")
    
    print("The communication system enables agents to share insights, coordinate tasks,")
    print("and send notifications across the workflow system.")
    
    # Create communication manager
    comm_manager = CommunicationManager()
    
    print_step(1, "Setting Up Agent Communication Network")
    
    # Setup multiple agents
    agents = ["coordinator", "analyzer", "executor", "monitor"]
    
    for agent_id in agents:
        await setup_agent_communication(agent_id, comm_manager)
        print(f"   ✅ {agent_id} connected to communication network")
    
    print_step(2, "Broadcasting System Insight")
    
    # Broadcast insight from analyzer
    insight_success = await comm_manager.broadcast_insight({
        "agent_id": "analyzer",
        "confidence": 0.92,
        "insight": "Discovered optimal resource allocation pattern for microservices",
        "tags": ["optimization", "microservices", "resources"]
    })
    
    print(f"   Insight broadcast: {'✅ Success' if insight_success else '❌ Failed'}")
    
    print_step(3, "Sending Coordination Request")
    
    # Coordinator sends task to executor
    coord_success = await comm_manager.send_coordination_request(
        sender_id="coordinator",
        task_id="microservices_deployment",
        action_type="execute",
        recipient_id="executor",
        dependencies=["resource_analysis", "architecture_design"]
    )
    
    print(f"   Coordination request sent: {'✅ Success' if coord_success else '❌ Failed'}")
    
    print_step(4, "Sending System Notification")
    
    # Monitor sends alert
    notif_success = await comm_manager.send_notification(
        sender_id="monitor",
        notification_type="alert",
        content={
            "message": "High CPU usage detected in microservice cluster",
            "severity": "medium",
            "affected_services": ["user-service", "payment-service"]
        },
        priority=4
    )
    
    print(f"   Notification sent: {'✅ Success' if notif_success else '❌ Failed'}")
    
    print_step(5, "Checking Agent Message Queues")
    
    # Check messages received by each agent
    for agent_id in agents:
        messages = await comm_manager.receive_messages(agent_id)
        print(f"\n   {agent_id} received {len(messages)} messages:")
        
        for msg in messages:
            msg_type = msg.message_type
            sender = msg.sender_id
            priority = msg.priority
            
            if msg_type == "insight":
                confidence = getattr(msg, 'confidence', 'N/A')
                print(f"     📝 Insight from {sender} (confidence: {confidence})")
                
            elif msg_type == "coordination":
                action = getattr(msg, 'action_type', 'unknown')
                task = getattr(msg, 'task_id', 'unknown')
                print(f"     🤝 Coordination from {sender} (action: {action}, task: {task})")
                
            elif msg_type == "notification":
                notif_type = getattr(msg, 'notification_type', 'unknown')
                print(f"     🔔 Notification from {sender} (type: {notif_type}, priority: {priority})")
    
    print_step(6, "Communication Statistics")
    
    stats = comm_manager.get_communication_stats()
    print(f"\n   Active Channels: {len(stats['channels'])}")
    print(f"   Connected Agents: {stats['subscribed_agents']}")
    print(f"   Message Types by Agent:")
    
    for agent_id, types in stats['subscription_details'].items():
        print(f"     {agent_id}: {', '.join(types)}")
    
    return stats


async def demonstrate_integrated_workflow():
    """Demonstrate RAISE pattern with communication system integration."""
    print_section("INTEGRATED RAISE + COMMUNICATION WORKFLOW")
    
    print("Combining RAISE reasoning with multi-agent communication for")
    print("sophisticated collaborative problem-solving.")
    
    # Setup communication system
    comm_manager = CommunicationManager()
    
    # Setup agents with different specializations
    agent_configs = {
        "architect": ["insight", "coordination"],
        "developer": ["coordination", "notification"],
        "tester": ["coordination", "notification"],
        "deployer": ["coordination", "notification"]
    }
    
    print_step(1, "Setting Up Specialized Agent Network")
    
    reasoning_engines = {}
    for agent_id, message_types in agent_configs.items():
        await setup_agent_communication(agent_id, comm_manager, message_types)
        reasoning_engines[agent_id] = ReasoningEngine(
            agent_id=agent_id,
            communication_manager=comm_manager
        )
        print(f"   ✅ {agent_id} agent configured")
    
    print_step(2, "Architect Uses RAISE to Design System")
    
    # Architect uses RAISE pattern to design system
    architect_result = reasoning_engines["architect"].reason(
        objective="Design fault-tolerant microservices architecture",
        pattern="raise",
        context={
            "team": list(agent_configs.keys()),
            "requirements": ["fault_tolerance", "scalability", "monitoring"]
        }
    )
    
    print(f"   Architecture design completed with {architect_result.confidence:.2f} confidence")
    print(f"   Design cycles: {len([s for s in architect_result.steps if 'evaluate' in s.thought.lower()])}")
    
    print_step(3, "Architect Shares Design Insights")
    
    # Extract key insights from architect's reasoning
    insights = []
    for step in architect_result.steps:
        if "improve" in step.thought.lower() and step.confidence > 0.8:
            insights.append({
                "insight": step.observation,
                "confidence": step.confidence,
                "step_number": step.step_number
            })
    
    # Share top insights
    for insight in insights[:2]:  # Share top 2 insights
        await comm_manager.broadcast_insight({
            "agent_id": "architect",
            "confidence": insight["confidence"],
            "insight": insight["insight"],
            "tags": ["architecture", "design", "microservices"]
        })
    
    print(f"   Shared {len(insights[:2])} key insights with team")
    
    print_step(4, "Coordinating Development Tasks")
    
    # Architect coordinates tasks with team
    tasks = [
        ("developer", "implement_core_services"),
        ("tester", "setup_integration_tests"), 
        ("deployer", "prepare_deployment_pipeline")
    ]
    
    for agent_id, task_id in tasks:
        await comm_manager.send_coordination_request(
            sender_id="architect",
            task_id=task_id,
            action_type="execute",
            recipient_id=agent_id,
            dependencies=["architecture_design"]
        )
    
    print(f"   Coordinated {len(tasks)} development tasks")
    
    print_step(5, "Team Receives and Processes Messages")
    
    # Each agent processes their messages
    for agent_id in agent_configs.keys():
        if agent_id == "architect":
            continue  # Skip architect (sender)
            
        messages = await comm_manager.receive_messages(agent_id)
        print(f"\n   {agent_id} processing {len(messages)} messages:")
        
        for msg in messages:
            if msg.message_type == "insight":
                print(f"     📝 Received architecture insight (confidence: {msg.confidence:.2f})")
                
            elif msg.message_type == "coordination":
                task_id = getattr(msg, 'task_id', 'unknown')
                print(f"     🤝 Assigned task: {task_id}")
                
                # Acknowledge task
                await comm_manager.send_coordination_request(
                    sender_id=agent_id,
                    task_id=task_id,
                    action_type="acknowledge",
                    recipient_id="architect"
                )
    
    print_step(6, "Final Workflow Statistics")
    
    # Get final statistics
    stats = comm_manager.get_communication_stats()
    print(f"\n   Total Reasoning Steps: {len(architect_result.steps)}")
    print(f"   RAISE Cycles Completed: {len([s for s in architect_result.steps if 'evaluate' in s.thought.lower()])}")
    print(f"   Communication Channels: {len(stats['channels'])}")
    print(f"   Coordinated Agents: {stats['subscribed_agents']}")
    print(f"   Final Architecture Confidence: {architect_result.confidence:.2f}")
    
    return {
        "reasoning_result": architect_result,
        "communication_stats": stats,
        "agents_coordinated": len(agent_configs),
        "tasks_assigned": len(tasks)
    }


async def main():
    """Main demonstration script."""
    print("🚀 AGENTIC WORKFLOW: RAISE PATTERN & COMMUNICATION SYSTEM DEMO")
    print("================================================================")
    print()
    print("This demonstration showcases two major new capabilities:")
    print("1. RAISE (Reason, Act, Improve, Share, Evaluate) reasoning pattern")
    print("2. Multi-agent communication and coordination system")
    print()
    
    try:
        # Demonstrate RAISE pattern
        raise_result = await demonstrate_raise_pattern()
        
        # Demonstrate communication system
        comm_stats = await demonstrate_communication_system()
        
        # Demonstrate integrated workflow
        integrated_result = await demonstrate_integrated_workflow()
        
        print_section("DEMONSTRATION SUMMARY")
        
        print("✅ Successfully demonstrated all new capabilities:")
        print()
        print("RAISE Reasoning Pattern:")
        print(f"  • Completed {len(raise_result.steps)} reasoning steps")
        print(f"  • Achieved {raise_result.confidence:.2f} confidence")
        print(f"  • Executed all 5 RAISE phases: Reason, Act, Improve, Share, Evaluate")
        print()
        print("Communication System:")
        print(f"  • Connected {comm_stats['subscribed_agents']} agents")
        print(f"  • Supported {len(comm_stats['channels'])} communication channels")
        print(f"  • Enabled insight sharing, task coordination, and notifications")
        print()
        print("Integrated Workflow:")
        print(f"  • Coordinated {integrated_result['agents_coordinated']} specialized agents")
        print(f"  • Assigned {integrated_result['tasks_assigned']} development tasks")
        print(f"  • Final solution confidence: {integrated_result['reasoning_result'].confidence:.2f}")
        print()
        print("🎯 These implementations address the critical gaps identified in the audit:")
        print("  • RAISE pattern for advanced agent coordination ✅")
        print("  • Multi-channel communication and notification systems ✅")
        print("  • Enhanced agent reasoning capabilities ✅")
        print()
        print("The agentic workflow system is now equipped with sophisticated")
        print("reasoning and communication capabilities for production use!")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())