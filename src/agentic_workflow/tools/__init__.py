"""Tool integration and discovery system for agentic workflow.

This module provides dynamic tool discovery, registration, and management
capabilities that allow agents to discover and utilize tools at runtime.
"""

import asyncio
import importlib
import inspect
import json
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from pkgutil import iter_modules
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from agentic_workflow.core.exceptions import AgentError
from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)


class ToolCapability(BaseModel):
    """Describes a tool's capabilities and metadata."""

    name: str
    description: str
    category: str  # e.g., "development", "communication", "analysis"
    tags: List[str] = []
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    requirements: List[str] = []  # e.g., ["python>=3.8", "requests"]
    author: Optional[str] = None
    version: str = "1.0.0"
    documentation_url: Optional[str] = None


class ToolExecution(BaseModel):
    """Records a tool execution for monitoring and analytics."""

    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_id: str
    agent_id: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any] = {}
    success: bool = False
    error_message: Optional[str] = None
    execution_time: float = 0.0
    start_time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    end_time: Optional[str] = None
    metadata: Dict[str, Any] = {}


class Tool(ABC):
    """Abstract base class for all tools in the system."""

    def __init__(self, tool_id: str, capabilities: ToolCapability):
        self.tool_id = tool_id
        self.capabilities = capabilities
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self._executions: List[ToolExecution] = []

    @abstractmethod
    async def execute(
        self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the tool with given inputs."""
        pass

    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate that inputs match the tool's expected schema."""
        pass

    async def execute_with_monitoring(
        self,
        inputs: Dict[str, Any],
        agent_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolExecution:
        """Execute tool with full monitoring and error handling."""
        execution = ToolExecution(
            tool_id=self.tool_id, agent_id=agent_id, inputs=inputs
        )

        start_time = datetime.now(UTC)

        try:
            # Validate inputs
            if not self.validate_inputs(inputs):
                raise ValueError(f"Invalid inputs for tool {self.tool_id}")

            self.logger.info(f"Executing tool {self.tool_id} for agent {agent_id}")

            # Execute the tool
            outputs = await self.execute(inputs, context)

            execution.outputs = outputs
            execution.success = True

            self.logger.info(f"Tool {self.tool_id} executed successfully")

        except Exception as e:
            execution.error_message = str(e)
            execution.success = False
            self.logger.error(f"Tool {self.tool_id} execution failed: {e}")

        finally:
            end_time = datetime.now(UTC)
            execution.end_time = end_time.isoformat()
            execution.execution_time = (end_time - start_time).total_seconds()

            # Store execution record
            self._executions.append(execution)

        return execution

    def get_execution_history(self, limit: int = 100) -> List[ToolExecution]:
        """Get recent execution history for this tool."""
        return self._executions[-limit:]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this tool."""
        if not self._executions:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "average_execution_time": 0.0,
                "error_rate": 0.0,
            }

        total = len(self._executions)
        successful = sum(1 for exec in self._executions if exec.success)
        avg_time = sum(exec.execution_time for exec in self._executions) / total

        return {
            "total_executions": total,
            "success_rate": successful / total,
            "average_execution_time": avg_time,
            "error_rate": (total - successful) / total,
            "last_execution": (
                self._executions[-1].start_time if self._executions else None
            ),
        }


class ToolRegistry:
    """Central registry for tool discovery and management."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._capabilities: Dict[str, ToolCapability] = {}
        self._categories: Dict[str, List[str]] = {}
        self.logger = get_logger(__name__)

    def register_tool(self, tool: Tool) -> None:
        """Register a tool in the registry."""
        tool_id = tool.tool_id
        capabilities = tool.capabilities

        if tool_id in self._tools:
            self.logger.warning(f"Tool {tool_id} already registered, overwriting")

        self._tools[tool_id] = tool
        self._capabilities[tool_id] = capabilities

        # Update category index
        category = capabilities.category
        if category not in self._categories:
            self._categories[category] = []
        if tool_id not in self._categories[category]:
            self._categories[category].append(tool_id)

        self.logger.info(f"Registered tool: {tool_id} (category: {category})")

    def unregister_tool(self, tool_id: str) -> None:
        """Unregister a tool from the registry."""
        if tool_id not in self._tools:
            raise ValueError(f"Tool {tool_id} not found in registry")

        capabilities = self._capabilities[tool_id]
        category = capabilities.category

        del self._tools[tool_id]
        del self._capabilities[tool_id]

        if category in self._categories:
            self._categories[category].remove(tool_id)
            if not self._categories[category]:
                del self._categories[category]

        self.logger.info(f"Unregistered tool: {tool_id}")

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def list_tools(
        self, category: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[str]:
        """List available tools, optionally filtered by category or tags."""
        if category:
            tool_ids = self._categories.get(category, [])
        else:
            tool_ids = list(self._tools.keys())

        if tags:
            filtered_ids = []
            for tool_id in tool_ids:
                capabilities = self._capabilities[tool_id]
                if any(tag in capabilities.tags for tag in tags):
                    filtered_ids.append(tool_id)
            tool_ids = filtered_ids

        return tool_ids

    def get_capabilities(self, tool_id: str) -> Optional[ToolCapability]:
        """Get capabilities for a specific tool."""
        return self._capabilities.get(tool_id)

    def list_categories(self) -> List[str]:
        """List all available tool categories."""
        return list(self._categories.keys())

    def search_tools(self, query: str) -> List[str]:
        """Search tools by name, description, or tags."""
        query_lower = query.lower()
        query_words = query_lower.split()
        matching_tools = []

        for tool_id, capabilities in self._capabilities.items():
            # Search in name, description, and tags
            searchable_text = " ".join(
                [
                    capabilities.name.lower(),
                    capabilities.description.lower(),
                    " ".join(capabilities.tags).lower(),
                ]
            )

            # Check if all words in query are found in searchable text
            if all(word in searchable_text for word in query_words):
                matching_tools.append(tool_id)

        return matching_tools

    async def execute_tool(
        self,
        tool_id: str,
        inputs: Dict[str, Any],
        agent_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolExecution:
        """Execute a tool by ID."""
        tool = self.get_tool(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found in registry")

        return await tool.execute_with_monitoring(inputs, agent_id, context)

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the tool registry."""
        return {
            "total_tools": len(self._tools),
            "categories": len(self._categories),
            "tools_by_category": {
                cat: len(tools) for cat, tools in self._categories.items()
            },
            "all_categories": list(self._categories.keys()),
        }


class ToolDiscovery:
    """Automatic tool discovery system."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.logger = get_logger(__name__)

    def discover_from_module(self, module_name: str) -> List[str]:
        """Discover tools from a Python module."""
        discovered_tools = []

        try:
            module = importlib.import_module(module_name)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Tool)
                    and obj != Tool
                    and not inspect.isabstract(obj)
                ):

                    try:
                        # Try to instantiate the tool
                        # This assumes the tool has a default constructor or factory method
                        if hasattr(obj, "create_default"):
                            tool_instance = obj.create_default()
                        else:
                            # Skip tools that can't be auto-instantiated
                            continue

                        self.registry.register_tool(tool_instance)
                        discovered_tools.append(tool_instance.tool_id)

                    except Exception as e:
                        self.logger.warning(f"Failed to instantiate tool {name}: {e}")

            self.logger.info(
                f"Discovered {len(discovered_tools)} tools from {module_name}"
            )

        except ImportError as e:
            self.logger.error(f"Failed to import module {module_name}: {e}")

        return discovered_tools

    def discover_from_directory(self, directory_path: str) -> List[str]:
        """Discover tools from a directory containing Python files."""
        discovered_tools: List[str] = []
        directory = Path(directory_path)

        if not directory.exists():
            self.logger.error(f"Directory {directory_path} does not exist")
            return discovered_tools

        for py_file in directory.glob("*.py"):
            if py_file.stem == "__init__":
                continue

            try:
                # Create module name from file path
                module_name = f"{directory.stem}.{py_file.stem}"
                tools = self.discover_from_module(module_name)
                discovered_tools.extend(tools)

            except Exception as e:
                self.logger.warning(f"Failed to discover tools from {py_file}: {e}")

        return discovered_tools

    def discover_from_package(self, package_name: str) -> List[str]:
        """Discover tools from a Python package."""
        discovered_tools = []

        try:
            package = importlib.import_module(package_name)

            if hasattr(package, "__path__"):
                for finder, name, ispkg in iter_modules(
                    package.__path__, package.__name__ + "."
                ):
                    tools = self.discover_from_module(name)
                    discovered_tools.extend(tools)

        except ImportError as e:
            self.logger.error(f"Failed to import package {package_name}: {e}")

        return discovered_tools


class ToolManager:
    """High-level tool management interface."""

    def __init__(self) -> None:
        self.registry = ToolRegistry()
        self.discovery = ToolDiscovery(self.registry)
        self.logger = get_logger(__name__)

    async def initialize(self) -> None:
        """Initialize the tool manager with default tools."""
        self.logger.info("Initializing tool manager")

        # Discover built-in tools
        built_in_tools = []

        # Try to discover from common tool locations
        tool_locations = [
            "agentic_workflow.tools.builtin",
            "agentic_workflow.tools.development",
            "agentic_workflow.tools.communication",
        ]

        for location in tool_locations:
            try:
                tools = self.discovery.discover_from_package(location)
                built_in_tools.extend(tools)
            except Exception as e:
                self.logger.debug(f"No tools found in {location}: {e}")

        self.logger.info(
            f"Initialized tool manager with {len(built_in_tools)} built-in tools"
        )

    async def execute_tool(
        self,
        tool_identifier: str,
        inputs: Dict[str, Any],
        agent_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolExecution:
        """Execute a tool by ID or find best match."""

        # First try direct tool ID lookup
        tool = self.registry.get_tool(tool_identifier)
        if tool:
            return await self.registry.execute_tool(
                tool_identifier, inputs, agent_id, context
            )

        # If not found, try searching for similar tools
        matching_tools = self.registry.search_tools(tool_identifier)
        if matching_tools:
            best_match = matching_tools[0]  # Take first match
            self.logger.info(
                f"Using tool {best_match} as best match for '{tool_identifier}'"
            )
            return await self.registry.execute_tool(
                best_match, inputs, agent_id, context
            )

        raise ValueError(f"No tool found matching '{tool_identifier}'")

    def recommend_tools(
        self, task_description: str, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Recommend tools based on task description."""
        # Simple keyword-based recommendation
        recommendations = []

        # Search for tools matching the task description
        matching_tools = self.registry.search_tools(task_description)

        # Filter by category if specified
        if category:
            category_tools = self.registry.list_tools(category=category)
            matching_tools = [t for t in matching_tools if t in category_tools]

        for tool_id in matching_tools:
            capabilities = self.registry.get_capabilities(tool_id)
            tool = self.registry.get_tool(tool_id)

            if capabilities and tool:
                metrics = tool.get_performance_metrics()
                recommendations.append(
                    {
                        "tool_id": tool_id,
                        "name": capabilities.name,
                        "description": capabilities.description,
                        "category": capabilities.category,
                        "success_rate": metrics["success_rate"],
                        "avg_execution_time": metrics["average_execution_time"],
                    }
                )

        # Sort by success rate and avg execution time
        recommendations.sort(
            key=lambda x: (-x["success_rate"], x["avg_execution_time"])
        )

        return recommendations

    def get_tool_catalog(self) -> Dict[str, Any]:
        """Get a complete catalog of available tools."""
        catalog: Dict[str, Any] = {
            "categories": {},
            "total_tools": 0,
            "registry_stats": self.registry.get_registry_stats(),
        }

        for category in self.registry.list_categories():
            tools_in_category = []
            tool_ids = self.registry.list_tools(category=category)

            for tool_id in tool_ids:
                capabilities = self.registry.get_capabilities(tool_id)
                tool = self.registry.get_tool(tool_id)

                if capabilities and tool:
                    metrics = tool.get_performance_metrics()
                    tools_in_category.append(
                        {
                            "id": tool_id,
                            "name": capabilities.name,
                            "description": capabilities.description,
                            "version": capabilities.version,
                            "tags": capabilities.tags,
                            "metrics": metrics,
                        }
                    )

            catalog["categories"][category] = tools_in_category
            catalog["total_tools"] += len(tools_in_category)

        return catalog
