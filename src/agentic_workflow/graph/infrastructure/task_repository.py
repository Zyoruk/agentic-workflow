"""Neo4j implementation of the task graph repository."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from ..domain.task_models import TaskGraph, TaskNode, TaskRelationship
from ..domain.task_ports import TaskGraphRepository


class Neo4jTaskGraphRepository(TaskGraphRepository):
    """Neo4j implementation of the task graph repository."""

    def __init__(self, driver: AsyncDriver):
        """Initialize the repository with a Neo4j driver.

        Args:
            driver: Neo4j async driver instance
        """
        self.driver = driver

    async def create_task_graph(self, graph: TaskGraph) -> TaskGraph:
        """Create a new task graph.

        Args:
            graph: The task graph to create

        Returns:
            The created task graph
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._create_task_graph_tx,
                graph.model_dump(),
            )
            return TaskGraph(**result)

    async def get_task_graph(self, graph_id: UUID) -> Optional[TaskGraph]:
        """Get a task graph by ID.

        Args:
            graph_id: The ID of the task graph to retrieve

        Returns:
            The task graph if found, None otherwise
        """
        async with self.driver.session() as session:
            result = await session.execute_read(
                self._get_task_graph_tx,
                str(graph_id),
            )
            return TaskGraph(**result) if result else None

    async def update_task_graph(self, graph: TaskGraph) -> TaskGraph:
        """Update an existing task graph.

        Args:
            graph: The task graph to update

        Returns:
            The updated task graph
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._update_task_graph_tx,
                graph.model_dump(),
            )
            return TaskGraph(**result)

    async def delete_task_graph(self, graph_id: UUID) -> bool:
        """Delete a task graph by ID.

        Args:
            graph_id: The ID of the task graph to delete

        Returns:
            True if deleted, False otherwise
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._delete_task_graph_tx,
                str(graph_id),
            )
            return bool(result)

    async def add_task_node(self, graph_id: UUID, node: TaskNode) -> TaskNode:
        """Add a task node to a graph.

        Args:
            graph_id: The ID of the graph
            node: The task node to add

        Returns:
            The added task node
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._add_task_node_tx,
                str(graph_id),
                node.model_dump(),
            )
            return TaskNode(**result)

    async def get_task_node(self, graph_id: UUID, node_id: UUID) -> Optional[TaskNode]:
        """Get a task node by ID.

        Args:
            graph_id: The ID of the graph
            node_id: The ID of the task node to retrieve

        Returns:
            The task node if found, None otherwise
        """
        async with self.driver.session() as session:
            result = await session.execute_read(
                self._get_task_node_tx,
                str(graph_id),
                str(node_id),
            )
            return TaskNode(**result) if result else None

    async def update_task_node(self, graph_id: UUID, node: TaskNode) -> TaskNode:
        """Update an existing task node.

        Args:
            graph_id: The ID of the graph
            node: The task node to update

        Returns:
            The updated task node
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._update_task_node_tx,
                str(graph_id),
                node.model_dump(),
            )
            return TaskNode(**result)

    async def delete_task_node(self, graph_id: UUID, node_id: UUID) -> bool:
        """Delete a task node by ID.

        Args:
            graph_id: The ID of the graph
            node_id: The ID of the task node to delete

        Returns:
            True if deleted, False otherwise
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._delete_task_node_tx,
                str(graph_id),
                str(node_id),
            )
            return bool(result)

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
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._add_task_relationship_tx,
                str(graph_id),
                relationship.model_dump(),
            )
            return TaskRelationship(**result)

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
        async with self.driver.session() as session:
            result = await session.execute_read(
                self._get_task_relationship_tx,
                str(graph_id),
                str(relationship_id),
            )
            return TaskRelationship(**result) if result else None

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
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._update_task_relationship_tx,
                str(graph_id),
                relationship.model_dump(),
            )
            return TaskRelationship(**result)

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
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._delete_task_relationship_tx,
                str(graph_id),
                str(relationship_id),
            )
            return bool(result)

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
        async with self.driver.session() as session:
            results = await session.execute_read(
                self._get_task_dependencies_tx,
                str(graph_id),
                str(node_id),
            )
            return [TaskNode(**r) for r in results]

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
        async with self.driver.session() as session:
            results = await session.execute_read(
                self._get_task_dependents_tx,
                str(graph_id),
                str(node_id),
            )
            return [TaskNode(**r) for r in results]

    async def calculate_execution_order(self, graph_id: UUID) -> List[UUID]:
        """Calculate the execution order of tasks in a graph.

        Args:
            graph_id: The ID of the graph

        Returns:
            List of task IDs in execution order
        """
        async with self.driver.session() as session:
            results = await session.execute_read(
                self._calculate_execution_order_tx,
                str(graph_id),
            )
            return [UUID(r["id"]) for r in results]

    @staticmethod
    async def _create_task_graph_tx(
        tx: AsyncManagedTransaction, graph_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to create a task graph."""
        query = """
        CREATE (g:TaskGraph {
            id: $id,
            metadata: $metadata,
            created_at: datetime(),
            updated_at: datetime()
        })
        RETURN g
        """
        result = await tx.run(query, graph_data)
        record = await result.single()
        return dict(record["g"]) if record else {}

    @staticmethod
    async def _get_task_graph_tx(
        tx: AsyncManagedTransaction, graph_id: str
    ) -> Optional[Dict[str, Any]]:
        """Transaction function to get a task graph."""
        query = """
        MATCH (g:TaskGraph {id: $id})
        OPTIONAL MATCH (g)-[:CONTAINS]->(n:TaskNode)
        OPTIONAL MATCH (n)-[r:RELATES_TO]->(m:TaskNode)
        RETURN g,
               collect(distinct n) as nodes,
               collect(distinct r) as relationships
        """
        result = await tx.run(query, {"id": graph_id})
        record = await result.single()
        if not record:
            return None

        graph_data = dict(record["g"])
        graph_data["nodes"] = {n["id"]: dict(n) for n in record["nodes"] if n}
        graph_data["relationships"] = {
            r["id"]: dict(r) for r in record["relationships"] if r
        }
        return graph_data

    @staticmethod
    async def _update_task_graph_tx(
        tx: AsyncManagedTransaction, graph_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to update a task graph."""
        query = """
        MATCH (g:TaskGraph {id: $id})
        SET g += {
            metadata: $metadata,
            updated_at: datetime()
        }
        RETURN g
        """
        result = await tx.run(query, graph_data)
        record = await result.single()
        return dict(record["g"]) if record else {}

    @staticmethod
    async def _delete_task_graph_tx(tx: AsyncManagedTransaction, graph_id: str) -> bool:
        """Transaction function to delete a task graph."""
        query = """
        MATCH (g:TaskGraph {id: $id})
        DETACH DELETE g
        RETURN count(g) as deleted
        """
        result = await tx.run(query, {"id": graph_id})
        record = await result.single()
        return bool(record["deleted"]) if record else False

    @staticmethod
    async def _add_task_node_tx(
        tx: AsyncManagedTransaction, graph_id: str, node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to add a task node."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})
        CREATE (n:TaskNode {
            id: $id,
            type: $type,
            status: $status,
            priority: $priority,
            name: $name,
            description: $description,
            requirements: $requirements,
            metadata: $metadata,
            created_at: datetime(),
            updated_at: datetime(),
            started_at: $started_at,
            completed_at: $completed_at,
            estimated_duration: $estimated_duration,
            actual_duration: $actual_duration,
            retry_count: $retry_count,
            max_retries: $max_retries,
            error_message: $error_message
        })
        CREATE (g)-[:CONTAINS]->(n)
        RETURN n
        """
        result = await tx.run(query, {"graph_id": graph_id, **node_data})
        record = await result.single()
        return dict(record["n"]) if record else {}

    @staticmethod
    async def _get_task_node_tx(
        tx: AsyncManagedTransaction, graph_id: str, node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Transaction function to get a task node."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(n:TaskNode {id: $node_id})
        RETURN n
        """
        result = await tx.run(query, {"graph_id": graph_id, "node_id": node_id})
        record = await result.single()
        return dict(record["n"]) if record else None

    @staticmethod
    async def _update_task_node_tx(
        tx: AsyncManagedTransaction, graph_id: str, node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to update a task node."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(n:TaskNode {id: $id})
        SET n += {
            type: $type,
            status: $status,
            priority: $priority,
            name: $name,
            description: $description,
            requirements: $requirements,
            metadata: $metadata,
            updated_at: datetime(),
            started_at: $started_at,
            completed_at: $completed_at,
            estimated_duration: $estimated_duration,
            actual_duration: $actual_duration,
            retry_count: $retry_count,
            max_retries: $max_retries,
            error_message: $error_message
        }
        RETURN n
        """
        result = await tx.run(query, {"graph_id": graph_id, **node_data})
        record = await result.single()
        return dict(record["n"]) if record else {}

    @staticmethod
    async def _delete_task_node_tx(
        tx: AsyncManagedTransaction, graph_id: str, node_id: str
    ) -> bool:
        """Transaction function to delete a task node."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(n:TaskNode {id: $node_id})
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        result = await tx.run(query, {"graph_id": graph_id, "node_id": node_id})
        record = await result.single()
        return bool(record["deleted"]) if record else False

    @staticmethod
    async def _add_task_relationship_tx(
        tx: AsyncManagedTransaction, graph_id: str, relationship_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to add a task relationship."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(source:TaskNode {id: $source_id})
        MATCH (g)-[:CONTAINS]->(target:TaskNode {id: $target_id})
        CREATE (source)-[r:RELATES_TO {
            id: $id,
            type: $type,
            properties: $properties,
            metadata: $metadata,
            created_at: datetime(),
            updated_at: datetime()
        }]->(target)
        RETURN r
        """
        result = await tx.run(query, {"graph_id": graph_id, **relationship_data})
        record = await result.single()
        return dict(record["r"]) if record else {}

    @staticmethod
    async def _get_task_relationship_tx(
        tx: AsyncManagedTransaction, graph_id: str, relationship_id: str
    ) -> Optional[Dict[str, Any]]:
        """Transaction function to get a task relationship."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(source:TaskNode)-[r:RELATES_TO {id: $relationship_id}]->(target:TaskNode)
        RETURN r
        """
        result = await tx.run(
            query, {"graph_id": graph_id, "relationship_id": relationship_id}
        )
        record = await result.single()
        return dict(record["r"]) if record else None

    @staticmethod
    async def _update_task_relationship_tx(
        tx: AsyncManagedTransaction, graph_id: str, relationship_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to update a task relationship."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(source:TaskNode)-[r:RELATES_TO {id: $id}]->(target:TaskNode)
        SET r += {
            type: $type,
            properties: $properties,
            metadata: $metadata,
            updated_at: datetime()
        }
        RETURN r
        """
        result = await tx.run(query, {"graph_id": graph_id, **relationship_data})
        record = await result.single()
        return dict(record["r"]) if record else {}

    @staticmethod
    async def _delete_task_relationship_tx(
        tx: AsyncManagedTransaction, graph_id: str, relationship_id: str
    ) -> bool:
        """Transaction function to delete a task relationship."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(source:TaskNode)-[r:RELATES_TO {id: $relationship_id}]->(target:TaskNode)
        DELETE r
        RETURN count(r) as deleted
        """
        result = await tx.run(
            query, {"graph_id": graph_id, "relationship_id": relationship_id}
        )
        record = await result.single()
        return bool(record["deleted"]) if record else False

    @staticmethod
    async def _get_task_dependencies_tx(
        tx: AsyncManagedTransaction, graph_id: str, node_id: str
    ) -> List[Dict[str, Any]]:
        """Transaction function to get task dependencies."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(source:TaskNode)-[r:RELATES_TO]->(target:TaskNode {id: $node_id})
        RETURN source
        """
        result = await tx.run(query, {"graph_id": graph_id, "node_id": node_id})
        records = await result.data()
        return [dict(record["source"]) for record in records]

    @staticmethod
    async def _get_task_dependents_tx(
        tx: AsyncManagedTransaction, graph_id: str, node_id: str
    ) -> List[Dict[str, Any]]:
        """Transaction function to get task dependents."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(source:TaskNode {id: $node_id})-[r:RELATES_TO]->(target:TaskNode)
        RETURN target
        """
        result = await tx.run(query, {"graph_id": graph_id, "node_id": node_id})
        records = await result.data()
        return [dict(record["target"]) for record in records]

    @staticmethod
    async def _calculate_execution_order_tx(
        tx: AsyncManagedTransaction, graph_id: str
    ) -> List[Dict[str, Any]]:
        """Transaction function to calculate execution order."""
        query = """
        MATCH (g:TaskGraph {id: $graph_id})-[:CONTAINS]->(n:TaskNode)
        WITH n
        CALL {
            WITH n
            MATCH path = (n)-[:RELATES_TO*]->(m:TaskNode)
            RETURN count(path) as depth
        }
        RETURN n.id as id
        ORDER BY depth DESC
        """
        result = await tx.run(query, {"graph_id": graph_id})
        records = await result.data()
        return records
