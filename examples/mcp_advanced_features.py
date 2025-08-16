"""
Example: Advanced MCP features including security and memory integration.

This example demonstrates advanced MCP features like security policies,
memory integration, and multi-agent coordination.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

from agentic_workflow.mcp import MCPClient, MCPServerConfig
from agentic_workflow.mcp.client.registry import MCPServerRegistry
from agentic_workflow.mcp.tools.enhanced_registry import EnhancedToolRegistry
from agentic_workflow.mcp.integration.agents import MCPEnhancedAgent
from agentic_workflow.mcp.integration.security import SecurityManager, SecurityPolicy, SecurityLevel, PermissionType
from agentic_workflow.mcp.integration.memory import MCPMemoryManager
from agentic_workflow.agents.base import AgentTask
from agentic_workflow.memory.manager import MemoryManager


async def main():
    """Advanced MCP features example."""
    logging.basicConfig(level=logging.INFO)
    
    print("=== Advanced MCP Features Example ===")
    
    # 1. Setup security manager
    print("\n1. Setting up security framework...")
    security_manager = SecurityManager()
    await security_manager.initialize()
    
    # Create security policies
    strict_policy = SecurityPolicy(
        name="strict_development",
        description="Strict policy for development tools",
        server_patterns=["git", "filesystem"],
        tool_patterns=["*"],
        allowed_permissions={PermissionType.READ, PermissionType.EXECUTE},
        denied_operations={"delete", "rm", "drop"},
        security_level=SecurityLevel.HIGH,
        max_execution_time=120,
        audit_required=True
    )
    
    await security_manager.add_policy(strict_policy, is_default=True)
    print("   ✓ Security policies configured")
    
    # 2. Setup memory integration
    print("2. Setting up memory integration...")
    memory_manager = MemoryManager()
    await memory_manager.initialize()
    
    mcp_memory = MCPMemoryManager(memory_manager)
    await mcp_memory.initialize()
    print("   ✓ Memory integration ready")
    
    # 3. Create MCP client with security
    print("3. Creating secure MCP client...")
    mcp_client = MCPClient(max_connections=10)
    await mcp_client.initialize()
    
    # Add security validation callback
    async def security_validator(agent_id, server_config):
        return await security_manager.validate_server_connection(agent_id, server_config)
    
    # 4. Setup enhanced registry with memory
    print("4. Setting up enhanced tool registry...")
    tool_registry = EnhancedToolRegistry(mcp_client)
    await tool_registry.initialize()
    
    # 5. Create multiple agents for coordination example
    print("5. Creating multiple MCP-enhanced agents...")
    
    agents = []
    for i in range(3):
        agent = MCPEnhancedAgent(
            agent_id=f"advanced_agent_{i}",
            mcp_enabled=True,
            mcp_categories=["development", "data"],
            auto_discover_servers=True,
            max_mcp_connections=5
        )
        await agent.initialize()
        agents.append(agent)
    
    print(f"   ✓ Created {len(agents)} agents")
    
    # 6. Define and execute collaborative tasks
    print("\n6. Executing collaborative tasks...")
    
    tasks = [
        AgentTask(
            type="code_analysis",
            description="Analyze Python files for code quality",
            target_files=["*.py"],
            requirements=["syntax check", "style analysis"]
        ),
        AgentTask(
            type="data_processing",
            description="Process configuration files",
            target_files=["*.yaml", "*.json"],
            requirements=["validation", "schema check"]
        ),
        AgentTask(
            type="documentation",
            description="Generate documentation from code",
            target_files=["src/**/*.py"],
            requirements=["docstring extraction", "API documentation"]
        )
    ]
    
    # Execute tasks in parallel
    results = []
    for i, task in enumerate(tasks):
        agent = agents[i % len(agents)]
        try:
            result = await agent.execute(task)
            results.append(result)
            
            # Store execution in memory
            await mcp_memory.record_execution(
                agent_id=agent.agent_id,
                server_id="builtin",
                tool_name="task_executor",
                parameters=dict(task),
                result=result.data if result.success else None,
                success=result.success,
                execution_time=result.execution_time,
                error=result.error if not result.success else None
            )
            
            print(f"   Task {i+1} ({task.task_type}) - Agent {agent.agent_id}: {'✓' if result.success else '✗'}")
            
        except Exception as e:
            print(f"   Task {i+1} failed: {e}")
    
    # 7. Analyze agent preferences
    print("\n7. Learning agent preferences...")
    for agent in agents:
        try:
            preferences = await mcp_memory.learn_agent_preferences(agent.agent_id)
            print(f"   Agent {agent.agent_id}:")
            
            # Show preferred tools
            pref_tools = preferences.get('preferred_tools', {})
            if pref_tools:
                top_tools = sorted(pref_tools.items(), 
                                 key=lambda x: x[1].get('preference_score', 0), 
                                 reverse=True)[:3]
                print(f"     Top tools: {[tool[0] for tool in top_tools]}")
            
            # Show preferred servers
            pref_servers = preferences.get('preferred_servers', {})
            if pref_servers:
                top_servers = sorted(pref_servers.items(),
                                   key=lambda x: x[1].get('preference_score', 0),
                                   reverse=True)[:2]
                print(f"     Preferred servers: {[server[0] for server in top_servers]}")
                
        except Exception as e:
            print(f"   Failed to analyze preferences for {agent.agent_id}: {e}")
    
    # 8. Get tool recommendations based on context
    print("\n8. Context-aware tool recommendations...")
    contexts = [
        "analyze Python code for security vulnerabilities",
        "process JSON configuration files",
        "generate API documentation from source code"
    ]
    
    for context in contexts:
        try:
            recommendations = await mcp_memory.recommend_tools(
                agent_id=agents[0].agent_id,
                task_context=context,
                limit=3
            )
            
            print(f"   Context: '{context[:50]}...'")
            for i, rec in enumerate(recommendations, 1):
                cap = rec['capability']
                score = rec['score']
                print(f"     {i}. {cap['name']} (score: {score:.2f}) - {cap['description'][:40]}...")
                
        except Exception as e:
            print(f"   Recommendation failed for context: {e}")
    
    # 9. Security audit and monitoring
    print("\n9. Security audit and monitoring...")
    
    # Get security metrics
    try:
        sec_metrics = security_manager.get_security_metrics()
        print(f"   Total audit events: {sec_metrics['total_audit_events']}")
        print(f"   Success rate: {sec_metrics['success_rate']:.2%}")
        print(f"   Active policies: {sec_metrics['security_policies_count']}")
        
        # Show recent security events
        recent_events = security_manager.get_audit_events(limit=5)
        if recent_events:
            print("   Recent security events:")
            for event in recent_events[-3:]:
                status = "✓" if event.success else "✗"
                print(f"     {status} {event.event_type} - {event.agent_id}")
                
    except Exception as e:
        print(f"   Security audit failed: {e}")
    
    # 10. Memory statistics
    print("\n10. Memory usage statistics...")
    try:
        memory_stats = await mcp_memory.get_memory_statistics()
        print("   Memory collections:")
        for collection_type, stats in memory_stats.items():
            if isinstance(stats, dict) and 'count' in stats:
                print(f"     {collection_type}: {stats['count']} records")
            
    except Exception as e:
        print(f"   Memory statistics failed: {e}")
    
    # 11. Performance analysis
    print("\n11. Performance analysis...")
    try:
        # Get execution history
        for agent in agents:
            history = await mcp_memory.get_execution_history(agent_id=agent.agent_id, limit=5)
            if history:
                avg_time = sum(h.get('execution_time', 0) for h in history) / len(history)
                success_rate = sum(1 for h in history if h.get('success', False)) / len(history)
                print(f"   {agent.agent_id}: {len(history)} executions, "
                      f"avg time: {avg_time:.2f}s, success: {success_rate:.1%}")
                
    except Exception as e:
        print(f"   Performance analysis failed: {e}")
    
    # 12. Export audit logs and metrics
    print("\n12. Exporting audit data...")
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audit_file = Path(f"mcp_audit_{timestamp}.json")
        
        success = await security_manager.export_audit_log(audit_file)
        if success:
            print(f"   ✓ Audit log exported to {audit_file}")
        else:
            print("   ✗ Failed to export audit log")
            
    except Exception as e:
        print(f"   Export failed: {e}")
    
    # 13. Demonstrate tool workflow
    print("\n13. Tool workflow demonstration...")
    try:
        # Create a workflow for code analysis
        workflow_created = await tool_registry.create_tool_workflow(
            "code_analysis_workflow",
            ["echo", "current_time"],  # Simple workflow with available tools
            "Basic code analysis workflow"
        )
        
        if workflow_created:
            print("   ✓ Created code analysis workflow")
            
            # Execute workflow
            workflow_results = await tool_registry.execute_workflow(
                "code_analysis_workflow",
                {"text": "Starting code analysis..."}
            )
            print(f"   ✓ Workflow executed: {len(workflow_results)} steps completed")
        else:
            print("   ✗ Failed to create workflow")
            
    except Exception as e:
        print(f"   Workflow demonstration failed: {e}")
    
    # 14. Cleanup and resource management
    print("\n14. Cleanup and resource management...")
    try:
        # Clean up old memory data (demo with 0 days retention)
        cleanup_success = await mcp_memory.cleanup_old_data(retention_days=0)
        if cleanup_success:
            print("   ✓ Memory cleanup completed")
        
        # Close all components
        for agent in agents:
            await agent.close()
        
        await tool_registry.close()
        await mcp_client.close()
        
        print("   ✓ All resources cleaned up")
        
    except Exception as e:
        print(f"   Cleanup failed: {e}")
    
    print("\n=== Advanced features example completed ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"\nExample failed: {e}")
        import traceback
        traceback.print_exc()