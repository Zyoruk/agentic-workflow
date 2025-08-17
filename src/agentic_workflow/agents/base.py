"""Base agent interface and implementation for the agentic workflow system."""

import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from agentic_workflow.core.exceptions import AgentError
from agentic_workflow.core.interfaces import Component, ComponentStatus, ServiceResponse
from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.guardrails.service import GuardrailsService
from agentic_workflow.memory.manager import MemoryManager


class AgentTask(dict):
    """Represents a task for agent execution."""

    def __init__(self, task_id: Optional[str] = None, **kwargs: Any) -> None:
        """Initialize agent task.

        Args:
            task_id: Unique task identifier
            **kwargs: Task parameters
        """
        super().__init__(**kwargs)
        self["task_id"] = task_id or str(uuid.uuid4())
        self["created_at"] = datetime.now(UTC).isoformat()

    @property
    def task_id(self) -> str:
        """Get task ID."""
        return str(self["task_id"])

    @property
    def task_type(self) -> str:
        """Get task type."""
        return str(self.get("type", "unknown"))


class AgentResult(ServiceResponse):
    """Standard agent execution result."""

    task_id: str
    agent_id: str
    execution_time: float
    steps_taken: List[Dict[str, Any]] = []


class Agent(Component, ABC):
    """Base agent interface for all agentic workflow agents.

    This abstract base class defines the core contract that all agents
    must implement, providing a consistent interface for task execution,
    planning, and lifecycle management.
    """

    def __init__(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None,
        memory_manager: Optional[MemoryManager] = None,
        guardrails_service: Optional[GuardrailsService] = None,
    ):
        """Initialize agent.

        Args:
            agent_id: Unique agent identifier
            config: Agent configuration
            memory_manager: Memory management service
            guardrails_service: Safety and validation service
        """
        super().__init__(name=agent_id, config=config)
        self.agent_id = agent_id
        self.memory_manager = memory_manager
        self.guardrails = guardrails_service
        self.logger = get_logger(f"agent.{agent_id}")
        self._execution_history: List[Dict[str, Any]] = []

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute agent task and return results.

        This is the core method that all agents must implement. It should
        handle the main business logic for the agent's specific capability.

        Args:
            task: Task to execute with parameters and context

        Returns:
            AgentResult containing execution status, outputs, and metadata

        Raises:
            AgentError: If task execution fails
        """
        pass

    @abstractmethod
    async def plan(
        self, objective: str, context: Optional[Dict[str, Any]] = None
    ) -> List[AgentTask]:
        """Create execution plan for objective.

        Break down a high-level objective into a sequence of executable tasks.
        This enables complex goal achievement through step-by-step execution.

        Args:
            objective: High-level goal or objective to achieve
            context: Additional context for planning

        Returns:
            List of AgentTask objects representing the execution plan

        Raises:
            AgentError: If planning fails
        """
        pass

    async def initialize(self) -> None:
        """Initialize the agent."""
        self.logger.info(f"Initializing agent: {self.agent_id}")
        try:
            await self._setup_dependencies()
            await self._load_agent_configuration()
            self.status = ComponentStatus.READY
            self.logger.info(f"Agent {self.agent_id} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            self.status = ComponentStatus.ERROR
            raise AgentError(f"Agent initialization failed: {e}")

    async def start(self) -> None:
        """Start the agent."""
        if self.status != ComponentStatus.READY:
            raise AgentError(f"Agent {self.agent_id} not ready for startup")

        self.logger.info(f"Starting agent: {self.agent_id}")
        self.status = ComponentStatus.RUNNING
        self.logger.info(f"Agent {self.agent_id} started successfully")

    async def stop(self) -> None:
        """Stop the agent."""
        self.logger.info(f"Stopping agent: {self.agent_id}")
        await self._cleanup_resources()
        self.status = ComponentStatus.STOPPED
        self.logger.info(f"Agent {self.agent_id} stopped successfully")

    async def health_check(self) -> ServiceResponse:
        """Check agent health."""
        try:
            # Basic health checks
            is_healthy = (
                self.status in [ComponentStatus.READY, ComponentStatus.RUNNING]
                and await self._perform_health_checks()
            )

            return ServiceResponse(
                success=is_healthy,
                data={
                    "agent_id": self.agent_id,
                    "status": self.status.value,
                    "execution_count": len(self._execution_history),
                    "dependencies": self.get_dependencies(),
                },
                metadata={"timestamp": datetime.now(UTC).isoformat()},
            )
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"Health check failed: {e}",
                metadata={"timestamp": datetime.now(UTC).isoformat()},
            )

    async def safe_execute(self, task: AgentTask) -> AgentResult:
        """Execute task with comprehensive safety checks and error handling.

        This method wraps the core execute method with guardrails,
        validation, monitoring, and error recovery.

        Args:
            task: Task to execute safely

        Returns:
            AgentResult with execution outcome

        Raises:
            AgentError: If execution fails after recovery attempts
        """
        start_time = datetime.now(UTC)
        self.logger.info(f"Starting safe execution of task {task.task_id}")

        try:
            # Pre-execution validation and safety checks
            if self.guardrails:
                # Note: Simplified guardrails calls - actual implementation may vary
                await self.guardrails.validate_input(task, {})
                # Note: Resource limits checking would be implemented here
                # when the guardrails service interface is finalized

            # Execute the task
            result = await self.execute(task)

            # Post-execution validation
            if self.guardrails:
                # Note: Using validate_input instead of validate_output for now
                await self.guardrails.validate_input(result.model_dump(), {})

            # Record successful execution
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            self._record_execution(task, result, execution_time, True)

            self.logger.info(
                f"Task {task.task_id} completed successfully in {execution_time:.2f}s"
            )
            return result

        except Exception as e:
            execution_time = (datetime.now(UTC) - start_time).total_seconds()
            self.logger.error(
                f"Task {task.task_id} failed after {execution_time:.2f}s: {e}"
            )

            # Handle error with guardrails
            if self.guardrails and hasattr(self.guardrails, "handle_error"):
                await self.guardrails.handle_error(e)

            # Record failed execution
            error_result = AgentResult(
                success=False,
                error=str(e),
                task_id=task.task_id,
                agent_id=self.agent_id,
                execution_time=execution_time,
            )
            self._record_execution(task, error_result, execution_time, False)

            raise AgentError(
                f"Agent {self.agent_id} failed to execute task {task.task_id}: {e}"
            )

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get agent execution history."""
        return self._execution_history.copy()

    def get_capabilities(self) -> List[str]:
        """Get list of agent capabilities.

        Subclasses should override this to specify their capabilities.

        Returns:
            List of capability names
        """
        return ["execute", "plan"]

    async def _setup_dependencies(self) -> None:
        """Setup agent dependencies."""
        # Initialize memory manager if not provided
        if not self.memory_manager:
            self.memory_manager = MemoryManager()
            await self.memory_manager.initialize()

        # Initialize guardrails if not provided
        if not self.guardrails:
            self.guardrails = GuardrailsService()
            await self.guardrails.initialize()

    async def _load_agent_configuration(self) -> None:
        """Load agent-specific configuration."""
        # Load configuration from memory or config files
        # Subclasses can override this for specific config loading
        pass

    async def _cleanup_resources(self) -> None:
        """Cleanup agent resources."""
        # Cleanup memory, connections, etc.
        # Subclasses can override for specific cleanup
        pass

    async def _perform_health_checks(self) -> bool:
        """Perform agent-specific health checks.

        Returns:
            True if healthy, False otherwise
        """
        return True

    def _record_execution(
        self,
        task: AgentTask,
        result: AgentResult,
        execution_time: float,
        success: bool,
    ) -> None:
        """Record execution in history."""
        self._execution_history.append(
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "execution_time": execution_time,
                "success": success,
                "result_data": result.data if hasattr(result, "data") else None,
                "error": result.error if hasattr(result, "error") else None,
            }
        )

        # Keep only last 100 executions to prevent memory bloat
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-100:]
    
    async def close(self) -> None:
        """Clean up agent resources."""
        self.logger.info(f"Closing agent: {self.agent_id}")
        self.status = ComponentStatus.STOPPED
        
        # Clean up memory manager if available
        if self.memory_manager:
            try:
                await self.memory_manager.close()
            except Exception as e:
                self.logger.warning(f"Error closing memory manager: {e}")
        
        # Clean up guardrails if available
        if self.guardrails:
            try:
                await self.guardrails.close()
            except Exception as e:
                self.logger.warning(f"Error closing guardrails: {e}")
