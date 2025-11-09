"""
Tests for protected workflow endpoints with authentication.
"""

import pytest
from fastapi.testclient import TestClient

from agentic_workflow.api.main import app
from agentic_workflow.api.workflows import workflow_storage, execution_storage
from agentic_workflow.api.auth import create_access_token


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear workflow and execution storage before each test."""
    workflow_storage.clear()
    execution_storage.clear()
    yield
    workflow_storage.clear()
    execution_storage.clear()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Generate an admin token with all scopes."""
    return create_access_token(
        data={
            "sub": "admin",
            "scopes": ["workflow:read", "workflow:write", "workflow:execute", "workflow:delete"]
        }
    )


@pytest.fixture
def user_token():
    """Generate a regular user token with limited scopes."""
    return create_access_token(
        data={
            "sub": "user",
            "scopes": ["workflow:read", "workflow:execute"]
        }
    )


@pytest.fixture
def sample_workflow():
    """Sample workflow definition."""
    return {
        "id": "wf_test123",
        "name": "Test Workflow",
        "description": "A test workflow",
        "nodes": [
            {
                "id": "node_0",
                "type": "agent",
                "position": {"x": 250, "y": 100},
                "data": {
                    "agent_type": "code_generation",
                    "label": "Generate Code",
                    "config": {"temperature": 0.2}
                }
            }
        ],
        "edges": []
    }


