# MCP Implementation Guide

## Overview

This guide provides step-by-step instructions for integrating the Model Context Protocol (MCP) with the agentic workflow system. The implementation follows a phased approach that maintains backward compatibility while gradually adding MCP capabilities.

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- Basic MCP client implementation
- Core server connectivity
- Tool system enhancement
- Security framework

### Phase 2: Core Integration (Weeks 3-4)
- Agent framework enhancement
- Memory system integration
- Essential server connections
- Basic monitoring

### Phase 3: Advanced Features (Weeks 5-6)
- Reasoning pattern enhancement
- Performance optimization
- Custom server development
- Advanced monitoring

### Phase 4: Production Readiness (Weeks 7-8)
- Security hardening
- Performance tuning
- Documentation completion
- Deployment automation

## Phase 1: Foundation Implementation

### 1.1 Project Structure Setup

Create the MCP integration structure:

```bash
# Create MCP module structure
mkdir -p src/agentic_workflow/mcp
mkdir -p src/agentic_workflow/mcp/client
mkdir -p src/agentic_workflow/mcp/servers
mkdir -p src/agentic_workflow/mcp/tools
mkdir -p tests/unit/mcp
mkdir -p tests/integration/mcp
```

### 1.2 Dependencies Installation

Add MCP dependencies to `pyproject.toml`:

```toml
[project.optional-dependencies]
mcp = [
    "mcp>=1.0.0",
    "mcp-python>=1.0.0",
    "httpx>=0.24.0",
    "websockets>=11.0",
    "jsonschema>=4.17.0",
    "tenacity>=8.2.0",
]
```

Install dependencies:
```bash
pip install -e ".[mcp]"
```

### 1.3 Core MCP Client Implementation

Create the base MCP client:

