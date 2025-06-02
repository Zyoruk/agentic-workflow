"""Redis-based cache store implementation with improved architecture."""

import json
import time
from typing import Any, Dict, List, Optional, cast

from ..core.logging_config import get_logger
from ..utils.serialization import (
    memory_entry_to_dict,
    serialize_to_json,
)
from .connections import RedisConnectionManager
from .connections.redis_connection import RedisClientNotAvailableError
from .interfaces import (
    CacheStore,
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryType,
)

logger = get_logger(__name__)


class RedisCacheStore(CacheStore):
    """Redis-based cache store with improved architecture.

    This implementation uses a dedicated connection manager and adheres to
    both the legacy CacheStore interface and the new KeyValueStore protocol.
    """

    def __init__(
        self, name: str = "redis_cache_store", config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Redis cache store.

        Args:
            name: Name of the store
            config: Configuration parameters
        """
        super().__init__(name, config)

        # Create Redis connection manager
        self.redis = RedisConnectionManager(f"{name}_connection", self.config)

        # Statistics
        self.total_sets = 0
        self.total_gets = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.last_cleanup_time = time.time()

        logger.info(f"Initialized Redis cache store: {name}")

    def _get_key(self, entry_id: str) -> str:
        """Get Redis key for entry."""
        return f"entry:{entry_id}"

    def _get_metadata_key(self, entry_id: str) -> str:
        """Get Redis key for entry metadata."""
        return f"metadata:{entry_id}"

    def _get_type_key(self, memory_type: MemoryType) -> str:
        """Get Redis key for memory type index."""
        return f"type:{memory_type.value}"

    def _get_tag_key(self, tag: str) -> str:
        """Get Redis key for tag index."""
        return f"tag:{tag}"

    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry.

        Args:
            entry: Memory entry to store

        Returns:
            True if successful, False otherwise

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return False

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)

            # Convert entry to dict and serialize
            entry_dict = memory_entry_to_dict(entry)
            serialized_data = serialize_to_json(entry_dict)

            # Store entry data
            if entry.ttl:
                await client.setex(self._get_key(entry.id), entry.ttl, serialized_data)
            else:
                await client.set(self._get_key(entry.id), serialized_data)

            # Store metadata
            metadata = {str(k): str(v) for k, v in entry.metadata.items()}
            await client.hset(self._get_metadata_key(entry.id), mapping=metadata)

            # Add to type index
            await client.sadd(self._get_type_key(entry.memory_type), entry.id)

            # Add to tag indices
            for tag in entry.tags:
                await client.sadd(self._get_tag_key(tag), entry.id)

            self.total_sets += 1
            return True
        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error storing entry: {e}")
            return False

    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve memory entries based on query.

        Args:
            query: Query parameters

        Returns:
            Query results

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)

            start_time = time.time()
            entries = []
            entry_ids = []

            # Get entry IDs based on query filters
            if query.memory_type:
                type_key = self._get_type_key(query.memory_type)
                type_entries = await client.smembers(type_key)
                entry_ids.extend(
                    [entry_id.decode("utf-8") for entry_id in type_entries]
                )
            elif query.tags:
                for tag in query.tags:
                    tag_key = self._get_tag_key(tag)
                    tag_entries = await client.smembers(tag_key)
                    entry_ids.extend(
                        [entry_id.decode("utf-8") for entry_id in tag_entries]
                    )
            else:
                keys = await client.keys("entry:*")
                entry_ids = [key.decode("utf-8").split(":")[-1] for key in keys]

            # Remove duplicates
            entry_ids = list(set(entry_ids))

            # Retrieve entries
            for entry_id in entry_ids:
                entry_data = await client.get(self._get_key(entry_id))
                if entry_data:
                    try:
                        # First deserialize the JSON string to a dictionary
                        entry_dict = json.loads(entry_data)
                        # Then create the MemoryEntry
                        entry = MemoryEntry(**entry_dict)
                        entries.append(entry)
                    except Exception as e:
                        logger.error(f"Failed to parse entry {entry_id}: {e}")
                        continue

            # Apply limit
            if query.limit and query.limit > 0:
                entries = entries[: query.limit]

            query_time = time.time() - start_time
            return MemoryResult(
                entries=entries,
                total_count=len(entries),
                query_time=query_time,
                similarity_scores=[1.0] * len(entries),
                success=True,
            )
        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )
        except Exception as e:
            logger.error(f"Error retrieving entries: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    def _matches_metadata(
        self, metadata: Dict[str, Any], filters: Dict[str, Any]
    ) -> bool:
        """Check if metadata matches filters.

        Args:
            metadata: Entry metadata
            filters: Metadata filters

        Returns:
            True if metadata matches filters, False otherwise
        """
        for k, v in filters.items():
            if k not in metadata or metadata[k] != v:
                return False
        return True

    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry.

        Args:
            entry_id: Entry ID
            updates: Dictionary of field names and new values

        Returns:
            True if successful, False otherwise

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return False

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)

            # Get existing entry
            entry_data = await client.get(self._get_key(entry_id))
            if not entry_data:
                return False

            try:
                # First deserialize the JSON string to a dictionary
                entry_dict = json.loads(entry_data)
                # Then create the MemoryEntry
                entry = MemoryEntry(**entry_dict)
            except Exception as e:
                logger.error(f"Failed to parse entry {entry_id}: {e}")
                return False

            # Update fields
            for field, value in updates.items():
                if hasattr(entry, field):
                    setattr(entry, field, value)

            # Store updated entry
            return await self.store(entry)

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating entry: {e}")
            return False

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: Entry ID

        Returns:
            True if successful, False otherwise

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return False

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)

            # Get entry data first to get metadata
            entry_data = await client.get(self._get_key(entry_id))
            if not entry_data:
                return False

            try:
                entry_dict = json.loads(entry_data)
                entry = MemoryEntry(**entry_dict)
            except Exception as e:
                logger.error(f"Failed to parse entry {entry_id}: {e}")
                return False

            # Delete entry data
            await client.delete(self._get_key(entry_id))

            # Delete metadata
            await client.delete(self._get_metadata_key(entry_id))

            # Remove from type index
            await client.srem(self._get_type_key(entry.memory_type), entry_id)

            # Remove from tag indices
            for tag in entry.tags:
                await client.srem(self._get_tag_key(tag), entry_id)

            return True

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting entry: {e}")
            return False

    async def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear all entries or entries of a specific type.

        Args:
            memory_type: Optional memory type to clear

        Returns:
            True if successful, False otherwise

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return False

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)

            if memory_type:
                # Get all entries of this type
                type_key = self._get_type_key(memory_type)
                entry_ids = await client.smembers(type_key)
                entry_ids = [entry_id.decode("utf-8") for entry_id in entry_ids]

                # Delete each entry
                for entry_id in entry_ids:
                    await self.delete(entry_id)

                # Clear the type index
                await client.delete(type_key)
            else:
                # Clear all entries
                keys = await client.keys("entry:*")
                if keys:
                    await client.delete(*keys)

                # Clear all metadata
                keys = await client.keys("metadata:*")
                if keys:
                    await client.delete(*keys)

                # Clear all type indices
                keys = await client.keys("type:*")
                if keys:
                    await client.delete(*keys)

                # Clear all tag indices
                keys = await client.keys("tag:*")
                if keys:
                    await client.delete(*keys)

            return True

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error clearing entries: {e}")
            return False

    async def get_stats(self) -> MemoryStats:
        """Get cache statistics.

        Returns:
            Cache statistics

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return MemoryStats(
                    total_entries=0,
                    memory_usage=0,
                    hit_rate=0.0,
                    average_retrieval_time=0.0,
                    entries_by_type={},
                    total_stores=self.total_sets,
                    total_retrievals=self.total_gets,
                )

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)

            # Get total entries
            keys = await client.keys("entry:*")
            total_entries = len(keys)

            # Get entries by type
            entries_by_type: Dict[str, int] = {}
            type_keys = await client.keys("type:*")
            for type_key in type_keys:
                type_name = type_key.decode("utf-8").split(":")[-1]
                count = await client.scard(type_key)
                entries_by_type[type_name] = count

            # Calculate hit rate
            total_requests = self.total_gets
            hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0

            # Get memory usage from Redis info
            info = await client.info()
            memory_usage = info.get("used_memory", 0)

            return MemoryStats(
                total_entries=total_entries,
                memory_usage=memory_usage,
                hit_rate=hit_rate,
                average_retrieval_time=0.0,  # TODO: Implement query time tracking
                entries_by_type=entries_by_type,
                total_stores=self.total_sets,
                total_retrievals=self.total_gets,
            )

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return MemoryStats(
                total_entries=0,
                memory_usage=0,
                hit_rate=0.0,
                average_retrieval_time=0.0,
                entries_by_type={},
                total_stores=self.total_sets,
                total_retrievals=self.total_gets,
            )
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return MemoryStats(
                total_entries=0,
                memory_usage=0,
                hit_rate=0.0,
                average_retrieval_time=0.0,
                entries_by_type={},
                total_stores=self.total_sets,
                total_retrievals=self.total_gets,
            )

    async def health_check(self) -> bool:
        """Check if the cache store is healthy.

        Returns:
            True if healthy, False otherwise

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return False

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)
            return bool(await client.ping())

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            return False

    async def close(self) -> None:
        """Close the cache store."""
        await self.redis.disconnect()

    async def _add_to_set(self, set_key: str, value: str) -> None:
        """Add value to a Redis set.

        Args:
            set_key: Set key
            value: Value to add

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)
            await client.sadd(set_key, value)

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
        except Exception as e:
            logger.error(f"Error adding to set: {e}")

    async def _remove_from_set(self, set_key: str, value: str) -> None:
        """Remove value from a Redis set.

        Args:
            set_key: Set key
            value: Value to remove

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)
            await client.srem(set_key, value)

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
        except Exception as e:
            logger.error(f"Error removing from set: {e}")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a key-value pair in the cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Optional time-to-live in seconds

        Returns:
            True if successful, False otherwise

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return False

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)

            # Serialize value
            if isinstance(value, (str, int, float, bool)):
                serialized = str(value)
            else:
                serialized = serialize_to_json(value)

            # Store with optional TTL
            if ttl:
                success = await client.setex(key, ttl, serialized)
            else:
                success = await client.set(key, serialized)

            if isinstance(success, bool):
                if success:
                    self.total_sets += 1
                return success
            # If Redis returns 1/0 or other types, convert to bool
            if success:
                self.total_sets += 1
            return bool(success)

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting cache value: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return None

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)

            # Get value
            self.total_gets += 1
            value = await client.get(key)
            if not value:
                self.cache_misses += 1
                return None

            self.cache_hits += 1
            # Try to deserialize
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Convert to string to ensure consistent return type
                return str(value) if value is not None else None

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting cache value: {e}")
            return None

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return False

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)
            result = await client.exists(key)
            return bool(result)

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking key existence: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return False

            self.redis._ensure_client()
            client = cast(Any, self.redis.client)
            return bool(await client.expire(key, ttl))

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting expiration: {e}")
            return False

    async def create_embedding(self, content: str) -> List[float]:
        """Create an embedding for the given content.

        Args:
            content: Text content to embed

        Returns:
            Embedding vector

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return []

            self.redis._ensure_client()
            # TODO: Implement embedding creation
            return []

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return []
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return []

    async def similarity_search(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Search for similar entries using vector similarity.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            threshold: Similarity threshold

        Returns:
            Query results

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            self.redis._ensure_client()
            # TODO: Implement vector similarity search
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=True,
            )

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )
        except Exception as e:
            logger.error(f"Error performing similarity search: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    async def semantic_search(
        self, query_text: str, limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Search for semantically similar entries.

        Args:
            query_text: Query text
            limit: Maximum number of results
            threshold: Similarity threshold

        Returns:
            Query results

        Raises:
            RedisClientNotAvailableError: If Redis client is not available
        """
        try:
            if not await self.redis.ensure_connected():
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            self.redis._ensure_client()

            # Create embedding for query
            query_embedding = await self.create_embedding(query_text)
            if not query_embedding:
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            # Perform similarity search
            return await self.similarity_search(
                query_embedding, limit=limit, threshold=threshold
            )

        except RedisClientNotAvailableError as e:
            logger.error(f"Redis client not available: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )
