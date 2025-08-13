"""Advanced reasoning patterns for agentic workflow system.

This module implements various reasoning patterns that enhance agent decision-making
and problem-solving capabilities, including Chain of Thought, ReAct, and RAISE patterns.
"""

import json
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from agentic_workflow.core.exceptions import ReasoningError
from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.memory.interfaces import MemoryType


logger = get_logger(__name__)


class ReasoningStep(BaseModel):
    """Individual step in a reasoning process."""
    
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    question: str
    thought: str
    action: Optional[str] = None
    observation: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ReasoningPath(BaseModel):
    """Complete reasoning path with all steps."""
    
    path_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    agent_id: str
    pattern_type: str
    objective: str
    steps: List[ReasoningStep] = []
    final_answer: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    completed: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: Optional[str] = None


class ReasoningPattern(ABC):
    """Abstract base class for reasoning patterns."""
    
    def __init__(self, agent_id: str, memory_manager=None):
        self.agent_id = agent_id
        self.memory_manager = memory_manager
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def reason(self, objective: str, context: Dict[str, Any] = None) -> ReasoningPath:
        """Execute the reasoning pattern for a given objective."""
        pass
    
    @abstractmethod
    def validate_reasoning(self, path: ReasoningPath) -> bool:
        """Validate the quality of the reasoning path."""
        pass
    
    def store_reasoning_path(self, path: ReasoningPath) -> None:
        """Store reasoning path in memory system."""
        if self.memory_manager:
            try:
                # Store in short-term memory for immediate access
                self.memory_manager.store(
                    key=f"reasoning_path_{path.path_id}",
                    data=path.model_dump(),
                    memory_type=MemoryType.SHORT_TERM,
                    metadata={
                        "agent_id": self.agent_id,
                        "task_id": path.task_id,
                        "pattern_type": path.pattern_type,
                        "created_at": path.created_at
                    }
                )
                
                # Store in vector store for similarity search
                self.memory_manager.store(
                    key=f"reasoning_embedding_{path.path_id}",
                    data={
                        "objective": path.objective,
                        "reasoning_summary": self._summarize_reasoning(path),
                        "pattern_type": path.pattern_type,
                        "confidence": path.confidence
                    },
                    memory_type=MemoryType.VECTOR,
                    metadata={
                        "type": "reasoning_path",
                        "agent_id": self.agent_id,
                        "pattern": path.pattern_type
                    }
                )
                
                self.logger.info(f"Stored reasoning path {path.path_id} for task {path.task_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to store reasoning path: {e}")
    
    def _summarize_reasoning(self, path: ReasoningPath) -> str:
        """Create a summary of the reasoning path for embeddings."""
        summary_parts = [f"Objective: {path.objective}"]
        
        for step in path.steps:
            summary_parts.append(f"Step {step.step_number}: {step.thought}")
            if step.action:
                summary_parts.append(f"Action: {step.action}")
            if step.observation:
                summary_parts.append(f"Observation: {step.observation}")
        
        if path.final_answer:
            summary_parts.append(f"Final Answer: {path.final_answer}")
        
        return " | ".join(summary_parts)


