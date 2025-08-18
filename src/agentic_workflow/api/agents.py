"""API endpoints for agent management and execution."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from agentic_workflow.agents import Agent, create_agent, get_available_agent_types
from agentic_workflow.agents.base import AgentTask
from agentic_workflow.core.exceptions import AgentError, ValidationError
from agentic_workflow.core.logging_config import get_logger

# Create router
router = APIRouter(prefix="/agents", tags=["agents"])
logger = get_logger(__name__)

# Global agent registry for managing active agents
_active_agents: Dict[str, Agent] = {}


# Request/Response Models
class AgentCreateRequest(BaseModel):
    """Request to create a new agent."""

    agent_type: str = Field(..., description="Type of agent to create")
    agent_id: Optional[str] = Field(None, description="Optional agent ID")
    config: Optional[Dict[str, Any]] = Field(
        default={}, description="Agent configuration"
    )


class AgentResponse(BaseModel):
    """Standard agent response."""

    agent_id: str
    agent_type: str
    status: str
    capabilities: List[str]
    created_at: str


class TaskExecutionRequest(BaseModel):
    """Request to execute a task with an agent."""

    prompt: str = Field(..., description="Task prompt or description")
    language: str = Field(default="python", description="Programming language")
    style: str = Field(default="clean", description="Code style")
    include_tests: bool = Field(default=False, description="Include test generation")
    include_docs: bool = Field(default=True, description="Include documentation")
    complexity: str = Field(default="medium", description="Complexity level")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context"
    )


class TaskExecutionResponse(BaseModel):
    """Response from task execution."""

    success: bool
    task_id: str
    agent_id: str
    execution_time: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    steps_taken: List[Dict[str, Any]] = []


class PlanningRequest(BaseModel):
    """Request for agent planning."""

    objective: str = Field(..., description="High-level objective to plan for")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Planning context"
    )


class PlanningResponse(BaseModel):
    """Response from agent planning."""

    success: bool
    agent_id: str
    objective: str
    tasks: List[Dict[str, Any]]
    total_tasks: int


class AgentHealthResponse(BaseModel):
    """Agent health check response."""

    agent_id: str
    status: str
    is_healthy: bool
    execution_count: int
    dependencies: List[str]
    last_check: str


# API Endpoints
@router.get("/types", response_model=List[str])
async def get_agent_types() -> List[str]:
    """Get list of available agent types."""
    try:
        types = get_available_agent_types()
        logger.info(f"Retrieved {len(types)} available agent types")
        return types
    except Exception as e:
        logger.error(f"Failed to get agent types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent types: {e}",
        )


@router.post(
    "/create", response_model=AgentResponse, status_code=status.HTTP_201_CREATED
)
async def create_new_agent(request: AgentCreateRequest) -> AgentResponse:
    """Create a new agent instance."""
    try:
        logger.info(f"Creating agent of type: {request.agent_type}")

        # Create agent with proper type handling
        agent_id = request.agent_id or f"{request.agent_type}_agent"
        config = request.config or {}

        agent = create_agent(
            agent_type=request.agent_type,
            agent_id=agent_id,
            config=config,
        )

        # Initialize and start agent
        await agent.initialize()
        await agent.start()

        # Store in active agents registry
        _active_agents[agent.agent_id] = agent

        logger.info(f"Successfully created and started agent: {agent.agent_id}")

        return AgentResponse(
            agent_id=agent.agent_id,
            agent_type=request.agent_type,
            status=agent.status.value,
            capabilities=agent.get_capabilities(),
            created_at=datetime.now(UTC).isoformat(),
        )

    except ValueError as e:
        logger.error(f"Invalid agent type: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AgentError as e:
        logger.error(f"Agent creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent creation failed: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error creating agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {e}",
        )


@router.get("/", response_model=List[AgentResponse])
async def list_agents() -> List[AgentResponse]:
    """List all active agents."""
    try:
        agents = []
        for agent in _active_agents.values():
            agents.append(
                AgentResponse(
                    agent_id=agent.agent_id,
                    agent_type=agent.__class__.__name__.replace("Agent", "").lower(),
                    status=agent.status.value,
                    capabilities=agent.get_capabilities(),
                    created_at=datetime.now(
                        UTC
                    ).isoformat(),  # Note: actual creation time would be stored
                )
            )

        logger.info(f"Listed {len(agents)} active agents")
        return agents

    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {e}",
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str) -> AgentResponse:
    """Get information about a specific agent."""
    try:
        agent = _get_agent_or_404(agent_id)

        return AgentResponse(
            agent_id=agent.agent_id,
            agent_type=agent.__class__.__name__.replace("Agent", "").lower(),
            status=agent.status.value,
            capabilities=agent.get_capabilities(),
            created_at=datetime.now(UTC).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve agent: {e}",
        )


@router.post("/{agent_id}/execute", response_model=TaskExecutionResponse)
async def execute_task(
    agent_id: str, request: TaskExecutionRequest
) -> TaskExecutionResponse:
    """Execute a task with the specified agent."""
    try:
        agent = _get_agent_or_404(agent_id)

        logger.info(f"Executing task with agent {agent_id}: {request.prompt[:100]}...")

        # Create agent task
        task = AgentTask(
            type="generate_code",
            prompt=request.prompt,
            language=request.language,
            style=request.style,
            include_tests=request.include_tests,
            include_docs=request.include_docs,
            complexity=request.complexity,
            context=request.context,
        )

        # Execute task safely
        result = await agent.safe_execute(task)

        logger.info(
            f"Task execution completed for agent {agent_id}: success={result.success}"
        )

        return TaskExecutionResponse(
            success=result.success,
            task_id=result.task_id,
            agent_id=result.agent_id,
            execution_time=result.execution_time,
            result=result.data if result.success else None,
            error=result.error if not result.success else None,
            steps_taken=result.steps_taken,
        )

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Task validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid task parameters: {e}",
        )
    except AgentError as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during task execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {e}",
        )


@router.post("/{agent_id}/plan", response_model=PlanningResponse)
async def plan_objective(agent_id: str, request: PlanningRequest) -> PlanningResponse:
    """Create an execution plan for an objective."""
    try:
        agent = _get_agent_or_404(agent_id)

        logger.info(f"Planning objective with agent {agent_id}: {request.objective}")

        # Create execution plan
        tasks = await agent.plan(request.objective, request.context)

        # Convert tasks to serializable format
        task_list = [dict(task) for task in tasks]

        logger.info(f"Planning completed for agent {agent_id}: {len(tasks)} tasks")

        return PlanningResponse(
            success=True,
            agent_id=agent_id,
            objective=request.objective,
            tasks=task_list,
            total_tasks=len(tasks),
        )

    except HTTPException:
        raise
    except AgentError as e:
        logger.error(f"Planning failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Planning failed: {e}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during planning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {e}",
        )


@router.get("/{agent_id}/health", response_model=AgentHealthResponse)
async def check_agent_health(agent_id: str) -> AgentHealthResponse:
    """Check the health status of an agent."""
    try:
        agent = _get_agent_or_404(agent_id)

        # Perform health check
        health_result = await agent.health_check()

        # Safely extract data with None checking
        data = health_result.data or {}
        status_value = data.get("status", "unknown") if data else "unknown"
        execution_count = data.get("execution_count", 0) if data else 0
        dependencies = data.get("dependencies", []) if data else []

        return AgentHealthResponse(
            agent_id=agent_id,
            status=status_value,
            is_healthy=health_result.success,
            execution_count=execution_count,
            dependencies=dependencies,
            last_check=datetime.now(UTC).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {e}",
        )


@router.get("/{agent_id}/history")
async def get_agent_history(agent_id: str) -> List[Dict[str, Any]]:
    """Get execution history for an agent."""
    try:
        agent = _get_agent_or_404(agent_id)

        history = agent.get_execution_history()
        logger.info(f"Retrieved {len(history)} execution records for agent {agent_id}")

        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {e}",
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_agent(agent_id: str) -> None:
    """Stop and remove an agent."""
    try:
        agent = _get_agent_or_404(agent_id)

        logger.info(f"Stopping agent: {agent_id}")

        # Stop the agent
        await agent.stop()

        # Remove from active agents registry
        del _active_agents[agent_id]

        logger.info(f"Successfully stopped and removed agent: {agent_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop agent: {e}",
        )


# Utility Functions
def _get_agent_or_404(agent_id: str) -> Agent:
    """Get agent by ID or raise 404."""
    if agent_id not in _active_agents:
        logger.warning(f"Agent not found: {agent_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return _active_agents[agent_id]


# Health check endpoint for the API itself
@router.get("/health", include_in_schema=False)
async def api_health() -> Dict[str, Any]:
    """Health check for the agents API."""
    return {
        "status": "healthy",
        "active_agents": len(_active_agents),
        "timestamp": datetime.now(UTC).isoformat(),
    }
