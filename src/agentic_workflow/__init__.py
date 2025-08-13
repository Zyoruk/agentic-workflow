"""Agentic Workflow framework for building AI agent-based applications."""

from typing import Any, List

__version__ = "0.1.0"

# Import core components
from .core.config import get_config, reload_config
from .core.interfaces import Component, ComponentStatus, Service, ServiceResponse
from .core.logging_config import get_logger, setup_logging

# Import memory management components
try:  # Optional dependency: pydantic/redis/etc.
    from .memory.cache_store import RedisCacheStore
    from .memory.interfaces import (
        MemoryEntry,
        MemoryQuery,
        MemoryResult,
        MemoryStore,
        MemoryType,
    )
    from .memory.manager import MemoryManager
    from .memory.short_term import ShortTermMemory
except Exception:  # pragma: no cover - missing optional deps
    RedisCacheStore = None  # type: ignore
    MemoryEntry = MemoryQuery = MemoryResult = MemoryStore = MemoryType = None  # type: ignore
    MemoryManager = ShortTermMemory = None  # type: ignore

try:
    from .memory.vector_store import WeaviateVectorStore
except Exception:  # pragma: no cover - optional dependency
    # This is fine - Weaviate might not be installed
    WeaviateVectorStore = None  # type: ignore

# Import agents components - may require heavy optional deps (e.g., openai)
try:  # pragma: no cover - only executed when deps installed
    from .agents import (
        Agent,
        AgentResult,
        AgentTask,
        CodeGenerationAgent,
        create_agent,
        get_available_agent_types,
    )
except Exception:  # pragma: no cover - optional dependency handling
    Agent = AgentResult = AgentTask = CodeGenerationAgent = None  # type: ignore

    def create_agent(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        """Fallback when agent dependencies are missing."""
        raise ImportError(
            "Agent dependencies are not installed. Install optional requirements to use agents."
        )

    def get_available_agent_types() -> List[str]:
        return []


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
    # Agents
    "Agent",
    "AgentResult",
    "AgentTask",
    "CodeGenerationAgent",
    "create_agent",
    "get_available_agent_types",
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
