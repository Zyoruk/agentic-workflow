"""Logging configuration and utilities for the agentic workflow system."""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_config


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
        record: Log record to format

        Returns:
        JSON formatted log message
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.

        Args:
        record: Log record to format

        Returns:
        Colored log message
        """
        # Add color to level name
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"

        return super().format(record)


def setup_logging(
    config: Optional[Dict[str, Any]] = None, force_reload: bool = False
) -> None:
    """Setup logging configuration.

    Args:
    config: Optional logging configuration override
    force_reload: Force reload of logging configuration
    """
    if not force_reload and logging.getLogger().handlers:
        # Logging already configured
        return

    # Get configuration
    app_config = get_config()
    log_config = config or app_config.logging.dict()

    # Clear existing handlers if force reload
    if force_reload:
        logging.getLogger().handlers.clear()

    # Set root logger level
    log_level = getattr(logging, log_config.get("level", "INFO").upper())
    logging.getLogger().setLevel(log_level)

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)

    console_formatter: logging.Formatter
    if app_config.environment == "development":
        # Use colored formatter for development
        console_format = log_config.get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_formatter = ColoredFormatter(console_format)
    else:
        # Use JSON formatter for production
        console_formatter = JSONFormatter()

    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)

    # Add console handler to root logger
    logging.getLogger().addHandler(console_handler)

    # Setup file handler if file path is specified
    file_path = log_config.get("file_path")
    if file_path:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler
        max_bytes = log_config.get("max_file_size", 10 * 1024 * 1024)
        backup_count = log_config.get("backup_count", 5)

        file_handler = logging.handlers.RotatingFileHandler(
            file_path, maxBytes=max_bytes, backupCount=backup_count
        )

        # Always use JSON formatter for file output
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)

        # Add file handler to root logger
        logging.getLogger().addHandler(file_handler)

    # Set specific logger levels
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log configuration completion
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "extra_fields": {
                "level": log_config.get("level", "INFO"),
                "file_path": str(file_path) if file_path else None,
                "environment": app_config.environment,
            }
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with optional extra configuration.

    Args:
    name: Logger name (usually __name__)

    Returns:
    Configured logger instance
    """
    # Ensure logging is configured
    setup_logging()

    logger = logging.getLogger(name)

    # Add custom methods for structured logging
    def log_with_extra(level: str, message: str, **kwargs: Any) -> None:
        """Log message with extra structured data."""
        extra_fields = {k: v for k, v in kwargs.items() if k != "exc_info"}
        if extra_fields:
            extra = {"extra_fields": extra_fields}
        else:
            extra = {}

        log_method = getattr(logger, level.lower())
        log_method(message, extra=extra, exc_info=kwargs.get("exc_info"))

    # Add convenience methods
    logger.info_with_data = lambda msg, **kwargs: log_with_extra("INFO", msg, **kwargs)  # type: ignore[attr-defined]
    logger.error_with_data = lambda msg, **kwargs: log_with_extra("ERROR", msg, **kwargs)  # type: ignore[attr-defined]
    logger.warning_with_data = lambda msg, **kwargs: log_with_extra("WARNING", msg, **kwargs)  # type: ignore[attr-defined]
    logger.debug_with_data = lambda msg, **kwargs: log_with_extra("DEBUG", msg, **kwargs)  # type: ignore[attr-defined]

    return logger


def log_function_call(
    func_name: str, args: tuple = (), kwargs: Optional[dict] = None
) -> None:
    """Log function call with parameters.

    Args:
    func_name: Name of the function being called
    args: Function arguments
    kwargs: Function keyword arguments
    """
    logger = get_logger("function_calls")

    kwargs = kwargs or {}

    logger.debug_with_data(  # type: ignore[attr-defined]
        f"Function call: {func_name}",
        function=func_name,
        args=list(args),
        kwargs=kwargs,
    )


def log_performance(operation: str, duration: float, **metadata: Any) -> None:
    """Log performance metrics.

    Args:
    operation: Name of the operation
    duration: Duration in seconds
    **"""
    logger = get_logger("performance")

    logger.info_with_data(  # type: ignore[attr-defined]
        f"Performance: {operation}",
        operation=operation,
        duration_seconds=duration,
        **metadata,
    )


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Log error with context.

    Args:
    error: Exception to log
    context: Additional context information
    """
    logger = get_logger("errors")

    context = context or {}

    logger.error_with_data(  # type: ignore[attr-defined]
        f"Error occurred: {str(error)}",
        error_type=error.__class__.__name__,
        error_message=str(error),
        exc_info=True,
        **context,
    )
