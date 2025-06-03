"""Configuration management system for the agentic workflow."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration."""

    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")

    weaviate_url: str = Field(default="http://localhost:8080")
    weaviate_api_key: Optional[str] = None

    redis_url: str = Field(default="redis://localhost:6379")
    redis_password: Optional[str] = None


class LLMConfig(BaseModel):
    """LLM configuration."""

    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    default_model: str = Field(default="gpt-4")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0)
    timeout: int = Field(default=30, gt=0)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_path: Optional[Path] = None
    max_file_size: int = Field(default=10 * 1024 * 1024)  # 10MB
    backup_count: int = Field(default=5)


class MonitoringConfig(BaseModel):
    """Monitoring and metrics configuration."""

    prometheus_enabled: bool = Field(default=False)
    prometheus_port: int = Field(default=8000)
    grafana_enabled: bool = Field(default=False)
    grafana_url: Optional[str] = None

    health_check_interval: int = Field(default=30)  # seconds
    metrics_collection_interval: int = Field(default=10)  # seconds


class SecurityConfig(BaseModel):
    """Security configuration."""

    secret_key: str = Field(default="dev-secret-key-change-in-production")
    jwt_expiration: int = Field(default=3600)  # seconds
    max_request_size: int = Field(default=10 * 1024 * 1024)  # 10MB
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)  # seconds


class Config(BaseModel):
    """Main configuration class."""

    # Environment
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # Core settings
    app_name: str = Field(default="Agentic Workflow")
    app_version: str = Field(default="0.2.0")

    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    # Additional settings
    worker_threads: int = Field(default=4, gt=0)
    max_concurrent_workflows: int = Field(default=10, gt=0)
    default_timeout: int = Field(default=300, gt=0)  # seconds

    model_config = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix="AGENTIC_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
    )


# Global configuration instance
_config: Optional[Config] = None


def load_config_from_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
    file_path: Path to configuration file

    Returns:
    Configuration dictionary

    Raises:
    FileNotFoundError: If config file doesn't exist
    yaml.YAMLError: If config file is invalid YAML
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    try:
        with open(file_path, "r") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in config file {file_path}: {e}")
        raise


def load_config_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables.

    Returns:
    Configuration dictionary with environment variables
    """
    config_dict: Dict[str, Any] = {}

    # Get all environment variables with AGENTIC_ prefix
    for key, value in os.environ.items():
        if key.startswith("AGENTIC_"):
            # Remove prefix and convert to lowercase
            config_key = key[8:].lower()

            # Handle nested keys (e.g., AGENTIC_DATABASE__NEO4J_URI)
            if "__" in config_key:
                parts = config_key.split("__")
                current: Dict[str, Any] = config_dict

                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                current[parts[-1]] = value
            else:
                config_dict[config_key] = value

    return config_dict


def create_config(
    config_file: Optional[Union[str, Path]] = None,
    override_dict: Optional[Dict[str, Any]] = None,
) -> Config:
    """Create configuration from multiple sources.

    Priority (highest to lowest):
    1. override_dict parameter
    2. Environment variables
    3. Configuration file
    4. Default values

    Args:
    config_file: Path to configuration file
    override_dict: Dictionary to override configuration values

    Returns:
    Configuration instance

    Raises:
    ValidationError: If configuration is invalid
    """
    # Start with empty dict
    config_dict = {}

    # 1. Load from file if specified
    if config_file:
        try:
            file_config = load_config_from_file(config_file)
            config_dict.update(file_config)
            logger.info(f"Loaded configuration from file: {config_file}")
        except Exception as e:
            logger.warning(f"Could not load config file {config_file}: {e}")

    # 2. Load from environment variables
    env_config = load_config_from_env()
    if env_config:
        config_dict.update(env_config)
        logger.info("Loaded configuration from environment variables")

    # 3. Apply overrides
    if override_dict:
        config_dict.update(override_dict)
        logger.info("Applied configuration overrides")

    try:
        return Config(**config_dict)
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise


def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
    Global configuration instance

    Raises:
    RuntimeError: If configuration hasn't been initialized
    """
    global _config

    if _config is None:
        # Auto-initialize with defaults and environment
        _config = create_config()
        logger.info("Auto-initialized configuration")

    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance.

    Args:
    config: Configuration instance to set as global
    """
    global _config
    _config = config
    logger.info("Updated global configuration")


def reload_config(
    config_file: Optional[Union[str, Path]] = None,
    override_dict: Optional[Dict[str, Any]] = None,
) -> Config:
    """Reload configuration from sources.

    Args:
    config_file: Path to configuration file
    override_dict: Dictionary to override configuration values

    Returns:
    New configuration instance
    """
    new_config = create_config(config_file, override_dict)
    set_config(new_config)
    logger.info("Configuration reloaded")
    return new_config
