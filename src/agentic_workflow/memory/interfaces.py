"""Memory management interfaces and data models."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryType(Enum):
    """Types of memory storage."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    CACHE = "cache"
    VECTOR = "vector"


class MemoryEntry(BaseModel):
    """Represents a single memory entry."""

    id: str = Field(..., description="Unique identifier for the memory entry")
    content: str = Field(..., description="The content to be stored")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    memory_type: MemoryType = Field(..., description="Type of memory storage")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the entry was created",
    )
    ttl: Optional[int] = Field(default=None, description="Time to live in seconds")
    embedding: Optional[List[float]] = Field(
        default=None, description="Vector embedding of the content"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    priority: int = Field(
        default=0, description="Priority level (higher = more important)"
    )


class MemoryQuery(BaseModel):
    """Query parameters for memory retrieval."""

    content: Optional[str] = Field(default=None, description="Content to search for")
    memory_type: Optional[MemoryType] = Field(
        default=None, description="Filter by memory type"
    )
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    metadata_filters: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata filters"
    )
    limit: int = Field(
        default=10, ge=1, le=1000, description="Maximum number of results"
    )
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum similarity score"
    )
    time_range: Optional[tuple[datetime, datetime]] = Field(
        default=None, description="Time range filter"
    )


class MemoryResult(BaseModel):
    """Result of a memory query operation."""

    entries: List[MemoryEntry] = Field(
        default_factory=list, description="Retrieved memory entries"
    )
    total_count: int = Field(default=0, description="Total number of matching entries")
    query_time: float = Field(
        default=0.0, description="Query execution time in seconds"
    )
    similarity_scores: List[float] = Field(
        default_factory=list, description="Similarity scores for vector queries"
    )


class MemoryStats(BaseModel):
    """Memory store statistics."""

    total_entries: int = Field(default=0, description="Total number of entries")
    memory_usage: int = Field(default=0, description="Memory usage in bytes")
    hit_rate: float = Field(default=0.0, description="Cache hit rate (0.0-1.0)")
    average_retrieval_time: float = Field(
        default=0.0, description="Average retrieval time in seconds"
    )
    entries_by_type: Dict[str, int] = Field(
        default_factory=dict, description="Count by memory type"
    )


class MemoryStore(ABC):
    """Abstract base class for memory storage implementations."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize the memory store.

        Args:
            name: Name of the memory store
            config: Configuration parameters
        """
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry.

        Args:
            entry: Memory entry to store

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve memory entries based on query.

        Args:
            query: Query parameters

        Returns:
            Query results
        """
        pass

    @abstractmethod
    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry.

        Args:
            entry_id: ID of the entry to update
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear memory entries.

        Args:
            memory_type: Optional filter by memory type

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_stats(self) -> MemoryStats:
        """Get memory store statistics.

        Returns:
            Memory statistics
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the memory store is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the memory store and cleanup resources."""
        pass

    @abstractmethod
    async def create_embedding(self, content: str) -> List[float]:
        """Create vector embedding for content.

        Args:
            content: Text content to embed

        Returns:
            Vector embedding
        """
        pass

    @abstractmethod
    async def similarity_search(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform similarity search using vector embeddings.

        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            Similar memory entries
        """
        pass


class VectorStore(MemoryStore):
    """Abstract base class for vector storage implementations."""

    @abstractmethod
    async def similarity_search(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform similarity search using vector embeddings.

        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            Similar memory entries
        """
        pass

    @abstractmethod
    async def create_embedding(self, content: str) -> List[float]:
        """Create vector embedding for content.

        Args:
            content: Text content to embed

        Returns:
            Vector embedding
        """
        pass


class CacheStore(MemoryStore):
    """Abstract base class for cache storage implementations."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a cache value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a cache value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        pass
