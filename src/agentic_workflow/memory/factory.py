"""Factory for creating memory store instances."""

from typing import Any, Dict, Optional, cast

from ..core.logging_config import get_logger
from .cache_store import RedisCacheStore
from .interfaces import CacheStore, MemoryStore, VectorStore
from .short_term import ShortTermMemory

logger = get_logger(__name__)

# Import vector store implementation if available
try:
    from .vector_store import WeaviateVectorStore

    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    WeaviateVectorStore = None  # type: ignore


class MemoryStoreFactory:
    """Factory for creating memory store instances."""

    @staticmethod
    def create_store(
        store_type: str, name: str, config: Optional[Dict[str, Any]] = None
    ) -> Optional[MemoryStore]:
        """Create a memory store instance.

        Args:
            store_type: Type of memory store
            name: Name of the store
            config: Configuration parameters

        Returns:
            Memory store instance or None if creation failed
        """
        config = config or {}

        try:
            if store_type == "short_term":
                return ShortTermMemory(name=name, config=config)

            elif store_type == "cache":
                return RedisCacheStore(name=name, config=config)

            elif store_type == "vector":
                if not VECTOR_STORE_AVAILABLE:
                    logger.warning(
                        "Vector store not available - install weaviate-client"
                    )
                    return None
                return cast(VectorStore, WeaviateVectorStore(name=name, config=config))

            else:
                logger.error(f"Unknown store type: {store_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create memory store of type {store_type}: {e}")
            return None

    @staticmethod
    def create_short_term_store(
        name: str = "short_term_memory", config: Optional[Dict[str, Any]] = None
    ) -> ShortTermMemory:
        """Create a short-term memory store.

        Args:
            name: Name of the store
            config: Configuration parameters

        Returns:
            Short-term memory store
        """
        return ShortTermMemory(name=name, config=config or {})

    @staticmethod
    def create_cache_store(
        name: str = "cache_store", config: Optional[Dict[str, Any]] = None
    ) -> CacheStore:
        """Create a cache store.

        Args:
            name: Name of the store
            config: Configuration parameters

        Returns:
            Cache store
        """
        return RedisCacheStore(name=name, config=config or {})

    @staticmethod
    def create_vector_store(
        name: str = "vector_store", config: Optional[Dict[str, Any]] = None
    ) -> Optional[VectorStore]:
        """Create a vector store.

        Args:
            name: Name of the store
            config: Configuration parameters

        Returns:
            Vector store or None if creation failed
        """
        if not VECTOR_STORE_AVAILABLE:
            logger.warning("Vector store not available - install weaviate-client")
            return None

        return cast(VectorStore, WeaviateVectorStore(name=name, config=config or {}))
