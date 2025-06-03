"""Unit tests for knowledge graph service implementation."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from agentic_workflow.graph.application.knowledge_graph_service import (
    DefaultKnowledgeGraphService,
)
from agentic_workflow.graph.domain.models import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelationship,
    NodeType,
    RelationshipType,
)
from agentic_workflow.graph.domain.ports import KnowledgeGraphRepository


@pytest.fixture
def mock_repository():
    """Create a mock repository for testing."""
    return AsyncMock(spec=KnowledgeGraphRepository)


@pytest.fixture
def service(mock_repository):
    """Create a service instance with a mock repository."""
    return DefaultKnowledgeGraphService(mock_repository)


class TestDefaultKnowledgeGraphService:
    """Test cases for DefaultKnowledgeGraphService."""

    @pytest.mark.asyncio
    async def test_add_knowledge(self, service, mock_repository):
        """Test adding new knowledge to the graph."""
        # Arrange
        node = KnowledgeNode(type=NodeType.CONCEPT, name="Test Concept")
        relationships = [
            KnowledgeRelationship(
                type=RelationshipType.DEPENDS_ON,
                source_id=node.id,
                target_id=UUID("00000000-0000-0000-0000-000000000002"),
            )
        ]
        mock_repository.create_node.return_value = node
        mock_repository.create_relationship.return_value = relationships[0]

        # Act
        result = await service.add_knowledge(node, relationships)

        # Assert
        assert isinstance(result, KnowledgeGraph)
        assert len(result.nodes) == 1
        assert len(result.relationships) == 1
        assert result.nodes[0] == node
        assert result.relationships[0] == relationships[0]
        mock_repository.create_node.assert_called_once_with(node)
        mock_repository.create_relationship.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_related_knowledge(self, service, mock_repository):
        """Test finding related knowledge."""
        # Arrange
        node_id = UUID("00000000-0000-0000-0000-000000000001")
        expected_graph = KnowledgeGraph(
            nodes=[
                KnowledgeNode(type=NodeType.CONCEPT, name="Test Concept"),
            ],
            relationships=[
                KnowledgeRelationship(
                    type=RelationshipType.DEPENDS_ON,
                    source_id=node_id,
                    target_id=UUID("00000000-0000-0000-0000-000000000002"),
                ),
            ],
        )
        mock_repository.query_graph.return_value = expected_graph

        # Act
        result = await service.find_related_knowledge(node_id, max_depth=2)

        # Assert
        assert result == expected_graph
        mock_repository.query_graph.assert_called_once()
        query = mock_repository.query_graph.call_args[0][0]
        assert (
            "MATCH path = (n:KnowledgeNode {id: $id})-[r:RELATES_TO*1..2]->(m:KnowledgeNode)"
            in query
        )

    @pytest.mark.asyncio
    async def test_find_path(self, service, mock_repository):
        """Test finding a path between nodes."""
        # Arrange
        source_id = UUID("00000000-0000-0000-0000-000000000001")
        target_id = UUID("00000000-0000-0000-0000-000000000002")
        expected_relationships = [
            KnowledgeRelationship(
                type=RelationshipType.DEPENDS_ON,
                source_id=source_id,
                target_id=target_id,
            ),
        ]
        mock_repository.query_graph.return_value = KnowledgeGraph(
            nodes=[],
            relationships=expected_relationships,
        )

        # Act
        result = await service.find_path(source_id, target_id)

        # Assert
        assert result == expected_relationships
        mock_repository.query_graph.assert_called_once()
        query = mock_repository.query_graph.call_args[0][0]
        assert (
            "MATCH path = shortestPath((source:KnowledgeNode {id: $source_id})-[r:RELATES_TO*1..3]->(target:KnowledgeNode {id: $target_id}))"
            in query
        )

    @pytest.mark.asyncio
    async def test_merge_knowledge(self, service, mock_repository):
        """Test merging two nodes."""
        # Arrange
        source_id = UUID("00000000-0000-0000-0000-000000000001")
        target_id = UUID("00000000-0000-0000-0000-000000000002")
        source_node = KnowledgeNode(type=NodeType.CONCEPT, name="Source")
        target_node = KnowledgeNode(type=NodeType.CONCEPT, name="Target")
        relationships = [
            KnowledgeRelationship(
                type=RelationshipType.DEPENDS_ON,
                source_id=source_id,
                target_id=UUID("00000000-0000-0000-0000-000000000003"),
            ),
        ]

        mock_repository.get_node.side_effect = [source_node, target_node]
        mock_repository.get_node_relationships.return_value = relationships
        mock_repository.create_relationship.return_value = relationships[0]
        mock_repository.delete_node.return_value = True

        # Act
        result = await service.merge_knowledge(source_id, target_id)

        # Assert
        assert result == target_node
        assert mock_repository.get_node.call_count == 2
        mock_repository.get_node_relationships.assert_called_once_with(source_id)
        mock_repository.create_relationship.assert_called_once()
        mock_repository.delete_node.assert_called_once_with(source_id)

    @pytest.mark.asyncio
    async def test_merge_knowledge_missing_nodes(self, service, mock_repository):
        """Test merging nodes when one is missing."""
        # Arrange
        source_id = UUID("00000000-0000-0000-0000-000000000001")
        target_id = UUID("00000000-0000-0000-0000-000000000002")
        mock_repository.get_node.side_effect = [None, None]

        # Act & Assert
        with pytest.raises(ValueError, match="Both source and target nodes must exist"):
            await service.merge_knowledge(source_id, target_id)
