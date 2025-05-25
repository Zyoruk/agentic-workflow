"""Memory management module for the agentic workflow system."""

from .cache_store import RedisCacheStore
from .factory import MemoryStoreFactory
from .interfaces import (
    BasicMemoryStore,
    CacheStore,
    KeyValueStore,
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryStore,
    MemoryType,
    VectorCapableStore,
    VectorStore,
)
from .manager import MemoryManager
from .short_term import ShortTermMemory

try:
    from .vector_store import WeaviateVectorStore
except ImportError:
    # This is fine - Weaviate might not be installed
    WeaviateVectorStore = None  # type: ignore

__all__ = [
    # Interfaces
    "MemoryEntry",
    "MemoryQuery",
    "MemoryResult",
    "MemoryStats",
    "MemoryType",
    "MemoryStore",
    "CacheStore",
    "VectorStore",
    "BasicMemoryStore",
    "KeyValueStore",
    "VectorCapableStore",
    # Implementations
    "RedisCacheStore",
    "ShortTermMemory",
    "WeaviateVectorStore",
    # Manager
    "MemoryManager",
    # Factory
    "MemoryStoreFactory",
]
