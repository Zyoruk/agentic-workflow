"""Tests for reasoning patterns in agentic workflow system."""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock

from agentic_workflow.core.reasoning import (
    ChainOfThoughtReasoning,
    RAISEReasoning,
    ReActReasoning,
    ReasoningEngine,
    ReasoningStep,
    ReasoningPath,
    ReasoningError
)


class TestReasoningStep:
    """Test ReasoningStep model."""
    
    def test_reasoning_step_creation(self):
        """Test basic reasoning step creation."""
        step = ReasoningStep(
            step_number=1,
            question="What is the problem?",
            thought="The problem is complex and requires decomposition.",
            confidence=0.8
        )
        
        assert step.step_number == 1
        assert step.question == "What is the problem?"
        assert step.thought == "The problem is complex and requires decomposition."
        assert step.confidence == 0.8
        assert step.step_id is not None
        assert step.created_at is not None
    
    def test_reasoning_step_with_action_and_observation(self):
        """Test reasoning step with action and observation."""
        step = ReasoningStep(
            step_number=2,
            question="What action should I take?",
            thought="I should analyze the requirements first.",
            action="analyze_requirements",
            observation="Requirements are well-defined.",
            confidence=0.9
        )
        
        assert step.action == "analyze_requirements"
        assert step.observation == "Requirements are well-defined."
        assert step.confidence == 0.9


class TestReasoningPath:
    """Test ReasoningPath model."""
    
    def test_reasoning_path_creation(self):
        """Test basic reasoning path creation."""
        path = ReasoningPath(
            task_id="test_task",
            agent_id="test_agent",
            pattern_type="chain_of_thought",
            objective="Solve complex problem"
        )
        
        assert path.task_id == "test_task"
        assert path.agent_id == "test_agent"
        assert path.pattern_type == "chain_of_thought"
        assert path.objective == "Solve complex problem"
        assert len(path.steps) == 0
        assert not path.completed
        assert path.path_id is not None