```python
# src/agentic_workflow/mcp/client/base.py
"""
Core MCP client implementation for agentic workflow system.
"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.models import Tool, Resource, Prompt

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    name: str
    command: List[str]
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3


@dataclass
class MCPCapability:
    """Represents an MCP capability (tool, resource, or prompt)."""
    name: str
    type: str  # 'tool', 'resource', 'prompt'
    description: str
    server_id: str
    parameters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPClient:
    """
    Central MCP client for the agentic workflow system.
    
    Manages connections to multiple MCP servers and provides
    a unified interface for agents to access MCP capabilities.
    """
    
    def __init__(self):
        self.servers: Dict[str, ClientSession] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.capabilities_cache: Dict[str, List[MCPCapability]] = {}
        self.connection_status: Dict[str, bool] = {}
        self._lock = asyncio.Lock()
        
    async def register_server(self, config: MCPServerConfig) -> bool:
        """
        Register and connect to an MCP server.
        
        Args:
            config: Server configuration
            
        Returns:
            True if connection successful, False otherwise
        """
        async with self._lock:
            try:
                logger.info(f"Registering MCP server: {config.name}")
                
                # Create server parameters
                server_params = StdioServerParameters(
                    command=config.command,
                    args=config.args or [],
                    env=config.env or {}
                )
                
                # Create and start session
                session = ClientSession(server_params)
                await session.initialize()
                
                # Store connection
                self.servers[config.name] = session
                self.server_configs[config.name] = config
                self.connection_status[config.name] = True
                
                # Cache capabilities
                await self._cache_server_capabilities(config.name)
                
                logger.info(f"Successfully connected to MCP server: {config.name}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {config.name}: {e}")
                self.connection_status[config.name] = False
                return False
    
    async def _cache_server_capabilities(self, server_id: str) -> None:
        """Cache capabilities for a server."""
        try:
            session = self.servers[server_id]
            capabilities = []
            
            # Get tools
            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                capabilities.append(MCPCapability(
                    name=tool.name,
                    type='tool',
                    description=tool.description or '',
                    server_id=server_id,
                    parameters=tool.inputSchema,
                    metadata={'tool': tool}
                ))
            
            # Get resources
            resources_result = await session.list_resources()
            for resource in resources_result.resources:
                capabilities.append(MCPCapability(
                    name=resource.name,
                    type='resource',
                    description=resource.description or '',
                    server_id=server_id,
                    metadata={'resource': resource}
                ))
            
            # Get prompts
            prompts_result = await session.list_prompts()
            for prompt in prompts_result.prompts:
                capabilities.append(MCPCapability(
                    name=prompt.name,
                    type='prompt',
                    description=prompt.description or '',
                    server_id=server_id,
                    parameters=prompt.arguments,
                    metadata={'prompt': prompt}
                ))
            
            self.capabilities_cache[server_id] = capabilities
            logger.info(f"Cached {len(capabilities)} capabilities for server {server_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache capabilities for {server_id}: {e}")
    
    async def discover_capabilities(self) -> Dict[str, List[MCPCapability]]:
        """
        Discover all capabilities across all connected servers.
        
        Returns:
            Dictionary mapping server IDs to their capabilities
        """
        return self.capabilities_cache.copy()
    
    async def execute_tool(
        self, 
        server_id: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Execute a tool on an MCP server.
        
        Args:
            server_id: ID of the MCP server
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if server_id not in self.servers:
            raise ValueError(f"Server {server_id} not connected")
        
        if not self.connection_status.get(server_id, False):
            raise ConnectionError(f"Server {server_id} not available")
        
        try:
            session = self.servers[server_id]
            result = await session.call_tool(tool_name, arguments)
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {server_id}.{tool_name}: {e}")
            raise
    
    async def get_resource(
        self, 
        server_id: str, 
        resource_uri: str
    ) -> Any:
        """
        Retrieve a resource from an MCP server.
        
        Args:
            server_id: ID of the MCP server
            resource_uri: URI of the resource
            
        Returns:
            Resource content
        """
        if server_id not in self.servers:
            raise ValueError(f"Server {server_id} not connected")
        
        try:
            session = self.servers[server_id]
            result = await session.read_resource(resource_uri)
            return result
            
        except Exception as e:
            logger.error(f"Resource retrieval failed: {server_id}.{resource_uri}: {e}")
            raise
    
    async def health_check(self, server_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Check health of MCP servers.
        
        Args:
            server_id: Specific server to check, or None for all
            
        Returns:
            Health status for servers
        """
        servers_to_check = [server_id] if server_id else list(self.servers.keys())
        health_status = {}
        
        for sid in servers_to_check:
            try:
                if sid in self.servers:
                    # Simple ping to check connectivity
                    await self.servers[sid].list_tools()
                    health_status[sid] = True
                    self.connection_status[sid] = True
                else:
                    health_status[sid] = False
                    
            except Exception as e:
                logger.warning(f"Health check failed for server {sid}: {e}")
                health_status[sid] = False
                self.connection_status[sid] = False
        
        return health_status
    
    async def disconnect_server(self, server_id: str) -> None:
        """Disconnect from an MCP server."""
        if server_id in self.servers:
            try:
                await self.servers[server_id].close()
            except Exception as e:
                logger.warning(f"Error closing server {server_id}: {e}")
            finally:
                del self.servers[server_id]
                self.connection_status[server_id] = False
                if server_id in self.capabilities_cache:
                    del self.capabilities_cache[server_id]
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for server_id in list(self.servers.keys()):
            await self.disconnect_server(server_id)


# Singleton instance
_mcp_client = None

def get_mcp_client() -> MCPClient:
    """Get the global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
```

### 1.4 Tool System Enhancement

Enhance the existing tool system to integrate MCP capabilities:

