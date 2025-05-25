"""Unit tests for memory management components."""

import random
from typing import Any, Dict, List, Optional

import pytest

from agentic_workflow.memory import (
    CacheStore,
    MemoryEntry,
    MemoryManager,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryStore,
    MemoryType,
    RedisCacheStore,
    VectorStore,
)


class MockMemoryStore(MemoryStore):
    """Mock memory store for testing."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize mock store."""
        super().__init__(name, config)
        self.entries: Dict[str, MemoryEntry] = {}
        self.health_status = True
        self.stats = MemoryStats()

    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry."""
        self.entries[entry.id] = entry
        return True

    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve memory entries based on query."""
        entries = []
        for entry in self.entries.values():
            entries.append(entry)
        return MemoryResult(entries=entries, total_count=len(entries))

    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        if entry_id not in self.entries:
            return False
        entry = self.entries[entry_id]
        if "content" in updates:
            entry.content = updates["content"]
        if "metadata" in updates:
            entry.metadata.update(updates["metadata"])
        if "tags" in updates:
            entry.tags = updates["tags"]
        return True

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    async def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear memory entries."""
        if memory_type:
            self.entries = {
                k: v for k, v in self.entries.items() if v.memory_type != memory_type
            }
        else:
            self.entries = {}
        return True

    async def get_stats(self) -> MemoryStats:
        """Get memory store statistics."""
        return self.stats

    async def health_check(self) -> bool:
        """Check if the memory store is healthy."""
        return self.health_status

    async def close(self) -> None:
        """Close the memory store."""
        pass

    async def create_embedding(self, content: str) -> List[float]:
        """Create vector embedding for content."""
        return [0.1, 0.2, 0.3]

    async def similarity_search(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform similarity search."""
        return MemoryResult(entries=list(self.entries.values())[:limit])

    async def semantic_search(
        self, query_text: str, limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform semantic search."""
        return MemoryResult(entries=list(self.entries.values())[:limit])


class MockVectorStore(VectorStore):
    """Mock vector store for testing."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize mock vector store."""
        super().__init__(name, config)
        self.entries: Dict[str, MemoryEntry] = {}
        self.health_status = True
        self.stats = MemoryStats()

    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry."""
        self.entries[entry.id] = entry
        return True

    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve memory entries based on query."""
        entries = []
        for entry in self.entries.values():
            entries.append(entry)
        return MemoryResult(entries=entries, total_count=len(entries))

    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        if entry_id not in self.entries:
            return False
        entry = self.entries[entry_id]
        if "content" in updates:
            entry.content = updates["content"]
        if "metadata" in updates:
            entry.metadata.update(updates["metadata"])
        if "tags" in updates:
            entry.tags = updates["tags"]
        return True

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            return True
        return False

    async def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear memory entries."""
        if memory_type:
            self.entries = {
                k: v for k, v in self.entries.items() if v.memory_type != memory_type
            }
        else:
            self.entries = {}
        return True

    async def get_stats(self) -> MemoryStats:
        """Get memory store statistics."""
        return self.stats

    async def health_check(self) -> bool:
        """Check if the memory store is healthy."""
        return self.health_status

    async def close(self) -> None:
        """Close the memory store."""
        pass

    async def create_embedding(self, content: str) -> List[float]:
        """Create vector embedding for content."""
        return [0.1, 0.2, 0.3]

    async def similarity_search(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform similarity search."""
        entries = list(self.entries.values())
        random.shuffle(entries)
        return MemoryResult(
            entries=entries[:limit],
            similarity_scores=[
                random.random() for _ in range(min(limit, len(entries)))
            ],
        )

    async def semantic_search(
        self, query_text: str, limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform semantic search."""
        entries = list(self.entries.values())
        random.shuffle(entries)
        return MemoryResult(
            entries=entries[:limit],
            similarity_scores=[
                random.random() for _ in range(min(limit, len(entries)))
            ],
        )


@pytest.fixture
def memory_manager() -> MemoryManager:
    """Create a memory manager with mock stores."""
    manager = MemoryManager()

    # Set up mock stores
    short_term = MockMemoryStore("short_term")
    vector_store = MockVectorStore("vector_store")
    cache_store = MockMemoryStore("cache")

    # Register stores
    manager.stores = {
        "short_term": short_term,
        "vector_store": vector_store,
        "cache": cache_store,
    }

    # Set up type mappings
    manager.store_types = {
        MemoryType.SHORT_TERM: "short_term",
        MemoryType.LONG_TERM: "vector_store",
        MemoryType.CACHE: "cache",
        MemoryType.VECTOR: "vector_store",
    }

    return manager


class TestMemoryManager:
    """Tests for the MemoryManager class."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store(self, memory_manager: MemoryManager) -> None:
        """Test storing content in memory."""
        entry_id = await memory_manager.store(
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
            metadata={"test": "value"},
            tags=["test"],
        )

        assert entry_id is not None
        assert memory_manager.total_operations == 1

        # Check that it was stored in the right store
        store = memory_manager.stores["short_term"]
        assert entry_id in store.entries  # type: ignore
        assert store.entries[entry_id].content == "Test content"  # type: ignore

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve(self, memory_manager: MemoryManager) -> None:
        """Test retrieving memory entries."""
        # Store some entries
        entry_id1 = await memory_manager.store(
            content="Test content 1",
            memory_type=MemoryType.SHORT_TERM,
        )
        entry_id2 = await memory_manager.store(
            content="Test content 2",
            memory_type=MemoryType.LONG_TERM,
        )

        # Retrieve from specific store
        result1 = await memory_manager.retrieve(memory_type=MemoryType.SHORT_TERM)
        assert len(result1.entries) == 1
        assert result1.entries[0].id == entry_id1

        # Retrieve from all stores
        result2 = await memory_manager.retrieve()
        assert len(result2.entries) >= 2
        retrieved_ids = [entry.id for entry in result2.entries]
        assert entry_id1 in retrieved_ids
        assert entry_id2 in retrieved_ids

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update(self, memory_manager: MemoryManager) -> None:
        """Test updating memory entries."""
        # Store an entry
        entry_id = await memory_manager.store(
            content="Original content",
            memory_type=MemoryType.SHORT_TERM,
        )

        # Update the entry
        success = await memory_manager.update(
            entry_id=entry_id,
            updates={"content": "Updated content"},
            memory_type=MemoryType.SHORT_TERM,
        )

        assert success is True

        # Verify update
        store = memory_manager.stores["short_term"]
        assert store.entries[entry_id].content == "Updated content"  # type: ignore

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete(self, memory_manager: MemoryManager) -> None:
        """Test deleting memory entries."""
        # Store an entry
        entry_id = await memory_manager.store(
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
        )

        # Delete the entry
        success = await memory_manager.delete(
            entry_id=entry_id,
            memory_type=MemoryType.SHORT_TERM,
        )

        assert success is True

        # Verify deletion
        store = memory_manager.stores["short_term"]
        assert entry_id not in store.entries  # type: ignore

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clear(self, memory_manager: MemoryManager) -> None:
        """Test clearing memory entries."""
        # Store entries in different stores
        await memory_manager.store(
            content="Test content 1",
            memory_type=MemoryType.SHORT_TERM,
        )
        await memory_manager.store(
            content="Test content 2",
            memory_type=MemoryType.LONG_TERM,
        )

        # Clear one store
        success = await memory_manager.clear(memory_type=MemoryType.SHORT_TERM)
        assert success is True

        # Verify clearing
        short_term_store = memory_manager.stores["short_term"]
        vector_store = memory_manager.stores["vector_store"]
        assert len(short_term_store.entries) == 0  # type: ignore
        assert len(vector_store.entries) > 0  # type: ignore

        # Clear all stores
        success = await memory_manager.clear()
        assert success is True

        # Verify all cleared
        assert len(vector_store.entries) == 0  # type: ignore


class TestCacheStore:
    """Tests for the cache store implementation."""

    @pytest.fixture
    def mock_cache_store(self) -> CacheStore:
        """Create a mock cache store."""
        config = {"url": "redis://localhost:6379/0"}
        return RedisCacheStore("test_cache", config)

    @pytest.mark.unit
    def test_initialization(self, mock_cache_store: CacheStore) -> None:
        """Test cache store initialization."""
        assert mock_cache_store.name == "test_cache"
        assert mock_cache_store.config["url"] == "redis://localhost:6379/0"
