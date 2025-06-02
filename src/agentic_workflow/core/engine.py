"""Core workflow engine for the agentic workflow system."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set

from .config import Config, get_config
from .interfaces import (
    Component,
    ComponentStatus,
    EventHandler,
    ServiceResponse,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStep,
)
from .logging_config import get_logger, log_error, log_performance

logger = get_logger(__name__)


class ComponentRegistry:
    """Registry for managing system components."""

    def __init__(self) -> None:
        """Initialize component registry."""
        self._components: Dict[str, Component] = {}
        self._dependencies: Dict[str, Set[str]] = {}

    def register(self, component: Component) -> None:
        """Register a component.

        Args:
            component: Component to register

        Raises:
            ValueError: If component name already exists
        """
        if component.name in self._components:
            raise ValueError(f"Component '{component.name}' already registered")

        self._components[component.name] = component
        self._dependencies[component.name] = set(component.get_dependencies())

        logger.info(f"Registered component: {component.name}")

    def get(self, name: str) -> Optional[Component]:
        """Get component by name.

        Args:
            name: Component name

        Returns:
            Component instance or None if not found
        """
        return self._components.get(name)

    def get_all(self) -> Dict[str, Component]:
        """Get all registered components."""
        return self._components.copy()

    def get_startup_order(self) -> List[str]:
        """Get component startup order based on dependencies.

        Returns:
            List of component names in startup order

        Raises:
            ValueError: If circular dependencies detected
        """
        return self._topological_sort()

    def _topological_sort(self) -> List[str]:
        """Perform topological sort of components based on dependencies."""
        visited = set()
        temp_visited = set()
        result = []

        def visit(component_name: str) -> None:
            if component_name in temp_visited:
                raise ValueError(
                    f"Circular dependency detected involving: {component_name}"
                )

            if component_name not in visited:
                temp_visited.add(component_name)

                for dependency in self._dependencies.get(component_name, set()):
                    if dependency in self._components:
                        visit(dependency)

                temp_visited.remove(component_name)
                visited.add(component_name)
                result.append(component_name)

        for component_name in self._components:
            if component_name not in visited:
                visit(component_name)

        return result


class WorkflowEngine:
    """Main workflow engine that orchestrates system components."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize workflow engine.

        Args:
            config: Optional configuration override
        """
        self.config = config or get_config()
        self.components = ComponentRegistry()
        self.event_handlers: List[EventHandler] = []
        self.running_workflows: Dict[str, WorkflowExecution] = {}
        self._shutdown_event = asyncio.Event()

        logger.info("Workflow engine initialized")

    def register_component(self, component: Component) -> None:
        """Register a system component.

        Args:
            component: Component to register
        """
        self.components.register(component)

    def register_event_handler(self, handler: EventHandler) -> None:
        """Register an event handler.

        Args:
            handler: Event handler to register
        """
        self.event_handlers.append(handler)
        logger.info(f"Registered event handler: {handler.__class__.__name__}")

    async def start(self) -> None:
        """Start the workflow engine and all components."""
        logger.info("Starting workflow engine...")

        try:
            # Get startup order based on dependencies
            startup_order = self.components.get_startup_order()
            logger.info(f"Component startup order: {startup_order}")

            # Initialize and start components in order
            for component_name in startup_order:
                component = self.components.get(component_name)
                if component:
                    await self._start_component(component)

            logger.info("Workflow engine started successfully")

        except Exception as e:
            log_error(e, {"operation": "engine_start"})
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the workflow engine and all components."""
        logger.info("Stopping workflow engine...")

        # Signal shutdown
        self._shutdown_event.set()

        # Stop all components in reverse order
        startup_order = self.components.get_startup_order()
        for component_name in reversed(startup_order):
            component = self.components.get(component_name)
            if component:
                await self._stop_component(component)

        logger.info("Workflow engine stopped")

    async def _start_component(self, component: Component) -> None:
        """Start a single component.

        Args:
            component: Component to start
        """
        try:
            logger.info(f"Starting component: {component.name}")
            component.status = ComponentStatus.INITIALIZING

            await component.initialize()
            await component.start()

            component.status = ComponentStatus.RUNNING
            logger.info(f"Component started: {component.name}")

        except Exception as e:
            component.status = ComponentStatus.ERROR
            log_error(e, {"component": component.name, "operation": "start"})
            raise

    async def _stop_component(self, component: Component) -> None:
        """Stop a single component.

        Args:
            component: Component to stop
        """
        try:
            logger.info(f"Stopping component: {component.name}")

            await component.stop()
            component.status = ComponentStatus.STOPPED

            logger.info(f"Component stopped: {component.name}")

        except Exception as e:
            log_error(e, {"component": component.name, "operation": "stop"})

    async def execute_workflow(self, workflow: WorkflowDefinition) -> WorkflowExecution:
        """Execute a workflow.

        Args:
            workflow: Workflow definition to execute

        Returns:
            Workflow execution result
        """
        execution = WorkflowExecution(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            status="running",
            current_step=None,
            start_time=datetime.now(UTC).isoformat(),
            end_time=None,
            result=None,
            error=None,
        )

        self.running_workflows[execution.id] = execution

        logger.info_with_data(  # type: ignore[attr-defined]
            f"Starting workflow execution: {workflow.name}",
            workflow_id=workflow.id,
            execution_id=execution.id,
        )

        try:
            start_time_perf = asyncio.get_event_loop().time()

            # Execute workflow steps
            for step in workflow.steps:
                await self._execute_step(step, execution)

            # Mark as completed
            execution.status = "completed"
            execution.end_time = datetime.now(UTC).isoformat()

            duration = asyncio.get_event_loop().time() - start_time_perf
            log_performance(
                "workflow_execution",
                duration,
                workflow_id=workflow.id,
                execution_id=execution.id,
                steps_count=len(workflow.steps),
            )

            logger.info_with_data(  # type: ignore[attr-defined]
                f"Workflow execution completed: {workflow.name}",
                workflow_id=workflow.id,
                execution_id=execution.id,
                duration_seconds=duration,
            )

        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
            execution.end_time = datetime.now(UTC).isoformat()

            log_error(
                e,
                {
                    "workflow_id": workflow.id,
                    "execution_id": execution.id,
                    "operation": "workflow_execution",
                },
            )

        finally:
            # Remove from running workflows
            self.running_workflows.pop(execution.id, None)

        return execution

    async def _execute_step(
        self, step: WorkflowStep, execution: WorkflowExecution
    ) -> None:
        """Execute a single workflow step.

        Args:
            step: Workflow step to execute
            execution: Current workflow execution

        Raises:
            RuntimeError: If component not found or step fails
        """
        logger.info_with_data(  # type: ignore[attr-defined]
            f"Executing step: {step.name}",
            step_id=step.id,
            component=step.component,
            action=step.action,
        )

        # Check dependencies
        for dep_step_id in step.dependencies:
            if dep_step_id not in execution.completed_steps:
                execution.failed_steps.append(step.id)
                execution.error = f"Step dependency not met: {dep_step_id}"
                raise RuntimeError(f"Step dependency not met: {dep_step_id}")

        # Get component
        component = self.components.get(step.component)
        if not component:
            raise RuntimeError(f"Component not found: {step.component}")

        # Check component health
        health = await component.health_check()
        if not health.success:
            raise RuntimeError(f"Component unhealthy: {step.component}")

        try:
            # Execute step with timeout
            timeout = step.timeout or self.config.default_timeout

            request = {
                "action": step.action,
                "parameters": step.parameters,
                "step_id": step.id,
                "execution_id": execution.id,
            }

            # Execute with timeout
            if hasattr(component, "process_request"):
                response = await asyncio.wait_for(
                    component.process_request(request), timeout=timeout
                )
            else:
                raise RuntimeError(
                    f"Component does not support requests: {step.component}"
                )

            if not response.success:
                raise RuntimeError(f"Step failed: {response.error}")

            # Mark step as completed
            execution.completed_steps.append(step.id)
            execution.current_step = step.id

            # Emit event
            await self._emit_event(
                "step_completed",
                {
                    "step_id": step.id,
                    "execution_id": execution.id,
                    "response": response.model_dump(),
                },
            )

        except asyncio.TimeoutError:
            execution.failed_steps.append(step.id)
            execution.error = f"Step timeout: {step.name}"
            raise RuntimeError(f"Step timeout: {step.name}")

    async def _emit_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Emit an event to all registered handlers.

        Args:
            event_type: Type of event
            event_data: Event data
        """
        for handler in self.event_handlers:
            try:
                await handler.handle_event(event_type, event_data)
            except Exception as e:
                log_error(
                    e,
                    {"event_type": event_type, "handler": handler.__class__.__name__},
                )

    async def health_check(self) -> ServiceResponse:
        """Check health of the workflow engine and all components.

        Returns:
            Health check response
        """
        try:
            components_health = {}
            overall_healthy = True

            for name, component in self.components.get_all().items():
                health = await component.health_check()
                components_health[name] = {
                    "healthy": health.success,
                    "status": component.status.value,
                    "error": health.error,
                }

                if not health.success:
                    overall_healthy = False

            return ServiceResponse(
                success=overall_healthy,
                data={
                    "engine_status": "healthy" if overall_healthy else "unhealthy",
                    "components": components_health,
                    "running_workflows": len(self.running_workflows),
                },
            )

        except Exception as e:
            return ServiceResponse(success=False, error=str(e))

    @asynccontextmanager
    async def lifecycle(self) -> Any:
        """Async context manager for engine lifecycle.

        Usage:
            async with engine.lifecycle():
                # Engine is running
                pass
            # Engine is stopped
        """
        await self.start()
        try:
            yield self
        finally:
            await self.stop()