```python
# src/agentic_workflow/mcp/tools/enhanced_manager.py
"""
Enhanced tool manager that integrates MCP capabilities.
"""

from typing import List, Dict, Any, Optional, Union
from agentic_workflow.tools.registry import ToolRegistry
from agentic_workflow.mcp.client.base import MCPClient, get_mcp_client
from agentic_workflow.core.interfaces import Tool, ToolResult

class MCPTool(Tool):
    """Wrapper for MCP tools to integrate with existing tool system."""
    
    def __init__(self, capability, mcp_client: MCPClient):
        self.capability = capability
        self.mcp_client = mcp_client
        super().__init__(
            name=capability.name,
            description=capability.description,
            parameters=capability.parameters or {}
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the MCP tool."""
        try:
            result = await self.mcp_client.execute_tool(
                self.capability.server_id,
                self.capability.name,
                kwargs
            )
            
            return ToolResult(
                success=True,
                data=result,
                tool_name=self.name,
                execution_time=0.0  # TODO: Add timing
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name,
                execution_time=0.0
            )


class EnhancedToolManager:
    """
    Enhanced tool manager that combines built-in tools with MCP capabilities.
    """
    
    def __init__(self, mcp_client: Optional[MCPClient] = None):
        self.builtin_registry = ToolRegistry()
        self.mcp_client = mcp_client or get_mcp_client()
        self.mcp_tools: Dict[str, MCPTool] = {}
        
    async def discover_tools(self) -> List[Tool]:
        """Discover all available tools (built-in + MCP)."""
        tools = []
        
        # Get built-in tools
        builtin_tools = await self.builtin_registry.list_tools()
        tools.extend(builtin_tools)
        
        # Get MCP tools
        capabilities = await self.mcp_client.discover_capabilities()
        for server_id, caps in capabilities.items():
            for cap in caps:
                if cap.type == 'tool':
                    mcp_tool = MCPTool(cap, self.mcp_client)
                    self.mcp_tools[cap.name] = mcp_tool
                    tools.append(mcp_tool)
        
        return tools
    
    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a specific tool by name."""
        # Check built-in tools first
        tool = await self.builtin_registry.get_tool(tool_name)
        if tool:
            return tool
        
        # Check MCP tools
        if tool_name in self.mcp_tools:
            return self.mcp_tools[tool_name]
        
        # If not cached, refresh MCP tools
        await self.discover_tools()
        return self.mcp_tools.get(tool_name)
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = await self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
                tool_name=tool_name,
                execution_time=0.0
            )
        
        return await tool.execute(**kwargs)
    
    async def search_tools(self, query: str, category: Optional[str] = None) -> List[Tool]:
        """Search for tools by query and optional category."""
        all_tools = await self.discover_tools()
        
        # Simple text search (can be enhanced with semantic search)
        matching_tools = []
        query_lower = query.lower()
        
        for tool in all_tools:
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower()):
                matching_tools.append(tool)
        
        return matching_tools
    
    async def get_tool_categories(self) -> Dict[str, List[str]]:
        """Get tools organized by category."""
        all_tools = await self.discover_tools()
        categories = {}
        
        for tool in all_tools:
            # Determine category based on tool source and name
            if isinstance(tool, MCPTool):
                category = f"MCP-{tool.capability.server_id}"
            else:
                category = "Built-in"
            
            if category not in categories:
                categories[category] = []
            categories[category].append(tool.name)
        
        return categories
```

### 1.5 Agent Framework Enhancement

Enhance existing agents to support MCP capabilities:

```python
# src/agentic_workflow/mcp/agents/enhanced_base.py
"""
Enhanced agent base class with MCP capabilities.
"""

from typing import Dict, Any, Optional, List
from agentic_workflow.agents.base import Agent, AgentTask, AgentResult
from agentic_workflow.mcp.client.base import MCPClient, get_mcp_client
from agentic_workflow.mcp.tools.enhanced_manager import EnhancedToolManager

class MCPEnhancedAgent(Agent):
    """
    Enhanced agent with MCP capabilities.
    
    Maintains all existing functionality while adding:
    - Dynamic capability discovery
    - Real-time data access
    - External tool integration
    """
    
    def __init__(
        self, 
        agent_id: str, 
        config: Optional[Dict[str, Any]] = None,
        mcp_client: Optional[MCPClient] = None,
        **kwargs
    ):
        super().__init__(agent_id, config, **kwargs)
        self.mcp_client = mcp_client or get_mcp_client()
        self.enhanced_tool_manager = EnhancedToolManager(self.mcp_client)
        self._mcp_enabled = config.get('mcp_enabled', True) if config else True
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities including MCP capabilities."""
        capabilities = await super().get_capabilities()
        
        if self._mcp_enabled:
            # Add MCP capabilities
            mcp_capabilities = await self.mcp_client.discover_capabilities()
            capabilities['mcp_servers'] = list(mcp_capabilities.keys())
            capabilities['mcp_tools'] = {
                server: [cap.name for cap in caps if cap.type == 'tool']
                for server, caps in mcp_capabilities.items()
            }
            capabilities['mcp_resources'] = {
                server: [cap.name for cap in caps if cap.type == 'resource']
                for server, caps in mcp_capabilities.items()
            }
        
        return capabilities
    
    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover all available tools including MCP tools."""
        if not self._mcp_enabled:
            return await super().discover_tools()
        
        tools = await self.enhanced_tool_manager.discover_tools()
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.parameters,
                'source': 'mcp' if hasattr(tool, 'capability') else 'builtin'
            }
            for tool in tools
        ]
    
    async def execute_with_mcp(self, task: AgentTask) -> AgentResult:
        """Execute task with both built-in and MCP tools."""
        if not self._mcp_enabled:
            return await self.execute(task)
        
        try:
            # Determine optimal tool mix using reasoning
            tool_strategy = await self._plan_tool_usage(task)
            
            # Execute using optimal strategy
            result = await self._execute_with_strategy(task, tool_strategy)
            
            return result
            
        except Exception as e:
            self.logger.error(f"MCP-enhanced execution failed: {e}")
            # Fallback to standard execution
            return await self.execute(task)
    
    async def _plan_tool_usage(self, task: AgentTask) -> Dict[str, Any]:
        """Plan optimal tool usage for the task."""
        # Get available tools
        available_tools = await self.discover_tools()
        
        # Analyze task requirements
        task_analysis = await self._analyze_task_requirements(task)
        
        # Select optimal tools
        selected_tools = await self._select_optimal_tools(
            task_analysis, available_tools
        )
        
        return {
            'task_analysis': task_analysis,
            'selected_tools': selected_tools,
            'execution_plan': await self._create_execution_plan(selected_tools)
        }
    
    async def _analyze_task_requirements(self, task: AgentTask) -> Dict[str, Any]:
        """Analyze task to determine tool requirements."""
        # This would use reasoning patterns to analyze the task
        # For now, simple keyword-based analysis
        task_text = str(task.get('description', ''))
        
        requirements = {
            'needs_file_access': any(keyword in task_text.lower() 
                                   for keyword in ['file', 'read', 'write', 'directory']),
            'needs_api_access': any(keyword in task_text.lower() 
                                  for keyword in ['api', 'http', 'request', 'web']),
            'needs_database': any(keyword in task_text.lower() 
                                for keyword in ['database', 'query', 'sql', 'data']),
            'needs_code_analysis': any(keyword in task_text.lower() 
                                     for keyword in ['code', 'analyze', 'review', 'refactor']),
            'complexity': 'high' if len(task_text) > 200 else 'medium' if len(task_text) > 50 else 'low'
        }
        
        return requirements
    
    async def _select_optimal_tools(
        self, 
        requirements: Dict[str, Any], 
        available_tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Select optimal tools based on requirements."""
        selected = []
        
        for tool in available_tools:
            tool_name = tool['name'].lower()
            tool_desc = tool['description'].lower()
            
            # Simple matching logic (can be enhanced with ML)
            if requirements['needs_file_access'] and ('file' in tool_name or 'file' in tool_desc):
                selected.append(tool)
            elif requirements['needs_api_access'] and ('api' in tool_name or 'http' in tool_desc):
                selected.append(tool)
            elif requirements['needs_database'] and ('database' in tool_name or 'sql' in tool_desc):
                selected.append(tool)
            elif requirements['needs_code_analysis'] and ('code' in tool_name or 'analyze' in tool_desc):
                selected.append(tool)
        
        return selected
    
    async def _create_execution_plan(self, selected_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create execution plan for selected tools."""
        return {
            'tool_sequence': [tool['name'] for tool in selected_tools],
            'parallel_execution': len(selected_tools) > 1,
            'fallback_strategy': 'use_builtin_tools'
        }
    
    async def _execute_with_strategy(
        self, 
        task: AgentTask, 
        strategy: Dict[str, Any]
    ) -> AgentResult:
        """Execute task using the planned strategy."""
        # For now, delegate to standard execution
        # This would be enhanced with actual strategy execution
        return await self.execute(task)
    
    async def get_mcp_resource(self, server_id: str, resource_uri: str) -> Any:
        """Get a resource from an MCP server."""
        if not self._mcp_enabled:
            raise RuntimeError("MCP not enabled for this agent")
        
        return await self.mcp_client.get_resource(server_id, resource_uri)
    
    async def list_mcp_capabilities(self) -> Dict[str, List[str]]:
        """List all MCP capabilities available to this agent."""
        if not self._mcp_enabled:
            return {}
        
        capabilities = await self.mcp_client.discover_capabilities()
        return {
            server: [cap.name for cap in caps]
            for server, caps in capabilities.items()
        }
```

