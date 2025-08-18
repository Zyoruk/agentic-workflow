"""API endpoints for enhanced tool system management."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.mcp.tools.enhanced_registry import EnhancedToolRegistry
from agentic_workflow.mcp.client.base import MCPClient

# Create router
router = APIRouter(prefix="/tools", tags=["tools"])
logger = get_logger(__name__)

# Global tool registry instance
_tool_registry: Optional[EnhancedToolRegistry] = None


# Request/Response Models
class ToolSearchRequest(BaseModel):
    """Request to search for tools."""
    
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, description="Maximum number of results")
    source: Optional[str] = Field(default=None, description="Tool source filter (builtin, mcp, new_system)")
    category: Optional[str] = Field(default=None, description="Tool category filter")


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""
    
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default={}, description="Tool parameters")
    agent_id: str = Field(..., description="Agent ID for execution tracking")


class ToolResponse(BaseModel):
    """Response for tool information."""
    
    name: str
    description: str
    source: str  # 'builtin', 'mcp', 'new_system'
    category: Optional[str]
    parameters_schema: Optional[Dict[str, Any]]
    usage_count: int
    success_rate: float
    average_execution_time: float
    last_used: Optional[str]


class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    
    success: bool
    tool_name: str
    agent_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float
    timestamp: str


class ToolRecommendationResponse(BaseModel):
    """Response for tool recommendations."""
    
    query: str
    recommendations: List[ToolResponse]
    total_found: int


class ToolPerformanceMetrics(BaseModel):
    """Tool performance metrics."""
    
    tool_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    average_execution_time: float
    last_execution: Optional[str]


class ToolSystemStatusResponse(BaseModel):
    """Response for tool system status."""
    
    total_tools: int
    builtin_tools: int
    mcp_tools: int
    new_system_tools: int
    registry_initialized: bool
    mcp_integration_active: bool


# Utility Functions
async def _get_tool_registry() -> EnhancedToolRegistry:
    """Get or create the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        # Create MCP client if needed
        mcp_client = MCPClient()
        await mcp_client.initialize()
        
        # Create enhanced tool registry
        _tool_registry = EnhancedToolRegistry(mcp_client)
        await _tool_registry.initialize()
    
    return _tool_registry


# API Endpoints
@router.get("/status", response_model=ToolSystemStatusResponse)
async def get_tool_system_status() -> ToolSystemStatusResponse:
    """Get tool system status and statistics."""
    try:
        registry = await _get_tool_registry()
        
        # Get comprehensive tool list
        tools = registry.get_comprehensive_tool_list()
        
        return ToolSystemStatusResponse(
            total_tools=tools['total_count'],
            builtin_tools=len(tools['builtin_tools']),
            mcp_tools=len(tools['mcp_tools']),
            new_system_tools=len(tools['new_system_tools']),
            registry_initialized=True,
            mcp_integration_active=registry.mcp_client is not None
        )
        
    except Exception as e:
        logger.error(f"Failed to get tool system status: {e}")
        return ToolSystemStatusResponse(
            total_tools=0,
            builtin_tools=0,
            mcp_tools=0,
            new_system_tools=0,
            registry_initialized=False,
            mcp_integration_active=False
        )


@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    source: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[ToolResponse]:
    """List available tools with optional filtering."""
    try:
        registry = await _get_tool_registry()
        
        # Get tools based on source filter
        if source:
            tools = registry.list_tools(source=source)
        else:
            tools = registry.list_tools()
        
        # Apply category filter if specified
        if category:
            tools = [tool for tool in tools if getattr(tool, 'category', None) == category]
        
        # Apply limit
        tools = tools[:limit]
        
        # Get performance metrics
        metrics = registry.get_performance_metrics()
        
        response_tools = []
        for tool in tools:
            tool_metrics = metrics.get(tool.name, {})
            
            response_tools.append(ToolResponse(
                name=tool.name,
                description=tool.description,
                source=getattr(tool, 'source', 'builtin'),
                category=getattr(tool, 'category', None),
                parameters_schema=getattr(tool, 'parameters_schema', None),
                usage_count=tool_metrics.get('total_executions', 0),
                success_rate=tool_metrics.get('success_rate', 0.0),
                average_execution_time=tool_metrics.get('average_time', 0.0),
                last_used=tool_metrics.get('last_execution')
            ))
        
        logger.info(f"Listed {len(response_tools)} tools")
        return response_tools
        
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {e}"
        )