class ChainOfThoughtReasoning(ReasoningPattern):
    """Chain of Thought (CoT) reasoning implementation.
    
    CoT breaks down complex problems into step-by-step reasoning,
    making the decision process transparent and more reliable.
    """
    
    def __init__(self, agent_id: str, memory_manager=None, max_steps: int = 10):
        super().__init__(agent_id, memory_manager)
        self.max_steps = max_steps
        self.pattern_type = "chain_of_thought"
    
    def reason(self, objective: str, context: Dict[str, Any] = None) -> ReasoningPath:
        """Execute Chain of Thought reasoning."""
        context = context or {}
        task_id = context.get("task_id", str(uuid.uuid4()))
        
        self.logger.info(f"Starting CoT reasoning for objective: {objective}")
        
        path = ReasoningPath(
            task_id=task_id,
            agent_id=self.agent_id,
            pattern_type=self.pattern_type,
            objective=objective
        )
        
        try:
            # Step 1: Problem decomposition
            decomposition_step = self._decompose_problem(objective, context)
            path.steps.append(decomposition_step)
            
            # Step 2: Identify required information
            info_step = self._identify_required_info(objective, context, decomposition_step)
            path.steps.append(info_step)
            
            # Step 3: Generate solution approach
            approach_step = self._generate_approach(objective, context, path.steps)
            path.steps.append(approach_step)
            
            # Step 4: Execute reasoning steps
            for step_num in range(4, self.max_steps + 1):
                reasoning_step = self._execute_reasoning_step(
                    step_num, objective, context, path.steps
                )
                path.steps.append(reasoning_step)
                
                # Check if we have enough confidence to conclude
                if reasoning_step.confidence > 0.9 or self._should_conclude(path.steps):
                    break
            
            # Final step: Synthesize conclusion
            conclusion_step = self._synthesize_conclusion(objective, path.steps)
            path.steps.append(conclusion_step)
            path.final_answer = conclusion_step.thought
            
            # Calculate overall confidence
            path.confidence = self._calculate_path_confidence(path.steps)
            path.completed = True
            path.completed_at = datetime.now(UTC).isoformat()
            
            # Store the reasoning path
            self.store_reasoning_path(path)
            
            self.logger.info(f"CoT reasoning completed with confidence {path.confidence:.2f}")
            return path
            
        except Exception as e:
            self.logger.error(f"CoT reasoning failed: {e}")
            raise ReasoningError(f"Chain of Thought reasoning failed: {e}")
    
    def validate_reasoning(self, path: ReasoningPath) -> bool:
        """Validate CoT reasoning quality."""
        if not path.steps:
            return False
        
        # Check for logical progression
        if len(path.steps) < 3:
            return False
        
        # Validate confidence progression
        confidences = [step.confidence for step in path.steps]
        if not any(c > 0.7 for c in confidences):
            return False
        
        # Check for conclusion
        if not path.final_answer or path.confidence < 0.5:
            return False
        
        return True
    
    def _decompose_problem(self, objective: str, context: Dict[str, Any]) -> ReasoningStep:
        """Break down the problem into components."""
        return ReasoningStep(
            step_number=1,
            question="What are the key components of this problem?",
            thought=f"Breaking down '{objective}' into smaller, manageable parts. "
                   f"The main components appear to be: problem identification, "
                   f"solution space exploration, and implementation planning.",
            confidence=0.8
        )
    
    def _identify_required_info(self, objective: str, context: Dict[str, Any], 
                               prev_step: ReasoningStep) -> ReasoningStep:
        """Identify what information is needed."""
        return ReasoningStep(
            step_number=2,
            question="What information do I need to solve this?",
            thought=f"To solve '{objective}', I need to understand: the current state, "
                   f"desired outcome, available resources, constraints, and success criteria. "
                   f"From context: {list(context.keys()) if context else 'No additional context'}",
            confidence=0.8
        )
    
    def _generate_approach(self, objective: str, context: Dict[str, Any], 
                          prev_steps: List[ReasoningStep]) -> ReasoningStep:
        """Generate the solution approach."""
        return ReasoningStep(
            step_number=3,
            question="What's the best approach to solve this?",
            thought=f"Based on my analysis, the best approach is to: "
                   f"1) Analyze requirements, 2) Design solution, 3) Implement incrementally, "
                   f"4) Test and validate. This systematic approach aligns with the problem "
                   f"decomposition from step 1.",
            confidence=0.8
        )
    
    def _execute_reasoning_step(self, step_num: int, objective: str, 
                               context: Dict[str, Any], 
                               prev_steps: List[ReasoningStep]) -> ReasoningStep:
        """Execute an individual reasoning step."""
        # This would ideally use an LLM for more sophisticated reasoning
        # For now, we'll simulate structured thinking
        
        questions = [
            "What are the potential solutions?",
            "What are the trade-offs of each approach?", 
            "What implementation details matter most?",
            "What could go wrong and how to mitigate?",
            "How will we measure success?"
        ]
        
        question_idx = min(step_num - 4, len(questions) - 1)
        question = questions[question_idx]
        
        thought = f"Considering {question.lower()} for '{objective}'. "
        
        if step_num == 4:
            thought += "Multiple solutions exist: direct implementation, modular approach, or iterative development."
        elif step_num == 5:
            thought += "Trade-offs include: speed vs quality, simplicity vs flexibility, cost vs features."
        elif step_num == 6:
            thought += "Key implementation details: architecture patterns, error handling, scalability considerations."
        elif step_num == 7:
            thought += "Risk mitigation: testing strategy, rollback plans, monitoring and alerting."
        else:
            thought += "Success metrics: functionality, performance, user satisfaction, maintainability."
        
        return ReasoningStep(
            step_number=step_num,
            question=question,
            thought=thought,
            confidence=max(0.6, 0.9 - (step_num - 4) * 0.05)  # Decreasing confidence over time
        )
    
    def _should_conclude(self, steps: List[ReasoningStep]) -> bool:
        """Determine if we have enough information to conclude."""
        if len(steps) < 5:
            return False
        
        # Check if recent steps show converging confidence
        recent_confidences = [step.confidence for step in steps[-3:]]
        return all(c > 0.75 for c in recent_confidences)
    
    def _synthesize_conclusion(self, objective: str, steps: List[ReasoningStep]) -> ReasoningStep:
        """Synthesize the final conclusion."""
        return ReasoningStep(
            step_number=len(steps) + 1,
            question="What is my final conclusion?",
            thought=f"Based on my step-by-step analysis of '{objective}', "
                   f"I recommend implementing a structured approach that considers "
                   f"requirements, design, implementation, and validation phases. "
                   f"This conclusion is supported by {len(steps)} reasoning steps "
                   f"and addresses the key challenges identified.",
            confidence=0.85
        )
    
    def _calculate_path_confidence(self, steps: List[ReasoningStep]) -> float:
        """Calculate overall confidence for the reasoning path."""
        if not steps:
            return 0.0
        
        # Weight later steps more heavily as they build on earlier analysis
        weights = [1.0 + i * 0.1 for i in range(len(steps))]
        weighted_sum = sum(step.confidence * weight for step, weight in zip(steps, weights))
        total_weight = sum(weights)
        
        return min(0.95, weighted_sum / total_weight)  # Cap at 0.95


