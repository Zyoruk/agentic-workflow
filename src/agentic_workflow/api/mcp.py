"""API endpoints for MCP (Model Context Protocol) management."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.mcp.client.base import MCPClient, MCPServerConfig, MCPExecutionError
from agentic_workflow.mcp.integration.agents import MCPEnhancedAgent
from agentic_workflow.agents.base import AgentTask

# Create router
router = APIRouter(prefix="/mcp", tags=["mcp"])
logger = get_logger(__name__)

# Global MCP client instance
_mcp_client: Optional[MCPClient] = None
_mcp_agents: Dict[str, MCPEnhancedAgent] = {}


# Request/Response Models
class MCPServerCreateRequest(BaseModel):
    """Request to register a new MCP server."""
    
    name: str = Field(..., description="Server name")
    command: List[str] = Field(..., description="Command to start the server")
    args: Optional[List[str]] = Field(default=None, description="Additional command arguments")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    description: Optional[str] = Field(default=None, description="Server description")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    auto_reconnect: bool = Field(default=True, description="Enable auto-reconnection")


class MCPServerResponse(BaseModel):
    """Response for MCP server information."""
    
    name: str
    command: List[str]
    description: Optional[str]
    connected: bool
    capabilities_count: int
    last_error: Optional[str]


class MCPCapabilityResponse(BaseModel):
    """Response for MCP capability information."""
    
    name: str
    type: str  # 'tool', 'resource', 'prompt'
    description: str
    server_id: str
    parameters: Optional[Dict[str, Any]]
    usage_count: int
    last_used: Optional[str]


class MCPToolExecutionRequest(BaseModel):
    """Request to execute an MCP tool."""
    
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default={}, description="Tool parameters")
    server_id: Optional[str] = Field(default=None, description="Specific server to use")


class MCPToolExecutionResponse(BaseModel):
    """Response from MCP tool execution."""
    
    success: bool
    tool_name: str
    server_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float


class MCPEnhancedAgentCreateRequest(BaseModel):
    """Request to create an MCP-enhanced agent."""
    
    agent_id: str = Field(..., description="Agent identifier")
    mcp_servers: Optional[List[str]] = Field(default=None, description="MCP servers to connect to")
    mcp_categories: Optional[List[str]] = Field(default=None, description="MCP server categories")
    auto_discover_servers: bool = Field(default=False, description="Auto-discover available servers")
    reasoning_enabled: bool = Field(default=True, description="Enable reasoning capabilities")
    default_reasoning_pattern: str = Field(default="chain_of_thought", description="Default reasoning pattern")


class MCPEnhancedAgentResponse(BaseModel):
    """Response for MCP-enhanced agent information."""
    
    agent_id: str
    mcp_enabled: bool
    mcp_initialized: bool
    connected_servers: int
    available_capabilities: int
    reasoning_enabled: bool
    status: str


class MCPSystemStatusResponse(BaseModel):
    """Response for overall MCP system status."""
    
    mcp_available: bool
    client_initialized: bool
    total_servers: int
    connected_servers: int
    total_capabilities: int
    active_agents: int


# Utility Functions
async def _get_mcp_client() -> MCPClient:
    """Get or create the global MCP client."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
        await _mcp_client.initialize()
    return _mcp_client


# API Endpoints
@router.get("/status", response_model=MCPSystemStatusResponse)
async def get_mcp_status() -> MCPSystemStatusResponse:
    """Get overall MCP system status."""
    try:
        client = await _get_mcp_client()
        server_status = client.get_server_status()
        
        # Count connected servers
        connected_count = sum(1 for status in server_status.values() if status.get('connected', False))
        
        # Count total capabilities
        total_capabilities = sum(status.get('capabilities_count', 0) for status in server_status.values())
        
        return MCPSystemStatusResponse(
            mcp_available=True,  # If we got here, MCP is available
            client_initialized=True,
            total_servers=len(server_status),
            connected_servers=connected_count,
            total_capabilities=total_capabilities,
            active_agents=len(_mcp_agents)
        )
    except Exception as e:
        logger.error(f"Failed to get MCP status: {e}")
        # Return basic status even if MCP is not available
        return MCPSystemStatusResponse(
            mcp_available=False,
            client_initialized=False,
            total_servers=0,
            connected_servers=0,
            total_capabilities=0,
            active_agents=len(_mcp_agents)
        )


@router.get("/servers", response_model=List[MCPServerResponse])
async def list_mcp_servers() -> List[MCPServerResponse]:
    """List all registered MCP servers."""
    try:
        client = await _get_mcp_client()
        server_status = client.get_server_status()
        
        servers = []
        for server_id, status in server_status.items():
            config = status.get('config')
            if config:
                servers.append(MCPServerResponse(
                    name=server_id,
                    command=config.command,
                    description=config.description,
                    connected=status.get('connected', False),
                    capabilities_count=status.get('capabilities_count', 0),
                    last_error=status.get('last_error')
                ))
        
        logger.info(f"Listed {len(servers)} MCP servers")
        return servers
        
    except Exception as e:
        logger.error(f"Failed to list MCP servers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list servers: {e}"
        )


