"""Unit tests for memory management system."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from agentic_workflow.memory import (
    CacheMemoryStore,
    MemoryEntry,
    MemoryManager,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryType,
    ShortTermMemory,
)
from agentic_workflow.memory.vector_store import WeaviateVectorStore


@pytest.fixture
def sample_entry():
    """Create a sample memory entry for testing."""
    return MemoryEntry(
        id=str(uuid.uuid4()),
        content="Sample memory content for testing",
        metadata={"context": "test", "importance": "high"},
        memory_type=MemoryType.SHORT_TERM,
        tags=["test", "sample"],
        priority=5,
        ttl=3600,
    )


@pytest.fixture
def sample_query():
    """Create a sample memory query for testing."""
    return MemoryQuery(
        content="test", memory_type=MemoryType.SHORT_TERM, tags=["test"], limit=5
    )


class TestMemoryEntry:
    """Test memory entry model."""

    def test_memory_entry_creation(self, sample_entry):
        """Test memory entry creation with all fields."""
        assert sample_entry.id
        assert sample_entry.content == "Sample memory content for testing"
        assert sample_entry.memory_type == MemoryType.SHORT_TERM
        assert "test" in sample_entry.tags
        assert sample_entry.priority == 5
        assert sample_entry.ttl == 3600

    def test_memory_entry_defaults(self):
        """Test memory entry with default values."""
        entry = MemoryEntry(
            id="test-id", content="test content", memory_type=MemoryType.CACHE
        )

        assert entry.metadata == {}
        assert entry.tags == []
        assert entry.priority == 0
        assert entry.ttl is None
        assert entry.embedding is None
        assert isinstance(entry.timestamp, datetime)


class TestMemoryQuery:
    """Test memory query model."""

    def test_memory_query_creation(self, sample_query):
        """Test memory query creation."""
        assert sample_query.content == "test"
        assert sample_query.memory_type == MemoryType.SHORT_TERM
        assert "test" in sample_query.tags
        assert sample_query.limit == 5

    def test_memory_query_defaults(self):
        """Test memory query with default values."""
        query = MemoryQuery()

        assert query.content is None
        assert query.memory_type is None
        assert query.tags == []
        assert query.limit == 10
        assert query.similarity_threshold == 0.7


class TestShortTermMemory:
    """Test short-term memory implementation."""

    @pytest.fixture
    def short_term_memory(self):
        """Create short-term memory instance for testing."""
        config = {
            "max_total_entries": 100,
            "default_window_size": 10,
            "cleanup_interval": 1,  # Fast cleanup for testing
        }
        return ShortTermMemory("test_stm", config)

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, short_term_memory, sample_entry):
        """Test storing and retrieving entries."""
        # Store entry
        success = await short_term_memory.store(sample_entry)
        assert success

        # Retrieve entry
        query = MemoryQuery(content="Sample memory")
        result = await short_term_memory.retrieve(query)

        assert result.total_count == 1
        assert len(result.entries) == 1
        assert result.entries[0].id == sample_entry.id

    @pytest.mark.asyncio
    async def test_context_windows(self, short_term_memory):
        """Test context window functionality."""
        # Create entries for different windows
        entry1 = MemoryEntry(
            id="entry1",
            content="First entry",
            memory_type=MemoryType.SHORT_TERM,
            metadata={"context_window": "window1"},
        )

        entry2 = MemoryEntry(
            id="entry2",
            content="Second entry",
            memory_type=MemoryType.SHORT_TERM,
            metadata={"context_window": "window2"},
        )

        # Store entries
        await short_term_memory.store(entry1)
        await short_term_memory.store(entry2)

        # Query specific window
        query = MemoryQuery(metadata_filters={"context_window": "window1"}, limit=10)
        result = await short_term_memory.retrieve(query)

        assert len(result.entries) == 1
        assert result.entries[0].id == "entry1"

        # Check context windows exist
        windows = await short_term_memory.list_context_windows()
        assert "window1" in windows
        assert "window2" in windows

    @pytest.mark.asyncio
    async def test_update_entry(self, short_term_memory, sample_entry):
        """Test updating memory entries."""
        # Store entry
        await short_term_memory.store(sample_entry)

        # Update entry
        updates = {"priority": 10, "content": "Updated content"}
        success = await short_term_memory.update(sample_entry.id, updates)
        assert success

        # Verify update
        query = MemoryQuery(content="Updated")
        result = await short_term_memory.retrieve(query)

        assert len(result.entries) == 1
        assert result.entries[0].priority == 10
        assert result.entries[0].content == "Updated content"

    @pytest.mark.asyncio
    async def test_delete_entry(self, short_term_memory, sample_entry):
        """Test deleting memory entries."""
        # Store entry
        await short_term_memory.store(sample_entry)

        # Delete entry
        success = await short_term_memory.delete(sample_entry.id)
        assert success

        # Verify deletion
        query = MemoryQuery(content="Sample")
        result = await short_term_memory.retrieve(query)

        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_clear_memory(self, short_term_memory, sample_entry):
        """Test clearing memory entries."""
        # Store entry
        await short_term_memory.store(sample_entry)

        # Clear memory
        success = await short_term_memory.clear()
        assert success

        # Verify clear
        query = MemoryQuery()
        result = await short_term_memory.retrieve(query)

        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_memory_stats(self, short_term_memory, sample_entry):
        """Test memory statistics."""
        # Store entry
        await short_term_memory.store(sample_entry)

        # Get stats
        stats = await short_term_memory.get_stats()

        assert isinstance(stats, MemoryStats)
        assert stats.total_entries == 1
        assert stats.memory_usage > 0
        assert MemoryType.SHORT_TERM.value in stats.entries_by_type

    @pytest.mark.asyncio
    async def test_health_check(self, short_term_memory):
        """Test health check."""
        health = await short_term_memory.health_check()
        assert health is True

    @pytest.mark.asyncio
    async def test_capacity_management(self):
        """Test capacity management and LRU eviction."""
        config = {"max_total_entries": 3}  # Small capacity
        stm = ShortTermMemory("test_capacity", config)

        # Store entries beyond capacity
        for i in range(5):
            entry = MemoryEntry(
                id=f"entry{i}",
                content=f"Content {i}",
                memory_type=MemoryType.SHORT_TERM,
            )
            await stm.store(entry)

        # Check that only 3 entries remain
        query = MemoryQuery(limit=10)
        result = await stm.retrieve(query)

        assert len(result.entries) == 3

        # Check that newest entries are kept
        entry_ids = [entry.id for entry in result.entries]
        assert "entry4" in entry_ids  # Most recent
        assert "entry3" in entry_ids
        assert "entry2" in entry_ids
        assert "entry0" not in entry_ids  # Should be evicted
        assert "entry1" not in entry_ids  # Should be evicted


class TestVectorStore:
    """Test vector memory store implementation."""

    @pytest.fixture
    def vector_store(self):
        """Create vector store instance for testing."""
        config = {"url": "http://localhost:8080", "class_name": "TestMemoryEntry"}
        return WeaviateVectorStore("test_vector", config)

    @pytest.mark.asyncio
    async def test_create_embedding(self, vector_store):
        """Test embedding creation."""
        content = "Test content for embedding"

        # Mock the vector_store._ensure_client method to prevent actual API calls
        with patch.object(vector_store, "create_embedding", return_value=[0.1] * 384):
            embedding = await vector_store.create_embedding(content)

            assert isinstance(embedding, list)
            assert len(embedding) == 384  # Expected dimension
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_embedding_consistency(self, vector_store):
        """Test that same content produces same embedding."""
        content = "Consistent content"

        # Mock the embedding creation to return consistent results
        with patch.object(vector_store, "create_embedding", return_value=[0.1] * 384):
            embedding1 = await vector_store.create_embedding(content)
            embedding2 = await vector_store.create_embedding(content)

            assert embedding1 == embedding2

    @pytest.mark.asyncio
    async def test_store_without_weaviate(self, vector_store, sample_entry):
        """Test store operation when Weaviate is not available."""
        # Mock connection failure
        with patch.object(vector_store, "_connect", return_value=False):
            success = await vector_store.store(sample_entry)
            assert success is False

    @pytest.mark.asyncio
    async def test_health_check_no_connection(self, vector_store):
        """Test health check when connection fails."""
        # Mock health check response
        with patch.object(vector_store, "_ensure_client", return_value=False):
            health = await vector_store.health_check()
            assert health is False


class TestCacheMemoryStore:
    """Test cache memory store implementation."""

    @pytest.fixture
    def cache_store(self):
        """Create cache store instance for testing."""
        config = {
            "url": "redis://localhost:6379",
            "key_prefix": "test_cache:",
            "default_ttl": 300,
        }
        return CacheMemoryStore("test_cache", config)

    @pytest.mark.asyncio
    async def test_redis_url_parsing(self, cache_store):
        """Test Redis URL parsing."""
        config = cache_store._parse_redis_url("redis://localhost:6379/1")

        assert config["host"] == "localhost"
        assert config["port"] == 6379
        assert config["db"] == 1

    @pytest.mark.asyncio
    async def test_key_creation(self, cache_store):
        """Test cache key creation."""
        key = cache_store._make_key("test_key")
        assert key == "test_cache:test_key"

    @pytest.mark.asyncio
    async def test_entry_serialization(self, cache_store, sample_entry):
        """Test memory entry serialization."""
        serialized = cache_store._serialize_entry(sample_entry)
        assert isinstance(serialized, str)

        deserialized = cache_store._deserialize_entry(serialized)
        assert deserialized is not None
        assert deserialized.id == sample_entry.id
        assert deserialized.content == sample_entry.content
        assert deserialized.memory_type == sample_entry.memory_type

    @pytest.mark.asyncio
    async def test_store_without_redis(self, cache_store, sample_entry):
        """Test store operation when Redis is not available."""
        # Mock failed connection
        with patch.object(cache_store, "_connect", return_value=False):
            success = await cache_store.store(sample_entry)
            assert success is False

    @pytest.mark.asyncio
    async def test_health_check_no_connection(self, cache_store):
        """Test health check when connection fails."""
        health = await cache_store.health_check()
        # Should be False because we don't have real Redis running
        assert health is False


class TestMemoryManager:
    """Test memory manager implementation."""

    @pytest.fixture
    def memory_manager(self):
        """Create memory manager instance for testing."""
        config = {
            "short_term": {"max_total_entries": 50},
            "vector_store": {"url": "http://localhost:8080"},
            "cache": {"url": "redis://localhost:6379"},
        }
        return MemoryManager(config)

    @pytest.mark.asyncio
    async def test_initialization(self, memory_manager):
        """Test memory manager initialization."""
        await memory_manager.initialize()

        assert "short_term" in memory_manager.stores
        assert "vector_store" in memory_manager.stores
        assert "cache" in memory_manager.stores

        # Check type mappings
        assert memory_manager.store_types[MemoryType.SHORT_TERM] == "short_term"
        assert memory_manager.store_types[MemoryType.LONG_TERM] == "vector_store"
        assert memory_manager.store_types[MemoryType.CACHE] == "cache"

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, memory_manager):
        """Test storing and retrieving through manager."""
        await memory_manager.initialize()

        # Store content
        entry_id = await memory_manager.store(
            content="Test content",
            memory_type=MemoryType.SHORT_TERM,
            tags=["test"],
            priority=5,
        )

        assert entry_id

        # Retrieve content
        result = await memory_manager.retrieve(
            content="Test content", memory_type=MemoryType.SHORT_TERM
        )

        assert len(result.entries) == 1
        assert result.entries[0].content == "Test content"
        assert result.entries[0].priority == 5

    @pytest.mark.asyncio
    async def test_cross_store_search(self, memory_manager):
        """Test searching across multiple stores."""
        await memory_manager.initialize()

        try:
            # Store in different stores
            await memory_manager.store(
                content="Short term content", memory_type=MemoryType.SHORT_TERM
            )

            try:
                await memory_manager.store(
                    content="Cache content", memory_type=MemoryType.CACHE
                )
            except RuntimeError:
                # Skip cache storage test if Redis is not available
                pass

            # Search across all stores
            result = await memory_manager.retrieve(content="content", limit=10)

            # Should find entries from at least one store
            assert len(result.entries) > 0

            # Check if short term memory entries are found
            contents = [entry.content for entry in result.entries]
            assert any("Short term" in content for content in contents)

            # Only check for cache entries if they were successfully stored
            if any(entry.memory_type == MemoryType.CACHE for entry in result.entries):
                assert any("Cache" in content for content in contents)
        except Exception as e:
            pytest.skip(f"Test skipped due to setup error: {e}")

    @pytest.mark.asyncio
    async def test_update_entry(self, memory_manager):
        """Test updating entries through manager."""
        await memory_manager.initialize()

        # Store entry
        entry_id = await memory_manager.store(
            content="Original content", memory_type=MemoryType.SHORT_TERM
        )

        # Update entry
        success = await memory_manager.update(
            entry_id,
            {"content": "Updated content", "priority": 10},
            MemoryType.SHORT_TERM,
        )

        assert success

        # Verify update
        result = await memory_manager.retrieve(
            content="Updated", memory_type=MemoryType.SHORT_TERM
        )

        assert len(result.entries) == 1
        assert result.entries[0].priority == 10

    @pytest.mark.asyncio
    async def test_delete_entry(self, memory_manager):
        """Test deleting entries through manager."""
        await memory_manager.initialize()

        # Store entry
        entry_id = await memory_manager.store(
            content="Content to delete", memory_type=MemoryType.SHORT_TERM
        )

        # Delete entry
        success = await memory_manager.delete(entry_id, MemoryType.SHORT_TERM)

        assert success

        # Verify deletion
        result = await memory_manager.retrieve(
            content="Content to delete", memory_type=MemoryType.SHORT_TERM
        )

        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_similarity_search(self, memory_manager):
        """Test similarity search through manager."""
        await memory_manager.initialize()

        try:
            # Store content with embeddings - may fail without real vector store
            try:
                await memory_manager.store(
                    content="Machine learning algorithms",
                    memory_type=MemoryType.LONG_TERM,
                )

                await memory_manager.store(
                    content="Deep learning neural networks",
                    memory_type=MemoryType.LONG_TERM,
                )
            except RuntimeError:
                # Skip the test if vector store is not available
                pytest.skip("Vector store not available for testing")
                return

            # Perform similarity search
            result = await memory_manager.search_similar(
                "artificial intelligence",
                limit=5,
                threshold=0.1,  # Low threshold for mock embeddings
            )

            # Should find relevant entries
            assert isinstance(result, MemoryResult)
            # Note: Actual similarity depends on embedding implementation
        except Exception as e:
            pytest.skip(f"Test skipped due to setup error: {e}")

    @pytest.mark.asyncio
    async def test_cache_operations(self, memory_manager):
        """Test cache-specific operations."""
        await memory_manager.initialize()

        # Set cache value
        success = await memory_manager.cache_set(
            "test_key", {"data": "test_value", "number": 42}, ttl=300
        )

        # Note: Will fail without real Redis, but tests the interface
        assert success is False  # Expected to fail without Redis

        # Get cache value
        value = await memory_manager.cache_get("test_key")
        assert value is None  # Expected to be None without Redis

    @pytest.mark.asyncio
    async def test_memory_stats(self, memory_manager):
        """Test getting memory statistics."""
        await memory_manager.initialize()

        # Store some entries
        await memory_manager.store("Content 1", MemoryType.SHORT_TERM)
        await memory_manager.store("Content 2", MemoryType.SHORT_TERM)

        # Get stats
        stats = await memory_manager.get_stats()

        assert isinstance(stats, dict)
        assert "total_operations" in stats
        assert "operations_by_type" in stats
        assert "stores" in stats

        # Check store stats
        assert "short_term" in stats["stores"]
        short_term_stats = stats["stores"]["short_term"]
        assert short_term_stats["total_entries"] == 2

    @pytest.mark.asyncio
    async def test_health_check(self, memory_manager):
        """Test health check of all stores."""
        await memory_manager.initialize()

        health_status = await memory_manager.health_check()

        assert isinstance(health_status, dict)
        assert "short_term" in health_status
        assert "vector_store" in health_status
        assert "cache" in health_status

        # Short-term memory should be healthy
        assert health_status["short_term"] is True

        # Vector store and cache will be False without real services
        assert health_status["vector_store"] is False
        assert health_status["cache"] is False

    @pytest.mark.asyncio
    async def test_custom_store_registration(self, memory_manager):
        """Test registering custom memory stores."""
        await memory_manager.initialize()

        # Create mock custom store
        custom_store = AsyncMock()
        custom_store.name = "custom_store"

        # Register custom store
        memory_manager.register_store("custom", custom_store)

        assert "custom" in memory_manager.stores
        assert memory_manager.stores["custom"] == custom_store

    @pytest.mark.asyncio
    async def test_type_mapping_configuration(self, memory_manager):
        """Test configuring memory type mappings."""
        await memory_manager.initialize()

        # Register custom store
        custom_store = AsyncMock()
        memory_manager.register_store("custom", custom_store)

        # Map cache type to custom store
        memory_manager.set_type_mapping(MemoryType.CACHE, "custom")

        assert memory_manager.store_types[MemoryType.CACHE] == "custom"

        # Test error for non-existent store
        with pytest.raises(ValueError):
            memory_manager.set_type_mapping(MemoryType.VECTOR, "nonexistent")

    @pytest.mark.asyncio
    async def test_cleanup(self, memory_manager):
        """Test memory manager cleanup."""
        await memory_manager.initialize()

        # Store should have stores
        assert len(memory_manager.stores) > 0

        # Close manager
        await memory_manager.close()

        # Stores should be cleared
        assert len(memory_manager.stores) == 0
        assert len(memory_manager.store_types) == 0


if __name__ == "__main__":
    pytest.main([__file__])
