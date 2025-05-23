"""Unit tests for core architecture components."""

from typing import Any, Dict
from unittest.mock import patch

import pytest

from agentic_workflow.core.config import Config, create_config
from agentic_workflow.core.engine import ComponentRegistry, WorkflowEngine
from agentic_workflow.core.interfaces import (
    Component,
    ComponentStatus,
    Service,
    ServiceResponse,
    WorkflowDefinition,
    WorkflowStep,
)


class MockComponent(Component):
    """Mock component for testing."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.initialized = False
        self.started = False
        self.stopped = False

    async def initialize(self) -> None:
        """Initialize the mock component."""
        self.initialized = True

    async def start(self) -> None:
        """Start the mock component."""
        self.started = True

    async def stop(self) -> None:
        """Stop the mock component."""
        self.stopped = True

    async def health_check(self) -> ServiceResponse:
        """Check mock component health."""
        return ServiceResponse(success=True, data={"status": "healthy"})


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.initialized = False
        self.started = False
        self.stopped = False
        self.requests_processed = 0

    async def initialize(self) -> None:
        """Initialize the mock service."""
        self.initialized = True

    async def start(self) -> None:
        """Start the mock service."""
        self.started = True

    async def stop(self) -> None:
        """Stop the mock service."""
        self.stopped = True

    async def health_check(self) -> ServiceResponse:
        """Check mock service health."""
        return ServiceResponse(success=True, data={"status": "healthy"})

    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a mock request."""
        self.requests_processed += 1
        return ServiceResponse(
            success=True, data={"action": request.get("action"), "processed": True}
        )


@pytest.mark.unit
class TestConfig:
    """Test configuration management."""

    def test_default_config_creation(self):
        """Test creating config with defaults."""
        config = Config()

        assert config.app_name == "Agentic Workflow"
        assert config.environment == "development"
        assert config.debug is False
        assert config.database.neo4j_uri == "bolt://localhost:7687"

    def test_config_validation(self):
        """Test config validation."""
        # Valid config
        config = Config(worker_threads=8, max_concurrent_workflows=20)
        assert config.worker_threads == 8
        assert config.max_concurrent_workflows == 20

        # Invalid config - should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            Config(worker_threads=-1)  # Must be > 0

    @patch.dict(
        "os.environ",
        {
            "AGENTIC_DEBUG": "true",
            "AGENTIC_DATABASE__NEO4J_URI": "bolt://test:7687",
        },
    )
    def test_config_from_environment(self):
        """Test loading config from environment variables."""
        # Clear any existing config
        import agentic_workflow.core.config as config_module

        config_module._config = None

        config = create_config()
        assert config.debug is True
        assert config.database.neo4j_uri == "bolt://test:7687"


