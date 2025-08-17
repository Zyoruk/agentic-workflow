"""
Unit tests for enhanced tool registry.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from agentic_workflow.mcp.tools.enhanced_registry import (
    EnhancedToolRegistry, Tool, BuiltinTool, MCPTool, ToolMetadata
)
from agentic_workflow.mcp.client.base import MCPClient, MCPCapability


@pytest.fixture
def sample_tool_metadata():
    """Sample tool metadata."""
    return ToolMetadata(
        name="test_tool",
        description="Test tool for testing",
        parameters={"param1": {"type": "string"}},
        source="builtin",
        category="test"
    )


@pytest.fixture
def sample_builtin_tool(sample_tool_metadata):
    """Sample built-in tool."""
    def test_func(text="hello"):
        return f"Echo: {text}"
    
    return BuiltinTool(
        name="echo_tool",
        description="Echo tool",
        func=test_func,
        parameters={"text": {"type": "string"}},
        category="utility"
    )


@pytest.fixture
def sample_mcp_capability():
    """Sample MCP capability."""
    return MCPCapability(
        name="mcp_test_tool",
        type="tool",
        description="MCP test tool",
        server_id="test_server",
        parameters={"input": {"type": "string"}}
    )


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client."""
    client = Mock(spec=MCPClient)
    client.execute_tool = AsyncMock(return_value="mcp_result")
    client.list_capabilities = AsyncMock(return_value=[])
    return client


