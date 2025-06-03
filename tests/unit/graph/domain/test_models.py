"""Unit tests for knowledge graph domain models."""

from datetime import datetime
from uuid import UUID

from agentic_workflow.graph.domain.models import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelationship,
    NodeType,
    RelationshipType,
)


class TestKnowledgeNode:
    """Test cases for KnowledgeNode model."""

    def test_create_node_with_minimal_data(self):
        """Test creating a node with minimal required data."""
        node = KnowledgeNode(
            type=NodeType.CONCEPT,
            name="Test Concept",
        )
        assert isinstance(node.id, UUID)
        assert node.type == NodeType.CONCEPT
        assert node.name == "Test Concept"
        assert node.description is None
        assert node.properties == {}
        assert isinstance(node.created_at, datetime)
        assert isinstance(node.updated_at, datetime)
        assert node.metadata == {}

    def test_create_node_with_all_data(self):
        """Test creating a node with all optional data."""
        properties = {"key": "value"}
        metadata = {"source": "test"}
        node = KnowledgeNode(
            type=NodeType.TASK,
            name="Test Task",
            description="Test Description",
            properties=properties,
            metadata=metadata,
        )
        assert node.type == NodeType.TASK
        assert node.name == "Test Task"
        assert node.description == "Test Description"
        assert node.properties == properties
        assert node.metadata == metadata

    def test_node_equality(self):
        """Test node equality based on ID."""
        node1 = KnowledgeNode(type=NodeType.CONCEPT, name="Test")
        node2 = KnowledgeNode(type=NodeType.CONCEPT, name="Test")
        assert node1 != node2  # Different IDs

        node2.id = node1.id
        assert node1 == node2  # Same ID


class TestKnowledgeRelationship:
    """Test cases for KnowledgeRelationship model."""

    def test_create_relationship_with_minimal_data(self):
        """Test creating a relationship with minimal required data."""
        source_id = UUID("00000000-0000-0000-0000-000000000001")
        target_id = UUID("00000000-0000-0000-0000-000000000002")
        rel = KnowledgeRelationship(
            type=RelationshipType.DEPENDS_ON,
            source_id=source_id,
            target_id=target_id,
        )
        assert isinstance(rel.id, UUID)
        assert rel.type == RelationshipType.DEPENDS_ON
        assert rel.source_id == source_id
        assert rel.target_id == target_id
        assert rel.properties == {}
        assert isinstance(rel.created_at, datetime)
        assert isinstance(rel.updated_at, datetime)
        assert rel.metadata == {}

    def test_create_relationship_with_all_data(self):
        """Test creating a relationship with all optional data."""
        source_id = UUID("00000000-0000-0000-0000-000000000001")
        target_id = UUID("00000000-0000-0000-0000-000000000002")
        properties = {"weight": 1.0}
        metadata = {"confidence": 0.9}
        rel = KnowledgeRelationship(
            type=RelationshipType.REQUIRES,
            source_id=source_id,
            target_id=target_id,
            properties=properties,
            metadata=metadata,
        )
        assert rel.type == RelationshipType.REQUIRES
        assert rel.source_id == source_id
        assert rel.target_id == target_id
        assert rel.properties == properties
        assert rel.metadata == metadata

    def test_relationship_equality(self):
        """Test relationship equality based on ID."""
        source_id = UUID("00000000-0000-0000-0000-000000000001")
        target_id = UUID("00000000-0000-0000-0000-000000000002")
        rel1 = KnowledgeRelationship(
            type=RelationshipType.DEPENDS_ON,
            source_id=source_id,
            target_id=target_id,
        )
        rel2 = KnowledgeRelationship(
            type=RelationshipType.DEPENDS_ON,
            source_id=source_id,
            target_id=target_id,
        )
        assert rel1 != rel2  # Different IDs

        rel2.id = rel1.id
        assert rel1 == rel2  # Same ID


class TestKnowledgeGraph:
    """Test cases for KnowledgeGraph model."""

    def test_create_empty_graph(self):
        """Test creating an empty knowledge graph."""
        graph = KnowledgeGraph()
        assert graph.nodes == []
        assert graph.relationships == []

    def test_create_graph_with_data(self):
        """Test creating a knowledge graph with nodes and relationships."""
        node1 = KnowledgeNode(type=NodeType.CONCEPT, name="Concept 1")
        node2 = KnowledgeNode(type=NodeType.CONCEPT, name="Concept 2")
        rel = KnowledgeRelationship(
            type=RelationshipType.DEPENDS_ON,
            source_id=node1.id,
            target_id=node2.id,
        )
        graph = KnowledgeGraph(nodes=[node1, node2], relationships=[rel])
        assert len(graph.nodes) == 2
        assert len(graph.relationships) == 1
        assert node1 in graph.nodes
        assert node2 in graph.nodes
        assert rel in graph.relationships