@router.get("/categories", response_model=List[str])
async def get_tool_categories() -> List[str]:
    """Get list of available tool categories."""
    try:
        registry = await _get_tool_registry()
        
        tools = registry.list_tools()
        categories = set()
        
        for tool in tools:
            category = getattr(tool, 'category', None)
            if category:
                categories.add(category)
        
        category_list = sorted(list(categories))
        
        logger.info(f"Found {len(category_list)} tool categories")
        return category_list
        
    except Exception as e:
        logger.error(f"Failed to get tool categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {e}"
        )


@router.get("/sources", response_model=List[str])
async def get_tool_sources() -> List[str]:
    """Get list of available tool sources."""
    try:
        registry = await _get_tool_registry()
        
        tools = registry.get_comprehensive_tool_list()
        
        sources = []
        if tools['builtin_tools']:
            sources.append('builtin')
        if tools['mcp_tools']:
            sources.append('mcp')
        if tools['new_system_tools']:
            sources.append('new_system')
        
        logger.info(f"Found {len(sources)} tool sources")
        return sources
        
    except Exception as e:
        logger.error(f"Failed to get tool sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sources: {e}"
        )


@router.get("/{tool_name}", response_model=ToolResponse)
async def get_tool(tool_name: str) -> ToolResponse:
    """Get information about a specific tool."""
    try:
        registry = await _get_tool_registry()
        
        # Find the tool
        tools = registry.list_tools()
        tool = next((t for t in tools if t.name == tool_name), None)
        
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_name}' not found"
            )
        
        # Get performance metrics
        metrics = registry.get_performance_metrics()
        tool_metrics = metrics.get(tool_name, {})
        
        return ToolResponse(
            name=tool.name,
            description=tool.description,
            source=getattr(tool, 'source', 'builtin'),
            category=getattr(tool, 'category', None),
            parameters_schema=getattr(tool, 'parameters_schema', None),
            usage_count=tool_metrics.get('total_executions', 0),
            success_rate=tool_metrics.get('success_rate', 0.0),
            average_execution_time=tool_metrics.get('average_time', 0.0),
            last_used=tool_metrics.get('last_execution')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool {tool_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool: {e}"
        )


@router.post("/search", response_model=ToolRecommendationResponse)
async def search_tools(request: ToolSearchRequest) -> ToolRecommendationResponse:
    """Search for tools based on a query."""
    try:
        registry = await _get_tool_registry()
        
        logger.info(f"Searching for tools with query: {request.query}")
        
        # Get tool recommendations
        recommendations = registry.get_tool_recommendations(
            request.query,
            limit=request.limit
        )
        
        # Filter by source if specified
        if request.source:
            recommendations = [
                tool for tool in recommendations 
                if getattr(tool, 'source', 'builtin') == request.source
            ]
        
        # Filter by category if specified
        if request.category:
            recommendations = [
                tool for tool in recommendations 
                if getattr(tool, 'category', None) == request.category
            ]
        
        # Get performance metrics
        metrics = registry.get_performance_metrics()
        
        response_tools = []
        for tool in recommendations:
            tool_metrics = metrics.get(tool.name, {})
            
            response_tools.append(ToolResponse(
                name=tool.name,
                description=tool.description,
                source=getattr(tool, 'source', 'builtin'),
                category=getattr(tool, 'category', None),
                parameters_schema=getattr(tool, 'parameters_schema', None),
                usage_count=tool_metrics.get('total_executions', 0),
                success_rate=tool_metrics.get('success_rate', 0.0),
                average_execution_time=tool_metrics.get('average_time', 0.0),
                last_used=tool_metrics.get('last_execution')
            ))
        
        logger.info(f"Found {len(response_tools)} tool recommendations")
        
        return ToolRecommendationResponse(
            query=request.query,
            recommendations=response_tools,
            total_found=len(response_tools)
        )
        
    except Exception as e:
        logger.error(f"Failed to search tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool search failed: {e}"
        )


@router.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(request: ToolExecutionRequest) -> ToolExecutionResponse:
    """Execute a tool with the specified parameters."""
    try:
        registry = await _get_tool_registry()
        
        logger.info(f"Executing tool {request.tool_name} for agent {request.agent_id}")
        
        start_time = datetime.now()
        
        # Execute the tool
        result = await registry.execute_tool(
            request.tool_name,
            request.parameters,
            request.agent_id
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Successfully executed tool {request.tool_name}")
        
        return ToolExecutionResponse(
            success=True,
            tool_name=request.tool_name,
            agent_id=request.agent_id,
            result=result,
            execution_time=execution_time,
            timestamp=datetime.now(UTC).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Tool execution failed for {request.tool_name}: {e}")
        
        return ToolExecutionResponse(
            success=False,
            tool_name=request.tool_name,
            agent_id=request.agent_id,
            error=str(e),
            execution_time=0.0,
            timestamp=datetime.now(UTC).isoformat()
        )


@router.get("/metrics/performance", response_model=List[ToolPerformanceMetrics])
async def get_tool_performance_metrics() -> List[ToolPerformanceMetrics]:
    """Get performance metrics for all tools."""
    try:
        registry = await _get_tool_registry()
        
        metrics = registry.get_performance_metrics()
        
        performance_metrics = []
        for tool_name, tool_metrics in metrics.items():
            total_executions = tool_metrics.get('total_executions', 0)
            successful_executions = tool_metrics.get('successful_executions', 0)
            failed_executions = total_executions - successful_executions
            
            performance_metrics.append(ToolPerformanceMetrics(
                tool_name=tool_name,
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                success_rate=tool_metrics.get('success_rate', 0.0),
                average_execution_time=tool_metrics.get('average_time', 0.0),
                last_execution=tool_metrics.get('last_execution')
            ))
        
        logger.info(f"Retrieved performance metrics for {len(performance_metrics)} tools")
        return performance_metrics
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {e}"
        )


@router.get("/metrics/{tool_name}", response_model=ToolPerformanceMetrics)
async def get_tool_metrics(tool_name: str) -> ToolPerformanceMetrics:
    """Get performance metrics for a specific tool."""
    try:
        registry = await _get_tool_registry()
        
        metrics = registry.get_performance_metrics()
        tool_metrics = metrics.get(tool_name)
        
        if not tool_metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No metrics found for tool '{tool_name}'"
            )
        
        total_executions = tool_metrics.get('total_executions', 0)
        successful_executions = tool_metrics.get('successful_executions', 0)
        failed_executions = total_executions - successful_executions
        
        return ToolPerformanceMetrics(
            tool_name=tool_name,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            success_rate=tool_metrics.get('success_rate', 0.0),
            average_execution_time=tool_metrics.get('average_time', 0.0),
            last_execution=tool_metrics.get('last_execution')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics for tool {tool_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool metrics: {e}"
        )


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_tools() -> Dict[str, Any]:
    """Refresh the tool registry and reload tools."""
    try:
        registry = await _get_tool_registry()
        
        logger.info("Refreshing tool registry")
        
        # Re-initialize the registry to pick up new tools
        await registry.initialize()
        
        # Get updated tool counts
        tools = registry.get_comprehensive_tool_list()
        
        logger.info("Successfully refreshed tool registry")
        
        return {
            "success": True,
            "message": "Tool registry refreshed successfully",
            "total_tools": tools['total_count'],
            "builtin_tools": len(tools['builtin_tools']),
            "mcp_tools": len(tools['mcp_tools']),
            "new_system_tools": len(tools['new_system_tools'])
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh tool registry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh tools: {e}"
        )