"""
MCP-enhanced agent integration for the agentic workflow system.

This module provides agents with MCP capabilities while maintaining
full backward compatibility with existing agent implementations.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from agentic_workflow.agents.base import Agent, AgentResult, AgentTask
from agentic_workflow.core.logging_config import get_logger

try:
    from agentic_workflow.memory.manager import MemoryManager
except ImportError:
    MemoryManager = None
try:
    from agentic_workflow.guardrails.service import GuardrailsService
except ImportError:
    GuardrailsService = None
try:
    from agentic_workflow.core.reasoning import ReasoningEngine
except ImportError:
    ReasoningEngine = None
try:
    from agentic_workflow.core.communication import CommunicationManager
except ImportError:
    CommunicationManager = None
from agentic_workflow.mcp.client.base import MCPClient, MCPServerConfig
from agentic_workflow.mcp.client.registry import MCPServerRegistry
from agentic_workflow.mcp.tools.enhanced_registry import EnhancedToolRegistry

logger = get_logger(__name__)


class MCPEnhancedAgent(Agent):
    """
    Agent enhanced with MCP capabilities, advanced reasoning patterns, and communication.

    Extends the base Agent class to provide:
    - Access to dynamic MCP tools, resources, and prompts
    - Advanced reasoning patterns (Chain of Thought, ReAct, RAISE)
    - Multi-agent communication and coordination
    - Full backward compatibility with existing agent implementations

    The agent intelligently combines MCP capabilities with reasoning patterns:
    - Uses RAISE pattern for multi-agent coordination tasks
    - Uses ReAct pattern for iterative implementation tasks
    - Uses Chain of Thought for strategic planning and analysis
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str = "mcp_enhanced",
        config: Optional[Dict[str, Any]] = None,
        memory_manager: Optional[Any] = None,
        guardrails_service: Optional[Any] = None,
        communication_manager: Optional[Any] = None,
        mcp_enabled: bool = True,
        mcp_servers: Optional[List[MCPServerConfig]] = None,
        mcp_categories: Optional[List[str]] = None,
        auto_discover_servers: bool = True,
        max_mcp_connections: int = 10,
        reasoning_enabled: bool = True,
        default_reasoning_pattern: str = "chain_of_thought",
        **kwargs,
    ):
        """
        Initialize MCP-enhanced agent with advanced reasoning and communication.

        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent
            config: Agent configuration
            memory_manager: Memory manager instance
            guardrails_service: Guardrails service instance
            communication_manager: Communication manager for multi-agent coordination
            mcp_enabled: Whether to enable MCP capabilities
            mcp_servers: List of MCP server configurations to connect
            mcp_categories: List of server categories to auto-connect
            auto_discover_servers: Whether to auto-discover available servers
            max_mcp_connections: Maximum MCP server connections
            reasoning_enabled: Whether to enable advanced reasoning patterns
            default_reasoning_pattern: Default reasoning pattern (chain_of_thought, react, raise)
            **kwargs: Additional agent configuration
        """
        super().__init__(agent_id, config, memory_manager, guardrails_service)

        # MCP configuration
        self.mcp_enabled = mcp_enabled
        self.mcp_servers = mcp_servers or []
        self.mcp_categories = mcp_categories or ["development", "data"]
        self.auto_discover_servers = auto_discover_servers
        self.max_mcp_connections = max_mcp_connections

        # Enhanced capabilities configuration
        self.reasoning_enabled = reasoning_enabled and ReasoningEngine is not None
        self.default_reasoning_pattern = default_reasoning_pattern
        self.communication_manager = communication_manager

        # MCP components
        self.mcp_client: Optional[MCPClient] = None
        self.mcp_registry: Optional[MCPServerRegistry] = None
        self.enhanced_tools: Optional[EnhancedToolRegistry] = None

        # Enhanced reasoning components
        self.reasoning_engine: Optional[Any] = None

        # MCP state
        self.mcp_initialized = False
        self.connected_servers: Dict[str, bool] = {}
        self.mcp_capabilities_cache: Dict[str, Any] = {}

        # Enhanced reasoning state
        self.dynamic_capabilities: List[str] = []
        self.capability_usage_history: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize the agent with MCP and enhanced capabilities."""
        logger.info(f"Initializing MCP-enhanced agent: {self.agent_id}")

        # Initialize base agent
        await super().initialize()

        # Initialize enhanced reasoning
        if self.reasoning_enabled:
            await self._initialize_reasoning()

        # Initialize MCP if enabled
        if self.mcp_enabled:
            await self._initialize_mcp()

        logger.info(
            f"Agent {self.agent_id} initialized with MCP: {self.mcp_enabled}, Reasoning: {self.reasoning_enabled}"
        )

    async def _initialize_reasoning(self) -> None:
        """Initialize reasoning engine with MCP awareness."""
        try:
            if ReasoningEngine:
                self.reasoning_engine = ReasoningEngine(
                    agent_id=self.agent_id,
                    memory_manager=self.memory_manager,
                    communication_manager=self.communication_manager,
                )
                logger.info(f"Reasoning engine initialized for agent {self.agent_id}")
            else:
                logger.warning(
                    f"ReasoningEngine not available for agent {self.agent_id}"
                )
                self.reasoning_enabled = False
        except Exception as e:
            logger.error(
                f"Failed to initialize reasoning engine for agent {self.agent_id}: {e}"
            )
            self.reasoning_enabled = False

    async def _initialize_mcp(self) -> None:
        """Initialize MCP components."""
        try:
            # Create MCP client
            self.mcp_client = MCPClient(max_connections=self.max_mcp_connections)
            await self.mcp_client.initialize()

            # Create MCP registry
            self.mcp_registry = MCPServerRegistry()
            await self.mcp_registry.initialize(self.mcp_client)

            # Create enhanced tool registry
            self.enhanced_tools = EnhancedToolRegistry(self.mcp_client)
            await self.enhanced_tools.initialize()

            # Connect to specified servers
            await self._connect_mcp_servers()

            # Auto-discover servers if enabled
            if self.auto_discover_servers:
                await self._auto_discover_servers()

            # Cache initial capabilities
            await self._cache_mcp_capabilities()

            self.mcp_initialized = True
            logger.info(f"MCP initialization completed for agent {self.agent_id}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP for agent {self.agent_id}: {e}")
            self.mcp_enabled = False

    async def _connect_mcp_servers(self) -> None:
        """Connect to configured MCP servers."""
        if not self.mcp_registry:
            return

        # Register and connect specified servers
        for server_config in self.mcp_servers:
            success = await self.mcp_registry.register_server(server_config)
            if success:
                self.connected_servers[server_config.name] = True
            else:
                self.connected_servers[server_config.name] = False

        # Connect servers from categories
        for category in self.mcp_categories:
            results = await self.mcp_registry.connect_servers(category=category)
            self.connected_servers.update(results)

        connected_count = sum(
            1 for connected in self.connected_servers.values() if connected
        )
        logger.info(f"Agent {self.agent_id} connected to {connected_count} MCP servers")

    async def _auto_discover_servers(self) -> None:
        """Auto-discover available MCP servers."""
        if not self.mcp_registry:
            return

        try:
            discovered = await self.mcp_registry.discover_available_servers()
            logger.info(
                f"Agent {self.agent_id} discovered {len(discovered)} available servers"
            )

            # Connect to high-priority discovered servers
            high_priority_servers = self.mcp_registry.get_servers_by_priority(1)
            for server_config in high_priority_servers[
                :5
            ]:  # Limit to 5 auto-discovered
                if server_config.name not in self.connected_servers:
                    success = await self.mcp_client.register_server(server_config)
                    self.connected_servers[server_config.name] = success

        except Exception as e:
            logger.warning(f"Auto-discovery failed for agent {self.agent_id}: {e}")

    async def _cache_mcp_capabilities(self) -> None:
        """Cache available MCP capabilities."""
        if not self.mcp_client:
            return

        try:
            # Cache tools
            tools = await self.mcp_client.list_capabilities("tool")
            self.mcp_capabilities_cache["tools"] = [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "server": cap.server_id,
                }
                for cap in tools
            ]

            # Cache resources
            resources = await self.mcp_client.list_capabilities("resource")
            self.mcp_capabilities_cache["resources"] = [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "server": cap.server_id,
                }
                for cap in resources
            ]

            # Cache prompts
            prompts = await self.mcp_client.list_capabilities("prompt")
            self.mcp_capabilities_cache["prompts"] = [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "server": cap.server_id,
                }
                for cap in prompts
            ]

            # Update dynamic capabilities list
            self.dynamic_capabilities = [
                cap["name"] for cap in self.mcp_capabilities_cache.get("tools", [])
            ]

            logger.info(
                f"Agent {self.agent_id} cached {len(tools)} tools, {len(resources)} resources, {len(prompts)} prompts"
            )

        except Exception as e:
            logger.error(
                f"Failed to cache MCP capabilities for agent {self.agent_id}: {e}"
            )

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute a task with enhanced MCP capabilities.

        Args:
            task: Task to execute

        Returns:
            Agent execution result
        """
        # If MCP is disabled, provide a simple fallback execution
        if not self.mcp_enabled:
            logger.info(
                f"Agent {self.agent_id} executing task without MCP: {task.task_id}"
            )
            start_time = datetime.now()

            # Simple fallback execution - just return success with basic data
            fallback_result = {
                "result": "traditional execution",
                "task_completed": True,
                "mcp_enabled": False,
            }

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                success=True,
                data=fallback_result,
                task_id=task.task_id,
                agent_id=self.agent_id,
                execution_time=execution_time,
                steps_taken=[
                    {
                        "step": "fallback_execution",
                        "timestamp": datetime.now().isoformat(),
                        "data": fallback_result,
                    }
                ],
                metadata={"mcp_enabled": False, "execution_mode": "fallback"},
            )

        start_time = datetime.now()
        execution_steps = []

        try:
            logger.info(f"Agent {self.agent_id} executing task: {task.task_id}")

            # Pre-execution: Assess available capabilities
            if self.mcp_enabled and self.mcp_initialized:
                await self._assess_dynamic_capabilities(task)
                execution_steps.append(
                    {
                        "step": "capability_assessment",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "available_tools": len(self.dynamic_capabilities),
                            "connected_servers": len(
                                [s for s in self.connected_servers.values() if s]
                            ),
                        },
                    }
                )

            # Enhanced reasoning with MCP awareness
            reasoning_result = await self._enhanced_reasoning(task)
            execution_steps.append(
                {
                    "step": "enhanced_reasoning",
                    "timestamp": datetime.now().isoformat(),
                    "data": reasoning_result,
                }
            )

            # Execute task with dynamic tools
            task_result = await self._execute_with_mcp(task, reasoning_result)
            execution_steps.append(
                {
                    "step": "task_execution",
                    "timestamp": datetime.now().isoformat(),
                    "data": task_result,
                }
            )

            # Post-execution: Update capability usage
            if self.mcp_enabled and self.mcp_initialized:
                await self._update_capability_usage(task, task_result)

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                success=True,
                data=task_result,
                task_id=task.task_id,
                agent_id=self.agent_id,
                execution_time=execution_time,
                steps_taken=execution_steps,
                metadata={
                    "mcp_enabled": self.mcp_enabled,
                    "mcp_tools_used": getattr(self, "_mcp_tools_used", []),
                    "dynamic_capabilities_count": len(self.dynamic_capabilities),
                },
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Task execution failed for agent {self.agent_id}: {e}")

            return AgentResult(
                success=False,
                error=str(e),
                task_id=task.task_id,
                agent_id=self.agent_id,
                execution_time=execution_time,
                steps_taken=execution_steps,
            )

    async def plan(
        self, objective: str, context: Optional[Dict[str, Any]] = None
    ) -> List[AgentTask]:
        """
        Create execution plan for objective with MCP capability awareness.

        Args:
            objective: High-level goal or objective to achieve
            context: Additional context for planning

        Returns:
            List of AgentTask objects representing the execution plan
        """
        try:
            logger.info(f"Agent {self.agent_id} planning for objective: {objective}")

            # Assess available capabilities for planning
            if self.mcp_enabled and self.mcp_initialized:
                await self._cache_mcp_capabilities()

            # Break down objective into tasks
            tasks = []

            # Simple planning approach - can be enhanced with more sophisticated AI planning
            objective_lower = objective.lower()

            if "analyze" in objective_lower:
                # Analysis objective
                if "code" in objective_lower:
                    tasks.append(
                        AgentTask(
                            type="code_analysis",
                            description=f"Analyze code for: {objective}",
                            requirements=["syntax check", "quality analysis"],
                        )
                    )
                elif "file" in objective_lower:
                    tasks.append(
                        AgentTask(
                            type="file_analysis",
                            description=f"Analyze files for: {objective}",
                            requirements=["content analysis", "structure check"],
                        )
                    )
                else:
                    tasks.append(
                        AgentTask(
                            type="general_analysis",
                            description=f"General analysis for: {objective}",
                            requirements=["data analysis"],
                        )
                    )

            elif "process" in objective_lower or "transform" in objective_lower:
                # Processing objective
                tasks.append(
                    AgentTask(
                        type="data_processing",
                        description=f"Process data for: {objective}",
                        requirements=["data transformation", "validation"],
                    )
                )

            elif "generate" in objective_lower or "create" in objective_lower:
                # Generation objective
                tasks.append(
                    AgentTask(
                        type="content_generation",
                        description=f"Generate content for: {objective}",
                        requirements=["content creation"],
                    )
                )

            else:
                # Default task
                tasks.append(
                    AgentTask(
                        type="general_task",
                        description=objective,
                        requirements=["general execution"],
                    )
                )

            # Add context to tasks if provided
            if context:
                for task in tasks:
                    task.update(context)

            logger.info(f"Agent {self.agent_id} created plan with {len(tasks)} tasks")
            return tasks

        except Exception as e:
            logger.error(f"Planning failed for agent {self.agent_id}: {e}")
            # Return basic fallback task
            return [
                AgentTask(
                    type="fallback_task",
                    description=objective,
                    requirements=["basic execution"],
                )
            ]

    async def _assess_dynamic_capabilities(self, task: AgentTask) -> None:
        """Assess available dynamic capabilities for the task."""
        try:
            # Refresh capabilities cache
            await self._cache_mcp_capabilities()

            # Analyze task requirements against available capabilities
            task_description = task.get("description", "")
            task_type = task.get("type", "")

            # Simple keyword-based capability matching
            relevant_tools = []
            for tool_info in self.mcp_capabilities_cache.get("tools", []):
                if any(
                    keyword in tool_info["description"].lower()
                    for keyword in [task_type.lower(), "file", "code", "git", "data"]
                ):
                    relevant_tools.append(tool_info["name"])

            self.dynamic_capabilities = relevant_tools
            logger.debug(
                f"Agent {self.agent_id} identified {len(relevant_tools)} relevant tools for task"
            )

        except Exception as e:
            logger.warning(
                f"Capability assessment failed for agent {self.agent_id}: {e}"
            )

    async def _enhanced_reasoning(self, task: AgentTask) -> Dict[str, Any]:
        """
        Enhanced reasoning with MCP capability awareness.

        Integrates traditional reasoning patterns (CoT, ReAct, RAISE) with dynamic MCP capability assessment.
        """
        reasoning_result = {
            "approach": "enhanced_mcp_reasoning",
            "capabilities_considered": self.dynamic_capabilities.copy(),
            "reasoning_steps": [],
            "selected_tools": [],
            "confidence": 0.8,
            "reasoning_pattern": self.default_reasoning_pattern,
        }

        try:
            # Use new reasoning engine if available
            if self.reasoning_enabled and self.reasoning_engine:
                objective = task.get("description", "Execute task")
                context = {
                    "task_id": task.get("id", "unknown"),
                    "task_type": task.get("type", "general"),
                    "available_mcp_tools": self.dynamic_capabilities,
                    "mcp_capabilities": self.mcp_capabilities_cache,
                }

                # Execute reasoning with MCP context
                reasoning_path = await self._execute_mcp_aware_reasoning(
                    objective, context
                )

                reasoning_result.update(
                    {
                        "reasoning_path_id": reasoning_path.path_id,
                        "reasoning_steps": [
                            {
                                "step_number": step.step_number,
                                "question": step.question,
                                "thought": step.thought,
                                "action": step.action,
                                "observation": step.observation,
                                "confidence": step.confidence,
                            }
                            for step in reasoning_path.steps
                        ],
                        "final_answer": reasoning_path.final_answer,
                        "confidence": reasoning_path.confidence,
                        "reasoning_pattern": reasoning_path.pattern_type,
                    }
                )

                # Extract tool selections from reasoning
                selected_tools = self._extract_tools_from_reasoning(reasoning_path)
                reasoning_result["selected_tools"] = selected_tools

                return reasoning_result

            # Fallback to basic MCP-aware reasoning
            return await self._basic_mcp_reasoning(task, reasoning_result)

        except Exception as e:
            logger.error(f"Enhanced reasoning failed for agent {self.agent_id}: {e}")
            reasoning_result["error"] = str(e)
            reasoning_result["confidence"] = 0.1
            return reasoning_result

    async def _execute_mcp_aware_reasoning(
        self, objective: str, context: Dict[str, Any]
    ):
        """Execute reasoning with MCP capability awareness."""
        # Choose reasoning pattern based on task complexity
        task_type = context.get("task_type", "general")

        if task_type in ["coordination", "multi_agent", "collaboration"]:
            pattern = "raise"  # Use RAISE for coordination tasks
        elif task_type in ["implementation", "debugging", "iterative"]:
            pattern = "react"  # Use ReAct for implementation tasks
        else:
            pattern = self.default_reasoning_pattern  # Default to CoT

        # All patterns are now async, so use reason_async
        return await self.reasoning_engine.reason_async(objective, pattern, context)

    def _extract_tools_from_reasoning(self, reasoning_path) -> List[str]:
        """Extract MCP tools mentioned in reasoning steps."""
        selected_tools = []

        for step in reasoning_path.steps:
            # Look for tool names in actions and observations
            if step.action:
                for tool in self.dynamic_capabilities:
                    if tool.lower() in step.action.lower():
                        if tool not in selected_tools:
                            selected_tools.append(tool)

            if step.observation:
                for tool in self.dynamic_capabilities:
                    if tool.lower() in step.observation.lower():
                        if tool not in selected_tools:
                            selected_tools.append(tool)

        return selected_tools

    async def _basic_mcp_reasoning(
        self, task: AgentTask, reasoning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Basic MCP-aware reasoning fallback."""
        # Step 1: Analyze task requirements
        task_analysis = {
            "task_type": task.get("type", "unknown"),
            "complexity": self._assess_task_complexity(task),
            "required_capabilities": self._identify_required_capabilities(task),
        }
        reasoning_result["reasoning_steps"].append(
            {"step": "task_analysis", "result": task_analysis}
        )

        # Step 2: Match capabilities to requirements
        capability_matches = []
        for capability in task_analysis["required_capabilities"]:
            matching_tools = self._find_matching_tools(capability)
            if matching_tools:
                capability_matches.append(
                    {"capability": capability, "matching_tools": matching_tools}
                )

        reasoning_result["reasoning_steps"].append(
            {"step": "capability_matching", "result": capability_matches}
        )

        # Step 3: Select optimal tool sequence
        selected_tools = self._select_optimal_tools(capability_matches, task_analysis)
        reasoning_result["selected_tools"] = selected_tools

        reasoning_result["reasoning_steps"].append(
            {"step": "tool_selection", "result": selected_tools}
        )

        # Adjust confidence based on tool availability
        if selected_tools:
            reasoning_result["confidence"] = min(0.95, 0.6 + len(selected_tools) * 0.1)
        else:
            reasoning_result["confidence"] = 0.3

        return reasoning_result

    def _assess_task_complexity(self, task: AgentTask) -> str:
        """Assess task complexity."""
        description = task.get("description", "")
        task_type = task.get("type", "")

        # Simple heuristics for complexity assessment
        if any(
            keyword in description.lower()
            for keyword in ["complex", "multiple", "integrate", "analyze"]
        ):
            return "high"
        elif any(
            keyword in description.lower() for keyword in ["simple", "basic", "single"]
        ):
            return "low"
        else:
            return "medium"

    def _identify_required_capabilities(self, task: AgentTask) -> List[str]:
        """Identify required capabilities from task."""
        description = task.get("description", "").lower()
        task_type = task.get("type", "").lower()

        capabilities = []

        # Map keywords to capabilities
        capability_keywords = {
            "file_operations": ["file", "read", "write", "directory", "path"],
            "code_analysis": ["code", "analyze", "review", "parse", "ast"],
            "git_operations": ["git", "commit", "branch", "repository", "clone"],
            "data_processing": ["data", "process", "transform", "filter", "query"],
            "api_calls": ["api", "request", "http", "rest", "endpoint"],
            "database": ["database", "sql", "query", "table", "record"],
        }

        for capability, keywords in capability_keywords.items():
            if any(
                keyword in description or keyword in task_type for keyword in keywords
            ):
                capabilities.append(capability)

        return capabilities

    def _find_matching_tools(self, capability: str) -> List[str]:
        """Find tools that match a capability."""
        matching_tools = []

        if not self.enhanced_tools:
            return matching_tools

        # Search for tools by capability keywords
        capability_keywords = {
            "file_operations": ["file", "filesystem", "directory"],
            "code_analysis": ["code", "ast", "parse", "analyze"],
            "git_operations": ["git", "repository", "commit"],
            "data_processing": ["data", "process", "transform"],
            "api_calls": ["http", "api", "request"],
            "database": ["database", "sql", "postgres", "sqlite"],
        }

        keywords = capability_keywords.get(capability, [capability])

        for keyword in keywords:
            tools = self.enhanced_tools.search_tools(keyword)
            matching_tools.extend([tool.name for tool in tools])

        return list(set(matching_tools))  # Remove duplicates

    def _select_optimal_tools(
        self, capability_matches: List[Dict], task_analysis: Dict
    ) -> List[str]:
        """Select optimal tools based on capability matches and task analysis."""
        selected_tools = []

        # Simple selection strategy: pick the most used tool for each capability
        for match in capability_matches:
            tools = match["matching_tools"]
            if tools:
                # For now, just pick the first tool
                # In a more sophisticated implementation, this would consider
                # performance metrics, success rates, etc.
                selected_tools.append(tools[0])

        return selected_tools

    async def _execute_with_mcp(
        self, task: AgentTask, reasoning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute task using MCP tools and capabilities."""
        self._mcp_tools_used = []
        execution_result = {
            "task_type": task.get("type", "unknown"),
            "execution_approach": "mcp_enhanced",
            "tools_executed": [],
            "results": {},
            "success": True,
        }

        try:
            selected_tools = reasoning_result.get("selected_tools", [])

            if not selected_tools:
                # Fallback to traditional execution
                logger.info(
                    f"No MCP tools selected, using traditional execution for agent {self.agent_id}"
                )
                execution_result["execution_approach"] = "traditional"
                execution_result["results"][
                    "message"
                ] = "Task executed using traditional approach"
                return execution_result

            # Execute selected tools
            for tool_name in selected_tools:
                try:
                    if self.enhanced_tools:
                        # Get tool parameters from task
                        tool_params = self._extract_tool_parameters(task, tool_name)

                        # Execute tool
                        tool_result = await self.enhanced_tools.execute_tool(
                            tool_name, tool_params
                        )

                        execution_result["tools_executed"].append(
                            {
                                "tool": tool_name,
                                "parameters": tool_params,
                                "success": True,
                                "result": tool_result,
                            }
                        )

                        self._mcp_tools_used.append(tool_name)

                        # Store result for potential use by subsequent tools
                        execution_result["results"][tool_name] = tool_result

                    else:
                        logger.warning(
                            f"Enhanced tools not available for agent {self.agent_id}"
                        )

                except Exception as e:
                    logger.error(
                        f"Tool execution failed for {tool_name} in agent {self.agent_id}: {e}"
                    )
                    execution_result["tools_executed"].append(
                        {"tool": tool_name, "success": False, "error": str(e)}
                    )
                    execution_result["success"] = False

            # Combine results
            if execution_result["success"]:
                execution_result["final_result"] = self._combine_tool_results(
                    execution_result["results"]
                )

            return execution_result

        except Exception as e:
            logger.error(f"MCP execution failed for agent {self.agent_id}: {e}")
            execution_result["success"] = False
            execution_result["error"] = str(e)
            return execution_result

    def _extract_tool_parameters(
        self, task: AgentTask, tool_name: str
    ) -> Dict[str, Any]:
        """Extract parameters for a tool from the task."""
        # Simple parameter extraction
        # In a more sophisticated implementation, this would use NLP or predefined mappings

        base_params = {}

        # Add common parameters from task
        if "file_path" in task:
            base_params["file_path"] = task["file_path"]
        if "directory" in task:
            base_params["directory"] = task["directory"]
        if "query" in task:
            base_params["query"] = task["query"]
        if "content" in task:
            base_params["content"] = task["content"]

        # Tool-specific parameter mapping
        tool_param_mapping = {
            "file-read": {"path": task.get("file_path", ".")},
            "git-status": {"repository": task.get("repository", ".")},
            "code-analyze": {"file_path": task.get("file_path", "")},
        }

        return tool_param_mapping.get(tool_name, base_params)

    def _combine_tool_results(self, results: Dict[str, Any]) -> Any:
        """Combine results from multiple tool executions."""
        if not results:
            return None

        if len(results) == 1:
            return list(results.values())[0]

        # Simple combination strategy
        combined = {
            "combined_results": results,
            "summary": f"Executed {len(results)} tools successfully",
        }

        return combined

    async def _update_capability_usage(
        self, task: AgentTask, result: Dict[str, Any]
    ) -> None:
        """Update capability usage statistics."""
        try:
            usage_record = {
                "task_id": task.task_id,
                "task_type": task.get("type", "unknown"),
                "tools_used": getattr(self, "_mcp_tools_used", []),
                "success": result.get("success", False),
                "timestamp": datetime.now().isoformat(),
            }

            self.capability_usage_history.append(usage_record)

            # Limit history size
            if len(self.capability_usage_history) > 100:
                self.capability_usage_history = self.capability_usage_history[-100:]

        except Exception as e:
            logger.warning(
                f"Failed to update capability usage for agent {self.agent_id}: {e}"
            )

    async def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP integration status."""
        status = {
            "mcp_enabled": self.mcp_enabled,
            "mcp_initialized": self.mcp_initialized,
            "connected_servers": self.connected_servers.copy(),
            "available_capabilities": len(self.dynamic_capabilities),
            "capability_cache": self.mcp_capabilities_cache,
            "usage_history_count": len(self.capability_usage_history),
        }

        if self.mcp_client:
            status["mcp_client_status"] = self.mcp_client.get_server_status()

        return status

    async def refresh_mcp_capabilities(self) -> bool:
        """Refresh MCP capabilities from connected servers."""
        if not self.mcp_enabled or not self.mcp_initialized:
            return False

        try:
            await self._cache_mcp_capabilities()

            if self.enhanced_tools:
                await self.enhanced_tools.refresh_mcp_tools()

            logger.info(f"Refreshed MCP capabilities for agent {self.agent_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to refresh MCP capabilities for agent {self.agent_id}: {e}"
            )
            return False

    async def connect_mcp_server(self, server_config: MCPServerConfig) -> bool:
        """Connect to an additional MCP server."""
        if not self.mcp_enabled or not self.mcp_registry:
            return False

        try:
            success = await self.mcp_registry.register_server(server_config)
            if success:
                self.connected_servers[server_config.name] = True
                await self.refresh_mcp_capabilities()
            else:
                self.connected_servers[server_config.name] = False

            return success

        except Exception as e:
            logger.error(
                f"Failed to connect MCP server {server_config.name} for agent {self.agent_id}: {e}"
            )
            return False

    async def disconnect_mcp_server(self, server_name: str) -> bool:
        """Disconnect from an MCP server."""
        if not self.mcp_enabled or not self.mcp_client:
            return False

        try:
            success = await self.mcp_client.disconnect_server(server_name)
            if success:
                self.connected_servers[server_name] = False
                await self.refresh_mcp_capabilities()

            return success

        except Exception as e:
            logger.error(
                f"Failed to disconnect MCP server {server_name} for agent {self.agent_id}: {e}"
            )
            return False

    async def stop(self) -> None:
        """Stop the agent and cleanup MCP resources."""
        logger.info(f"Stopping MCP-enhanced agent: {self.agent_id}")

        try:
            # Close MCP components
            if self.enhanced_tools:
                await self.enhanced_tools.close()

            if self.mcp_client:
                await self.mcp_client.close()

            # Call parent stop method
            await super().stop()

        except Exception as e:
            logger.error(f"Error closing agent {self.agent_id}: {e}")

        logger.info(f"Agent {self.agent_id} stopped")

    async def close(self) -> None:
        """Close the agent and cleanup resources (alias for stop)."""
        await self.stop()


# Backward compatibility helper
def create_mcp_enhanced_agent(
    agent_class: Type[Agent], **mcp_kwargs
) -> Type[MCPEnhancedAgent]:
    """
    Create an MCP-enhanced version of an existing agent class.

    Args:
        agent_class: Original agent class
        **mcp_kwargs: MCP configuration arguments

    Returns:
        MCP-enhanced agent class
    """

    class EnhancedAgentClass(MCPEnhancedAgent, agent_class):
        def __init__(self, *args, **kwargs):
            # Merge MCP kwargs with instance kwargs
            merged_kwargs = {**mcp_kwargs, **kwargs}
            super().__init__(*args, **merged_kwargs)

        async def execute(self, task: AgentTask) -> AgentResult:
            # Use MCP-enhanced execution if available, fallback to original
            if self.mcp_enabled and self.mcp_initialized:
                return await MCPEnhancedAgent.execute(self, task)
            else:
                return await agent_class.execute(self, task)

    return EnhancedAgentClass
