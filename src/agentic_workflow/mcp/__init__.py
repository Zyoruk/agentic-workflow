"""
Model Context Protocol (MCP) integration for agentic workflow system.

This module provides MCP client capabilities, server connections, and
dynamic tool discovery for enhanced agent capabilities.
"""

from .client.base import MCPCapability, MCPClient, MCPServerConfig
from .client.registry import MCPServerRegistry
from .integration.agents import MCPEnhancedAgent
from .tools.enhanced_registry import EnhancedToolRegistry

__all__ = [
    "MCPClient",
    "MCPServerConfig",
    "MCPCapability",
    "MCPServerRegistry",
    "EnhancedToolRegistry",
    "MCPEnhancedAgent",
]
