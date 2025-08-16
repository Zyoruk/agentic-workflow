"""
Example: Basic MCP integration with agentic workflow system.

This example demonstrates how to set up and use MCP capabilities
with agents in the agentic workflow system.
"""

import asyncio
import logging
from pathlib import Path

from agentic_workflow.mcp import MCPClient, MCPServerConfig
from agentic_workflow.mcp.client.registry import MCPServerRegistry
from agentic_workflow.mcp.tools.enhanced_registry import EnhancedToolRegistry
from agentic_workflow.mcp.integration.agents import MCPEnhancedAgent
from agentic_workflow.agents.base import AgentTask


async def main():
    """Main example function."""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    print("=== MCP Integration Example ===")
    
    # 1. Create MCP client
    print("\n1. Creating MCP client...")
    mcp_client = MCPClient(max_connections=5)
    await mcp_client.initialize()
    
    # 2. Create server registry
    print("2. Setting up server registry...")
    registry = MCPServerRegistry()
    await registry.initialize(mcp_client)
    
    # 3. Define server configurations
    print("3. Configuring MCP servers...")
    
    # Example server configurations (these would need actual MCP servers to work)
    server_configs = [
        MCPServerConfig(
            name="filesystem",
            command=["mcp-server-filesystem"],
            args=["--root", str(Path.cwd())],
            description="File system access server",
            timeout=30
        ),
        MCPServerConfig(
            name="git",
            command=["mcp-server-git"],
            args=["--repository", str(Path.cwd())],
            description="Git repository server",
            timeout=60
        ),
        # Note: These servers would need to be installed separately
        # This is just for demonstration
    ]
    
    # 4. Register servers
    print("4. Registering servers...")
    connection_results = {}
    for config in server_configs:
        try:
            success = await registry.register_server(config, category="development")
            connection_results[config.name] = success
            if success:
                print(f"   ✓ Connected to {config.name}")
            else:
                print(f"   ✗ Failed to connect to {config.name}")
        except Exception as e:
            print(f"   ✗ Error connecting to {config.name}: {e}")
            connection_results[config.name] = False
    
    # 5. Create enhanced tool registry
    print("5. Setting up enhanced tool registry...")
    tool_registry = EnhancedToolRegistry(mcp_client)
    await tool_registry.initialize()
    
    # 6. List available tools
    print("6. Available tools:")
    all_tools = tool_registry.list_tools()
    print(f"   Total tools: {len(all_tools)}")
    
    builtin_tools = tool_registry.list_tools(source="builtin")
    mcp_tools = tool_registry.list_tools(source="mcp")
    
    print(f"   Built-in tools: {len(builtin_tools)}")
    for tool in builtin_tools[:3]:  # Show first 3
        print(f"     - {tool.name}: {tool.description}")
    
    print(f"   MCP tools: {len(mcp_tools)}")
    for tool in mcp_tools[:3]:  # Show first 3
        print(f"     - {tool.name}: {tool.description}")
    
    # 7. Create MCP-enhanced agent
    print("\n7. Creating MCP-enhanced agent...")
    agent = MCPEnhancedAgent(
        agent_id="example_agent",
        mcp_enabled=True,
        mcp_servers=server_configs,
        mcp_categories=["development"],
        auto_discover_servers=True
    )
    
    await agent.initialize()
    
    # 8. Get agent status
    print("8. Agent MCP status:")
    status = await agent.get_mcp_status()
    print(f"   MCP enabled: {status['mcp_enabled']}")
    print(f"   MCP initialized: {status['mcp_initialized']}")
    print(f"   Connected servers: {len([s for s in status['connected_servers'].values() if s])}")
    print(f"   Available capabilities: {status['available_capabilities']}")
    
    # 9. Execute example tasks
    print("\n9. Executing example tasks...")
    
    # Example task 1: Simple built-in tool
    task1 = AgentTask(
        type="utility",
        description="Echo a message",
        message="Hello from MCP-enhanced agent!"
    )
    
    try:
        result1 = await agent.execute(task1)
        print(f"   Task 1 result: {result1.success}")
        if result1.success:
            print(f"   Steps taken: {len(result1.steps_taken)}")
            print(f"   MCP tools used: {result1.metadata.get('mcp_tools_used', [])}")
    except Exception as e:
        print(f"   Task 1 failed: {e}")
    
    # Example task 2: File operation (if filesystem server connected)
    if connection_results.get("filesystem", False):
        task2 = AgentTask(
            type="file_analysis",
            description="Analyze a Python file",
            file_path="example_mcp_usage.py"
        )
        
        try:
            result2 = await agent.execute(task2)
            print(f"   Task 2 result: {result2.success}")
            if result2.success:
                print(f"   Execution time: {result2.execution_time:.2f}s")
        except Exception as e:
            print(f"   Task 2 failed: {e}")
    
    # 10. Tool recommendations
    print("\n10. Tool recommendations for 'analyze code file':")
    try:
        recommendations = tool_registry.get_tool_recommendations("analyze code file", limit=3)
        for i, rec in enumerate(recommendations, 1):
            tool_name = rec.name
            score = rec.usage_count + (1 if "code" in rec.description.lower() else 0)
            print(f"    {i}. {tool_name} (score: {score}) - {rec.description}")
    except Exception as e:
        print(f"   Error getting recommendations: {e}")
    
    # 11. Performance metrics
    print("\n11. Performance metrics:")
    try:
        metrics = tool_registry.get_performance_metrics()
        if metrics:
            for tool_name, tool_metrics in list(metrics.items())[:3]:
                print(f"   {tool_name}:")
                print(f"     Executions: {tool_metrics.get('total_executions', 0)}")
                print(f"     Success rate: {tool_metrics.get('success_rate', 0):.2%}")
                print(f"     Avg time: {tool_metrics.get('average_time', 0):.3f}s")
        else:
            print("   No performance metrics available yet")
    except Exception as e:
        print(f"   Error getting metrics: {e}")
    
    # 12. Cleanup
    print("\n12. Cleaning up...")
    try:
        await tool_registry.close()
        await agent.close()
        await mcp_client.close()
        print("   Cleanup completed successfully")
    except Exception as e:
        print(f"   Cleanup error: {e}")
    
    print("\n=== Example completed ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"\nExample failed: {e}")
        import traceback
        traceback.print_exc()