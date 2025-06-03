"""Ports (interfaces) for the knowledge graph."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from .models import KnowledgeGraph, KnowledgeNode, KnowledgeRelationship


class KnowledgeGraphRepository(ABC):
    """Repository interface for knowledge graph operations."""

    @abstractmethod
    async def create_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Create a new node in the knowledge graph."""
        pass

    @abstractmethod
    async def get_node(self, node_id: UUID) -> Optional[KnowledgeNode]:
        """Get a node by its ID."""
        pass

    @abstractmethod
    async def update_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Update an existing node."""
        pass

    @abstractmethod
    async def delete_node(self, node_id: UUID) -> bool:
        """Delete a node by its ID."""
        pass

    @abstractmethod
    async def create_relationship(
        self, relationship: KnowledgeRelationship
    ) -> KnowledgeRelationship:
        """Create a new relationship between nodes."""
        pass

    @abstractmethod
    async def get_relationship(
        self, relationship_id: UUID
    ) -> Optional[KnowledgeRelationship]:
        """Get a relationship by its ID."""
        pass

    @abstractmethod
    async def update_relationship(
        self, relationship: KnowledgeRelationship
    ) -> KnowledgeRelationship:
        """Update an existing relationship."""
        pass

    @abstractmethod
    async def delete_relationship(self, relationship_id: UUID) -> bool:
        """Delete a relationship by its ID."""
        pass

    @abstractmethod
    async def get_node_relationships(
        self, node_id: UUID, relationship_type: Optional[str] = None
    ) -> List[KnowledgeRelationship]:
        """Get all relationships for a node."""
        pass

    @abstractmethod
    async def query_graph(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> KnowledgeGraph:
        """Execute a custom query on the knowledge graph."""
        pass


class KnowledgeGraphService(ABC):
    """Service interface for knowledge graph operations."""

    @abstractmethod
    async def add_knowledge(
        self, node: KnowledgeNode, relationships: List[KnowledgeRelationship]
    ) -> KnowledgeGraph:
        """Add new knowledge to the graph."""
        pass

    @abstractmethod
    async def find_related_knowledge(
        self, node_id: UUID, max_depth: int = 1
    ) -> KnowledgeGraph:
        """Find knowledge related to a node up to a certain depth."""
        pass

    @abstractmethod
    async def find_path(
        self, source_id: UUID, target_id: UUID, max_depth: int = 3
    ) -> List[KnowledgeRelationship]:
        """Find a path between two nodes."""
        pass

    @abstractmethod
    async def merge_knowledge(self, source_id: UUID, target_id: UUID) -> KnowledgeNode:
        """Merge two nodes and their relationships."""
        pass
