"""Redis-based cache store for sessions and temporary data."""

import json
import pickle
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..core.config import get_config
from ..core.logging_config import get_logger
from .interfaces import (
    CacheStore,
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryType,
)

REDIS_AVAILABLE = False  # Default, will be set to True if redis is importable

if TYPE_CHECKING:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    from redis.exceptions import ConnectionError, RedisError
else:
    try:
        import redis.asyncio as redis
        from redis.asyncio import Redis
        from redis.exceptions import ConnectionError, RedisError

        REDIS_AVAILABLE = True
    except ImportError:
        redis = None  # type: ignore[assignment]
        Redis = None  # type: ignore[assignment]

        class ConnectionError(Exception):
            pass

        class RedisError(Exception):
            pass

        # REDIS_AVAILABLE remains False

logger = get_logger(__name__)


class CacheMemoryStore(CacheStore):
    """Redis-based cache store for fast temporary data access."""

    def __init__(
        self, name: str = "cache_memory_store", config: Optional[Dict[str, Any]] = None
    ):
        """Initialize cache memory store.

        Args:
        name: Name of the memory store
        config: Configuration parameters
        """
        super().__init__(name, config)

        # Configuration
        app_config = get_config()
        redis_url = self.config.get("url", app_config.database.redis_url)
        self.password = self.config.get("password", app_config.database.redis_password)
        self.db = int(self.config.get("db", 0))
        self.key_prefix = self.config.get("key_prefix", "agentic_memory:")
        self.default_ttl = int(self.config.get("default_ttl", 3600))  # 1 hour
        self.max_connections = int(self.config.get("max_connections", 10))
        self.encoding = self.config.get("encoding", "utf-8")

        # Parse Redis URL
        self.redis_config = self._parse_redis_url(redis_url)

        # Client
        self.client: Optional[Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None

        # Statistics
        self.total_sets = 0
        self.total_gets = 0
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info(f"Initialized cache memory store: {name}")

    def _parse_redis_url(self, redis_url: str) -> Dict[str, Any]:
        """Parse Redis URL into connection parameters."""
        # Simple URL parsing for redis://host:port/db
        host: str
        port: int
        db: int
        if redis_url.startswith("redis://"):
            url_parts = redis_url[8:].split("/")
            host_port = url_parts[0]

            if ":" in host_port:
                host, port_str = host_port.split(":", 1)
                port = int(port_str)
            else:
                host = host_port
                port = 6379

            db = int(url_parts[1]) if len(url_parts) > 1 else 0
        else:
            # Fallback for simple host:port format
            if ":" in redis_url:
                host, port_str = redis_url.split(":", 1)
                port = int(port_str)
            else:
                host = redis_url
                port = 6379
            db = self.db  # self.db is always int

        return {
            "host": host,
            "port": port,
            "db": db,
            "password": self.password,
            "encoding": self.encoding,
            "decode_responses": True,
        }

    async def _connect(self) -> bool:
        """Connect to Redis instance.

        Returns:
            True if connection successful, False otherwise
        """
        # Check if Redis is available
        if not REDIS_AVAILABLE or redis is None:
            logger.warning("Redis is not available - install redis to use cache store")
            return False

        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(
                max_connections=self.max_connections, **self.redis_config
            )

            # Create client and test connection
            self.client = redis.Redis(connection_pool=self.connection_pool)
            if self.client is not None:
                await self.client.ping()

            logger.info(
                f"Connected to Redis at {self.redis_config['host']}:{self.redis_config['port']}"
            )
            return True

        except Exception as e:
            # Clean up if connection failed
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
            self.connection_pool = None
            return False

    async def _ensure_client(self) -> bool:
        """Ensure Redis client is connected.

        Returns:
            True if client is available, False otherwise
        """
        if self.client is None:
            return await self._connect()
        return True

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}{key}"

    def _serialize_entry(self, entry: MemoryEntry) -> str:
        """Serialize memory entry to JSON string."""
        try:
            data = {
                "id": entry.id,
                "content": entry.content,
                "metadata": entry.metadata,
                "memory_type": entry.memory_type.value,
                "timestamp": entry.timestamp.isoformat(),
                "ttl": entry.ttl,
                "embedding": entry.embedding,
                "tags": entry.tags,
                "priority": entry.priority,
            }
            return json.dumps(data)
        except Exception as e:
            logger.error(f"Failed to serialize entry: {e}")
            return "{}"

    def _deserialize_entry(self, data: str) -> Optional[MemoryEntry]:
        """Deserialize JSON string to memory entry."""
        try:
            from datetime import datetime

            entry_data = json.loads(data)

            # Parse timestamp
            timestamp_str = entry_data.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = datetime.utcnow()

            return MemoryEntry(
                id=entry_data.get("id", "unknown"),
                content=entry_data.get("content", ""),
                metadata=entry_data.get("metadata", {}),
                memory_type=MemoryType(entry_data.get("memory_type", "cache")),
                timestamp=timestamp,
                ttl=entry_data.get("ttl"),
                embedding=entry_data.get("embedding"),
                tags=entry_data.get("tags", []),
                priority=entry_data.get("priority", 0),
            )

        except Exception as e:
            logger.error(f"Failed to deserialize entry: {e}")
            return None

    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry in cache.

        Args:
            entry: Memory entry to store

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            key = self._make_key(entry.id)
            value = self._serialize_entry(entry)
            ttl = entry.ttl or self.default_ttl

            await self.client.setex(key, ttl, value)

            self.total_sets += 1

            logger.debug(f"Stored entry in cache: {entry.id} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to store entry {entry.id}: {e}")
            return False

    async def retrieve(self, query: MemoryQuery) -> MemoryResult:
        """Retrieve memory entries based on query.

        Note: This implementation is limited compared to other stores
        because Redis doesn't have advanced query capabilities.

        Args:
            query: Query parameters

        Returns:
            Query results
        """
        start_time = time.time()
        self.total_gets += 1

        try:
            if not await self._ensure_client() or self.client is None:
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=True,
                )

            matching_entries = []

            # If looking for specific content, try direct key lookup
            if query.content and len(query.content.split()) == 1:
                # Assume content might be a key
                possible_key = self._make_key(query.content)
                value = await self.client.get(possible_key)

                if value:
                    entry = self._deserialize_entry(value)
                    if entry and self._matches_query(entry, query):
                        matching_entries.append(entry)
                        self.cache_hits += 1
                    else:
                        self.cache_misses += 1
                else:
                    self.cache_misses += 1

            # Scan for keys matching pattern (expensive operation)
            if not matching_entries and query.limit <= 100:  # Limit scan operations
                pattern = f"{self.key_prefix}*"

                async for key in self.client.scan_iter(match=pattern, count=100):
                    if len(matching_entries) >= query.limit:
                        break

                    try:
                        value = await self.client.get(key)
                        if value:
                            entry = self._deserialize_entry(value)
                            if entry and self._matches_query(entry, query):
                                matching_entries.append(entry)
                    except Exception:
                        continue  # Skip problematic entries

            # Sort by priority and timestamp
            matching_entries.sort(
                key=lambda e: (-e.priority, e.timestamp), reverse=True
            )

            # Apply limit
            limited_entries = matching_entries[: query.limit]

            query_time = time.time() - start_time

            logger.debug(
                f"Retrieved {len(limited_entries)} entries from cache in {query_time:.3f}s"
            )

            return MemoryResult(
                entries=limited_entries,
                total_count=len(matching_entries),
                query_time=query_time,
                similarity_scores=[],
            )

        except Exception as e:
            logger.error(f"Failed to retrieve cache entries: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    def _matches_query(self, entry: MemoryEntry, query: MemoryQuery) -> bool:
        """Check if an entry matches the query criteria."""
        # Memory type filter
        if query.memory_type and entry.memory_type != query.memory_type:
            return False

        # Content filter (simple text search)
        if query.content and query.content.lower() not in entry.content.lower():
            return False

        # Tags filter
        if query.tags:
            if not any(tag in entry.tags for tag in query.tags):
                return False

        # Metadata filters
        for key, value in query.metadata_filters.items():
            if entry.metadata.get(key) != value:
                return False

        # Time range filter
        if query.time_range:
            start_time, end_time = query.time_range
            if not (start_time <= entry.timestamp <= end_time):
                return False

        return True

    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry.

        Args:
            entry_id: ID of the entry to update
            updates: Dictionary of field names and new values

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            key = self._make_key(entry_id)
            value = await self.client.get(key)

            if not value:
                logger.warning(f"Entry not found in cache: {entry_id}")
                return False

            entry = self._deserialize_entry(value)
            if not entry:
                logger.warning(f"Failed to deserialize entry: {entry_id}")
                return False

            # Update fields
            for field, new_value in updates.items():
                if hasattr(entry, field):
                    setattr(entry, field, new_value)

            # Store updated entry
            updated_value = self._serialize_entry(entry)
            # Get remaining TTL
            ttl = await self.client.ttl(key)
            if ttl is None or ttl < 0:
                ttl = self.default_ttl
            await self.client.setex(key, ttl, updated_value)

            logger.debug(f"Updated entry in cache: {entry_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update cache entry: {e}")
            return False

    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            key = self._make_key(entry_id)
            result = await self.client.delete(key)

            logger.debug(f"Deleted entry from cache: {entry_id}")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to delete cache entry: {e}")
            return False

    async def clear(self, memory_type: Optional[MemoryType] = None) -> bool:
        """Clear memory entries.

        Args:
            memory_type: Optional filter by memory type

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            if memory_type is None:
                # Clear all keys with prefix
                pattern = f"{self.key_prefix}*"
                deleted_count = 0

                async for key in self.client.scan_iter(match=pattern, count=1000):
                    await self.client.delete(key)
                    deleted_count += 1

                logger.info(f"Cleared {deleted_count} entries from cache")
                return True

            # Clear entries of specific type
            pattern = f"{self.key_prefix}*"
            deleted_count = 0

            async for key in self.client.scan_iter(match=pattern, count=100):
                try:
                    value = await self.client.get(key)
                    if value:
                        entry = self._deserialize_entry(value)
                        if entry and entry.memory_type == memory_type:
                            await self.client.delete(key)
                            deleted_count += 1
                except Exception:
                    continue

            logger.info(
                f"Cleared {deleted_count} entries of type {memory_type} from cache"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    async def get_stats(self) -> MemoryStats:
        """Get memory store statistics.

        Returns:
            Memory statistics
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return MemoryStats(
                    total_entries=0,
                    memory_usage=0,
                    hit_rate=0.0,
                    average_retrieval_time=0.0,
                    entries_by_type={},
                    total_stores=0,
                    total_retrievals=0,
                )

            # Get basic Redis info
            info = await self.client.info()

            # Count keys with our prefix
            pattern = f"{self.key_prefix}*"
            total_entries = 0
            entries_by_type: Dict[str, int] = {}

            async for key in self.client.scan_iter(match=pattern, count=100):
                total_entries += 1

                # Try to get memory type from entry (expensive)
                if total_entries <= 1000:  # Limit detailed analysis
                    try:
                        value = await self.client.get(key)
                        if value:
                            entry = self._deserialize_entry(value)
                            if entry:
                                entry_type = entry.memory_type.value
                                entries_by_type[entry_type] = (
                                    entries_by_type.get(entry_type, 0) + 1
                                )
                    except Exception:
                        continue

            # Calculate hit rate
            total_requests = self.total_gets
            hit_rate = self.cache_hits / max(total_requests, 1)

            # Memory usage from Redis info
            memory_usage = info.get("used_memory", 0)

            # Calculate average retrieval time
            average_retrieval_time = 0.0  # Would need to track this

            return MemoryStats(
                total_entries=total_entries,
                memory_usage=memory_usage,
                hit_rate=hit_rate,
                average_retrieval_time=average_retrieval_time,
                entries_by_type=entries_by_type,
                total_stores=self.total_sets,
                total_retrievals=self.total_gets,
            )

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return MemoryStats(
                total_entries=0,
                memory_usage=0,
                hit_rate=0.0,
                average_retrieval_time=0.0,
                entries_by_type={},
                total_stores=0,
                total_retrievals=0,
            )

    async def health_check(self) -> bool:
        """Check if the memory store is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            # Test with ping
            await self.client.ping()
            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    # CacheStore specific methods

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a cache value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            cache_key = self._make_key(key)
            ttl = ttl or self.default_ttl

            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            elif isinstance(value, str):
                serialized_value = value
            else:
                # Use pickle for complex objects
                serialized_value = pickle.dumps(value).decode("latin1")

            await self.client.setex(cache_key, ttl, serialized_value)

            self.total_sets += 1

            logger.debug(f"Set cache value: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to set cache value {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a cache value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return None

            cache_key = self._make_key(key)
            value = await self.client.get(cache_key)

            self.total_gets += 1

            if value is None:
                self.cache_misses += 1
                return None

            self.cache_hits += 1

            # Try to deserialize
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                try:
                    # Try pickle
                    return pickle.loads(value.encode("latin1"))
                except Exception:
                    # Return as string
                    return value

        except Exception as e:
            logger.error(f"Failed to get cache value {key}: {e}")
            return None

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            cache_key = self._make_key(key)
            result = await self.client.exists(cache_key)
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_client() or self.client is None:
                return False

            cache_key = self._make_key(key)
            result = await self.client.expire(cache_key, ttl)
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return False

    async def close(self) -> None:
        """Close the memory store and cleanup resources."""
        if self.client is not None:
            await self.client.close()
            self.client = None
            self.connection_pool = None

        logger.info("Cache memory store closed")

    async def create_embedding(self, content: str) -> List[float]:
        """Create vector embedding for content.

        Args:
            content: Text content to embed

        Returns:
            Vector embedding
        """
        # Cache store doesn't create real embeddings, just a placeholder
        # In a real implementation, you would use a proper embedding model
        logger.warning("Cache memory store doesn't support real embeddings")
        return [0.0] * 10  # Return a placeholder embedding

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
        # Cache store doesn't support real vector similarity search
        logger.warning("Cache memory store doesn't support vector similarity search")

        # Return empty result as cache is not meant for vector search
        return MemoryResult(
            entries=[],
            total_count=0,
            query_time=0.0,
            similarity_scores=[],
        )
