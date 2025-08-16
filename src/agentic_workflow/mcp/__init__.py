"""
Model Context Protocol (MCP) integration for agentic workflow system.

This module provides MCP client capabilities, server connections, and
dynamic tool discovery for enhanced agent capabilities.
"""

from .client.base import MCPClient, MCPServerConfig, MCPCapability
from .client.registry import MCPServerRegistry
from .tools.enhanced_registry import EnhancedToolRegistry
from .integration.agents import MCPEnhancedAgent

__all__ = [
    "MCPClient",
    "MCPServerConfig", 
    "MCPCapability",
    "MCPServerRegistry",
    "EnhancedToolRegistry",
    "MCPEnhancedAgent",
]