"""Health check implementations for system components."""

import asyncio
from typing import Dict, Any
from datetime import datetime, UTC

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.core.config import get_config


logger = get_logger(__name__)


async def memory_health_check() -> Dict[str, Any]:
    """Check memory system health."""
    try:
        from agentic_workflow.memory.manager import MemoryManager
        
        # Test basic memory operations
        memory_manager = MemoryManager()
        
        # Check if initialization works
        await memory_manager.initialize()
        
        # Test a simple store/retrieve operation
        test_key = f"health_check_{datetime.now(UTC).timestamp()}"
        store_result = await memory_manager.store(
            content="health check test",
            memory_type="SHORT_TERM",
            metadata={"test": True}
        )
        
        if store_result.success:
            # Test retrieval
            retrieve_result = await memory_manager.retrieve(
                query="health check test",
                memory_type="SHORT_TERM",
                limit=1
            )
            
            healthy = retrieve_result.success and len(retrieve_result.results) > 0
            message = "Memory system operational" if healthy else "Memory retrieval failed"
        else:
            healthy = False
            message = "Memory storage failed"
        
        return {
            'healthy': healthy,
            'message': message,
            'details': {
                'store_success': store_result.success,
                'timestamp': datetime.now(UTC).isoformat()
            }
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'message': f"Memory health check failed: {str(e)}",
            'details': {'error': str(e)}
        }


async def agent_registry_health_check() -> Dict[str, Any]:
    """Check agent registry health."""
    try:
        from agentic_workflow.agents import get_available_agent_types, create_agent
        
        # Check if agent types are available
        agent_types = get_available_agent_types()
        
        if not agent_types:
            return {
                'healthy': False,
                'message': "No agent types available",
                'details': {'agent_count': 0}
            }
        
        # Test creating a simple agent
        try:
            test_agent = create_agent('planning', agent_id='health_check_agent')
            agent_created = test_agent is not None
        except Exception as e:
            agent_created = False
            logger.warning(f"Agent creation test failed: {e}")
        
        healthy = len(agent_types) > 0 and agent_created
        message = f"Agent registry operational with {len(agent_types)} types" if healthy else "Agent registry issues detected"
        
        return {
            'healthy': healthy,
            'message': message,
            'details': {
                'available_types': len(agent_types),
                'agent_creation': agent_created,
                'types': agent_types[:5]  # First 5 types
            }
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'message': f"Agent registry health check failed: {str(e)}",
            'details': {'error': str(e)}
        }


async def reasoning_engine_health_check() -> Dict[str, Any]:
    """Check reasoning engine health."""
    try:
        from agentic_workflow.core.reasoning import ReasoningEngine
        
        # Create reasoning engine
        reasoning_engine = ReasoningEngine(agent_id="health_check")
        
        # Test basic reasoning capability
        test_objective = "Simple test objective for health check"
        
        # Use basic reasoning pattern
        try:
            reasoning_result = await reasoning_engine.reason_async(
                objective=test_objective,
                pattern="chain_of_thought",
                context={"task_id": "health_check"}
            )
            
            reasoning_works = (reasoning_result.completed and 
                             reasoning_result.confidence > 0 and
                             len(reasoning_result.steps) > 0)
        except Exception as e:
            reasoning_works = False
            logger.warning(f"Reasoning test failed: {e}")
        
        healthy = reasoning_works
        message = "Reasoning engine operational" if healthy else "Reasoning engine issues detected"
        
        return {
            'healthy': healthy,
            'message': message,
            'details': {
                'reasoning_test': reasoning_works,
                'timestamp': datetime.now(UTC).isoformat()
            }
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'message': f"Reasoning engine health check failed: {str(e)}",
            'details': {'error': str(e)}
        }


