"""
Tests for authentication API endpoints.

Sprint 1-2: Security Implementation
"""

import pytest
from fastapi.testclient import TestClient

from agentic_workflow.api.main import app


class TestAuthAPI:
    """Test authentication API endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_login_json_success(self):
        """Test successful login with JSON body."""
        response = self.client.post(
            "/api/v1/auth/login/json",
            json={"username": "admin", "password": "secret"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_json_invalid_password(self):
        """Test login with invalid password."""
        response = self.client.post(
            "/api/v1/auth/login/json",
            json={"username": "admin", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_json_invalid_username(self):
        """Test login with invalid username."""
        response = self.client.post(
            "/api/v1/auth/login/json",
            json={"username": "nonexistent", "password": "secret"}
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_oauth2_success(self):
        """Test successful login with OAuth2 form."""
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "secret"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_get_current_user(self):
        """Test getting current user information."""
        # First login to get token
        login_response = self.client.post(
            "/api/v1/auth/login/json",
            json={"username": "admin", "password": "secret"}
        )
        token = login_response.json()["access_token"]
        
        # Get current user
        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["email"] == "admin@agenticworkflow.com"
        assert "workflow:read" in data["scopes"]
        assert "workflow:write" in data["scopes"]

    def test_get_current_user_unauthorized(self):
        """Test getting current user without token."""
        response = self.client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # FastAPI returns 403 for missing credentials

    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401

    def test_regular_user_scopes(self):
        """Test that regular user has limited scopes."""
        # Login as regular user
        login_response = self.client.post(
            "/api/v1/auth/login/json",
            json={"username": "user", "password": "secret"}
        )
        token = login_response.json()["access_token"]
        
        # Get user info
        response = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "user"
        assert "workflow:read" in data["scopes"]
        assert "workflow:execute" in data["scopes"]
        assert "workflow:write" not in data["scopes"]  # Regular user can't write
        assert "workflow:delete" not in data["scopes"]  # Regular user can't delete
