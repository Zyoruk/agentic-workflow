"""Agentic Workflow framework for building AI agent-based applications."""

__version__ = "0.1.0"

# Import core components
from .core.config import get_config, reload_config
from .core.interfaces import (
    Component,
    ComponentStatus,
    Service,
    ServiceResponse,
)
from .core.logging_config import get_logger, setup_logging
from .memory.cache_store import RedisCacheStore

# Import memory management components
from .memory.interfaces import (
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStore,
    MemoryType,
)
from .memory.manager import MemoryManager
from .memory.short_term import ShortTermMemory

try:
    from .memory.vector_store import WeaviateVectorStore
except ImportError:
    # This is fine - Weaviate might not be installed
    WeaviateVectorStore = None  # type: ignore

# Import exceptions
from .core.exceptions import (
    AgentError,
    AgenticWorkflowError,
    ConfigurationError,
    NotFoundError,
    ResourceLimitError,
    SecurityViolationError,
    ServiceError,
    TimeoutError,
    ValidationError,
)
from .guardrails.error_handling import ErrorHandler, ErrorSeverity, RecoveryStrategy

# Import guardrails components
from .guardrails.input_validation import InputValidator, ValidationRule
from .guardrails.resource_limits import ResourceLimiter, ResourceType, ResourceUsage
from .guardrails.safety_checks import SafetyChecker, SafetyLevel, SafetyViolation
from .guardrails.service import GuardrailsService

# Convenient access to services
memory_service = None
guardrails_service = None

__all__ = [
    # Version
    "__version__",
    # Core
    "get_config",
    "reload_config",
    "get_logger",
    "setup_logging",
    "Component",
    "ComponentStatus",
    "Service",
    "ServiceResponse",
    # Memory
    "MemoryEntry",
    "MemoryQuery",
    "MemoryResult",
    "MemoryStore",
    "MemoryType",
    "MemoryManager",
    "ShortTermMemory",
    "RedisCacheStore",
    "WeaviateVectorStore",
    # Guardrails
    "InputValidator",
    "ValidationRule",
    "ValidationError",
    "ResourceLimiter",
    "ResourceType",
    "ResourceUsage",
    "ErrorHandler",
    "RecoveryStrategy",
    "ErrorSeverity",
    "SafetyChecker",
    "SafetyViolation",
    "SafetyLevel",
    "GuardrailsService",
    # Exceptions
    "AgenticWorkflowError",
    "ValidationError",
    "ResourceLimitError",
    "ConfigurationError",
    "ServiceError",
    "AgentError",
    "SecurityViolationError",
    "NotFoundError",
    "TimeoutError",
    # Service instances
    "memory_service",
    "guardrails_service",
]
