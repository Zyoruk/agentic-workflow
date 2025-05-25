"""AI-driven agentic workflow system for autonomous workflows."""

__version__ = "0.3.0"

import logging
import sys

# Core imports
from .core.config import Config, create_config, get_config
from .core.engine import ComponentRegistry, WorkflowEngine
from .core.interfaces import (
    Component,
    ComponentStatus,
    EventHandler,
    Service,
    ServiceResponse,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStep,
)
from .core.logging_config import get_logger

# Memory management
from .memory import (  # Memory interfaces; Memory implementations; Memory manager
    BasicMemoryStore,
    CacheStore,
    KeyValueStore,
    MemoryEntry,
    MemoryManager,
    MemoryQuery,
    MemoryResult,
    MemoryStats,
    MemoryStore,
    MemoryType,
    RedisCacheStore,
    ShortTermMemory,
    VectorCapableStore,
    VectorStore,
    WeaviateVectorStore,
)

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

__all__ = [
    # Version
    "__version__",
    # Core interfaces
    "Component",
    "ComponentStatus",
    "EventHandler",
    "Service",
    "ServiceResponse",
    "WorkflowDefinition",
    "WorkflowExecution",
    "WorkflowStep",
    # Core components
    "ComponentRegistry",
    "Config",
    "WorkflowEngine",
    # Configuration
    "create_config",
    "get_config",
    # Logging
    "get_logger",
    # Memory interfaces
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
    # Memory implementations
    "RedisCacheStore",
    "ShortTermMemory",
    "WeaviateVectorStore",
    # Memory manager
    "MemoryManager",
]
