"""Unit tests for logging_config logic."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from agentic_workflow.core.logging_config import (
    get_logger,
    log_error,
    log_performance,
    setup_logging,
)


@pytest.mark.unit
def test_get_logger_returns_logger():
    logger = get_logger("test")
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")


def test_setup_logging_calls_basicConfig():
    with (
        patch("logging.getLogger") as mock_getLogger,
        patch("logging.StreamHandler") as mock_stream_handler,
        patch("agentic_workflow.core.config.get_config") as mock_get_config,
    ):

        # Mock root logger
        mock_logger = MagicMock()
        mock_getLogger.return_value = mock_logger
        mock_getLogger().handlers = []  # Ensure handlers list is empty

        # Mock config
        mock_config = MagicMock()
        mock_config.environment = "development"
        mock_config.logging.dict.return_value = {"level": "DEBUG"}
        mock_get_config.return_value = mock_config

        # Test with config
        setup_logging(config={"level": "DEBUG"})

        # Verify logger was configured with DEBUG level at least once
        assert any(
            call.args[0] == logging.DEBUG
            for call in mock_logger.setLevel.call_args_list
        )
        mock_logger.addHandler.assert_called()
        mock_stream_handler.assert_called_once()


def test_log_error_logs_exception():
    with patch("logging.getLogger") as mock_getLogger:
        mock_logger = MagicMock()
        mock_getLogger.return_value = mock_logger
        log_error(Exception("fail"), context={"foo": "bar"})
        assert mock_logger.error.called


def test_log_performance_logs_info():
    with patch("logging.getLogger") as mock_getLogger:
        mock_logger = MagicMock()
        mock_getLogger.return_value = mock_logger
        log_performance("test", duration=1.23, context={"foo": "bar"})

        # Ensure info was called with expected message and metadata
        mock_logger.info.assert_called_once()
        args, kwargs = mock_logger.info.call_args
        assert args[0] == "Performance: test"
        extra_fields = kwargs["extra"]["extra_fields"]
        assert extra_fields["operation"] == "test"
        assert extra_fields["duration_seconds"] == 1.23