async def communication_health_check() -> Dict[str, Any]:
    """Check communication system health."""
    try:
        from agentic_workflow.core.communication import CommunicationManager
        
        # Create communication manager
        comm_manager = CommunicationManager()
        
        # Test basic communication setup
        test_agent_id = "health_check_agent"
        
        try:
            # Test subscription
            await comm_manager.subscribe_to_channel(test_agent_id, "test")
            
            # Test message sending
            test_message = {
                "content": {"test": "health check"},
                "message_type": "test",
                "sender_id": test_agent_id
            }
            
            await comm_manager.send_message(test_message, "test")
            
            # Test message receiving
            messages = await comm_manager.receive_messages(test_agent_id)
            
            comm_works = True  # If we got here without exceptions
        except Exception as e:
            comm_works = False
            logger.warning(f"Communication test failed: {e}")
        
        healthy = comm_works
        message = "Communication system operational" if healthy else "Communication system issues detected"
        
        return {
            'healthy': healthy,
            'message': message,
            'details': {
                'communication_test': comm_works,
                'timestamp': datetime.now(UTC).isoformat()
            }
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'message': f"Communication health check failed: {str(e)}",
            'details': {'error': str(e)}
        }


async def tool_system_health_check() -> Dict[str, Any]:
    """Check tool system health."""
    try:
        from agentic_workflow.tools import ToolManager
        
        # Create tool manager
        tool_manager = ToolManager()
        await tool_manager.initialize()
        
        # Check available tools
        available_tools = tool_manager.registry.list_tools()
        
        # Test tool discovery
        try:
            # Test search functionality
            search_results = tool_manager.registry.search_tools("test")
            search_works = isinstance(search_results, list)
        except Exception as e:
            search_works = False
            logger.warning(f"Tool search test failed: {e}")
        
        healthy = search_works  # Basic check that tool system is functional
        message = f"Tool system operational with {len(available_tools)} tools" if healthy else "Tool system issues detected"
        
        return {
            'healthy': healthy,
            'message': message,
            'details': {
                'available_tools': len(available_tools),
                'search_functional': search_works,
                'timestamp': datetime.now(UTC).isoformat()
            }
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'message': f"Tool system health check failed: {str(e)}",
            'details': {'error': str(e)}
        }


async def configuration_health_check() -> Dict[str, Any]:
    """Check configuration system health."""
    try:
        from agentic_workflow.core.config import get_config
        
        # Test configuration loading
        config = get_config()
        
        # Check essential configuration values
        has_app_name = hasattr(config, 'app_name') and config.app_name
        has_version = hasattr(config, 'app_version') and config.app_version
        has_database = hasattr(config, 'database')
        has_logging = hasattr(config, 'logging')
        
        essential_checks = [has_app_name, has_version, has_database, has_logging]
        healthy = all(essential_checks)
        
        message = "Configuration system operational" if healthy else "Configuration issues detected"
        
        return {
            'healthy': healthy,
            'message': message,
            'details': {
                'app_name': has_app_name,
                'version': has_version,
                'database_config': has_database,
                'logging_config': has_logging,
                'timestamp': datetime.now(UTC).isoformat()
            }
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'message': f"Configuration health check failed: {str(e)}",
            'details': {'error': str(e)}
        }


# Health check registry
HEALTH_CHECKS = {
    'memory': memory_health_check,
    'agents': agent_registry_health_check,
    'reasoning': reasoning_engine_health_check,
    'communication': communication_health_check,
    'tools': tool_system_health_check,
    'configuration': configuration_health_check,
}


async def run_all_health_checks() -> Dict[str, Any]:
    """Run all registered health checks."""
    results = {}
    overall_healthy = True
    
    for name, check_func in HEALTH_CHECKS.items():
        try:
            result = await check_func()
            results[name] = result
            if not result.get('healthy', False):
                overall_healthy = False
        except Exception as e:
            results[name] = {
                'healthy': False,
                'message': f"Health check exception: {str(e)}",
                'details': {'error': str(e)}
            }
            overall_healthy = False
    
    return {
        'overall_healthy': overall_healthy,
        'checks': results,
        'timestamp': datetime.now(UTC).isoformat(),
        'summary': {
            'total_checks': len(HEALTH_CHECKS),
            'healthy_checks': sum(1 for r in results.values() if r.get('healthy', False)),
            'unhealthy_checks': sum(1 for r in results.values() if not r.get('healthy', False))
        }
    }