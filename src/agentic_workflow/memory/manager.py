"""Memory manager that coordinates multiple memory stores."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.logging_config import get_logger
from .factory import MemoryStoreFactory
from .interfaces import (
    CacheStore,
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStore,
    MemoryType,
    VectorStore,
)

logger = get_logger(__name__)


class MemoryManager:
    """Coordinates multiple memory stores and provides unified memory operations.

    This implementation follows improved architecture with dependency injection
    and better separation of concerns.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize memory manager.

        Args:
        config: Configuration for memory stores
        """
        self.config = config or {}

        # Memory stores
        self.stores: Dict[str, MemoryStore] = {}
        self.store_types: Dict[MemoryType, str] = {}

        # Default store mappings
        self.default_mappings = {
            MemoryType.SHORT_TERM: "short_term",
            MemoryType.LONG_TERM: "vector_store",
            MemoryType.CACHE: "cache",
            MemoryType.VECTOR: "vector_store",
        }

        # Statistics
        self.total_operations = 0
        self.operations_by_type: Dict[str, int] = {}

        logger.info("Initialized memory manager")

    async def initialize(self) -> None:
        """Initialize all memory stores using the factory."""
        try:
            # Create stores using factory
            factory = MemoryStoreFactory()

            # Initialize short-term memory
            short_term_config = self.config.get("short_term", {})
            short_term_store = factory.create_short_term_store(
                name="short_term", config=short_term_config
            )
            self.stores["short_term"] = short_term_store

            # Initialize vector store
            vector_config = self.config.get("vector_store", {})
            vector_store = factory.create_vector_store(
                name="vector_store", config=vector_config
            )
            if vector_store:
                self.stores["vector_store"] = vector_store

            # Initialize cache store
            cache_config = self.config.get("cache", {})
            cache_store = factory.create_cache_store(name="cache", config=cache_config)
            self.stores["cache"] = cache_store

            # Set up type mappings
            for memory_type, store_name in self.default_mappings.items():
                self.store_types[memory_type] = store_name

            logger.info("Memory manager initialized with all stores")

        except Exception as e:
            logger.error(f"Failed to initialize memory manager: {e}")
            raise

    def register_store(self, name: str, store: MemoryStore) -> None:
        """Register a custom memory store.

        Args:
        name: Name of the store
        store: Memory store instance
        """
        self.stores[name] = store
        logger.info(f"Registered memory store: {name}")

    def set_type_mapping(self, memory_type: MemoryType, store_name: str) -> None:
        """Set which store to use for a specific memory type.

        Args:
        memory_type: Type of memory
        store_name: Name of the store to use
        """
        if store_name not in self.stores:
            raise ValueError(f"Store '{store_name}' not found")

        self.store_types[memory_type] = store_name
        logger.info(f"Mapped {memory_type.value} to store: {store_name}")

    def _get_store_for_type(self, memory_type: MemoryType) -> MemoryStore:
        """Get the appropriate store for a memory type.

        Args:
        memory_type: Type of memory

        Returns:
        Memory store instance

        Raises:
        ValueError: If no store is configured for the type
        """
        store_name = self.store_types.get(memory_type)
        if not store_name:
            raise ValueError(f"No store configured for memory type: {memory_type}")

        store = self.stores.get(store_name)
        if not store:
            raise ValueError(f"Store not found: {store_name}")

        return store

    async def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        priority: int = 0,
        ttl: Optional[int] = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """Store content in memory.

        Args:
            content: Content to store
            memory_type: Type of memory storage
            metadata: Additional metadata
            tags: Tags for categorization
            priority: Priority level
            ttl: Time to live in seconds
            entry_id: Optional custom ID

        Returns:
            Entry ID

        Raises:
            ValueError: If store is not available
        """
        try:
            # Generate ID if not provided
            if not entry_id:
                entry_id = str(uuid.uuid4())

            # Create memory entry
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                metadata=metadata or {},
                memory_type=memory_type,
                timestamp=datetime.now(timezone.utc),
                ttl=ttl,
                tags=tags or [],
                priority=priority,
            )

            # Get appropriate store
            store = self._get_store_for_type(memory_type)

            # Store entry
            success = await store.store(entry)

            if success:
                self.total_operations += 1
                op_type = f"store_{memory_type.value}"
                self.operations_by_type[op_type] = (
                    self.operations_by_type.get(op_type, 0) + 1
                )

                logger.debug(f"Stored entry {entry_id} in {memory_type.value} memory")
                return entry_id
            else:
                raise RuntimeError(
                    f"Failed to store entry in {memory_type.value} memory"
                )

        except Exception as e:
            logger.error(f"Failed to store memory entry: {e}")
            raise

    async def retrieve(
        self,
        query: Optional[MemoryQuery] = None,
        content: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> MemoryResult:
        """Retrieve memory entries.

        Args:
            query: Prepared query object
            content: Content to search for
            memory_type: Filter by memory type
            tags: Filter by tags
            limit: Maximum number of results

        Returns:
            Memory retrieval results
        """
        try:
            # Build query if not provided
            if not query:
                query = MemoryQuery(
                    content=content,
                    memory_type=memory_type,
                    tags=tags or [],
                    limit=limit,
                )

            # If memory type is specified, use specific store
            if query.memory_type:
                store = self._get_store_for_type(query.memory_type)
                result = await store.retrieve(query)
            else:
                # Search across all stores and merge results
                all_results = []

                for store_name, store in self.stores.items():
                    try:
                        store_result = await store.retrieve(query)
                        all_results.extend(store_result.entries)
                    except Exception as e:
                        logger.warning(f"Failed to query store {store_name}: {e}")
                        continue

                # Sort merged results by priority and timestamp (highest priority, most recent first)
                all_results.sort(key=lambda e: (e.priority, e.timestamp), reverse=True)

                # Apply limit
                limited_results = all_results[: query.limit]

                result = MemoryResult(
                    entries=limited_results,
                    total_count=len(all_results),
                    query_time=0.0,  # Would need to aggregate timing
                    similarity_scores=[1.0] * len(limited_results),
                    success=True,
                )

            # Update statistics
            self.total_operations += 1
            op_type = "retrieve"
            if query.memory_type:
                op_type = f"retrieve_{query.memory_type.value}"
            current_count = self.operations_by_type.get(op_type, 0)
            self.operations_by_type[op_type] = current_count + 1

            logger.debug(f"Retrieved {len(result.entries)} memory entries")
            return result

        except Exception as e:
            logger.error(f"Failed to retrieve memory entries: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    async def search_similar(
        self,
        content: str,
        limit: int = 10,
        threshold: float = 0.7,
        memory_type: Optional[MemoryType] = None,
    ) -> MemoryResult:
        """Perform semantic similarity search.

        Args:
            content: Content to find similar entries for
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            memory_type: Optional filter by memory type

        Returns:
            Similar memory entries
        """
        try:
            # Use vector store for similarity search
            vector_store = None

            if memory_type == MemoryType.VECTOR or memory_type == MemoryType.LONG_TERM:
                vector_store = self.stores.get("vector_store")
            else:
                # Try to find any vector store
                for store in self.stores.values():
                    if isinstance(store, VectorStore):
                        vector_store = store
                        break

            if not vector_store:
                logger.warning("No vector store available for similarity search")
                return MemoryResult(
                    entries=[],
                    total_count=0,
                    query_time=0.0,
                    similarity_scores=[],
                    success=False,
                )

            # Create embedding and search
            query_embedding = await vector_store.create_embedding(content)
            result = await vector_store.similarity_search(
                query_embedding, limit=limit, threshold=threshold
            )

            self.total_operations += 1
            current_count = self.operations_by_type.get("similarity_search", 0)
            self.operations_by_type["similarity_search"] = current_count + 1

            logger.debug(f"Found {len(result.entries)} similar entries")
            return result

        except Exception as e:
            logger.error(f"Failed to perform similarity search: {e}")
            return MemoryResult(
                entries=[],
                total_count=0,
                query_time=0.0,
                similarity_scores=[],
                success=False,
            )

    async def update(
        self,
        entry_id: str,
        updates: Dict[str, Any],
        memory_type: Optional[MemoryType] = None,
    ) -> bool:
        """Update a memory entry.

        Args:
            entry_id: ID of the entry to update
            updates: Fields to update
            memory_type: Type of memory (if known)

        Returns:
            True if successful, False otherwise
        """
        try:
            if memory_type:
                # Update in specific store
                store = self._get_store_for_type(memory_type)
                success = await store.update(entry_id, updates)
            else:
                # Try all stores
                success = False
                for store in self.stores.values():
                    try:
                        if await store.update(entry_id, updates):
                            success = True
                            break
                    except Exception:
                        continue

            if success:
                self.total_operations += 1
                op_type = "update"
                if memory_type:
                    op_type = f"update_{memory_type.value}"
                self.operations_by_type[op_type] = (
                    self.operations_by_type.get(op_type, 0) + 1
                )

                logger.debug(f"Updated memory entry: {entry_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to update memory entry: {e}")
            return False

    async def delete(
        self, entry_id: str, memory_type: Optional[MemoryType] = None
    ) -> bool:
        """Delete a memory entry.

        Args:
            entry_id: ID of the entry to delete
            memory_type: Type of memory (if known)

        Returns:
            True if successful, False otherwise
        """
        try:
            if memory_type:
                # Delete from specific store
                store = self._get_store_for_type(memory_type)
                success = await store.delete(entry_id)
            else:
                # Try all stores
                success = False
                for store in self.stores.values():
                    try:
                        if await store.delete(entry_id):
                            success = True
                            # Don't break - might exist in multiple stores
                    except Exception:
                        continue

            if success:
                self.total_operations += 1
                op_type = "delete"
                if memory_type:
                    op_type = f"delete_{memory_type.value}"
                self.operations_by_type[op_type] = (
                    self.operations_by_type.get(op_type, 0) + 1
                )

                logger.debug(f"Deleted memory entry: {entry_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete memory entry: {e}")
            return False

    async def clear(
        self, memory_type: Optional[MemoryType] = None, store_name: Optional[str] = None
    ) -> bool:
        """Clear memory entries.

        Args:
            memory_type: Optional filter by memory type
            store_name: Optional specific store to clear

        Returns:
            True if successful, False otherwise
        """
        try:
            success = True

            if store_name:
                # Clear specific store
                store = self.stores.get(store_name)
                if store:
                    success = await store.clear(memory_type)
                else:
                    logger.warning(f"Store not found: {store_name}")
                    return False
            elif memory_type:
                # Clear specific memory type
                store = self._get_store_for_type(memory_type)
                success = await store.clear(memory_type)
            else:
                # Clear all stores
                for store in self.stores.values():
                    try:
                        await store.clear()
                    except Exception as e:
                        logger.error(f"Failed to clear store {store.name}: {e}")
                        success = False

            if success:
                self.total_operations += 1
                self.operations_by_type["clear"] = (
                    self.operations_by_type.get("clear", 0) + 1
                )
                logger.info("Cleared memory entries")

            return success

        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics.

        Returns:
            Memory statistics from all stores
        """
        try:
            stats: Dict[str, Any] = {
                "total_operations": self.total_operations,
                "operations_by_type": self.operations_by_type.copy(),
                "stores": {},
            }

            # Initialize stores dictionary
            stores_dict: Dict[str, Any] = {}
            stats["stores"] = stores_dict

            for store_name, store in self.stores.items():
                try:
                    store_stats = await store.get_stats()
                    store_stats_dict = {
                        "total_entries": store_stats.total_entries,
                        "memory_usage": store_stats.memory_usage,
                        "hit_rate": store_stats.hit_rate,
                        "average_retrieval_time": store_stats.average_retrieval_time,
                        "entries_by_type": store_stats.entries_by_type,
                    }
                    stores_dict[store_name] = store_stats_dict
                except Exception as e:
                    logger.error(f"Failed to get stats from store {store_name}: {e}")
                    stores_dict[store_name] = {"error": str(e)}

            return stats

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all memory stores.

        Returns:
            Health status of each store
        """
        health_status: Dict[str, bool] = {}

        for store_name, store in self.stores.items():
            try:
                is_healthy = await store.health_check()
                health_status[store_name] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for store {store_name}: {e}")
                health_status[store_name] = False

        return health_status

    # Cache-specific convenience methods

    async def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_store = self.stores.get("cache")
            if not cache_store or not isinstance(cache_store, CacheStore):
                logger.error("Cache store not available")
                return False

            return await cache_store.set(key, value, ttl)

        except Exception as e:
            logger.error(f"Failed to set cache value: {e}")
            return False

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            cache_store = self.stores.get("cache")
            if not cache_store or not isinstance(cache_store, CacheStore):
                logger.error("Cache store not available")
                return None

            return await cache_store.get(key)

        except Exception as e:
            logger.error(f"Failed to get cache value: {e}")
            return None

    async def close(self) -> None:
        """Close all memory stores and cleanup resources."""
        for store_name, store in self.stores.items():
            try:
                await store.close()
                logger.debug(f"Closed memory store: {store_name}")
            except Exception as e:
                logger.error(f"Failed to close store {store_name}: {e}")

        self.stores.clear()
        self.store_types.clear()

        logger.info("Memory manager closed")
