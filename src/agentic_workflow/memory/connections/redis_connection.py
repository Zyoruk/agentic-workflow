"""Redis connection management."""

from typing import Any, Dict, Optional

from ...core.config import get_config
from ...core.logging_config import get_logger
from ...utils.connection import ConnectionManager

logger = get_logger(__name__)

# Check if Redis is available
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore
    Redis = None  # type: ignore

    class RedisConnectionError(Exception):
        """Exception raised when Redis connection fails."""

        pass

    class RedisGeneralError(Exception):
        """Exception raised for general Redis errors."""

        pass

    REDIS_AVAILABLE = False


class RedisClientNotAvailableError(Exception):
    """Exception raised when attempting to use Redis client before it's available."""

    def __init__(self, message: str = "Redis client is not available"):
        super().__init__(message)


class RedisConnectionManager(ConnectionManager["Redis"]):
    """Manages connections to Redis."""

    def __init__(
        self, name: str = "redis_connection", config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Redis connection manager.

        Args:
            name: Connection name
            config: Connection configuration
        """
        # Set default configuration
        config = config or {}
        app_config = get_config()

        # Apply defaults from app config
        if not config.get("url"):
            config["url"] = app_config.database.redis_url
        if not config.get("password"):
            config["password"] = app_config.database.redis_password

        # Other defaults
        config.setdefault("db", 0)
        config.setdefault("encoding", "utf-8")
        config.setdefault("max_connections", 10)
        config.setdefault("key_prefix", "agentic_memory:")

        # Parse connection info
        self.connection_config = self._parse_redis_url(config["url"])
        self.connection_config["password"] = config["password"]
        self.connection_config["db"] = int(config["db"])
        self.connection_config["encoding"] = config["encoding"]
        self.connection_config["decode_responses"] = True

        self.key_prefix = config["key_prefix"]
        self.max_connections = int(config["max_connections"])

        super().__init__(name, config)
        # Initialize as None, but will be set during connect()
        self.connection_pool: Optional[Any] = None

    def _parse_redis_url(self, redis_url: str) -> Dict[str, Any]:
        """Parse Redis URL into connection parameters."""
        # Simple URL parsing for redis://host:port/db
        host: str
        port: int
        db: int = 0

        if redis_url.startswith("redis://"):
            url_parts = redis_url[8:].split("/")
            host_port = url_parts[0]

            if ":" in host_port:
                host, port_str = host_port.split(":", 1)
                port = int(port_str)
            else:
                host = host_port
                port = 6379

            if len(url_parts) > 1 and url_parts[1]:
                db = int(url_parts[1])
        else:
            # Fallback for simple host:port format
            if ":" in redis_url:
                host, port_str = redis_url.split(":", 1)
                port = int(port_str)
            else:
                host = redis_url
                port = 6379

        return {
            "host": host,
            "port": port,
            "db": db,
        }

    async def connect(self) -> bool:
        """Connect to Redis.

        Returns:
            True if connection successful, False otherwise
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis is not available - install redis package")
            return False

        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(
                max_connections=self.max_connections, **self.connection_config
            )

            # Create client and test connection
            self.client = redis.Redis(connection_pool=self.connection_pool)
            await self.client.ping()

            self._is_healthy = True
            logger.info(
                f"Connected to Redis at {self.connection_config['host']}:{self.connection_config['port']}"
            )
            return True

        except Exception as e:
            # Clean up if connection failed
            self._last_error = e
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
            self.connection_pool = None
            self._is_healthy = False
            return False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.client = None

        if self.connection_pool:
            self.connection_pool.disconnect()
            self.connection_pool = None

        self._is_healthy = False
        logger.info("Disconnected from Redis")

    async def _check_connection_health(self) -> bool:
        """Check if Redis connection is healthy."""
        if not self.client:
            return False

        try:
            await self.client.ping()
            self._is_healthy = True
            return True
        except Exception as e:
            self._last_error = e
            self._is_healthy = False
            logger.error(f"Redis health check failed: {e}")
            return False

    def make_key(self, key: str) -> str:
        """Create a prefixed Redis key.

        Args:
            key: Base key

        Returns:
            Prefixed key
        """
        return f"{self.key_prefix}{key}"

    async def ping(self) -> bool:
        """Check if Redis connection is alive."""
        if self.client is None:
            return False
        try:
            return await self.client.ping()
        except Exception:
            return False

    def _ensure_client(self) -> None:
        """Ensure Redis client is available.

        Raises:
            RedisClientNotAvailableError: If client is not available
        """
        if not self.client:
            raise RedisClientNotAvailableError(
                "Redis client is not available. Call connect() first."
            )
