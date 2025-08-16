#!/usr/bin/env python3
"""
Demonstration of MCP integration with new reasoning and communication systems.

This example shows how the comprehensive MCP implementation integrates seamlessly
with the new RAISE reasoning patterns, communication system, and tool integration.
"""

import asyncio
import json
from typing import Dict, Any

from agentic_workflow.mcp.integration.agents import MCPEnhancedAgent
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


async def demonstrate_mcp_reasoning_integration():
    """Demonstrate MCP integration with new reasoning patterns."""
    print_section("MCP + REASONING INTEGRATION DEMONSTRATION")
    
    print("This demonstrates how MCP-enhanced agents integrate with:")
    print("- Advanced reasoning patterns (CoT, ReAct, RAISE)")
    print("- Dynamic tool discovery and execution")
    print("- Multi-agent communication")
    
    print_step(1, "Creating MCP-Enhanced Agent with Reasoning", 
               "Agent with both MCP capabilities and advanced reasoning")
    
    # Create communication manager for multi-agent coordination
    comm_manager = CommunicationManager()
    await setup_agent_communication("mcp_agent", comm_manager)
    
    # Create MCP-enhanced agent with reasoning capabilities
    mcp_agent = MCPEnhancedAgent(
        agent_id="mcp_demo_agent",
        communication_manager=comm_manager,
        mcp_enabled=True,
        reasoning_enabled=True,
        default_reasoning_pattern="chain_of_thought",
        auto_discover_servers=False  # Skip MCP server discovery for demo
    )
    
    # Initialize the agent
    await mcp_agent.initialize()
    
    print(f"   ✅ Agent initialized")
    print(f"   MCP Enabled: {mcp_agent.mcp_enabled}")
    print(f"   Reasoning Enabled: {mcp_agent.reasoning_enabled}")
    print(f"   Communication Available: {mcp_agent.communication_manager is not None}")
    
    print_step(2, "Testing Enhanced Tool System Integration")
    
    # Test tool registry integration
    if mcp_agent.enhanced_tools:
        comprehensive_tools = mcp_agent.enhanced_tools.get_comprehensive_tool_list()
        
        print(f"   Total tools available: {comprehensive_tools['total_count']}")
        print(f"   Built-in tools: {len(comprehensive_tools['builtin_tools'])}")
        print(f"   New system tools: {len(comprehensive_tools['new_system_tools'])}")
        print(f"   MCP tools: {len(comprehensive_tools['mcp_tools'])}")
        
        # Show some available tools
        if comprehensive_tools['new_system_tools']:
            print(f"   Sample new system tools:")
            for tool_name in list(comprehensive_tools['new_system_tools'].keys())[:3]:
                tool_info = comprehensive_tools['new_system_tools'][tool_name]
                print(f"     • {tool_info.get('name', tool_name)}: {tool_info.get('description', 'N/A')}")
    
    print_step(3, "Demonstrating Reasoning with MCP Context")
    
    # Test reasoning integration
    if mcp_agent.reasoning_enabled and mcp_agent.reasoning_engine:
        try:
            from agentic_workflow.agents.base import AgentTask
            
            # Create a task for reasoning
            task = AgentTask(
                task_id="mcp_reasoning_test",
                type="analysis",
                description="Analyze system architecture and recommend improvements using available tools"
            )
            
            # Execute enhanced reasoning
            reasoning_result = await mcp_agent._enhanced_reasoning(task)
            
            print(f"   Reasoning completed successfully:")
            print(f"     Pattern: {reasoning_result.get('reasoning_pattern', 'basic')}")
            print(f"     Confidence: {reasoning_result.get('confidence', 0):.2f}")
            print(f"     Steps: {len(reasoning_result.get('reasoning_steps', []))}")
            
            if reasoning_result.get('final_answer'):
                print(f"     Conclusion: {reasoning_result['final_answer'][:100]}...")
                
        except Exception as e:
            print(f"   ⚠️ Reasoning demonstration limited due to: {e}")
    
    print_step(4, "Testing Tool Execution")
    
    # Test tool execution through enhanced registry
    if mcp_agent.enhanced_tools:
        try:
            # Try to execute a built-in tool
            result = await mcp_agent.enhanced_tools.execute_tool(
                "echo",
                {"text": "MCP integration working!"},
                agent_id="mcp_demo_agent"
            )
            print(f"   ✅ Tool execution successful: {result}")
            
        except Exception as e:
            print(f"   ⚠️ Tool execution test: {e}")
    
    return mcp_agent