@router.post("/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def register_mcp_server(request: MCPServerCreateRequest) -> MCPServerResponse:
    """Register a new MCP server."""
    try:
        client = await _get_mcp_client()
        
        # Create server configuration
        config = MCPServerConfig(
            name=request.name,
            command=request.command,
            args=request.args,
            env=request.env,
            description=request.description,
            timeout=request.timeout,
            retry_attempts=request.retry_attempts,
            auto_reconnect=request.auto_reconnect
        )
        
        logger.info(f"Registering MCP server: {request.name}")
        
        # Register the server
        success = await client.register_server(config)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to register server '{request.name}'"
            )
        
        # Get server status
        server_status = client.get_server_status(request.name)
        
        logger.info(f"Successfully registered MCP server: {request.name}")
        
        return MCPServerResponse(
            name=request.name,
            command=request.command,
            description=request.description,
            connected=server_status.get('connected', False),
            capabilities_count=server_status.get('capabilities_count', 0),
            last_error=server_status.get('last_error')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register MCP server {request.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register server: {e}"
        )


@router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(server_id: str) -> MCPServerResponse:
    """Get information about a specific MCP server."""
    try:
        client = await _get_mcp_client()
        server_status = client.get_server_status(server_id)
        
        if not server_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server '{server_id}' not found"
            )
        
        config = server_status.get('config')
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server configuration for '{server_id}' not found"
            )
        
        return MCPServerResponse(
            name=server_id,
            command=config.command,
            description=config.description,
            connected=server_status.get('connected', False),
            capabilities_count=server_status.get('capabilities_count', 0),
            last_error=server_status.get('last_error')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MCP server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get server: {e}"
        )


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_mcp_server(server_id: str) -> None:
    """Disconnect from an MCP server."""
    try:
        client = await _get_mcp_client()
        
        logger.info(f"Disconnecting MCP server: {server_id}")
        
        success = await client.disconnect_server(server_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server '{server_id}' not found or already disconnected"
            )
        
        logger.info(f"Successfully disconnected MCP server: {server_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disconnect MCP server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect server: {e}"
        )


@router.get("/capabilities", response_model=List[MCPCapabilityResponse])
async def list_mcp_capabilities(
    capability_type: Optional[str] = None,
    server_id: Optional[str] = None
) -> List[MCPCapabilityResponse]:
    """List available MCP capabilities."""
    try:
        client = await _get_mcp_client()
        
        # Get capabilities with optional filtering
        capabilities = await client.list_capabilities(capability_type, server_id)
        
        response_capabilities = []
        for cap in capabilities:
            response_capabilities.append(MCPCapabilityResponse(
                name=cap.name,
                type=cap.type,
                description=cap.description,
                server_id=cap.server_id,
                parameters=cap.parameters,
                usage_count=cap.usage_count,
                last_used=cap.last_used.isoformat() if cap.last_used else None
            ))
        
        logger.info(f"Listed {len(capabilities)} MCP capabilities")
        return response_capabilities
        
    except Exception as e:
        logger.error(f"Failed to list MCP capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list capabilities: {e}"
        )