@pytest.mark.unit
class TestComponentRegistry:
    """Test component registry functionality."""

    def test_component_registration(self):
        """Test registering components."""
        registry = ComponentRegistry()
        component = MockComponent("test-component")

        registry.register(component)

        assert registry.get("test-component") == component
        assert "test-component" in registry.get_all()

    def test_duplicate_registration_error(self):
        """Test error on duplicate component registration."""
        registry = ComponentRegistry()
        component1 = MockComponent("test-component")
        component2 = MockComponent("test-component")

        registry.register(component1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(component2)

    def test_dependency_ordering(self):
        """Test component startup ordering based on dependencies."""
        registry = ComponentRegistry()

        # Create components with dependencies
        comp_a = MockComponent("component-a")
        comp_b = MockComponent("component-b")
        comp_c = MockComponent("component-c")

        # B depends on A, C depends on B
        comp_b.add_dependency("component-a")
        comp_c.add_dependency("component-b")

        registry.register(comp_c)  # Register in random order
        registry.register(comp_a)
        registry.register(comp_b)

        startup_order = registry.get_startup_order()

        # A should come before B, B should come before C
        assert startup_order.index("component-a") < startup_order.index("component-b")
        assert startup_order.index("component-b") < startup_order.index("component-c")

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        registry = ComponentRegistry()

        comp_a = MockComponent("component-a")
        comp_b = MockComponent("component-b")

        # Create circular dependency
        comp_a.add_dependency("component-b")
        comp_b.add_dependency("component-a")

        registry.register(comp_a)
        registry.register(comp_b)

        with pytest.raises(ValueError, match="Circular dependency"):
            registry.get_startup_order()


@pytest.mark.unit
class TestWorkflowEngine:
    """Test workflow engine functionality."""

    @pytest.fixture
    def engine(self):
        """Create a workflow engine for testing."""
        return WorkflowEngine()

    @pytest.fixture
    def mock_workflow(self):
        """Create a mock workflow definition."""
        return WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=[
                WorkflowStep(
                    id="step-1",
                    name="First Step",
                    component="test-service",
                    action="process",
                ),
                WorkflowStep(
                    id="step-2",
                    name="Second Step",
                    component="test-service",
                    action="finalize",
                    dependencies=["step-1"],
                ),
            ],
        )

    def test_component_registration(self, engine):
        """Test registering components with engine."""
        component = MockComponent("test-component")

        engine.register_component(component)

        assert engine.components.get("test-component") == component

    @pytest.mark.asyncio
    async def test_engine_lifecycle(self, engine):
        """Test engine start and stop lifecycle."""
        component = MockComponent("test-component")
        engine.register_component(component)

        # Start engine
        await engine.start()

        assert component.initialized
        assert component.started
        assert component.status == ComponentStatus.RUNNING

        # Stop engine
        await engine.stop()

        assert component.stopped
        assert component.status == ComponentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_workflow_execution(self, engine, mock_workflow):
        """Test basic workflow execution."""
        service = MockService("test-service")
        engine.register_component(service)

        await engine.start()

        execution = await engine.execute_workflow(mock_workflow)

        assert execution.status == "completed"
        assert len(execution.completed_steps) == 2
        assert "step-1" in execution.completed_steps
        assert "step-2" in execution.completed_steps
        assert service.requests_processed == 2

        await engine.stop()

    @pytest.mark.asyncio
    async def test_workflow_step_dependencies(self, engine):
        """Test workflow step dependency handling."""
        service = MockService("test-service")
        engine.register_component(service)

        # Create workflow with dependencies
        workflow = WorkflowDefinition(
            id="dep-workflow",
            name="Dependency Workflow",
            description="Workflow with dependencies",
            steps=[
                WorkflowStep(
                    id="step-2",
                    name="Second Step",
                    component="test-service",
                    action="process",
                    dependencies=["step-1"],  # Depends on step-1 which doesn't exist
                )
            ],
        )

        await engine.start()

        execution = await engine.execute_workflow(workflow)

        # Should fail due to unmet dependency
        assert execution.status == "failed"
        assert "step-2" in execution.failed_steps

        await engine.stop()

    @pytest.mark.asyncio
    async def test_health_check(self, engine):
        """Test engine health check."""
        component = MockComponent("test-component")
        engine.register_component(component)

        await engine.start()

        health = await engine.health_check()

        assert health.success
        assert health.data["engine_status"] == "healthy"
        assert "test-component" in health.data["components"]
        assert health.data["components"]["test-component"]["healthy"]

        await engine.stop()


@pytest.mark.unit
class TestServiceResponse:
    """Test service response model."""

    def test_successful_response(self):
        """Test creating successful response."""
        response = ServiceResponse(
            success=True, data={"result": "test"}, metadata={"timestamp": "2024-01-01"}
        )

        assert response.success
        assert response.data["result"] == "test"
        assert response.error is None
        assert response.metadata["timestamp"] == "2024-01-01"

    def test_error_response(self):
        """Test creating error response."""
        response = ServiceResponse(success=False, error="Something went wrong")

        assert not response.success
        assert response.error == "Something went wrong"
        assert response.data is None


@pytest.mark.unit
class TestWorkflowDefinition:
    """Test workflow definition models."""

    def test_workflow_step_creation(self):
        """Test creating workflow step."""
        step = WorkflowStep(
            id="test-step",
            name="Test Step",
            component="test-component",
            action="test-action",
            parameters={"param1": "value1"},
            dependencies=["other-step"],
            timeout=30,
        )

        assert step.id == "test-step"
        assert step.name == "Test Step"
        assert step.component == "test-component"
        assert step.action == "test-action"
        assert step.parameters["param1"] == "value1"
        assert "other-step" in step.dependencies
        assert step.timeout == 30

    def test_workflow_definition_creation(self):
        """Test creating workflow definition."""
        steps = [
            WorkflowStep(
                id="step-1", name="First Step", component="comp-1", action="action-1"
            )
        ]

        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=steps,
            metadata={"created_by": "test"},
        )

        assert workflow.id == "test-workflow"
        assert workflow.name == "Test Workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].id == "step-1"
        assert workflow.metadata["created_by"] == "test"