class TestChainOfThoughtReasoning:
    """Test Chain of Thought reasoning pattern."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent_id = "test_agent"
        self.mock_memory = Mock()
        self.cot = ChainOfThoughtReasoning(
            agent_id=self.agent_id,
            memory_manager=self.mock_memory,
            max_steps=6
        )
    
    def test_cot_initialization(self):
        """Test CoT reasoning initialization."""
        assert self.cot.agent_id == self.agent_id
        assert self.cot.memory_manager == self.mock_memory
        assert self.cot.max_steps == 6
        assert self.cot.pattern_type == "chain_of_thought"
    
    @pytest.mark.asyncio
    async def test_cot_reasoning_basic(self):
        """Test basic CoT reasoning execution."""
        objective = "Create a web application"
        context = {"task_id": "web_app_task"}
        
        # Mock memory manager store method
        self.mock_memory.store = AsyncMock()
        
        path = await self.cot.reason(objective, context)
        
        assert isinstance(path, ReasoningPath)
        assert path.objective == objective
        assert path.task_id == "web_app_task"
        assert path.agent_id == self.agent_id
        assert path.pattern_type == "chain_of_thought"
        assert len(path.steps) >= 4  # At least decomposition, info, approach, conclusion
        assert path.completed
        assert path.final_answer is not None
        assert path.confidence > 0.0
        
        # Verify memory storage was called
        self.mock_memory.store.assert_called()
    
    @pytest.mark.asyncio
    async def test_cot_reasoning_steps_progression(self):
        """Test that CoT reasoning steps follow logical progression."""
        objective = "Design a microservices architecture"
        
        self.mock_memory.store = AsyncMock()
        
        path = await self.cot.reason(objective)
        
        # Check that steps are numbered sequentially
        for i, step in enumerate(path.steps):
            assert step.step_number == i + 1
        
        # Check that first few steps follow expected pattern
        assert "components" in path.steps[0].thought.lower()  # Decomposition
        assert "need" in path.steps[1].thought.lower() or "information" in path.steps[1].thought.lower()  # Info identification
        assert "approach" in path.steps[2].thought.lower()    # Approach generation
        
        # Check final step is conclusion
        final_step = path.steps[-1]
        assert "conclusion" in final_step.thought.lower() or "recommend" in final_step.thought.lower()
    
    def test_cot_validation_valid_path(self):
        """Test validation of valid reasoning path."""
        path = ReasoningPath(
            task_id="test",
            agent_id="test",
            pattern_type="chain_of_thought",
            objective="Test objective"
        )
        
        # Add valid steps
        for i in range(4):
            step = ReasoningStep(
                step_number=i + 1,
                question=f"Question {i + 1}",
                thought=f"Thought {i + 1}",
                confidence=0.8
            )
            path.steps.append(step)
        
        path.final_answer = "Valid conclusion"
        path.confidence = 0.8
        
        assert self.cot.validate_reasoning(path)
    
    def test_cot_validation_invalid_path(self):
        """Test validation of invalid reasoning paths."""
        # Empty path
        empty_path = ReasoningPath(
            task_id="test",
            agent_id="test", 
            pattern_type="chain_of_thought",
            objective="Test"
        )
        assert not self.cot.validate_reasoning(empty_path)
        
        # Too few steps
        short_path = ReasoningPath(
            task_id="test",
            agent_id="test",
            pattern_type="chain_of_thought", 
            objective="Test"
        )
        short_path.steps = [
            ReasoningStep(step_number=1, question="Q1", thought="T1", confidence=0.8)
        ]
        assert not self.cot.validate_reasoning(short_path)
        
        # Low confidence
        low_conf_path = ReasoningPath(
            task_id="test",
            agent_id="test",
            pattern_type="chain_of_thought",
            objective="Test"
        )
        for i in range(4):
            step = ReasoningStep(
                step_number=i + 1,
                question=f"Q{i+1}",
                thought=f"T{i+1}",
                confidence=0.3  # Low confidence
            )
            low_conf_path.steps.append(step)
        low_conf_path.confidence = 0.3
        
        assert not self.cot.validate_reasoning(low_conf_path)


class TestReActReasoning:
    """Test ReAct reasoning pattern."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent_id = "test_agent"
        self.mock_memory = Mock()
        self.react = ReActReasoning(
            agent_id=self.agent_id,
            memory_manager=self.mock_memory,
            max_cycles=3
        )
    
    def test_react_initialization(self):
        """Test ReAct reasoning initialization."""
        assert self.react.agent_id == self.agent_id
        assert self.react.memory_manager == self.mock_memory
        assert self.react.max_cycles == 3
        assert self.react.pattern_type == "react"
    
    @pytest.mark.asyncio
    async def test_react_reasoning_basic(self):
        """Test basic ReAct reasoning execution."""
        objective = "Implement user authentication"
        context = {"task_id": "auth_task"}
        
        self.mock_memory.store = AsyncMock()
        
        path = await self.react.reason(objective, context)
        
        assert isinstance(path, ReasoningPath)
        assert path.objective == objective
        assert path.task_id == "auth_task"
        assert path.agent_id == self.agent_id
        assert path.pattern_type == "react"
        assert path.completed
        assert path.final_answer is not None
        
        # ReAct should have cycles of Reason-Act-Observe + conclusion
        # Minimum: 3 steps per cycle + 1 conclusion = 4 steps for 1 cycle
        assert len(path.steps) >= 4
        
        # Verify memory storage was called
        self.mock_memory.store.assert_called()
    
    @pytest.mark.asyncio
    async def test_react_reasoning_cycles(self):
        """Test ReAct reasoning cycle structure."""
        objective = "Build API endpoints"
        
        self.mock_memory.store = AsyncMock()
        
        path = await self.react.reason(objective)
        
        # Check that we have proper cycle structure
        # Should have sets of 3 steps (reason, act, observe) + conclusion
        cycle_steps = len(path.steps) - 1  # Exclude conclusion
        assert cycle_steps % 3 == 0  # Should be multiple of 3
        
        # Check that actions and observations are present
        actions = [step for step in path.steps if step.action]
        observations = [step for step in path.steps if step.observation]
        
        assert len(actions) > 0
        assert len(observations) > 0
        assert len(actions) == len(observations)  # Should match
    
    def test_react_validation_valid_path(self):
        """Test validation of valid ReAct path."""
        path = ReasoningPath(
            task_id="test",
            agent_id="test",
            pattern_type="react",
            objective="Test objective"
        )
        
        # Add 2 complete cycles (6 steps) + conclusion
        for cycle in range(2):
            # Reasoning step
            path.steps.append(ReasoningStep(
                step_number=cycle * 3 + 1,
                question=f"Reasoning {cycle + 1}",
                thought=f"Analysis for cycle {cycle + 1}",
                confidence=0.8
            ))
            
            # Acting step
            path.steps.append(ReasoningStep(
                step_number=cycle * 3 + 2,
                question=f"Action {cycle + 1}",
                thought=f"Taking action {cycle + 1}",
                action=f"action_{cycle + 1}",
                confidence=0.8
            ))
            
            # Observation step
            path.steps.append(ReasoningStep(
                step_number=cycle * 3 + 3,
                question=f"Observation {cycle + 1}",
                thought=f"Observing results {cycle + 1}",
                observation=f"Results from action {cycle + 1}",
                confidence=0.8
            ))
        
        # Add conclusion
        path.steps.append(ReasoningStep(
            step_number=7,
            question="Final conclusion",
            thought="Final analysis",
            confidence=0.8
        ))
        
        path.final_answer = "Valid conclusion"
        path.confidence = 0.8
        
        assert self.react.validate_reasoning(path)
    
    def test_react_validation_invalid_path(self):
        """Test validation of invalid ReAct paths."""
        # Too few steps
        short_path = ReasoningPath(
            task_id="test",
            agent_id="test",
            pattern_type="react",
            objective="Test"
        )
        short_path.steps = [
            ReasoningStep(step_number=1, question="Q1", thought="T1", confidence=0.8)
        ]
        assert not self.react.validate_reasoning(short_path)
        
        # No actions
        no_action_path = ReasoningPath(
            task_id="test",
            agent_id="test",
            pattern_type="react",
            objective="Test"
        )
        for i in range(7):
            step = ReasoningStep(
                step_number=i + 1,
                question=f"Q{i+1}",
                thought=f"T{i+1}",
                confidence=0.8
                # No action field
            )
            no_action_path.steps.append(step)
        no_action_path.confidence = 0.8
        
        assert not self.react.validate_reasoning(no_action_path)


