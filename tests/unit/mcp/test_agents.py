"""
Unit tests for MCP-enhanced agents.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from agentic_workflow.agents.base import AgentTask, AgentResult
from agentic_workflow.mcp.integration.agents import MCPEnhancedAgent, create_mcp_enhanced_agent
from agentic_workflow.mcp.client.base import MCPServerConfig


@pytest.fixture
def sample_agent_task():
    """Sample agent task."""
    return AgentTask(
        task_id="test_task_123",
        type="code_analysis",
        description="Analyze the given code file",
        file_path="/test/sample.py",
        requirements=["analyze syntax", "check for issues"]
    )


@pytest.fixture
def sample_server_config():
    """Sample MCP server configuration."""
    return MCPServerConfig(
        name="test_analyzer",
        command=["code-analyzer-server"],
        description="Code analysis server",
        timeout=60
    )


@pytest.mark.asyncio
class TestMCPEnhancedAgent:
    """Test MCP-enhanced agent functionality."""
    
    async def test_initialization_with_mcp_enabled(self, sample_server_config):
        """Test agent initialization with MCP enabled."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True,
            mcp_servers=[sample_server_config],
            mcp_categories=["development"],
            reasoning_enabled=False,  # Disable reasoning for focused test
            communication_manager=None
        )
        
        assert agent.mcp_enabled
        assert len(agent.mcp_servers) == 1
        assert agent.mcp_categories == ["development"]
        assert not agent.mcp_initialized  # Not initialized until initialize() is called
        assert not agent.reasoning_enabled  # Explicitly disabled
    
    async def test_initialization_with_mcp_disabled(self):
        """Test agent initialization with MCP disabled."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=False,
            reasoning_enabled=False,  # Disable reasoning for focused test
            communication_manager=None
        )
        
        assert not agent.mcp_enabled
        assert agent.mcp_client is None
        assert agent.mcp_registry is None
        assert agent.enhanced_tools is None
        assert not agent.reasoning_enabled
    
    @patch('agentic_workflow.mcp.integration.agents.MCPClient')
    @patch('agentic_workflow.mcp.integration.agents.MCPServerRegistry')
    @patch('agentic_workflow.mcp.integration.agents.EnhancedToolRegistry')
    @pytest.mark.asyncio
    async def test_mcp_initialization_success(self, mock_tools, mock_registry, mock_client):
        """Test successful MCP initialization."""
        # Setup mocks
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock()
        mock_client.return_value = mock_client_instance
        
        mock_registry_instance = AsyncMock()
        mock_registry_instance.initialize = AsyncMock()
        mock_registry_instance.register_server = AsyncMock(return_value=True)
        mock_registry_instance.connect_servers = AsyncMock(return_value={"test_server": True})
        mock_registry.return_value = mock_registry_instance
        
        mock_tools_instance = AsyncMock()
        mock_tools_instance.initialize = AsyncMock()
        mock_tools.return_value = mock_tools_instance
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        await agent.initialize()
        
        assert agent.mcp_initialized
        assert agent.mcp_client is not None
        assert agent.mcp_registry is not None
        assert agent.enhanced_tools is not None
        
        # Verify initialization calls
        mock_client_instance.initialize.assert_called_once()
        mock_registry_instance.initialize.assert_called_once()
        mock_tools_instance.initialize.assert_called_once()
    
    @patch('agentic_workflow.mcp.integration.agents.MCPClient')
    async def test_mcp_initialization_failure(self, mock_client):
        """Test MCP initialization failure."""
        # Make initialization fail
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize.side_effect = Exception("Init failed")
        mock_client.return_value = mock_client_instance
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        await agent.initialize()
        
        # Should disable MCP on failure
        assert not agent.mcp_enabled
        assert not agent.mcp_initialized
    
    async def test_execute_without_mcp(self, sample_agent_task):
        """Test task execution without MCP capabilities."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=False
        )
        
        await agent.initialize()
        
        # Mock the parent execute method
        with patch.object(agent.__class__.__bases__[0], 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AgentResult(
                success=True,
                data={"result": "traditional execution"},
                task_id=sample_agent_task.task_id,
                agent_id=agent.agent_id,
                execution_time=1.0,
                steps_taken=[]
            )
            
            result = await agent.execute(sample_agent_task)
            
            assert result.success
            assert result.data["result"] == "traditional execution"
            assert not result.metadata.get("mcp_enabled", False)
    
    @patch('agentic_workflow.mcp.integration.agents.MCPClient')
    @patch('agentic_workflow.mcp.integration.agents.MCPServerRegistry')  
    @patch('agentic_workflow.mcp.integration.agents.EnhancedToolRegistry')
    async def test_execute_with_mcp(self, mock_tools, mock_registry, mock_client, sample_agent_task):
        """Test task execution with MCP capabilities."""
        # Setup mocks with proper async behavior
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock()
        mock_client_instance.list_capabilities = AsyncMock(return_value=[])
        mock_client.return_value = mock_client_instance
        
        mock_registry_instance = AsyncMock()
        mock_registry_instance.initialize = AsyncMock()
        mock_registry_instance.connect_servers = AsyncMock(return_value={})
        mock_registry_instance.register_server = AsyncMock(return_value=True)
        mock_registry.return_value = mock_registry_instance
        
        mock_tools_instance = AsyncMock()
        mock_tools_instance.initialize = AsyncMock()
        mock_tools_instance.search_tools = AsyncMock(return_value=[
            Mock(name="code_analyzer", metadata=Mock(name="code_analyzer"))
        ])
        mock_tools_instance.execute_tool = AsyncMock(return_value={"analysis": "code looks good"})
        mock_tools_instance.refresh_mcp_tools = AsyncMock()
        mock_tools.return_value = mock_tools_instance
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        # Force MCP initialization to succeed for this test
        with patch.object(agent, '_initialize_mcp', new_callable=AsyncMock) as mock_init_mcp:
            mock_init_mcp.return_value = None
            agent.mcp_initialized = True
            agent.mcp_client = mock_client_instance
            agent.mcp_registry = mock_registry_instance
            agent.enhanced_tools = mock_tools_instance
            
            await agent.initialize()
            
            result = await agent.execute(sample_agent_task)
            
            assert result.success
            assert result.metadata["mcp_enabled"]
            assert "execution_time" in result.__dict__
            assert len(result.steps_taken) > 0
    
    async def test_capability_assessment(self, sample_agent_task):
        """Test dynamic capability assessment."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        # Mock MCP components
        agent.mcp_initialized = True
        agent.mcp_capabilities_cache = {
            'tools': [
                {'name': 'code_analyzer', 'description': 'Analyze code files', 'server': 'analyzer_server'},
                {'name': 'file_reader', 'description': 'Read file contents', 'server': 'fs_server'}
            ]
        }
        
        await agent._assess_dynamic_capabilities(sample_agent_task)
        
        # Should identify relevant tools based on task type
        assert len(agent.dynamic_capabilities) > 0
        # Code analysis task should match code analyzer tool
        assert any('code' in cap.lower() for cap in agent.dynamic_capabilities)
    
    async def test_enhanced_reasoning(self, sample_agent_task):
        """Test enhanced reasoning with MCP awareness."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        agent.dynamic_capabilities = ["code_analyzer", "file_reader"]
        
        reasoning_result = await agent._enhanced_reasoning(sample_agent_task)
        
        assert reasoning_result["approach"] == "enhanced_mcp_reasoning"
        assert len(reasoning_result["capabilities_considered"]) == 2
        assert len(reasoning_result["reasoning_steps"]) > 0
        assert "confidence" in reasoning_result
        assert reasoning_result["confidence"] > 0
    
    async def test_task_complexity_assessment(self, sample_agent_task):
        """Test task complexity assessment."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        # Test different complexity levels
        simple_task = AgentTask(description="simple file read", type="read")
        complex_task = AgentTask(description="complex analysis with multiple integrations", type="analysis")
        medium_task = AgentTask(description="process data file", type="processing")
        
        assert agent._assess_task_complexity(simple_task) == "low"
        assert agent._assess_task_complexity(complex_task) == "high"
        assert agent._assess_task_complexity(medium_task) == "medium"
    
    async def test_capability_identification(self, sample_agent_task):
        """Test required capability identification."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        capabilities = agent._identify_required_capabilities(sample_agent_task)
        
        # Code analysis task should identify code-related capabilities
        assert "code_analysis" in capabilities
        assert "file_operations" in capabilities
    
    async def test_tool_parameter_extraction(self, sample_agent_task):
        """Test tool parameter extraction from tasks."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        params = agent._extract_tool_parameters(sample_agent_task, "file-read")
        
        assert "path" in params
        assert params["path"] == sample_agent_task.get("file_path")
    
    @patch('agentic_workflow.mcp.integration.agents.EnhancedToolRegistry')
    async def test_mcp_execution_with_tools(self, mock_tools, sample_agent_task):
        """Test MCP execution with tool usage."""
        mock_tools_instance = AsyncMock()
        mock_tools_instance.execute_tool.return_value = {"analysis_result": "success"}
        mock_tools.return_value = mock_tools_instance
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        agent.enhanced_tools = mock_tools_instance
        
        reasoning_result = {
            "selected_tools": ["code_analyzer"],
            "approach": "mcp_enhanced"
        }
        
        execution_result = await agent._execute_with_mcp(sample_agent_task, reasoning_result)
        
        assert execution_result["success"]
        assert len(execution_result["tools_executed"]) == 1
        assert execution_result["tools_executed"][0]["tool"] == "code_analyzer"
        mock_tools_instance.execute_tool.assert_called_once()
    
    async def test_mcp_execution_no_tools(self, sample_agent_task):
        """Test MCP execution when no tools are selected."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        reasoning_result = {
            "selected_tools": [],
            "approach": "traditional"
        }
        
        execution_result = await agent._execute_with_mcp(sample_agent_task, reasoning_result)
        
        assert execution_result["execution_approach"] == "traditional"
        assert execution_result["success"]
    
    async def test_capability_usage_tracking(self, sample_agent_task):
        """Test capability usage tracking."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        agent._mcp_tools_used = ["tool1", "tool2"]
        result = {"success": True, "tools_executed": []}
        
        await agent._update_capability_usage(sample_agent_task, result)
        
        assert len(agent.capability_usage_history) == 1
        history_record = agent.capability_usage_history[0]
        assert history_record["task_id"] == sample_agent_task.task_id
        assert history_record["tools_used"] == ["tool1", "tool2"]
        assert history_record["success"] == True
    
    async def test_get_mcp_status(self):
        """Test MCP status reporting."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        agent.mcp_initialized = True
        agent.connected_servers = {"server1": True, "server2": False}
        agent.dynamic_capabilities = ["tool1", "tool2", "tool3"]
        
        status = await agent.get_mcp_status()
        
        assert status["mcp_enabled"]
        assert status["mcp_initialized"]
        assert status["connected_servers"]["server1"]
        assert not status["connected_servers"]["server2"]
        assert status["available_capabilities"] == 3
    
    @patch('agentic_workflow.mcp.integration.agents.MCPClient')
    @patch('agentic_workflow.mcp.integration.agents.MCPServerRegistry')
    @patch('agentic_workflow.mcp.integration.agents.EnhancedToolRegistry')
    async def test_refresh_mcp_capabilities(self, mock_tools, mock_registry, mock_client):
        """Test refreshing MCP capabilities."""
        # Setup mocks
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize = AsyncMock()
        mock_client_instance.list_capabilities = AsyncMock(return_value=[])
        mock_client.return_value = mock_client_instance
        
        mock_registry_instance = AsyncMock()
        mock_registry_instance.initialize = AsyncMock()
        mock_registry_instance.connect_servers = AsyncMock(return_value={})
        mock_registry.return_value = mock_registry_instance
        
        mock_tools_instance = AsyncMock()
        mock_tools_instance.initialize = AsyncMock()
        mock_tools_instance.refresh_mcp_tools = AsyncMock()
        mock_tools.return_value = mock_tools_instance
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        # Force successful MCP initialization for this test
        with patch.object(agent, '_initialize_mcp', new_callable=AsyncMock) as mock_init_mcp:
            mock_init_mcp.return_value = None
            agent.mcp_initialized = True
            agent.mcp_client = mock_client_instance
            agent.mcp_registry = mock_registry_instance
            agent.enhanced_tools = mock_tools_instance
            
            await agent.initialize()
            
            success = await agent.refresh_mcp_capabilities()
            
            assert success
            mock_tools_instance.refresh_mcp_tools.assert_called_once()
    
    async def test_refresh_capabilities_disabled(self):
        """Test refreshing capabilities when MCP is disabled."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=False
        )
        
        success = await agent.refresh_mcp_capabilities()
        
        assert not success
    
    @patch('agentic_workflow.mcp.integration.agents.MCPServerRegistry')
    async def test_connect_mcp_server(self, mock_registry, sample_server_config):
        """Test connecting to additional MCP server."""
        mock_registry_instance = AsyncMock()
        mock_registry_instance.register_server.return_value = True
        mock_registry.return_value = mock_registry_instance
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        agent.mcp_registry = mock_registry_instance
        
        # Mock refresh capabilities
        with patch.object(agent, 'refresh_mcp_capabilities', return_value=True):
            success = await agent.connect_mcp_server(sample_server_config)
        
        assert success
        assert agent.connected_servers[sample_server_config.name]
        mock_registry_instance.register_server.assert_called_once_with(sample_server_config)
    
    async def test_connect_server_disabled(self, sample_server_config):
        """Test connecting server when MCP is disabled."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=False
        )
        
        success = await agent.connect_mcp_server(sample_server_config)
        
        assert not success
    
    @patch('agentic_workflow.mcp.integration.agents.MCPClient')
    async def test_disconnect_mcp_server(self, mock_client):
        """Test disconnecting from MCP server."""
        mock_client_instance = AsyncMock()
        mock_client_instance.disconnect_server.return_value = True
        mock_client.return_value = mock_client_instance
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        agent.mcp_client = mock_client_instance
        
        # Mock refresh capabilities
        with patch.object(agent, 'refresh_mcp_capabilities', return_value=True):
            success = await agent.disconnect_mcp_server("test_server")
        
        assert success
        mock_client_instance.disconnect_server.assert_called_once_with("test_server")
    
    async def test_agent_close_cleanup(self):
        """Test agent cleanup on close."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True
        )
        
        # Mock MCP components
        mock_tools = AsyncMock()
        mock_client = AsyncMock()
        agent.enhanced_tools = mock_tools
        agent.mcp_client = mock_client
        
        # Call close - no need to mock parent close since base Agent doesn't have it
        await agent.close()
        
        mock_tools.close.assert_called_once()
        mock_client.close.assert_called_once()


class TestCreateMCPEnhancedAgent:
    """Test MCP enhanced agent creation helper."""
    
    def test_create_enhanced_agent_class(self):
        """Test creating MCP-enhanced agent class."""
        from agentic_workflow.agents.base import Agent
        
        # Create enhanced version of base Agent
        EnhancedAgent = create_mcp_enhanced_agent(
            Agent,
            mcp_enabled=True,
            mcp_categories=["development"]
        )
        
        # Should be a subclass of both MCPEnhancedAgent and Agent
        assert issubclass(EnhancedAgent, MCPEnhancedAgent)
        assert issubclass(EnhancedAgent, Agent)
    
    @pytest.mark.asyncio
    async def test_enhanced_agent_instance(self):
        """Test creating instance of enhanced agent."""
        from agentic_workflow.agents.base import Agent
        
        EnhancedAgent = create_mcp_enhanced_agent(
            Agent,
            mcp_enabled=True,
            mcp_categories=["development"]
        )
        
        agent = EnhancedAgent("test_agent")
        
        assert agent.agent_id == "test_agent"
        assert agent.mcp_enabled
        assert agent.mcp_categories == ["development"]
    
    @patch('agentic_workflow.mcp.integration.agents.MCPClient')
    @patch('agentic_workflow.mcp.integration.agents.MCPServerRegistry')
    @patch('agentic_workflow.mcp.integration.agents.EnhancedToolRegistry')
    @pytest.mark.asyncio
    async def test_enhanced_agent_execution_fallback(self, mock_tools, mock_registry, mock_client, sample_agent_task):
        """Test enhanced agent execution with fallback."""
        from agentic_workflow.agents.base import Agent
        
        # Setup mocks to make MCP initialization fail
        mock_client_instance = AsyncMock()
        mock_client_instance.initialize.side_effect = Exception("MCP failed")
        mock_client.return_value = mock_client_instance
        
        EnhancedAgent = create_mcp_enhanced_agent(Agent, mcp_enabled=True)
        agent = EnhancedAgent("test_agent")
        
        # Mock original Agent.execute
        with patch.object(Agent, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AgentResult(
                success=True,
                data={"result": "fallback execution"},
                task_id=sample_agent_task.task_id,
                agent_id=agent.agent_id,
                execution_time=1.0,
                steps_taken=[]
            )
            
            await agent.initialize()
            result = await agent.execute(sample_agent_task)
            
            # Should fall back to original execution when MCP fails
            assert result.success
            assert result.data["result"] == "fallback execution"
            mock_execute.assert_called_once()


@pytest.mark.asyncio
class TestMCPAgentIntegration:
    """Integration tests for MCP-enhanced agents."""
    
    async def test_end_to_end_workflow(self, sample_agent_task, sample_server_config):
        """Test complete end-to-end MCP agent workflow."""
        # This test would require more extensive mocking or actual MCP servers
        # For now, we'll test the basic workflow structure
        
        agent = MCPEnhancedAgent(
            agent_id="integration_test_agent",
            mcp_enabled=True,
            mcp_servers=[sample_server_config],
            auto_discover_servers=False
        )
        
        # Mock all MCP components
        with patch('agentic_workflow.mcp.integration.agents.MCPClient') as mock_client:
            with patch('agentic_workflow.mcp.integration.agents.MCPServerRegistry') as mock_registry:
                with patch('agentic_workflow.mcp.integration.agents.EnhancedToolRegistry') as mock_tools:
                    
                    # Setup mocks
                    mock_client_instance = AsyncMock()
                    mock_client.return_value = mock_client_instance
                    
                    mock_registry_instance = AsyncMock()
                    mock_registry_instance.connect_servers.return_value = {sample_server_config.name: True}
                    mock_registry.return_value = mock_registry_instance
                    
                    mock_tools_instance = AsyncMock()
                    mock_tools_instance.search_tools.return_value = []
                    mock_tools.return_value = mock_tools_instance
                    
                    # Initialize and execute
                    await agent.initialize()
                    result = await agent.execute(sample_agent_task)
                    
                    # Verify workflow
                    assert result.success
                    assert result.task_id == sample_agent_task.task_id
                    assert result.agent_id == agent.agent_id
                    assert result.metadata["mcp_enabled"]
                    
                    # Verify MCP components were used
                    mock_client_instance.initialize.assert_called_once()
                    mock_registry_instance.initialize.assert_called_once()
                    mock_tools_instance.initialize.assert_called_once()
    
    async def test_error_handling_and_recovery(self, sample_agent_task):
        """Test error handling and recovery in MCP operations."""
        agent = MCPEnhancedAgent(
            agent_id="error_test_agent",
            mcp_enabled=True
        )
        
        # Test with various error conditions
        with patch('agentic_workflow.mcp.integration.agents.MCPClient') as mock_client:
            # Simulate intermittent failures
            mock_client_instance = AsyncMock()
            mock_client_instance.initialize.side_effect = [Exception("Network error"), None]
            mock_client.return_value = mock_client_instance
            
            # First initialization should fail and disable MCP
            await agent.initialize()
            assert not agent.mcp_enabled
            
            # Execution should still work without MCP
            result = await agent.execute(sample_agent_task)
            assert result.success


@pytest.mark.asyncio 
class TestMCPEnhancedIntegration:
    """Test MCP integration with new reasoning and communication systems."""
    
    async def test_initialization_with_reasoning_enabled(self):
        """Test agent initialization with reasoning enabled."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=False,  # Focus on reasoning
            reasoning_enabled=True,
            communication_manager=None
        )
        
        assert agent.reasoning_enabled
        assert agent.default_reasoning_pattern == "chain_of_thought"
        # Reasoning engine will be None until ReasoningEngine is available
    
    async def test_initialization_with_communication(self):
        """Test agent initialization with communication manager."""
        mock_comm_manager = Mock()
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=False,  # Focus on communication
            reasoning_enabled=False,
            communication_manager=mock_comm_manager
        )
        
        assert agent.communication_manager is mock_comm_manager
    
    async def test_enhanced_features_integration(self):
        """Test agent with all enhanced features enabled."""
        mock_comm_manager = Mock()
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True,
            reasoning_enabled=True,
            communication_manager=mock_comm_manager,
            default_reasoning_pattern="raise"
        )
        
        assert agent.mcp_enabled
        assert agent.reasoning_enabled
        assert agent.communication_manager is mock_comm_manager
        assert agent.default_reasoning_pattern == "raise"
    
    @patch('agentic_workflow.mcp.integration.agents.ReasoningEngine')
    async def test_reasoning_engine_initialization(self, mock_reasoning_engine):
        """Test reasoning engine initialization."""
        mock_engine_instance = Mock()
        mock_reasoning_engine.return_value = mock_engine_instance
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=False,
            reasoning_enabled=True
        )
        
        await agent.initialize()
        
        assert agent.reasoning_engine is mock_engine_instance
        mock_reasoning_engine.assert_called_once_with(
            agent_id="test_agent",
            memory_manager=agent.memory_manager,
            communication_manager=agent.communication_manager
        )
    
    async def test_enhanced_reasoning_with_mcp_context(self):
        """Test enhanced reasoning with MCP context."""
        from agentic_workflow.agents.base import AgentTask
        
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            mcp_enabled=True,
            reasoning_enabled=False  # Disable for fallback test
        )
        
        # Mock dynamic capabilities
        agent.dynamic_capabilities = ["git_tool", "file_tool", "code_analyzer"]
        
        task = AgentTask(
            task_id="test_task",
            type="analysis",
            description="Analyze code repository"
        )
        
        reasoning_result = await agent._enhanced_reasoning(task)
        
        assert reasoning_result["approach"] == "enhanced_mcp_reasoning"
        assert reasoning_result["capabilities_considered"] == agent.dynamic_capabilities
        assert "reasoning_steps" in reasoning_result
        assert "confidence" in reasoning_result
    
    async def test_reasoning_pattern_selection(self):
        """Test automatic reasoning pattern selection based on task type."""
        agent = MCPEnhancedAgent(
            agent_id="test_agent",
            reasoning_enabled=True
        )
        
        # Mock reasoning engine with AsyncMock for async methods
        mock_engine = Mock()
        mock_reasoning_path = Mock()
        mock_reasoning_path.path_id = "test_path"
        mock_reasoning_path.steps = []
        mock_reasoning_path.final_answer = "Test answer"
        mock_reasoning_path.confidence = 0.85
        mock_reasoning_path.pattern_type = "chain_of_thought"
        
        # All patterns now use reason_async
        mock_engine.reason_async = AsyncMock(return_value=mock_reasoning_path)
        agent.reasoning_engine = mock_engine
        
        # Test different task types
        test_cases = [
            ("coordination", "raise"),
            ("implementation", "react"), 
            ("analysis", "chain_of_thought")
        ]
        
        for task_type, expected_pattern in test_cases:
            objective = f"Test {task_type} task"
            context = {"task_type": task_type}
            
            result = await agent._execute_mcp_aware_reasoning(objective, context)
            
            # Verify reason_async was called (all patterns now use async reasoning)
            mock_engine.reason_async.assert_called()
            
            # Check that the correct pattern was passed
            call_args = mock_engine.reason_async.call_args
            assert call_args[0][1] == expected_pattern  # Second argument is the pattern
    
    async def test_tool_extraction_from_reasoning(self):
        """Test extracting MCP tools from reasoning steps."""
        agent = MCPEnhancedAgent(agent_id="test_agent")
        agent.dynamic_capabilities = ["git_tool", "file_analyzer", "code_reviewer"]
        
        # Mock reasoning path with tool references
        mock_step1 = Mock()
        mock_step1.action = "Use git_tool to check repository status"
        mock_step1.observation = "Repository is clean"
        
        mock_step2 = Mock()
        mock_step2.action = "Execute file_analyzer on source files"
        mock_step2.observation = "Found 50 Python files using file_analyzer"
        
        mock_step3 = Mock()
        mock_step3.action = "No specific tool needed"
        mock_step3.observation = "Analysis complete"
        
        mock_reasoning_path = Mock()
        mock_reasoning_path.steps = [mock_step1, mock_step2, mock_step3]
        
        extracted_tools = agent._extract_tools_from_reasoning(mock_reasoning_path)
        
        assert "git_tool" in extracted_tools
        assert "file_analyzer" in extracted_tools
        assert "code_reviewer" not in extracted_tools  # Not referenced
        assert len(extracted_tools) == 2
    
    async def test_backward_compatibility(self):
        """Test that enhanced features work with backward compatibility."""
        # Test with reasoning disabled
        agent_basic = MCPEnhancedAgent(
            agent_id="basic_agent",
            mcp_enabled=True,
            reasoning_enabled=False
        )
        
        assert agent_basic.mcp_enabled
        assert not agent_basic.reasoning_enabled
        assert agent_basic.reasoning_engine is None
        
        # Test with communication disabled
        agent_no_comm = MCPEnhancedAgent(
            agent_id="no_comm_agent",
            mcp_enabled=True,
            communication_manager=None
        )
        
        assert agent_no_comm.mcp_enabled
        assert agent_no_comm.communication_manager is None
        
        # Both should still work for basic MCP functionality
        from agentic_workflow.agents.base import AgentTask
        
        task = AgentTask(
            task_id="compat_test",
            type="basic",
            description="Basic compatibility test"
        )
        
        # Should not raise exceptions
        result_basic = await agent_basic._enhanced_reasoning(task)
        result_no_comm = await agent_no_comm._enhanced_reasoning(task)
        
        assert result_basic["approach"] == "enhanced_mcp_reasoning"
        assert result_no_comm["approach"] == "enhanced_mcp_reasoning"