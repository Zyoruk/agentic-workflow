"""Tests for workflow orchestration API endpoints."""

import pytest
import uuid
from io import BytesIO

from agentic_workflow.core.tenant import get_tenant_service, TierType
from agentic_workflow.core.file_attachment import FileService
from agentic_workflow.api.workflow_orchestration import (
    WorkflowExecutionRequest,
    execute_workflow,
    execute_workflow_json,
    get_workflow_status,
    list_executions,
)


@pytest.mark.asyncio
class TestWorkflowOrchestration:
    """Tests for workflow orchestration endpoints."""



    async def test_execute_workflow_simple_prompt(self):
        """Test executing workflow with simple prompt."""
        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.STANDARD,
        )

        result = await execute_workflow(
            tenant_id=tenant.id,
            prompt="Create a simple REST API for user management",
            files=None,
            preferences=None,
            agent_type="planning",
        )

        assert result["tenant_id"] == tenant.id
        assert result["status"] in ["completed", "failed"]
        assert result["prompt_info"]["total_chunks"] >= 1
        assert result["files_processed"] == 0
        assert "agent_results" in result

    async def test_execute_workflow_nonexistent_tenant(self):
        """Test executing workflow with nonexistent tenant fails."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await execute_workflow(
                tenant_id="nonexistent",
                prompt="Test prompt",
                files=None,
                preferences=None,
                agent_type="planning",
            )
        
        assert exc_info.value.status_code == 404

    async def test_execute_workflow_free_tier_no_files(self):
        """Test free tier cannot upload files."""
        from fastapi import HTTPException
        from unittest.mock import Mock

        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Free Tenant {id(self)}",
            tier=TierType.FREE,
        )

        # Create mock upload file
        mock_file = Mock()
        mock_file.filename = "test.txt"
        mock_file.content_type = "text/plain"
        mock_file.read = lambda: b"test content"

        with pytest.raises(HTTPException) as exc_info:
            await execute_workflow(
                tenant_id=tenant.id,
                prompt="Test",
                files=[mock_file],
                preferences=None,
                agent_type="planning",
            )
        
        assert exc_info.value.status_code == 403
        assert "does not support file attachments" in str(exc_info.value.detail)

    async def test_execute_workflow_prompt_too_large(self):
        """Test prompt exceeding tier limit fails."""
        from fastapi import HTTPException

        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Free Tenant {id(self)}",
            tier=TierType.FREE,  # 10K token limit
        )

        # Create a very large prompt
        large_prompt = "A" * 100000  # ~25K tokens

        with pytest.raises(HTTPException) as exc_info:
            await execute_workflow(
                tenant_id=tenant.id,
                prompt=large_prompt,
                files=None,
                preferences=None,
                agent_type="planning",
            )
        
        assert exc_info.value.status_code == 400
        assert "too large" in str(exc_info.value.detail).lower()

    async def test_execute_workflow_with_preferences(self):
        """Test executing workflow with preferences."""
        import json

        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.STANDARD,
        )

        # Set tenant preference
        await tenant_service.set_preference(
            tenant.id,
            "default_model",
            {"model": "gpt-4"},
        )

        # Override with request preference
        prefs_json = json.dumps({"output_format": "detailed"})

        result = await execute_workflow(
            tenant_id=tenant.id,
            prompt="Test prompt",
            files=None,
            preferences=prefs_json,
            agent_type="planning",
        )

        # Should have both tenant and request preferences
        assert len(result["preferences_applied"]) >= 2
        assert "default_model" in result["preferences_applied"]
        assert "output_format" in result["preferences_applied"]

    async def test_execute_workflow_quota_exceeded(self):
        """Test workflow fails when quota exceeded."""
        from fastapi import HTTPException

        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.FREE,  # 50 requests/day limit
        )

        # Exhaust quota
        await tenant_service.track_usage(tenant.id, requests=60)

        with pytest.raises(HTTPException) as exc_info:
            await execute_workflow(
                tenant_id=tenant.id,
                prompt="Test",
                files=None,
                preferences=None,
                agent_type="planning",
            )
        
        assert exc_info.value.status_code == 429
        assert "quota" in str(exc_info.value.detail).lower()

    async def test_execute_workflow_json_endpoint(self):
        """Test JSON endpoint for workflow execution."""
        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.STANDARD,
        )

        request = WorkflowExecutionRequest(
            tenant_id=tenant.id,
            prompt="Create a REST API",
            file_ids=None,
            preferences={"output_format": "detailed"},
            agent_type="planning",
        )

        result = await execute_workflow_json(request)

        assert result["tenant_id"] == tenant.id
        assert result["status"] in ["completed", "failed"]
        assert result["preferences_applied"]["output_format"] == "detailed"

    async def test_execute_workflow_json_with_files(self):
        """Test JSON endpoint with file IDs."""
        from agentic_workflow.core.file_attachment import FileService

        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        file_service = FileService(tenant_service=tenant_service)
        
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.STANDARD,
        )

        # Upload a file first
        file_attachment = await file_service.upload_file(
            tenant_id=tenant.id,
            filename="test.txt",
            content=b"Test content",
            content_type="text/plain",
        )

        request = WorkflowExecutionRequest(
            tenant_id=tenant.id,
            prompt="Analyze this file",
            file_ids=[file_attachment.id],
            preferences=None,
            agent_type="planning",
        )

        result = await execute_workflow_json(request)

        assert result["files_processed"] == 1

    async def test_execute_workflow_json_invalid_file_id(self):
        """Test JSON endpoint with invalid file ID fails."""
        from fastapi import HTTPException

        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.STANDARD,
        )

        request = WorkflowExecutionRequest(
            tenant_id=tenant.id,
            prompt="Test",
            file_ids=["nonexistent"],
            preferences=None,
            agent_type="planning",
        )

        with pytest.raises(HTTPException) as exc_info:
            await execute_workflow_json(request)
        
        assert exc_info.value.status_code == 404

    async def test_execute_workflow_json_file_access_denied(self):
        """Test JSON endpoint denies access to other tenant's files."""
        from fastapi import HTTPException
        from agentic_workflow.core.file_attachment import FileService

        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        file_service = FileService(tenant_service=tenant_service)
        
        tenant1 = await tenant_service.create_tenant(
            name=f"Tenant 1 {id(self)}",
            tier=TierType.STANDARD,
        )
        tenant2 = await tenant_service.create_tenant(
            name=f"Tenant 2 {id(self)}",
            tier=TierType.STANDARD,
        )

        # Upload file for tenant1
        file_attachment = await file_service.upload_file(
            tenant_id=tenant1.id,
            filename="test.txt",
            content=b"Test content",
            content_type="text/plain",
        )

        # Try to access from tenant2
        request = WorkflowExecutionRequest(
            tenant_id=tenant2.id,
            prompt="Test",
            file_ids=[file_attachment.id],
            preferences=None,
            agent_type="planning",
        )

        with pytest.raises(HTTPException) as exc_info:
            await execute_workflow_json(request)
        
        assert exc_info.value.status_code == 403

    async def test_get_workflow_status(self):
        """Test getting workflow status."""
        from fastapi import HTTPException

        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.STANDARD,
        )

        # Execute workflow
        result = await execute_workflow(
            tenant_id=tenant.id,
            prompt="Test",
            files=None,
            preferences=None,
            agent_type="planning",
        )

        execution_id = result["execution_id"]

        # Get status
        status = await get_workflow_status(execution_id)

        assert status["execution_id"] == execution_id
        assert "status" in status
        assert "progress" in status

    async def test_get_workflow_status_not_found(self):
        """Test getting status of nonexistent execution fails."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_workflow_status("nonexistent")
        
        assert exc_info.value.status_code == 404

    async def test_list_executions(self):
        """Test listing executions for a tenant."""
        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.STANDARD,
        )

        # Execute a couple workflows
        await execute_workflow(
            tenant_id=tenant.id,
            prompt="Test 1",
            files=None,
            preferences=None,
            agent_type="planning",
        )
        await execute_workflow(
            tenant_id=tenant.id,
            prompt="Test 2",
            files=None,
            preferences=None,
            agent_type="planning",
        )

        # List executions
        result = await list_executions(tenant.id, limit=10)

        assert result["tenant_id"] == tenant.id
        assert result["total"] == 2
        assert len(result["executions"]) == 2

    async def test_prompt_chunking(self):
        """Test large prompts are automatically chunked."""
        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.BUSINESS,  # Large token limit
        )

        # Create a prompt that will need chunking
        large_prompt = "Test sentence. " * 5000  # ~25K tokens

        result = await execute_workflow(
            tenant_id=tenant.id,
            prompt=large_prompt,
            files=None,
            preferences=None,
            agent_type="planning",
        )

        # Should be chunked
        assert result["prompt_info"]["total_chunks"] > 1
        assert result["prompt_info"]["estimated_tokens"] > 10000

    async def test_usage_tracking(self):
        """Test usage is tracked for workflow executions."""
        from agentic_workflow.core.tenant import get_tenant_service
        tenant_service = get_tenant_service()
        tenant = await tenant_service.create_tenant(
            name=f"Test Corp {id(self)}",
            tier=TierType.STANDARD,
        )

        # Execute workflow
        await execute_workflow(
            tenant_id=tenant.id,
            prompt="Test prompt for usage tracking",
            files=None,
            preferences=None,
            agent_type="planning",
        )

        # Check usage
        usage = await tenant_service.get_usage(tenant.id)
        assert usage is not None
        assert usage.requests_count >= 1
        assert usage.tokens_used > 0
