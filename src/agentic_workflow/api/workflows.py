"""
Workflow Visual Builder API.

This module provides REST API endpoints for the visual workflow builder,
allowing users to create, manage, and execute workflows through a graphical interface.

Sprint 1-2: Foundation - API Structure
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from agentic_workflow.core.engine import WorkflowEngine, WorkflowDefinition, WorkflowStep
from agentic_workflow.core.interfaces import ServiceResponse
from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


# ============================================================================
# Pydantic Models for Visual Workflow Builder
# ============================================================================

class NodePosition(BaseModel):
    """Position of a node in the visual canvas."""
    x: float
    y: float


class NodeData(BaseModel):
    """Data associated with a workflow node."""
    agent_type: str = Field(..., description="Type of agent (planning, code_generation, testing, etc.)")
    label: str = Field(..., description="Display label for the node")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific configuration")


class VisualNode(BaseModel):
    """A node in the visual workflow."""
    id: str = Field(..., description="Unique node identifier")
    type: str = Field(default="agent", description="Node type (agent, tool, condition)")
    position: NodePosition
    data: NodeData


class VisualEdge(BaseModel):
    """An edge connecting two nodes in the visual workflow."""
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: Optional[str] = Field(None, description="Edge label (for conditional branches)")


class VisualWorkflowDefinition(BaseModel):
    """Complete visual workflow definition."""
    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    nodes: List[VisualNode] = Field(..., description="List of workflow nodes")
    edges: List[VisualEdge] = Field(..., description="List of edges connecting nodes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WorkflowExecutionRequest(BaseModel):
    """Request to execute a workflow."""
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters for the workflow")


class WorkflowExecutionResponse(BaseModel):
    """Response from workflow execution."""
    execution_id: str
    workflow_id: str
    status: str
    created_at: Optional[str] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WorkflowListItem(BaseModel):
    """Summary of a workflow for list views."""
    id: str
    name: str
    description: Optional[str]
    node_count: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    status: str = "active"
    owner: Optional[str] = None


# ============================================================================
# Workflow Storage (In-memory for Sprint 1-2, will use PostgreSQL later)
# ============================================================================

class WorkflowStorage:
    """Simple in-memory storage for workflows (Sprint 1-2 MVP)."""
    
    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._executions: Dict[str, Dict[str, Any]] = {}
    
    def save_workflow(self, workflow_id: str, workflow: VisualWorkflowDefinition) -> Dict[str, Any]:
        """Save a workflow definition."""
        now = datetime.now(timezone.utc)
        workflow_data = {
            "id": workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": [node.model_dump() for node in workflow.nodes],
            "edges": [edge.model_dump() for edge in workflow.edges],
            "metadata": workflow.metadata,
            "created_at": self._workflows.get(workflow_id, {}).get("created_at", now),
            "updated_at": now,
        }
        self._workflows[workflow_id] = workflow_data
        return workflow_data
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        return list(self._workflows.values())
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False
    
    def save_execution(self, execution_id: str, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save execution data."""
        self._executions[execution_id] = execution_data
        return execution_data
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve execution data."""
        return self._executions.get(execution_id)


# Global storage instance (will be replaced with database in Sprint 3-4)
_storage_instance = WorkflowStorage()

# Expose internal dicts for backward compatibility and protected endpoints
workflow_storage: Dict[str, Dict[str, Any]] = _storage_instance._workflows
execution_storage: Dict[str, Dict[str, Any]] = _storage_instance._executions


# ============================================================================
# Workflow Converter: Visual Graph <-> WorkflowDefinition
# ============================================================================

class WorkflowConverter:
    """Converts between visual workflow format and engine WorkflowDefinition."""
    
    @staticmethod
    def visual_to_workflow(visual: VisualWorkflowDefinition) -> WorkflowDefinition:
        """
        Convert visual workflow to engine WorkflowDefinition.
        
        This performs topological sort of the graph to create a linear execution plan.
        Sprint 1-2: Simple linear conversion
        Sprint 3-4: Handle branching and parallel execution
        """
        # Build adjacency list from edges
        graph: Dict[str, List[str]] = {node.id: [] for node in visual.nodes}
        in_degree: Dict[str, int] = {node.id: 0 for node in visual.nodes}
        
        for edge in visual.edges:
            graph[edge.source].append(edge.target)
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
        
        # Topological sort (Kahn's algorithm)
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        sorted_nodes = []
        
        while queue:
            node_id = queue.pop(0)
            sorted_nodes.append(node_id)
            
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(sorted_nodes) != len(visual.nodes):
            raise ValueError("Workflow contains a cycle, which is not allowed")
        
        # Create workflow steps
        node_map = {node.id: node for node in visual.nodes}
        steps = []
        
        for idx, node_id in enumerate(sorted_nodes):
            node = node_map[node_id]
            step = WorkflowStep(
                id=f"step_{idx}",
                name=node.data.label,
                component=node.data.agent_type,
                action="execute",
                parameters=node.data.config,
            )
            steps.append(step)
        
        return WorkflowDefinition(
            id=f"wf_def_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            name=visual.name,
            description=visual.description or "",
            steps=steps,
        )
    
    @staticmethod
    def workflow_to_visual(workflow: WorkflowDefinition, workflow_id: str) -> Dict[str, Any]:
        """
        Convert engine WorkflowDefinition to visual format.
        
        Creates a linear graph layout for simple workflows.
        Sprint 1-2: Linear layout
        Sprint 3-4: Smart layout algorithms
        """
        nodes = []
        edges = []
        
        # Create nodes with vertical layout
        x_position = 250  # Center horizontally
        y_spacing = 150   # Vertical spacing between nodes
        
        for idx, step in enumerate(workflow.steps):
            node_id = f"node_{idx}"
            node = {
                "id": node_id,
                "type": "agent",
                "position": {"x": x_position, "y": idx * y_spacing + 100},
                "data": {
                    "agent_type": step.service,
                    "label": step.name,
                    "config": step.parameters or {},
                }
            }
            nodes.append(node)
            
            # Create edge to next node
            if idx < len(workflow.steps) - 1:
                edge = {
                    "id": f"edge_{idx}",
                    "source": node_id,
                    "target": f"node_{idx + 1}",
                    "label": None,
                }
                edges.append(edge)
        
        return {
            "id": workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": nodes,
            "edges": edges,
            "metadata": {},
        }


# Module-level helper functions for easier import
def visual_to_workflow(visual: VisualWorkflowDefinition) -> WorkflowDefinition:
    """Convert visual workflow to engine WorkflowDefinition."""
    return WorkflowConverter.visual_to_workflow(visual)


def workflow_to_visual(workflow: WorkflowDefinition, workflow_id: str) -> Dict[str, Any]:
    """Convert engine WorkflowDefinition to visual format."""
    return WorkflowConverter.workflow_to_visual(workflow, workflow_id)


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/visual/create", status_code=status.HTTP_201_CREATED)
async def create_visual_workflow(definition: VisualWorkflowDefinition) -> Dict[str, Any]:
    """
    Create a new visual workflow.
    
    Sprint 1-2: MVP implementation
    - Validates the workflow structure
    - Converts to internal format
    - Stores in memory
    
    Args:
        definition: Visual workflow definition with nodes and edges
    
    Returns:
        Created workflow with assigned ID
    """
    try:
        # Generate workflow ID
        workflow_id = f"wf_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Validate by converting to workflow definition (checks for cycles, etc.)
        workflow_def = WorkflowConverter.visual_to_workflow(definition)
        
        logger.info(f"Creating visual workflow: {definition.name} (ID: {workflow_id})")
        logger.info(f"Workflow has {len(definition.nodes)} nodes and {len(definition.edges)} edges")
        
        # Save to storage
        workflow_data = _storage_instance.save_workflow(workflow_id, definition)
        
        return {
            "workflow_id": workflow_id,
            "name": workflow_data["name"],
            "created_at": workflow_data["created_at"].isoformat(),
            "node_count": len(definition.nodes),
            "message": "Workflow created successfully"
        }
        
    except ValueError as e:
        logger.error(f"Invalid workflow structure: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow structure: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> Dict[str, Any]:
    """
    Get a workflow by ID.
    
    Returns the workflow in visual format (nodes and edges).
    
    Args:
        workflow_id: Unique workflow identifier
    
    Returns:
        Visual workflow definition
    """
    workflow = _storage_instance.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    return workflow


@router.get("/")
async def list_workflows() -> List[WorkflowListItem]:
    """
    List all workflows.
    
    Returns a summary of all workflows for display in a list view.
    
    Returns:
        List of workflow summaries
    """
    workflows = list(workflow_storage.values())
    
    return [
        WorkflowListItem(
            id=wf["id"],
            name=wf["name"],
            description=wf.get("description"),
            node_count=len(wf.get("nodes", [])),
            created_at=wf["created_at"],
            updated_at=wf["updated_at"],
            created_by=wf.get("metadata", {}).get("created_by"),
        )
        for wf in workflows
    ]


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, definition: VisualWorkflowDefinition) -> Dict[str, Any]:
    """
    Update an existing workflow.
    
    Args:
        workflow_id: Workflow to update
        definition: New workflow definition
    
    Returns:
        Updated workflow data
    """
    existing = _storage_instance.get_workflow(workflow_id)
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    try:
        # Validate new definition
        workflow_def = WorkflowConverter.visual_to_workflow(definition)
        
        logger.info(f"Updating workflow: {workflow_id}")
        
        # Save updated version
        workflow_data = _storage_instance.save_workflow(workflow_id, definition)
        
        return {
            "workflow_id": workflow_id,
            "name": workflow_data["name"],
            "updated_at": workflow_data["updated_at"].isoformat(),
            "message": "Workflow updated successfully"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow structure: {str(e)}"
        )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str):
    """
    Delete a workflow.
    
    Args:
        workflow_id: Workflow to delete
    """
    if not _storage_instance.delete_workflow(workflow_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    logger.info(f"Deleted workflow: {workflow_id}")


@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, request: WorkflowExecutionRequest) -> WorkflowExecutionResponse:
    """
    Execute a visual workflow.
    
    Sprint 1-2: Basic synchronous execution
    Sprint 5-6: Add real-time progress tracking
    
    Args:
        workflow_id: Workflow to execute
        request: Execution parameters
    
    Returns:
        Execution result
    """
    # Get workflow
    workflow_data = _storage_instance.get_workflow(workflow_id)
    
    if not workflow_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )
    
    try:
        # Convert visual workflow to engine format
        visual_def = VisualWorkflowDefinition(
            name=workflow_data["name"],
            description=workflow_data.get("description"),
            nodes=[VisualNode(**node) for node in workflow_data["nodes"]],
            edges=[VisualEdge(**edge) for edge in workflow_data["edges"]],
            metadata=workflow_data.get("metadata", {}),
        )
        
        workflow_def = WorkflowConverter.visual_to_workflow(visual_def)
        
        # Generate execution ID
        execution_id = f"exec_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(f"Executing workflow {workflow_id} (execution: {execution_id})")
        
        # Create execution record
        started_at = datetime.now(timezone.utc)
        execution_data = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": "running",
            "started_at": started_at,
            "completed_at": None,
            "result": None,
            "error": None,
        }
        _storage_instance.save_execution(execution_id, execution_data)
        
        # Execute workflow (Sprint 1-2: simplified execution)
        # In Sprint 3-4, this will use the actual WorkflowEngine
        try:
            # Placeholder execution logic
            result = {
                "steps_completed": len(workflow_def.steps),
                "workflow_name": workflow_def.name,
                "message": "Workflow executed successfully (MVP mode)",
            }
            
            completed_at = datetime.now(timezone.utc)
            execution_data.update({
                "status": "completed",
                "completed_at": completed_at,
                "result": result,
            })
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution_data.update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc),
                "error": str(e),
            })
        
        _storage_instance.save_execution(execution_id, execution_data)
        
        return WorkflowExecutionResponse(**execution_data)
        
    except Exception as e:
        logger.error(f"Error executing workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(workflow_id: str) -> List[WorkflowExecutionResponse]:
    """
    List all executions of a workflow.
    
    Args:
        workflow_id: Workflow ID
    
    Returns:
        List of executions
    """
    # For Sprint 1-2, return from in-memory storage
    # Sprint 3-4: Query from database with pagination
    executions = [
        exec_data for exec_data in execution_storage.values()
        if exec_data["workflow_id"] == workflow_id
    ]
    
    return [WorkflowExecutionResponse(**exec_data) for exec_data in executions]


@router.get("/executions/{execution_id}")
async def get_execution_status(execution_id: str) -> WorkflowExecutionResponse:
    """
    Get execution status.
    
    Args:
        execution_id: Execution ID
    
    Returns:
        Execution status and result
    """
    execution = _storage_instance.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )
    
    return WorkflowExecutionResponse(**execution)
