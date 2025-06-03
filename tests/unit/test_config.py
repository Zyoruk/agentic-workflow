"""Tests for configuration system."""

import os
from pathlib import Path
from typing import Dict

import pytest
from pydantic import ValidationError

from agentic_workflow.core.config import (
    Config,
    DatabaseConfig,
    LLMConfig,
    LoggingConfig,
    MonitoringConfig,
    SecurityConfig,
    create_config,
    get_config,
    reload_config,
    set_config,
)


class TestConfig:
    """Test configuration functionality."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = Config()
        assert config.environment == "development"
        assert config.debug is False
        assert config.app_name == "Agentic Workflow"
        assert config.app_version == "0.2.0"
        assert config.worker_threads == 4
        assert config.max_concurrent_workflows == 10
        assert config.default_timeout == 300

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = Config(
            environment="production",
            debug=True,
            app_name="Custom App",
            app_version="1.0.0",
            worker_threads=8,
            max_concurrent_workflows=20,
            default_timeout=600,
        )
        assert config.environment == "production"
        assert config.debug is True
        assert config.app_name == "Custom App"
        assert config.app_version == "1.0.0"
        assert config.worker_threads == 8
        assert config.max_concurrent_workflows == 20
        assert config.default_timeout == 600

    def test_invalid_worker_threads(self) -> None:
        """Test invalid worker threads value."""
        with pytest.raises(ValidationError):
            Config(worker_threads=0)

    def test_invalid_max_concurrent_workflows(self) -> None:
        """Test invalid max concurrent workflows value."""
        with pytest.raises(ValidationError):
            Config(max_concurrent_workflows=0)

    def test_invalid_default_timeout(self) -> None:
        """Test invalid default timeout value."""
        with pytest.raises(ValidationError):
            Config(default_timeout=0)

    def test_database_config(self) -> None:
        """Test database configuration."""
        db_config = DatabaseConfig(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="test_user",
            neo4j_password="test_pass",
            weaviate_url="http://localhost:8080",
            redis_url="redis://localhost:6379",
        )
        assert db_config.neo4j_uri == "bolt://localhost:7687"
        assert db_config.neo4j_user == "test_user"
        assert db_config.neo4j_password == "test_pass"
        assert db_config.weaviate_url == "http://localhost:8080"
        assert db_config.redis_url == "redis://localhost:6379"

    def test_llm_config(self) -> None:
        """Test LLM configuration."""
        llm_config = LLMConfig(
            openai_api_key="test_key",
            openai_base_url="https://api.openai.com",
            default_model="gpt-4",
            temperature=0.7,
            max_tokens=1000,
        )
        assert llm_config.openai_api_key == "test_key"
        assert llm_config.openai_base_url == "https://api.openai.com"
        assert llm_config.default_model == "gpt-4"
        assert llm_config.temperature == 0.7
        assert llm_config.max_tokens == 1000

    def test_logging_config(self) -> None:
        """Test logging configuration."""
        log_config = LoggingConfig(
            level="INFO",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            file_path=Path("app.log"),
        )
        assert log_config.level == "INFO"
        assert (
            log_config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        assert str(log_config.file_path) == "app.log"

    def test_monitoring_config(self) -> None:
        """Test monitoring configuration."""
        monitor_config = MonitoringConfig(
            prometheus_enabled=True,
            prometheus_port=9090,
            grafana_enabled=True,
            grafana_url="http://localhost:3000",
            health_check_interval=60,
            metrics_collection_interval=30,
        )
        assert monitor_config.prometheus_enabled is True
        assert monitor_config.prometheus_port == 9090
        assert monitor_config.grafana_enabled is True
        assert monitor_config.grafana_url == "http://localhost:3000"
        assert monitor_config.health_check_interval == 60
        assert monitor_config.metrics_collection_interval == 30

    def test_security_config(self) -> None:
        """Test security configuration."""
        security_config = SecurityConfig(
            secret_key="test_secret_key",
            jwt_expiration=3600,
            max_request_size=10 * 1024 * 1024,
            rate_limit_requests=100,
            rate_limit_window=60,
        )
        assert security_config.secret_key == "test_secret_key"
        assert security_config.jwt_expiration == 3600
        assert security_config.max_request_size == 10 * 1024 * 1024
        assert security_config.rate_limit_requests == 100
        assert security_config.rate_limit_window == 60


class TestConfigManagement:
    """Test configuration management functions."""

    def test_create_config(self) -> None:
        """Test creating configuration."""
        config = create_config()
        assert isinstance(config, Config)
        assert config.environment == "development"

    def test_get_config(self) -> None:
        """Test getting configuration."""
        config = get_config()
        assert isinstance(config, Config)

    def test_set_config(self) -> None:
        """Test setting configuration."""
        new_config = Config(environment="test")
        set_config(new_config)
        assert get_config().environment == "test"

    def test_reload_config(self) -> None:
        """Test reloading configuration."""
        # Set environment variable
        os.environ["AGENTIC_ENVIRONMENT"] = "production"

        # Reload config
        reload_config()

        # Check if environment was updated
        assert get_config().environment == "production"

        # Clean up
        del os.environ["AGENTIC_ENVIRONMENT"]

    def test_environment_variables(self) -> None:
        """Test configuration from environment variables."""
        env_vars: Dict[str, str] = {
            "AGENTIC_ENVIRONMENT": "production",
            "AGENTIC_DEBUG": "true",
            "AGENTIC_WORKER_THREADS": "8",
            "AGENTIC_MAX_CONCURRENT_WORKFLOWS": "20",
            "AGENTIC_DEFAULT_TIMEOUT": "600",
            "AGENTIC_DATABASE__NEO4J_URI": "bolt://db.example.com:7687",
            "AGENTIC_DATABASE__NEO4J_USER": "test_user",
            "AGENTIC_DATABASE__NEO4J_PASSWORD": "test_pass",
            "AGENTIC_LLM__OPENAI_API_KEY": "test_key",
            "AGENTIC_LLM__DEFAULT_MODEL": "gpt-4",
        }

        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value

        try:
            # Reload config
            reload_config()
            config = get_config()

            # Check values
            assert config.environment == "production"
            assert config.debug is True
            assert config.worker_threads == 8
            assert config.max_concurrent_workflows == 20
            assert config.default_timeout == 600
            assert config.database.neo4j_uri == "bolt://db.example.com:7687"
            assert config.database.neo4j_user == "test_user"
            assert config.database.neo4j_password == "test_pass"
            assert config.llm.openai_api_key == "test_key"
            assert config.llm.default_model == "gpt-4"

        finally:
            # Clean up environment variables
            for key in env_vars:
                if key in os.environ:
                    del os.environ[key]
