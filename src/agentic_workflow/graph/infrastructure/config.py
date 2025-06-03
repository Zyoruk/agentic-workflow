"""Neo4j configuration."""

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, validator


class Neo4jConfig(BaseModel):
    """Neo4j configuration."""

    uri: str = Field(..., description="Neo4j connection URI")
    username: str = Field(..., description="Neo4j username")
    password: str = Field(..., description="Neo4j password")
    database: Optional[str] = Field(None, description="Neo4j database name")
    max_connection_lifetime: int = Field(
        default=3600,
        description="Maximum connection lifetime in seconds",
    )
    max_connection_pool_size: int = Field(
        default=50,
        description="Maximum connection pool size",
    )
    connection_timeout: int = Field(
        default=30,
        description="Connection timeout in seconds",
    )
    max_retry_time: int = Field(
        default=300,
        description="Maximum retry time in seconds",
    )
    retry_delay: int = Field(
        default=1,
        description="Delay between retries in seconds",
    )

    @validator("uri")
    def validate_uri(cls, v: str) -> str:
        """Validate the Neo4j URI.

        Args:
            v: The URI to validate

        Returns:
            The validated URI

        Raises:
            ValueError: If the URI is invalid
        """
        try:
            result = urlparse(v)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid Neo4j URI")
            if result.scheme not in ["neo4j", "neo4j+s", "bolt", "bolt+s"]:
                raise ValueError("Invalid Neo4j URI scheme")
            return v
        except Exception as e:
            raise ValueError(f"Invalid Neo4j URI: {str(e)}")

    @validator(
        "max_connection_lifetime", "max_connection_pool_size", "connection_timeout"
    )
    def validate_positive_int(cls, v: int) -> int:
        """Validate that the value is a positive integer.

        Args:
            v: The value to validate

        Returns:
            The validated value

        Raises:
            ValueError: If the value is not positive
        """
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
