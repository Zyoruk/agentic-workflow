"""Planning Agent for breaking down objectives into actionable workflows.

This module implements the PlanningAgent, which serves as the primary orchestrator
for complex task decomposition and workflow planning in the agentic system.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from agentic_workflow.agents.base import Agent, AgentResult, AgentTask
from agentic_workflow.core.exceptions import AgentError, ValidationError
from agentic_workflow.memory import MemoryType


class PlanningAgent(Agent):
    """Agent for decomposing objectives into actionable workflows.

    The PlanningAgent serves as the primary orchestrator for complex task
    breakdown, workflow planning, and execution coordination. It analyzes
    high-level objectives and creates detailed execution plans that can be
    executed by specialized agents in the system.

    Key capabilities:
    - Objective analysis and decomposition
    - Task dependency management
    - Resource requirement estimation
    - Risk assessment and mitigation planning
    - Multi-agent coordination
    - Execution monitoring and adaptation
    """

    def __init__(
        self,
        agent_id: str = "planning_agent",
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize PlanningAgent.

        Args:
            agent_id: Unique identifier for this agent
            config: Agent configuration dictionary
            **kwargs: Additional arguments passed to base Agent
        """
        config = config or {}
        super().__init__(agent_id=agent_id, config=config, **kwargs)

        # Planning configuration
        self.max_depth = config.get("max_planning_depth", 5)
        self.min_task_size = config.get("min_task_size_hours", 0.5)
        self.max_task_size = config.get("max_task_size_hours", 8.0)
        self.default_complexity = config.get("default_complexity", "medium")

        # Available agent types for delegation
        self.available_agents = config.get(
            "available_agents", ["code_generation", "testing", "review", "deployment"]
        )

        # Task templates for different domains
        self.task_templates = self._initialize_task_templates()

        self.logger.info(
            f"PlanningAgent initialized with {len(self.available_agents)} available agents"
        )

    def _initialize_task_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize task templates for different project types."""
        return {
            "software_development": [
                {
                    "type": "requirements_analysis",
                    "description": "Analyze and document requirements",
                    "estimated_hours": 2.0,
                    "dependencies": [],
                    "agent_type": "planning",
                },
                {
                    "type": "architecture_design",
                    "description": "Design system architecture",
                    "estimated_hours": 4.0,
                    "dependencies": ["requirements_analysis"],
                    "agent_type": "planning",
                },
                {
                    "type": "code_generation",
                    "description": "Generate code implementation",
                    "estimated_hours": 6.0,
                    "dependencies": ["architecture_design"],
                    "agent_type": "code_generation",
                },
                {
                    "type": "testing",
                    "description": "Create and execute tests",
                    "estimated_hours": 3.0,
                    "dependencies": ["code_generation"],
                    "agent_type": "testing",
                },
                {
                    "type": "review",
                    "description": "Code review and quality assurance",
                    "estimated_hours": 2.0,
                    "dependencies": ["testing"],
                    "agent_type": "review",
                },
            ],
            "api_development": [
                {
                    "type": "api_specification",
                    "description": "Define API specification and contracts",
                    "estimated_hours": 3.0,
                    "dependencies": [],
                    "agent_type": "planning",
                },
                {
                    "type": "endpoint_implementation",
                    "description": "Implement API endpoints",
                    "estimated_hours": 5.0,
                    "dependencies": ["api_specification"],
                    "agent_type": "code_generation",
                },
                {
                    "type": "api_testing",
                    "description": "Create API tests and validation",
                    "estimated_hours": 3.0,
                    "dependencies": ["endpoint_implementation"],
                    "agent_type": "testing",
                },
                {
                    "type": "documentation",
                    "description": "Generate API documentation",
                    "estimated_hours": 2.0,
                    "dependencies": ["api_testing"],
                    "agent_type": "code_generation",
                },
            ],
            "data_processing": [
                {
                    "type": "data_analysis",
                    "description": "Analyze data requirements and structure",
                    "estimated_hours": 2.0,
                    "dependencies": [],
                    "agent_type": "planning",
                },
                {
                    "type": "pipeline_design",
                    "description": "Design data processing pipeline",
                    "estimated_hours": 3.0,
                    "dependencies": ["data_analysis"],
                    "agent_type": "planning",
                },
                {
                    "type": "pipeline_implementation",
                    "description": "Implement data processing pipeline",
                    "estimated_hours": 6.0,
                    "dependencies": ["pipeline_design"],
                    "agent_type": "code_generation",
                },
                {
                    "type": "validation_testing",
                    "description": "Create data validation and testing",
                    "estimated_hours": 2.0,
                    "dependencies": ["pipeline_implementation"],
                    "agent_type": "testing",
                },
            ],
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute a planning task.

        Args:
            task: Planning task to execute

        Returns:
            AgentResult with execution plan and metadata

        Raises:
            AgentError: If planning execution fails
        """
        self.logger.info(f"Executing planning task: {task.task_type}")

        try:
            # Execute planning task based on type
            if task.task_type == "create_plan":
                result = await self._create_execution_plan(task)
            elif task.task_type == "analyze_objective":
                result = await self._analyze_objective(task)
            elif task.task_type == "estimate_resources":
                result = await self._estimate_resources(task)
            elif task.task_type == "validate_plan":
                result = await self._validate_plan(task)
            elif task.task_type == "optimize_plan":
                result = await self._optimize_plan(task)
            else:
                raise ValidationError(f"Unknown planning task type: {task.task_type}")

            # Store execution in memory
            if self.memory_manager:
                content = json.dumps(
                    {
                        "task": dict(task),
                        "result": result.model_dump(),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )
                await self.memory_manager.store(
                    content=content,
                    memory_type=MemoryType.SHORT_TERM,
                    metadata={
                        "agent_id": self.agent_id,
                        "task_type": task.task_type,
                        "success": result.success,
                    },
                    entry_id=f"planning_execution_{task.task_id}",
                )

            self.logger.info(f"Planning task completed successfully: {task.task_type}")
            return result

        except Exception as e:
            self.logger.error(f"Planning task execution failed: {e}")
            raise AgentError(f"Planning execution failed for task {task.task_id}: {e}")

    async def plan(
        self, objective: str, context: Optional[Dict[str, Any]] = None
    ) -> List[AgentTask]:
        """Create execution plan for a high-level objective.

        Args:
            objective: High-level objective to achieve
            context: Additional context for planning

        Returns:
            List of AgentTask objects representing the execution plan
        """
        self.logger.info(f"Creating execution plan for objective: {objective}")

        context = context or {}

        # Analyze objective to determine project type and complexity
        project_analysis = await self._analyze_project_objective(objective, context)

        # Select appropriate task template
        project_type = project_analysis.get("project_type", "software_development")
        template_tasks = self.task_templates.get(
            project_type, self.task_templates["software_development"]
        )

        # Generate customized tasks based on objective
        tasks = []
        type_to_task_id = {}  # Map template types to actual task IDs

        for i, template in enumerate(template_tasks):
            task_id = f"task_{i+1}_{template['type']}"
            type_to_task_id[template["type"]] = task_id

            task = AgentTask(
                task_id=task_id,
                type=template["type"],
                prompt=self._customize_task_prompt(template, objective, context),
                context={
                    **context,
                    "objective": objective,
                    "template": template,
                    "project_analysis": project_analysis,
                },
                agent_type=template.get("agent_type", "planning"),
                priority=context.get("priority", "medium"),
                estimated_duration=template.get("estimated_hours", 2.0),
                dependencies=template.get("dependencies", []),
            )
            tasks.append(task)

        # Update dependencies to use actual task IDs
        for task in tasks:
            if task.get("dependencies"):
                updated_deps = []
                for dep in task.get("dependencies", []):
                    if dep in type_to_task_id:
                        updated_deps.append(type_to_task_id[dep])
                    else:
                        updated_deps.append(dep)  # Keep original if not found
                task["dependencies"] = updated_deps

        # Add custom tasks based on specific requirements
        additional_tasks = await self._generate_additional_tasks(
            objective, context, project_analysis
        )
        tasks.extend(additional_tasks)

        # Optimize task order and dependencies
        optimized_tasks = await self._optimize_task_sequence(tasks)

        self.logger.info(f"Created execution plan with {len(optimized_tasks)} tasks")
        return optimized_tasks

    async def _create_execution_plan(self, task: AgentTask) -> AgentResult:
        """Create a detailed execution plan."""
        objective = task.get("context", {}).get("objective", task.get("prompt", ""))
        context = task.get("context", {}).copy()

        # Generate execution plan
        execution_tasks = await self.plan(objective, context)

        # Calculate timeline and resource requirements
        timeline = await self._calculate_timeline(execution_tasks)
        resources = await self._estimate_execution_resources(execution_tasks)
        risks = await self._assess_risks(execution_tasks, context)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            execution_time=0.0,
            success=True,
            data={
                "execution_plan": [dict(t) for t in execution_tasks],
                "timeline": timeline,
                "resources": resources,
                "risks": risks,
                "total_tasks": len(execution_tasks),
                "estimated_duration_hours": sum(
                    t.get("estimated_duration", 0) for t in execution_tasks
                ),
            },
            metadata={
                "objective": objective,
                "planning_depth": len(execution_tasks),
                "project_type": context.get("project_type", "unknown"),
            },
        )

    async def _analyze_objective(self, task: AgentTask) -> AgentResult:
        """Analyze an objective to understand requirements and scope."""
        objective = task.get("context", {}).get("objective", task.get("prompt", ""))

        analysis = await self._analyze_project_objective(
            objective, task.get("context", {})
        )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            execution_time=0.0,
            success=True,
            data=analysis,
            metadata={"analysis_type": "objective_analysis"},
        )

    async def _estimate_resources(self, task: AgentTask) -> AgentResult:
        """Estimate resource requirements for a plan or objective."""
        context = task.get("context", {})
        if "execution_plan" in context:
            tasks = [AgentTask(**t) for t in context["execution_plan"]]
        else:
            objective = context.get("objective", task.get("prompt", ""))
            tasks = await self.plan(objective, context)

        resources = await self._estimate_execution_resources(tasks)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            execution_time=0.0,
            success=True,
            data=resources,
            metadata={"estimation_type": "resource_estimation"},
        )

    async def _validate_plan(self, task: AgentTask) -> AgentResult:
        """Validate an execution plan for feasibility and completeness."""
        execution_plan = task.get("context", {}).get("execution_plan", [])

        if not execution_plan:
            raise ValidationError("No execution plan provided for validation")

        validation_results: Dict[str, Any] = {
            "is_valid": True,
            "issues": [],
            "suggestions": [],
            "completeness_score": 0.0,
        }

        # Check task dependencies
        task_ids = {t.get("task_id") for t in execution_plan}
        for task_data in execution_plan:
            dependencies = task_data.get("dependencies", [])
            for dep in dependencies:
                if dep not in task_ids:
                    validation_results["issues"].append(
                        f"Task {task_data.get('task_id')} depends on missing task: {dep}"
                    )
                    validation_results["is_valid"] = False

        # Check resource constraints
        total_duration = sum(t.get("estimated_duration", 0) for t in execution_plan)
        if total_duration > 40:  # More than a work week
            validation_results["suggestions"].append(
                "Consider breaking down the plan into smaller phases"
            )

        # Calculate completeness score
        required_fields = ["task_id", "type", "prompt", "agent_type"]
        completed_fields = 0
        total_fields = len(required_fields) * len(execution_plan)

        for task_data in execution_plan:
            for field in required_fields:
                if task_data.get(field):
                    completed_fields += 1

        validation_results["completeness_score"] = (
            completed_fields / total_fields if total_fields > 0 else 0.0
        )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            execution_time=0.0,
            success=True,
            data=validation_results,
            metadata={"validation_type": "plan_validation"},
        )

    async def _optimize_plan(self, task: AgentTask) -> AgentResult:
        """Optimize an execution plan for efficiency and resource usage."""
        execution_plan = task.get("context", {}).get("execution_plan", [])

        if not execution_plan:
            raise ValidationError("No execution plan provided for optimization")

        # Convert to AgentTask objects for processing
        tasks = [AgentTask(**t) for t in execution_plan]

        # Optimize task sequence
        optimized_tasks = await self._optimize_task_sequence(tasks)

        # Calculate improvements
        original_duration = sum(t.get("estimated_duration", 0) for t in tasks)
        optimized_duration = sum(
            t.get("estimated_duration", 0) for t in optimized_tasks
        )

        optimization_results = {
            "optimized_plan": [dict(t) for t in optimized_tasks],
            "improvements": {
                "duration_reduction_hours": original_duration - optimized_duration,
                "efficiency_gain_percent": (
                    ((original_duration - optimized_duration) / original_duration * 100)
                    if original_duration > 0
                    else 0
                ),
                "parallelizable_tasks": len(
                    [t for t in optimized_tasks if not t.get("dependencies")]
                ),
            },
        }

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            execution_time=0.0,
            success=True,
            data=optimization_results,
            metadata={"optimization_type": "plan_optimization"},
        )

    async def _analyze_project_objective(
        self, objective: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze objective to determine project type and characteristics."""
        objective_lower = objective.lower()

        # Determine project type
        project_type = "software_development"  # default
        if any(
            keyword in objective_lower
            for keyword in ["api", "endpoint", "rest", "graphql"]
        ):
            project_type = "api_development"
        elif any(
            keyword in objective_lower
            for keyword in ["data", "pipeline", "etl", "processing"]
        ):
            project_type = "data_processing"

        # Estimate complexity
        complexity_indicators = {
            "simple": ["simple", "basic", "minimal", "quick"],
            "medium": ["standard", "typical", "moderate"],
            "high": ["complex", "advanced", "sophisticated", "enterprise"],
            "very_high": [
                "very complex",
                "distributed",
                "scalable",
                "high-performance",
            ],
        }

        complexity = self.default_complexity
        for level, indicators in complexity_indicators.items():
            if any(indicator in objective_lower for indicator in indicators):
                complexity = level
                break

        # Extract technology preferences
        technologies = []
        tech_keywords = {
            "python": ["python", "django", "flask", "fastapi"],
            "javascript": ["javascript", "node", "react", "vue"],
            "java": ["java", "spring", "maven"],
            "database": ["database", "sql", "postgres", "mysql", "mongodb"],
        }

        for tech, keywords in tech_keywords.items():
            if any(keyword in objective_lower for keyword in keywords):
                technologies.append(tech)

        return {
            "objective": objective,
            "project_type": project_type,
            "complexity": complexity,
            "technologies": technologies,
            "estimated_scope": self._estimate_scope(objective, complexity),
            "analysis_timestamp": datetime.now(UTC).isoformat(),
        }

    def _estimate_scope(self, objective: str, complexity: str) -> Dict[str, Any]:
        """Estimate project scope based on objective and complexity."""
        base_hours = {"simple": 8, "medium": 20, "high": 40, "very_high": 80}

        return {
            "estimated_hours": base_hours.get(complexity, 20),
            "estimated_tasks": base_hours.get(complexity, 20) // 4,
            "estimated_duration_days": base_hours.get(complexity, 20) // 8,
        }

    def _customize_task_prompt(
        self, template: Dict[str, Any], objective: str, context: Dict[str, Any]
    ) -> str:
        """Customize task prompt based on template and objective."""
        base_prompt: str = str(template["description"])

        # Add objective-specific context
        if "for" not in base_prompt.lower():
            base_prompt += f" for: {objective}"

        # Add technology-specific context
        technologies = context.get("technologies", [])
        if technologies:
            base_prompt += f" using {', '.join(technologies)}"

        # Add complexity context
        complexity = context.get("complexity", "medium")
        if complexity in ["high", "very_high"]:
            base_prompt += f" (complexity: {complexity})"

        return base_prompt

    async def _generate_additional_tasks(
        self, objective: str, context: Dict[str, Any], analysis: Dict[str, Any]
    ) -> List[AgentTask]:
        """Generate additional tasks based on specific requirements."""
        additional_tasks = []

        # Add documentation task if needed
        if "documentation" in objective.lower() or analysis.get("complexity") in [
            "high",
            "very_high",
        ]:
            doc_task = AgentTask(
                task_id="additional_documentation",
                type="documentation",
                prompt=f"Create comprehensive documentation for: {objective}",
                context=context,
                agent_type="code_generation",
                priority="low",
                estimated_duration=2.0,
            )
            additional_tasks.append(doc_task)

        # Add security review for sensitive projects
        if any(
            keyword in objective.lower()
            for keyword in ["security", "authentication", "api", "database"]
        ):
            security_task = AgentTask(
                task_id="additional_security_review",
                type="security_review",
                prompt=f"Perform security review for: {objective}",
                context=context,
                agent_type="review",
                priority="high",
                estimated_duration=1.5,
            )
            additional_tasks.append(security_task)

        return additional_tasks

    async def _optimize_task_sequence(self, tasks: List[AgentTask]) -> List[AgentTask]:
        """Optimize task sequence for parallel execution and efficiency."""
        # Create dependency graph
        task_map = {task.task_id: task for task in tasks}
        remaining_tasks = set(task.task_id for task in tasks)
        optimized_sequence = []

        # Process tasks in dependency order
        while remaining_tasks:
            # Find tasks with no unresolved dependencies
            ready_tasks = []
            for task_id in remaining_tasks:
                task = task_map[task_id]
                dependencies = task.get("dependencies", [])
                # Check if all dependencies have been processed (not in remaining_tasks)
                if not dependencies or all(
                    dep not in remaining_tasks for dep in dependencies
                ):
                    ready_tasks.append(task_id)

            if not ready_tasks:
                # Handle circular dependencies by taking the first remaining task
                self.logger.warning("Circular dependency detected, breaking cycle")
                ready_tasks = [next(iter(remaining_tasks))]

            # Sort ready tasks by priority and duration
            ready_tasks.sort(
                key=lambda tid: (
                    {"high": 0, "medium": 1, "low": 2}.get(
                        task_map[tid].get("priority", "medium"), 1
                    ),
                    task_map[tid].get("estimated_duration", 0.0),
                )
            )

            # Add ready tasks to sequence
            for task_id in ready_tasks:
                optimized_sequence.append(task_map[task_id])
                remaining_tasks.remove(task_id)

        return optimized_sequence

    async def _calculate_timeline(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """Calculate project timeline based on tasks."""
        total_hours = sum(task.get("estimated_duration", 0.0) for task in tasks)

        # Assume 8-hour work days and identify parallel tasks
        sequential_hours = 0
        parallel_groups = []
        current_group = []

        for task in tasks:
            dependencies = task.get("dependencies", [])
            if not dependencies:
                current_group.append(task)
            else:
                if current_group:
                    parallel_groups.append(current_group)
                    current_group = []
                sequential_hours += task.get("estimated_duration", 0.0)

        if current_group:
            parallel_groups.append(current_group)

        # Calculate parallel time savings
        parallel_savings = 0
        for group in parallel_groups:
            if len(group) > 1:
                max_duration = max(
                    task.get("estimated_duration", 0.0) for task in group
                )
                total_duration = sum(
                    task.get("estimated_duration", 0.0) for task in group
                )
                parallel_savings += total_duration - max_duration

        effective_hours = total_hours - parallel_savings

        return {
            "total_estimated_hours": total_hours,
            "effective_hours_with_parallelization": effective_hours,
            "estimated_work_days": effective_hours / 8,
            "estimated_calendar_days": (effective_hours / 8)
            * 1.4,  # Account for non-work time
            "parallelization_savings_hours": parallel_savings,
            "start_date": datetime.now(UTC).isoformat(),
            "estimated_completion": (
                datetime.now(UTC) + timedelta(days=effective_hours / 8 * 1.4)
            ).isoformat(),
        }

    async def _estimate_execution_resources(
        self, tasks: List[AgentTask]
    ) -> Dict[str, Any]:
        """Estimate resource requirements for executing tasks."""
        agent_utilization: Dict[str, float] = {}
        for task in tasks:
            agent_type = task.get("agent_type", "unknown")
            agent_utilization[agent_type] = agent_utilization.get(
                agent_type, 0
            ) + task.get("estimated_duration", 0.0)

        return {
            "total_effort_hours": sum(
                task.get("estimated_duration", 0.0) for task in tasks
            ),
            "agent_utilization": agent_utilization,
            "peak_concurrent_agents": len(
                set(
                    task.get("agent_type", "unknown")
                    for task in tasks
                    if not task.get("dependencies")
                )
            ),
            "required_agent_types": list(
                set(task.get("agent_type", "unknown") for task in tasks)
            ),
            "estimated_cost_units": sum(
                task.get("estimated_duration", 0.0)
                * self._get_agent_cost_factor(task.get("agent_type", "unknown"))
                for task in tasks
            ),
        }

    def _get_agent_cost_factor(self, agent_type: str) -> float:
        """Get cost factor for different agent types."""
        cost_factors = {
            "planning": 1.0,
            "code_generation": 1.5,
            "testing": 1.2,
            "review": 1.1,
            "deployment": 0.8,
        }
        return cost_factors.get(agent_type, 1.0)

    async def _assess_risks(
        self, tasks: List[AgentTask], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess risks for the execution plan."""
        risks = []

        # Complexity risk
        total_complexity = len(
            [t for t in tasks if context.get("complexity") in ["high", "very_high"]]
        )
        if total_complexity > 3:
            risks.append(
                {
                    "type": "complexity",
                    "level": "medium",
                    "description": "High number of complex tasks may lead to delays",
                }
            )

        # Dependency risk
        max_dependencies = (
            max(len(task.get("dependencies", [])) for task in tasks) if tasks else 0
        )
        if max_dependencies > 3:
            risks.append(
                {
                    "type": "dependency",
                    "level": "medium",
                    "description": "Complex dependency chain may cause bottlenecks",
                }
            )

        # Resource risk
        total_hours = sum(task.get("estimated_duration", 0.0) for task in tasks)
        if total_hours > 40:
            risks.append(
                {
                    "type": "resource",
                    "level": "high",
                    "description": "Large project may require additional resources",
                }
            )

        return {
            "identified_risks": risks,
            "overall_risk_level": (
                "high"
                if any(r["level"] == "high" for r in risks)
                else "medium" if risks else "low"
            ),
            "mitigation_suggestions": [
                "Regular progress reviews and checkpoints",
                "Parallel task execution where possible",
                "Early identification of blockers",
            ],
        }
