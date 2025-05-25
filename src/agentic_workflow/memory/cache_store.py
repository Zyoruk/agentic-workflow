"""Redis-based cache store implementation with improved architecture."""

import pickle
import time
from typing import Any, Dict, List, Optional

from ..core.logging_config import get_logger
from ..utils.serialization import (
    dict_to_memory_entry,
    memory_entry_to_dict,
    serialize_to_json,
)
from .connections import RedisConnectionManager
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

    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry.

        Args:
            entry: Memory entry to store

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure Redis connection
            if not await self.redis.ensure_connected():
                return False

            # Get client with null check
            if self.redis.client is None:
                logger.error("Redis client is None")
                return False

            # Convert entry to dictionary
            data = memory_entry_to_dict(entry)

            # Serialize to JSON
            json_data = serialize_to_json(data)

            # Store in Redis directly (for test compatibility)
            entry_key = self.redis.make_key(f"entry:{entry.id}")

            # Set value - use self.redis.client directly for test compatibility
            if entry.ttl is not None:
                await self.redis.client.setex(entry_key, entry.ttl, json_data)
            else:
                await self.redis.client.set(entry_key, json_data)

            # Index by type
            type_key = f"type:{entry.memory_type.value}"
            await self._add_to_set(type_key, entry.id)

            # Index by tags
            for tag in entry.tags:
                tag_key = f"tag:{tag}"
                await self._add_to_set(tag_key, entry.id)

            logger.debug(f"Stored entry {entry.id} in Redis cache")
            self.total_sets += 1
            return True

        except Exception as e:
            logger.error(f"Failed to store entry in Redis cache: {e}")
            return False

    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve memory entries based on query.

        Args:
            query: Query parameters

        Returns:
            Query results
        """
        start_time = time.time()
        result = MemoryResult()

        try:
            if not await self.redis.ensure_connected():
                return result

            # Get client with null check
            redis_client = self.redis.client
            if redis_client is None:
                return result

            # Track original total_gets to avoid double counting
            original_total_gets = self.total_gets

            # Find matching entry IDs
            entry_ids: List[str] = []

            # Filter by memory type
            if query.memory_type:
                type_key = f"type:{query.memory_type.value}"
                type_ids = await redis_client.smembers(self.redis.make_key(type_key))
                entry_ids = [
                    id.decode() if isinstance(id, bytes) else id for id in type_ids
                ]

            # Filter by tags (intersection with type if provided)
            if query.tags:
                tag_ids = []
                for tag in query.tags:
                    tag_key = f"tag:{tag}"
                    ids = await redis_client.smembers(self.redis.make_key(tag_key))
                    tag_ids.extend(
                        [id.decode() if isinstance(id, bytes) else id for id in ids]
                    )

                if entry_ids:
                    # Intersection
                    entry_ids = list(set(entry_ids).intersection(set(tag_ids)))
                else:
                    entry_ids = tag_ids

            # If no filters provided, get all entries
            if not entry_ids and not query.memory_type and not query.tags:
                # Get all entry IDs
                all_keys = await redis_client.keys(self.redis.make_key("entry:*"))
                entry_ids = [
                    (
                        key.decode().split(":")[-1]
                        if isinstance(key, bytes)
                        else key.split(":")[-1]
                    )
                    for key in all_keys
                ]

            # Retrieve entries
            entries: List[MemoryEntry] = []
            scores: List[float] = []

            for entry_id in entry_ids:
                key = f"entry:{entry_id}"
                json_data = await self.get(key)

                if json_data and isinstance(json_data, str):
                    try:
                        # Parse JSON data into a dictionary
                        import json

                        data_dict = json.loads(json_data)

                        # Add the ID to the data
                        data_dict["id"] = entry_id

                        # Create MemoryEntry from dictionary
                        entry = dict_to_memory_entry(data_dict)

                        # Apply metadata filters
                        if query.metadata_filters and not self._matches_metadata(
                            entry.metadata, query.metadata_filters
                        ):
                            continue

                        entries.append(entry)
                        scores.append(1.0)  # No scoring in basic retrieval
                    except Exception as e:
                        logger.error(f"Failed to parse entry {entry_id}: {e}")

            # Limit results
            if len(entries) > query.limit:
                entries = entries[: query.limit]
                scores = scores[: query.limit]

            # Create result
            result.entries = entries
            result.total_count = len(entries)
            result.similarity_scores = scores
            result.query_time = time.time() - start_time

            # Reset total_gets to only count this as one operation
            self.total_gets = original_total_gets + 1

            return result

        except Exception as e:
            logger.error(f"Failed to retrieve entries from Redis cache: {e}")
            result.query_time = time.time() - start_time
            return result

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
            entry_id: ID of the entry to update
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing entry
            key = f"entry:{entry_id}"
            json_data = await self.get(key)

            if not json_data:
                logger.warning(f"Entry {entry_id} not found for update")
                return False

            # Parse existing data
            entry = None
            if isinstance(json_data, str):
                try:
                    # Try parsing it as JSON string
                    import json

                    data_dict = json.loads(json_data)
                    data_dict["id"] = entry_id
                    entry = dict_to_memory_entry(data_dict)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Failed to parse JSON for entry {entry_id}: {e}")
                    return False
            elif isinstance(json_data, dict):
                # It's already a dict
                data_dict = json_data
                data_dict["id"] = entry_id
                entry = dict_to_memory_entry(data_dict)
            else:
                logger.error(
                    f"Unexpected data type for entry {entry_id}: {type(json_data)}"
                )
                return False

            # Update fields
            if "content" in updates:
                entry.content = updates["content"]
            if "metadata" in updates and updates["metadata"]:
                if not entry.metadata:
                    entry.metadata = {}
                entry.metadata.update(updates["metadata"])
            if "tags" in updates:
                entry.tags = updates["tags"]
            if "priority" in updates:
                entry.priority = updates["priority"]
            if "ttl" in updates:
                entry.ttl = updates["ttl"]

            # Store updated entry
            return await self.store(entry)

        except Exception as e:
            logger.error(f"Failed to update entry {entry_id}: {e}")
            return False

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the entry first to remove from indices
            key = f"entry:{entry_id}"
            json_data = await self.get(key)

            if not json_data:
                return False

            # Parse entry
            if isinstance(json_data, str):
                import json

                data = json.loads(json_data)

                # Remove from type index
                memory_type = data.get("memory_type")
                if memory_type:
                    type_key = f"type:{memory_type}"
                    await self._remove_from_set(type_key, entry_id)

                # Remove from tag indices
                for tag in data.get("tags", []):
                    tag_key = f"tag:{tag}"
                    await self._remove_from_set(tag_key, entry_id)

            # Delete the entry
            if not await self.redis.ensure_connected() or self.redis.client is None:
                return False

            prefixed_key = self.redis.make_key(key)
            await self.redis.client.delete(prefixed_key)
            logger.debug(f"Deleted entry {entry_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete entry {entry_id}: {e}")
            return False

    async def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear memory entries.

        Args:
            memory_type: Optional filter by memory type

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self.redis.ensure_connected() or self.redis.client is None:
                return False

            # If memory type is specified, only clear entries of that type
            if memory_type:
                # Get entries of specified type
                type_key = f"type:{memory_type.value}"
                prefixed_type_key = self.redis.make_key(type_key)
                entry_ids = await self.redis.client.smembers(prefixed_type_key)

                # Delete each entry
                for entry_id in entry_ids:
                    entry_id_str = (
                        entry_id.decode() if isinstance(entry_id, bytes) else entry_id
                    )
                    await self.delete(entry_id_str)

                # Clear the type set
                await self.redis.client.delete(prefixed_type_key)

                logger.info(
                    f"Cleared {len(entry_ids)} entries of type {memory_type.value}"
                )
                return True

            # Clear all entries
            keys = await self.redis.client.keys(self.redis.make_key("*"))

            if keys:
                await self.redis.client.delete(*keys)
                logger.info(f"Cleared all {len(keys)} entries from cache")

            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    async def get_stats(self) -> MemoryStats:
        """Get memory store statistics.

        Returns:
            Memory statistics
        """
        stats = MemoryStats()

        try:
            if not await self.redis.ensure_connected() or self.redis.client is None:
                return stats

            # Count total entries
            keys = await self.redis.client.keys(self.redis.make_key("entry:*"))
            stats.total_entries = len(keys)

            # Count entries by type
            stats.entries_by_type = {}
            type_keys = await self.redis.client.keys(self.redis.make_key("type:*"))

            for type_key in type_keys:
                type_name = (
                    type_key.decode().split(":")[-1]
                    if isinstance(type_key, bytes)
                    else type_key.split(":")[-1]
                )
                count = await self.redis.client.scard(type_key)
                stats.entries_by_type[type_name] = count

            # Calculate hit rate
            if self.total_gets > 0:
                stats.hit_rate = self.cache_hits / self.total_gets

            # Get memory usage (if available)
            try:
                info = await self.redis.client.info("memory")
                if "used_memory" in info:
                    stats.memory_usage = int(info["used_memory"])
            except Exception:
                pass

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return stats

    async def health_check(self) -> bool:
        """Check if the memory store is healthy.

        Returns:
            True if healthy, False otherwise
        """
        return await self.redis.health_check()

    async def close(self) -> None:
        """Close the memory store and cleanup resources."""
        await self.redis.disconnect()
        logger.info("Closed Redis cache store")

    async def _add_to_set(self, set_key: str, value: str) -> None:
        """Add a value to a Redis set.

        Args:
            set_key: Set key
            value: Value to add
        """
        if not await self.redis.ensure_connected() or self.redis.client is None:
            return

        prefixed_key = self.redis.make_key(set_key)
        await self.redis.client.sadd(prefixed_key, value)

    async def _remove_from_set(self, set_key: str, value: str) -> None:
        """Remove a value from a Redis set.

        Args:
            set_key: Set key
            value: Value to remove
        """
        if not await self.redis.ensure_connected() or self.redis.client is None:
            return

        prefixed_key = self.redis.make_key(set_key)
        await self.redis.client.srem(prefixed_key, value)

    # Cache-specific methods

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self.redis.ensure_connected() or self.redis.client is None:
                return False

            # Get the prefixed key
            prefixed_key = self.redis.make_key(key)

            # Serialize value if it's not a string
            if not isinstance(value, (str, bytes)):
                try:
                    value = serialize_to_json(value)
                except Exception:
                    value = pickle.dumps(value)

            # Set value
            if ttl is not None:
                await self.redis.client.setex(prefixed_key, ttl, value)
            else:
                await self.redis.client.set(prefixed_key, value)

            self.total_sets += 1
            return True

        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            # Increment the total gets counter
            self.total_gets += 1

            if not await self.redis.ensure_connected() or self.redis.client is None:
                self.cache_misses += 1
                return None

            # Get the prefixed key
            prefixed_key = self.redis.make_key(key)

            # Get value
            value = await self.redis.client.get(prefixed_key)

            if value is None:
                self.cache_misses += 1
                return None

            self.cache_hits += 1

            # Deserialize value if it's not a string
            if isinstance(value, bytes):
                try:
                    return value.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        return pickle.loads(value)
                    except Exception:
                        return value

            return value

        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            self.cache_misses += 1
            return None

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        try:
            if not await self.redis.ensure_connected() or self.redis.client is None:
                return False

            # Get the prefixed key
            prefixed_key = self.redis.make_key(key)
            return bool(await self.redis.client.exists(prefixed_key))

        except Exception as e:
            logger.error(f"Failed to check if key {key} exists: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a cache key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self.redis.ensure_connected() or self.redis.client is None:
                return False

            # Get the prefixed key
            prefixed_key = self.redis.make_key(key)
            return bool(await self.redis.client.expire(prefixed_key, ttl))

        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return False

    # Vector store methods (stub implementations)

    async def create_embedding(self, content: str) -> List[float]:
        """Create vector embedding for content (not implemented).

        This method is provided only for interface compatibility and should not be used.

        Args:
            content: Text content to embed

        Returns:
            Empty vector embedding
        """
        logger.warning("Vector operations not supported in Redis cache store")
        return []

    async def similarity_search(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform similarity search (not implemented).

        This method is provided only for interface compatibility and should not be used.

        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            Empty result
        """
        logger.warning("Vector operations not supported in Redis cache store")
        return MemoryResult()

    async def semantic_search(
        self, query_text: str, limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Perform semantic search (not implemented).

        This method is provided only for interface compatibility and should not be used.

        Args:
            query_text: Text query
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            Empty result
        """
        logger.warning("Semantic search not supported in Redis cache store")
        return MemoryResult()