### 1.6 Configuration Management

Add MCP configuration to the existing configuration system:

```python
# src/agentic_workflow/config/mcp_config.py
"""
MCP configuration management.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from agentic_workflow.mcp.client.base import MCPServerConfig

class MCPConfig(BaseModel):
    """MCP configuration settings."""
    
    enabled: bool = Field(default=True, description="Enable MCP integration")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    health_check_interval: int = Field(default=60, description="Health check interval in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    cache_ttl: int = Field(default=3600, description="Capability cache TTL in seconds")
    
    servers: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="MCP server configurations"
    )
    
    security: Dict[str, Any] = Field(
        default_factory=dict,
        description="Security settings"
    )

# Add to main config
class Config(BaseModel):
    # ... existing config fields ...
    mcp: MCPConfig = Field(default_factory=MCPConfig)
```

### 1.7 Basic Security Framework

Implement basic security for MCP operations:

```python
# src/agentic_workflow/mcp/security/auth.py
"""
MCP security and authentication framework.
"""

import asyncio
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class MCPAuthProvider(ABC):
    """Abstract base class for MCP authentication providers."""
    
    @abstractmethod
    async def authenticate(self, server_id: str, credentials: Dict[str, Any]) -> bool:
        """Authenticate with an MCP server."""
        pass
    
    @abstractmethod
    async def authorize_operation(
        self, 
        agent_id: str, 
        server_id: str, 
        operation: str, 
        resource: Optional[str] = None
    ) -> bool:
        """Authorize an operation for an agent."""
        pass

class BasicMCPAuthProvider(MCPAuthProvider):
    """Basic MCP authentication provider."""
    
    def __init__(self):
        self.authenticated_servers: Dict[str, bool] = {}
        self.agent_permissions: Dict[str, Dict[str, List[str]]] = {}
    
    async def authenticate(self, server_id: str, credentials: Dict[str, Any]) -> bool:
        """Basic authentication implementation."""
        # TODO: Implement actual authentication logic
        self.authenticated_servers[server_id] = True
        return True
    
    async def authorize_operation(
        self, 
        agent_id: str, 
        server_id: str, 
        operation: str, 
        resource: Optional[str] = None
    ) -> bool:
        """Basic authorization implementation."""
        # TODO: Implement actual authorization logic
        return True

class MCPSecurityManager:
    """Manages security for MCP operations."""
    
    def __init__(self, auth_provider: Optional[MCPAuthProvider] = None):
        self.auth_provider = auth_provider or BasicMCPAuthProvider()
        self.audit_log: List[Dict[str, Any]] = []
    
    async def authenticate_server(self, server_id: str, credentials: Dict[str, Any]) -> bool:
        """Authenticate with an MCP server."""
        try:
            result = await self.auth_provider.authenticate(server_id, credentials)
            await self._audit_authentication(server_id, result)
            return result
        except Exception as e:
            logger.error(f"Authentication failed for server {server_id}: {e}")
            return False
    
    async def authorize_agent_operation(
        self, 
        agent_id: str, 
        server_id: str, 
        operation: str, 
        resource: Optional[str] = None
    ) -> bool:
        """Authorize an agent operation."""
        try:
            result = await self.auth_provider.authorize_operation(
                agent_id, server_id, operation, resource
            )
            await self._audit_authorization(agent_id, server_id, operation, resource, result)
            return result
        except Exception as e:
            logger.error(f"Authorization failed for {agent_id}: {e}")
            return False
    
    async def _audit_authentication(self, server_id: str, success: bool) -> None:
        """Audit authentication attempts."""
        self.audit_log.append({
            'type': 'authentication',
            'server_id': server_id,
            'success': success,
            'timestamp': asyncio.get_event_loop().time()
        })
    
    async def _audit_authorization(
        self, 
        agent_id: str, 
        server_id: str, 
        operation: str, 
        resource: Optional[str], 
        success: bool
    ) -> None:
        """Audit authorization attempts."""
        self.audit_log.append({
            'type': 'authorization',
            'agent_id': agent_id,
            'server_id': server_id,
            'operation': operation,
            'resource': resource,
            'success': success,
            'timestamp': asyncio.get_event_loop().time()
        })
```

