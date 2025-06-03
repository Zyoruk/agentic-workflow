"""Core interfaces and abstract base classes for the agentic workflow system."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ComponentStatus(Enum):
    """Component status enumeration."""

    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class ServiceResponse(BaseModel):
    """Standard service response format."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class Component(ABC):
    """Abstract base class for all system components."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize component.

        Args:
        name: Component name
        config: Component configuration
        """
        self.name = name
        self.config = config or {}
        self.status = ComponentStatus.INITIALIZING
        self._dependencies: List[str] = []

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the component."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the component."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the component."""
        pass

    @abstractmethod
    async def health_check(self) -> ServiceResponse:
        """Check component health."""
        pass

    def add_dependency(self, component_name: str) -> None:
        """Add a dependency on another component.

        Args:
        component_name: Name of the dependent component
        """
        if component_name not in self._dependencies:
            self._dependencies.append(component_name)

    def get_dependencies(self) -> List[str]:
        """Get list of component dependencies."""
        return self._dependencies.copy()


class Service(Component):
    """Abstract base class for services that handle requests."""

    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a service request.

        Args:
            request: Request data

        Returns:
            Service response
        """
        pass


class EventHandler(ABC):
    """Abstract base class for event handlers."""

    @abstractmethod
    async def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle an event.

        Args:
            event_type: Type of event
            event_data: Event data
        """
        pass


class WorkflowStep(BaseModel):
    """Represents a single step in a workflow."""

    id: str
    name: str
    component: str
    action: str
    parameters: Dict[str, Any] = {}
    dependencies: List[str] = []
    timeout: Optional[int] = None


class WorkflowDefinition(BaseModel):
    """Defines a complete workflow."""

    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    metadata: Dict[str, Any] = {}


class WorkflowExecution(BaseModel):
    """Tracks workflow execution state."""

    id: str
    workflow_id: str
    status: str
    current_step: Optional[str] = None
    completed_steps: List[str] = []
    failed_steps: List[str] = []
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
