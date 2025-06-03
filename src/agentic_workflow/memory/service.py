"""Memory service component for the agentic workflow system."""

from typing import Any, Dict, List, Optional

from ..core.interfaces import ComponentStatus, Service, ServiceResponse
from ..core.logging_config import get_logger
from .interfaces import MemoryQuery, MemoryResult, MemoryType
from .manager import MemoryManager

logger = get_logger(__name__)


class MemoryService(Service):
    """Memory service component that provides unified memory operations."""

    def __init__(
        self, name: str = "memory_service", config: Optional[Dict[str, Any]] = None
    ):
        """Initialize memory service.

        Args:
        name: Service name
        config: Service configuration
        """
        super().__init__(name, config)

        # Memory manager configuration
        memory_config = config.get("memory", {}) if config else {}
        self.memory_manager = MemoryManager(memory_config)

        # Service state
        self.initialized = False

        logger.info(f"Initialized memory service: {name}")

    async def initialize(self) -> None:
        """Initialize the memory service."""
        try:
            self.status = ComponentStatus.INITIALIZING

            # Initialize memory manager
            await self.memory_manager.initialize()

            self.initialized = True
            self.status = ComponentStatus.READY

            logger.info("Memory service initialized successfully")

        except Exception as e:
            self.status = ComponentStatus.ERROR
            logger.error(f"Failed to initialize memory service: {e}")
            raise

    async def start(self) -> None:
        """Start the memory service."""
        try:
            if not self.initialized:
                await self.initialize()

            self.status = ComponentStatus.RUNNING
            logger.info("Memory service started")

        except Exception as e:
            self.status = ComponentStatus.ERROR
            logger.error(f"Failed to start memory service: {e}")
            raise

    async def stop(self) -> None:
        """Stop the memory service."""
        try:
            # Close memory manager
            await self.memory_manager.close()

            self.status = ComponentStatus.STOPPED
            logger.info("Memory service stopped")

        except Exception as e:
            logger.error(f"Error stopping memory service: {e}")
            self.status = ComponentStatus.ERROR

    async def health_check(self) -> ServiceResponse:
        """Check memory service health."""
        try:
            if not self.initialized:
                return ServiceResponse(
                    success=False, error="Memory service not initialized"
                )

            # Check memory manager health
            health_status = await self.memory_manager.health_check()

            # Determine overall health
            all_healthy = all(health_status.values())

            return ServiceResponse(
                success=all_healthy,
                data={
                    "status": "healthy" if all_healthy else "degraded",
                    "stores": health_status,
                    "component_status": self.status.value,
                },
                metadata={"service": self.name},
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return ServiceResponse(
                success=False,
                error=f"Health check failed: {e}",
                metadata={"service": self.name},
            )

    async def process_request(self, request: Dict[str, Any]) -> ServiceResponse:
        """Process a memory service request.

        Args:
            request: Request data with action and parameters

        Returns:
            Service response
        """
        try:
            action = request.get("action")
            params = request.get("parameters", {})

            if action == "store":
                return await self._handle_store_request(params)
            elif action == "retrieve":
                return await self._handle_retrieve_request(params)
            elif action == "search_similar":
                return await self._handle_similarity_search_request(params)
            elif action == "update":
                return await self._handle_update_request(params)
            elif action == "delete":
                return await self._handle_delete_request(params)
            elif action == "clear":
                return await self._handle_clear_request(params)
            elif action == "get_stats":
                return await self._handle_stats_request(params)
            elif action == "cache_set":
                return await self._handle_cache_set_request(params)
            elif action == "cache_get":
                return await self._handle_cache_get_request(params)
            else:
                return ServiceResponse(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Failed to process request: {e}")
            return ServiceResponse(
                success=False, error=f"Request processing failed: {e}"
            )

    async def _handle_store_request(self, params: Dict[str, Any]) -> ServiceResponse:
        """Handle store memory request."""
        try:
            content = params.get("content")
            if not content:
                return ServiceResponse(
                    success=False, error="Content is required for store operation"
                )

            memory_type_str = params.get("memory_type", "short_term")
            memory_type = MemoryType(memory_type_str)

            entry_id = await self.memory_manager.store(
                content=content,
                memory_type=memory_type,
                metadata=params.get("metadata"),
                tags=params.get("tags"),
                priority=params.get("priority", 0),
                ttl=params.get("ttl"),
                entry_id=params.get("entry_id"),
            )

            return ServiceResponse(
                success=True,
                data={"entry_id": entry_id},
                metadata={"action": "store", "memory_type": memory_type.value},
            )

        except Exception as e:
            return ServiceResponse(success=False, error=f"Store operation failed: {e}")

    async def _handle_retrieve_request(self, params: Dict[str, Any]) -> ServiceResponse:
        """Handle retrieve memory request."""
        try:
            # Build query from parameters
            query = None
            if "query" in params:
                # Use provided query object
                query_data = params["query"]
                query = MemoryQuery(**query_data)
            else:
                # Build query from individual parameters
                memory_type_str = params.get("memory_type")
                memory_type = MemoryType(memory_type_str) if memory_type_str else None

                query = MemoryQuery(
                    content=params.get("content"),
                    memory_type=memory_type,
                    tags=params.get("tags", []),
                    metadata_filters=params.get("metadata_filters", {}),
                    limit=params.get("limit", 10),
                    similarity_threshold=params.get("similarity_threshold", 0.7),
                    time_range=params.get("time_range"),
                )

            result = await self.memory_manager.retrieve(query)

            # Convert result to serializable format
            return ServiceResponse(
                success=True,
                data={
                    "entries": [entry.model_dump() for entry in result.entries],
                    "total_count": result.total_count,
                    "query_time": result.query_time,
                    "similarity_scores": result.similarity_scores,
                },
                metadata={"action": "retrieve", "query_limit": query.limit},
            )

        except Exception as e:
            return ServiceResponse(
                success=False, error=f"Retrieve operation failed: {e}"
            )

    async def _handle_similarity_search_request(
        self, params: Dict[str, Any]
    ) -> ServiceResponse:
        """Handle similarity search request."""
        try:
            content = params.get("content")
            if not content:
                return ServiceResponse(
                    success=False, error="Content is required for similarity search"
                )

            result = await self.memory_manager.search_similar(
                content=content,
                limit=params.get("limit", 10),
                threshold=params.get("threshold", 0.7),
                memory_type=(
                    MemoryType(params["memory_type"])
                    if params.get("memory_type")
                    else None
                ),
            )

            return ServiceResponse(
                success=True,
                data={
                    "entries": [entry.model_dump() for entry in result.entries],
                    "total_count": result.total_count,
                    "query_time": result.query_time,
                    "similarity_scores": result.similarity_scores,
                },
                metadata={
                    "action": "similarity_search",
                    "content_length": len(content),
                },
            )

        except Exception as e:
            return ServiceResponse(
                success=False, error=f"Similarity search failed: {e}"
            )

    async def _handle_update_request(self, params: Dict[str, Any]) -> ServiceResponse:
        """Handle update memory entry request."""
        try:
            entry_id = params.get("entry_id")
            updates = params.get("updates")

            if not entry_id or not updates:
                return ServiceResponse(
                    success=False, error="entry_id and updates are required"
                )

            memory_type_str = params.get("memory_type")
            memory_type = MemoryType(memory_type_str) if memory_type_str else None

            success = await self.memory_manager.update(
                entry_id=entry_id, updates=updates, memory_type=memory_type
            )

            return ServiceResponse(
                success=success,
                data={"updated": success},
                metadata={"action": "update", "entry_id": entry_id},
            )

        except Exception as e:
            return ServiceResponse(success=False, error=f"Update operation failed: {e}")

    async def _handle_delete_request(self, params: Dict[str, Any]) -> ServiceResponse:
        """Handle delete memory entry request."""
        try:
            entry_id = params.get("entry_id")
            if not entry_id:
                return ServiceResponse(success=False, error="entry_id is required")

            memory_type_str = params.get("memory_type")
            memory_type = MemoryType(memory_type_str) if memory_type_str else None

            success = await self.memory_manager.delete(
                entry_id=entry_id, memory_type=memory_type
            )

            return ServiceResponse(
                success=success,
                data={"deleted": success},
                metadata={"action": "delete", "entry_id": entry_id},
            )

        except Exception as e:
            return ServiceResponse(success=False, error=f"Delete operation failed: {e}")

    async def _handle_clear_request(self, params: Dict[str, Any]) -> ServiceResponse:
        """Handle clear memory request."""
        try:
            memory_type_str = params.get("memory_type")
            memory_type = MemoryType(memory_type_str) if memory_type_str else None

            store_name = params.get("store_name")

            success = await self.memory_manager.clear(
                memory_type=memory_type, store_name=store_name
            )

            return ServiceResponse(
                success=success,
                data={"cleared": success},
                metadata={
                    "action": "clear",
                    "memory_type": memory_type_str,
                    "store_name": store_name,
                },
            )

        except Exception as e:
            return ServiceResponse(success=False, error=f"Clear operation failed: {e}")

    async def _handle_stats_request(self, params: Dict[str, Any]) -> ServiceResponse:
        """Handle get statistics request."""
        try:
            stats = await self.memory_manager.get_stats()

            return ServiceResponse(
                success=True, data=stats, metadata={"action": "get_stats"}
            )

        except Exception as e:
            return ServiceResponse(
                success=False, error=f"Get stats operation failed: {e}"
            )

    async def _handle_cache_set_request(
        self, params: Dict[str, Any]
    ) -> ServiceResponse:
        """Handle cache set request."""
        try:
            key = params.get("key")
            value = params.get("value")

            if not key or value is None:
                return ServiceResponse(
                    success=False, error="key and value are required"
                )

            success = await self.memory_manager.cache_set(
                key=key, value=value, ttl=params.get("ttl")
            )

            return ServiceResponse(
                success=success,
                data={"cached": success},
                metadata={"action": "cache_set", "key": key},
            )

        except Exception as e:
            return ServiceResponse(
                success=False, error=f"Cache set operation failed: {e}"
            )

    async def _handle_cache_get_request(
        self, params: Dict[str, Any]
    ) -> ServiceResponse:
        """Handle cache get request."""
        try:
            key = params.get("key")
            if not key:
                return ServiceResponse(success=False, error="key is required")

            value = await self.memory_manager.cache_get(key)

            return ServiceResponse(
                success=True,
                data={"value": value, "found": value is not None},
                metadata={"action": "cache_get", "key": key},
            )

        except Exception as e:
            return ServiceResponse(
                success=False, error=f"Cache get operation failed: {e}"
            )

    # Convenience methods for direct access
    async def store_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        priority: int = 0,
        ttl: Optional[int] = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """Store content in memory (convenience method).

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
        """
        return await self.memory_manager.store(
            content=content,
            memory_type=memory_type,
            metadata=metadata,
            tags=tags,
            priority=priority,
            ttl=ttl,
            entry_id=entry_id,
        )

    async def retrieve_memory(
        self,
        query: Optional[MemoryQuery] = None,
        *,
        content: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> MemoryResult:
        """Retrieve memory entries (convenience method).

        Args:
            query: Memory query
            content: Content to search for
            memory_type: Filter by memory type
            tags: Filter by tags
            limit: Maximum number of results

        Returns:
            Memory result
        """
        if query is None:
            # Build query from kwargs
            query = MemoryQuery(
                content=content,
                memory_type=memory_type,
                tags=tags or [],
                limit=limit,
            )

        return await self.memory_manager.retrieve(query)

    async def search_similar_memory(
        self, content: str, limit: int = 10, threshold: float = 0.7
    ) -> MemoryResult:
        """Search for similar memory entries (convenience method).

        Args:
            content: Content to search for
            limit: Maximum results
            threshold: Similarity threshold

        Returns:
            Memory result
        """
        return await self.memory_manager.search_similar(
            content=content, limit=limit, threshold=threshold
        )

    async def close(self) -> None:
        """Close the memory service and its resources."""
        await self.memory_manager.close()