@pytest.mark.asyncio
class TestEnhancedToolRegistry:
    """Test enhanced tool registry functionality."""
    
    async def test_initialization(self, mock_mcp_client):
        """Test tool registry initialization."""
        registry = EnhancedToolRegistry(mock_mcp_client)
        await registry.initialize()
        
        # Should have some built-in tools
        assert len(registry.builtin_tools) > 0
        assert "echo" in registry.builtin_tools
        assert "calculate" in registry.builtin_tools
        assert "current_time" in registry.builtin_tools
    
    async def test_initialization_without_mcp(self):
        """Test initialization without MCP client."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        # Should still have built-in tools
        assert len(registry.builtin_tools) > 0
        assert len(registry.mcp_tools) == 0
    
    async def test_register_builtin_tool(self, sample_builtin_tool):
        """Test registering built-in tools."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        success = await registry.register_builtin_tool(sample_builtin_tool)
        
        assert success
        assert sample_builtin_tool.metadata.name in registry.builtin_tools
        assert sample_builtin_tool.metadata.category in registry.tool_categories
    
    async def test_register_duplicate_builtin_tool(self, sample_builtin_tool):
        """Test registering duplicate built-in tool."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        # Register first time
        success1 = await registry.register_builtin_tool(sample_builtin_tool)
        assert success1
        
        # Register again (should fail)
        success2 = await registry.register_builtin_tool(sample_builtin_tool)
        assert not success2
    
    async def test_unregister_builtin_tool(self, sample_builtin_tool):
        """Test unregistering built-in tools."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        # Register then unregister
        await registry.register_builtin_tool(sample_builtin_tool)
        success = await registry.unregister_builtin_tool(sample_builtin_tool.metadata.name)
        
        assert success
        assert sample_builtin_tool.metadata.name not in registry.builtin_tools
    
    async def test_get_tool(self, sample_builtin_tool):
        """Test getting tools by name."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        await registry.register_builtin_tool(sample_builtin_tool)
        
        # Get existing tool
        tool = registry.get_tool(sample_builtin_tool.metadata.name)
        assert tool is not None
        assert tool.metadata.name == sample_builtin_tool.metadata.name
        
        # Get non-existent tool
        missing_tool = registry.get_tool("nonexistent_tool")
        assert missing_tool is None
    
    async def test_list_tools_filtering(self, sample_builtin_tool):
        """Test tool listing with filters."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        await registry.register_builtin_tool(sample_builtin_tool)
        
        # List all tools
        all_tools = registry.list_tools()
        assert len(all_tools) > 0
        
        # Filter by category
        utility_tools = registry.list_tools(category="utility")
        utility_names = [tool.name for tool in utility_tools]
        assert sample_builtin_tool.metadata.name in utility_names
        
        # Filter by source
        builtin_tools = registry.list_tools(source="builtin")
        assert len(builtin_tools) > 0
        assert all(tool.source == "builtin" for tool in builtin_tools)
        
        # Filter by tags
        tagged_tools = registry.list_tools(tags=["utility"])
        # Should return tools that have any of the specified tags
    
    async def test_execute_builtin_tool(self):
        """Test executing built-in tools."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        # Execute echo tool
        result = await registry.execute_tool("echo", {"text": "test message"})
        assert result == "test message"
        
        # Execute current_time tool
        result = await registry.execute_tool("current_time")
        assert isinstance(result, str)
        assert "T" in result  # ISO format timestamp
    
    async def test_execute_nonexistent_tool(self):
        """Test executing non-existent tool."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        with pytest.raises(ValueError, match="Tool 'nonexistent' not found"):
            await registry.execute_tool("nonexistent")
    
    async def test_search_tools(self, sample_builtin_tool):
        """Test tool search functionality."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        await registry.register_builtin_tool(sample_builtin_tool)
        
        # Search by name
        results = registry.search_tools("echo")
        assert len(results) > 0
        assert any("echo" in tool.name.lower() for tool in results)
        
        # Search by description
        results = registry.search_tools("time")
        assert len(results) > 0
    
    async def test_tool_recommendations(self, sample_builtin_tool):
        """Test tool recommendation system."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        await registry.register_builtin_tool(sample_builtin_tool)
        
        # Get recommendations
        recommendations = registry.get_tool_recommendations("echo some text", limit=3)
        
        assert len(recommendations) <= 3
        # Should recommend echo tool for echo context
        recommended_names = [rec.name for rec in recommendations]
        assert "echo" in recommended_names or sample_builtin_tool.metadata.name in recommended_names
    
    async def test_execution_history_tracking(self):
        """Test execution history tracking."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        # Execute a tool
        await registry.execute_tool("echo", {"text": "test"})
        
        # Check history
        history = registry.get_execution_history()
        assert len(history) >= 1
        
        recent_execution = history[-1]
        assert recent_execution['tool_name'] == "echo"
        assert recent_execution['success'] == True
        assert 'execution_time' in recent_execution
        assert 'timestamp' in recent_execution
    
    async def test_performance_metrics(self):
        """Test performance metrics tracking."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        # Execute tool multiple times
        for i in range(3):
            await registry.execute_tool("echo", {"text": f"test_{i}"})
        
        # Check metrics
        metrics = registry.get_performance_metrics("echo")
        assert metrics['total_executions'] == 3
        assert metrics['successful_executions'] == 3
        assert metrics['success_rate'] == 1.0
        assert metrics['average_time'] > 0
    
    async def test_tool_aliases(self, sample_builtin_tool):
        """Test tool alias functionality."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        await registry.register_builtin_tool(sample_builtin_tool)
        
        # Add alias
        success = registry.add_tool_alias("echo_alias", sample_builtin_tool.metadata.name)
        assert success
        
        # Use alias
        tool_via_alias = registry.get_tool("echo_alias")
        tool_direct = registry.get_tool(sample_builtin_tool.metadata.name)
        
        assert tool_via_alias is not None
        assert tool_via_alias == tool_direct
    
    async def test_tool_workflows(self, sample_builtin_tool):
        """Test tool workflow creation and execution."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        await registry.register_builtin_tool(sample_builtin_tool)
        
        # Create workflow
        success = await registry.create_tool_workflow(
            "test_workflow",
            ["echo", "current_time"],
            "Test workflow"
        )
        assert success
        
        # Execute workflow
        results = await registry.execute_workflow("test_workflow", {"text": "workflow test"})
        assert len(results) == 2
        assert results[0] == "workflow test"  # echo result
        assert isinstance(results[1], str)  # current_time result
    
    async def test_workflow_with_missing_tools(self):
        """Test workflow with missing tools."""
        registry = EnhancedToolRegistry()
        await registry.initialize()
        
        # Try to create workflow with non-existent tool
        success = await registry.create_tool_workflow(
            "invalid_workflow",
            ["nonexistent_tool"],
            "Invalid workflow"
        )
        assert not success
    
    async def test_mcp_tool_integration(self, sample_mcp_capability, mock_mcp_client):
        """Test MCP tool integration."""
        registry = EnhancedToolRegistry(mock_mcp_client)
        
        # Simulate capability addition
        await registry._on_capability_added(sample_mcp_capability)
        
        # Check MCP tool was added
        assert sample_mcp_capability.name in registry.mcp_tools
        
        # Execute MCP tool
        result = await registry.execute_tool(sample_mcp_capability.name, {"input": "test"})
        assert result == "mcp_result"
        
        # Verify MCP client was called
        mock_mcp_client.execute_tool.assert_called_once_with(
            sample_mcp_capability.name,
            {"input": "test"},
            sample_mcp_capability.server_id
        )
    
    async def test_mcp_tool_removal(self, sample_mcp_capability, mock_mcp_client):
        """Test MCP tool removal."""
        registry = EnhancedToolRegistry(mock_mcp_client)
        
        # Add then remove capability
        await registry._on_capability_added(sample_mcp_capability)
        assert sample_mcp_capability.name in registry.mcp_tools
        
        await registry._on_capability_removed(sample_mcp_capability)
        assert sample_mcp_capability.name not in registry.mcp_tools
    
    async def test_refresh_mcp_tools(self, mock_mcp_client):
        """Test refreshing MCP tools."""
        # Setup mock client to return capabilities
        mock_capability = MCPCapability(
            name="refreshed_tool",
            type="tool",
            description="Refreshed tool",
            server_id="test_server"
        )
        mock_mcp_client.list_capabilities.return_value = [mock_capability]
        
        registry = EnhancedToolRegistry(mock_mcp_client)
        await registry.initialize()
        
        # Add initial tool
        old_capability = MCPCapability(
            name="old_tool",
            type="tool",
            description="Old tool",
            server_id="test_server"
        )
        registry.mcp_tools["old_tool"] = MCPTool(old_capability, mock_mcp_client)
        
        # Refresh tools
        await registry.refresh_mcp_tools()
        
        # Old tool should be removed, new tool should be added
        assert "old_tool" not in registry.mcp_tools
        assert "refreshed_tool" in registry.mcp_tools
    
    async def test_close_cleanup(self, mock_mcp_client):
        """Test registry cleanup on close."""
        registry = EnhancedToolRegistry(mock_mcp_client)
        await registry.initialize()
        
        # Add some data
        await registry.execute_tool("echo", {"text": "test"})
        
        initial_builtin_count = len(registry.builtin_tools)
        initial_history_count = len(registry.execution_history)
        
        await registry.close()
        
        # Data should be cleared
        assert len(registry.builtin_tools) == 0
        assert len(registry.mcp_tools) == 0
        assert len(registry.execution_history) == 0
        assert len(registry.performance_metrics) == 0


