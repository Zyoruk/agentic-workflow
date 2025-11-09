"""
Protected workflow endpoints with JWT authentication.

This module extends the basic workflow endpoints with authentication
and permission checks, ready for Sprint 3-4 integration.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from agentic_workflow.api.auth import User, require_workflow_read, require_workflow_write, require_workflow_execute, require_workflow_delete
from agentic_workflow.api.workflows import (
    VisualWorkflowDefinition,
    WorkflowResponse,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    workflow_storage,
    execution_storage,
    visual_to_workflow,
)

router = APIRouter(prefix="/workflows/protected", tags=["Protected Workflows"])


@router.post("/create", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_protected_workflow(
    workflow: VisualWorkflowDefinition,
    current_user: User = Depends(require_workflow_write)
) -> WorkflowResponse:
    """
    Create a new visual workflow (protected endpoint).
    
    Requires workflow:write scope.
    """
    # Convert visual workflow to internal format
    internal_workflow = visual_to_workflow(workflow)
    
    # Store workflow with owner information
    workflow_data = workflow.model_dump()
    workflow_data["owner"] = current_user.username
    workflow_storage[workflow.id] = workflow_data
    
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        created_at=workflow_data.get("created_at"),
        updated_at=workflow_data.get("updated_at"),
        status="created",
        owner=current_user.username,
    )


@router.get("/", response_model=List[WorkflowResponse])
async def list_protected_workflows(
    current_user: User = Depends(require_workflow_read)
) -> List[WorkflowResponse]:
    """
    List all workflows accessible by the current user (protected endpoint).
    
    Requires workflow:read scope.
    """
    workflows = []
    for wf_id, wf_data in workflow_storage.items():
        # Users can see their own workflows and admins can see all
        if wf_data.get("owner") == current_user.username or "workflow:delete" in current_user.scopes:
            workflows.append(WorkflowResponse(
                id=wf_id,
                name=wf_data.get("name", ""),
                description=wf_data.get("description"),
                created_at=wf_data.get("created_at"),
                updated_at=wf_data.get("updated_at"),
                status="active",
                owner=wf_data.get("owner"),
            ))
    return workflows


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_protected_workflow(
    workflow_id: str,
    current_user: User = Depends(require_workflow_read)
) -> WorkflowResponse:
    """
    Get a specific workflow by ID (protected endpoint).
    
    Requires workflow:read scope.
    """
    if workflow_id not in workflow_storage:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf_data = workflow_storage[workflow_id]
    
    # Check ownership or admin access
    if wf_data.get("owner") != current_user.username and "workflow:delete" not in current_user.scopes:
        raise HTTPException(status_code=403, detail="Access denied to this workflow")
    
    return WorkflowResponse(
        id=workflow_id,
        name=wf_data.get("name", ""),
        description=wf_data.get("description"),
        created_at=wf_data.get("created_at"),
        updated_at=wf_data.get("updated_at"),
        status="active",
        owner=wf_data.get("owner"),
    )


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_protected_workflow(
    workflow_id: str,
    workflow: VisualWorkflowDefinition,
    current_user: User = Depends(require_workflow_write)
) -> WorkflowResponse:
    """
    Update an existing workflow (protected endpoint).
    
    Requires workflow:write scope and ownership.
    """
    if workflow_id not in workflow_storage:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf_data = workflow_storage[workflow_id]
    
    # Check ownership or admin access
    if wf_data.get("owner") != current_user.username and "workflow:delete" not in current_user.scopes:
        raise HTTPException(status_code=403, detail="Cannot update workflow you don't own")
    
    # Update workflow
    from datetime import datetime, timezone
    wf_data.update({
        "name": workflow.name,
        "description": workflow.description,
        "nodes": [n.model_dump() for n in workflow.nodes],
        "edges": [e.model_dump() for e in workflow.edges],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    
    return WorkflowResponse(
        id=workflow_id,
        name=workflow.name,
        description=workflow.description,
        created_at=wf_data.get("created_at"),
        updated_at=wf_data.get("updated_at"),
        status="updated",
        owner=wf_data.get("owner"),
    )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_protected_workflow(
    workflow_id: str,
    current_user: User = Depends(require_workflow_delete)
) -> None:
    """
    Delete a workflow (protected endpoint).
    
    Requires workflow:delete scope (admin only).
    """
    if workflow_id not in workflow_storage:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    del workflow_storage[workflow_id]
    
    # Also clean up executions
    executions_to_delete = [
        exec_id for exec_id, exec_data in execution_storage.items()
        if exec_data.get("workflow_id") == workflow_id
    ]
    for exec_id in executions_to_delete:
        del execution_storage[exec_id]


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_protected_workflow(
    workflow_id: str,
    request: WorkflowExecutionRequest,
    current_user: User = Depends(require_workflow_execute)
) -> WorkflowExecutionResponse:
    """
    Execute a workflow (protected endpoint).
    
    Requires workflow:execute scope.
    """
    if workflow_id not in workflow_storage:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf_data = workflow_storage[workflow_id]
    
    # Check ownership or admin access
    if wf_data.get("owner") != current_user.username and "workflow:delete" not in current_user.scopes:
        raise HTTPException(status_code=403, detail="Cannot execute workflow you don't own")
    
    # Create execution record
    from datetime import datetime, timezone
    import uuid
    
    execution_id = f"exec_{uuid.uuid4().hex[:12]}"
    execution_storage[execution_id] = {
        "id": execution_id,
        "workflow_id": workflow_id,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": request.parameters,
        "owner": current_user.username,
    }
    
    return WorkflowExecutionResponse(
        execution_id=execution_id,
        workflow_id=workflow_id,
        status="queued",
        message=f"Workflow execution queued by {current_user.username}",
        created_at=execution_storage[execution_id]["created_at"],
    )


@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecutionResponse])
async def list_protected_workflow_executions(
    workflow_id: str,
    current_user: User = Depends(require_workflow_read)
) -> List[WorkflowExecutionResponse]:
    """
    List all executions for a specific workflow (protected endpoint).
    
    Requires workflow:read scope.
    """
    if workflow_id not in workflow_storage:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf_data = workflow_storage[workflow_id]
    
    # Check ownership or admin access
    if wf_data.get("owner") != current_user.username and "workflow:delete" not in current_user.scopes:
        raise HTTPException(status_code=403, detail="Cannot view executions for workflow you don't own")
    
    executions = []
    for exec_id, exec_data in execution_storage.items():
        if exec_data.get("workflow_id") == workflow_id:
            executions.append(WorkflowExecutionResponse(
                execution_id=exec_id,
                workflow_id=workflow_id,
                status=exec_data.get("status", "unknown"),
                created_at=exec_data.get("created_at"),
            ))
    
    return executions