@router.post("/tools/execute", response_model=MCPToolExecutionResponse)
async def execute_mcp_tool(request: MCPToolExecutionRequest) -> MCPToolExecutionResponse:
    """Execute an MCP tool."""
    try:
        client = await _get_mcp_client()
        
        logger.info(f"Executing MCP tool: {request.tool_name}")
        
        start_time = datetime.now()
        
        # Execute the tool
        result = await client.execute_tool(
            request.tool_name,
            request.parameters,
            request.server_id
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Find which server was used
        capability = await client._find_capability(request.tool_name, 'tool', request.server_id)
        server_id = capability.server_id if capability else "unknown"
        
        logger.info(f"Successfully executed MCP tool: {request.tool_name}")
        
        return MCPToolExecutionResponse(
            success=True,
            tool_name=request.tool_name,
            server_id=server_id,
            result=result,
            execution_time=execution_time
        )
        
    except MCPExecutionError as e:
        logger.error(f"MCP tool execution failed: {e}")
        return MCPToolExecutionResponse(
            success=False,
            tool_name=request.tool_name,
            server_id=request.server_id or "unknown",
            error=str(e),
            execution_time=0.0
        )
    except Exception as e:
        logger.error(f"Unexpected error executing MCP tool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {e}"
        )


@router.post("/agents", response_model=MCPEnhancedAgentResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_enhanced_agent(request: MCPEnhancedAgentCreateRequest) -> MCPEnhancedAgentResponse:
    """Create an MCP-enhanced agent."""
    try:
        logger.info(f"Creating MCP-enhanced agent: {request.agent_id}")
        
        # Create MCP-enhanced agent
        agent = MCPEnhancedAgent(
            agent_id=request.agent_id,
            mcp_enabled=True,
            mcp_servers=request.mcp_servers or [],
            mcp_categories=request.mcp_categories or [],
            auto_discover_servers=request.auto_discover_servers,
            reasoning_enabled=request.reasoning_enabled,
            default_reasoning_pattern=request.default_reasoning_pattern
        )
        
        # Initialize the agent
        await agent.initialize()
        
        # Store in registry
        _mcp_agents[request.agent_id] = agent
        
        # Get agent status
        mcp_status = await agent.get_mcp_status()
        
        logger.info(f"Successfully created MCP-enhanced agent: {request.agent_id}")
        
        return MCPEnhancedAgentResponse(
            agent_id=request.agent_id,
            mcp_enabled=mcp_status['mcp_enabled'],
            mcp_initialized=mcp_status['mcp_initialized'],
            connected_servers=len([s for s in mcp_status['connected_servers'].values() if s]),
            available_capabilities=mcp_status['available_capabilities'],
            reasoning_enabled=request.reasoning_enabled,
            status=agent.status.value
        )
        
    except Exception as e:
        logger.error(f"Failed to create MCP-enhanced agent {request.agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {e}"
        )


@router.get("/agents", response_model=List[MCPEnhancedAgentResponse])
async def list_mcp_enhanced_agents() -> List[MCPEnhancedAgentResponse]:
    """List all MCP-enhanced agents."""
    try:
        agents = []
        for agent_id, agent in _mcp_agents.items():
            mcp_status = await agent.get_mcp_status()
            
            agents.append(MCPEnhancedAgentResponse(
                agent_id=agent_id,
                mcp_enabled=mcp_status['mcp_enabled'],
                mcp_initialized=mcp_status['mcp_initialized'],
                connected_servers=len([s for s in mcp_status['connected_servers'].values() if s]),
                available_capabilities=mcp_status['available_capabilities'],
                reasoning_enabled=agent.reasoning_enabled,
                status=agent.status.value
            ))
        
        logger.info(f"Listed {len(agents)} MCP-enhanced agents")
        return agents
        
    except Exception as e:
        logger.error(f"Failed to list MCP-enhanced agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {e}"
        )


@router.get("/agents/{agent_id}", response_model=MCPEnhancedAgentResponse)
async def get_mcp_enhanced_agent(agent_id: str) -> MCPEnhancedAgentResponse:
    """Get information about a specific MCP-enhanced agent."""
    try:
        if agent_id not in _mcp_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP-enhanced agent '{agent_id}' not found"
            )
        
        agent = _mcp_agents[agent_id]
        mcp_status = await agent.get_mcp_status()
        
        return MCPEnhancedAgentResponse(
            agent_id=agent_id,
            mcp_enabled=mcp_status['mcp_enabled'],
            mcp_initialized=mcp_status['mcp_initialized'],
            connected_servers=len([s for s in mcp_status['connected_servers'].values() if s]),
            available_capabilities=mcp_status['available_capabilities'],
            reasoning_enabled=agent.reasoning_enabled,
            status=agent.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MCP-enhanced agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {e}"
        )


@router.post("/agents/{agent_id}/execute", response_model=Dict[str, Any])
async def execute_mcp_agent_task(agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a task with an MCP-enhanced agent."""
    try:
        if agent_id not in _mcp_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP-enhanced agent '{agent_id}' not found"
            )
        
        agent = _mcp_agents[agent_id]
        
        logger.info(f"Executing task with MCP-enhanced agent {agent_id}")
        
        # Create agent task
        agent_task = AgentTask(**task)
        
        # Execute task
        result = await agent.execute(agent_task)
        
        return {
            "success": result.success,
            "task_id": result.task_id,
            "agent_id": result.agent_id,
            "execution_time": result.execution_time,
            "result": result.data,
            "error": result.error,
            "steps_taken": result.steps_taken,
            "metadata": result.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute task with MCP-enhanced agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {e}"
        )


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_mcp_enhanced_agent(agent_id: str) -> None:
    """Remove an MCP-enhanced agent."""
    try:
        if agent_id not in _mcp_agents:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP-enhanced agent '{agent_id}' not found"
            )
        
        agent = _mcp_agents[agent_id]
        
        logger.info(f"Removing MCP-enhanced agent: {agent_id}")
        
        # Close the agent
        await agent.close()
        
        # Remove from registry
        del _mcp_agents[agent_id]
        
        logger.info(f"Successfully removed MCP-enhanced agent: {agent_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove MCP-enhanced agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove agent: {e}"
        )


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_mcp_capabilities(server_id: Optional[str] = None) -> Dict[str, Any]:
    """Refresh MCP capabilities for all or specific servers."""
    try:
        client = await _get_mcp_client()
        
        logger.info(f"Refreshing MCP capabilities for server: {server_id or 'all'}")
        
        await client.refresh_capabilities(server_id)
        
        # Get updated status
        server_status = client.get_server_status()
        total_capabilities = sum(status.get('capabilities_count', 0) for status in server_status.values())
        
        logger.info(f"Successfully refreshed MCP capabilities")
        
        return {
            "success": True,
            "message": f"Refreshed capabilities for {server_id or 'all servers'}",
            "total_capabilities": total_capabilities
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh MCP capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh capabilities: {e}"
        )