### 1.8 Testing Framework

Create comprehensive tests for MCP integration:

```python
# tests/unit/mcp/test_mcp_client.py
"""
Unit tests for MCP client functionality.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from agentic_workflow.mcp.client.base import MCPClient, MCPServerConfig, MCPCapability

class TestMCPClient:
    """Test the MCP client implementation."""
    
    @pytest.fixture
    def mcp_client(self):
        """Create MCP client for testing."""
        return MCPClient()
    
    @pytest.fixture
    def server_config(self):
        """Create test server configuration."""
        return MCPServerConfig(
            name="test_server",
            command=["echo", "test"],
            description="Test MCP server"
        )
    
    async def test_register_server_success(self, mcp_client, server_config):
        """Test successful server registration."""
        with patch('agentic_workflow.mcp.client.base.ClientSession') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            # Mock successful initialization
            mock_session_instance.initialize.return_value = None
            
            # Mock capabilities
            mock_session_instance.list_tools.return_value = Mock(tools=[])
            mock_session_instance.list_resources.return_value = Mock(resources=[])
            mock_session_instance.list_prompts.return_value = Mock(prompts=[])
            
            result = await mcp_client.register_server(server_config)
            
            assert result is True
            assert server_config.name in mcp_client.servers
            assert mcp_client.connection_status[server_config.name] is True
    
    async def test_register_server_failure(self, mcp_client, server_config):
        """Test server registration failure."""
        with patch('agentic_workflow.mcp.client.base.ClientSession') as mock_session:
            mock_session.side_effect = Exception("Connection failed")
            
            result = await mcp_client.register_server(server_config)
            
            assert result is False
            assert server_config.name not in mcp_client.servers
            assert mcp_client.connection_status[server_config.name] is False
    
    async def test_discover_capabilities(self, mcp_client):
        """Test capability discovery."""
        # Setup test capabilities
        test_capabilities = [
            MCPCapability("test_tool", "tool", "Test tool", "test_server"),
            MCPCapability("test_resource", "resource", "Test resource", "test_server")
        ]
        mcp_client.capabilities_cache["test_server"] = test_capabilities
        
        capabilities = await mcp_client.discover_capabilities()
        
        assert "test_server" in capabilities
        assert len(capabilities["test_server"]) == 2
        assert capabilities["test_server"][0].name == "test_tool"
        assert capabilities["test_server"][1].name == "test_resource"
    
    async def test_execute_tool_success(self, mcp_client):
        """Test successful tool execution."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.call_tool.return_value = {"result": "success"}
        mcp_client.servers["test_server"] = mock_session
        mcp_client.connection_status["test_server"] = True
        
        result = await mcp_client.execute_tool(
            "test_server", 
            "test_tool", 
            {"param": "value"}
        )
        
        assert result == {"result": "success"}
        mock_session.call_tool.assert_called_once_with("test_tool", {"param": "value"})
    
    async def test_execute_tool_server_not_found(self, mcp_client):
        """Test tool execution with non-existent server."""
        with pytest.raises(ValueError, match="Server non_existent not connected"):
            await mcp_client.execute_tool("non_existent", "test_tool", {})
    
    async def test_health_check(self, mcp_client):
        """Test health check functionality."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.list_tools.return_value = Mock(tools=[])
        mcp_client.servers["test_server"] = mock_session
        
        health = await mcp_client.health_check("test_server")
        
        assert health["test_server"] is True
        assert mcp_client.connection_status["test_server"] is True
    
    async def test_disconnect_server(self, mcp_client):
        """Test server disconnection."""
        # Setup mock session
        mock_session = AsyncMock()
        mcp_client.servers["test_server"] = mock_session
        mcp_client.connection_status["test_server"] = True
        mcp_client.capabilities_cache["test_server"] = []
        
        await mcp_client.disconnect_server("test_server")
        
        assert "test_server" not in mcp_client.servers
        assert mcp_client.connection_status["test_server"] is False
        assert "test_server" not in mcp_client.capabilities_cache
        mock_session.close.assert_called_once()
```

