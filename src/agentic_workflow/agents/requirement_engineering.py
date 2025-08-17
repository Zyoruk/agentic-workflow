"""Requirement Engineering Agent for gathering and analyzing project requirements."""

import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from agentic_workflow.agents.base import Agent, AgentResult, AgentTask
from agentic_workflow.core.exceptions import AgentError
from agentic_workflow.memory.interfaces import MemoryType


class RequirementRequest(BaseModel):
    """Request for requirement engineering operations."""

    operation: str  # gather, analyze, validate, document
    context: Dict[str, Any] = {}
    stakeholders: List[str] = []
    project_scope: Optional[str] = None
    constraints: List[str] = []
    priority: str = "medium"  # low, medium, high, critical


class Requirement(BaseModel):
    """Individual requirement model."""

    id: str
    title: str
    description: str
    type: str  # functional, non-functional, business, technical
    priority: str  # low, medium, high, critical
    status: str  # draft, review, approved, implemented
    stakeholders: List[str] = []
    acceptance_criteria: List[str] = []
    dependencies: List[str] = []
    effort_estimate: Optional[str] = None
    business_value: Optional[str] = None
    created_at: str
    updated_at: str


class RequirementDocument(BaseModel):
    """Complete requirement document model."""

    project_id: str
    title: str
    version: str
    created_at: str
    updated_at: str
    stakeholders: List[str] = []
    requirements: List[Requirement] = []
    assumptions: List[str] = []
    constraints: List[str] = []
    glossary: Dict[str, str] = {}
    approval_status: str = "draft"


