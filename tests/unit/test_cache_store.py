"""Unit tests for cache store implementation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_workflow.memory import (
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryType,
    RedisCacheStore,
)


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
        return client

    @pytest.fixture
    def mock_redis_manager(self, mock_redis_client: AsyncMock) -> AsyncMock:
        """Create a mock Redis connection manager."""
        manager = AsyncMock()
        manager.client = mock_redis_client
        manager.ensure_connected = AsyncMock(return_value=True)
        manager.health_check = AsyncMock(return_value=True)
        manager.disconnect = AsyncMock()

        # This is critical - we need to actually prefix keys in our mock
        def make_key(key: str) -> str:
            return f"test:{key}"

        manager.make_key = Mock(side_effect=make_key)
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
            # Ensure the mock is properly set
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
    def test_initialization(self) -> None:
        """Test cache store initialization."""
        with patch("agentic_workflow.memory.cache_store.RedisConnectionManager"):
            store = RedisCacheStore(
                "test_cache",
                {
                    "url": "redis://localhost:6379/0",
                    "key_prefix": "test:",
                },
            )

            assert store.name == "test_cache"
            assert store.config["url"] == "redis://localhost:6379/0"
            assert store.config["key_prefix"] == "test:"
            assert store.total_sets == 0
            assert store.total_gets == 0
            assert store.cache_hits == 0
            assert store.cache_misses == 0

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
        serialized_data = '{"mocked":"json"}'

        with (
            patch(
                "agentic_workflow.memory.cache_store.memory_entry_to_dict",
                return_value={"test": "data"},
            ),
            patch(
                "agentic_workflow.memory.cache_store.serialize_to_json",
                return_value=serialized_data,
            ),
        ):

            success = await redis_cache_store.store(sample_entry)

            assert success is True

            # Verify proper keys were used
            entry_key = f"test:entry:{sample_entry.id}"

            # Check if TTL is set, use appropriate assertion
            if sample_entry.ttl is not None:
                mock_redis_client.setex.assert_called_once_with(
                    entry_key, sample_entry.ttl, serialized_data
                )
            else:
                mock_redis_client.set.assert_called_once_with(
                    entry_key, serialized_data
                )

            # Check that type index was updated
            type_key = "test:type:cache"
            mock_redis_client.sadd.assert_any_call(type_key, sample_entry.id)

            # Check that tag indices were updated
            for tag in sample_entry.tags:
                tag_key = f"test:tag:{tag}"
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
        serialized_data = '{"mocked":"json"}'

        # Mock serialization
        with (
            patch(
                "agentic_workflow.memory.cache_store.memory_entry_to_dict",
                return_value={"test": "data"},
            ),
            patch(
                "agentic_workflow.memory.cache_store.serialize_to_json",
                return_value=serialized_data,
            ),
        ):

            success = await redis_cache_store.store(sample_entry)

            assert success is True

            # Check that setex was called with TTL
            entry_key = f"test:entry:{sample_entry.id}"
            mock_redis_client.setex.assert_called_once_with(
                entry_key, 60, serialized_data
            )

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
            b"test:entry:test-123",
            b"test:entry:test-456",
        ]

        # Set up mock get responses for each key
        mock_redis_client.get.side_effect = [
            '{"content":"Test content 1","memory_type":"cache","metadata":{},"timestamp":"2023-05-23T12:00:00+00:00","tags":[]}',
            '{"content":"Test content 2","memory_type":"cache","metadata":{},"timestamp":"2023-05-23T12:00:00+00:00","tags":[]}',
        ]

        # Create query
        query = MemoryQuery(limit=10)

        # Execute retrieval
        with patch(
            "agentic_workflow.memory.cache_store.dict_to_memory_entry",
            side_effect=[
                MemoryEntry(
                    id="test-123",
                    content="Test content 1",
                    memory_type=MemoryType.CACHE,
                    metadata={},
                    timestamp=datetime.now(timezone.utc),
                ),
                MemoryEntry(
                    id="test-456",
                    content="Test content 2",
                    memory_type=MemoryType.CACHE,
                    metadata={},
                    timestamp=datetime.now(timezone.utc),
                ),
            ],
        ):

            result = await redis_cache_store.retrieve(query)

            # Check result
            assert isinstance(result, MemoryResult)
            assert len(result.entries) == 2
            assert result.total_count == 2
            assert result.entries[0].id in ["test-123", "test-456"]
            assert result.entries[1].id in ["test-123", "test-456"]
            assert redis_cache_store.total_gets == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_by_memory_type(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test retrieval by memory type."""
        # Set up mock data for type filter
        mock_redis_client.smembers.return_value = [b"test-123", b"test-456"]

        # Set up mock get responses for each key
        mock_redis_client.get.side_effect = [
            '{"content":"Test content 1","memory_type":"cache","metadata":{},"timestamp":"2023-05-23T12:00:00+00:00","tags":[]}',
            '{"content":"Test content 2","memory_type":"cache","metadata":{},"timestamp":"2023-05-23T12:00:00+00:00","tags":[]}',
        ]

        # Create query with memory type
        query = MemoryQuery(memory_type=MemoryType.CACHE, limit=10)

        # Execute retrieval
        with patch(
            "agentic_workflow.memory.cache_store.dict_to_memory_entry",
            side_effect=[
                MemoryEntry(
                    id="test-123",
                    content="Test content 1",
                    memory_type=MemoryType.CACHE,
                    metadata={},
                    timestamp=datetime.now(timezone.utc),
                ),
                MemoryEntry(
                    id="test-456",
                    content="Test content 2",
                    memory_type=MemoryType.CACHE,
                    metadata={},
                    timestamp=datetime.now(timezone.utc),
                ),
            ],
        ):

            result = await redis_cache_store.retrieve(query)

            # Check result
            assert isinstance(result, MemoryResult)
            assert len(result.entries) == 2
            assert result.total_count == 2
            # Verify type set was queried
            mock_redis_client.smembers.assert_called_with("test:type:cache")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_by_tags(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test retrieval by tags."""
        # Set up mock data for tag filter
        mock_redis_client.smembers.return_value = [b"test-123"]

        # Set up mock get response
        mock_redis_client.get.return_value = '{"content":"Test content 1","memory_type":"cache","metadata":{},"timestamp":"2023-05-23T12:00:00+00:00","tags":["test"]}'

        # Create query with tag
        query = MemoryQuery(tags=["test"], limit=10)

        # Execute retrieval
        with patch(
            "agentic_workflow.memory.cache_store.dict_to_memory_entry",
            return_value=MemoryEntry(
                id="test-123",
                content="Test content 1",
                memory_type=MemoryType.CACHE,
                metadata={},
                timestamp=datetime.now(timezone.utc),
                tags=["test"],
            ),
        ):

            result = await redis_cache_store.retrieve(query)

            # Check result
            assert isinstance(result, MemoryResult)
            assert len(result.entries) == 1
            assert result.total_count == 1
            assert result.entries[0].id == "test-123"
            # Verify tag set was queried
            mock_redis_client.smembers.assert_called_with("test:tag:test")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_entry(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test updating a memory entry."""
        # Set up mock data
        entry_json = '{"id":"test-123","content":"Original content","memory_type":"cache","metadata":{},"timestamp":"2023-05-23T12:00:00+00:00","tags":[]}'
        mock_redis_client.get.return_value = entry_json

        # Mock dict_to_memory_entry to return a proper entry
        entry = MemoryEntry(
            id="test-123",
            content="Original content",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )

        # Mock store method to verify updated entry is stored
        with (
            patch(
                "agentic_workflow.memory.cache_store.dict_to_memory_entry",
                return_value=entry,
            ),
            patch.object(
                redis_cache_store, "store", AsyncMock(return_value=True)
            ) as mock_store,
        ):

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
        entry_json = '{"id":"test-123","content":"Test content","memory_type":"cache","metadata":{},"timestamp":"2023-05-23T12:00:00+00:00","tags":["test"]}'
        mock_redis_client.get.return_value = entry_json

        # Execute delete
        entry = MemoryEntry(
            id="test-123",
            content="Test content",
            memory_type=MemoryType.CACHE,
            metadata={},
            timestamp=datetime.now(timezone.utc),
            tags=["test"],
        )

        with patch(
            "agentic_workflow.memory.cache_store.dict_to_memory_entry",
            return_value=entry,
        ):
            success = await redis_cache_store.delete("test-123")

            assert success is True
            # Verify key was deleted
            mock_redis_client.delete.assert_called_once_with("test:entry:test-123")
            # Verify type index was updated
            mock_redis_client.srem.assert_any_call("test:type:cache", "test-123")
            # Verify tag index was updated
            mock_redis_client.srem.assert_any_call("test:tag:test", "test-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clear_all(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test clearing all entries."""
        # Set up mock keys
        mock_redis_client.keys.return_value = [
            b"test:entry:1",
            b"test:type:cache",
            b"test:tag:test",
        ]

        success = await redis_cache_store.clear()

        assert success is True
        # Verify all keys were deleted
        mock_redis_client.delete.assert_called_once_with(
            *[b"test:entry:1", b"test:type:cache", b"test:tag:test"]
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clear_by_type(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test clearing entries by type."""
        # Set up mock data
        mock_redis_client.smembers.return_value = [b"test-123", b"test-456"]

        # Mock delete method to verify entries are deleted
        with patch.object(
            redis_cache_store, "delete", AsyncMock(return_value=True)
        ) as mock_delete:

            success = await redis_cache_store.clear(MemoryType.CACHE)

            assert success is True
            assert mock_delete.call_count == 2
            mock_delete.assert_any_call("test-123")
            mock_delete.assert_any_call("test-456")
            # Verify type key was deleted
            mock_redis_client.delete.assert_called_once_with("test:type:cache")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_stats(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test getting cache statistics."""
        # Set up mock data
        mock_redis_client.keys.side_effect = [
            [b"test:entry:1", b"test:entry:2"],  # Entry keys
            [b"test:type:cache", b"test:type:short_term"],  # Type keys
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
    async def test_health_check(self, redis_cache_store: RedisCacheStore) -> None:
        """Test health check."""
        # Set up mock Redis manager health
        redis_cache_store.redis.health_check = AsyncMock(return_value=True)

        is_healthy = await redis_cache_store.health_check()

        assert is_healthy is True
        redis_cache_store.redis.health_check.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close(self, redis_cache_store: RedisCacheStore) -> None:
        """Test closing cache store."""
        await redis_cache_store.close()

        redis_cache_store.redis.disconnect.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_set(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test setting a cache value."""
        # String value
        success = await redis_cache_store.set("test-key", "test-value")

        assert success is True
        mock_redis_client.set.assert_called_with("test:test-key", "test-value")
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
            mock_redis_client.set.assert_called_with(
                "test:test-key2", '{"key":"value"}'
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_set_with_ttl(
        self, redis_cache_store: RedisCacheStore, mock_redis_client: AsyncMock
    ) -> None:
        """Test setting a cache value with TTL."""
        success = await redis_cache_store.set("test-key", "test-value", ttl=60)

        assert success is True
        mock_redis_client.setex.assert_called_with("test:test-key", 60, "test-value")

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
        mock_redis_client.get.assert_called_with("test:test-key")
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
        mock_redis_client.exists.assert_called_with("test:test-key")

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
        mock_redis_client.expire.assert_called_with("test:test-key", 60)