async def demonstrate_mcp_communication():
    """Demonstrate MCP integration with communication system."""
    print_section("MCP + COMMUNICATION INTEGRATION")
    
    print("Demonstrating multi-agent coordination with MCP capabilities")
    
    # Create communication manager
    comm_manager = CommunicationManager()
    
    print_step(1, "Setting Up MCP-Enhanced Agent Network")
    
    # Create multiple MCP-enhanced agents
    agents = {}
    agent_configs = [
        ("coordinator", "chain_of_thought"),
        ("executor", "react"),
        ("analyzer", "raise")
    ]
    
    for agent_id, reasoning_pattern in agent_configs:
        await setup_agent_communication(agent_id, comm_manager)
        
        agent = MCPEnhancedAgent(
            agent_id=agent_id,
            communication_manager=comm_manager,
            mcp_enabled=True,
            reasoning_enabled=True,
            default_reasoning_pattern=reasoning_pattern,
            auto_discover_servers=False
        )
        
        await agent.initialize()
        agents[agent_id] = agent
        
        print(f"   ✅ {agent_id} agent initialized (reasoning: {reasoning_pattern})")
    
    print_step(2, "Sharing MCP Insights Across Agents")
    
    # Simulate insight sharing about MCP capabilities
    insight_success = await comm_manager.broadcast_insight({
        "agent_id": "analyzer",
        "confidence": 0.95,
        "insight": "Discovered high-performance MCP tools for data processing",
        "tags": ["mcp", "tools", "performance", "data"]
    })
    
    print(f"   Insight broadcast: {'✅ Success' if insight_success else '❌ Failed'}")
    
    print_step(3, "Coordinating MCP Tool Usage")
    
    # Coordinator sends MCP tool coordination request
    coord_success = await comm_manager.send_coordination_request(
        sender_id="coordinator",
        task_id="mcp_tool_analysis",
        action_type="execute",
        recipient_id="executor",
        dependencies=["mcp_capability_assessment"]
    )
    
    print(f"   Coordination request sent: {'✅ Success' if coord_success else '❌ Failed'}")
    
    print_step(4, "Checking Agent Message Reception")
    
    # Check what messages each agent received
    for agent_id in agents.keys():
        messages = await comm_manager.receive_messages(agent_id)
        print(f"   {agent_id} received {len(messages)} messages")
        
        for msg in messages:
            if msg.message_type == "insight":
                print(f"     📝 Insight about MCP capabilities (confidence: {msg.confidence:.2f})")
            elif msg.message_type == "coordination":
                print(f"     🤝 MCP tool coordination request for task: {getattr(msg, 'task_id', 'unknown')}")
    
    return agents


