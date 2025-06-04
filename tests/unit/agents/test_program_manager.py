"""Tests for Program Manager Agent."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.program_manager import (
    ProgramManagerAgent,
    ProjectStatus,
    ResourceType,
    TaskPriority,
)
from agentic_workflow.core.exceptions import AgentError


class TestProgramManagerAgent:
    """Test cases for Program Manager Agent."""

    @pytest_asyncio.fixture
    async def agent(self):
        """Create Program Manager agent instance for testing."""
        config = {
            "max_concurrent_projects": 5,
            "default_risk_tolerance": "medium",
            "budget_alert_threshold": 0.8,
            "available_agents": [
                "code_generation",
                "testing",
                "review",
                "cicd",
                "planning",
            ],
            "max_agent_utilization": 0.8,
            "detailed_reporting": True,
        }
        agent = ProgramManagerAgent(config=config)
        await agent.initialize()
        return agent

    @pytest.fixture
    def project_config(self):
        """Sample project configuration."""
        return {
            "name": "Test Project Alpha",
            "description": "A comprehensive test project for validation",
            "objectives": [
                "Deliver high-quality solution",
                "Meet timeline requirements",
                "Stay within budget constraints",
            ],
            "timeline": {
                "duration_weeks": 6,
                "buffer_percentage": 0.2,
            },
            "budget": 15000.0,
            "stakeholders": ["Product Manager", "Development Team", "QA Team"],
            "risk_tolerance": "medium",
        }

    @pytest.mark.asyncio
    async def test_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "program_manager"
        assert agent.max_concurrent_projects == 5
        assert agent.default_risk_tolerance == "medium"
        assert agent.budget_alert_threshold == 0.8
        assert "code_generation" in agent.available_agents
        assert len(agent.resource_pool) > 0

    @pytest.mark.asyncio
    async def test_get_capabilities(self, agent):
        """Test agent capabilities."""
        capabilities = agent.get_capabilities()

        expected_capabilities = [
            "project_planning",
            "resource_allocation",
            "agent_coordination",
            "progress_tracking",
            "risk_management",
            "budget_management",
            "timeline_management",
            "stakeholder_communication",
            "milestone_tracking",
            "workflow_orchestration",
            "performance_optimization",
            "strategic_planning",
        ]

        for capability in expected_capabilities:
            assert capability in capabilities

    @pytest.mark.asyncio
    async def test_create_project_success(self, agent, project_config):
        """Test successful project creation."""
        task = AgentTask(
            type="create_project",
            prompt="Create comprehensive software development project",
            context={
                "project_config": project_config,
                "project_scope": "full",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "project_id" in result.data
        assert result.data["tasks_count"] > 0
        assert result.data["milestones_count"] > 0
        assert result.data["estimated_duration"] > 0
        assert result.data["estimated_cost"] > 0

        # Check project was stored
        project_id = result.data["project_id"]
        assert project_id in agent.active_projects

        project = agent.active_projects[project_id]
        assert project.config.name == project_config["name"]
        assert project.status == ProjectStatus.PLANNING
        assert len(project.tasks) > 0
        assert len(project.milestones) > 0
        assert len(project.risks) >= 0

    @pytest.mark.asyncio
    async def test_create_project_default_config(self, agent):
        """Test project creation with default configuration."""
        task = AgentTask(
            type="create_project",
            prompt="Create simple project with defaults",
            context={"project_scope": "standard"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "project_id" in result.data

        project_id = result.data["project_id"]
        project = agent.active_projects[project_id]
        assert "Project: Create simple project with defaults" in project.config.name
        assert project.config.budget == 10000.0  # Standard scope budget

    @pytest.mark.asyncio
    async def test_manage_project_status(self, agent, project_config):
        """Test project status management."""
        # First create a project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for status testing",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Test status check
        status_task = AgentTask(
            type="manage_project",
            prompt="Check project status",
            context={
                "project_id": project_id,
                "action": "status",
            },
        )

        result = await agent.execute(status_task)

        assert result.success is True
        assert result.data["project_id"] == project_id
        assert result.data["action"] == "status"
        assert "result" in result.data
        assert result.data["result"]["success"] is True

    @pytest.mark.asyncio
    async def test_manage_project_update(self, agent, project_config):
        """Test project updates."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for update testing",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Update project
        update_task = AgentTask(
            type="manage_project",
            prompt="Update project progress",
            context={
                "project_id": project_id,
                "action": "update",
                "updates": {
                    "progress_percentage": 25.0,
                    "budget_used": 2500.0,
                    "task_updates": [
                        {
                            "task_id": "task_planning",
                            "status": "completed",
                            "completion_percentage": 100.0,
                            "actual_hours": 10.0,
                        }
                    ],
                },
            },
        )

        result = await agent.execute(update_task)

        assert result.success is True
        assert result.data["result"]["success"] is True

        # Verify updates were applied
        project = agent.active_projects[project_id]
        assert project.progress_percentage == 25.0
        assert project.budget_used == 2500.0

    @pytest.mark.asyncio
    async def test_manage_project_complete(self, agent, project_config):
        """Test project completion."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for completion testing",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Complete project
        complete_task = AgentTask(
            type="manage_project",
            prompt="Complete project",
            context={
                "project_id": project_id,
                "action": "complete",
            },
        )

        result = await agent.execute(complete_task)

        assert result.success is True
        assert result.data["result"]["success"] is True

        # Verify project is completed
        project = agent.active_projects[project_id]
        assert project.status == ProjectStatus.COMPLETED
        assert project.progress_percentage == 100.0
        assert project.end_date is not None

    @pytest.mark.asyncio
    async def test_manage_project_invalid_id(self, agent):
        """Test project management with invalid project ID."""
        task = AgentTask(
            type="manage_project",
            prompt="Manage non-existent project",
            context={
                "project_id": "invalid_project_id",
                "action": "status",
            },
        )

        with pytest.raises(AgentError, match="Program management execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_allocate_resources_initial(self, agent, project_config):
        """Test initial resource allocation."""
        # Create project first
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for resource allocation",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Allocate resources
        allocation_task = AgentTask(
            type="allocate_resources",
            prompt="Allocate initial resources",
            context={
                "allocation_type": "initial",
                "project_id": project_id,
                "resource_requirements": {},
            },
        )

        result = await agent.execute(allocation_task)

        assert result.success is True
        assert result.data["allocation_type"] == "initial"
        assert result.data["project_id"] == project_id
        assert "allocation_result" in result.data
        assert "resource_utilization" in result.data

    @pytest.mark.asyncio
    async def test_allocate_resources_optimization(self, agent):
        """Test resource allocation optimization."""
        task = AgentTask(
            type="allocate_resources",
            prompt="Optimize resource allocation",
            context={
                "allocation_type": "optimization",
                "project_id": "test_project",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["allocation_type"] == "optimization"
        assert "allocation_result" in result.data
        optimization_results = result.data["allocation_result"]["optimization_results"]
        assert "efficiency_gain" in optimization_results
        assert "cost_reduction" in optimization_results

    @pytest.mark.asyncio
    async def test_track_progress_project(self, agent, project_config):
        """Test project progress tracking."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for progress tracking",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Track progress
        track_task = AgentTask(
            type="track_progress",
            prompt="Track project progress",
            context={
                "tracking_type": "project",
                "project_id": project_id,
            },
        )

        result = await agent.execute(track_task)

        assert result.success is True
        assert result.data["tracking_type"] == "project"
        assert result.data["project_id"] == project_id
        assert "progress_result" in result.data
        progress_result = result.data["progress_result"]
        assert "progress_percentage" in progress_result
        assert "completed_tasks" in progress_result
        assert "total_tasks" in progress_result

    @pytest.mark.asyncio
    async def test_track_progress_milestone(self, agent, project_config):
        """Test milestone progress tracking."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for milestone tracking",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Track milestones
        track_task = AgentTask(
            type="track_progress",
            prompt="Track milestone progress",
            context={
                "tracking_type": "milestone",
                "project_id": project_id,
            },
        )

        result = await agent.execute(track_task)

        assert result.success is True
        assert result.data["tracking_type"] == "milestone"
        assert "progress_result" in result.data
        progress_result = result.data["progress_result"]
        assert "milestone_status" in progress_result
        assert "milestones_completed" in progress_result

    @pytest.mark.asyncio
    async def test_track_progress_overall(self, agent):
        """Test overall progress tracking."""
        task = AgentTask(
            type="track_progress",
            prompt="Track overall progress",
            context={"tracking_type": "overall"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["tracking_type"] == "overall"
        assert "progress_result" in result.data
        progress_result = result.data["progress_result"]
        assert "overall_progress_percentage" in progress_result
        assert "statistics" in progress_result
        assert "resource_utilization" in progress_result

    @pytest.mark.asyncio
    async def test_manage_risks_assess(self, agent, project_config):
        """Test risk assessment."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for risk assessment",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Assess risks
        risk_task = AgentTask(
            type="manage_risks",
            prompt="Assess project risks",
            context={
                "project_id": project_id,
                "risk_action": "assess",
            },
        )

        result = await agent.execute(risk_task)

        assert result.success is True
        assert result.data["project_id"] == project_id
        assert result.data["risk_action"] == "assess"
        assert "risk_result" in result.data
        risk_result = result.data["risk_result"]
        assert "current_risks" in risk_result
        assert "risk_count" in risk_result

    @pytest.mark.asyncio
    async def test_manage_risks_mitigate(self, agent, project_config):
        """Test risk mitigation."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for risk mitigation",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Get a risk ID from the project
        project = agent.active_projects[project_id]
        if project.risks:
            risk_id = project.risks[0]["risk_id"]

            # Mitigate risk
            risk_task = AgentTask(
                type="manage_risks",
                prompt="Mitigate project risk",
                context={
                    "project_id": project_id,
                    "risk_action": "mitigate",
                    "risk_id": risk_id,
                },
            )

            result = await agent.execute(risk_task)

            assert result.success is True
            assert result.data["risk_action"] == "mitigate"
            assert "risk_result" in result.data

    @pytest.mark.asyncio
    async def test_coordinate_agents_setup(self, agent, project_config):
        """Test agent coordination setup."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for agent coordination",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Setup coordination
        coord_task = AgentTask(
            type="coordinate_agents",
            prompt="Setup agent coordination",
            context={
                "coordination_type": "setup",
                "project_id": project_id,
            },
        )

        result = await agent.execute(coord_task)

        assert result.success is True
        assert result.data["coordination_type"] == "setup"
        assert result.data["project_id"] == project_id
        assert "coordination_result" in result.data
        coord_result = result.data["coordination_result"]
        assert "coordination_plan" in coord_result

    @pytest.mark.asyncio
    async def test_coordinate_agents_execute(self, agent):
        """Test agent coordination execution."""
        task = AgentTask(
            type="coordinate_agents",
            prompt="Execute agent coordination",
            context={
                "coordination_type": "execute",
                "project_id": "test_project",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["coordination_type"] == "execute"
        assert "coordination_result" in result.data

    @pytest.mark.asyncio
    async def test_coordinate_agents_monitor(self, agent):
        """Test agent coordination monitoring."""
        task = AgentTask(
            type="coordinate_agents",
            prompt="Monitor agent coordination",
            context={
                "coordination_type": "monitor",
                "project_id": "test_project",
            },
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["coordination_type"] == "monitor"
        assert "coordination_result" in result.data
        coord_result = result.data["coordination_result"]
        assert "monitoring_data" in coord_result

    @pytest.mark.asyncio
    async def test_generate_report_status(self, agent, project_config):
        """Test status report generation."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for status reporting",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Generate status report
        report_task = AgentTask(
            type="generate_report",
            prompt="Generate project status report",
            context={
                "report_type": "status",
                "project_id": project_id,
            },
        )

        result = await agent.execute(report_task)

        assert result.success is True
        assert result.data["report_type"] == "status"
        assert result.data["project_id"] == project_id
        assert "report" in result.data
        report = result.data["report"]["report"]
        assert report["report_type"] == "status"
        assert "project_name" in report
        assert "progress_percentage" in report
        assert "budget_status" in report

    @pytest.mark.asyncio
    async def test_generate_report_progress(self, agent, project_config):
        """Test progress report generation."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for progress reporting",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Generate progress report
        report_task = AgentTask(
            type="generate_report",
            prompt="Generate project progress report",
            context={
                "report_type": "progress",
                "project_id": project_id,
            },
        )

        result = await agent.execute(report_task)

        assert result.success is True
        assert result.data["report_type"] == "progress"
        assert "report" in result.data
        report = result.data["report"]["report"]
        assert report["report_type"] == "progress"
        assert "task_details" in report
        assert "milestone_progress" in report
        assert "performance_metrics" in report

    @pytest.mark.asyncio
    async def test_generate_report_resource(self, agent):
        """Test resource report generation."""
        task = AgentTask(
            type="generate_report",
            prompt="Generate resource utilization report",
            context={"report_type": "resource"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["report_type"] == "resource"
        assert "report" in result.data
        report = result.data["report"]["report"]
        assert report["report_type"] == "resource"
        assert "resource_utilization" in report
        assert "utilization_summary" in report

    @pytest.mark.asyncio
    async def test_generate_report_executive(self, agent):
        """Test executive report generation."""
        task = AgentTask(
            type="generate_report",
            prompt="Generate executive summary report",
            context={"report_type": "executive"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["report_type"] == "executive"
        assert "report" in result.data
        report = result.data["report"]["report"]
        assert report["report_type"] == "executive"
        assert "executive_summary" in report
        assert "financial_summary" in report
        assert "strategic_recommendations" in report

    @pytest.mark.asyncio
    async def test_manage_timeline_optimize(self, agent, project_config):
        """Test timeline optimization."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for timeline optimization",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Optimize timeline
        timeline_task = AgentTask(
            type="manage_timeline",
            prompt="Optimize project timeline",
            context={
                "project_id": project_id,
                "timeline_action": "optimize",
            },
        )

        result = await agent.execute(timeline_task)

        assert result.success is True
        assert result.data["project_id"] == project_id
        assert result.data["timeline_action"] == "optimize"
        assert "timeline_result" in result.data
        timeline_result = result.data["timeline_result"]
        assert "optimization_results" in timeline_result

    @pytest.mark.asyncio
    async def test_manage_timeline_validate(self, agent, project_config):
        """Test timeline validation."""
        # Create project
        create_task = AgentTask(
            type="create_project",
            prompt="Create project for timeline validation",
            context={"project_config": project_config},
        )
        create_result = await agent.execute(create_task)
        project_id = create_result.data["project_id"]

        # Validate timeline
        timeline_task = AgentTask(
            type="manage_timeline",
            prompt="Validate project timeline",
            context={
                "project_id": project_id,
                "timeline_action": "validate",
            },
        )

        result = await agent.execute(timeline_task)

        assert result.success is True
        assert result.data["timeline_action"] == "validate"
        assert "timeline_result" in result.data
        timeline_result = result.data["timeline_result"]
        assert "validation_results" in timeline_result

    @pytest.mark.asyncio
    async def test_execute_unknown_task_type(self, agent):
        """Test executing unknown task type raises error."""
        task = AgentTask(type="unknown_mgmt", prompt="Unknown management type")

        with pytest.raises(AgentError, match="Program management execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_plan_new_project(self, agent):
        """Test planning for new project creation."""
        objective = (
            "Create comprehensive software development project with full lifecycle"
        )

        tasks = await agent.plan(objective)

        assert len(tasks) == 4
        task_types = [task.get("type") for task in tasks]
        assert "create_project" in task_types
        assert "allocate_resources" in task_types
        assert "coordinate_agents" in task_types
        assert "track_progress" in task_types

        # Check dependencies
        resource_task = next(
            (task for task in tasks if task.get("type") == "allocate_resources"), None
        )
        assert resource_task is not None
        assert "project_creation" in resource_task.get("dependencies", [])

    @pytest.mark.asyncio
    async def test_plan_project_monitoring(self, agent):
        """Test planning for project monitoring."""
        objective = "Monitor progress and track project status"

        tasks = await agent.plan(objective)

        assert len(tasks) == 3
        task_types = [task.get("type") for task in tasks]
        assert "track_progress" in task_types
        assert "manage_risks" in task_types
        assert "generate_report" in task_types

        # Check dependencies
        report_task = next(
            (task for task in tasks if task.get("type") == "generate_report"), None
        )
        assert report_task is not None
        assert "risk_assessment" in report_task.get("dependencies", [])

    @pytest.mark.asyncio
    async def test_plan_resource_optimization(self, agent):
        """Test planning for resource optimization."""
        objective = "Optimize resource allocation and improve efficiency"

        tasks = await agent.plan(objective)

        assert len(tasks) == 2
        task_types = [task.get("type") for task in tasks]
        assert "allocate_resources" in task_types
        assert "manage_timeline" in task_types

        # Check dependencies
        timeline_task = next(
            (task for task in tasks if task.get("type") == "manage_timeline"), None
        )
        assert timeline_task is not None
        assert "resource_analysis" in timeline_task.get("dependencies", [])

    @pytest.mark.asyncio
    async def test_determine_management_strategy(self, agent):
        """Test management strategy determination."""
        # Test new project strategy
        strategy = agent._determine_management_strategy(
            "create new software project", {}
        )
        assert strategy == "new_project"

        # Test monitoring strategy
        strategy = agent._determine_management_strategy("monitor project progress", {})
        assert strategy == "project_monitoring"

        # Test optimization strategy
        strategy = agent._determine_management_strategy(
            "optimize resource allocation", {}
        )
        assert strategy == "resource_optimization"

    @pytest.mark.asyncio
    async def test_resource_pool_initialization(self, agent):
        """Test resource pool initialization."""
        assert len(agent.resource_pool) > 0

        # Check agent resources
        for agent_name in agent.available_agents:
            resource_id = f"agent_{agent_name}"
            assert resource_id in agent.resource_pool
            resource = agent.resource_pool[resource_id]
            assert resource.resource_type == ResourceType.AGENT
            assert resource.availability == 1.0
            assert resource.cost_per_hour == 50.0

        # Check compute resources
        assert "compute_standard" in agent.resource_pool
        assert "compute_high_performance" in agent.resource_pool

    @pytest.mark.asyncio
    async def test_calculate_resource_utilization(self, agent):
        """Test resource utilization calculation."""
        utilization = agent._calculate_resource_utilization()

        assert isinstance(utilization, dict)
        assert len(utilization) > 0

        for resource_id, util_data in utilization.items():
            assert "type" in util_data
            assert "utilization_percentage" in util_data
            assert "allocated_to" in util_data
            assert "availability" in util_data

    @pytest.mark.asyncio
    async def test_project_task_generation(self, agent):
        """Test project task generation."""
        from agentic_workflow.agents.program_manager import ProjectConfig

        config = ProjectConfig(
            name="Test Project",
            description="Test project for task generation",
            objectives=["Test objective"],
            timeline={"duration_weeks": 4},
        )

        tasks = agent._generate_project_tasks(config, "full")

        assert len(tasks) > 0
        task_names = [task.name for task in tasks]
        assert "Project Planning" in task_names
        assert "Development" in task_names
        assert "Testing" in task_names
        assert "Code Review" in task_names
        assert "Deployment" in task_names

        # Check task priorities and assignments
        for task in tasks:
            assert task.priority in [
                TaskPriority.LOW,
                TaskPriority.MEDIUM,
                TaskPriority.HIGH,
                TaskPriority.CRITICAL,
            ]
            assert task.estimated_hours > 0

    @pytest.mark.asyncio
    async def test_project_milestone_generation(self, agent):
        """Test project milestone generation."""
        from agentic_workflow.agents.program_manager import (
            ProjectConfig,
            Task,
            TaskPriority,
        )

        config = ProjectConfig(
            name="Test Project",
            description="Test project for milestone generation",
            objectives=["Test objective"],
            timeline={"duration_weeks": 4},
        )

        tasks = [
            Task(
                task_id="task_development",
                name="Development",
                description="Development task",
                priority=TaskPriority.HIGH,
                estimated_hours=40.0,
            ),
            Task(
                task_id="task_testing",
                name="Testing",
                description="Testing task",
                priority=TaskPriority.HIGH,
                estimated_hours=16.0,
            ),
        ]

        milestones = agent._generate_project_milestones(config, tasks)

        assert len(milestones) > 0
        milestone_names = [m["name"] for m in milestones]
        assert "Planning Complete" in milestone_names

        # Check milestone structure
        for milestone in milestones:
            assert "milestone_id" in milestone
            assert "name" in milestone
            assert "description" in milestone
            assert "target_date" in milestone
            assert "criteria" in milestone
            assert "status" in milestone

    @pytest.mark.asyncio
    async def test_project_risk_assessment(self, agent):
        """Test project risk assessment."""
        from agentic_workflow.agents.program_manager import (
            ProjectConfig,
            Task,
            TaskPriority,
        )

        config = ProjectConfig(
            name="Large Test Project",
            description="Large project for risk assessment",
            objectives=["Test objective"],
            timeline={"duration_weeks": 8},
            budget=30000.0,  # Large budget to trigger budget risk
        )

        # Create tasks with high complexity to trigger timeline risk
        tasks = [
            Task(
                task_id=f"task_{i}",
                name=f"Task {i}",
                description=f"Complex task {i}",
                priority=TaskPriority.HIGH,
                estimated_hours=30.0,
                assigned_agent=f"agent_{i % 3}",
            )
            for i in range(5)  # Many tasks to trigger resource risk
        ]

        risks = agent._assess_project_risks(config, tasks)

        assert len(risks) > 0

        # Check risk structure
        for risk in risks:
            assert "risk_id" in risk
            assert "category" in risk
            assert "description" in risk
            assert "probability" in risk
            assert "impact" in risk
            assert "mitigation" in risk
            assert "status" in risk

    @pytest.mark.asyncio
    async def test_project_cost_calculation(self, agent):
        """Test project cost calculation."""
        from agentic_workflow.agents.program_manager import (
            Project,
            ProjectConfig,
            Task,
            TaskPriority,
        )

        config = ProjectConfig(
            name="Cost Test Project",
            description="Project for cost calculation testing",
            objectives=["Test objective"],
            timeline={"duration_weeks": 4},
        )

        project = Project(
            project_id="test_cost_project",
            config=config,
            tasks=[
                Task(
                    task_id="task_1",
                    name="Task 1",
                    description="First task",
                    priority=TaskPriority.HIGH,
                    estimated_hours=20.0,
                    assigned_agent="code_generation",
                ),
                Task(
                    task_id="task_2",
                    name="Task 2",
                    description="Second task",
                    priority=TaskPriority.MEDIUM,
                    estimated_hours=15.0,
                    assigned_agent="testing",
                ),
            ],
        )

        cost = agent._calculate_project_cost(project)

        # Expected cost: (20 + 15) * 50 = 1750
        assert cost == 1750.0

    @pytest.mark.asyncio
    async def test_memory_storage_integration(self, agent, project_config):
        """Test memory storage integration."""
        task = AgentTask(
            type="create_project",
            prompt="Create project with memory storage",
            context={"project_config": project_config},
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
    async def test_error_handling_in_project_operations(self, agent):
        """Test error handling during project operations."""
        # Test with invalid project configuration
        task = AgentTask(
            type="create_project",
            prompt="Create project with invalid config",
            context={
                "project_config": {
                    # Missing required fields
                    "invalid_field": "invalid_value"
                }
            },
        )

        with pytest.raises(AgentError, match="Program management execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """Test agent configuration validation."""
        # Test with minimal config
        minimal_agent = ProgramManagerAgent(config={})
        await minimal_agent.initialize()

        assert minimal_agent.max_concurrent_projects == 10
        assert minimal_agent.default_risk_tolerance == "medium"

        # Test with custom config
        custom_config = {
            "max_concurrent_projects": 15,
            "default_risk_tolerance": "high",
            "budget_alert_threshold": 0.9,
            "available_agents": ["custom_agent"],
        }

        custom_agent = ProgramManagerAgent(config=custom_config)
        await custom_agent.initialize()

        assert custom_agent.max_concurrent_projects == 15
        assert custom_agent.default_risk_tolerance == "high"
        assert custom_agent.budget_alert_threshold == 0.9
        assert custom_agent.available_agents == ["custom_agent"]