class RequirementEngineeringAgent(Agent):
    """Agent for automated requirement engineering tasks."""

    def __init__(self, agent_id: str = "requirement_engineering", **kwargs: Any):
        """Initialize the Requirement Engineering Agent.

        Args:
            agent_id: Agent identifier
            **kwargs: Additional configuration
        """
        super().__init__(agent_id, **kwargs)
        self.capabilities = [
            "stakeholder_input_gathering",
            "requirement_analysis",
            "requirement_validation",
            "requirement_documentation",
            "change_management",
            "traceability_analysis",
            "feasibility_assessment",
            "requirement_prioritization",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute requirement engineering task.

        Args:
            task: Task to execute

        Returns:
            Agent execution result
        """
        try:
            request = RequirementRequest(**task)
            operation = request.operation.lower()

            if operation == "gather":
                result = await self._gather_requirements(request)
            elif operation == "analyze":
                result = await self._analyze_requirements(request)
            elif operation == "validate":
                result = await self._validate_requirements(request)
            elif operation == "document":
                result = await self._document_requirements(request)
            elif operation == "prioritize":
                result = await self._prioritize_requirements(request)
            elif operation == "assess_feasibility":
                result = await self._assess_feasibility(request)
            else:
                raise AgentError(f"Unknown operation: {operation}")

            return AgentResult(
                success=True,
                data=result,
                task_id=task.task_id,
                agent_id=self.name,
                execution_time=0.0,  # TODO: Add timing
                steps_taken=[{"operation": operation, "status": "completed"}],
            )

        except Exception as e:
            self.logger.error(f"Requirement engineering task failed: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                task_id=task.task_id,
                agent_id=self.name,
                execution_time=0.0,
                steps_taken=[
                    {"operation": task.get("operation", "unknown"), "status": "failed"}
                ],
            )

    async def plan(
        self, objective: str, context: Optional[Dict[str, Any]] = None
    ) -> List[AgentTask]:
        """Create execution plan for requirement engineering objective.

        Args:
            objective: High-level requirement engineering goal
            context: Additional context for planning

        Returns:
            List of AgentTask objects representing the execution plan
        """
        self.logger.info(f"Planning requirement engineering tasks for: {objective}")

        context = context or {}
        tasks = []

        # Standard requirement engineering workflow
        if "gather" in objective.lower() or "collect" in objective.lower():
            tasks.append(
                AgentTask(
                    operation="gather",
                    context=context,
                    stakeholders=context.get("stakeholders", []),
                    priority="high",
                )
            )

        if "analyze" in objective.lower() or "assessment" in objective.lower():
            tasks.append(
                AgentTask(operation="analyze", context=context, priority="medium")
            )

        if "validate" in objective.lower() or "check" in objective.lower():
            tasks.append(
                AgentTask(operation="validate", context=context, priority="medium")
            )

        if "document" in objective.lower() or "specification" in objective.lower():
            tasks.append(
                AgentTask(operation="document", context=context, priority="high")
            )

        if "prioritize" in objective.lower():
            tasks.append(
                AgentTask(operation="prioritize", context=context, priority="medium")
            )

        if "feasibility" in objective.lower():
            tasks.append(
                AgentTask(
                    operation="assess_feasibility", context=context, priority="medium"
                )
            )

        # If no specific operation mentioned, create comprehensive plan
        if not tasks:
            comprehensive_tasks = [
                AgentTask(operation="gather", context=context, priority="high"),
                AgentTask(operation="analyze", context=context, priority="medium"),
                AgentTask(operation="validate", context=context, priority="medium"),
                AgentTask(operation="document", context=context, priority="high"),
                AgentTask(operation="prioritize", context=context, priority="medium"),
                AgentTask(
                    operation="assess_feasibility", context=context, priority="low"
                ),
            ]
            tasks.extend(comprehensive_tasks)

        self.logger.info(f"Created plan with {len(tasks)} tasks")
        return tasks

    async def _gather_requirements(self, request: RequirementRequest) -> Dict[str, Any]:
        """Gather requirements from stakeholders and context.

        Args:
            request: Requirement request

        Returns:
            Gathered requirements data
        """
        self.logger.info("Gathering requirements from stakeholders")

        # Simulate stakeholder interviews and input gathering
        requirements = []

        # Generate functional requirements based on context
        if request.context.get("domain"):
            domain = request.context["domain"]
            functional_reqs = await self._generate_functional_requirements(
                domain, request.context
            )
            requirements.extend(functional_reqs)

        # Generate non-functional requirements
        non_functional_reqs = await self._generate_non_functional_requirements(
            request.constraints
        )
        requirements.extend(non_functional_reqs)

        # Store in memory for future reference
        await self._store_requirements(requirements, request.context.get("project_id"))

        return {
            "requirements": requirements,
            "stakeholders_consulted": request.stakeholders,
            "gathering_method": "automated_analysis",
            "total_requirements": len(requirements),
        }

    async def _analyze_requirements(
        self, request: RequirementRequest
    ) -> Dict[str, Any]:
        """Analyze existing requirements for completeness and quality.

        Args:
            request: Requirement request

        Returns:
            Analysis results
        """
        self.logger.info("Analyzing requirements quality and completeness")

        # Retrieve existing requirements
        requirements = await self._retrieve_requirements(
            request.context.get("project_id")
        )

        analysis = {
            "total_requirements": len(requirements),
            "by_type": self._analyze_by_type(requirements),
            "by_priority": self._analyze_by_priority(requirements),
            "completeness_score": self._calculate_completeness_score(requirements),
            "quality_issues": self._identify_quality_issues(requirements),
            "recommendations": self._generate_recommendations(requirements),
        }

        return analysis

    async def _validate_requirements(
        self, request: RequirementRequest
    ) -> Dict[str, Any]:
        """Validate requirements for consistency, feasibility, and clarity.

        Args:
            request: Requirement request

        Returns:
            Validation results
        """
        self.logger.info("Validating requirements")

        requirements = await self._retrieve_requirements(
            request.context.get("project_id")
        )

        validation_results = {
            "valid_requirements": 0,
            "invalid_requirements": 0,
            "warnings": [],
            "errors": [],
            "validation_details": [],
        }

        for req in requirements:
            validation = await self._validate_single_requirement(req, requirements)
            validation_results["validation_details"].append(validation)

            if validation["is_valid"]:
                validation_results["valid_requirements"] += 1
            else:
                validation_results["invalid_requirements"] += 1
                validation_results["errors"].extend(validation["errors"])

            validation_results["warnings"].extend(validation.get("warnings", []))

        return validation_results

    async def _document_requirements(
        self, request: RequirementRequest
    ) -> Dict[str, Any]:
        """Generate comprehensive requirement documentation.

        Args:
            request: Requirement request

        Returns:
            Generated documentation
        """
        self.logger.info("Generating requirement documentation")

        requirements = await self._retrieve_requirements(
            request.context.get("project_id")
        )

        document = RequirementDocument(
            project_id=request.context.get("project_id", str(uuid.uuid4())),
            title=request.context.get(
                "project_title", "Software Requirements Specification"
            ),
            version="1.0",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            stakeholders=request.stakeholders,
            requirements=requirements,
            assumptions=request.context.get("assumptions", []),
            constraints=request.constraints,
        )

        # Generate formatted documentation
        formatted_doc = await self._format_requirement_document(document)

        return {
            "document": document.model_dump(),
            "formatted_document": formatted_doc,
            "document_type": "SRS",
            "format": "markdown",
        }

    async def _prioritize_requirements(
        self, request: RequirementRequest
    ) -> Dict[str, Any]:
        """Prioritize requirements based on business value and effort.

        Args:
            request: Requirement request

        Returns:
            Prioritization results
        """
        self.logger.info("Prioritizing requirements")

        requirements = await self._retrieve_requirements(
            request.context.get("project_id")
        )

        # Calculate priority scores based on business value, effort, and risk
        prioritized_requirements = []
        for req in requirements:
            priority_score = await self._calculate_priority_score(req, request.context)
            req["priority_score"] = priority_score
            prioritized_requirements.append(req)

        # Sort by priority score
        prioritized_requirements.sort(key=lambda x: x["priority_score"], reverse=True)

        return {
            "prioritized_requirements": prioritized_requirements,
            "prioritization_method": "business_value_effort_matrix",
            "high_priority_count": len(
                [r for r in prioritized_requirements if r["priority"] == "high"]
            ),
            "medium_priority_count": len(
                [r for r in prioritized_requirements if r["priority"] == "medium"]
            ),
            "low_priority_count": len(
                [r for r in prioritized_requirements if r["priority"] == "low"]
            ),
        }

    async def _assess_feasibility(self, request: RequirementRequest) -> Dict[str, Any]:
        """Assess feasibility of requirements given constraints.

        Args:
            request: Requirement request

        Returns:
            Feasibility assessment
        """
        self.logger.info("Assessing requirement feasibility")

        requirements = await self._retrieve_requirements(
            request.context.get("project_id")
        )

        feasibility_assessment = {
            "overall_feasibility": "medium",
            "technical_feasibility": "high",
            "resource_feasibility": "medium",
            "timeline_feasibility": "medium",
            "risk_factors": [],
            "recommendations": [],
            "requirement_assessments": [],
        }

        for req in requirements:
            assessment = await self._assess_requirement_feasibility(
                req, request.context
            )
            feasibility_assessment["requirement_assessments"].append(assessment)

        return feasibility_assessment

    # Helper methods for requirement processing

    async def _generate_functional_requirements(
        self, domain: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate functional requirements based on domain and context."""
        # This would typically use LLM to generate domain-specific requirements
        base_requirements = [
            {
                "id": f"FR-{i:03d}",
                "title": f"Core {domain} functionality",
                "description": f"The system shall provide core {domain} capabilities",
                "type": "functional",
                "priority": "high",
                "status": "draft",
                "acceptance_criteria": [f"System supports {domain} operations"],
            }
            for i in range(1, 6)
        ]
        return base_requirements

    async def _generate_non_functional_requirements(
        self, constraints: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate non-functional requirements based on constraints."""
        nfr_requirements = [
            {
                "id": "NFR-001",
                "title": "Performance Requirements",
                "description": "The system shall respond to user requests within 2 seconds",
                "type": "non-functional",
                "priority": "high",
                "status": "draft",
                "acceptance_criteria": ["Response time < 2 seconds", "99% uptime"],
            },
            {
                "id": "NFR-002",
                "title": "Security Requirements",
                "description": "The system shall implement secure authentication and authorization",
                "type": "non-functional",
                "priority": "high",
                "status": "draft",
                "acceptance_criteria": [
                    "Multi-factor authentication",
                    "Role-based access control",
                ],
            },
        ]
        return nfr_requirements

    async def _store_requirements(
        self, requirements: List[Dict[str, Any]], project_id: Optional[str]
    ) -> None:
        """Store requirements in memory system."""
        if self.memory_manager:
            for req in requirements:
                await self.memory_manager.store(
                    memory_type=MemoryType.SHORT_TERM,
                    key=f"requirement_{req['id']}",
                    data=req,
                    metadata={"project_id": project_id, "type": "requirement"},
                )

    async def _retrieve_requirements(
        self, project_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Retrieve requirements from memory system."""
        requirements = []
        if self.memory_manager:
            # This would retrieve all requirements for the project
            # For now, return mock data
            requirements = [
                {
                    "id": "REQ-001",
                    "title": "User Authentication",
                    "description": "Users must be able to authenticate securely",
                    "type": "functional",
                    "priority": "high",
                    "status": "approved",
                    "acceptance_criteria": ["Support multi-factor authentication"],
                    "dependencies": [],
                    "stakeholders": [],
                    "effort_estimate": None,
                    "business_value": None,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            ]
        return requirements

    def _analyze_by_type(self, requirements: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze requirements by type."""
        type_counts = {}
        for req in requirements:
            req_type = req.get("type", "unknown")
            type_counts[req_type] = type_counts.get(req_type, 0) + 1
        return type_counts

    def _analyze_by_priority(
        self, requirements: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze requirements by priority."""
        priority_counts = {}
        for req in requirements:
            priority = req.get("priority", "unknown")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        return priority_counts

    def _calculate_completeness_score(
        self, requirements: List[Dict[str, Any]]
    ) -> float:
        """Calculate completeness score for requirements."""
        if not requirements:
            return 0.0

        total_score = 0
        for req in requirements:
            score = 0
            if req.get("description"):
                score += 20
            if req.get("acceptance_criteria"):
                score += 30
            if req.get("priority"):
                score += 20
            if req.get("stakeholders"):
                score += 15
            if req.get("effort_estimate"):
                score += 15

            total_score += score

        return total_score / (len(requirements) * 100) * 100

    def _identify_quality_issues(self, requirements: List[Dict[str, Any]]) -> List[str]:
        """Identify quality issues in requirements."""
        issues = []
        for req in requirements:
            if not req.get("description") or len(req["description"]) < 10:
                issues.append(
                    f"Requirement {req.get('id')} has insufficient description"
                )
            if not req.get("acceptance_criteria"):
                issues.append(f"Requirement {req.get('id')} lacks acceptance criteria")
        return issues

    def _generate_recommendations(
        self, requirements: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations for improving requirements."""
        recommendations = [
            "Add more detailed acceptance criteria for functional requirements",
            "Define measurable quality attributes for non-functional requirements",
            "Establish traceability links between requirements",
            "Conduct stakeholder reviews for requirement validation",
        ]
        return recommendations

    async def _validate_single_requirement(
        self, requirement: Dict[str, Any], all_requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate a single requirement."""
        validation = {
            "requirement_id": requirement.get("id"),
            "is_valid": True,
            "errors": [],
            "warnings": [],
        }

        # Check required fields
        required_fields = ["id", "title", "description", "type"]
        for field in required_fields:
            if not requirement.get(field):
                validation["errors"].append(f"Missing required field: {field}")
                validation["is_valid"] = False

        # Check for duplicate IDs
        req_id = requirement.get("id")
        if req_id:
            duplicates = [r for r in all_requirements if r.get("id") == req_id]
            if len(duplicates) > 1:
                validation["errors"].append(f"Duplicate requirement ID: {req_id}")
                validation["is_valid"] = False

        return validation

    async def _format_requirement_document(self, document: RequirementDocument) -> str:
        """Format requirement document as markdown."""
        formatted = f"""# {document.title}

**Version**: {document.version}
**Created**: {document.created_at}
**Updated**: {document.updated_at}

## Stakeholders
{', '.join(document.stakeholders)}

## Requirements

"""
        for req in document.requirements:
            formatted += f"""### {req.id}: {req.title}

**Type**: {req.type}
**Priority**: {req.priority}
**Status**: {req.status}

{req.description}

**Acceptance Criteria:**
"""
            for criteria in req.acceptance_criteria:
                formatted += f"- {criteria}\n"

            formatted += "\n"

        return formatted

    async def _calculate_priority_score(
        self, requirement: Dict[str, Any], context: Dict[str, Any]
    ) -> float:
        """Calculate priority score for requirement."""
        # Simple scoring algorithm - would be more sophisticated in practice
        priority_weights = {"critical": 100, "high": 75, "medium": 50, "low": 25}
        type_weights = {"functional": 1.2, "non-functional": 1.0, "business": 1.3}

        base_score = priority_weights.get(requirement.get("priority", "medium"), 50)
        type_multiplier = type_weights.get(requirement.get("type", "functional"), 1.0)

        return base_score * type_multiplier

    async def _assess_requirement_feasibility(
        self, requirement: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess feasibility of a single requirement."""
        return {
            "requirement_id": requirement.get("id"),
            "feasibility_score": 0.8,  # Mock score
            "technical_risk": "low",
            "resource_impact": "medium",
            "timeline_impact": "low",
            "recommendations": ["Consider phased implementation"],
        }