class TestReasoningEngine:
    """Test the central reasoning engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.agent_id = "test_agent"
        self.mock_memory = Mock()
        self.engine = ReasoningEngine(
            agent_id=self.agent_id,
            memory_manager=self.mock_memory
        )
    
    def test_engine_initialization(self):
        """Test reasoning engine initialization."""
        assert self.engine.agent_id == self.agent_id
        assert self.engine.memory_manager == self.mock_memory
        assert "chain_of_thought" in self.engine.patterns
        assert "react" in self.engine.patterns
    
    def test_engine_reason_cot(self):
        """Test reasoning with Chain of Thought pattern."""
        objective = "Solve a complex problem"
        
        mock_memory = Mock()
        engine = ReasoningEngine("test_agent", mock_memory)
        
        path = engine.reason(objective, pattern="chain_of_thought")
        
        assert isinstance(path, ReasoningPath)
        assert path.pattern_type == "chain_of_thought"
        assert path.objective == objective
    
    def test_engine_reason_react(self):
        """Test reasoning with ReAct pattern."""
        objective = "Implement a solution"
        
        mock_memory = Mock()
        engine = ReasoningEngine("test_agent", mock_memory)
        
        path = engine.reason(objective, pattern="react")
        
        assert isinstance(path, ReasoningPath)
        assert path.pattern_type == "react"
        assert path.objective == objective
    
    def test_engine_unknown_pattern(self):
        """Test error handling for unknown pattern."""
        with pytest.raises(ReasoningError, match="Unknown reasoning pattern"):
            self.engine.reason("test objective", pattern="unknown_pattern")
    
    def test_get_similar_reasoning(self):
        """Test retrieval of similar reasoning paths."""
        # Mock memory search
        mock_results = [
            {
                "objective": "Similar problem",
                "pattern_type": "chain_of_thought",
                "confidence": 0.8
            }
        ]
        self.mock_memory.search = Mock(return_value=mock_results)
        
        results = self.engine.get_similar_reasoning("Find similar solutions")
        
        assert len(results) == 1
        assert results[0]["objective"] == "Similar problem"
        
        # Verify search was called with correct parameters
        self.mock_memory.search.assert_called_once()
        call_args = self.mock_memory.search.call_args
        assert "Find similar solutions" in call_args[1]["query"]
    
    def test_get_similar_reasoning_no_memory(self):
        """Test similar reasoning retrieval without memory manager."""
        engine_no_memory = ReasoningEngine("test_agent", memory_manager=None)
        
        results = engine_no_memory.get_similar_reasoning("test objective")
        
        assert results == []
    
    def test_get_reasoning_history(self):
        """Test retrieval of reasoning history."""
        # Mock memory search
        mock_result = {
            "path_id": "test_path",
            "task_id": "test_task",
            "agent_id": "test_agent",
            "pattern_type": "chain_of_thought",
            "objective": "Test objective",
            "steps": [],
            "completed": True
        }
        self.mock_memory.search = Mock(return_value=[mock_result])
        
        path = self.engine.get_reasoning_history("test_task")
        
        assert isinstance(path, ReasoningPath)
        assert path.task_id == "test_task"
    
    def test_get_reasoning_history_not_found(self):
        """Test reasoning history retrieval when not found."""
        self.mock_memory.search = Mock(return_value=[])
        
        path = self.engine.get_reasoning_history("nonexistent_task")
        
        assert path is None


class TestReasoningMemoryIntegration:
    """Test reasoning pattern integration with memory system."""
    
    @pytest.mark.asyncio
    async def test_store_reasoning_path(self):
        """Test storing reasoning path in memory."""
        mock_memory = Mock()
        mock_memory.store = AsyncMock()
        
        cot = ChainOfThoughtReasoning("test_agent", mock_memory)
        
        path = ReasoningPath(
            task_id="test_task",
            agent_id="test_agent",
            pattern_type="chain_of_thought",
            objective="Test objective"
        )
        path.steps = [
            ReasoningStep(
                step_number=1,
                question="What is the problem?",
                thought="This is a test problem.",
                confidence=0.8
            )
        ]
        
        await cot.store_reasoning_path(path)
        
        # Verify store was called twice (short-term and vector)
        assert mock_memory.store.call_count == 2
        
        # Check the calls
        calls = mock_memory.store.call_args_list
        
        # First call should be short-term memory
        short_term_call = calls[0]
        assert "reasoning_path_" in short_term_call.kwargs["entry_id"]
        
        # Second call should be vector store
        vector_call = calls[1]
        assert "reasoning_embedding_" in vector_call.kwargs["entry_id"]
    
    @pytest.mark.asyncio
    async def test_store_reasoning_path_error_handling(self):
        """Test error handling when storing reasoning path fails."""
        mock_memory = Mock()
        mock_memory.store = AsyncMock(side_effect=Exception("Storage failed"))
        
        cot = ChainOfThoughtReasoning("test_agent", mock_memory)
        
        path = ReasoningPath(
            task_id="test_task",
            agent_id="test_agent", 
            pattern_type="chain_of_thought",
            objective="Test objective"
        )
        
        # Should not raise exception, just log error
        await cot.store_reasoning_path(path)
        
        # Verify store was attempted
        assert mock_memory.store.called


class TestRAISEReasoning:
    """Test RAISE reasoning pattern."""
    
    def test_raise_reasoning_creation(self):
        """Test RAISE reasoning instance creation."""
        mock_communication = Mock()
        raise_reasoning = RAISEReasoning("test_agent", communication_manager=mock_communication)
        
        assert raise_reasoning.agent_id == "test_agent"
        assert raise_reasoning.pattern_type == "raise"
        assert raise_reasoning.communication_manager == mock_communication
        assert raise_reasoning.max_cycles == 8
        assert raise_reasoning.improvement_threshold == 0.7
    
    @pytest.mark.asyncio
    async def test_raise_reasoning_execution(self):
        """Test RAISE reasoning execution."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        raise_reasoning = RAISEReasoning("test_agent", mock_memory, mock_communication)
        
        result = await raise_reasoning.reason("Implement microservices architecture")
        
        assert isinstance(result, ReasoningPath)
        assert result.pattern_type == "raise"
        assert result.objective == "Implement microservices architecture"
        assert len(result.steps) > 0
        assert result.completed
        assert result.final_answer is not None
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_raise_phases_representation(self):
        """Test that all RAISE phases are represented in reasoning."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        raise_reasoning = RAISEReasoning("test_agent", mock_memory, mock_communication)
        
        result = await raise_reasoning.reason("Test objective")
        
        # Check that all RAISE phases are present
        phases = ["reason", "act", "improve", "share", "evaluate"]
        found_phases = set()
        
        for step in result.steps:
            for phase in phases:
                if phase.lower() in step.thought.lower():
                    found_phases.add(phase)
        
        assert len(found_phases) == 5, f"Missing phases: {set(phases) - found_phases}"
    
    @pytest.mark.asyncio
    async def test_raise_reasoning_validation(self):
        """Test RAISE reasoning path validation."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        raise_reasoning = RAISEReasoning("test_agent", mock_memory, mock_communication)
        
        result = await raise_reasoning.reason("Test validation objective")
        
        assert raise_reasoning.validate_reasoning(result)
        assert result.confidence >= 0.6
    
    @pytest.mark.asyncio
    async def test_raise_reasoning_with_communication_error(self):
        """Test RAISE reasoning when communication fails."""
        mock_memory = Mock()
        mock_communication = Mock()
        mock_communication.broadcast_insight = AsyncMock(side_effect=Exception("Communication failed"))
        
        raise_reasoning = RAISEReasoning("test_agent", mock_memory, mock_communication)
        
        # Should not fail even if communication fails
        result = await raise_reasoning.reason("Test with communication error")
        
        assert isinstance(result, ReasoningPath)
        assert result.completed
    
    @pytest.mark.asyncio
    async def test_raise_reasoning_confidence_improvement(self):
        """Test that RAISE reasoning improves confidence over cycles."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        raise_reasoning = RAISEReasoning("test_agent", mock_memory, mock_communication)
        
        result = await raise_reasoning.reason("Complex optimization problem")
        
        # Find improve steps and check confidence progression
        improve_steps = [s for s in result.steps if "improve" in s.thought.lower()]
        
        assert len(improve_steps) > 0
        # At least some improve steps should show confidence improvement
        for step in improve_steps:
            assert step.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_raise_reasoning_early_completion(self):
        """Test RAISE reasoning early completion when threshold is met."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        # Set a lower threshold for easier completion
        raise_reasoning = RAISEReasoning("test_agent", mock_memory, mock_communication)
        raise_reasoning.improvement_threshold = 0.65
        
        result = await raise_reasoning.reason("Simple task")
        
        assert result.completed
        assert result.confidence >= 0.65
        # Should complete in fewer than max cycles
        assert len(result.steps) < raise_reasoning.max_cycles * 5  # 5 steps per cycle


