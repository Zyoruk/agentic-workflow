"""Health check and monitoring API endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from agentic_workflow.monitoring import monitoring_service
from agentic_workflow.monitoring.health import run_all_health_checks

router = APIRouter(tags=["health", "monitoring"])


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns the health status of all system components including:
    - Memory system
    - Agent registry
    - Reasoning engine
    - Communication system
    - Tool system
    - Configuration
    """
    try:
        health_results = await run_all_health_checks()

        return {
            "status": "healthy" if health_results["overall_healthy"] else "unhealthy",
            "uptime_seconds": monitoring_service.get_uptime(),
            "version": "0.6.0",
            **health_results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/health/simple")
async def simple_health_check() -> Dict[str, Any]:
    """
    Simple health check endpoint for load balancers.

    Returns a simple OK status if the service is running.
    """
    return {
        "status": "ok",
        "uptime_seconds": monitoring_service.get_uptime(),
        "version": "0.6.0",
    }


@router.get("/metrics/summary")
async def metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of system metrics.

    Note: For full Prometheus metrics, use the /metrics endpoint
    when prometheus is enabled.
    """
    try:
        # Run a quick health check to get component status
        health_results = await run_all_health_checks()

        summary = {
            "system_status": (
                "operational" if health_results["overall_healthy"] else "degraded"
            ),
            "uptime_seconds": monitoring_service.get_uptime(),
            "components": {
                name: "healthy" if check.get("healthy", False) else "unhealthy"
                for name, check in health_results["checks"].items()
            },
            "summary": health_results["summary"],
            "monitoring_enabled": monitoring_service.metrics.enabled,
            "version": "0.6.0",
        }

        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics summary failed: {str(e)}")


@router.get("/health/{component}")
async def component_health_check(component: str) -> Dict[str, Any]:
    """
    Check health of a specific system component.

    Available components: memory, agents, reasoning, communication, tools, configuration
    """
    try:
        health_results = await run_all_health_checks()

        if component not in health_results["checks"]:
            raise HTTPException(
                status_code=404,
                detail=f"Component '{component}' not found. Available: {list(health_results['checks'].keys())}",
            )

        component_result = health_results["checks"][component]

        return {
            "component": component,
            "status": (
                "healthy" if component_result.get("healthy", False) else "unhealthy"
            ),
            **component_result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Component health check failed: {str(e)}"
        )
