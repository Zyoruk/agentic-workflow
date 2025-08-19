"""Monitoring and metrics collection for the agentic workflow system."""

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from agentic_workflow.core.config import get_config
from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """Represents a metric value with metadata."""

    name: str
    value: float
    labels: Optional[Dict[str, str]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.labels is None:
            self.labels = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


class SystemMetrics:
    """Core system metrics for the agentic workflow platform."""

    def __init__(self) -> None:
        self.config = get_config()
        self.enabled = getattr(self.config.monitoring, "prometheus_enabled", False)
        self._metrics = {}

        if self.enabled and PROMETHEUS_AVAILABLE:
            self._initialize_prometheus_metrics()
        else:
            logger.info("Prometheus metrics disabled or unavailable")

    def _initialize_prometheus_metrics(self) -> None:
        """Initialize Prometheus metrics."""
        # Agent execution metrics
        self._metrics["agent_tasks_total"] = Counter(
            "agentic_agent_tasks_total",
            "Total tasks processed by agents",
            ["agent_id", "agent_type", "status"],
        )

        self._metrics["agent_task_duration"] = Histogram(
            "agentic_agent_task_duration_seconds",
            "Time spent processing agent tasks",
            ["agent_id", "agent_type"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")],
        )

        # Reasoning pattern metrics
        self._metrics["reasoning_executions_total"] = Counter(
            "agentic_reasoning_executions_total",
            "Total reasoning pattern executions",
            ["agent_id", "pattern_type", "success"],
        )

        self._metrics["reasoning_confidence"] = Histogram(
            "agentic_reasoning_confidence",
            "Confidence scores for reasoning executions",
            ["agent_id", "pattern_type"],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )

        # Memory system metrics
        self._metrics["memory_operations_total"] = Counter(
            "agentic_memory_operations_total",
            "Total memory operations",
            ["operation_type", "memory_type", "status"],
        )

        self._metrics["memory_size"] = Gauge(
            "agentic_memory_size_bytes",
            "Current memory usage in bytes",
            ["memory_type"],
        )

        # Tool execution metrics
        self._metrics["tool_executions_total"] = Counter(
            "agentic_tool_executions_total",
            "Total tool executions",
            ["tool_id", "agent_id", "status"],
        )

        self._metrics["tool_execution_duration"] = Histogram(
            "agentic_tool_execution_duration_seconds",
            "Tool execution duration",
            ["tool_id", "category"],
        )

        # Communication metrics
        self._metrics["messages_total"] = Counter(
            "agentic_messages_total",
            "Total messages sent between agents",
            ["sender_id", "recipient_id", "message_type"],
        )

        # System health metrics
        self._metrics["active_agents"] = Gauge(
            "agentic_active_agents", "Number of currently active agents"
        )

        self._metrics["system_uptime"] = Info(
            "agentic_system_uptime", "System uptime information"
        )

        logger.info("Prometheus metrics initialized")

    def record_agent_task(
        self, agent_id: str, agent_type: str, duration: float, success: bool
    ) -> None:
        """Record agent task execution metrics."""
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return

        status = "success" if success else "failure"

        self._metrics["agent_tasks_total"].labels(
            agent_id=agent_id, agent_type=agent_type, status=status
        ).inc()

        self._metrics["agent_task_duration"].labels(
            agent_id=agent_id, agent_type=agent_type
        ).observe(duration)

    def record_reasoning_execution(
        self, agent_id: str, pattern_type: str, confidence: float, success: bool
    ) -> None:
        """Record reasoning pattern execution metrics."""
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return

        self._metrics["reasoning_executions_total"].labels(
            agent_id=agent_id, pattern_type=pattern_type, success=str(success).lower()
        ).inc()

        self._metrics["reasoning_confidence"].labels(
            agent_id=agent_id, pattern_type=pattern_type
        ).observe(confidence)

    def record_memory_operation(
        self,
        operation_type: str,
        memory_type: str,
        success: bool,
        size_bytes: Optional[int] = None,
    ) -> None:
        """Record memory operation metrics."""
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return

        status = "success" if success else "failure"

        self._metrics["memory_operations_total"].labels(
            operation_type=operation_type, memory_type=memory_type, status=status
        ).inc()

        if size_bytes is not None:
            self._metrics["memory_size"].labels(memory_type=memory_type).set(size_bytes)

    def record_tool_execution(
        self, tool_id: str, agent_id: str, category: str, duration: float, success: bool
    ) -> None:
        """Record tool execution metrics."""
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return

        status = "success" if success else "failure"

        self._metrics["tool_executions_total"].labels(
            tool_id=tool_id, agent_id=agent_id, status=status
        ).inc()

        self._metrics["tool_execution_duration"].labels(
            tool_id=tool_id, category=category
        ).observe(duration)

    def record_message(
        self, sender_id: str, recipient_id: str, message_type: str
    ) -> None:
        """Record message transmission metrics."""
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return

        self._metrics["messages_total"].labels(
            sender_id=sender_id,
            recipient_id=recipient_id or "broadcast",
            message_type=message_type,
        ).inc()

    def update_active_agents(self, count: int) -> None:
        """Update active agent count."""
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return

        self._metrics["active_agents"].set(count)

    def set_system_info(self, info: Dict[str, str]) -> None:
        """Set system information."""
        if not self.enabled or not PROMETHEUS_AVAILABLE:
            return

        self._metrics["system_uptime"].info(info)


class HealthChecker:
    """Health check system for monitoring component status."""

    def __init__(self) -> None:
        self.components = {}
        self.logger = get_logger(f"{__name__}.health")

    def register_component(self, name: str, check_func: Callable[[], bool]) -> None:
        """Register a component health check function."""
        self.components[name] = {
            "check_func": check_func,
            "last_check": None,
            "status": "unknown",
            "message": "",
        }
        self.logger.info(f"Registered health check for component: {name}")

    async def check_component(self, name: str) -> Dict[str, Any]:
        """Check health of a specific component."""
        if name not in self.components:
            return {
                "status": "error",
                "message": f"Component {name} not registered",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        component = self.components[name]
        try:
            result = await component["check_func"]()
            status = "healthy" if result.get("healthy", False) else "unhealthy"
            message = result.get("message", "")
        except Exception as e:
            status = "error"
            message = str(e)
            self.logger.error(f"Health check failed for {name}: {e}")

        component.update(
            {"last_check": datetime.now(UTC), "status": status, "message": message}
        )

        return {
            "name": name,
            "status": status,
            "message": message,
            "timestamp": component["last_check"].isoformat(),
        }

    async def check_all(self) -> Dict[str, Any]:
        """Check health of all registered components."""
        results = {}
        overall_healthy = True

        for name in self.components:
            result = await self.check_component(name)
            results[name] = result
            if result["status"] != "healthy":
                overall_healthy = False

        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "components": results,
            "timestamp": datetime.now(UTC).isoformat(),
        }


class MonitoringService:
    """Central monitoring service for the agentic workflow system."""

    def __init__(self) -> None:
        self.config = get_config()
        self.metrics = SystemMetrics()
        self.health_checker = HealthChecker()
        self.logger = get_logger(__name__)
        self.started = False

        # Start time for uptime tracking
        self.start_time = time.time()

    async def start(self) -> None:
        """Start the monitoring service."""
        if self.started:
            return

        # Start Prometheus HTTP server if enabled
        if (
            self.metrics.enabled
            and PROMETHEUS_AVAILABLE
            and hasattr(self.config.monitoring, "prometheus_port")
        ):

            port = getattr(self.config.monitoring, "prometheus_port", 8000)
            try:
                start_http_server(port)
                self.logger.info(f"Prometheus metrics server started on port {port}")
            except Exception as e:
                self.logger.error(f"Failed to start Prometheus server: {e}")

        # Set initial system info
        self.metrics.set_system_info(
            {
                "version": "0.6.0",
                "start_time": datetime.now(UTC).isoformat(),
                "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
            }
        )

        self.started = True
        self.logger.info("Monitoring service started")

    async def stop(self) -> None:
        """Stop the monitoring service."""
        self.started = False
        self.logger.info("Monitoring service stopped")

    def get_uptime(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self.start_time


# Global monitoring service instance
monitoring_service = MonitoringService()
