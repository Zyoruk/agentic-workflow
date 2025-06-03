"""Knowledge graph service implementation."""

from typing import List
from uuid import UUID

from ..domain.models import KnowledgeGraph, KnowledgeNode, KnowledgeRelationship
from ..domain.ports import KnowledgeGraphRepository, KnowledgeGraphService


class DefaultKnowledgeGraphService(KnowledgeGraphService):
    """Default implementation of the knowledge graph service."""

    def __init__(self, repository: KnowledgeGraphRepository):
        """Initialize the service with a repository.

        Args:
            repository: The knowledge graph repository to use
        """
        self.repository = repository

    async def add_knowledge(
        self, node: KnowledgeNode, relationships: List[KnowledgeRelationship]
    ) -> KnowledgeGraph:
        """Add new knowledge to the graph.

        Args:
            node: The node to add
            relationships: The relationships to create

        Returns:
            The updated knowledge graph
        """
        # Create the node
        created_node = await self.repository.create_node(node)

        # Create relationships
        created_relationships = []
        for rel in relationships:
            rel.source_id = created_node.id
            created_rel = await self.repository.create_relationship(rel)
            created_relationships.append(created_rel)

        # Return the updated graph
        return KnowledgeGraph(
            nodes=[created_node],
            relationships=created_relationships,
        )

    async def find_related_knowledge(
        self, node_id: UUID, max_depth: int = 1
    ) -> KnowledgeGraph:
        """Find knowledge related to a node up to a certain depth.

        Args:
            node_id: The ID of the node to find relations for
            max_depth: Maximum depth of relationships to traverse

        Returns:
            The knowledge graph containing related nodes and relationships
        """
        # Build the Cypher query for traversing relationships
        query = f"""
        MATCH path = (n:KnowledgeNode {{id: $id}})-[r:RELATES_TO*1..{max_depth}]->(m:KnowledgeNode)
        RETURN n, r, m
        """
        return await self.repository.query_graph(query, {"id": str(node_id)})

    async def find_path(
        self, source_id: UUID, target_id: UUID, max_depth: int = 3
    ) -> List[KnowledgeRelationship]:
        """Find a path between two nodes.

        Args:
            source_id: The ID of the source node
            target_id: The ID of the target node
            max_depth: Maximum depth of relationships to traverse

        Returns:
            List of relationships forming the path
        """
        # Build the Cypher query for finding the shortest path
        query = f"""
        MATCH path = shortestPath((source:KnowledgeNode {{id: $source_id}})-[r:RELATES_TO*1..{max_depth}]->(target:KnowledgeNode {{id: $target_id}}))
        RETURN r
        """
        result = await self.repository.query_graph(
            query,
            {
                "source_id": str(source_id),
                "target_id": str(target_id),
            },
        )
        return result.relationships

    async def merge_knowledge(self, source_id: UUID, target_id: UUID) -> KnowledgeNode:
        """Merge two nodes and their relationships.

        Args:
            source_id: The ID of the source node to merge
            target_id: The ID of the target node to merge into

        Returns:
            The merged node
        """
        # Get both nodes
        source_node = await self.repository.get_node(source_id)
        target_node = await self.repository.get_node(target_id)

        if not source_node or not target_node:
            raise ValueError("Both source and target nodes must exist")

        # Get all relationships for the source node
        source_relationships = await self.repository.get_node_relationships(source_id)

        # Create new relationships from target to source's connections
        for rel in source_relationships:
            new_rel = KnowledgeRelationship(
                type=rel.type,
                source_id=target_id,
                target_id=rel.target_id,
                properties=rel.properties,
                metadata=rel.metadata,
            )
            await self.repository.create_relationship(new_rel)

        # Delete the source node (this will also delete its relationships)
        await self.repository.delete_node(source_id)

        # Return the target node
        return target_node
