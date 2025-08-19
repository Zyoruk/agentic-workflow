"""FastAPI application for the Agentic Workflow System."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_workflow import __version__, monitoring_service
from agentic_workflow.api.agents import router as agents_router
from agentic_workflow.api.health import router as health_router
from agentic_workflow.api.mcp import router as mcp_router
from agentic_workflow.api.tools import router as tools_router
from agentic_workflow.core.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    setup_logging()
    logger.info(f"Starting Agentic Workflow System v{__version__}")

    # Start monitoring service
    await monitoring_service.start()
    logger.info("System services started")

    yield

    # Shutdown
    await monitoring_service.stop()
    logger.info("System services stopped")


# Create FastAPI application
app = FastAPI(
    title="Agentic Workflow System",
    description="AI-driven autonomous software development workflow system",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(tools_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with system information."""
    return {
        "name": "Agentic Workflow System",
        "version": __version__,
        "status": "operational",
        "endpoints": {
            "health": "/api/v1/health",
            "agents": "/api/v1/agents",
            "mcp": "/api/v1/mcp",
            "tools": "/api/v1/tools",
            "docs": "/docs",
            "metrics": "/metrics" if monitoring_service.metrics.enabled else None,
        },
    }


@app.get("/status")
async def status() -> dict[str, Any]:
    """Quick status endpoint."""
    return {
        "status": "ok",
        "version": __version__,
        "uptime_seconds": monitoring_service.get_uptime(),
    }


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
    return app


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "agentic_workflow.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
