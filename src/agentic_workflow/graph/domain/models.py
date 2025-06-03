"""Domain models for the knowledge graph."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    CONCEPT = "concept"
    TASK = "task"
    SKILL = "skill"
    AGENT = "agent"
    TOOL = "tool"
    DOCUMENT = "document"


class RelationshipType(str, Enum):
    """Types of relationships in the knowledge graph."""

    DEPENDS_ON = "depends_on"
    REQUIRES = "requires"
    USES = "uses"
    CREATED_BY = "created_by"
    PART_OF = "part_of"
    SIMILAR_TO = "similar_to"
    LEADS_TO = "leads_to"


class KnowledgeNode(BaseModel):
    """A node in the knowledge graph."""

    id: UUID = Field(default_factory=uuid4)
    type: NodeType
    name: str
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __eq__(self, other: Any) -> bool:
        """Compare two nodes for equality based on their ID."""
        if not isinstance(other, KnowledgeNode):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Generate a hash based on the node's ID."""
        return hash(self.id)


class KnowledgeRelationship(BaseModel):
    """A relationship between nodes in the knowledge graph."""

    id: UUID = Field(default_factory=uuid4)
    type: RelationshipType
    source_id: UUID
    target_id: UUID
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __eq__(self, other: Any) -> bool:
        """Compare two relationships for equality based on their ID."""
        if not isinstance(other, KnowledgeRelationship):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Generate a hash based on the relationship's ID."""
        return hash(self.id)


class KnowledgeGraph(BaseModel):
    """The complete knowledge graph."""

    nodes: List[KnowledgeNode] = Field(default_factory=list)
    relationships: List[KnowledgeRelationship] = Field(default_factory=list)

    def __eq__(self, other: Any) -> bool:
        """Compare two graphs for equality based on their nodes and relationships."""
        if not isinstance(other, KnowledgeGraph):
            return False
        return set(self.nodes) == set(other.nodes) and set(self.relationships) == set(
            other.relationships
        )
