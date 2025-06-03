"""Unit tests for core architecture components."""

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from agentic_workflow.core.config import Config, create_config
from agentic_workflow.core.engine import ComponentRegistry, WorkflowEngine
from agentic_workflow.core.interfaces import (
    Component,
    Service,
    ServiceResponse,
    WorkflowDefinition,
    WorkflowStep,
)


class MockComponent(Component):
    """Mock component for testing."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config or {})
        self.initialized = False
        self.started = False
        self.stopped = False
        self.requests_processed = 0

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

    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a mock request."""
        self.requests_processed += 1
        return ServiceResponse(
            success=True, data={"action": request.get("action"), "processed": True}
        )


class MockService(Service):
    """Mock service for testing."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config or {})
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


class MockEventHandler:
    """Mock event handler for testing."""

    pass


@pytest.mark.unit
class TestConfig:
    """Test configuration management."""

    def test_default_config_creation(self) -> None:
        """Test creating config with defaults."""
        config = Config()

        assert config.app_name == "Agentic Workflow"
        assert config.environment == "development"
        assert config.debug is False
        assert config.database.neo4j_uri == "bolt://localhost:7687"

    def test_config_validation(self) -> None:
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
    def test_config_from_environment(self) -> None:
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

    def test_component_registration(self) -> None:
        """Test registering components."""
        registry = ComponentRegistry()
        component = MockComponent("test-component")

        registry.register(component)

        assert registry.get("test-component") == component
        assert "test-component" in registry.get_all()

    def test_duplicate_registration_error(self) -> None:
        """Test error on duplicate component registration."""
        registry = ComponentRegistry()
        component1 = MockComponent("test-component")
        component2 = MockComponent("test-component")

        registry.register(component1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(component2)

    def test_dependency_ordering(self) -> None:
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

    def test_circular_dependency_detection(self) -> None:
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

    def test_register_duplicate_component(self) -> None:
        """Test registering duplicate component raises error."""
        registry = ComponentRegistry()
        component = MockComponent("test")
        registry.register(component)

        with pytest.raises(ValueError, match="Component 'test' already registered"):
            registry.register(component)

    def test_get_nonexistent_component(self) -> None:
        """Test getting nonexistent component returns None."""
        registry = ComponentRegistry()
        assert registry.get("nonexistent") is None

    def test_circular_dependency_detection_three_components(self) -> None:
        """Test circular dependency detection with three components."""
        registry = ComponentRegistry()
        comp1 = MockComponent("comp1")
        comp2 = MockComponent("comp2")
        comp3 = MockComponent("comp3")

        comp1.add_dependency("comp2")
        comp2.add_dependency("comp3")
        comp3.add_dependency("comp1")

        registry.register(comp1)
        registry.register(comp2)
        registry.register(comp3)

        with pytest.raises(ValueError, match="Circular dependency detected"):
            registry.get_startup_order()


@pytest.mark.unit
class TestWorkflowEngine:
    """Test workflow engine functionality."""

    @pytest.fixture
    def engine(self) -> WorkflowEngine:
        """Create a workflow engine for testing."""
        return WorkflowEngine()

    @pytest.fixture
    def mock_workflow(self) -> WorkflowDefinition:
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
                    action="process",
                ),
            ],
        )

    def test_component_registration(self, engine: WorkflowEngine) -> None:
        """Test registering components with the engine."""
        component = MockComponent("test-component")
        engine.register_component(component)
        assert engine.components.get("test-component") == component

    @pytest.mark.asyncio
    async def test_engine_lifecycle(self, engine: WorkflowEngine) -> None:
        """Test engine lifecycle methods."""
        component = MockComponent("test-component")
        engine.register_component(component)

        await engine.start()
        assert component.started

        await engine.stop()
        assert component.stopped

    @pytest.mark.asyncio
    async def test_workflow_execution(
        self, engine: WorkflowEngine, mock_workflow: WorkflowDefinition
    ) -> None:
        """Test executing a workflow."""
        service = MockService("test-service")
        engine.register_component(service)

        await engine.start()

        result = await engine.execute_workflow(mock_workflow)
        assert result.status == "completed"
        assert service.requests_processed == 2

        await engine.stop()

    @pytest.mark.asyncio
    async def test_workflow_step_dependencies(self, engine: WorkflowEngine) -> None:
        """Test workflow step dependencies."""
        service = MockService("test-service")
        engine.register_component(service)

        workflow = WorkflowDefinition(
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
                    action="process",
                    dependencies=["step-1"],
                ),
            ],
        )

        await engine.start()

        result = await engine.execute_workflow(workflow)
        assert result.status == "completed"
        assert service.requests_processed == 2

        await engine.stop()

    @pytest.mark.asyncio
    async def test_health_check(self, engine: WorkflowEngine) -> None:
        """Test health check functionality."""
        component = MockComponent("test-component")
        engine.register_component(component)

        await engine.start()

        health = await engine.health_check()
        assert health.success
        assert health.data["engine_status"] == "healthy"
        assert "test-component" in health.data["components"]
        assert health.data["components"]["test-component"]["healthy"]

        await engine.stop()

    @pytest.fixture
    def mock_component(self) -> MockComponent:
        """Create a mock component for testing."""
        return MockComponent("test-component")

    @pytest.mark.asyncio
    async def test_register_event_handler(
        self, engine: WorkflowEngine, mock_component: MockComponent
    ) -> None:
        """Test registering event handlers."""
        engine.register_component(mock_component)
        handler = MockEventHandler()
        engine.register_event_handler(handler)
        assert handler in engine.event_handlers

    @pytest.mark.asyncio
    async def test_health_check_with_unhealthy_component(
        self, engine: WorkflowEngine, mock_component: MockComponent
    ) -> None:
        """Test health check with an unhealthy component."""
        engine.register_component(mock_component)
        await engine.start()

        # Simulate unhealthy component
        async def unhealthy_check() -> ServiceResponse:
            return ServiceResponse(success=False, data={"status": "unhealthy"})

        mock_component.health_check = unhealthy_check

        health = await engine.health_check()
        assert not health.success
        assert health.data["components"]["test-component"]["healthy"] is False

        await engine.stop()

    @pytest.mark.asyncio
    async def test_execute_workflow_with_timeout(
        self, engine: WorkflowEngine, mock_component: MockComponent
    ) -> None:
        """Test workflow execution with timeout."""
        engine.register_component(mock_component)
        await engine.start()

        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=[
                WorkflowStep(
                    id="step-1",
                    name="First Step",
                    component="test-component",
                    action="process",
                    timeout=1,
                ),
            ],
        )

        # Mock a slow request
        async def slow_request(*args: Any, **kwargs: Any) -> ServiceResponse:
            await asyncio.sleep(2)
            return ServiceResponse(success=True, data={"status": "done"})

        mock_component.process_request = slow_request

        result = await engine.execute_workflow(workflow)
        assert result.status == "failed"
        assert "step timeout" in result.error.lower()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_execute_workflow_with_missing_dependency(
        self, engine: WorkflowEngine, mock_component: MockComponent
    ) -> None:
        """Test workflow execution with missing dependency."""
        engine.register_component(mock_component)
        await engine.start()

        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=[
                WorkflowStep(
                    id="step-1",
                    name="First Step",
                    component="test-component",
                    action="process",
                ),
                WorkflowStep(
                    id="step-2",
                    name="Second Step",
                    component="test-component",
                    action="process",
                    dependencies=["nonexistent-step"],
                ),
            ],
        )

        result = await engine.execute_workflow(workflow)
        assert result.status == "failed"
        assert "step dependency not met" in result.error.lower()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_execute_workflow_with_nonexistent_component(
        self, engine: WorkflowEngine
    ) -> None:
        """Test workflow execution with nonexistent component."""
        await engine.start()

        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=[
                WorkflowStep(
                    id="step-1",
                    name="First Step",
                    component="nonexistent-component",
                    action="process",
                ),
            ],
        )

        result = await engine.execute_workflow(workflow)
        assert result.status == "failed"
        assert "component" in result.error.lower()

        await engine.stop()

    @pytest.mark.asyncio
    async def test_lifecycle_context_manager(self, engine: WorkflowEngine) -> None:
        """Test engine lifecycle using context manager."""
        component = MockComponent("test-component")
        engine.register_component(component)

        async with engine.lifecycle():
            assert component.started
            assert not component.stopped

        assert component.stopped


@pytest.mark.unit
class TestServiceResponse:
    """Test service response functionality."""

    def test_successful_response(self) -> None:
        """Test creating a successful response."""
        response = ServiceResponse(success=True, data={"message": "success"})
        assert response.success
        assert response.data["message"] == "success"
        assert response.error is None

    def test_error_response(self) -> None:
        """Test creating an error response."""
        response = ServiceResponse(
            success=False, error="Something went wrong", data={"error": "details"}
        )
        assert not response.success
        assert response.error == "Something went wrong"
        assert response.data["error"] == "details"


@pytest.mark.unit
class TestWorkflowDefinition:
    """Test workflow definition functionality."""

    def test_workflow_step_creation(self) -> None:
        """Test creating workflow steps."""
        step = WorkflowStep(
            id="test-step",
            name="Test Step",
            component="test-component",
            action="process",
            dependencies=["step-1", "step-2"],
        )

        assert step.id == "test-step"
        assert step.name == "Test Step"
        assert step.component == "test-component"
        assert step.action == "process"
        assert step.dependencies == ["step-1", "step-2"]

    def test_workflow_definition_creation(self) -> None:
        """Test creating workflow definitions."""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=[
                WorkflowStep(
                    id="step-1",
                    name="First Step",
                    component="test-component",
                    action="process",
                ),
                WorkflowStep(
                    id="step-2",
                    name="Second Step",
                    component="test-component",
                    action="process",
                    dependencies=["step-1"],
                ),
            ],
        )

        assert workflow.id == "test-workflow"
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert len(workflow.steps) == 2
        assert workflow.steps[0].id == "step-1"
        assert workflow.steps[1].id == "step-2"
        assert workflow.steps[1].dependencies == ["step-1"]