class TestToolMetadata:
    """Test tool metadata functionality."""
    
    def test_metadata_creation(self, sample_tool_metadata):
        """Test metadata creation with defaults."""
        assert sample_tool_metadata.name == "test_tool"
        assert sample_tool_metadata.source == "builtin"
        assert sample_tool_metadata.usage_count == 0
        assert isinstance(sample_tool_metadata.created_at, datetime)
        assert sample_tool_metadata.tags == []
    
    def test_metadata_with_custom_values(self):
        """Test metadata with custom values."""
        metadata = ToolMetadata(
            name="custom_tool",
            description="Custom tool",
            parameters={},
            source="mcp",
            category="custom",
            tags=["tag1", "tag2"],
            version="2.0.0"
        )
        
        assert metadata.name == "custom_tool"
        assert metadata.source == "mcp"
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.version == "2.0.0"


class TestBuiltinTool:
    """Test built-in tool functionality."""
    
    @pytest.mark.asyncio
    async def test_builtin_tool_execution(self, sample_builtin_tool):
        """Test built-in tool execution."""
        result = await sample_builtin_tool.execute(text="hello world")
        assert result == "Echo: hello world"
    
    @pytest.mark.asyncio
    async def test_builtin_tool_metadata(self, sample_builtin_tool):
        """Test built-in tool metadata."""
        metadata = sample_builtin_tool.metadata
        assert metadata.name == "echo_tool"
        assert metadata.source == "builtin"
        assert metadata.category == "utility"
    
    @pytest.mark.asyncio
    async def test_builtin_tool_parameter_validation(self, sample_builtin_tool):
        """Test parameter validation."""
        # This is a basic test - in a real implementation, 
        # you'd want more sophisticated validation
        is_valid = await sample_builtin_tool.validate_parameters({"text": "test"})
        assert is_valid


class TestMCPTool:
    """Test MCP tool functionality."""
    
    @pytest.mark.asyncio
    async def test_mcp_tool_creation(self, sample_mcp_capability, mock_mcp_client):
        """Test MCP tool creation."""
        tool = MCPTool(sample_mcp_capability, mock_mcp_client)
        
        assert tool.metadata.name == sample_mcp_capability.name
        assert tool.metadata.source == "mcp"
        assert tool.metadata.description == sample_mcp_capability.description
    
    @pytest.mark.asyncio
    async def test_mcp_tool_execution(self, sample_mcp_capability, mock_mcp_client):
        """Test MCP tool execution."""
        tool = MCPTool(sample_mcp_capability, mock_mcp_client)
        
        result = await tool.execute(input="test input")
        
        assert result == "mcp_result"
        mock_mcp_client.execute_tool.assert_called_once_with(
            sample_mcp_capability.name,
            {"input": "test input"},
            sample_mcp_capability.server_id
        )
    
    @pytest.mark.asyncio
    async def test_mcp_tool_usage_tracking(self, sample_mcp_capability, mock_mcp_client):
        """Test usage tracking in MCP tools."""
        tool = MCPTool(sample_mcp_capability, mock_mcp_client)
        
        initial_usage = tool.metadata.usage_count
        initial_last_used = tool.metadata.last_used
        
        await tool.execute(input="test")
        
        assert tool.metadata.usage_count == initial_usage + 1
        assert tool.metadata.last_used != initial_last_used