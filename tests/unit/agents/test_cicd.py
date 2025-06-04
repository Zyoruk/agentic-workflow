"""Tests for CI/CD Agent."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.cicd import CICDAgent
from agentic_workflow.core.exceptions import AgentError


class TestCICDAgent:
    """Test cases for CI/CD Agent."""

    @pytest_asyncio.fixture
    async def agent(self):
        """Create CI/CD agent instance for testing."""
        config = {
            "gitlab_url": "https://gitlab.com",
            "gitlab_token": "test-token",
            "project_id": "123",
            "supported_environments": ["development", "staging", "production"],
            "deployment_timeout": 300,
            "auto_rollback_enabled": True,
        }
        agent = CICDAgent(config=config)
        await agent.initialize()
        return agent

    @pytest.fixture
    def deployment_config(self):
        """Sample deployment configuration."""
        return {
            "environment": "staging",
            "branch": "main",
            "dockerfile_path": "Dockerfile",
            "build_args": {"ENV": "staging"},
            "env_vars": {"DATABASE_URL": "postgres://test"},
            "replicas": 2,
        }

    @pytest.fixture
    def pipeline_config(self):
        """Sample pipeline configuration."""
        return {
            "stages": ["build", "test", "deploy"],
            "variables": {"CI": "true"},
            "build": {
                "stage": "build",
                "script": ["echo Building..."],
            },
        }

    @pytest.mark.asyncio
    async def test_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "cicd_agent"
        assert agent.gitlab_url == "https://gitlab.com"
        assert "staging" in agent.supported_environments
        assert agent.deployment_timeout == 300
        assert agent.auto_rollback_enabled is True

    @pytest.mark.asyncio
    async def test_get_capabilities(self, agent):
        """Test agent capabilities."""
        capabilities = agent.get_capabilities()

        expected_capabilities = [
            "deployment_automation",
            "pipeline_management",
            "environment_management",
            "rollback_recovery",
            "health_monitoring",
            "gitlab_integration",
            "kubernetes_deployment",
            "docker_management",
            "infrastructure_as_code",
            "deployment_validation",
            "continuous_integration",
            "continuous_deployment",
        ]

        for capability in expected_capabilities:
            assert capability in capabilities

    @pytest.mark.asyncio
    async def test_deploy_application_success(self, agent, deployment_config):
        """Test successful application deployment."""
        task = AgentTask(
            type="deploy",
            prompt="Deploy application to staging",
            context=deployment_config,
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "deployment_result" in result.data
        assert result.data["environment"] == "staging"
        assert result.data["deployment_result"]["status"] == "success"
        assert "deployment_id" in result.data
        assert "validation_result" in result.data

        # Check metadata
        assert result.metadata["environment"] == "staging"
        assert result.metadata["deployment_status"] == "success"

    @pytest.mark.asyncio
    async def test_deploy_application_invalid_environment(self, agent):
        """Test deployment with invalid environment."""
        task = AgentTask(
            type="deploy",
            prompt="Deploy to invalid environment",
            context={"environment": "invalid_env"},
        )

        with pytest.raises(AgentError, match="CI/CD execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_rollback_deployment(self, agent):
        """Test deployment rollback."""
        task = AgentTask(
            type="rollback",
            prompt="Rollback deployment",
            context={
                "environment": "staging",
                "target_version": "v1.0.20240603",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "rollback_result" in result.data
        assert result.data["environment"] == "staging"
        assert result.data["previous_version"] == "v1.0.20240603"
        assert "rollback_timestamp" in result.data

    @pytest.mark.asyncio
    async def test_create_pipeline(self, agent, pipeline_config):
        """Test pipeline creation."""
        task = AgentTask(
            type="create_pipeline",
            prompt="Create CI/CD pipeline",
            context={
                "pipeline_type": "basic_python",
                "pipeline_config": pipeline_config,
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "pipeline_config" in result.data
        assert "gitlab_ci_content" in result.data
        assert "pipeline_result" in result.data
        assert result.data["pipeline_type"] == "basic_python"

        # Check GitLab CI content was generated
        gitlab_ci = result.data["gitlab_ci_content"]
        assert "stages:" in gitlab_ci
        assert "build" in gitlab_ci

    @pytest.mark.asyncio
    async def test_manage_environment_create(self, agent):
        """Test environment creation."""
        task = AgentTask(
            type="manage_environment",
            prompt="Create new environment",
            context={
                "action": "create",
                "environment": "development",
                "config": {"replicas": 1},
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["environment_result"]["environment"] == "development"
        assert result.data["environment_result"]["status"] == "created"
        assert result.data["action"] == "create"

    @pytest.mark.asyncio
    async def test_manage_environment_delete_production_forbidden(self, agent):
        """Test that production environment cannot be deleted."""
        task = AgentTask(
            type="manage_environment",
            prompt="Delete production environment",
            context={
                "action": "delete",
                "environment": "production",
            },
        )

        result = await agent.execute(task)

        assert result.success is False
        assert (
            "Cannot delete production environment"
            in result.data["environment_result"]["error"]
        )

    @pytest.mark.asyncio
    async def test_manage_environment_status(self, agent):
        """Test environment status check."""
        task = AgentTask(
            type="manage_environment",
            prompt="Check environment status",
            context={
                "action": "status",
                "environment": "staging",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["environment_result"]["environment"] == "staging"
        assert result.data["environment_result"]["status"] == "active"
        assert "version" in result.data["environment_result"]
        assert "health" in result.data["environment_result"]

    @pytest.mark.asyncio
    async def test_perform_health_check(self, agent):
        """Test health check execution."""
        task = AgentTask(
            type="health_check",
            prompt="Perform health check",
            context={
                "environment": "staging",
                "check_type": "comprehensive",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "health_result" in result.data
        assert result.data["health_result"]["overall_health"] is True
        assert result.data["environment"] == "staging"
        assert result.data["check_type"] == "comprehensive"

        # Check health check details
        health_result = result.data["health_result"]
        assert "checks" in health_result
        assert "application_health" in health_result["checks"]
        assert "resource_utilization" in health_result["checks"]

    @pytest.mark.asyncio
    async def test_check_pipeline_status(self, agent):
        """Test pipeline status check."""
        task = AgentTask(
            type="pipeline_status",
            prompt="Check pipeline status",
            context={
                "pipeline_id": "12345",
                "branch": "main",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "pipeline_status" in result.data
        assert result.data["pipeline_id"] == "12345"
        assert result.data["branch"] == "main"

        # Check pipeline status details
        pipeline_status = result.data["pipeline_status"]
        assert "status" in pipeline_status
        assert "jobs" in pipeline_status

    @pytest.mark.asyncio
    async def test_check_pipeline_status_no_id(self, agent):
        """Test pipeline status check without pipeline ID."""
        task = AgentTask(
            type="pipeline_status",
            prompt="Check latest pipeline status",
            context={"branch": "develop"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "pipeline_status" in result.data
        assert result.data["branch"] == "develop"

    @pytest.mark.asyncio
    async def test_execute_unknown_task_type(self, agent):
        """Test executing unknown task type raises error."""
        task = AgentTask(type="unknown_cicd", prompt="Unknown CI/CD type")

        with pytest.raises(AgentError, match="CI/CD execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_plan_full_deployment(self, agent):
        """Test planning for full deployment."""
        objective = "Deploy application to staging with complete validation"

        tasks = await agent.plan(objective)

        assert len(tasks) == 4
        task_types = [task.get("type") for task in tasks]
        assert "create_pipeline" in task_types
        assert "manage_environment" in task_types
        assert "deploy" in task_types
        assert "health_check" in task_types

        # Check dependencies
        deploy_task = next(
            (task for task in tasks if task.get("type") == "deploy"), None
        )
        assert deploy_task is not None
        assert "environment_setup" in deploy_task.get("dependencies", [])

    @pytest.mark.asyncio
    async def test_plan_rollback(self, agent):
        """Test planning for rollback."""
        objective = "Rollback production deployment"

        tasks = await agent.plan(objective)

        assert len(tasks) == 1
        assert tasks[0].get("type") == "rollback"
        assert tasks[0].get("priority") == "critical"

    @pytest.mark.asyncio
    async def test_plan_pipeline_only(self, agent):
        """Test planning for pipeline creation only."""
        objective = "Create CI/CD pipeline for Python project"

        tasks = await agent.plan(objective)

        assert len(tasks) == 2
        task_types = [task.get("type") for task in tasks]
        assert "create_pipeline" in task_types
        assert "pipeline_status" in task_types

        # Check dependencies
        validation_task = next(
            (task for task in tasks if task.get("type") == "pipeline_status"), None
        )
        assert validation_task is not None
        assert "pipeline_creation" in validation_task.get("dependencies", [])

    @pytest.mark.asyncio
    async def test_determine_cicd_strategy(self, agent):
        """Test CI/CD strategy determination."""
        # Test rollback strategy
        strategy = agent._determine_cicd_strategy("rollback to previous version", {})
        assert strategy == "rollback"

        # Test pipeline only strategy
        strategy = agent._determine_cicd_strategy("create pipeline for project", {})
        assert strategy == "pipeline_only"

        # Test full deployment strategy
        strategy = agent._determine_cicd_strategy("deploy application", {})
        assert strategy == "full_deployment"

    @pytest.mark.asyncio
    async def test_execute_deployment_process(self, agent):
        """Test deployment execution process."""
        from agentic_workflow.agents.cicd import DeploymentConfig

        config = DeploymentConfig(
            environment="staging",
            branch="main",
            replicas=2,
        )

        result = await agent._execute_deployment(config)

        assert result.status == "success"
        assert result.environment == "staging"
        assert "deploy-staging-" in result.deployment_id
        assert len(result.logs) > 0
        assert "metrics" in result.model_dump()

    @pytest.mark.asyncio
    async def test_validate_deployment(self, agent):
        """Test deployment validation."""
        deployment_id = "test-deployment-123"
        environment = "staging"

        validation_result = await agent._validate_deployment(deployment_id, environment)

        assert validation_result["deployment_id"] == deployment_id
        assert validation_result["environment"] == environment
        assert validation_result["validation_success"] is True
        assert "health_checks" in validation_result
        assert "performance_metrics" in validation_result

    @pytest.mark.asyncio
    async def test_rollback_info_and_execution(self, agent):
        """Test rollback information retrieval and execution."""
        environment = "staging"
        target_version = "v1.0.20240603"

        # Test rollback info
        rollback_info = await agent._get_rollback_info(environment, target_version)
        assert rollback_info["environment"] == environment
        assert rollback_info["previous_version"] == target_version

        # Test rollback execution
        rollback_result = await agent._execute_rollback(environment, rollback_info)
        assert rollback_result["success"] is True
        assert rollback_result["environment"] == environment
        assert rollback_result["rolled_back_to"] == target_version

    @pytest.mark.asyncio
    async def test_generate_gitlab_ci(self, agent):
        """Test GitLab CI YAML generation."""
        pipeline_config = {
            "stages": ["build", "test"],
            "variables": {"CI": "true"},
            "build": {
                "stage": "build",
                "script": ["echo Building..."],
            },
        }

        gitlab_ci_content = await agent._generate_gitlab_ci(pipeline_config)

        assert "stages:" in gitlab_ci_content
        assert "build" in gitlab_ci_content
        assert "CI: 'true'" in gitlab_ci_content

    @pytest.mark.asyncio
    async def test_create_gitlab_pipeline(self, agent):
        """Test GitLab pipeline creation."""
        gitlab_ci_content = "stages:\n  - build\n  - test"

        result = await agent._create_gitlab_pipeline(gitlab_ci_content)

        assert result["success"] is True
        assert "pipeline_id" in result
        assert result["gitlab_ci_content"] == gitlab_ci_content

    @pytest.mark.asyncio
    async def test_environment_operations(self, agent):
        """Test environment management operations."""
        environment = "test-env"
        config = {"replicas": 1}

        # Test create
        create_result = await agent._create_environment(environment, config)
        assert create_result["success"] is True
        assert create_result["environment"] == environment

        # Test update
        update_result = await agent._update_environment(environment, config)
        assert update_result["success"] is True
        assert update_result["environment"] == environment

        # Test status
        status_result = await agent._get_environment_status(environment)
        assert status_result["success"] is True
        assert status_result["environment"] == environment

        # Test delete
        delete_result = await agent._delete_environment(environment)
        assert delete_result["success"] is True

    @pytest.mark.asyncio
    async def test_health_checks(self, agent):
        """Test health check execution."""
        environment = "staging"

        # Test basic health check
        basic_result = await agent._execute_health_checks(environment, "basic")
        assert basic_result["overall_health"] is True
        assert basic_result["environment"] == environment

        # Test comprehensive health check
        comprehensive_result = await agent._execute_health_checks(
            environment, "comprehensive"
        )
        assert comprehensive_result["overall_health"] is True
        assert "ssl_certificate" in comprehensive_result["checks"]
        assert "security_scan" in comprehensive_result["checks"]

    @pytest.mark.asyncio
    async def test_gitlab_pipeline_status(self, agent):
        """Test GitLab pipeline status retrieval."""
        # Test with pipeline ID
        pipeline_id = "12345"
        branch = "main"

        result_with_id = await agent._get_gitlab_pipeline_status(pipeline_id, branch)
        assert result_with_id["success"] is True
        assert result_with_id["pipeline_id"] == pipeline_id
        assert result_with_id["status"] == "success"

        # Test without pipeline ID
        result_without_id = await agent._get_gitlab_pipeline_status(None, branch)
        assert result_without_id["success"] is True
        assert result_without_id["status"] == "running"

    @pytest.mark.asyncio
    async def test_pipeline_templates(self, agent):
        """Test pipeline templates initialization."""
        templates = agent.pipeline_templates

        assert "basic_python" in templates
        assert "kubernetes_deployment" in templates

        # Test basic Python template
        python_template = templates["basic_python"]
        assert "stages" in python_template
        assert "build" in python_template
        assert "test" in python_template
        assert "deploy" in python_template

        # Test Kubernetes template
        k8s_template = templates["kubernetes_deployment"]
        assert "package" in k8s_template
        assert "deploy_staging" in k8s_template

    @pytest.mark.asyncio
    async def test_memory_storage_integration(self, agent, deployment_config):
        """Test memory storage integration."""
        task = AgentTask(
            type="deploy",
            prompt="Deploy with memory storage",
            context=deployment_config,
        )

        # Mock memory manager
        with patch.object(
            agent.memory_manager, "store", new_callable=AsyncMock
        ) as mock_store:
            result = await agent.execute(task)

            assert result.success is True
            mock_store.assert_called_once()

            # Verify stored data
            call_args = mock_store.call_args
            assert "content" in call_args.kwargs
            assert "metadata" in call_args.kwargs
            assert call_args.kwargs["metadata"]["agent_id"] == agent.agent_id

    @pytest.mark.asyncio
    async def test_error_handling_in_deployment(self, agent):
        """Test error handling during deployment."""
        with patch.object(agent, "_execute_deployment") as mock_deploy:
            mock_deploy.side_effect = Exception("Deployment failed")

            task = AgentTask(
                type="deploy",
                prompt="Deploy with error",
                context={"environment": "staging"},
            )

            with pytest.raises(AgentError, match="CI/CD execution failed"):
                await agent.execute(task)

    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """Test agent configuration validation."""
        # Test with minimal config
        minimal_agent = CICDAgent(config={})
        await minimal_agent.initialize()

        assert minimal_agent.default_environment == "staging"
        assert "development" in minimal_agent.supported_environments

        # Test with custom config
        custom_config = {
            "default_environment": "production",
            "supported_environments": ["prod", "stage"],
            "deployment_timeout": 900,
        }

        custom_agent = CICDAgent(config=custom_config)
        await custom_agent.initialize()

        assert custom_agent.default_environment == "production"
        assert custom_agent.supported_environments == ["prod", "stage"]
        assert custom_agent.deployment_timeout == 900
