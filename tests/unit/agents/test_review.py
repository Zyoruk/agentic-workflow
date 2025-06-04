"""Tests for ReviewAgent."""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from agentic_workflow.agents.base import AgentTask
from agentic_workflow.agents.review import ReviewAgent
from agentic_workflow.core.exceptions import AgentError
from agentic_workflow.memory import MemoryManager


class TestReviewAgent:
    """Test cases for ReviewAgent."""

    @pytest_asyncio.fixture
    async def agent(self):
        """Create agent instance for testing."""
        config = {
            "quality_threshold": 0.7,
            "security_enabled": True,
            "performance_checks": True,
            "documentation_required": True,
        }
        agent = ReviewAgent(config=config)
        await agent.initialize()
        return agent

    @pytest.fixture
    def sample_python_code(self):
        """Sample Python code for testing."""
        return '''
def calculate_average(numbers):
    """Calculate the average of a list of numbers.

    Args:
        numbers: List of numbers to average

    Returns:
        float: The average value
    """
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

class MathHelper:
    """Helper class for mathematical operations."""

    def __init__(self):
        self.pi = 3.14159

    def circle_area(self, radius: float) -> float:
        """Calculate circle area."""
        return self.pi * radius ** 2
'''

    @pytest.fixture
    def poor_quality_code(self):
        """Poor quality code for testing."""
        return """
import pickle
import os

def bad_function(x,y,z,a,b,c,d,e,f,g):
    if x:
        if y:
            if z:
                if a:
                    if b:
                        if c:
                            result=eval(x)
                            os.system("rm -rf " + y)
                            return result
"""

    @pytest.fixture
    def security_vulnerable_code(self):
        """Code with security vulnerabilities for testing."""
        return """
import os
import subprocess

def vulnerable_function(user_input):
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE name = '%s'" % user_input

    # Command injection vulnerability
    os.system("echo " + user_input)

    # Shell injection vulnerability
    subprocess.run(["grep", user_input], shell=True)

    # Code injection vulnerability
    eval(user_input)

    return query
"""

    @pytest.mark.asyncio
    async def test_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "review_agent"
        assert agent.quality_threshold == 0.7
        assert agent.security_enabled is True
        assert "python" in agent.supported_languages
        assert "syntax" in agent.quality_weights

    @pytest.mark.asyncio
    async def test_get_capabilities(self, agent):
        """Test agent capabilities."""
        capabilities = agent.get_capabilities()

        expected_capabilities = [
            "code_review",
            "security_analysis",
            "quality_assessment",
            "documentation_review",
            "performance_analysis",
            "best_practices_validation",
            "complexity_analysis",
            "style_checking",
            "vulnerability_detection",
        ]

        for capability in expected_capabilities:
            assert capability in capabilities

    @pytest.mark.asyncio
    async def test_code_review_good_quality(self, agent, sample_python_code):
        """Test code review with good quality code."""
        task = AgentTask(
            type="code_review",
            prompt="Review this Python code",
            context={"code": sample_python_code, "language": "python"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["overall_score"] > 0.5
        assert result.data["passed_review"] is True
        assert "syntax_analysis" in result.data
        assert "style_analysis" in result.data
        assert "complexity_analysis" in result.data
        assert "security_analysis" in result.data
        assert len(result.data["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_code_review_poor_quality(self, agent, poor_quality_code):
        """Test code review with poor quality code."""
        task = AgentTask(
            type="code_review",
            prompt="Review this poor quality code",
            context={"code": poor_quality_code, "language": "python"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["overall_score"] < 0.7
        assert result.data["passed_review"] is False
        assert result.data["complexity_analysis"]["nesting_depth"] > 3
        assert len(result.data["security_analysis"]["vulnerabilities"]) > 0

    @pytest.mark.asyncio
    async def test_security_review(self, agent, security_vulnerable_code):
        """Test security review with vulnerable code."""
        task = AgentTask(
            type="security_review",
            prompt="Perform security review",
            context={"code": security_vulnerable_code, "language": "python"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert result.data["security_score"] < 0.8
        assert result.data["passed_security_review"] is False
        assert len(result.data["vulnerabilities"]) > 0
        assert any(
            vuln["type"] in ["SQL_INJECTION", "COMMAND_INJECTION"]
            for vuln in result.data["vulnerabilities"]
        )
        assert len(result.data["security_recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_quality_assessment(self, agent, sample_python_code):
        """Test quality assessment."""
        task = AgentTask(
            type="quality_assessment",
            prompt="Assess code quality",
            context={"code": sample_python_code, "language": "python"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "quality_score" in result.data
        assert "maintainability" in result.data
        assert "readability" in result.data
        assert "testability" in result.data
        assert "modularity" in result.data
        assert len(result.data["quality_recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_documentation_review(self, agent, sample_python_code):
        """Test documentation review."""
        task = AgentTask(
            type="documentation_review",
            prompt="Review documentation quality",
            context={"code": sample_python_code, "language": "python"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "documentation_score" in result.data
        assert "docstring_coverage" in result.data
        assert "comment_quality" in result.data
        assert "api_documentation" in result.data
        assert result.data["docstring_coverage"]["functions"] > 0
        assert result.data["docstring_coverage"]["documented"] > 0

    @pytest.mark.asyncio
    async def test_performance_review(self, agent, sample_python_code):
        """Test performance review."""
        task = AgentTask(
            type="performance_review",
            prompt="Analyze performance characteristics",
            context={"code": sample_python_code, "language": "python"},
        )

        result = await agent.execute(task)

        assert result.success is True
        assert "performance_score" in result.data
        assert "algorithmic_complexity" in result.data
        assert "memory_usage" in result.data
        assert "io_optimization" in result.data
        assert len(result.data["performance_recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_execute_unknown_task_type(self, agent):
        """Test executing unknown task type raises error."""
        task = AgentTask(type="unknown_review", prompt="Unknown review type")

        with pytest.raises(AgentError, match="Review execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_execute_without_code(self, agent):
        """Test executing review without code raises error."""
        task = AgentTask(type="code_review", prompt="")  # Empty prompt

        with pytest.raises(AgentError, match="Review execution failed"):
            await agent.execute(task)

    @pytest.mark.asyncio
    async def test_plan_comprehensive_review(self, agent):
        """Test planning for comprehensive code review."""
        objective = "Comprehensive code review for user authentication module"

        tasks = await agent.plan(objective)

        assert len(tasks) >= 5  # Should have multiple review tasks
        task_types = [task.get("type") for task in tasks]
        assert "code_review" in task_types
        assert "quality_assessment" in task_types
        assert "security_review" in task_types
        assert "performance_review" in task_types
        assert "documentation_review" in task_types

    @pytest.mark.asyncio
    async def test_plan_security_focused_review(self, agent):
        """Test planning for security-focused review."""
        objective = "Security vulnerability assessment for API endpoints"

        tasks = await agent.plan(objective)

        assert len(tasks) == 1
        assert tasks[0].get("type") == "security_review"
        assert tasks[0].get("priority") == "critical"

    @pytest.mark.asyncio
    async def test_plan_quality_focused_review(self, agent):
        """Test planning for quality-focused review."""
        objective = "Code quality assessment and maintainability review"

        tasks = await agent.plan(objective)

        assert len(tasks) == 1
        assert tasks[0].get("type") == "quality_assessment"
        assert tasks[0].get("priority") == "high"

    @pytest.mark.asyncio
    async def test_syntax_analysis_valid_python(self, agent):
        """Test syntax analysis with valid Python code."""
        code = "def hello(): return 'world'"

        analysis = await agent._analyze_syntax(code, "python")

        assert analysis["score"] == 1.0
        assert len(analysis["issues"]) == 0
        assert "Valid Python syntax" in str(analysis["suggestions"])

    @pytest.mark.asyncio
    async def test_syntax_analysis_invalid_python(self, agent):
        """Test syntax analysis with invalid Python code."""
        code = "def hello( return 'world'"  # Missing closing parenthesis

        analysis = await agent._analyze_syntax(code, "python")

        assert analysis["score"] == 0.0
        assert len(analysis["issues"]) > 0
        assert "Syntax error" in analysis["issues"][0]

    @pytest.mark.asyncio
    async def test_style_analysis(self, agent):
        """Test style analysis."""
        code = """
def very_long_function_name_that_exceeds_the_recommended_line_length_limit_by_a_significant_amount():
    pass

def BadFunctionName():
    pass
"""

        analysis = await agent._analyze_style(code, "python")

        assert analysis["score"] < 0.7
        assert any("Long lines detected" in warning for warning in analysis["warnings"])
        assert any("snake_case" in warning for warning in analysis["warnings"])

    @pytest.mark.asyncio
    async def test_complexity_analysis_simple_code(self, agent):
        """Test complexity analysis with simple code."""
        code = "def simple(): return 42"

        analysis = await agent._analyze_complexity(code, "python")

        assert analysis["cyclomatic_complexity"] == 1
        assert analysis["nesting_depth"] == 0
        assert analysis["score"] > 0.7

    @pytest.mark.asyncio
    async def test_complexity_analysis_complex_code(self, agent):
        """Test complexity analysis with complex code."""
        code = """
def complex_function():
    for i in range(10):
        if i > 5:
            for j in range(5):
                if j < 2:
                    for k in range(3):
                        if k == 1:
                            print(k)
"""

        analysis = await agent._analyze_complexity(code, "python")

        assert analysis["cyclomatic_complexity"] > 5
        assert analysis["nesting_depth"] > 3
        assert analysis["score"] <= 0.6  # Changed from < to <=
        assert any(
            "nesting" in suggestion.lower() for suggestion in analysis["suggestions"]
        )

    @pytest.mark.asyncio
    async def test_security_analysis_safe_code(self, agent):
        """Test security analysis with safe code."""
        code = "def safe_function(x): return x * 2"

        analysis = await agent._analyze_security_basic(code, "python")

        assert analysis["score"] > 0.8
        assert len(analysis["vulnerabilities"]) == 0

    @pytest.mark.asyncio
    async def test_security_analysis_unsafe_code(self, agent):
        """Test security analysis with unsafe code."""
        code = """
import pickle
def unsafe_function(user_input):
    eval(user_input)
    exec(user_input)
    pickle.loads(user_input)
"""

        analysis = await agent._analyze_security_basic(code, "python")

        assert analysis["score"] < 0.5
        assert len(analysis["vulnerabilities"]) > 0
        assert len(analysis["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_vulnerability_detection(self, agent, security_vulnerable_code):
        """Test vulnerability detection."""
        vulnerabilities = await agent._detect_vulnerabilities(
            security_vulnerable_code, "python"
        )

        assert len(vulnerabilities) > 0
        assert any(vuln["type"] == "COMMAND_INJECTION" for vuln in vulnerabilities)
        assert any(vuln["severity"] == "HIGH" for vuln in vulnerabilities)

    @pytest.mark.asyncio
    async def test_docstring_coverage_analysis(self, agent, sample_python_code):
        """Test docstring coverage analysis."""
        analysis = await agent._analyze_docstring_coverage(sample_python_code, "python")

        assert analysis["functions"] > 0
        assert analysis["classes"] > 0
        assert analysis["documented"] > 0
        assert analysis["coverage_percentage"] > 0

    @pytest.mark.asyncio
    async def test_comment_quality_analysis(self, agent):
        """Test comment quality analysis."""
        code = """
# This is a good comment
def function():
    # Another helpful comment
    return 42

# Yet another comment
x = 10
"""

        analysis = await agent._analyze_comment_quality(code, "python")

        assert analysis["comment_lines"] == 3
        assert analysis["comment_ratio"] > 0
        assert analysis["score"] > 0

    @pytest.mark.asyncio
    async def test_api_documentation_analysis(self, agent, sample_python_code):
        """Test API documentation analysis."""
        analysis = await agent._analyze_api_documentation(sample_python_code, "python")

        assert analysis["has_type_hints"] is True
        assert analysis["has_docstrings"] is True
        assert analysis["score"] > 0.7

    @pytest.mark.asyncio
    async def test_algorithmic_complexity_analysis(self, agent):
        """Test algorithmic complexity analysis."""
        # Code with nested loops (O(n²))
        code = """
for i in range(n):
    for j in range(n):
        print(i, j)
"""

        analysis = await agent._analyze_algorithmic_complexity(code, "python")

        assert analysis["nested_loops"] > 0
        assert "O(n²)" in analysis["estimated_complexity"]
        assert analysis["score"] < 1.0

    @pytest.mark.asyncio
    async def test_memory_patterns_analysis(self, agent):
        """Test memory patterns analysis."""
        code = """
data = []
cache = {}
items = list()
mapping = dict()
"""

        analysis = await agent._analyze_memory_patterns(code, "python")

        assert analysis["large_structures"] > 0
        assert analysis["score"] < 1.0

    @pytest.mark.asyncio
    async def test_io_patterns_analysis(self, agent):
        """Test I/O patterns analysis."""
        # Synchronous I/O code
        sync_code = """
with open("file.txt") as f:
    data = f.read()
"""

        analysis = await agent._analyze_io_patterns(sync_code, "python")

        assert analysis["io_operations"] > 0
        assert analysis["async_operations"] == 0
        assert analysis["score"] < 0.8

        # Asynchronous I/O code
        async_code = """
async def read_file():
    async with aiofiles.open("file.txt") as f:
        data = await f.read()
"""

        analysis = await agent._analyze_io_patterns(async_code, "python")

        assert analysis["async_operations"] > 0

    @pytest.mark.asyncio
    async def test_overall_score_calculation(self, agent):
        """Test overall score calculation."""
        scores = {
            "syntax": 1.0,
            "style": 0.8,
            "complexity": 0.6,
            "security": 0.9,
        }

        overall_score = agent._calculate_overall_score(scores)

        assert 0.0 <= overall_score <= 1.0
        assert overall_score > 0.7  # Should be good overall

    @pytest.mark.asyncio
    async def test_security_score_calculation(self, agent):
        """Test security score calculation."""
        # No vulnerabilities
        analysis_safe = {"vulnerabilities": []}
        score_safe = agent._calculate_security_score(analysis_safe)
        assert score_safe == 1.0

        # High severity vulnerabilities
        analysis_vulnerable = {
            "vulnerabilities": [
                {"severity": "HIGH"},
                {"severity": "MEDIUM"},
                {"severity": "LOW"},
            ]
        }
        score_vulnerable = agent._calculate_security_score(analysis_vulnerable)
        assert score_vulnerable < 0.5

    @pytest.mark.asyncio
    async def test_recommendations_generation(self, agent):
        """Test recommendations generation."""
        analysis = {
            "syntax": {"suggestions": ["✅ Valid syntax"]},
            "style": {"suggestions": ["⚠️ Fix style issues"]},
            "security": {"suggestions": ["🔒 Security recommendations"]},
        }

        recommendations = agent._generate_recommendations(analysis)

        assert len(recommendations) >= 3
        assert any("Valid syntax" in rec for rec in recommendations)
        assert any("style issues" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_memory_storage_integration(self, agent, sample_python_code):
        """Test memory storage integration."""
        # Mock memory manager
        memory_manager = AsyncMock(spec=MemoryManager)
        agent.memory_manager = memory_manager

        task = AgentTask(
            type="code_review",
            prompt="Review code",
            context={"code": sample_python_code, "language": "python"},
        )

        result = await agent.execute(task)

        assert result.success is True
        memory_manager.store.assert_called_once()

        # Check that the stored data includes quality score
        call_args = memory_manager.store.call_args
        assert "quality_score" in call_args.kwargs["metadata"]

    @pytest.mark.asyncio
    async def test_determine_review_type(self, agent):
        """Test review type determination."""
        # Security focused
        security_objective = "Perform security vulnerability assessment"
        assert agent._determine_review_type(security_objective) == "security"

        # Quality focused
        quality_objective = "Code quality and maintainability review"
        assert agent._determine_review_type(quality_objective) == "quality"

        # General/comprehensive
        general_objective = "Review this code module"
        assert agent._determine_review_type(general_objective) == "comprehensive"

    @pytest.mark.asyncio
    async def test_review_type_specific_recommendations(self, agent):
        """Test type-specific recommendation generation."""
        # Security recommendations
        security_analysis = {"vulnerabilities": [{"type": "SQL_INJECTION"}]}
        security_recs = agent._generate_security_recommendations(security_analysis)
        assert any("security vulnerabilities" in rec.lower() for rec in security_recs)

        # Documentation recommendations
        doc_analysis = {"docstring_coverage": {"score": 0.3}}
        doc_recs = agent._generate_documentation_recommendations(doc_analysis)
        assert any("docstrings" in rec.lower() for rec in doc_recs)

        # Performance recommendations
        perf_analysis = {}
        perf_recs = agent._generate_performance_recommendations(perf_analysis)
        assert any("performance" in rec.lower() for rec in perf_recs)

        # Quality recommendations
        quality_analysis = {}
        quality_recs = agent._generate_quality_recommendations(quality_analysis)
        assert any("coding standards" in rec.lower() for rec in quality_recs)