class TestReasoningEngineWithRAISE:
    """Test ReasoningEngine with RAISE pattern integration."""
    
    def test_reasoning_engine_includes_raise(self):
        """Test that ReasoningEngine includes RAISE pattern."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        engine = ReasoningEngine("test_agent", mock_memory, mock_communication)
        
        assert "raise" in engine.patterns
        assert isinstance(engine.patterns["raise"], RAISEReasoning)
    
    def test_reasoning_engine_raise_execution(self):
        """Test ReasoningEngine can execute RAISE pattern."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        engine = ReasoningEngine("test_agent", mock_memory, mock_communication)
        
        result = engine.reason("Test RAISE execution", pattern="raise")
        
        assert isinstance(result, ReasoningPath)
        assert result.pattern_type == "raise"
        assert result.completed
    
    def test_reasoning_engine_pattern_selection(self):
        """Test that different patterns can be selected."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        engine = ReasoningEngine("test_agent", mock_memory, mock_communication)
        
        # Test CoT
        cot_result = engine.reason("Test objective", pattern="chain_of_thought")
        assert cot_result.pattern_type == "chain_of_thought"
        
        # Test ReAct
        react_result = engine.reason("Test objective", pattern="react")
        assert react_result.pattern_type == "react"
        
        # Test RAISE
        raise_result = engine.reason("Test objective", pattern="raise")
        assert raise_result.pattern_type == "raise"
    
    def test_reasoning_engine_unknown_pattern_error(self):
        """Test error handling for unknown patterns."""
        mock_memory = Mock()
        mock_communication = Mock()
        
        engine = ReasoningEngine("test_agent", mock_memory, mock_communication)
        
        with pytest.raises(ReasoningError, match="Unknown reasoning pattern: unknown"):
            engine.reason("Test objective", pattern="unknown")
        
        # Store should not be called for unknown patterns since it fails before execution
        assert not mock_memory.store.called