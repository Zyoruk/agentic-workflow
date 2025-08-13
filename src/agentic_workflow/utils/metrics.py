"""Prometheus metrics utilities (lightweight and optional)."""

from __future__ import annotations

from typing import Optional

try:
    from prometheus_client import Counter
except ImportError:  # pragma: no cover - prometheus may be optional
    Counter = None  # type: ignore

from agentic_workflow.core.config import get_config

_model_fallback_counter: Optional["Counter"] = None


def get_model_fallback_counter() -> Optional["Counter"]:
    """Get or create the model fallback counter if Prometheus is enabled.

    Returns None if prometheus_client is not installed or disabled via config.
    """
    cfg = get_config()
    if not getattr(cfg.monitoring, "prometheus_enabled", False):
        return None
    if Counter is None:
        return None
    global _model_fallback_counter
    if _model_fallback_counter is None:
        _model_fallback_counter = Counter(
            "agentic_llm_model_fallback_total",
            "Number of times LLM model fell back to default",
            ["agent_id", "from_model", "to_model"],
        )
    return _model_fallback_counter


def inc_model_fallback(agent_id: str, from_model: str, to_model: str) -> None:
    """Increment model fallback metric if enabled."""
    counter = get_model_fallback_counter()
    if counter is not None:
        counter.labels(
            agent_id=agent_id, from_model=from_model, to_model=to_model
        ).inc()
