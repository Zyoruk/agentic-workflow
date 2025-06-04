"""Agentic Workflow Agents Module.

This module provides the agent implementations for the agentic workflow system.
Each agent specializes in different aspects of software development and workflow
orchestration.
"""

from typing import Any, Dict, List, Optional

from .base import Agent, AgentResult, AgentTask
from .code_generation import CodeGenerationAgent
from .planning import PlanningAgent
from .review import ReviewAgent
from .testing import TestingAgent

# Agent registry for factory pattern
AGENT_REGISTRY: Dict[str, type] = {
    "code_generation": CodeGenerationAgent,
    "code_gen": CodeGenerationAgent,  # Alias
    "planning": PlanningAgent,
    "planner": PlanningAgent,  # Alias
    "review": ReviewAgent,
    "reviewer": ReviewAgent,  # Alias
    "testing": TestingAgent,
    "tester": TestingAgent,  # Alias
}


def create_agent(
    agent_type: str,
    agent_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Agent:
    """Factory function to create agents by type.

    Args:
        agent_type: Type of agent to create
        agent_id: Optional agent ID (auto-generated if not provided)
        config: Optional agent configuration
        **kwargs: Additional arguments passed to agent constructor

    Returns:
        Agent instance

    Raises:
        ValueError: If agent_type is not supported
    """
    if agent_type not in AGENT_REGISTRY:
        available_types = list(AGENT_REGISTRY.keys())
        raise ValueError(
            f"Unknown agent type '{agent_type}'. Available types: {available_types}"
        )

    agent_class = AGENT_REGISTRY[agent_type]
    agent_id = agent_id or f"{agent_type}_agent"
    config = config or {}

    # Create and return the agent instance with proper typing
    agent_instance: Agent = agent_class(agent_id=agent_id, config=config, **kwargs)
    return agent_instance


def get_available_agent_types() -> List[str]:
    """Get list of available agent types.

    Returns:
        List of supported agent type names
    """
    return list(AGENT_REGISTRY.keys())


__all__ = [
    "Agent",
    "AgentResult",
    "AgentTask",
    "CodeGenerationAgent",
    "PlanningAgent",
    "ReviewAgent",
    "TestingAgent",
    "create_agent",
    "get_available_agent_types",
    "AGENT_REGISTRY",
]
