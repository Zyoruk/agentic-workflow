"""Task graph domain models."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of tasks in the system."""

    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    DATA_PROCESSING = "data_processing"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """Possible states of a task."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskNode(BaseModel):
    """Represents a task in the task graph."""

    id: UUID = Field(default_factory=uuid4)
    type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    name: str
    description: Optional[str] = None
    requirements: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration: Optional[float] = None  # in seconds
    actual_duration: Optional[float] = None  # in seconds
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None

    def __eq__(self, other: object) -> bool:
        """Compare tasks based on their ID."""
        if not isinstance(other, TaskNode):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Generate hash based on task ID."""
        return hash(self.id)


class TaskRelationship(BaseModel):
    """Represents a relationship between tasks."""

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __eq__(self, other: object) -> bool:
        """Compare relationships based on their ID."""
        if not isinstance(other, TaskRelationship):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Generate hash based on relationship ID."""
        return hash(self.id)


class TaskGraph(BaseModel):
    """Represents a graph of tasks and their relationships."""

    nodes: Dict[UUID, TaskNode] = Field(default_factory=dict)
    relationships: Dict[UUID, TaskRelationship] = Field(default_factory=dict)
    execution_order: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def add_node(self, node: TaskNode) -> None:
        """Add a task node to the graph."""
        self.nodes[node.id] = node
        self.updated_at = datetime.now(UTC)

    def add_relationship(self, relationship: TaskRelationship) -> None:
        """Add a relationship between tasks."""
        if relationship.source_id not in self.nodes:
            raise ValueError(f"Source node {relationship.source_id} not found")
        if relationship.target_id not in self.nodes:
            raise ValueError(f"Target node {relationship.target_id} not found")
        self.relationships[relationship.id] = relationship
        self.updated_at = datetime.now(UTC)

    def get_node(self, node_id: UUID) -> Optional[TaskNode]:
        """Get a task node by ID."""
        return self.nodes.get(node_id)

    def get_relationship(self, relationship_id: UUID) -> Optional[TaskRelationship]:
        """Get a relationship by ID."""
        return self.relationships.get(relationship_id)

    def get_dependencies(self, node_id: UUID) -> List[TaskNode]:
        """Get all dependencies for a task."""
        dependencies = []
        for rel in self.relationships.values():
            if rel.target_id == node_id:
                source_node = self.get_node(rel.source_id)
                if source_node:
                    dependencies.append(source_node)
        return dependencies

    def get_dependents(self, node_id: UUID) -> List[TaskNode]:
        """Get all tasks that depend on this task."""
        dependents = []
        for rel in self.relationships.values():
            if rel.source_id == node_id:
                target_node = self.get_node(rel.target_id)
                if target_node:
                    dependents.append(target_node)
        return dependents

    def validate_structure(self) -> bool:
        """Validate the task graph structure."""
        # Check for cycles
        visited = set()
        path = set()

        def has_cycle(node_id: UUID) -> bool:
            if node_id in path:
                return True
            if node_id in visited:
                return False

            visited.add(node_id)
            path.add(node_id)

            for dep in self.get_dependencies(node_id):
                if has_cycle(dep.id):
                    return True

            path.remove(node_id)
            return False

        for node_id in self.nodes:
            if has_cycle(node_id):
                return False

        return True

    def calculate_execution_order(self) -> List[UUID]:
        """Calculate the topological order of tasks."""
        if not self.validate_structure():
            raise ValueError("Task graph contains cycles")

        visited = set()
        order = []

        def visit(node_id: UUID) -> None:
            if node_id in visited:
                return

            visited.add(node_id)
            for dep in self.get_dependencies(node_id):
                visit(dep.id)
            order.append(node_id)

        for node_id in self.nodes:
            visit(node_id)

        self.execution_order = order
        return order
