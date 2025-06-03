"""Unit tests for cache store implementation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from agentic_workflow.memory import (
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryType,
    RedisCacheStore,
)
from agentic_workflow.utils.serialization import memory_entry_to_dict, serialize_to_json


class TestRedisCacheStore:
    """Tests for the RedisCacheStore implementation."""

    @pytest.fixture
    def mock_redis_client(self) -> AsyncMock:
        """Create a mock Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.setex = AsyncMock(return_value=True)
        client.keys = AsyncMock(return_value=[])
        client.delete = AsyncMock(return_value=True)
        client.sadd = AsyncMock(return_value=1)
        client.srem = AsyncMock(return_value=1)
        client.smembers = AsyncMock(return_value=[])
        client.exists = AsyncMock(return_value=1)
        client.expire = AsyncMock(return_value=True)
        client.scard = AsyncMock(return_value=0)
        client.info = AsyncMock(return_value={"used_memory": 1024})
        client.hset = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def mock_redis_manager(self, mock_redis_client: AsyncMock) -> AsyncMock:
        """Create a mock Redis connection manager."""
        manager = AsyncMock()
        manager.client = mock_redis_client
        manager.ensure_connected = AsyncMock(return_value=True)
        manager.health_check = AsyncMock(return_value=True)
        manager.disconnect = AsyncMock()
        return manager

    @pytest.fixture
    def redis_cache_store(self, mock_redis_manager: AsyncMock) -> RedisCacheStore:
        """Create a RedisCacheStore with mocked Redis manager."""
        with patch(
            "agentic_workflow.memory.cache_store.RedisConnectionManager",
            return_value=mock_redis_manager,
        ):
            store = RedisCacheStore(
                "test_cache",
                {
                    "url": "redis://localhost:6379/0",
                    "key_prefix": "test:",
                },
            )
            store.redis = mock_redis_manager
            return store

    @pytest.fixture
    def sample_entry(self) -> MemoryEntry:
        """Create a sample memory entry."""
        return MemoryEntry(
            id="test-123",
            content="Test content",
            memory_type=MemoryType.CACHE,
            metadata={"test": "value"},
            tags=["test", "cache"],
            ttl=300,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_entry(
        self,
        redis_cache_store: RedisCacheStore,
        sample_entry: MemoryEntry,
        mock_redis_client: AsyncMock,
    ) -> None:
        """Test storing a memory entry."""
        # Mock serialization
        entry_dict = memory_entry_to_dict(sample_entry)
        serialized_data = serialize_to_json(entry_dict)

        success = await redis_cache_store.store(sample_entry)

        assert success is True

        # Verify proper keys were used
        entry_key = f"entry:{sample_entry.id}"
        metadata_key = f"metadata:{sample_entry.id}"
        type_key = f"type:{sample_entry.memory_type.value}"

        # Check if TTL is set, use appropriate assertion
        if sample_entry.ttl is not None:
            mock_redis_client.setex.assert_called_once_with(
                entry_key, sample_entry.ttl, serialized_data
            )
        else:
            mock_redis_client.set.assert_called_once_with(entry_key, serialized_data)

        # Check metadata was stored
        mock_redis_client.hset.assert_called_once_with(
            metadata_key, mapping=sample_entry.metadata
        )

        # Check that type index was updated
        mock_redis_client.sadd.assert_any_call(type_key, sample_entry.id)

        # Check that tag indices were updated
        for tag in sample_entry.tags:
            tag_key = f"tag:{tag}"
            mock_redis_client.sadd.assert_any_call(tag_key, sample_entry.id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_entry_with_ttl(
        self,
        redis_cache_store: RedisCacheStore,
        sample_entry: MemoryEntry,
        mock_redis_client: AsyncMock,
    ) -> None:
        """Test storing a memory entry with TTL."""
        # Set TTL
        sample_entry.ttl = 60
        entry_dict = memory_entry_to_dict(sample_entry)
        serialized_data = serialize_to_json(entry_dict)

        success = await redis_cache_store.store(sample_entry)

        assert success is True

        # Check that setex was called with TTL
        entry_key = f"entry:{sample_entry.id}"
        mock_redis_client.setex.assert_called_once_with(entry_key, 60, serialized_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_entry_connection_failure(
        self, redis_cache_store: RedisCacheStore, sample_entry: MemoryEntry
    ) -> None:
        """Test storing when connection fails."""
        # Mock connection failure
        redis_cache_store.redis.ensure_connected = AsyncMock(return_value=False)

        success = await redis_cache_store.store(sample_entry)

        assert success is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_basic(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test basic retrieval."""
        # Set up mock data
        mock_redis_client.keys.return_value = [
            b"entry:test-123",
            b"entry:test-456",
        ]

        # Set up mock get responses for each key
        entry1 = MemoryEntry(
            id="test-123",
            content="Test content 1",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        entry2 = MemoryEntry(
            id="test-456",
            content="Test content 2",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        mock_redis_client.get.side_effect = [
            serialize_to_json(memory_entry_to_dict(entry1)),
            serialize_to_json(memory_entry_to_dict(entry2)),
        ]

        # Create query
        query = MemoryQuery(limit=10)

        # Execute retrieval
        result = await redis_cache_store.retrieve(query)

        # Check result
        assert isinstance(result, MemoryResult)
        assert len(result.entries) == 2
        assert result.total_count == 2
        assert result.entries[0].id in ["test-123", "test-456"]
        assert result.entries[1].id in ["test-123", "test-456"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_by_memory_type(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test retrieval by memory type."""
        # Set up mock data for type filter
        mock_redis_client.smembers.return_value = [b"test-123", b"test-456"]

        # Set up mock get responses for each key
        entry1 = MemoryEntry(
            id="test-123",
            content="Test content 1",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        entry2 = MemoryEntry(
            id="test-456",
            content="Test content 2",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        mock_redis_client.get.side_effect = [
            serialize_to_json(memory_entry_to_dict(entry1)),
            serialize_to_json(memory_entry_to_dict(entry2)),
        ]

        # Create query with memory type
        query = MemoryQuery(memory_type=MemoryType.CACHE, limit=10)

        # Execute retrieval
        result = await redis_cache_store.retrieve(query)

        # Check result
        assert isinstance(result, MemoryResult)
        assert len(result.entries) == 2
        assert result.total_count == 2
        # Verify type set was queried
        mock_redis_client.smembers.assert_called_with("type:cache")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_by_tags(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test retrieval by tags."""
        # Set up mock data for tag filter
        mock_redis_client.smembers.return_value = [b"test-123"]

        # Set up mock get response
        entry = MemoryEntry(
            id="test-123",
            content="Test content 1",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
            tags=["test"],
        )

        mock_redis_client.get.return_value = serialize_to_json(
            memory_entry_to_dict(entry)
        )

        # Create query with tag
        query = MemoryQuery(tags=["test"], limit=10)

        # Execute retrieval
        result = await redis_cache_store.retrieve(query)

        # Check result
        assert isinstance(result, MemoryResult)
        assert len(result.entries) == 1
        assert result.total_count == 1
        assert result.entries[0].id == "test-123"
        # Verify tag set was queried
        mock_redis_client.smembers.assert_called_with("tag:test")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_entry(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test updating a memory entry."""
        # Set up mock data
        entry = MemoryEntry(
            id="test-123",
            content="Original content",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        mock_redis_client.get.return_value = serialize_to_json(
            memory_entry_to_dict(entry)
        )

        # Mock store method to verify updated entry is stored
        with patch.object(
            redis_cache_store, "store", AsyncMock(return_value=True)
        ) as mock_store:

            success = await redis_cache_store.update(
                "test-123", {"content": "Updated content", "priority": 10}
            )

            assert success is True
            mock_store.assert_called_once()
            # Check the updated entry
            called_entry = mock_store.call_args[0][0]
            assert called_entry.content == "Updated content"
            assert called_entry.priority == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_entry(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test deleting a memory entry."""
        # Set up mock data
        entry = MemoryEntry(
            id="test-123",
            content="Test content",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
            tags=["test"],
        )

        # Set up mock responses
        mock_redis_client.get.return_value = serialize_to_json(
            memory_entry_to_dict(entry)
        )
        mock_redis_client.srem.return_value = 1
        mock_redis_client.delete.return_value = 1

        success = await redis_cache_store.delete("test-123")

        assert success is True
        # Verify key was deleted
        mock_redis_client.delete.assert_any_call("entry:test-123")
        mock_redis_client.delete.assert_any_call("metadata:test-123")
        # Verify type index was updated
        mock_redis_client.srem.assert_any_call("type:cache", "test-123")
        # Verify tag index was updated
        mock_redis_client.srem.assert_any_call("tag:test", "test-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clear_all(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test clearing all entries."""
        # Set up mock keys for different key types
        mock_redis_client.keys.side_effect = [
            [b"entry:1", b"entry:2"],  # Entry keys
            [b"metadata:1", b"metadata:2"],  # Metadata keys
            [b"type:cache", b"type:short_term"],  # Type keys
            [b"tag:test", b"tag:important"],  # Tag keys
        ]

        success = await redis_cache_store.clear()

        assert success is True
        # Verify all key types were deleted in bulk
        assert mock_redis_client.delete.call_count == 4  # One call per key type
        mock_redis_client.delete.assert_any_call(b"entry:1", b"entry:2")
        mock_redis_client.delete.assert_any_call(b"metadata:1", b"metadata:2")
        mock_redis_client.delete.assert_any_call(b"type:cache", b"type:short_term")
        mock_redis_client.delete.assert_any_call(b"tag:test", b"tag:important")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clear_by_type(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test clearing entries by type."""
        # Set up mock data
        mock_redis_client.smembers.return_value = [b"test-123", b"test-456"]
        mock_redis_client.get.side_effect = [
            serialize_to_json(
                memory_entry_to_dict(
                    MemoryEntry(
                        id="test-123",
                        content="Test content 1",
                        memory_type=MemoryType.CACHE,
                        metadata={},
                        timestamp=datetime.now(timezone.utc),
                        tags=["test"],
                    )
                )
            ),
            serialize_to_json(
                memory_entry_to_dict(
                    MemoryEntry(
                        id="test-456",
                        content="Test content 2",
                        memory_type=MemoryType.CACHE,
                        metadata={},
                        timestamp=datetime.now(timezone.utc),
                        tags=["test"],
                    )
                )
            ),
        ]

        success = await redis_cache_store.clear(MemoryType.CACHE)

        assert success is True
        # Verify entries were deleted individually (since we need to get their metadata)
        assert (
            mock_redis_client.delete.call_count == 5
        )  # 2 entries + 2 metadata + 1 type key
        # Verify type key was deleted
        mock_redis_client.delete.assert_any_call("type:cache")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test getting cache statistics."""
        # Set up mock data
        mock_redis_client.keys.side_effect = [
            [b"entry:1", b"entry:2"],  # Entry keys
            [b"type:cache", b"type:short_term"],  # Type keys
        ]
        mock_redis_client.scard.return_value = 5

        # Set hit rate factors
        redis_cache_store.total_gets = 10
        redis_cache_store.cache_hits = 7

        stats = await redis_cache_store.get_stats()

        assert isinstance(stats, MemoryStats)
        assert stats.total_entries == 2
        assert stats.hit_rate == 0.7
        assert stats.memory_usage == 1024
        assert "cache" in stats.entries_by_type
        assert "short_term" in stats.entries_by_type
        assert stats.entries_by_type["cache"] == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_set(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test setting a cache value."""
        # String value
        success = await redis_cache_store.set("test-key", "test-value")

        assert success is True
        mock_redis_client.set.assert_called_with("test-key", "test-value")
        assert redis_cache_store.total_sets == 1

        # Reset mock for next test
        mock_redis_client.set.reset_mock()

        # Object value
        with patch(
            "agentic_workflow.memory.cache_store.serialize_to_json",
            return_value='{"key":"value"}',
        ):
            success = await redis_cache_store.set("test-key2", {"key": "value"})

            assert success is True
            mock_redis_client.set.assert_called_with("test-key2", '{"key":"value"}')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_set_with_ttl(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test setting a cache value with TTL."""
        success = await redis_cache_store.set("test-key", "test-value", ttl=60)

        assert success is True
        mock_redis_client.setex.assert_called_with("test-key", 60, "test-value")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_get(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test getting a cache value."""
        # Set up mock data
        mock_redis_client.get.return_value = "test-value"

        value = await redis_cache_store.get("test-key")

        assert value == "test-value"
        mock_redis_client.get.assert_called_with("test-key")
        assert redis_cache_store.cache_hits == 1
        assert redis_cache_store.total_gets == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_get_miss(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test cache miss."""
        # Set up mock data
        mock_redis_client.get.return_value = None

        value = await redis_cache_store.get("test-key")

        assert value is None
        assert redis_cache_store.cache_misses == 1
        assert redis_cache_store.total_gets == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_exists(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test checking if a key exists."""
        # Set up mock data
        mock_redis_client.exists.return_value = 1

        exists = await redis_cache_store.exists("test-key")

        assert exists is True
        mock_redis_client.exists.assert_called_with("test-key")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_expire(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test setting expiration on a key."""
        # Set up mock data
        mock_redis_client.expire.return_value = True

        success = await redis_cache_store.expire("test-key", 60)

        assert success is True
        mock_redis_client.expire.assert_called_with("test-key", 60)
