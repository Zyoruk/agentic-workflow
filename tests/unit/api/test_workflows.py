"""
Unit tests for the visual workflow builder API.

Sprint 1-2: Testing workflow CRUD operations and execution.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from agentic_workflow.api.main import app
from agentic_workflow.api.workflows import (
    VisualNode,
    VisualEdge,
    NodePosition,
    NodeData,
    VisualWorkflowDefinition,
    WorkflowConverter,
    workflow_storage,
    execution_storage,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear workflow storage before each test."""
    workflow_storage.clear()
    execution_storage.clear()
    yield
    workflow_storage.clear()
    execution_storage.clear()


class TestWorkflowAPI:
    """Test suite for workflow API endpoints."""

    def test_create_visual_workflow(self):
        """Test creating a visual workflow."""
        workflow_data = {
            "id": "wf_test123",
            "name": "Test Workflow",
            "description": "A test workflow",
            "nodes": [
                {
                    "id": "node_0",
                    "type": "agent",
                    "position": {"x": 250, "y": 100},
                    "data": {
                        "agent_type": "planning",
                        "label": "Planning Agent",
                        "config": {"temperature": 0.7}
                    }
                }
            ],
            "edges": [],
            "metadata": {}
        }

        response = client.post("/api/v1/workflows/visual/create", json=workflow_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "workflow_id" in data
        assert data["name"] == "Test Workflow"

    def test_list_workflows(self):
        """Test listing all workflows."""
        response = client.get("/api/v1/workflows/")
        
        assert response.status_code == 200
        workflows = response.json()
        assert isinstance(workflows, list)