```python
# tests/integration/mcp/test_mcp_integration.py
"""
Integration tests for MCP functionality.
"""

import pytest
from agentic_workflow.mcp.client.base import MCPClient, MCPServerConfig
from agentic_workflow.mcp.tools.enhanced_manager import EnhancedToolManager
from agentic_workflow.mcp.agents.enhanced_base import MCPEnhancedAgent

@pytest.mark.integration
class TestMCPIntegration:
    """Integration tests for MCP components."""
    
    @pytest.fixture
    async def mcp_setup(self):
        """Setup MCP client with test configuration."""
        client = MCPClient()
        
        # In a real test, you would connect to actual MCP servers
        # For integration testing, use test/mock servers
        
        yield client
        
        # Cleanup
        await client.disconnect_all()
    
    async def test_end_to_end_tool_execution(self, mcp_setup):
        """Test end-to-end MCP tool execution."""
        mcp_client = mcp_setup
        
        # This would test with actual MCP servers in integration environment
        # For now, just test the flow works
        tool_manager = EnhancedToolManager(mcp_client)
        tools = await tool_manager.discover_tools()
        
        # Should include built-in tools even without MCP servers
        assert len(tools) > 0
    
    async def test_agent_mcp_integration(self, mcp_setup):
        """Test agent integration with MCP."""
        mcp_client = mcp_setup
        
        agent = MCPEnhancedAgent("test_agent", mcp_client=mcp_client)
        capabilities = await agent.get_capabilities()
        
        # Should have MCP-related capabilities
        assert 'mcp_servers' in capabilities
        assert 'mcp_tools' in capabilities
        assert 'mcp_resources' in capabilities
```