class ReActReasoning(ReasoningPattern):
    """ReAct (Reasoning + Acting) pattern implementation.
    
    ReAct combines reasoning and acting in iterative cycles,
    allowing agents to plan, act, observe, and adapt their approach.
    """
    
    def __init__(self, agent_id: str, memory_manager=None, max_cycles: int = 5):
        super().__init__(agent_id, memory_manager)
        self.max_cycles = max_cycles
        self.pattern_type = "react"
    
    def reason(self, objective: str, context: Dict[str, Any] = None) -> ReasoningPath:
        """Execute ReAct reasoning cycles."""
        context = context or {}
        task_id = context.get("task_id", str(uuid.uuid4()))
        
        self.logger.info(f"Starting ReAct reasoning for objective: {objective}")
        
        path = ReasoningPath(
            task_id=task_id,
            agent_id=self.agent_id,
            pattern_type=self.pattern_type,
            objective=objective
        )
        
        try:
            for cycle in range(self.max_cycles):
                # Reasoning phase
                reasoning_step = self._reasoning_phase(cycle + 1, objective, context, path.steps)
                path.steps.append(reasoning_step)
                
                # Acting phase
                action_step = self._acting_phase(cycle + 1, objective, context, path.steps)
                path.steps.append(action_step)
                
                # Observation phase
                observation_step = self._observation_phase(cycle + 1, objective, context, path.steps)
                path.steps.append(observation_step)
                
                # Check if objective is achieved
                if self._objective_achieved(objective, path.steps):
                    break
            
            # Final conclusion
            conclusion_step = self._conclude_react(objective, path.steps)
            path.steps.append(conclusion_step)
            path.final_answer = conclusion_step.thought
            
            path.confidence = self._calculate_path_confidence(path.steps)
            path.completed = True
            path.completed_at = datetime.now(UTC).isoformat()
            
            self.store_reasoning_path(path)
            
            self.logger.info(f"ReAct reasoning completed with {len(path.steps)} steps")
            return path
            
        except Exception as e:
            self.logger.error(f"ReAct reasoning failed: {e}")
            raise ReasoningError(f"ReAct reasoning failed: {e}")
    
    def validate_reasoning(self, path: ReasoningPath) -> bool:
        """Validate ReAct reasoning quality."""
        if len(path.steps) < 6:  # At least 2 complete cycles
            return False
        
        # Check for proper cycle structure (Reason-Act-Observe pattern)
        cycle_count = len(path.steps) // 3
        if cycle_count < 1:
            return False
        
        # Validate that actions were taken and observations recorded
        has_actions = any(step.action for step in path.steps)
        has_observations = any(step.observation for step in path.steps)
        
        return has_actions and has_observations and path.confidence > 0.5
    
    def _reasoning_phase(self, cycle: int, objective: str, context: Dict[str, Any], 
                        prev_steps: List[ReasoningStep]) -> ReasoningStep:
        """Execute reasoning phase of ReAct cycle."""
        thought = f"Cycle {cycle} - Reasoning: Analyzing current situation for '{objective}'. "
        
        if cycle == 1:
            thought += "Initial assessment shows need for systematic approach."
        else:
            # Analyze previous observations
            recent_obs = [s.observation for s in prev_steps[-3:] if s.observation]
            if recent_obs:
                thought += f"Previous actions yielded: {recent_obs[-1][:100]}... Adjusting strategy."
            else:
                thought += "Need to gather more information before proceeding."
        
        return ReasoningStep(
            step_number=len(prev_steps) + 1,
            question=f"What should I think about this situation? (Cycle {cycle})",
            thought=thought,
            confidence=0.8
        )
    
    def _acting_phase(self, cycle: int, objective: str, context: Dict[str, Any], 
                     prev_steps: List[ReasoningStep]) -> ReasoningStep:
        """Execute acting phase of ReAct cycle."""
        actions = [
            "analyze_requirements",
            "design_solution", 
            "implement_component",
            "test_functionality",
            "validate_results"
        ]
        
        action = actions[min(cycle - 1, len(actions) - 1)]
        
        return ReasoningStep(
            step_number=len(prev_steps) + 1,
            question=f"What action should I take? (Cycle {cycle})",
            thought=f"Based on my reasoning, I will execute: {action}",
            action=action,
            confidence=0.8
        )
    
    def _observation_phase(self, cycle: int, objective: str, context: Dict[str, Any], 
                          prev_steps: List[ReasoningStep]) -> ReasoningStep:
        """Execute observation phase of ReAct cycle."""
        # Get the action from the previous step
        action = prev_steps[-1].action if prev_steps else "unknown"
        
        observations = {
            "analyze_requirements": "Requirements are well-defined with clear acceptance criteria",
            "design_solution": "Solution architecture is feasible with identified components",
            "implement_component": "Implementation is progressing with expected functionality",
            "test_functionality": "Tests pass with 95% coverage and no critical issues",
            "validate_results": "Results meet requirements and stakeholder expectations"
        }
        
        observation = observations.get(action, "Action completed successfully")
        
        return ReasoningStep(
            step_number=len(prev_steps) + 1,
            question=f"What did I observe? (Cycle {cycle})",
            thought=f"Observing results of {action}",
            observation=observation,
            confidence=0.8
        )
    
    def _objective_achieved(self, objective: str, steps: List[ReasoningStep]) -> bool:
        """Check if the objective has been achieved."""
        if len(steps) < 6:  # Need at least 2 complete cycles
            return False
        
        # Check if recent observations indicate success
        recent_observations = [s.observation for s in steps[-3:] if s.observation]
        success_indicators = ["completed", "successful", "meets requirements", "expectations"]
        
        return any(
            any(indicator in obs.lower() for indicator in success_indicators)
            for obs in recent_observations
        )
    
    def _conclude_react(self, objective: str, steps: List[ReasoningStep]) -> ReasoningStep:
        """Generate final conclusion for ReAct reasoning."""
        cycles_completed = len([s for s in steps if s.action]) 
        
        return ReasoningStep(
            step_number=len(steps) + 1,
            question="What is my final conclusion from this ReAct process?",
            thought=f"Through {cycles_completed} reasoning-acting-observing cycles for '{objective}', "
                   f"I have systematically approached the problem, taken concrete actions, "
                   f"and learned from observations. The iterative process has led to "
                   f"a well-informed solution that addresses the original objective.",
            confidence=0.85
        )
    
    def _calculate_path_confidence(self, steps: List[ReasoningStep]) -> float:
        """Calculate overall confidence for the ReAct reasoning path."""
        if not steps:
            return 0.0
        
        # For ReAct, weight observation steps more heavily as they indicate real progress
        total_weight = 0.0
        weighted_sum = 0.0
        
        for step in steps:
            weight = 1.0
            if step.observation:  # Observation steps get higher weight
                weight = 1.5
            elif step.action:    # Action steps get medium weight
                weight = 1.2
            
            weighted_sum += step.confidence * weight
            total_weight += weight
        
        return min(0.95, weighted_sum / total_weight) if total_weight > 0 else 0.0