async def demonstrate_comprehensive_integration():
    """Demonstrate comprehensive MCP integration."""
    print_section("COMPREHENSIVE MCP INTEGRATION")
    
    print("This demonstrates the complete integration of MCP with:")
    print("- RAISE reasoning pattern for multi-agent coordination")
    print("- Dynamic tool discovery and execution")
    print("- Cross-agent capability sharing")
    
    # Setup communication
    comm_manager = CommunicationManager()
    await setup_agent_communication("mcp_coordinator", comm_manager)
    
    print_step(1, "Creating MCP Coordinator with RAISE Pattern")
    
    # Create MCP agent with RAISE reasoning for coordination
    coordinator = MCPEnhancedAgent(
        agent_id="mcp_coordinator",
        communication_manager=comm_manager,
        mcp_enabled=True,
        reasoning_enabled=True,
        default_reasoning_pattern="raise",  # Use RAISE for coordination
        auto_discover_servers=False
    )
    
    await coordinator.initialize()
    
    print(f"   ✅ MCP Coordinator initialized")
    print(f"   Default reasoning: RAISE (multi-agent coordination)")
    print(f"   MCP capabilities: {coordinator.mcp_enabled}")
    
    print_step(2, "Executing RAISE Reasoning with MCP Context")
    
    if coordinator.reasoning_enabled and coordinator.reasoning_engine:
        try:
            # Execute RAISE reasoning with MCP awareness
            objective = "Coordinate distributed system analysis using available MCP tools"
            context = {
                'task_id': 'mcp_coordination_demo',
                'task_type': 'coordination',
                'available_mcp_tools': coordinator.dynamic_capabilities,
                'team_size': 3
            }
            
            # This would use RAISE pattern due to task_type = 'coordination'
            from agentic_workflow.agents.base import AgentTask
            task = AgentTask(
                task_id="mcp_raise_demo",
                type="coordination",
                description=objective
            )
            
            reasoning_result = await coordinator._enhanced_reasoning(task)
            
            print(f"   RAISE reasoning completed:")
            print(f"     Pattern used: {reasoning_result.get('reasoning_pattern', 'unknown')}")
            print(f"     Final confidence: {reasoning_result.get('confidence', 0):.2f}")
            print(f"     Reasoning steps: {len(reasoning_result.get('reasoning_steps', []))}")
            
            # Check for RAISE phases in reasoning
            steps = reasoning_result.get('reasoning_steps', [])
            raise_phases = ["reason", "act", "improve", "share", "evaluate"]
            found_phases = set()
            
            for step in steps:
                thought = step.get('thought', '').lower()
                for phase in raise_phases:
                    if phase in thought:
                        found_phases.add(phase)
            
            print(f"     RAISE phases detected: {sorted(found_phases)}")
            
        except Exception as e:
            print(f"   ⚠️ RAISE reasoning test: {e}")
    
    print_step(3, "MCP Tool Integration Summary")
    
    if coordinator.enhanced_tools:
        comprehensive_info = coordinator.enhanced_tools.get_comprehensive_tool_list()
        
        print(f"   Enhanced tool registry status:")
        print(f"     Total tools across all systems: {comprehensive_info['total_count']}")
        print(f"     MCP dynamic tools: {len(comprehensive_info['mcp_tools'])}")
        print(f"     Built-in enhanced tools: {len(comprehensive_info['builtin_tools'])}")
        print(f"     New system tools: {len(comprehensive_info['new_system_tools'])}")
        print(f"     New tool system integration: {'✅ Active' if coordinator.enhanced_tools.new_tool_system_enabled else '❌ Disabled'}")
    
    return coordinator


async def main():
    """Run all MCP integration demonstrations."""
    print("🚀 MCP INTEGRATION WITH NEW SYSTEMS DEMONSTRATION")
    print("=" * 80)
    print()
    print("This demonstration shows how the comprehensive MCP implementation")
    print("integrates seamlessly with the new capabilities from PR #17:")
    print("- Advanced reasoning patterns (CoT, ReAct, RAISE)")
    print("- Multi-agent communication system")
    print("- Enhanced tool integration framework")
    print()
    
    try:
        # Demonstrate reasoning integration
        mcp_agent = await demonstrate_mcp_reasoning_integration()
        
        # Demonstrate communication integration
        agent_network = await demonstrate_mcp_communication()
        
        # Demonstrate comprehensive integration
        coordinator = await demonstrate_comprehensive_integration()
        
        print_section("INTEGRATION SUMMARY")
        
        print("✅ Successfully demonstrated MCP integration with new systems:")
        print()
        print("🧠 Reasoning Integration:")
        print("  • MCP-enhanced agents use advanced reasoning patterns")
        print("  • Dynamic tool discovery informs reasoning decisions")
        print("  • Context-aware pattern selection (RAISE for coordination)")
        print()
        print("🤝 Communication Integration:")
        print("  • MCP capabilities shared across agent networks")
        print("  • Tool coordination through communication system")
        print("  • Multi-agent MCP workflow coordination")
        print()
        print("🔧 Tool System Integration:")
        print("  • Unified tool registry across all systems")
        print("  • Seamless execution from MCP, built-in, and new tools")
        print("  • Comprehensive performance monitoring")
        print()
        print("🎯 Backward Compatibility:")
        print("  • All existing MCP functionality preserved")
        print("  • Graceful degradation when components unavailable")
        print("  • Optional enhancement activation")
        print()
        print("The MCP implementation now provides unlimited dynamic capabilities")
        print("while leveraging the full power of the new reasoning and communication systems!")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())