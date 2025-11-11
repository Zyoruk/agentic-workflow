"""
Workflow Orchestration API - End-to-End Workflow Execution.

This module provides the seamless user experience endpoint that combines:
1. Prompt processing with chunking
2. File attachment handling
3. Tenant preferences application
4. Agent workflow execution
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from agentic_workflow.agents.planning import PlanningAgent
from agentic_workflow.agents.base import AgentTask
from agentic_workflow.core.tenant import TenantService, get_tenant_service
from agentic_workflow.core.file_attachment import FileService, get_file_service, ChunkingService
from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/workflow", tags=["workflow-orchestration"])


# Request/Response Models

class WorkflowExecutionRequest(BaseModel):
    """Request model for workflow execution (JSON alternative)."""

    tenant_id: str = Field(..., description="Tenant ID")
    prompt: str = Field(..., description="User prompt of any size")
    file_ids: Optional[List[str]] = Field(None, description="Optional file IDs to use as context")
    preferences: Optional[Dict[str, Any]] = Field(None, description="Optional preferences to override tenant defaults")
    agent_type: str = Field(default="planning", description="Agent type to execute (planning, code_generation, etc.)")


class PromptChunkInfo(BaseModel):
    """Information about prompt chunking."""

    total_chunks: int
    chunk_indices: List[int]
    estimated_tokens: int


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution."""

    execution_id: str
    tenant_id: str
    status: str
    prompt_info: PromptChunkInfo
    files_processed: int
    preferences_applied: Dict[str, Any]
    agent_results: Dict[str, Any]
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status check."""

    execution_id: str
    status: str
    progress: float
    current_step: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


# In-memory execution tracking (replace with database in production)
_executions: Dict[str, Dict[str, Any]] = {}


@router.post(
    "/execute",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_workflow(
    tenant_id: str = Form(...),
    prompt: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    preferences: Optional[str] = Form(None),  # JSON string
    agent_type: str = Form(default="planning"),
) -> Dict[str, Any]:
    """Execute end-to-end workflow with prompt, files, and preferences.

    This endpoint provides a seamless experience where users can:
    1. Send their prompt (any size)
    2. Attach files as context
    3. Send preferences for the workflow

    Args:
        tenant_id: Tenant ID for isolation and quota management
        prompt: User prompt of any size (will be chunked automatically)
        files: Optional file attachments to use as context
        preferences: Optional JSON string of preferences to override defaults
        agent_type: Agent type to execute (planning, code_generation, etc.)

    Returns:
        Workflow execution response with results
    """
    now = datetime.now(timezone.utc)
    execution_id = f"exec_{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond:06d}_{tenant_id[:8]}"
    
    try:
        # Initialize services (use singleton pattern for consistency)
        tenant_service = get_tenant_service()
        file_service = get_file_service()
        chunking_service = ChunkingService()

        # Step 1: Validate tenant and check quota
        tenant = await tenant_service.get_tenant(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found: {tenant_id}",
            )

        quota_check = await tenant_service.check_quota(tenant_id)
        if not quota_check["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quota exceeded: {quota_check['reason']}",
            )

        logger.info(f"Starting workflow execution {execution_id} for tenant {tenant_id}")

        # Step 2: Process and chunk prompt
        logger.info(f"Processing prompt ({len(prompt)} chars)")
        limits = tenant.get_limits()
        
        # Check prompt size against tier limit
        estimated_tokens = chunking_service.estimate_tokens(prompt)
        if estimated_tokens > limits.max_prompt_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt too large: {estimated_tokens} tokens exceeds limit of {limits.max_prompt_size}",
            )

        # Chunk the prompt if needed
        prompt_chunks = chunking_service.chunk_text(prompt)
        logger.info(f"Prompt chunked into {len(prompt_chunks)} pieces")

        # Step 3: Process file attachments
        file_ids = []
        files_processed = 0
        if files:
            if not limits.file_attachments:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Tenant tier '{tenant.tier}' does not support file attachments",
                )

            for file in files:
                content = await file.read()
                file_attachment = await file_service.upload_file(
                    tenant_id=tenant_id,
                    filename=file.filename or "unnamed",
                    content=content,
                    content_type=file.content_type or "application/octet-stream",
                    retention_days=limits.storage_days,
                )
                file_ids.append(file_attachment.id)
                files_processed += 1
            
            logger.info(f"Processed {files_processed} file attachments")

        # Step 4: Load and merge preferences
        import json
        preferences_dict = {}
        
        # Load tenant default preferences
        if limits.preference_storage:
            tenant_prefs = await tenant_service.get_all_preferences(tenant_id)
            preferences_dict = {
                key: pref.preference_value
                for key, pref in tenant_prefs.items()
            }
        
        # Override with request-specific preferences
        if preferences:
            try:
                request_prefs = json.loads(preferences)
                preferences_dict.update(request_prefs)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in preferences, skipping")

        logger.info(f"Applied {len(preferences_dict)} preferences")

        # Step 5: Prepare context for agent execution
        context = {
            "prompt": prompt,
            "prompt_chunks": [
                {
                    "index": chunk.metadata.chunk_index,
                    "content": chunk.content,
                    "tokens": chunk.metadata.tokens,
                }
                for chunk in prompt_chunks
            ],
            "file_ids": file_ids,
            "preferences": preferences_dict,
            "tenant_tier": tenant.tier.value,
        }

        # Step 6: Execute agent workflow
        logger.info(f"Executing {agent_type} agent")
        
        # For now, we'll use the planning agent as the default
        # In production, this would route to the appropriate agent
        agent = PlanningAgent(agent_id=f"{agent_type}_{execution_id}")
        
        task = AgentTask(
            task_id=execution_id,
            agent_id=agent.agent_id,
            objective=prompt,
            context=context,
        )

        try:
            result = await agent.execute(task)
            agent_results = {
                "success": result.success,
                "result": result.result,
                "metadata": result.metadata,
            }
            execution_status = "completed"
            error_msg = None
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            agent_results = {"error": str(e)}
            execution_status = "failed"
            error_msg = str(e)

        # Step 7: Track usage
        await tenant_service.track_usage(
            tenant_id,
            requests=1,
            tokens=estimated_tokens,
            files=files_processed,
        )

        # Step 8: Store execution record
        completed_at = datetime.now(timezone.utc).isoformat()
        execution_record = {
            "execution_id": execution_id,
            "tenant_id": tenant_id,
            "status": execution_status,
            "prompt_info": {
                "total_chunks": len(prompt_chunks),
                "chunk_indices": [c.metadata.chunk_index for c in prompt_chunks],
                "estimated_tokens": estimated_tokens,
            },
            "files_processed": files_processed,
            "preferences_applied": preferences_dict,
            "agent_results": agent_results,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": completed_at,
            "error": error_msg,
        }
        
        _executions[execution_id] = execution_record
        logger.info(f"Workflow execution {execution_id} completed: {execution_status}")

        return execution_record

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}",
        )


@router.post(
    "/execute-json",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_workflow_json(
    request: WorkflowExecutionRequest,
) -> Dict[str, Any]:
    """Execute workflow with JSON request (alternative to multipart form).

    This endpoint provides the same functionality as /execute but accepts
    JSON input instead of multipart form data. Files must be uploaded
    separately and referenced by ID.

    Args:
        request: Workflow execution request

    Returns:
        Workflow execution response with results
    """
    now = datetime.now(timezone.utc)
    execution_id = f"exec_{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond:06d}_{request.tenant_id[:8]}"
    
    try:
        # Initialize services (use singleton pattern for consistency)
        tenant_service = get_tenant_service()
        file_service = get_file_service()
        chunking_service = ChunkingService()

        # Step 1: Validate tenant and check quota
        tenant = await tenant_service.get_tenant(request.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found: {request.tenant_id}",
            )

        quota_check = await tenant_service.check_quota(request.tenant_id)
        if not quota_check["allowed"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quota exceeded: {quota_check['reason']}",
            )

        # Step 2: Process and chunk prompt
        limits = tenant.get_limits()
        estimated_tokens = chunking_service.estimate_tokens(request.prompt)
        
        if estimated_tokens > limits.max_prompt_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt too large: {estimated_tokens} tokens exceeds limit of {limits.max_prompt_size}",
            )

        prompt_chunks = chunking_service.chunk_text(request.prompt)

        # Step 3: Validate file IDs
        files_processed = 0
        if request.file_ids:
            if not limits.file_attachments:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Tenant tier '{tenant.tier}' does not support file attachments",
                )

            for file_id in request.file_ids:
                file_attachment = await file_service.get_file(file_id)
                if not file_attachment:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"File not found: {file_id}",
                    )
                if file_attachment.tenant_id != request.tenant_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied to file: {file_id}",
                    )
                files_processed += 1

        # Step 4: Load and merge preferences
        preferences_dict = {}
        if limits.preference_storage:
            tenant_prefs = await tenant_service.get_all_preferences(request.tenant_id)
            preferences_dict = {
                key: pref.preference_value
                for key, pref in tenant_prefs.items()
            }
        
        if request.preferences:
            preferences_dict.update(request.preferences)

        # Step 5: Prepare context and execute
        context = {
            "prompt": request.prompt,
            "prompt_chunks": [
                {
                    "index": chunk.metadata.chunk_index,
                    "content": chunk.content,
                    "tokens": chunk.metadata.tokens,
                }
                for chunk in prompt_chunks
            ],
            "file_ids": request.file_ids or [],
            "preferences": preferences_dict,
            "tenant_tier": tenant.tier.value,
        }

        agent = PlanningAgent(agent_id=f"{request.agent_type}_{execution_id}")
        task = AgentTask(
            task_id=execution_id,
            agent_id=agent.agent_id,
            objective=request.prompt,
            context=context,
        )

        try:
            result = await agent.execute(task)
            agent_results = {
                "success": result.success,
                "result": result.result,
                "metadata": result.metadata,
            }
            execution_status = "completed"
            error_msg = None
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            agent_results = {"error": str(e)}
            execution_status = "failed"
            error_msg = str(e)

        # Track usage
        await tenant_service.track_usage(
            request.tenant_id,
            requests=1,
            tokens=estimated_tokens,
            files=files_processed,
        )

        # Store execution record
        execution_record = {
            "execution_id": execution_id,
            "tenant_id": request.tenant_id,
            "status": execution_status,
            "prompt_info": {
                "total_chunks": len(prompt_chunks),
                "chunk_indices": [c.metadata.chunk_index for c in prompt_chunks],
                "estimated_tokens": estimated_tokens,
            },
            "files_processed": files_processed,
            "preferences_applied": preferences_dict,
            "agent_results": agent_results,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error": error_msg,
        }
        
        _executions[execution_id] = execution_record

        return execution_record

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}",
        )


@router.get(
    "/status/{execution_id}",
    response_model=WorkflowStatusResponse,
)
async def get_workflow_status(execution_id: str) -> Dict[str, Any]:
    """Get status of a workflow execution.

    Args:
        execution_id: Execution ID to check

    Returns:
        Workflow status information
    """
    if execution_id not in _executions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution not found: {execution_id}",
        )

    execution = _executions[execution_id]
    
    # Calculate progress
    if execution["status"] == "completed":
        progress = 1.0
    elif execution["status"] == "failed":
        progress = 0.0
    else:
        progress = 0.5  # In progress

    return {
        "execution_id": execution_id,
        "status": execution["status"],
        "progress": progress,
        "current_step": execution.get("current_step"),
        "results": execution.get("agent_results"),
    }


@router.get("/executions/{tenant_id}")
async def list_executions(
    tenant_id: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """List workflow executions for a tenant.

    Args:
        tenant_id: Tenant ID
        limit: Maximum number of results to return

    Returns:
        List of executions
    """
    tenant_executions = [
        {
            "execution_id": exec_id,
            "status": exec_data["status"],
            "created_at": exec_data["created_at"],
            "completed_at": exec_data.get("completed_at"),
        }
        for exec_id, exec_data in _executions.items()
        if exec_data["tenant_id"] == tenant_id
    ]

    # Sort by created_at descending
    tenant_executions.sort(
        key=lambda x: x["created_at"],
        reverse=True
    )

    return {
        "tenant_id": tenant_id,
        "executions": tenant_executions[:limit],
        "total": len(tenant_executions),
    }


@router.delete("/executions/{execution_id}")
async def delete_execution(execution_id: str) -> Dict[str, Any]:
    """Delete a workflow execution record.

    Args:
        execution_id: Execution ID to delete

    Returns:
        Success message
    """
    if execution_id not in _executions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution not found: {execution_id}",
        )

    del _executions[execution_id]

    return {
        "execution_id": execution_id,
        "message": "Execution deleted successfully",
    }