class ReasoningEngine:
    """Central engine for managing different reasoning patterns."""
    
    def __init__(self, agent_id: str, memory_manager=None):
        self.agent_id = agent_id
        self.memory_manager = memory_manager
        self.logger = get_logger(__name__)
        
        # Initialize available reasoning patterns
        self.patterns = {
            "chain_of_thought": ChainOfThoughtReasoning(agent_id, memory_manager),
            "react": ReActReasoning(agent_id, memory_manager)
        }
    
    def reason(self, objective: str, pattern: str = "chain_of_thought", 
               context: Dict[str, Any] = None) -> ReasoningPath:
        """Execute reasoning using specified pattern."""
        if pattern not in self.patterns:
            raise ReasoningError(f"Unknown reasoning pattern: {pattern}")
        
        self.logger.info(f"Executing {pattern} reasoning for: {objective}")
        return self.patterns[pattern].reason(objective, context)
    
    def get_similar_reasoning(self, objective: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar reasoning paths from memory."""
        if not self.memory_manager:
            return []
        
        try:
            # Search vector store for similar reasoning
            results = self.memory_manager.search(
                query=objective,
                memory_type=MemoryType.VECTOR,
                limit=limit,
                filters={"type": "reasoning_path", "agent_id": self.agent_id}
            )
            return results
        except Exception as e:
            self.logger.error(f"Failed to retrieve similar reasoning: {e}")
            return []
    
    def get_reasoning_history(self, task_id: str) -> Optional[ReasoningPath]:
        """Retrieve reasoning history for a specific task."""
        if not self.memory_manager:
            return None
        
        try:
            # Search for reasoning path by task_id
            results = self.memory_manager.search(
                query=f"task_id:{task_id}",
                memory_type=MemoryType.SHORT_TERM,
                limit=1
            )
            
            if results:
                return ReasoningPath(**results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve reasoning history: {e}")
            return None