## Phase 1 Implementation Checklist

- [ ] **Project Structure**: Create MCP module structure
- [ ] **Dependencies**: Add MCP dependencies to project
- [ ] **Core Client**: Implement MCPClient class
- [ ] **Tool Enhancement**: Create EnhancedToolManager
- [ ] **Agent Enhancement**: Create MCPEnhancedAgent base class
- [ ] **Configuration**: Add MCP configuration management
- [ ] **Security**: Implement basic security framework
- [ ] **Testing**: Create comprehensive test suite
- [ ] **Documentation**: Update API documentation
- [ ] **Integration**: Test with existing system

## Configuration Examples

### MCP Server Configuration
```yaml
# config/mcp_servers.yaml
mcp:
  enabled: true
  connection_timeout: 30
  health_check_interval: 60
  
  servers:
    - name: "git_server"
      command: ["git-mcp-server"]
      description: "Git operations server"
      env:
        GIT_CONFIG_PATH: "/path/to/config"
    
    - name: "file_server"
      command: ["file-mcp-server", "--root", "/workspace"]
      description: "File system operations"
      timeout: 20
    
    - name: "postgres_server"
      command: ["postgres-mcp-server"]
      env:
        POSTGRES_HOST: "localhost"
        POSTGRES_PORT: "5432"
        POSTGRES_DB: "agentic_workflow"
      description: "PostgreSQL database access"
```

### Agent Configuration with MCP
```yaml
# config/agents.yaml
agents:
  planning_agent:
    type: "planning"
    mcp_enabled: true
    mcp_servers: ["git_server", "file_server"]
    reasoning_patterns: ["chain_of_thought", "react"]
  
  code_generation_agent:
    type: "code_generation"
    mcp_enabled: true
    mcp_servers: ["git_server", "file_server", "postgres_server"]
    tools: ["builtin", "mcp"]
```

## Next Steps for Phase 2

With Phase 1 complete, Phase 2 will focus on:

1. **Memory System Integration**: Enhanced context management with MCP
2. **Reasoning Pattern Enhancement**: Integrate MCP with CoT and ReAct patterns
3. **Essential Server Connections**: Connect to Git, file system, and database servers
4. **Performance Optimization**: Caching and connection pooling
5. **Monitoring Integration**: Prometheus metrics for MCP operations

## Common Issues and Troubleshooting

### Connection Issues
```python
# Check MCP server health
health = await mcp_client.health_check()
print(f"Server health: {health}")

# Verify server configuration
for server_id, config in mcp_client.server_configs.items():
    print(f"Server {server_id}: {config.command}")
```

### Tool Discovery Issues
```python
# Debug tool discovery
capabilities = await mcp_client.discover_capabilities()
for server, caps in capabilities.items():
    print(f"Server {server} capabilities:")
    for cap in caps:
        print(f"  - {cap.name} ({cap.type}): {cap.description}")
```

### Performance Monitoring
```python
# Add timing to tool execution
import time

async def timed_tool_execution(tool_name: str, **kwargs):
    start_time = time.time()
    result = await enhanced_tool_manager.execute_tool(tool_name, **kwargs)
    execution_time = time.time() - start_time
    
    print(f"Tool {tool_name} executed in {execution_time:.3f}s")
    return result
```

## Key Takeaways

> **Phase 1 establishes the foundation for MCP integration while maintaining full backward compatibility with existing functionality.**

- **Zero Breaking Changes**: All existing agents and tools continue to work
- **Gradual Enhancement**: MCP capabilities can be enabled per agent
- **Solid Foundation**: Robust client, security, and testing infrastructure
- **Extensible Design**: Easy to add new servers and capabilities
- **Production Ready**: Comprehensive error handling and monitoring

**With Phase 1 complete, the agentic workflow system gains the foundational infrastructure needed for unlimited capability expansion through MCP servers.**