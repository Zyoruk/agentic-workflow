"""Task graph repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .task_models import TaskGraph, TaskNode, TaskRelationship


class TaskGraphRepository(ABC):
    """Repository interface for task graph operations."""

    @abstractmethod
    async def create_task_graph(self, graph: TaskGraph) -> TaskGraph:
        """Create a new task graph.

        Args:
            graph: The task graph to create

        Returns:
            The created task graph
        """
        pass

    @abstractmethod
    async def get_task_graph(self, graph_id: UUID) -> Optional[TaskGraph]:
        """Get a task graph by ID.

        Args:
            graph_id: The ID of the task graph to retrieve

        Returns:
            The task graph if found, None otherwise
        """
        pass

    @abstractmethod
    async def update_task_graph(self, graph: TaskGraph) -> TaskGraph:
        """Update an existing task graph.

        Args:
            graph: The task graph to update

        Returns:
            The updated task graph
        """
        pass

    @abstractmethod
    async def delete_task_graph(self, graph_id: UUID) -> bool:
        """Delete a task graph by ID.

        Args:
            graph_id: The ID of the task graph to delete

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    async def add_task_node(self, graph_id: UUID, node: TaskNode) -> TaskNode:
        """Add a task node to a graph.

        Args:
            graph_id: The ID of the graph
            node: The task node to add

        Returns:
            The added task node
        """
        pass

    @abstractmethod
    async def get_task_node(self, graph_id: UUID, node_id: UUID) -> Optional[TaskNode]:
        """Get a task node by ID.

        Args:
            graph_id: The ID of the graph
            node_id: The ID of the task node to retrieve

        Returns:
            The task node if found, None otherwise
        """
        pass

    @abstractmethod
    async def update_task_node(self, graph_id: UUID, node: TaskNode) -> TaskNode:
        """Update an existing task node.

        Args:
            graph_id: The ID of the graph
            node: The task node to update

        Returns:
            The updated task node
        """
        pass

    @abstractmethod
    async def delete_task_node(self, graph_id: UUID, node_id: UUID) -> bool:
        """Delete a task node by ID.

        Args:
            graph_id: The ID of the graph
            node_id: The ID of the task node to delete

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    async def add_task_relationship(
        self, graph_id: UUID, relationship: TaskRelationship
    ) -> TaskRelationship:
        """Add a relationship between tasks.

        Args:
            graph_id: The ID of the graph
            relationship: The relationship to add

        Returns:
            The added relationship
        """
        pass

    @abstractmethod
    async def get_task_relationship(
        self, graph_id: UUID, relationship_id: UUID
    ) -> Optional[TaskRelationship]:
        """Get a relationship by ID.

        Args:
            graph_id: The ID of the graph
            relationship_id: The ID of the relationship to retrieve

        Returns:
            The relationship if found, None otherwise
        """
        pass

    @abstractmethod
    async def update_task_relationship(
        self, graph_id: UUID, relationship: TaskRelationship
    ) -> TaskRelationship:
        """Update an existing relationship.

        Args:
            graph_id: The ID of the graph
            relationship: The relationship to update

        Returns:
            The updated relationship
        """
        pass

    @abstractmethod
    async def delete_task_relationship(
        self, graph_id: UUID, relationship_id: UUID
    ) -> bool:
        """Delete a relationship by ID.

        Args:
            graph_id: The ID of the graph
            relationship_id: The ID of the relationship to delete

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    async def get_task_dependencies(
        self, graph_id: UUID, node_id: UUID
    ) -> List[TaskNode]:
        """Get all dependencies for a task.

        Args:
            graph_id: The ID of the graph
            node_id: The ID of the task

        Returns:
            List of dependency tasks
        """
        pass

    @abstractmethod
    async def get_task_dependents(
        self, graph_id: UUID, node_id: UUID
    ) -> List[TaskNode]:
        """Get all tasks that depend on this task.

        Args:
            graph_id: The ID of the graph
            node_id: The ID of the task

        Returns:
            List of dependent tasks
        """
        pass

    @abstractmethod
    async def calculate_execution_order(self, graph_id: UUID) -> List[UUID]:
        """Calculate the execution order of tasks in a graph.

        Args:
            graph_id: The ID of the graph

        Returns:
            List of task IDs in execution order
        """
        pass
