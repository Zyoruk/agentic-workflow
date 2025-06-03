"""Neo4j repository implementation for the knowledge graph."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from neo4j import AsyncDriver, AsyncManagedTransaction

from ..domain.models import KnowledgeGraph, KnowledgeNode, KnowledgeRelationship
from ..domain.ports import KnowledgeGraphRepository


class Neo4jKnowledgeGraphRepository(KnowledgeGraphRepository):
    """Neo4j implementation of the knowledge graph repository."""

    def __init__(self, driver: AsyncDriver):
        """Initialize the repository with a Neo4j driver.

        Args:
            driver: Neo4j async driver instance
        """
        self.driver = driver

    async def create_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Create a new node in the knowledge graph.

        Args:
            node: The node to create

        Returns:
            The created node with updated metadata
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._create_node_tx,
                node.model_dump(),
            )
            return KnowledgeNode(**result)

    async def get_node(self, node_id: UUID) -> Optional[KnowledgeNode]:
        """Get a node by its ID.

        Args:
            node_id: The ID of the node to retrieve

        Returns:
            The node if found, None otherwise
        """
        async with self.driver.session() as session:
            result = await session.execute_read(
                self._get_node_tx,
                str(node_id),
            )
            return KnowledgeNode(**result) if result else None

    async def update_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Update an existing node.

        Args:
            node: The node to update

        Returns:
            The updated node
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._update_node_tx,
                node.model_dump(),
            )
            return KnowledgeNode(**result)

    async def delete_node(self, node_id: UUID) -> bool:
        """Delete a node by its ID.

        Args:
            node_id: The ID of the node to delete

        Returns:
            True if deleted, False otherwise
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._delete_node_tx,
                str(node_id),
            )
            return bool(result)

    async def create_relationship(
        self, relationship: KnowledgeRelationship
    ) -> KnowledgeRelationship:
        """Create a new relationship between nodes.

        Args:
            relationship: The relationship to create

        Returns:
            The created relationship with updated metadata
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._create_relationship_tx,
                relationship.model_dump(),
            )
            return KnowledgeRelationship(**result)

    async def get_relationship(
        self, relationship_id: UUID
    ) -> Optional[KnowledgeRelationship]:
        """Get a relationship by its ID.

        Args:
            relationship_id: The ID of the relationship to retrieve

        Returns:
            The relationship if found, None otherwise
        """
        async with self.driver.session() as session:
            result = await session.execute_read(
                self._get_relationship_tx,
                str(relationship_id),
            )
            return KnowledgeRelationship(**result) if result else None

    async def update_relationship(
        self, relationship: KnowledgeRelationship
    ) -> KnowledgeRelationship:
        """Update an existing relationship.

        Args:
            relationship: The relationship to update

        Returns:
            The updated relationship
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._update_relationship_tx,
                relationship.model_dump(),
            )
            return KnowledgeRelationship(**result)

    async def delete_relationship(self, relationship_id: UUID) -> bool:
        """Delete a relationship by its ID.

        Args:
            relationship_id: The ID of the relationship to delete

        Returns:
            True if deleted, False otherwise
        """
        async with self.driver.session() as session:
            result = await session.execute_write(
                self._delete_relationship_tx,
                str(relationship_id),
            )
            return bool(result)

    async def get_node_relationships(
        self, node_id: UUID, relationship_type: Optional[str] = None
    ) -> List[KnowledgeRelationship]:
        """Get all relationships for a node.

        Args:
            node_id: The ID of the node
            relationship_type: Optional relationship type filter

        Returns:
            List of relationships
        """
        async with self.driver.session() as session:
            results = await session.execute_read(
                self._get_node_relationships_tx,
                str(node_id),
                relationship_type,
            )
            return [KnowledgeRelationship(**r) for r in results]

    async def query_graph(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> KnowledgeGraph:
        """Execute a custom query on the knowledge graph.

        Args:
            query: The Cypher query to execute
            params: Optional query parameters

        Returns:
            The resulting knowledge graph
        """
        async with self.driver.session() as session:
            results = await session.execute_read(
                self._query_graph_tx,
                query,
                params or {},
            )
            return KnowledgeGraph(**results)

    @staticmethod
    async def _create_node_tx(
        tx: AsyncManagedTransaction, node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to create a node."""
        query = """
        CREATE (n:KnowledgeNode {
            id: $id,
            type: $type,
            name: $name,
            description: $description,
            properties: $properties,
            created_at: datetime(),
            updated_at: datetime(),
            metadata: $metadata
        })
        RETURN n
        """
        result = await tx.run(query, node_data)
        record = await result.single()
        return dict(record["n"]) if record else {}

    @staticmethod
    async def _get_node_tx(
        tx: AsyncManagedTransaction, node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Transaction function to get a node."""
        query = """
        MATCH (n:KnowledgeNode {id: $id})
        RETURN n
        """
        result = await tx.run(query, {"id": node_id})
        record = await result.single()
        return dict(record["n"]) if record else None

    @staticmethod
    async def _update_node_tx(
        tx: AsyncManagedTransaction, node_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to update a node."""
        query = """
        MATCH (n:KnowledgeNode {id: $id})
        SET n += {
            type: $type,
            name: $name,
            description: $description,
            properties: $properties,
            updated_at: datetime(),
            metadata: $metadata
        }
        RETURN n
        """
        result = await tx.run(query, node_data)
        record = await result.single()
        return dict(record["n"]) if record else {}

    @staticmethod
    async def _delete_node_tx(tx: AsyncManagedTransaction, node_id: str) -> bool:
        """Transaction function to delete a node."""
        query = """
        MATCH (n:KnowledgeNode {id: $id})
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        result = await tx.run(query, {"id": node_id})
        record = await result.single()
        return bool(record["deleted"]) if record else False

    @staticmethod
    async def _create_relationship_tx(
        tx: AsyncManagedTransaction, relationship_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to create a relationship."""
        query = """
        MATCH (source:KnowledgeNode {id: $source_id})
        MATCH (target:KnowledgeNode {id: $target_id})
        CREATE (source)-[r:RELATES_TO {
            id: $id,
            type: $type,
            properties: $properties,
            created_at: datetime(),
            updated_at: datetime(),
            metadata: $metadata
        }]->(target)
        RETURN r
        """
        result = await tx.run(query, relationship_data)
        record = await result.single()
        return dict(record["r"]) if record else {}

    @staticmethod
    async def _get_relationship_tx(
        tx: AsyncManagedTransaction, relationship_id: str
    ) -> Optional[Dict[str, Any]]:
        """Transaction function to get a relationship."""
        query = """
        MATCH ()-[r:RELATES_TO {id: $id}]->()
        RETURN r
        """
        result = await tx.run(query, {"id": relationship_id})
        record = await result.single()
        return dict(record["r"]) if record else None

    @staticmethod
    async def _update_relationship_tx(
        tx: AsyncManagedTransaction, relationship_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to update a relationship."""
        query = """
        MATCH ()-[r:RELATES_TO {id: $id}]->()
        SET r += {
            type: $type,
            properties: $properties,
            updated_at: datetime(),
            metadata: $metadata
        }
        RETURN r
        """
        result = await tx.run(query, relationship_data)
        record = await result.single()
        return dict(record["r"]) if record else {}

    @staticmethod
    async def _delete_relationship_tx(
        tx: AsyncManagedTransaction, relationship_id: str
    ) -> bool:
        """Transaction function to delete a relationship."""
        query = """
        MATCH ()-[r:RELATES_TO {id: $id}]->()
        DELETE r
        RETURN count(r) as deleted
        """
        result = await tx.run(query, {"id": relationship_id})
        record = await result.single()
        return bool(record["deleted"]) if record else False

    @staticmethod
    async def _get_node_relationships_tx(
        tx: AsyncManagedTransaction, node_id: str, relationship_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Transaction function to get node relationships."""
        query = """
        MATCH (n:KnowledgeNode {id: $id})-[r:RELATES_TO]->()
        WHERE $type IS NULL OR r.type = $type
        RETURN r
        """
        result = await tx.run(query, {"id": node_id, "type": relationship_type})
        records = await result.data()
        return [dict(record["r"]) for record in records]

    @staticmethod
    async def _query_graph_tx(
        tx: AsyncManagedTransaction, query: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transaction function to execute a custom query."""
        result = await tx.run(query, params)
        records = await result.data()
        return {
            "nodes": [dict(record["n"]) for record in records if "n" in record],
            "relationships": [dict(record["r"]) for record in records if "r" in record],
        }
