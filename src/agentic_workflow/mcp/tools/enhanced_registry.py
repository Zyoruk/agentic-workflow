"""
Enhanced tool registry that integrates built-in tools with MCP capabilities.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Union, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import inspect

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.mcp.client.base import MCPClient, MCPCapability, MCPExecutionError

# Import new tool system with fallback
try:
    from agentic_workflow.tools import ToolManager, ToolRegistry, ToolExecution, Tool as NewTool
    NEW_TOOL_SYSTEM_AVAILABLE = True
except ImportError:
    ToolManager = None
    ToolRegistry = None
    ToolExecution = None
    NewTool = None
    NEW_TOOL_SYSTEM_AVAILABLE = False

logger = get_logger(__name__)


@dataclass
class ToolMetadata:
    """Metadata for a tool."""
    name: str
    description: str
    parameters: Dict[str, Any]
    source: str  # 'builtin', 'mcp'
    category: str = 'general'
    tags: List[str] = None
    version: str = '1.0.0'
    author: str = 'system'
    created_at: datetime = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    performance_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.performance_metrics is None:
            self.performance_metrics = {}


class Tool(ABC):
    """Abstract base class for tools."""
    
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Get tool metadata."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass
    
    async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate parameters before execution."""
        return True


class BuiltinTool(Tool):
    """Base class for built-in tools."""
    
    def __init__(self, name: str, description: str, func: Callable, parameters: Dict[str, Any], **metadata_kwargs):
        """Initialize built-in tool.
        
        Args:
            name: Tool name
            description: Tool description  
            func: Tool function
            parameters: Tool parameters schema
            **metadata_kwargs: Additional metadata
        """
        self.func = func
        self._metadata = ToolMetadata(
            name=name,
            description=description,
            parameters=parameters,
            source='builtin',
            **metadata_kwargs
        )
    
    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata
    
    async def execute(self, **kwargs) -> Any:
        """Execute the built-in tool function."""
        try:
            if inspect.iscoroutinefunction(self.func):
                return await self.func(**kwargs)
            else:
                return self.func(**kwargs)
        except Exception as e:
            logger.error(f"Error executing builtin tool {self.metadata.name}: {e}")
            raise


class MCPTool(Tool):
    """Wrapper for MCP tools."""
    
    def __init__(self, capability: MCPCapability, mcp_client: MCPClient):
        """Initialize MCP tool.
        
        Args:
            capability: MCP capability
            mcp_client: MCP client instance
        """
        self.capability = capability
        self.mcp_client = mcp_client
        self._metadata = ToolMetadata(
            name=capability.name,
            description=capability.description,
            parameters=capability.parameters or {},
            source='mcp',
            category='mcp',
            tags=['mcp', capability.server_id],
            created_at=capability.created_at
        )
    
    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata
    
    async def execute(self, **kwargs) -> Any:
        """Execute the MCP tool."""
        try:
            result = await self.mcp_client.execute_tool(
                self.capability.name, 
                kwargs, 
                self.capability.server_id
            )
            
            # Update usage statistics
            self._metadata.last_used = datetime.now()
            self._metadata.usage_count += 1
            
            return result
            
        except MCPExecutionError as e:
            logger.error(f"Error executing MCP tool {self.metadata.name}: {e}")
            raise


