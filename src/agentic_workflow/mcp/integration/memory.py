"""
MCP integration with the memory system.

Extends the memory manager to store and retrieve MCP-related information,
including server configurations, capability mappings, execution history,
and performance metrics.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import asdict

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.memory.manager import MemoryManager
from agentic_workflow.mcp.client.base import MCPCapability, MCPServerConfig
from agentic_workflow.mcp.tools.enhanced_registry import ToolMetadata

logger = get_logger(__name__)


class MCPMemoryManager:
    """
    Memory manager for MCP-related data.
    
    Extends the core memory system to handle MCP server configurations,
    capability mappings, execution history, and learning from usage patterns.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        """Initialize MCP memory manager.
        
        Args:
            memory_manager: Core memory manager instance
        """
        self.memory_manager = memory_manager
        self.initialized = False
        
        # Memory collections for MCP data
        self.mcp_collections = {
            'server_configs': 'mcp_server_configs',
            'capabilities': 'mcp_capabilities',
            'execution_history': 'mcp_execution_history',
            'tool_performance': 'mcp_tool_performance',
            'agent_preferences': 'mcp_agent_preferences',
            'server_reliability': 'mcp_server_reliability',
            'capability_mappings': 'mcp_capability_mappings',
            'learning_data': 'mcp_learning_data'
        }
        
        # Cache for frequently accessed data
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        self.cache_timeout = timedelta(minutes=10)
        
    async def initialize(self) -> None:
        """Initialize MCP memory integration."""
        logger.info("Initializing MCP memory manager")
        
        # Create memory collections if they don't exist
        for collection_name in self.mcp_collections.values():
            try:
                await self.memory_manager.create_collection(collection_name)
            except Exception as e:
                # Collection might already exist
                logger.debug(f"Collection {collection_name} already exists or creation failed: {e}")
        
        self.initialized = True
        logger.info("MCP memory manager initialized")
    
    async def store_server_config(self, config: MCPServerConfig, agent_id: str) -> bool:
        """
        Store MCP server configuration.
        
        Args:
            config: Server configuration
            agent_id: Agent that registered the server
            
        Returns:
            True if storage successful
        """
        try:
            memory_data = {
                'config': asdict(config),
                'agent_id': agent_id,
                'registered_at': datetime.now().isoformat(),
                'last_used': None,
                'usage_count': 0,
                'success_rate': 0.0,
                'metadata': {
                    'server_type': 'mcp',
                    'version': '1.0'
                }
            }
            
            await self.memory_manager.store_memory(
                collection=self.mcp_collections['server_configs'],
                data=memory_data,
                memory_id=f"server_{config.name}",
                tags=['mcp', 'server_config', agent_id]
            )
            
            # Invalidate cache
            self._invalidate_cache('server_configs')
            
            logger.debug(f"Stored server config for {config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store server config {config.name}: {e}")
            return False
    
    async def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """
        Retrieve server configuration.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server configuration or None if not found
        """
        try:
            cache_key = f"server_config_{server_name}"
            if self._is_cached(cache_key):
                return self.cache[cache_key]
            
            memory_data = await self.memory_manager.retrieve_memory(
                collection=self.mcp_collections['server_configs'],
                memory_id=f"server_{server_name}"
            )
            
            if memory_data and 'config' in memory_data:
                config = MCPServerConfig(**memory_data['config'])
                self._cache_data(cache_key, config)
                return config
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve server config {server_name}: {e}")
            return None
    
    async def store_capability(self, capability: MCPCapability, agent_id: str) -> bool:
        """
        Store MCP capability information.
        
        Args:
            capability: MCP capability
            agent_id: Agent that discovered the capability
            
        Returns:
            True if storage successful
        """
        try:
            memory_data = {
                'capability': asdict(capability),
                'agent_id': agent_id,
                'discovered_at': datetime.now().isoformat(),
                'last_used': None,
                'usage_count': 0,
                'success_count': 0,
                'failure_count': 0,
                'average_execution_time': 0.0,
                'user_ratings': [],
                'metadata': {
                    'capability_type': capability.type,
                    'server_id': capability.server_id
                }
            }
            
            await self.memory_manager.store_memory(
                collection=self.mcp_collections['capabilities'],
                data=memory_data,
                memory_id=f"capability_{capability.server_id}_{capability.name}",
                tags=['mcp', 'capability', capability.type, capability.server_id, agent_id]
            )
            
            self._invalidate_cache('capabilities')
            
            logger.debug(f"Stored capability {capability.name} from {capability.server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store capability {capability.name}: {e}")
            return False
    
    async def get_capabilities(self, server_id: Optional[str] = None, 
                             capability_type: Optional[str] = None) -> List[MCPCapability]:
        """
        Retrieve capabilities with optional filtering.
        
        Args:
            server_id: Filter by server ID
            capability_type: Filter by capability type
            
        Returns:
            List of matching capabilities
        """
        try:
            cache_key = f"capabilities_{server_id}_{capability_type}"
            if self._is_cached(cache_key):
                return self.cache[cache_key]
            
            # Build search tags
            tags = ['mcp', 'capability']
            if server_id:
                tags.append(server_id)
            if capability_type:
                tags.append(capability_type)
            
            memory_results = await self.memory_manager.search_memories(
                collection=self.mcp_collections['capabilities'],
                tags=tags
            )
            
            capabilities = []
            for memory_data in memory_results:
                if 'capability' in memory_data:
                    capability = MCPCapability(**memory_data['capability'])
                    capabilities.append(capability)
            
            self._cache_data(cache_key, capabilities)
            return capabilities
            
        except Exception as e:
            logger.error(f"Failed to retrieve capabilities: {e}")
            return []
    
    async def record_execution(self, agent_id: str, server_id: str, tool_name: str,
                             parameters: Dict[str, Any], result: Any, success: bool,
                             execution_time: float, error: Optional[str] = None) -> bool:
        """
        Record tool execution for learning and analytics.
        
        Args:
            agent_id: Agent that executed the tool
            server_id: Server hosting the tool
            tool_name: Tool name
            parameters: Execution parameters
            result: Execution result
            success: Whether execution succeeded
            execution_time: Execution time in seconds
            error: Error message if failed
            
        Returns:
            True if recording successful
        """
        try:
            execution_record = {
                'agent_id': agent_id,
                'server_id': server_id,
                'tool_name': tool_name,
                'parameters': parameters,
                'result': result if success else None,
                'success': success,
                'execution_time': execution_time,
                'error': error,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'execution_type': 'mcp_tool',
                    'parameter_count': len(parameters),
                    'result_size': len(str(result)) if result else 0
                }
            }
            
            memory_id = f"execution_{agent_id}_{server_id}_{tool_name}_{datetime.now().timestamp()}"
            
            await self.memory_manager.store_memory(
                collection=self.mcp_collections['execution_history'],
                data=execution_record,
                memory_id=memory_id,
                tags=['mcp', 'execution', agent_id, server_id, tool_name, 'success' if success else 'failure']
            )
            
            # Update performance metrics
            await self._update_performance_metrics(server_id, tool_name, success, execution_time)
            
            # Update capability usage statistics
            await self._update_capability_usage(server_id, tool_name, success)
            
            self._invalidate_cache('execution_history')
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record execution: {e}")
            return False
    
    async def _update_performance_metrics(self, server_id: str, tool_name: str, 
                                        success: bool, execution_time: float) -> None:
        """Update performance metrics for a tool."""
        try:
            metric_id = f"performance_{server_id}_{tool_name}"
            
            # Get existing metrics
            existing_metrics = await self.memory_manager.retrieve_memory(
                collection=self.mcp_collections['tool_performance'],
                memory_id=metric_id
            )
            
            if existing_metrics:
                metrics = existing_metrics
            else:
                metrics = {
                    'server_id': server_id,
                    'tool_name': tool_name,
                    'total_executions': 0,
                    'successful_executions': 0,
                    'total_time': 0.0,
                    'min_time': float('inf'),
                    'max_time': 0.0,
                    'last_execution': None,
                    'created_at': datetime.now().isoformat()
                }
            
            # Update metrics
            metrics['total_executions'] += 1
            if success:
                metrics['successful_executions'] += 1
            
            metrics['total_time'] += execution_time
            metrics['min_time'] = min(metrics['min_time'], execution_time)
            metrics['max_time'] = max(metrics['max_time'], execution_time)
            metrics['last_execution'] = datetime.now().isoformat()
            
            # Calculate derived metrics
            metrics['success_rate'] = metrics['successful_executions'] / metrics['total_executions']
            metrics['average_time'] = metrics['total_time'] / metrics['total_executions']
            
            await self.memory_manager.store_memory(
                collection=self.mcp_collections['tool_performance'],
                data=metrics,
                memory_id=metric_id,
                tags=['mcp', 'performance', server_id, tool_name]
            )
            
        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")
    
    async def _update_capability_usage(self, server_id: str, tool_name: str, success: bool) -> None:
        """Update capability usage statistics."""
        try:
            capability_id = f"capability_{server_id}_{tool_name}"
            
            # Get existing capability data
            capability_data = await self.memory_manager.retrieve_memory(
                collection=self.mcp_collections['capabilities'],
                memory_id=capability_id
            )
            
            if capability_data:
                capability_data['usage_count'] = capability_data.get('usage_count', 0) + 1
                capability_data['last_used'] = datetime.now().isoformat()
                
                if success:
                    capability_data['success_count'] = capability_data.get('success_count', 0) + 1
                else:
                    capability_data['failure_count'] = capability_data.get('failure_count', 0) + 1
                
                await self.memory_manager.store_memory(
                    collection=self.mcp_collections['capabilities'],
                    data=capability_data,
                    memory_id=capability_id,
                    tags=capability_data.get('tags', [])
                )
            
        except Exception as e:
            logger.error(f"Failed to update capability usage: {e}")
    
    async def get_execution_history(self, agent_id: Optional[str] = None,
                                  server_id: Optional[str] = None,
                                  tool_name: Optional[str] = None,
                                  limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get execution history with optional filtering.
        
        Args:
            agent_id: Filter by agent ID
            server_id: Filter by server ID
            tool_name: Filter by tool name
            limit: Maximum number of records
            
        Returns:
            List of execution records
        """
        try:
            # Build search tags
            tags = ['mcp', 'execution']
            if agent_id:
                tags.append(agent_id)
            if server_id:
                tags.append(server_id)
            if tool_name:
                tags.append(tool_name)
            
            memory_results = await self.memory_manager.search_memories(
                collection=self.mcp_collections['execution_history'],
                tags=tags,
                limit=limit
            )
            
            # Sort by timestamp (most recent first)
            memory_results.sort(
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )
            
            return memory_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve execution history: {e}")
            return []
    
    async def get_performance_metrics(self, server_id: Optional[str] = None,
                                    tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get performance metrics with optional filtering.
        
        Args:
            server_id: Filter by server ID
            tool_name: Filter by tool name
            
        Returns:
            List of performance metrics
        """
        try:
            tags = ['mcp', 'performance']
            if server_id:
                tags.append(server_id)
            if tool_name:
                tags.append(tool_name)
            
            metrics = await self.memory_manager.search_memories(
                collection=self.mcp_collections['tool_performance'],
                tags=tags
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to retrieve performance metrics: {e}")
            return []
    
    async def learn_agent_preferences(self, agent_id: str) -> Dict[str, Any]:
        """
        Learn and store agent preferences based on usage patterns.
        
        Args:
            agent_id: Agent ID to analyze
            
        Returns:
            Learned preferences
        """
        try:
            # Get agent's execution history
            history = await self.get_execution_history(agent_id=agent_id, limit=1000)
            
            if not history:
                return {}
            
            # Analyze patterns
            preferences = {
                'preferred_servers': {},
                'preferred_tools': {},
                'preferred_categories': {},
                'usage_patterns': {},
                'success_patterns': {},
                'performance_preferences': {},
                'updated_at': datetime.now().isoformat()
            }
            
            # Count server usage
            server_usage = {}
            tool_usage = {}
            successful_tools = {}
            fast_tools = {}
            
            for record in history:
                server_id = record.get('server_id')
                tool_name = record.get('tool_name')
                success = record.get('success', False)
                exec_time = record.get('execution_time', 0)
                
                if server_id:
                    server_usage[server_id] = server_usage.get(server_id, 0) + 1
                
                if tool_name:
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
                    
                    if success:
                        successful_tools[tool_name] = successful_tools.get(tool_name, 0) + 1
                    
                    if exec_time < 5.0:  # Fast execution (< 5 seconds)
                        fast_tools[tool_name] = fast_tools.get(tool_name, 0) + 1
            
            # Calculate preferences
            total_executions = len(history)
            
            # Server preferences
            for server_id, count in server_usage.items():
                preferences['preferred_servers'][server_id] = {
                    'usage_count': count,
                    'usage_percentage': count / total_executions,
                    'preference_score': count / total_executions
                }
            
            # Tool preferences
            for tool_name, count in tool_usage.items():
                success_count = successful_tools.get(tool_name, 0)
                fast_count = fast_tools.get(tool_name, 0)
                
                preferences['preferred_tools'][tool_name] = {
                    'usage_count': count,
                    'success_count': success_count,
                    'fast_count': fast_count,
                    'success_rate': success_count / count if count > 0 else 0,
                    'speed_rate': fast_count / count if count > 0 else 0,
                    'preference_score': (
                        (count / total_executions) * 0.4 +
                        (success_count / count if count > 0 else 0) * 0.4 +
                        (fast_count / count if count > 0 else 0) * 0.2
                    )
                }
            
            # Store preferences
            await self.memory_manager.store_memory(
                collection=self.mcp_collections['agent_preferences'],
                data=preferences,
                memory_id=f"preferences_{agent_id}",
                tags=['mcp', 'preferences', agent_id]
            )
            
            return preferences
            
        except Exception as e:
            logger.error(f"Failed to learn agent preferences: {e}")
            return {}
    
    async def get_agent_preferences(self, agent_id: str) -> Dict[str, Any]:
        """
        Get stored agent preferences.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent preferences
        """
        try:
            preferences = await self.memory_manager.retrieve_memory(
                collection=self.mcp_collections['agent_preferences'],
                memory_id=f"preferences_{agent_id}"
            )
            
            if not preferences:
                # Learn preferences if not found
                preferences = await self.learn_agent_preferences(agent_id)
            
            return preferences or {}
            
        except Exception as e:
            logger.error(f"Failed to get agent preferences: {e}")
            return {}
    
    async def recommend_tools(self, agent_id: str, task_context: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Recommend tools based on agent preferences and task context.
        
        Args:
            agent_id: Agent ID
            task_context: Context or description of the task
            limit: Maximum number of recommendations
            
        Returns:
            List of tool recommendations
        """
        try:
            # Get agent preferences
            preferences = await self.get_agent_preferences(agent_id)
            
            # Get available capabilities
            capabilities = await self.get_capabilities()
            
            # Score capabilities based on preferences and context
            recommendations = []
            
            for capability in capabilities:
                score = 0.0
                
                # Preference score
                tool_prefs = preferences.get('preferred_tools', {}).get(capability.name, {})
                score += tool_prefs.get('preference_score', 0) * 0.5
                
                # Context relevance (simple keyword matching)
                context_lower = task_context.lower()
                desc_lower = capability.description.lower()
                
                # Count keyword matches
                context_words = set(context_lower.split())
                desc_words = set(desc_lower.split())
                common_words = context_words.intersection(desc_words)
                
                if common_words:
                    score += len(common_words) / len(context_words) * 0.3
                
                # Server reliability
                server_prefs = preferences.get('preferred_servers', {}).get(capability.server_id, {})
                score += server_prefs.get('preference_score', 0) * 0.2
                
                if score > 0:
                    recommendations.append({
                        'capability': asdict(capability),
                        'score': score,
                        'preference_data': tool_prefs,
                        'context_relevance': len(common_words) if common_words else 0
                    })
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Failed to recommend tools: {e}")
            return []
    
    async def store_learning_data(self, data_type: str, data: Dict[str, Any], 
                                agent_id: Optional[str] = None) -> bool:
        """
        Store learning data for improving MCP integration.
        
        Args:
            data_type: Type of learning data
            data: Learning data
            agent_id: Associated agent ID
            
        Returns:
            True if storage successful
        """
        try:
            learning_record = {
                'data_type': data_type,
                'data': data,
                'agent_id': agent_id,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'learning_type': 'mcp_integration',
                    'data_size': len(str(data))
                }
            }
            
            memory_id = f"learning_{data_type}_{datetime.now().timestamp()}"
            tags = ['mcp', 'learning', data_type]
            if agent_id:
                tags.append(agent_id)
            
            await self.memory_manager.store_memory(
                collection=self.mcp_collections['learning_data'],
                data=learning_record,
                memory_id=memory_id,
                tags=tags
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store learning data: {e}")
            return False
    
    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and not expired."""
        if key not in self.cache:
            return False
        
        if key in self.cache_ttl:
            if datetime.now() > self.cache_ttl[key]:
                del self.cache[key]
                del self.cache_ttl[key]
                return False
        
        return True
    
    def _cache_data(self, key: str, data: Any) -> None:
        """Cache data with expiration."""
        self.cache[key] = data
        self.cache_ttl[key] = datetime.now() + self.cache_timeout
    
    def _invalidate_cache(self, cache_pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        keys_to_remove = [key for key in self.cache.keys() if cache_pattern in key]
        for key in keys_to_remove:
            del self.cache[key]
            self.cache_ttl.pop(key, None)
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """Get MCP memory usage statistics."""
        try:
            stats = {}
            
            for collection_type, collection_name in self.mcp_collections.items():
                # Get collection size (this is a simplified approach)
                try:
                    memories = await self.memory_manager.search_memories(
                        collection=collection_name,
                        tags=['mcp']
                    )
                    stats[collection_type] = {
                        'count': len(memories),
                        'collection_name': collection_name
                    }
                except Exception:
                    stats[collection_type] = {
                        'count': 0,
                        'collection_name': collection_name
                    }
            
            stats['cache_size'] = len(self.cache)
            stats['cache_entries'] = list(self.cache.keys())
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get memory statistics: {e}")
            return {}
    
    async def cleanup_old_data(self, retention_days: int = 30) -> bool:
        """
        Clean up old MCP data based on retention policy.
        
        Args:
            retention_days: Number of days to retain data
            
        Returns:
            True if cleanup successful
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cutoff_str = cutoff_date.isoformat()
            
            # Collections to clean up
            cleanup_collections = [
                'execution_history',
                'learning_data'
            ]
            
            for collection_type in cleanup_collections:
                collection_name = self.mcp_collections[collection_type]
                
                # Get old memories (this is a simplified approach)
                memories = await self.memory_manager.search_memories(
                    collection=collection_name,
                    tags=['mcp']
                )
                
                deleted_count = 0
                for memory in memories:
                    memory_date = memory.get('timestamp', memory.get('created_at', ''))
                    if memory_date and memory_date < cutoff_str:
                        try:
                            memory_id = memory.get('memory_id')
                            if memory_id:
                                await self.memory_manager.delete_memory(
                                    collection=collection_name,
                                    memory_id=memory_id
                                )
                                deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to delete old memory {memory_id}: {e}")
                
                logger.info(f"Cleaned up {deleted_count} old records from {collection_type}")
            
            # Clear cache
            self.cache.clear()
            self.cache_ttl.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False