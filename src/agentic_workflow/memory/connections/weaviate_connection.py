"""Weaviate connection management."""

# mypy: disable-error-code="unreachable,unused-ignore,call-arg,arg-type"
from typing import Any, Dict, Optional

from ...core.config import get_config
from ...core.logging_config import get_logger
from ...utils.connection import ConnectionManager

logger = get_logger(__name__)

# Check if Weaviate is available
try:
    from weaviate import WeaviateClient
    from weaviate.auth import AuthApiKey
    from weaviate.collections import Collection
    from weaviate.collections.classes.config import DataType, Property
    from weaviate.connect import ConnectionParams
    from weaviate.exceptions import WeaviateQueryException

    WEAVIATE_AVAILABLE = True
except ImportError:
    WeaviateClient = None  # type: ignore
    AuthApiKey = None  # type: ignore
    Collection = None  # type: ignore
    ConnectionParams = None  # type: ignore
    # Define a placeholder for the exception

    class WeaviateQueryError(Exception):
        """Exception raised for Weaviate query errors when weaviate is not available."""

        pass

    WeaviateQueryException = WeaviateQueryError  # type: ignore
    DataType = None  # type: ignore
    Property = None  # type: ignore
    WEAVIATE_AVAILABLE = False


class WeaviateConnectionManager(ConnectionManager["WeaviateClient"]):
    """Manages connections to Weaviate."""

    def __init__(
        self, name: str = "weaviate_connection", config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Weaviate connection manager.

        Args:
        name: Connection name
        config: Connection configuration
        """
        # Set default configuration
        config = config or {}
        app_config = get_config()

        # Apply defaults from app config
        if not config.get("url"):
            config["url"] = app_config.database.weaviate_url
        if not config.get("api_key"):
            config["api_key"] = app_config.database.weaviate_api_key

        # Other defaults
        config.setdefault("timeout", 60)
        config.setdefault("grpc_port", None)
        config.setdefault("additional_headers", {})

        super().__init__(name, config)

        # Collection-related attributes
        self.collections: Dict[str, Collection] = {}
        self.default_class_name = config.get("class_name", "MemoryEntry")
        self.auth = None

        # Set up auth if provided
        if self.config.get("api_key"):
            if AuthApiKey is not None:
                self.auth = AuthApiKey(api_key=self.config["api_key"])
            else:
                logger.warning("AuthApiKey not available - unable to use API key")

    async def connect(self) -> bool:
        """Connect to Weaviate.

        Returns:
            True if connection successful, False otherwise
        """
        if not WEAVIATE_AVAILABLE:
            logger.warning(
                "Weaviate is not available - install weaviate-client package"
            )
            return False

        try:
            # Create connection parameters
            if ConnectionParams is not None:
                # Pass the URL as a parameter and let ConnectionParams handle it
                # The specific implementation may vary based on the weaviate-client version
                connection_params = ConnectionParams.from_url(
                    self.config["url"], grpc_port=self.config.get("grpc_port")
                )
            else:
                # Fallback for when ConnectionParams is not available (import error case)
                connection_params = {"url": self.config["url"]}  # type: ignore

            # Create client with auth if provided
            self.client = WeaviateClient(  # type: ignore
                connection_params=connection_params,
                auth_client_secret=self.auth,
                additional_headers=self.config.get("additional_headers", {}),
            )

            # Test connection
            if self.client is None:
                logger.error("Failed to create Weaviate client")
                self._is_healthy = False
                return False

            # Store the result of is_live() to avoid unreachable code
            self._is_healthy = self.client.is_live()

            if self._is_healthy:
                logger.info(f"Connected to Weaviate at {self.config['url']}")
                return True

            logger.error("Weaviate connection test failed")
            return False

        except Exception as e:
            self._last_error = e
            logger.error(f"Failed to connect to Weaviate: {e}")
            self.client = None
            self._is_healthy = False
            return False

    async def disconnect(self) -> None:
        """Close Weaviate connection."""
        # Weaviate client doesn't have an explicit close method
        self.client = None
        self.collections = {}
        self._is_healthy = False
        logger.info("Disconnected from Weaviate")

    async def _check_connection_health(self) -> bool:
        """Check if Weaviate connection is healthy."""
        if not self.client:
            return False

        try:
            return self.client.is_live()
        except Exception as e:
            self._last_error = e
            self._is_healthy = False
            logger.error(f"Weaviate health check failed: {e}")
            return False

    async def get_collection(
        self, class_name: Optional[str] = None
    ) -> Optional[Collection]:
        """Get or create a Weaviate collection.

        Args:
            class_name: Name of the collection (class)

        Returns:
            Collection object or None if creation failed
        """
        # Check if Weaviate is available
        if not WEAVIATE_AVAILABLE:
            logger.error("Unable to create collection - Weaviate not available")
            return None

        # If client is not connected, try to connect
        if not self.client:
            # Store the result of connect() to avoid unreachable code
            connect_result = await self.connect()
            if not connect_result:
                return None

        # Check again if client is None (connect might fail)
        if not self.client:
            return None

        # Use default class name if not provided
        class_name = class_name or self.default_class_name

        # Return cached collection if available
        if class_name in self.collections:
            return self.collections[class_name]

        try:
            # Check if collection exists
            if self.client.collections.exists(class_name):
                # Get existing collection
                collection = self.client.collections.get(class_name)
                self.collections[class_name] = collection
                return collection

            # Create collection with proper configuration
            collection = self.client.collections.create(
                name=class_name,
                properties=[
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="memory_type", data_type=DataType.TEXT),
                    Property(name="timestamp", data_type=DataType.DATE),
                    Property(name="metadata", data_type=DataType.TEXT),
                    Property(name="tags", data_type=DataType.TEXT_ARRAY),
                    Property(name="priority", data_type=DataType.NUMBER),
                    Property(name="ttl", data_type=DataType.NUMBER),
                ],
                vectorizer_config=None,  # No vectorizer, we'll provide vectors explicitly
            )

            self.collections[class_name] = collection
            logger.info(f"Created Weaviate collection: {class_name}")
            return collection

        except Exception as e:
            self._last_error = e
            logger.error(f"Failed to get/create collection {class_name}: {e}")
            return None
