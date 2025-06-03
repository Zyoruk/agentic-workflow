"""Connection management utilities for external services."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar

from ..core.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")  # Connection client type


class ConnectionManager(Generic[T], ABC):
    """Base class for managing connections to external services."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize connection manager.

        Args:
        name: Service name
        config: Connection configuration
        """
        self.name = name
        self.config = config
        self.client: Optional[T] = None
        self._lock = asyncio.Lock()
        self._is_healthy = False
        self._last_error: Optional[Exception] = None

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the service.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the service."""
        pass

    async def ensure_connected(self) -> bool:
        """Ensure connection is established.

        Returns:
            True if connected, False otherwise
        """
        if self.client is not None and self._is_healthy:
            return True

        async with self._lock:
            # Check again under the lock
            if self.client is not None and self._is_healthy:
                return True
            return await self.connect()

    async def health_check(self) -> bool:
        """Check if connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if self.client is None:
                return False
            return await self._check_connection_health()
        except Exception as e:
            self._last_error = e
            self._is_healthy = False
            logger.error(f"Health check failed for {self.name}: {e}")
            return False

    @abstractmethod
    async def _check_connection_health(self) -> bool:
        """Service-specific health check implementation."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get current connection status.

        Returns:
        Dictionary with connection status information
        """
        return {
            "name": self.name,
            "connected": self.client is not None,
            "healthy": self._is_healthy,
            "error": str(self._last_error) if self._last_error else None,
        }
