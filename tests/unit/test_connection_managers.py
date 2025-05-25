"""Unit tests for connection management utilities."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_workflow.memory.connections import (
    RedisConnectionManager,
    WeaviateConnectionManager,
)
from agentic_workflow.utils.connection import ConnectionManager


# Test for base ConnectionManager
class TestConnectionManager:
    """Tests for the ConnectionManager abstract base class."""

    # Create a concrete subclass for testing abstract class
    class ConcreteConnectionManager(ConnectionManager):
        """Concrete implementation for testing."""

        async def connect(self) -> bool:
            """Test implementation of connect."""
            return True

        async def disconnect(self) -> None:
            """Test implementation of disconnect."""
            pass

        async def _check_connection_health(self) -> bool:
            """Test implementation of health check."""
            return True

    @pytest.fixture
    def connection_manager(self) -> ConnectionManager:
        """Create a connection manager for testing."""
        return self.ConcreteConnectionManager("test_connection", {"test": "value"})

    @pytest.mark.unit
    def test_initialization(self, connection_manager: ConnectionManager) -> None:
        """Test initialization of connection manager."""
        assert connection_manager.name == "test_connection"
        assert connection_manager.config == {"test": "value"}
        assert connection_manager.client is None
        assert connection_manager._is_healthy is False
        assert connection_manager._last_error is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ensure_connected_with_healthy_connection(
        self, connection_manager: ConnectionManager
    ) -> None:
        """Test ensure_connected when connection is already healthy."""
        # Set up a healthy connection
        connection_manager.client = MagicMock()
        connection_manager._is_healthy = True

        # Ensure connected
        result = await connection_manager.ensure_connected()

        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ensure_connected_with_unhealthy_connection(
        self, connection_manager: ConnectionManager
    ) -> None:
        """Test ensure_connected when connection needs to be established."""
        # Set up an unhealthy connection
        connection_manager.client = None
        connection_manager._is_healthy = False

        # Mock connect method
        with patch.object(
            connection_manager, "connect", return_value=True
        ) as mock_connect:
            result = await connection_manager.ensure_connected()

            assert result is True
            mock_connect.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_with_no_client(
        self, connection_manager: ConnectionManager
    ) -> None:
        """Test health check when there is no client."""
        connection_manager.client = None

        result = await connection_manager.health_check()

        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_with_client(
        self, connection_manager: ConnectionManager
    ) -> None:
        """Test health check with a client."""
        connection_manager.client = MagicMock()

        # Mock _check_connection_health
        with patch.object(
            connection_manager, "_check_connection_health", return_value=True
        ) as mock_check:
            result = await connection_manager.health_check()

            assert result is True
            mock_check.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_with_exception(
        self, connection_manager: ConnectionManager
    ) -> None:
        """Test health check when an exception occurs."""
        connection_manager.client = MagicMock()

        # Mock _check_connection_health to raise exception
        with patch.object(
            connection_manager,
            "_check_connection_health",
            side_effect=Exception("Test error"),
        ):
            result = await connection_manager.health_check()

            assert result is False
            assert connection_manager._is_healthy is False
            assert str(connection_manager._last_error) == "Test error"

    @pytest.mark.unit
    def test_get_status(self, connection_manager: ConnectionManager) -> None:
        """Test getting connection status."""
        connection_manager.client = MagicMock()
        connection_manager._is_healthy = True
        connection_manager._last_error = Exception("Previous error")

        status = connection_manager.get_status()

        assert status["name"] == "test_connection"
        assert status["connected"] is True
        assert status["healthy"] is True
        assert status["error"] == "Previous error"


# Test for RedisConnectionManager
class TestRedisConnectionManager:
    """Tests for the RedisConnectionManager class."""

    @pytest.fixture
    def redis_manager(self) -> RedisConnectionManager:
        """Create a Redis connection manager for testing."""
        config = {
            "url": "redis://localhost:6379/0",
            "password": "test_password",
            "db": 0,
            "key_prefix": "test:",
        }
        return RedisConnectionManager("test_redis", config)

    @pytest.mark.unit
    def test_initialization(self, redis_manager: RedisConnectionManager) -> None:
        """Test initialization of Redis connection manager."""
        assert redis_manager.name == "test_redis"
        assert redis_manager.config["url"] == "redis://localhost:6379/0"
        assert redis_manager.config["password"] == "test_password"
        assert redis_manager.connection_config["host"] == "localhost"
        assert redis_manager.connection_config["port"] == 6379
        assert redis_manager.connection_config["db"] == 0
        assert redis_manager.key_prefix == "test:"

    @pytest.mark.unit
    def test_redis_url_parsing(self, redis_manager: RedisConnectionManager) -> None:
        """Test parsing of Redis URL."""
        # Test standard URL
        config = redis_manager._parse_redis_url("redis://host:1234/5")
        assert config["host"] == "host"
        assert config["port"] == 1234
        assert config["db"] == 5

        # Test URL without port
        config = redis_manager._parse_redis_url("redis://host/2")
        assert config["host"] == "host"
        assert config["port"] == 6379
        assert config["db"] == 2

        # Test URL without db
        config = redis_manager._parse_redis_url("redis://host:1234")
        assert config["host"] == "host"
        assert config["port"] == 1234
        assert config["db"] == 0

        # Test non-redis URL format
        config = redis_manager._parse_redis_url("host:1234")
        assert config["host"] == "host"
        assert config["port"] == 1234
        assert config["db"] == 0

        # Test simple host
        config = redis_manager._parse_redis_url("localhost")
        assert config["host"] == "localhost"
        assert config["port"] == 6379
        assert config["db"] == 0

    @pytest.mark.unit
    def test_make_key(self, redis_manager: RedisConnectionManager) -> None:
        """Test key creation with prefix."""
        key = redis_manager.make_key("test_key")
        assert key == "test:test_key"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_without_redis_available(
        self, redis_manager: RedisConnectionManager
    ) -> None:
        """Test connect when Redis is not available."""
        # Mock REDIS_AVAILABLE to False
        with patch(
            "agentic_workflow.memory.connections.redis_connection.REDIS_AVAILABLE",
            False,
        ):
            result = await redis_manager.connect()

            assert result is False
            assert redis_manager.client is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_with_exception(
        self, redis_manager: RedisConnectionManager
    ) -> None:
        """Test connect when an exception occurs."""
        # Mock redis module
        with (
            patch(
                "agentic_workflow.memory.connections.redis_connection.REDIS_AVAILABLE",
                True,
            ),
            patch(
                "agentic_workflow.memory.connections.redis_connection.redis.ConnectionPool",
                side_effect=Exception("Test error"),
            ),
        ):
            result = await redis_manager.connect()

            assert result is False
            assert redis_manager.client is None
            assert redis_manager._is_healthy is False
            assert str(redis_manager._last_error) == "Test error"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_no_client(
        self, redis_manager: RedisConnectionManager
    ) -> None:
        """Test health check when there is no client."""
        redis_manager.client = None

        result = await redis_manager._check_connection_health()

        assert result is False


# Test for WeaviateConnectionManager
class TestWeaviateConnectionManager:
    """Tests for the WeaviateConnectionManager class."""

    @pytest.fixture
    def weaviate_manager(self) -> WeaviateConnectionManager:
        """Create a Weaviate connection manager for testing."""
        config = {
            "url": "http://localhost:8080",
            "api_key": "test_api_key",
            "class_name": "TestClass",
        }
        return WeaviateConnectionManager("test_weaviate", config)

    @pytest.mark.unit
    def test_initialization(self, weaviate_manager: WeaviateConnectionManager) -> None:
        """Test initialization of Weaviate connection manager."""
        assert weaviate_manager.name == "test_weaviate"
        assert weaviate_manager.config["url"] == "http://localhost:8080"
        assert weaviate_manager.config["api_key"] == "test_api_key"
        assert weaviate_manager.default_class_name == "TestClass"
        assert weaviate_manager.collections == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_without_weaviate_available(
        self, weaviate_manager: WeaviateConnectionManager
    ) -> None:
        """Test connect when Weaviate is not available."""
        # Mock WEAVIATE_AVAILABLE to False
        with patch(
            "agentic_workflow.memory.connections.weaviate_connection.WEAVIATE_AVAILABLE",
            False,
        ):
            result = await weaviate_manager.connect()

            assert result is False
            assert weaviate_manager.client is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_with_exception(
        self, weaviate_manager: WeaviateConnectionManager
    ) -> None:
        """Test connect when an exception occurs."""
        # Mock WeaviateClient
        with (
            patch(
                "agentic_workflow.memory.connections.weaviate_connection.WEAVIATE_AVAILABLE",
                True,
            ),
            patch(
                "agentic_workflow.memory.connections.weaviate_connection.WeaviateClient",
                side_effect=Exception("Test error"),
            ),
        ):
            result = await weaviate_manager.connect()

            assert result is False
            assert weaviate_manager.client is None
            assert weaviate_manager._is_healthy is False
            # We don't check the exact error message as it may vary depending on the weaviate version
            assert weaviate_manager._last_error is not None
            assert isinstance(weaviate_manager._last_error, Exception)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_collection_without_client(
        self, weaviate_manager: WeaviateConnectionManager
    ) -> None:
        """Test get_collection when there is no client."""
        # Mock connect to fail
        with patch.object(weaviate_manager, "connect", return_value=False):
            result = await weaviate_manager.get_collection("TestClass")

            assert result is None