class EnhancedToolRegistry:
    """
    Enhanced tool registry that combines built-in tools with MCP capabilities and the new tool system.
    
    Provides unified interface for tool discovery, execution, and management
    across built-in tools, the new integrated tool system, and dynamically discovered MCP tools.
    """
    
    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """Initialize enhanced tool registry.
        
        Args:
            mcp_client: Optional MCP client for dynamic tools
        """
        self.mcp_client = mcp_client
        self.builtin_tools: Dict[str, BuiltinTool] = {}
        self.mcp_tools: Dict[str, MCPTool] = {}
        self.tool_aliases: Dict[str, str] = {}
        self.tool_categories: Dict[str, List[str]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.max_history = 1000
        
        # Performance tracking
        self.performance_metrics: Dict[str, Dict[str, float]] = {}
        
        # Tool composition support
        self.tool_workflows: Dict[str, List[str]] = {}
        
        # Integration with new tool system
        self.new_tool_manager: Optional[ToolManager] = None
        self.new_tool_system_enabled = NEW_TOOL_SYSTEM_AVAILABLE
        
    async def initialize(self) -> None:
        """Initialize the tool registry with all available tool systems."""
        logger.info("Initializing enhanced tool registry with integrated systems")
        
        # Initialize new tool system if available
        if self.new_tool_system_enabled and ToolManager:
            await self._initialize_new_tool_system()
        
        # Load built-in tools
        await self._load_builtin_tools()
        
        # Load MCP tools if client available
        if self.mcp_client:
            await self._load_mcp_tools()
            
            # Set up MCP event callbacks
            self.mcp_client.add_event_callback('capability_added', self._on_capability_added)
            self.mcp_client.add_event_callback('capability_removed', self._on_capability_removed)
        
        total_tools = len(self.get_all_tools())
        if self.new_tool_manager:
            catalog = self.new_tool_manager.get_tool_catalog()
            total_tools += catalog.get('total_tools', 0)
            
        logger.info(f"Enhanced tool registry initialized with {total_tools} tools across all systems")
    
    async def _initialize_new_tool_system(self) -> None:
        """Initialize the new integrated tool system."""
        try:
            self.new_tool_manager = ToolManager()
            await self.new_tool_manager.initialize()
            logger.info("New tool system integrated successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize new tool system: {e}")
            self.new_tool_system_enabled = False
    
    async def _load_builtin_tools(self) -> None:
        """Load built-in tools."""
        # Example built-in tools
        builtin_tools = [
            {
                'name': 'echo',
                'description': 'Echo text back',
                'func': lambda text: text,
                'parameters': {'text': {'type': 'string', 'description': 'Text to echo'}},
                'category': 'utility'
            },
            {
                'name': 'calculate',
                'description': 'Perform basic calculations',
                'func': lambda expression: eval(expression),  # Note: eval is dangerous, use safer alternative in production
                'parameters': {'expression': {'type': 'string', 'description': 'Mathematical expression'}},
                'category': 'math'
            },
            {
                'name': 'current_time',
                'description': 'Get current timestamp',
                'func': lambda: datetime.now().isoformat(),
                'parameters': {},
                'category': 'utility'
            }
        ]
        
        for tool_config in builtin_tools:
            tool = BuiltinTool(**tool_config)
            await self.register_builtin_tool(tool)
    
    async def _load_mcp_tools(self) -> None:
        """Load tools from MCP capabilities."""
        if not self.mcp_client:
            return
            
        capabilities = await self.mcp_client.list_capabilities('tool')
        for capability in capabilities:
            tool = MCPTool(capability, self.mcp_client)
            self.mcp_tools[tool.metadata.name] = tool
            self._update_categories(tool.metadata)
        
        logger.info(f"Loaded {len(capabilities)} MCP tools")
    
    async def _on_capability_added(self, capability: MCPCapability) -> None:
        """Handle new MCP capability."""
        if capability.type == 'tool':
            tool = MCPTool(capability, self.mcp_client)
            self.mcp_tools[tool.metadata.name] = tool
            self._update_categories(tool.metadata)
            logger.info(f"Added MCP tool: {tool.metadata.name}")
    
    async def _on_capability_removed(self, capability: MCPCapability) -> None:
        """Handle removed MCP capability."""
        if capability.type == 'tool' and capability.name in self.mcp_tools:
            tool = self.mcp_tools.pop(capability.name)
            self._remove_from_categories(tool.metadata)
            logger.info(f"Removed MCP tool: {tool.metadata.name}")
    
    def _update_categories(self, metadata: ToolMetadata) -> None:
        """Update tool categories."""
        if metadata.category not in self.tool_categories:
            self.tool_categories[metadata.category] = []
        
        if metadata.name not in self.tool_categories[metadata.category]:
            self.tool_categories[metadata.category].append(metadata.name)
    
    def _remove_from_categories(self, metadata: ToolMetadata) -> None:
        """Remove tool from categories."""
        if metadata.category in self.tool_categories:
            try:
                self.tool_categories[metadata.category].remove(metadata.name)
                if not self.tool_categories[metadata.category]:
                    del self.tool_categories[metadata.category]
            except ValueError:
                pass
    
    async def register_builtin_tool(self, tool: BuiltinTool) -> bool:
        """
        Register a built-in tool.
        
        Args:
            tool: Built-in tool to register
            
        Returns:
            True if registration successful
        """
        try:
            if tool.metadata.name in self.builtin_tools:
                logger.warning(f"Built-in tool {tool.metadata.name} already registered")
                return False
            
            self.builtin_tools[tool.metadata.name] = tool
            self._update_categories(tool.metadata)
            
            logger.info(f"Registered built-in tool: {tool.metadata.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register built-in tool {tool.metadata.name}: {e}")
            return False
    
    async def unregister_builtin_tool(self, tool_name: str) -> bool:
        """
        Unregister a built-in tool.
        
        Args:
            tool_name: Name of tool to unregister
            
        Returns:
            True if unregistration successful
        """
        try:
            if tool_name not in self.builtin_tools:
                logger.warning(f"Built-in tool {tool_name} not found")
                return False
            
            tool = self.builtin_tools.pop(tool_name)
            self._remove_from_categories(tool.metadata)
            
            logger.info(f"Unregistered built-in tool: {tool_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister built-in tool {tool_name}: {e}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool instance or None if not found
        """
        # Check aliases first
        actual_name = self.tool_aliases.get(tool_name, tool_name)
        
        # Check built-in tools
        if actual_name in self.builtin_tools:
            return self.builtin_tools[actual_name]
        
        # Check MCP tools
        if actual_name in self.mcp_tools:
            return self.mcp_tools[actual_name]
        
        return None
    
    def get_all_tools(self) -> Dict[str, Tool]:
        """Get all available tools from MCP and built-in systems."""
        all_tools = {}
        all_tools.update(self.builtin_tools)
        all_tools.update(self.mcp_tools)
        return all_tools
    
    def get_comprehensive_tool_list(self) -> Dict[str, Any]:
        """Get comprehensive tool information from all systems."""
        result = {
            'mcp_tools': {},
            'builtin_tools': {},
            'new_system_tools': {},
            'total_count': 0
        }
        
        # MCP tools
        for name, tool in self.mcp_tools.items():
            result['mcp_tools'][name] = {
                'metadata': tool.metadata,
                'source': 'mcp',
                'available': True
            }
        
        # Built-in tools
        for name, tool in self.builtin_tools.items():
            result['builtin_tools'][name] = {
                'metadata': tool.metadata,
                'source': 'builtin',
                'available': True
            }
        
        # New system tools
        if self.new_tool_manager:
            try:
                catalog = self.new_tool_manager.get_tool_catalog()
                for category, tools in catalog.get('categories', {}).items():
                    for tool_info in tools:
                        tool_name = tool_info.get('id', tool_info.get('name', 'unknown'))
                        result['new_system_tools'][tool_name] = {
                            'name': tool_info.get('name'),
                            'description': tool_info.get('description'),
                            'category': category,
                            'source': 'new_system',
                            'available': True,
                            'version': tool_info.get('version'),
                            'tags': tool_info.get('tags', [])
                        }
            except Exception as e:
                logger.warning(f"Failed to get new system tools: {e}")
        
        # Calculate total
        result['total_count'] = (
            len(result['mcp_tools']) + 
            len(result['builtin_tools']) + 
            len(result['new_system_tools'])
        )
        
        return result
    
    def list_tools(self, category: Optional[str] = None, source: Optional[str] = None, tags: Optional[List[str]] = None) -> List[ToolMetadata]:
        """
        List tools with optional filtering.
        
        Args:
            category: Filter by category
            source: Filter by source ('builtin' or 'mcp')
            tags: Filter by tags
            
        Returns:
            List of tool metadata
        """
        tools = []
        
        for tool in self.get_all_tools().values():
            metadata = tool.metadata
            
            # Apply filters
            if category and metadata.category != category:
                continue
            if source and metadata.source != source:
                continue
            if tags and not any(tag in metadata.tags for tag in tags):
                continue
            
            tools.append(metadata)
        
        # Sort by usage count (most used first)
        tools.sort(key=lambda t: t.usage_count, reverse=True)
        return tools
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None, agent_id: str = "enhanced_registry") -> Any:
        """
        Execute a tool from any available system.
        
        Tries to execute from:
        1. MCP tools (highest priority for dynamic capabilities)
        2. New integrated tool system
        3. Built-in tools (fallback)
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            agent_id: ID of the agent executing the tool
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
            Exception: If tool execution fails
        """
        parameters = parameters or {}
        
        # Record execution start
        execution_start = datetime.now()
        
        try:
            # Try MCP tools first (highest priority)
            if tool_name in self.mcp_tools:
                tool = self.mcp_tools[tool_name]
                if await tool.validate_parameters(parameters):
                    result = await tool.execute(**parameters)
                    execution_time = (datetime.now() - execution_start).total_seconds()
                    await self._record_execution(tool_name, parameters, result, execution_time, True, source="mcp")
                    return result
            
            # Try new tool system if available
            if self.new_tool_manager:
                try:
                    execution = await self.new_tool_manager.execute_tool(tool_name, parameters, agent_id)
                    if execution.success:
                        await self._record_execution(tool_name, parameters, execution.outputs, execution.execution_time, True, source="new_system")
                        return execution.outputs
                    else:
                        logger.warning(f"New tool system execution failed for {tool_name}: {execution.error_message}")
                except Exception as e:
                    logger.debug(f"New tool system couldn't execute {tool_name}: {e}")
            
            # Try built-in tools as fallback
            if tool_name in self.builtin_tools:
                tool = self.builtin_tools[tool_name]
                if await tool.validate_parameters(parameters):
                    result = await tool.execute(**parameters)
                    execution_time = (datetime.now() - execution_start).total_seconds()
                    await self._record_execution(tool_name, parameters, result, execution_time, True, source="builtin")
                    return result
            
            # Tool not found in any system
            raise ValueError(f"Tool '{tool_name}' not found in any available system")
            
        except Exception as e:
            # Record failed execution
            execution_time = (datetime.now() - execution_start).total_seconds()
            await self._record_execution(tool_name, parameters, None, execution_time, False, str(e))
            raise
    
    async def _record_execution(self, tool_name: str, parameters: Dict[str, Any], result: Any, 
                               execution_time: float, success: bool, error: Optional[str] = None, 
                               source: str = "unknown") -> None:
        """Record tool execution in history."""
        execution_record = {
            'tool_name': tool_name,
            'parameters': parameters,
            'result': result if success else None,
            'execution_time': execution_time,
            'success': success,
            'error': error,
            'source': source,
            'timestamp': datetime.now().isoformat()
        }
        
        self.execution_history.append(execution_record)
        
        # Limit history size
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]
        
        # Update performance metrics
        if tool_name not in self.performance_metrics:
            self.performance_metrics[tool_name] = {
                'total_executions': 0,
                'successful_executions': 0,
                'total_time': 0.0,
                'average_time': 0.0,
                'success_rate': 0.0
            }
        
        metrics = self.performance_metrics[tool_name]
        metrics['total_executions'] += 1
        if success:
            metrics['successful_executions'] += 1
        metrics['total_time'] += execution_time
        metrics['average_time'] = metrics['total_time'] / metrics['total_executions']
        metrics['success_rate'] = metrics['successful_executions'] / metrics['total_executions']
    
    def search_tools(self, query: str) -> List[ToolMetadata]:
        """
        Search tools by name, description, or tags.
        
        Args:
            query: Search query
            
        Returns:
            List of matching tool metadata
        """
        query_lower = query.lower()
        matches = []
        
        for tool in self.get_all_tools().values():
            metadata = tool.metadata
            
            # Check name, description, and tags
            if (query_lower in metadata.name.lower() or
                query_lower in metadata.description.lower() or
                any(query_lower in tag.lower() for tag in metadata.tags)):
                matches.append(metadata)
        
        return matches
    
    def get_tool_recommendations(self, context: str, limit: int = 5) -> List[ToolMetadata]:
        """
        Get tool recommendations based on context.
        
        Args:
            context: Context description
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended tool metadata
        """
        # Simple keyword-based recommendations
        context_lower = context.lower()
        scores = {}
        
        for tool in self.get_all_tools().values():
            metadata = tool.metadata
            score = 0
            
            # Score based on keyword matches
            if any(word in metadata.description.lower() for word in context_lower.split()):
                score += 10
            
            # Score based on usage count
            score += metadata.usage_count * 0.1
            
            # Score based on success rate
            metrics = self.performance_metrics.get(metadata.name, {})
            score += metrics.get('success_rate', 0) * 5
            
            scores[metadata.name] = score
        
        # Sort by score and return top recommendations
        sorted_tools = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for tool_name, score in sorted_tools[:limit]:
            tool = self.get_tool(tool_name)
            if tool and score > 0:
                recommendations.append(tool.metadata)
        
        return recommendations
    
    async def create_tool_workflow(self, workflow_name: str, tool_sequence: List[str], description: str = "") -> bool:
        """
        Create a workflow of tool executions.
        
        Args:
            workflow_name: Name of the workflow
            tool_sequence: Sequence of tool names
            description: Workflow description
            
        Returns:
            True if workflow creation successful
        """
        try:
            # Validate all tools exist
            missing_tools = [name for name in tool_sequence if not self.get_tool(name)]
            if missing_tools:
                logger.error(f"Missing tools for workflow: {missing_tools}")
                return False
            
            self.tool_workflows[workflow_name] = tool_sequence
            logger.info(f"Created workflow '{workflow_name}' with {len(tool_sequence)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create workflow {workflow_name}: {e}")
            return False
    
    async def execute_workflow(self, workflow_name: str, initial_parameters: Dict[str, Any] = None) -> List[Any]:
        """
        Execute a tool workflow.
        
        Args:
            workflow_name: Name of the workflow
            initial_parameters: Initial parameters
            
        Returns:
            List of results from each tool execution
        """
        if workflow_name not in self.tool_workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        tool_sequence = self.tool_workflows[workflow_name]
        results = []
        current_parameters = initial_parameters or {}
        
        for tool_name in tool_sequence:
            try:
                result = await self.execute_tool(tool_name, current_parameters)
                results.append(result)
                
                # Pass result to next tool if it's a dict
                if isinstance(result, dict):
                    current_parameters.update(result)
                
            except Exception as e:
                logger.error(f"Workflow {workflow_name} failed at tool {tool_name}: {e}")
                raise
        
        return results
    
    def add_tool_alias(self, alias: str, tool_name: str) -> bool:
        """
        Add an alias for a tool.
        
        Args:
            alias: Alias name
            tool_name: Actual tool name
            
        Returns:
            True if alias added successfully
        """
        if not self.get_tool(tool_name):
            logger.error(f"Cannot create alias '{alias}' for non-existent tool '{tool_name}'")
            return False
        
        self.tool_aliases[alias] = tool_name
        logger.info(f"Added alias '{alias}' for tool '{tool_name}'")
        return True
    
    def get_categories(self) -> Dict[str, List[str]]:
        """Get all tool categories."""
        return self.tool_categories.copy()
    
    def get_performance_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for tools."""
        if tool_name:
            return self.performance_metrics.get(tool_name, {})
        return self.performance_metrics.copy()
    
    def get_execution_history(self, tool_name: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get execution history."""
        history = self.execution_history
        
        if tool_name:
            history = [record for record in history if record['tool_name'] == tool_name]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    async def refresh_mcp_tools(self) -> None:
        """Refresh MCP tools from connected servers."""
        if not self.mcp_client:
            return
        
        # Clear existing MCP tools
        old_tools = list(self.mcp_tools.keys())
        for tool_name in old_tools:
            tool = self.mcp_tools.pop(tool_name)
            self._remove_from_categories(tool.metadata)
        
        # Reload MCP tools
        await self._load_mcp_tools()
        
        logger.info(f"Refreshed MCP tools: removed {len(old_tools)}, added {len(self.mcp_tools)}")
    
    async def close(self) -> None:
        """Close the tool registry and cleanup resources."""
        logger.info("Closing enhanced tool registry")
        
        # Remove MCP event callbacks
        if self.mcp_client:
            self.mcp_client.remove_event_callback('capability_added', self._on_capability_added)
            self.mcp_client.remove_event_callback('capability_removed', self._on_capability_removed)
        
        # Clear data
        self.builtin_tools.clear()
        self.mcp_tools.clear()
        self.tool_aliases.clear()
        self.tool_categories.clear()
        self.execution_history.clear()
        self.performance_metrics.clear()
        self.tool_workflows.clear()
        
        logger.info("Tool registry closed")