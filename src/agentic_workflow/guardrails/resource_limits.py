"""Resource limit enforcement for the agentic workflow system."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class ResourceType(Enum):
    """Types of resources that can be limited."""

    CPU = "cpu"
    MEMORY = "memory"
    TOKENS = "tokens"
    API_CALLS = "api_calls"
    REQUESTS = "requests"
    STORAGE = "storage"
    TIME = "time"
    BATCH_SIZE = "batch_size"
    CONCURRENCY = "concurrency"
    CUSTOM = "custom"


@dataclass
class ResourceUsage:
    """Current usage of a resource."""

    resource_type: ResourceType
    current: float
    limit: float
    unit: str

    @property
    def percentage(self) -> float:
        """Get percentage of resource used."""
        return (self.current / self.limit) * 100 if self.limit > 0 else 0

    @property
    def is_exceeded(self) -> bool:
        """Check if resource limit is exceeded."""
        return self.current > self.limit


class ResourceLimiter:
    """Resource limit enforcement for system stability and safety."""

    def __init__(self) -> None:
        """Initialize resource limiter."""
        self.limits: Dict[str, Dict[str, float]] = {}
        self.usages: Dict[str, Dict[str, float]] = {}
        self.start_times: Dict[str, Dict[str, float]] = {}
        self.callbacks: Dict[ResourceType, List[Callable]] = {}

        # Initialize default limits
        self._initialize_default_limits()

    def _initialize_default_limits(self) -> None:
        """Initialize default resource limits."""
        # Default API call limits
        self.set_limit("openai", ResourceType.API_CALLS, 100, "per_minute")
        self.set_limit("default", ResourceType.API_CALLS, 1000, "per_hour")

        # Default token limits
        self.set_limit("openai", ResourceType.TOKENS, 10000, "per_minute")
        self.set_limit("default", ResourceType.TOKENS, 100000, "per_day")

        # Default time limits
        self.set_limit("request", ResourceType.TIME, 30, "seconds")
        self.set_limit("task", ResourceType.TIME, 300, "seconds")

        # Default concurrency limits
        self.set_limit("default", ResourceType.CONCURRENCY, 10, "threads")

        # Default memory limits
        self.set_limit("process", ResourceType.MEMORY, 1024, "mb")

    def set_limit(
        self, context: str, resource_type: ResourceType, limit: float, unit: str
    ) -> None:
        """Set a resource limit.

        Args:
        context: Context identifier (e.g., "openai", "database")
        resource_type: Type of resource
        limit: Maximum value
        unit: Unit of measurement
        """
        if context not in self.limits:
            self.limits[context] = {}
            self.usages[context] = {}
            self.start_times[context] = {}

        resource_key = f"{resource_type.value}_{unit}"
        self.limits[context][resource_key] = limit
        self.usages[context][resource_key] = 0.0

        if resource_type == ResourceType.TIME:
            self.start_times[context][resource_key] = time.time()

        logger.debug(f"Set {resource_type.value} limit for {context} to {limit} {unit}")

    def register_callback(
        self, resource_type: ResourceType, callback: Callable
    ) -> None:
        """Register a callback for when a resource limit is approached or exceeded.

        Args:
        resource_type: Type of resource
        callback: Callback function
        """
        if resource_type not in self.callbacks:
            self.callbacks[resource_type] = []

        self.callbacks[resource_type].append(callback)

    def increment_usage(
        self,
        context: str,
        resource_type: ResourceType,
        amount: float = 1.0,
        unit: str = "",
        raise_on_limit: bool = False,
    ) -> bool:
        """Increment resource usage and check against limits.

        Args:
        context: Context identifier
        resource_type: Type of resource
        amount: Amount to increment
        unit: Unit of measurement
        raise_on_limit: Whether to raise an exception when limit is exceeded

        Returns:
        True if limit not exceeded, False otherwise

        Raises:
        ResourceLimitError: If limit exceeded and raise_on_limit is True
        """
        if context not in self.limits:
            logger.warning(f"No limits defined for context: {context}")
            return True

        resource_key = f"{resource_type.value}_{unit}"

        # If unit not specified, try to find any matching resource type
        if not unit:
            for key in self.limits[context]:
                if key.startswith(f"{resource_type.value}_"):
                    resource_key = key
                    break

        # Check if we have this specific limit
        if resource_key not in self.limits[context]:
            logger.warning(
                f"No {resource_type.value} limit with unit {unit} for {context}"
            )
            return True

        # Increment usage
        if resource_key not in self.usages[context]:
            self.usages[context][resource_key] = 0.0

        self.usages[context][resource_key] += amount

        # Check against limit
        current = self.usages[context][resource_key]
        limit = self.limits[context][resource_key]

        # Time-based reset
        if "per_" in resource_key:
            # Handle time-based limits with automatic reset
            current_time = time.time()

            # Get start time or initialize it
            if resource_key not in self.start_times[context]:
                self.start_times[context][resource_key] = current_time

            start_time = self.start_times[context][resource_key]
            elapsed = current_time - start_time

            # Reset based on time period
            if (
                ("per_minute" in resource_key and elapsed > 60)
                or ("per_hour" in resource_key and elapsed > 3600)
                or ("per_day" in resource_key and elapsed > 86400)
            ):
                self.usages[context][resource_key] = amount
                self.start_times[context][resource_key] = current_time
                current = amount

        # Log approaching limit at 80%
        if current >= 0.8 * limit and current < limit:
            logger.warning(
                f"{context} {resource_type.value} usage approaching limit: "
                f"{current:.2f}/{limit:.2f} ({current/limit*100:.1f}%)"
            )

            # Call callbacks for approaching limit
            self._trigger_callbacks(resource_type, context, current, limit, False)

        # Check if limit exceeded
        if current > limit:
            logger.error(
                f"{context} {resource_type.value} limit exceeded: "
                f"{current:.2f}/{limit:.2f}"
            )

            # Call callbacks for exceeded limit
            self._trigger_callbacks(resource_type, context, current, limit, True)

            if raise_on_limit:
                from ..core.exceptions import ResourceLimitError
                from .error_handling import ErrorSeverity

                raise ResourceLimitError(
                    f"{context} {resource_type.value} limit exceeded: "
                    f"{current:.2f}/{limit:.2f}",
                    severity=ErrorSeverity.HIGH,
                    resource_type=resource_type,
                    context=context,
                    current=current,
                    limit=limit,
                )

            return False

        return True

    def _trigger_callbacks(
        self,
        resource_type: ResourceType,
        context: str,
        current: float,
        limit: float,
        is_exceeded: bool,
    ) -> None:
        """Trigger callbacks for resource limit events.

        Args:
        resource_type: Type of resource
        context: Context identifier
        current: Current usage value
        limit: Limit value
        is_exceeded: Whether limit is exceeded
        """
        if resource_type in self.callbacks:
            for callback in self.callbacks[resource_type]:
                try:
                    callback(
                        resource_type=resource_type,
                        context=context,
                        current=current,
                        limit=limit,
                        is_exceeded=is_exceeded,
                    )
                except Exception as e:
                    logger.error(f"Error in resource limit callback: {e}")

    def reset_usage(
        self, context: str, resource_type: Optional[ResourceType] = None
    ) -> None:
        """Reset resource usage counter.

        Args:
        context: Context identifier
        resource_type: Optional resource type to reset
        """
        if context not in self.usages:
            return

        if resource_type:
            # Reset specific resource type
            for key in list(self.usages[context].keys()):
                if key.startswith(f"{resource_type.value}_"):
                    self.usages[context][key] = 0.0
                    if key in self.start_times[context]:
                        self.start_times[context][key] = time.time()
        else:
            # Reset all resource types for context
            for key in self.usages[context]:
                self.usages[context][key] = 0.0

            for key in self.start_times[context]:
                self.start_times[context][key] = time.time()

    def get_usage(
        self, context: str, resource_type: ResourceType, unit: str = ""
    ) -> Optional[ResourceUsage]:
        """Get current resource usage.

        Args:
        context: Context identifier
        resource_type: Type of resource
        unit: Unit of measurement

        Returns:
        ResourceUsage object or None if not found
        """
        if context not in self.limits:
            return None

        resource_key = f"{resource_type.value}_{unit}"

        # If unit not specified, try to find any matching resource type
        if not unit:
            for key in self.limits[context]:
                if key.startswith(f"{resource_type.value}_"):
                    resource_key = key
                    break

        if resource_key not in self.limits[context]:
            return None

        if resource_key not in self.usages[context]:
            self.usages[context][resource_key] = 0.0

        limit = self.limits[context][resource_key]
        current = self.usages[context][resource_key]

        # Extract the unit from the resource key
        extracted_unit = resource_key.split("_", 1)[1] if "_" in resource_key else unit

        return ResourceUsage(
            resource_type=resource_type,
            current=current,
            limit=limit,
            unit=extracted_unit,
        )

    def get_all_usages(self) -> Dict[str, List[ResourceUsage]]:
        """Get all resource usages.

        Returns:
        Dictionary mapping contexts to lists of ResourceUsage objects
        """
        result: Dict[str, List[ResourceUsage]] = {}

        for context in self.limits:
            result[context] = []

            for resource_key, limit in self.limits[context].items():
                parts = resource_key.split("_", 1)
                resource_type_str = parts[0]
                unit = parts[1] if len(parts) > 1 else ""

                try:
                    resource_type = ResourceType(resource_type_str)
                except ValueError:
                    logger.warning(f"Unknown resource type: {resource_type_str}")
                    continue

                current = self.usages[context].get(resource_key, 0.0)

                result[context].append(
                    ResourceUsage(
                        resource_type=resource_type,
                        current=current,
                        limit=limit,
                        unit=unit,
                    )
                )

        return result

    def check_limit(
        self, context: str, resource_type: ResourceType, unit: str = ""
    ) -> bool:
        usage = self.get_usage(context, resource_type, unit)
        if usage is None:
            return True  # No limit set, so not exceeded
        return not usage.is_exceeded
