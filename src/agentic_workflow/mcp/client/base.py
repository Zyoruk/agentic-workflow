"""
Core MCP client implementation for agentic workflow system.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import subprocess
from contextlib import asynccontextmanager

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.types import Tool, Resource, GetPromptResult
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create mock classes for when MCP is not available
    class ClientSession:
        pass
    class StdioServerParameters:
        pass
    class Tool:
        pass
    class Resource:
        pass
    class GetPromptResult:
        pass

from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)


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
    auto_reconnect: bool = True
    health_check_interval: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPCapability:
    """Represents an MCP capability (tool, resource, or prompt)."""
    name: str
    type: str  # 'tool', 'resource', 'prompt'
    description: str
    server_id: str
    parameters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    usage_count: int = 0


class MCPConnectionError(Exception):
    """Raised when MCP connection fails."""
    pass


class MCPExecutionError(Exception):
    """Raised when MCP execution fails."""
    pass


class MCPClient:
    """
    Central MCP client for the agentic workflow system.
    
    Manages connections to multiple MCP servers and provides
    a unified interface for agents to access MCP capabilities.
    """
    
    def __init__(self, max_connections: int = 10):
        """Initialize MCP client.
        
        Args:
            max_connections: Maximum number of concurrent server connections
        """
        if not MCP_AVAILABLE:
            logger.warning("MCP libraries not available. Install with: pip install mcp")
            
        self.servers: Dict[str, ClientSession] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.capabilities_cache: Dict[str, List[MCPCapability]] = {}
        self.connection_status: Dict[str, bool] = {}
        self.connection_errors: Dict[str, str] = {}
        self.max_connections = max_connections
        self._lock = asyncio.Lock()
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._event_callbacks: Dict[str, List[Callable]] = {
            'server_connected': [],
            'server_disconnected': [],
            'capability_added': [],
            'capability_removed': [],
        }
        
        # Rate limiting
        self._rate_limits: Dict[str, Dict[str, List[float]]] = {}
        self._rate_limit_window = 60  # 1 minute window
        self._rate_limit_max_requests = 60  # 60 requests per minute
        
    async def initialize(self) -> None:
        """Initialize the MCP client."""
        if not MCP_AVAILABLE:
            logger.warning("MCP not available - running in compatibility mode")
            return
            
        logger.info("Initializing MCP client")
        # Start with basic initialization
        
    async def register_server(self, config: MCPServerConfig) -> bool:
        """
        Register and connect to an MCP server.
        
        Args:
            config: Server configuration
            
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            MCPConnectionError: If connection fails after retries
        """
        if not MCP_AVAILABLE:
            logger.warning(f"Cannot register server {config.name} - MCP not available")
            return False
            
        async with self._lock:
            if len(self.servers) >= self.max_connections:
                logger.error(f"Maximum connections ({self.max_connections}) reached")
                return False
                
            try:
                logger.info(f"Registering MCP server: {config.name}")
                
                # Validate server command exists
                if not await self._validate_server_command(config):
                    raise MCPConnectionError(f"Server command not found: {config.command}")
                
                # Create server parameters
                server_params = StdioServerParameters(
                    command=config.command[0],  # First element is the command
                    args=config.command[1:] + (config.args or []),  # Rest + additional args
                    env=config.env
                )
                
                # Create and start session with retries
                session = await self._connect_with_retries(config, server_params)
                
                # Store connection
                self.servers[config.name] = session
                self.server_configs[config.name] = config
                self.connection_status[config.name] = True
                self.connection_errors.pop(config.name, None)
                
                # Cache capabilities
                await self._cache_server_capabilities(config.name)
                
                # Start health check if enabled
                if config.auto_reconnect:
                    self._start_health_check(config.name)
                
                # Notify event callbacks
                await self._notify_event('server_connected', config.name)
                
                logger.info(f"Successfully connected to MCP server: {config.name}")
                return True
                
            except Exception as e:
                error_msg = f"Failed to connect to MCP server {config.name}: {e}"
                logger.error(error_msg)
                self.connection_status[config.name] = False
                self.connection_errors[config.name] = str(e)
                return False
    
    async def _validate_server_command(self, config: MCPServerConfig) -> bool:
        """Validate that the server command exists and is executable."""
        try:
            # Check if command exists
            result = subprocess.run(
                ['which', config.command[0]], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def _connect_with_retries(self, config: MCPServerConfig, server_params) -> ClientSession:
        """Connect to server with retry logic."""
        last_error = None
        
        for attempt in range(config.retry_attempts):
            try:
                session = ClientSession(server_params)
                await asyncio.wait_for(session.initialize(), timeout=config.timeout)
                return session
            except Exception as e:
                last_error = e
                if attempt < config.retry_attempts - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Connection attempt {attempt + 1} failed for {config.name}, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
        
        raise MCPConnectionError(f"Failed to connect after {config.retry_attempts} attempts: {last_error}")
    
    async def _cache_server_capabilities(self, server_id: str) -> None:
        """Cache capabilities for a server."""
        try:
            session = self.servers[server_id]
            capabilities = []
            
            # Get tools
            try:
                tools_result = await session.list_tools()
                for tool in tools_result.tools:
                    capability = MCPCapability(
                        name=tool.name,
                        type='tool',
                        description=tool.description or '',
                        server_id=server_id,
                        parameters=tool.inputSchema,
                        metadata={'tool': tool}
                    )
                    capabilities.append(capability)
                    await self._notify_event('capability_added', capability)
            except Exception as e:
                logger.warning(f"Failed to list tools for {server_id}: {e}")
            
            # Get resources
            try:
                resources_result = await session.list_resources()
                for resource in resources_result.resources:
                    capability = MCPCapability(
                        name=resource.name,
                        type='resource',
                        description=resource.description or '',
                        server_id=server_id,
                        metadata={'resource': resource}
                    )
                    capabilities.append(capability)
                    await self._notify_event('capability_added', capability)
            except Exception as e:
                logger.warning(f"Failed to list resources for {server_id}: {e}")
            
            # Get prompts
            try:
                prompts_result = await session.list_prompts()
                for prompt in prompts_result.prompts:
                    capability = MCPCapability(
                        name=prompt.name,
                        type='prompt',
                        description=prompt.description or '',
                        server_id=server_id,
                        parameters=prompt.arguments,
                        metadata={'prompt': prompt}
                    )
                    capabilities.append(capability)
                    await self._notify_event('capability_added', capability)
            except Exception as e:
                logger.warning(f"Failed to list prompts for {server_id}: {e}")
            
            self.capabilities_cache[server_id] = capabilities
            logger.info(f"Cached {len(capabilities)} capabilities for server {server_id}")
            
        except Exception as e:
            logger.error(f"Failed to cache capabilities for {server_id}: {e}")
    
    def _start_health_check(self, server_id: str) -> None:
        """Start health check task for a server."""
        async def health_check_loop():
            config = self.server_configs[server_id]
            while server_id in self.servers and config.auto_reconnect:
                await asyncio.sleep(config.health_check_interval)
                
                if not await self._check_server_health(server_id):
                    logger.warning(f"Server {server_id} health check failed, attempting reconnection")
                    await self._reconnect_server(server_id)
        
        task = asyncio.create_task(health_check_loop())
        self._health_check_tasks[server_id] = task
    
    async def _check_server_health(self, server_id: str) -> bool:
        """Check if server connection is healthy."""
        try:
            session = self.servers.get(server_id)
            if not session:
                return False
                
            # Try a simple operation to check health
            await session.list_tools()
            return True
        except Exception:
            return False
    
    async def _reconnect_server(self, server_id: str) -> bool:
        """Attempt to reconnect to a server."""
        config = self.server_configs.get(server_id)
        if not config:
            return False
            
        # Clean up old connection
        await self.disconnect_server(server_id, cleanup_only=True)
        
        # Attempt to reconnect
        return await self.register_server(config)
    
    async def disconnect_server(self, server_id: str, cleanup_only: bool = False) -> bool:
        """
        Disconnect from an MCP server.
        
        Args:
            server_id: Server identifier
            cleanup_only: If True, only cleanup without notifying events
            
        Returns:
            True if disconnection successful
        """
        async with self._lock:
            try:
                # Stop health check
                if server_id in self._health_check_tasks:
                    self._health_check_tasks[server_id].cancel()
                    del self._health_check_tasks[server_id]
                
                # Close session
                if server_id in self.servers:
                    session = self.servers[server_id]
                    try:
                        await session.close()
                    except Exception as e:
                        logger.warning(f"Error closing session for {server_id}: {e}")
                    del self.servers[server_id]
                
                # Clean up status
                self.connection_status[server_id] = False
                
                # Remove capabilities
                if server_id in self.capabilities_cache:
                    capabilities = self.capabilities_cache[server_id]
                    del self.capabilities_cache[server_id]
                    
                    if not cleanup_only:
                        for capability in capabilities:
                            await self._notify_event('capability_removed', capability)
                
                if not cleanup_only:
                    await self._notify_event('server_disconnected', server_id)
                
                logger.info(f"Disconnected from MCP server: {server_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error disconnecting from server {server_id}: {e}")
                return False
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], server_id: Optional[str] = None) -> Any:
        """
        Execute a tool via MCP.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            server_id: Specific server to use (if None, searches all servers)
            
        Returns:
            Tool execution result
            
        Raises:
            MCPExecutionError: If tool execution fails
        """
        if not MCP_AVAILABLE:
            raise MCPExecutionError("MCP not available")
            
        # Find tool capability
        capability = await self._find_capability(tool_name, 'tool', server_id)
        if not capability:
            raise MCPExecutionError(f"Tool '{tool_name}' not found")
        
        try:
            session = self.servers[capability.server_id]
            result = await session.call_tool(tool_name, parameters)
            
            # Update usage statistics
            capability.last_used = datetime.now()
            capability.usage_count += 1
            
            return result
            
        except Exception as e:
            raise MCPExecutionError(f"Tool execution failed: {e}")
    
    async def get_resource(self, resource_name: str, server_id: Optional[str] = None) -> Any:
        """
        Get a resource via MCP.
        
        Args:
            resource_name: Name of the resource
            server_id: Specific server to use
            
        Returns:
            Resource content
            
        Raises:
            MCPExecutionError: If resource access fails
        """
        if not MCP_AVAILABLE:
            raise MCPExecutionError("MCP not available")
            
        capability = await self._find_capability(resource_name, 'resource', server_id)
        if not capability:
            raise MCPExecutionError(f"Resource '{resource_name}' not found")
        
        try:
            session = self.servers[capability.server_id]
            result = await session.read_resource(resource_name)
            
            capability.last_used = datetime.now()
            capability.usage_count += 1
            
            return result
            
        except Exception as e:
            raise MCPExecutionError(f"Resource access failed: {e}")
    
    async def execute_prompt(self, prompt_name: str, arguments: Dict[str, Any], server_id: Optional[str] = None) -> Any:
        """
        Execute a prompt via MCP.
        
        Args:
            prompt_name: Name of the prompt
            arguments: Prompt arguments
            server_id: Specific server to use
            
        Returns:
            Prompt result
            
        Raises:
            MCPExecutionError: If prompt execution fails
        """
        if not MCP_AVAILABLE:
            raise MCPExecutionError("MCP not available")
            
        capability = await self._find_capability(prompt_name, 'prompt', server_id)
        if not capability:
            raise MCPExecutionError(f"Prompt '{prompt_name}' not found")
        
        try:
            session = self.servers[capability.server_id]
            result = await session.get_prompt(prompt_name, arguments)
            
            capability.last_used = datetime.now()
            capability.usage_count += 1
            
            return result
            
        except Exception as e:
            raise MCPExecutionError(f"Prompt execution failed: {e}")
    
    async def _find_capability(self, name: str, capability_type: str, server_id: Optional[str] = None) -> Optional[MCPCapability]:
        """Find a capability by name and type."""
        servers_to_search = [server_id] if server_id else self.capabilities_cache.keys()
        
        for sid in servers_to_search:
            capabilities = self.capabilities_cache.get(sid, [])
            for capability in capabilities:
                if capability.name == name and capability.type == capability_type:
                    return capability
        
        return None
    
    async def list_capabilities(self, capability_type: Optional[str] = None, server_id: Optional[str] = None) -> List[MCPCapability]:
        """
        List available capabilities.
        
        Args:
            capability_type: Filter by capability type ('tool', 'resource', 'prompt')
            server_id: Filter by server ID
            
        Returns:
            List of matching capabilities
        """
        capabilities = []
        servers_to_search = [server_id] if server_id else self.capabilities_cache.keys()
        
        for sid in servers_to_search:
            server_capabilities = self.capabilities_cache.get(sid, [])
            for capability in server_capabilities:
                if capability_type is None or capability.type == capability_type:
                    capabilities.append(capability)
        
        return capabilities
    
    async def refresh_capabilities(self, server_id: Optional[str] = None) -> None:
        """
        Refresh capability cache for servers.
        
        Args:
            server_id: Specific server to refresh (if None, refresh all)
        """
        servers_to_refresh = [server_id] if server_id else list(self.servers.keys())
        
        for sid in servers_to_refresh:
            if sid in self.servers and self.connection_status.get(sid, False):
                await self._cache_server_capabilities(sid)
    
    def get_server_status(self, server_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status information for servers.
        
        Args:
            server_id: Specific server (if None, return all servers)
            
        Returns:
            Server status information
        """
        if server_id:
            return {
                'connected': self.connection_status.get(server_id, False),
                'config': self.server_configs.get(server_id),
                'capabilities_count': len(self.capabilities_cache.get(server_id, [])),
                'last_error': self.connection_errors.get(server_id),
            }
        else:
            return {
                sid: self.get_server_status(sid) 
                for sid in self.server_configs.keys()
            }
    
    def add_event_callback(self, event_type: str, callback: Callable) -> None:
        """Add event callback."""
        if event_type in self._event_callbacks:
            self._event_callbacks[event_type].append(callback)
    
    def remove_event_callback(self, event_type: str, callback: Callable) -> None:
        """Remove event callback."""
        if event_type in self._event_callbacks:
            try:
                self._event_callbacks[event_type].remove(callback)
            except ValueError:
                pass
    
    async def _notify_event(self, event_type: str, data: Any) -> None:
        """Notify event callbacks."""
        callbacks = self._event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in event callback for {event_type}: {e}")
    
    async def _check_rate_limit(self, agent_id: str, operation: str) -> bool:
        """
        Check if rate limit allows the operation.
        
        Args:
            agent_id: Agent identifier
            operation: Operation type
            
        Returns:
            True if operation is allowed, False if rate limited
        """
        current_time = asyncio.get_event_loop().time()
        
        # Initialize tracking for agent if needed
        if agent_id not in self._rate_limits:
            self._rate_limits[agent_id] = {}
        
        if operation not in self._rate_limits[agent_id]:
            self._rate_limits[agent_id][operation] = []
        
        # Clean up old requests outside the window
        request_times = self._rate_limits[agent_id][operation]
        window_start = current_time - self._rate_limit_window
        self._rate_limits[agent_id][operation] = [
            t for t in request_times if t > window_start
        ]
        
        # Check if under rate limit
        if len(self._rate_limits[agent_id][operation]) < self._rate_limit_max_requests:
            self._rate_limits[agent_id][operation].append(current_time)
            return True
        
        return False
    
    @asynccontextmanager
    async def server_session(self, server_id: str):
        """Context manager for server session access."""
        if server_id not in self.servers:
            raise MCPConnectionError(f"Server {server_id} not connected")
        
        session = self.servers[server_id]
        try:
            yield session
        except Exception as e:
            logger.error(f"Error in server session {server_id}: {e}")
            raise
    
    async def close(self) -> None:
        """Close all server connections and cleanup."""
        logger.info("Closing MCP client")
        
        # Cancel all health check tasks
        for task in self._health_check_tasks.values():
            task.cancel()
        
        # Disconnect all servers
        for server_id in list(self.servers.keys()):
            await self.disconnect_server(server_id, cleanup_only=True)
        
        # Clear all data
        self.servers.clear()
        self.server_configs.clear()
        self.capabilities_cache.clear()
        self.connection_status.clear()
        self.connection_errors.clear()
        self._health_check_tasks.clear()
        
        logger.info("MCP client closed")