"""Neo4j driver factory."""

from typing import Optional

from neo4j import AsyncDriver, GraphDatabase

from .config import Neo4jConfig


class Neo4jDriverFactory:
    """Factory for creating Neo4j drivers."""

    _instance: Optional[AsyncDriver] = None

    @classmethod
    def create_driver(cls, config: Neo4jConfig) -> AsyncDriver:
        """Create a Neo4j driver instance.

        Args:
            config: The Neo4j configuration

        Returns:
            A Neo4j driver instance
        """
        if cls._instance is None:
            driver = GraphDatabase.driver(
                config.uri,
                auth=(config.username, config.password),
                max_connection_lifetime=config.max_connection_lifetime,
                max_connection_pool_size=config.max_connection_pool_size,
                connection_timeout=config.connection_timeout,
            )
            if not isinstance(driver, AsyncDriver):
                raise TypeError("Expected AsyncDriver instance")
            cls._instance = driver
        return cls._instance

    @classmethod
    async def close_driver(cls) -> None:
        """Close the Neo4j driver instance."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