class TestProtectedWorkflowAPI:
    """Test suite for protected workflow API endpoints."""
    
    def test_create_workflow_with_admin(self, client, admin_token, sample_workflow):
        """Test creating a workflow with admin credentials."""
        response = client.post(
            "/api/v1/workflows/protected/create",
            json=sample_workflow,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "wf_test123"
        assert data["name"] == "Test Workflow"
        assert data["owner"] == "admin"
    
    def test_create_workflow_without_token(self, client, sample_workflow):
        """Test creating a workflow without authentication fails."""
        response = client.post(
            "/api/v1/workflows/protected/create",
            json=sample_workflow
        )
        assert response.status_code == 403
    
    def test_create_workflow_with_user_no_write_scope(self, client, user_token, sample_workflow):
        """Test creating a workflow with user token (no write scope) fails."""
        response = client.post(
            "/api/v1/workflows/protected/create",
            json=sample_workflow,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
        assert "workflow:write" in response.json()["detail"]
    
    def test_list_workflows_admin_sees_all(self, client, admin_token):
        """Test admin can see all workflows."""
        # Create workflows by different users
        workflow_storage["wf_1"] = {"name": "WF1", "owner": "admin"}
        workflow_storage["wf_2"] = {"name": "WF2", "owner": "user"}
        
        response = client.get(
            "/api/v1/workflows/protected/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_list_workflows_user_sees_own(self, client, user_token):
        """Test regular user only sees their own workflows."""
        # Create workflows by different users
        workflow_storage["wf_1"] = {"name": "WF1", "owner": "admin"}
        workflow_storage["wf_2"] = {"name": "WF2", "owner": "user"}
        workflow_storage["wf_3"] = {"name": "WF3", "owner": "user"}
        
        response = client.get(
            "/api/v1/workflows/protected/",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Only user's workflows
        assert all(wf["owner"] == "user" for wf in data)
    
    def test_get_workflow_owner_access(self, client, user_token):
        """Test user can access their own workflow."""
        workflow_storage["wf_test"] = {
            "name": "My Workflow",
            "owner": "user",
            "description": "Test"
        }
        
        response = client.get(
            "/api/v1/workflows/protected/wf_test",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wf_test"
        assert data["owner"] == "user"
    
    def test_get_workflow_denied_non_owner(self, client, user_token):
        """Test user cannot access another user's workflow."""
        workflow_storage["wf_test"] = {
            "name": "Admin Workflow",
            "owner": "admin",
            "description": "Test"
        }
        
        response = client.get(
            "/api/v1/workflows/protected/wf_test",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
    
    def test_get_workflow_admin_can_access_any(self, client, admin_token):
        """Test admin can access any workflow."""
        workflow_storage["wf_test"] = {
            "name": "User Workflow",
            "owner": "user",
            "description": "Test"
        }
        
        response = client.get(
            "/api/v1/workflows/protected/wf_test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["owner"] == "user"
    
    def test_update_workflow_owner(self, client, admin_token, sample_workflow):
        """Test owner can update their workflow."""
        workflow_storage["wf_test123"] = {
            "name": "Old Name",
            "owner": "admin",
            "nodes": [],
            "edges": []
        }
        
        sample_workflow["name"] = "Updated Name"
        response = client.put(
            "/api/v1/workflows/protected/wf_test123",
            json=sample_workflow,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
    
    def test_update_workflow_denied_non_owner(self, client, user_token, sample_workflow):
        """Test non-owner cannot update workflow."""
        workflow_storage["wf_test123"] = {
            "name": "Admin Workflow",
            "owner": "admin",
            "nodes": [],
            "edges": []
        }
        
        response = client.put(
            "/api/v1/workflows/protected/wf_test123",
            json=sample_workflow,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
        assert "workflow:write" in response.json()["detail"]
    
    def test_delete_workflow_admin_only(self, client, admin_token):
        """Test only admin can delete workflows."""
        workflow_storage["wf_test"] = {
            "name": "To Delete",
            "owner": "admin"
        }
        
        response = client.delete(
            "/api/v1/workflows/protected/wf_test",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 204
        assert "wf_test" not in workflow_storage
    
    def test_delete_workflow_user_denied(self, client, user_token):
        """Test regular user cannot delete workflows."""
        workflow_storage["wf_test"] = {
            "name": "User Workflow",
            "owner": "user"
        }
        
        response = client.delete(
            "/api/v1/workflows/protected/wf_test",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
        assert "workflow:delete" in response.json()["detail"]
    
    def test_execute_workflow_owner(self, client, user_token):
        """Test owner can execute their workflow."""
        workflow_storage["wf_test"] = {
            "name": "My Workflow",
            "owner": "user",
            "nodes": [],
            "edges": []
        }
        
        response = client.post(
            "/api/v1/workflows/protected/wf_test/execute",
            json={"parameters": {"key": "value"}},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 202
        data = response.json()
        assert data["workflow_id"] == "wf_test"
        assert data["status"] == "queued"
        assert "user" in data["message"]
    
    def test_execute_workflow_denied_non_owner(self, client, user_token):
        """Test non-owner cannot execute workflow."""
        workflow_storage["wf_test"] = {
            "name": "Admin Workflow",
            "owner": "admin",
            "nodes": [],
            "edges": []
        }
        
        response = client.post(
            "/api/v1/workflows/protected/wf_test/execute",
            json={"parameters": {}},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
        assert "Cannot execute workflow" in response.json()["detail"]
    
    def test_list_executions_owner(self, client, user_token):
        """Test owner can list executions for their workflow."""
        workflow_storage["wf_test"] = {
            "name": "My Workflow",
            "owner": "user"
        }
        execution_storage["exec_1"] = {
            "workflow_id": "wf_test",
            "status": "completed",
            "owner": "user"
        }
        execution_storage["exec_2"] = {
            "workflow_id": "wf_test",
            "status": "failed",
            "owner": "user"
        }
        
        response = client.get(
            "/api/v1/workflows/protected/wf_test/executions",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_list_executions_denied_non_owner(self, client, user_token):
        """Test non-owner cannot list executions."""
        workflow_storage["wf_test"] = {
            "name": "Admin Workflow",
            "owner": "admin"
        }
        
        response = client.get(
            "/api/v1/workflows/protected/wf_test/executions",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403
        assert "Cannot view executions" in response.json()["detail"]
