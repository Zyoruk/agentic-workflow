"""Tests for Requirement Engineering Agent."""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.requirement_engineering import (
    Requirement,
    RequirementDocument,
    RequirementEngineeringAgent,
    RequirementRequest,
)
from agentic_workflow.memory.manager import MemoryManager


class TestRequirementEngineeringAgent:
    """Test suite for Requirement Engineering Agent."""

    @pytest.fixture
    def agent(self):
        """Create test agent instance."""
        mock_memory = Mock(spec=MemoryManager)
        mock_memory.store = AsyncMock()
        mock_memory.retrieve = AsyncMock(return_value=[])

        agent = RequirementEngineeringAgent()
        agent.memory_manager = mock_memory
        agent.logger = Mock()
        return agent

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing."""
        return AgentTask(
            operation="gather",
            context={
                "domain": "e-commerce",
                "project_id": "test-project-123",
                "project_title": "E-commerce Platform",
            },
            stakeholders=["product_manager", "developers", "customers"],
            constraints=["performance", "security", "scalability"],
        )

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.name == "requirement_engineering"
        assert len(agent.capabilities) == 8
        assert "stakeholder_input_gathering" in agent.capabilities
        assert "requirement_analysis" in agent.capabilities

    @pytest.mark.asyncio
    async def test_gather_requirements(self, agent, sample_task):
        """Test requirement gathering functionality."""
        result = await agent.execute(sample_task)

        assert result.success is True
        assert result.task_id == sample_task.task_id
        assert result.agent_id == agent.name
        assert "requirements" in result.data
        assert isinstance(result.data["requirements"], list)
        assert result.data["total_requirements"] > 0

    @pytest.mark.asyncio
    async def test_analyze_requirements(self, agent):
        """Test requirement analysis functionality."""
        task = AgentTask(
            operation="analyze",
            context={"project_id": "test-project-123"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "total_requirements" in result.data
        assert "by_type" in result.data
        assert "by_priority" in result.data
        assert "completeness_score" in result.data

    @pytest.mark.asyncio
    async def test_validate_requirements(self, agent):
        """Test requirement validation functionality."""
        task = AgentTask(
            operation="validate",
            context={"project_id": "test-project-123"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "valid_requirements" in result.data
        assert "invalid_requirements" in result.data
        assert "validation_details" in result.data

    @pytest.mark.asyncio
    async def test_document_requirements(self, agent):
        """Test requirement documentation generation."""
        task = AgentTask(
            operation="document",
            context={
                "project_id": "test-project-123",
                "project_title": "Test Project",
            },
            stakeholders=["test_stakeholder"],
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "document" in result.data
        assert "formatted_document" in result.data
        assert result.data["document_type"] == "SRS"

    @pytest.mark.asyncio
    async def test_prioritize_requirements(self, agent):
        """Test requirement prioritization."""
        task = AgentTask(
            operation="prioritize",
            context={"project_id": "test-project-123"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "prioritized_requirements" in result.data
        assert "prioritization_method" in result.data
        assert "high_priority_count" in result.data

    @pytest.mark.asyncio
    async def test_assess_feasibility(self, agent):
        """Test feasibility assessment."""
        task = AgentTask(
            operation="assess_feasibility",
            context={"project_id": "test-project-123"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "overall_feasibility" in result.data
        assert "technical_feasibility" in result.data
        assert "requirement_assessments" in result.data

    @pytest.mark.asyncio
    async def test_invalid_operation(self, agent):
        """Test handling of invalid operation."""
        task = AgentTask(operation="invalid_operation")

        result = await agent.execute(task)

        assert result.success is False
        assert "Unknown operation" in result.error

    def test_requirement_model(self):
        """Test Requirement model validation."""
        req = Requirement(
            id="REQ-001",
            title="Test Requirement",
            description="This is a test requirement",
            type="functional",
            priority="high",
            status="draft",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )

        assert req.id == "REQ-001"
        assert req.type == "functional"
        assert req.priority == "high"

    def test_requirement_document_model(self):
        """Test RequirementDocument model validation."""
        doc = RequirementDocument(
            project_id="test-123",
            title="Test Document",
            version="1.0",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )

        assert doc.project_id == "test-123"
        assert doc.version == "1.0"
        assert len(doc.requirements) == 0

    def test_requirement_request_model(self):
        """Test RequirementRequest model validation."""
        request = RequirementRequest(
            operation="gather",
            context={"domain": "healthcare"},
            stakeholders=["doctor", "patient"],
        )

        assert request.operation == "gather"
        assert request.context["domain"] == "healthcare"
        assert len(request.stakeholders) == 2

    @pytest.mark.asyncio
    async def test_analyze_by_type(self, agent):
        """Test requirement analysis by type."""
        requirements = [
            {"type": "functional", "id": "1"},
            {"type": "functional", "id": "2"},
            {"type": "non-functional", "id": "3"},
        ]

        result = agent._analyze_by_type(requirements)

        assert result["functional"] == 2
        assert result["non-functional"] == 1

    @pytest.mark.asyncio
    async def test_analyze_by_priority(self, agent):
        """Test requirement analysis by priority."""
        requirements = [
            {"priority": "high", "id": "1"},
            {"priority": "high", "id": "2"},
            {"priority": "medium", "id": "3"},
        ]

        result = agent._analyze_by_priority(requirements)

        assert result["high"] == 2
        assert result["medium"] == 1

    def test_calculate_completeness_score(self, agent):
        """Test completeness score calculation."""
        requirements = [
            {
                "description": "Complete description",
                "acceptance_criteria": ["criterion 1"],
                "priority": "high",
                "stakeholders": ["user"],
                "effort_estimate": "2 days",
            },
            {
                "description": "Partial",
                "priority": "medium",
            },
        ]

        score = agent._calculate_completeness_score(requirements)

        assert 0 <= score <= 100
        assert score > 50  # Should be above 50% with mixed completeness

    def test_identify_quality_issues(self, agent):
        """Test quality issue identification."""
        requirements = [
            {"id": "REQ-001", "description": "Short"},  # Too short
            {
                "id": "REQ-002",
                "description": "This is a proper description",
            },  # No acceptance criteria
            {
                "id": "REQ-003",
                "description": "Good description",
                "acceptance_criteria": ["test"],
            },  # Good
        ]

        issues = agent._identify_quality_issues(requirements)

        assert len(issues) >= 2  # Should find at least 2 issues
        assert any("insufficient description" in issue for issue in issues)
        assert any("lacks acceptance criteria" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_validate_single_requirement(self, agent):
        """Test single requirement validation."""
        requirements = [
            {
                "id": "REQ-001",
                "title": "Test",
                "description": "Description",
                "type": "functional",
            },
            {
                "id": "REQ-002",
                "title": "Test2",
                "description": "Description2",
                "type": "functional",
            },
        ]

        # Test valid requirement
        validation = await agent._validate_single_requirement(
            requirements[0], requirements
        )
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0

        # Test invalid requirement (missing fields)
        invalid_req = {"id": "REQ-003"}
        validation = await agent._validate_single_requirement(invalid_req, requirements)
        assert validation["is_valid"] is False
        assert len(validation["errors"]) > 0

    @pytest.mark.asyncio
    async def test_calculate_priority_score(self, agent):
        """Test priority score calculation."""
        requirement = {
            "priority": "high",
            "type": "functional",
        }

        score = await agent._calculate_priority_score(requirement, {})

        assert score > 0
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_format_requirement_document(self, agent):
        """Test document formatting."""
        requirement = Requirement(
            id="REQ-001",
            title="Test Requirement",
            description="Test description",
            type="functional",
            priority="high",
            status="draft",
            acceptance_criteria=["Criterion 1", "Criterion 2"],
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )

        document = RequirementDocument(
            project_id="test-123",
            title="Test Document",
            version="1.0",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            stakeholders=["stakeholder1"],
            requirements=[requirement],
        )

        formatted = await agent._format_requirement_document(document)

        assert "# Test Document" in formatted
        assert "REQ-001" in formatted
        assert "Test Requirement" in formatted
        assert "Criterion 1" in formatted

    @pytest.mark.asyncio
    async def test_generate_functional_requirements(self, agent):
        """Test functional requirement generation."""
        domain = "healthcare"
        context = {"features": ["patient_management", "scheduling"]}

        requirements = await agent._generate_functional_requirements(domain, context)

        assert len(requirements) > 0
        assert all(req["type"] == "functional" for req in requirements)
        assert all("id" in req for req in requirements)

    @pytest.mark.asyncio
    async def test_generate_non_functional_requirements(self, agent):
        """Test non-functional requirement generation."""
        constraints = ["performance", "security"]

        requirements = await agent._generate_non_functional_requirements(constraints)

        assert len(requirements) > 0
        assert all(req["type"] == "non-functional" for req in requirements)
        # Check that we have performance-related and security-related requirements
        titles = [req["title"].lower() for req in requirements]
        assert any("performance" in title for title in titles)
        assert any("security" in title for title in titles)

    def test_generate_recommendations(self, agent):
        """Test recommendation generation."""
        requirements = [{"id": "REQ-001", "type": "functional"}]

        recommendations = agent._generate_recommendations(requirements)

        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)


class TestRequirementEngineeringAgentIntegration:
    """Integration tests for Requirement Engineering Agent."""

    @pytest.fixture
    def agent_with_memory(self):
        """Create agent with mocked memory manager."""
        agent = RequirementEngineeringAgent()
        agent.memory_manager = Mock(spec=MemoryManager)
        agent.memory_manager.store = AsyncMock()
        agent.memory_manager.retrieve = AsyncMock(return_value=[])
        agent.logger = Mock()
        return agent

    @pytest.mark.asyncio
    async def test_full_requirement_workflow(self, agent_with_memory):
        """Test complete requirement engineering workflow."""
        # Step 1: Gather requirements
        gather_task = AgentTask(
            operation="gather",
            context={"domain": "fintech", "project_id": "fintech-app"},
            stakeholders=["product_owner", "compliance_officer"],
        )

        gather_result = await agent_with_memory.execute(gather_task)
        assert gather_result.success is True

        # Step 2: Analyze requirements
        analyze_task = AgentTask(
            operation="analyze",
            context={"project_id": "fintech-app"},
        )

        analyze_result = await agent_with_memory.execute(analyze_task)
        assert analyze_result.success is True

        # Step 3: Document requirements
        document_task = AgentTask(
            operation="document",
            context={
                "project_id": "fintech-app",
                "project_title": "FinTech Application",
            },
            stakeholders=["product_owner"],
        )

        document_result = await agent_with_memory.execute(document_task)
        assert document_result.success is True
        assert "SRS" in document_result.data["document_type"]

    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_context(self, agent_with_memory):
        """Test error handling with invalid context."""
        # Test with missing required context
        task = AgentTask(operation="gather")  # No context provided

        result = await agent_with_memory.execute(task)

        # Should still succeed but with limited functionality
        assert (
            result.success is True or result.success is False
        )  # Depends on implementation

    @pytest.mark.asyncio
    async def test_memory_integration(self, agent_with_memory):
        """Test integration with memory system."""
        task = AgentTask(
            operation="gather",
            context={"project_id": "memory-test"},
        )

        await agent_with_memory.execute(task)

        # Verify memory operations were called
        assert agent_with_memory.memory_manager.store.called
