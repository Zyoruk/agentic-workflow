"""
Plugin architecture for custom MCP servers.

Provides a framework for users to easily add custom MCP servers
without modifying the core codebase.
"""

import asyncio
import importlib
import importlib.util
import inspect
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.mcp.client.base import MCPCapability, MCPServerConfig

logger = get_logger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for MCP server plugins."""

    name: str
    version: str
    description: str
    author: str
    category: str
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    min_python_version: str = "3.8"
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PluginConfig:
    """Configuration for a plugin instance."""

    plugin_name: str
    instance_name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    server_config: Optional[MCPServerConfig] = None


class MCPServerPlugin(ABC):
    """
    Abstract base class for MCP server plugins.

    All custom MCP server plugins must inherit from this class
    and implement the required methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the plugin.

        Args:
            config: Plugin configuration dictionary
        """
        self.config = config
        self.metadata: Optional[PluginMetadata] = None
        self._initialized = False

    @abstractmethod
    async def get_metadata(self) -> PluginMetadata:
        """
        Get plugin metadata.

        Returns:
            Plugin metadata
        """
        pass

    @abstractmethod
    async def create_server_config(self) -> MCPServerConfig:
        """
        Create MCP server configuration.

        Returns:
            MCP server configuration
        """
        pass

    @abstractmethod
    async def get_capabilities(self) -> List[MCPCapability]:
        """
        Get plugin capabilities.

        Returns:
            List of capabilities provided by this plugin
        """
        pass

    async def initialize(self) -> bool:
        """
        Initialize the plugin.

        Returns:
            True if initialization successful
        """
        try:
            self.metadata = await self.get_metadata()
            self._initialized = True
            logger.info(f"Initialized plugin: {self.metadata.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize plugin: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        self._initialized = False
        logger.info(
            f"Cleaned up plugin: {self.metadata.name if self.metadata else 'unknown'}"
        )

    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized

    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid
        """
        if not self.metadata or not self.metadata.config_schema:
            return True

        # Basic validation against schema (implement JSON schema validation here)
        return True

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health status information
        """
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "plugin": self.metadata.name if self.metadata else "unknown",
            "initialized": self._initialized,
            "timestamp": datetime.now().isoformat(),
        }


class PluginManager:
    """
    Manager for MCP server plugins.

    Handles plugin discovery, loading, configuration, and lifecycle management.
    """

    def __init__(
        self, plugins_dir: Optional[Path] = None, config_dir: Optional[Path] = None
    ):
        """
        Initialize plugin manager.

        Args:
            plugins_dir: Directory containing plugin files
            config_dir: Directory for plugin configurations
        """
        self.plugins_dir = plugins_dir or Path.home() / ".agentic_workflow" / "plugins"
        self.config_dir = config_dir or Path.home() / ".agentic_workflow" / "config"

        # Create directories if they don't exist
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Plugin registry
        self.available_plugins: Dict[str, Type[MCPServerPlugin]] = {}
        self.loaded_plugins: Dict[str, MCPServerPlugin] = {}
        self.plugin_configs: Dict[str, PluginConfig] = {}

        # Configuration files
        self._plugins_config_file = self.config_dir / "plugins.yaml"
        self._plugin_registry_file = self.config_dir / "plugin_registry.json"

    async def initialize(self) -> None:
        """Initialize plugin manager."""
        logger.info("Initializing plugin manager")

        # Load plugin configurations
        await self._load_plugin_configs()

        # Discover available plugins
        await self._discover_plugins()

        # Load enabled plugins
        await self._load_enabled_plugins()

        logger.info(
            f"Plugin manager initialized with {len(self.loaded_plugins)} plugins loaded"
        )

    async def _discover_plugins(self) -> None:
        """Discover available plugins in the plugins directory."""
        logger.info(f"Discovering plugins in {self.plugins_dir}")

        # Scan for Python files
        for plugin_file in self.plugins_dir.glob("*.py"):
            try:
                await self._load_plugin_file(plugin_file)
            except Exception as e:
                logger.error(f"Failed to load plugin file {plugin_file}: {e}")

        # Scan for plugin packages
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
                try:
                    await self._load_plugin_package(plugin_dir)
                except Exception as e:
                    logger.error(f"Failed to load plugin package {plugin_dir}: {e}")

        logger.info(f"Discovered {len(self.available_plugins)} plugins")

    async def _load_plugin_file(self, plugin_file: Path) -> None:
        """Load a plugin from a Python file."""
        module_name = f"mcp_plugin_{plugin_file.stem}"

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load spec for {plugin_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Find plugin classes
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, MCPServerPlugin)
                and obj is not MCPServerPlugin
                and not inspect.isabstract(obj)
            ):

                plugin_name = getattr(obj, "PLUGIN_NAME", name.lower())
                self.available_plugins[plugin_name] = obj
                logger.info(f"Discovered plugin: {plugin_name} from {plugin_file}")

    async def _load_plugin_package(self, plugin_dir: Path) -> None:
        """Load a plugin from a Python package."""
        # Add to Python path temporarily
        if str(plugin_dir.parent) not in sys.path:
            sys.path.insert(0, str(plugin_dir.parent))

        try:
            # Import the package
            module = importlib.import_module(plugin_dir.name)

            # Look for plugin classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, MCPServerPlugin)
                    and obj is not MCPServerPlugin
                    and not inspect.isabstract(obj)
                ):

                    plugin_name = getattr(obj, "PLUGIN_NAME", name.lower())
                    self.available_plugins[plugin_name] = obj
                    logger.info(f"Discovered plugin: {plugin_name} from {plugin_dir}")

        finally:
            # Remove from Python path
            if str(plugin_dir.parent) in sys.path:
                sys.path.remove(str(plugin_dir.parent))

    async def _load_plugin_configs(self) -> None:
        """Load plugin configurations from file."""
        try:
            if self._plugins_config_file.exists():
                with open(self._plugins_config_file, "r") as f:
                    data = yaml.safe_load(f)

                for config_data in data.get("plugins", []):
                    config = PluginConfig(**config_data)
                    self.plugin_configs[config.instance_name] = config

                logger.info(f"Loaded {len(self.plugin_configs)} plugin configurations")
        except Exception as e:
            logger.error(f"Failed to load plugin configurations: {e}")

    async def _save_plugin_configs(self) -> None:
        """Save plugin configurations to file."""
        try:
            data = {
                "plugins": [
                    {
                        "plugin_name": config.plugin_name,
                        "instance_name": config.instance_name,
                        "enabled": config.enabled,
                        "config": config.config,
                        "server_config": (
                            config.server_config.__dict__
                            if config.server_config
                            else None
                        ),
                    }
                    for config in self.plugin_configs.values()
                ]
            }

            with open(self._plugins_config_file, "w") as f:
                yaml.dump(data, f, default_flow_style=False)

            logger.info(f"Saved {len(self.plugin_configs)} plugin configurations")
        except Exception as e:
            logger.error(f"Failed to save plugin configurations: {e}")

    async def _load_enabled_plugins(self) -> None:
        """Load all enabled plugins."""
        for instance_name, config in self.plugin_configs.items():
            if config.enabled:
                try:
                    await self._load_plugin_instance(config)
                except Exception as e:
                    logger.error(f"Failed to load plugin instance {instance_name}: {e}")

    async def _load_plugin_instance(self, config: PluginConfig) -> None:
        """Load a specific plugin instance."""
        if config.plugin_name not in self.available_plugins:
            raise ValueError(f"Plugin {config.plugin_name} not available")

        plugin_class = self.available_plugins[config.plugin_name]
        plugin_instance = plugin_class(config.config)

        # Initialize the plugin
        if await plugin_instance.initialize():
            self.loaded_plugins[config.instance_name] = plugin_instance
            logger.info(f"Loaded plugin instance: {config.instance_name}")
        else:
            raise RuntimeError(
                f"Failed to initialize plugin instance {config.instance_name}"
            )

    async def install_plugin(
        self,
        plugin_name: str,
        instance_name: str,
        config: Dict[str, Any],
        enabled: bool = True,
    ) -> bool:
        """
        Install and configure a plugin.

        Args:
            plugin_name: Name of the plugin to install
            instance_name: Unique name for this plugin instance
            config: Plugin configuration
            enabled: Whether to enable the plugin immediately

        Returns:
            True if installation successful
        """
        try:
            if plugin_name not in self.available_plugins:
                raise ValueError(f"Plugin {plugin_name} not available")

            if instance_name in self.plugin_configs:
                raise ValueError(f"Plugin instance {instance_name} already exists")

            # Create plugin configuration
            plugin_config = PluginConfig(
                plugin_name=plugin_name,
                instance_name=instance_name,
                enabled=enabled,
                config=config,
            )

            # Validate configuration
            plugin_class = self.available_plugins[plugin_name]
            temp_plugin = plugin_class(config)

            if not await temp_plugin.validate_config(config):
                raise ValueError("Invalid plugin configuration")

            # Create server configuration
            await temp_plugin.initialize()
            server_config = await temp_plugin.create_server_config()
            plugin_config.server_config = server_config

            # Store configuration
            self.plugin_configs[instance_name] = plugin_config
            await self._save_plugin_configs()

            # Load plugin if enabled
            if enabled:
                await self._load_plugin_instance(plugin_config)

            logger.info(f"Installed plugin: {instance_name} ({plugin_name})")
            return True

        except Exception as e:
            logger.error(f"Failed to install plugin {plugin_name}: {e}")
            return False

    async def uninstall_plugin(self, instance_name: str) -> bool:
        """
        Uninstall a plugin instance.

        Args:
            instance_name: Name of the plugin instance to uninstall

        Returns:
            True if uninstallation successful
        """
        try:
            # Unload plugin if loaded
            if instance_name in self.loaded_plugins:
                plugin = self.loaded_plugins[instance_name]
                await plugin.cleanup()
                del self.loaded_plugins[instance_name]

            # Remove configuration
            if instance_name in self.plugin_configs:
                del self.plugin_configs[instance_name]
                await self._save_plugin_configs()

            logger.info(f"Uninstalled plugin: {instance_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to uninstall plugin {instance_name}: {e}")
            return False

    async def enable_plugin(self, instance_name: str) -> bool:
        """Enable a plugin instance."""
        try:
            if instance_name not in self.plugin_configs:
                raise ValueError(f"Plugin instance {instance_name} not found")

            config = self.plugin_configs[instance_name]

            if not config.enabled:
                config.enabled = True
                await self._save_plugin_configs()

                # Load the plugin
                await self._load_plugin_instance(config)

            logger.info(f"Enabled plugin: {instance_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable plugin {instance_name}: {e}")
            return False

    async def disable_plugin(self, instance_name: str) -> bool:
        """Disable a plugin instance."""
        try:
            if instance_name in self.loaded_plugins:
                plugin = self.loaded_plugins[instance_name]
                await plugin.cleanup()
                del self.loaded_plugins[instance_name]

            if instance_name in self.plugin_configs:
                self.plugin_configs[instance_name].enabled = False
                await self._save_plugin_configs()

            logger.info(f"Disabled plugin: {instance_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable plugin {instance_name}: {e}")
            return False

    async def reload_plugin(self, instance_name: str) -> bool:
        """Reload a plugin instance."""
        try:
            # Disable and re-enable
            await self.disable_plugin(instance_name)
            await asyncio.sleep(0.1)  # Small delay
            return await self.enable_plugin(instance_name)

        except Exception as e:
            logger.error(f"Failed to reload plugin {instance_name}: {e}")
            return False

    def get_available_plugins(self) -> Dict[str, Type[MCPServerPlugin]]:
        """Get all available plugins."""
        return self.available_plugins.copy()

    def get_loaded_plugins(self) -> Dict[str, MCPServerPlugin]:
        """Get all loaded plugins."""
        return self.loaded_plugins.copy()

    def get_plugin_configs(self) -> Dict[str, PluginConfig]:
        """Get all plugin configurations."""
        return self.plugin_configs.copy()

    async def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a plugin."""
        if plugin_name not in self.available_plugins:
            return None

        plugin_class = self.available_plugins[plugin_name]
        temp_plugin = plugin_class({})

        try:
            return await temp_plugin.get_metadata()
        except Exception as e:
            logger.error(f"Failed to get metadata for plugin {plugin_name}: {e}")
            return None

    async def get_plugin_capabilities(self, instance_name: str) -> List[MCPCapability]:
        """Get capabilities for a plugin instance."""
        if instance_name not in self.loaded_plugins:
            return []

        plugin = self.loaded_plugins[instance_name]

        try:
            return await plugin.get_capabilities()
        except Exception as e:
            logger.error(f"Failed to get capabilities for plugin {instance_name}: {e}")
            return []

    async def get_plugin_health(self, instance_name: str) -> Dict[str, Any]:
        """Get health status for a plugin instance."""
        if instance_name not in self.loaded_plugins:
            return {"status": "not_loaded", "instance": instance_name}

        plugin = self.loaded_plugins[instance_name]

        try:
            return await plugin.health_check()
        except Exception as e:
            logger.error(f"Failed to get health for plugin {instance_name}: {e}")
            return {"status": "error", "instance": instance_name, "error": str(e)}

    async def get_all_server_configs(self) -> List[MCPServerConfig]:
        """Get MCP server configurations for all loaded plugins."""
        configs = []

        for instance_name, plugin in self.loaded_plugins.items():
            try:
                config = await plugin.create_server_config()
                configs.append(config)
            except Exception as e:
                logger.error(
                    f"Failed to get server config for plugin {instance_name}: {e}"
                )

        return configs

    async def export_plugin_registry(self) -> Dict[str, Any]:
        """Export plugin registry for sharing."""
        registry = {
            "available_plugins": {},
            "loaded_plugins": {},
            "export_timestamp": datetime.now().isoformat(),
        }

        # Export available plugins with metadata
        for plugin_name, plugin_class in self.available_plugins.items():
            try:
                temp_plugin = plugin_class({})
                metadata = await temp_plugin.get_metadata()
                registry["available_plugins"][plugin_name] = {
                    "name": metadata.name,
                    "version": metadata.version,
                    "description": metadata.description,
                    "author": metadata.author,
                    "category": metadata.category,
                    "tags": metadata.tags,
                    "dependencies": metadata.dependencies,
                    "min_python_version": metadata.min_python_version,
                    "homepage": metadata.homepage,
                    "repository": metadata.repository,
                    "license": metadata.license,
                }
            except Exception as e:
                logger.error(f"Failed to export metadata for plugin {plugin_name}: {e}")

        # Export loaded plugins
        for instance_name, config in self.plugin_configs.items():
            if config.enabled and instance_name in self.loaded_plugins:
                registry["loaded_plugins"][instance_name] = {
                    "plugin_name": config.plugin_name,
                    "instance_name": config.instance_name,
                    "enabled": config.enabled,
                    "config_keys": list(
                        config.config.keys()
                    ),  # Don't export sensitive config
                    "server_name": (
                        config.server_config.name if config.server_config else None
                    ),
                }

        return registry

    async def cleanup(self) -> None:
        """Clean up all loaded plugins."""
        logger.info("Cleaning up plugin manager")

        for instance_name, plugin in self.loaded_plugins.items():
            try:
                await plugin.cleanup()
            except Exception as e:
                logger.error(f"Failed to cleanup plugin {instance_name}: {e}")

        self.loaded_plugins.clear()
        logger.info("Plugin manager cleanup completed")


# Example plugin implementation
class ExampleCustomMCPServer(MCPServerPlugin):
    """Example custom MCP server plugin."""

    PLUGIN_NAME = "example_custom_server"

    async def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="Example Custom MCP Server",
            version="1.0.0",
            description="An example custom MCP server plugin",
            author="Agentic Workflow Team",
            category="example",
            dependencies=["requests"],
            tags=["example", "demo", "custom"],
            homepage="https://github.com/Zyoruk/agentic-workflow",
            license="MIT",
        )

    async def create_server_config(self) -> MCPServerConfig:
        """Create MCP server configuration."""
        return MCPServerConfig(
            name="example_custom_server",
            command=["python", "-m", "example_custom_server"],
            args=[],
            description="Example custom MCP server",
            timeout=30,
            metadata={"plugin": "example_custom_server"},
        )

    async def get_capabilities(self) -> List[MCPCapability]:
        """Get plugin capabilities."""
        return [
            MCPCapability(
                name="hello_world",
                type="tool",
                description="A simple hello world tool",
                server_id="example_custom_server",
                parameters={"name": {"type": "string", "description": "Name to greet"}},
            ),
            MCPCapability(
                name="example_data",
                type="resource",
                description="Example data resource",
                server_id="example_custom_server",
            ),
        ]


# Plugin discovery helper functions
def create_plugin_template(plugin_name: str, output_dir: Path) -> bool:
    """
    Create a template plugin file.

    Args:
        plugin_name: Name of the plugin
        output_dir: Directory to create the plugin in

    Returns:
        True if template created successfully
    """
    template = f'''"""
Custom MCP Server Plugin: {plugin_name}

This is a template for creating custom MCP server plugins.
"""

from typing import Dict, List, Any
from datetime import datetime

from agentic_workflow.mcp.integration.plugin_manager import MCPServerPlugin, PluginMetadata
from agentic_workflow.mcp.client.base import MCPServerConfig, MCPCapability


class {plugin_name.title().replace('_', '')}Plugin(MCPServerPlugin):
    """Custom MCP server plugin: {plugin_name}"""

    PLUGIN_NAME = "{plugin_name}"

    async def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="{plugin_name.title().replace('_', ' ')}",
            version="1.0.0",
            description="Custom MCP server plugin for {plugin_name}",
            author="Your Name",
            category="custom",
            dependencies=[],
            tags=["custom", "{plugin_name}"],
            homepage="",
            license="MIT"
        )

    async def create_server_config(self) -> MCPServerConfig:
        """Create MCP server configuration."""
        return MCPServerConfig(
            name="{plugin_name}",
            command=["python", "-m", "{plugin_name}_server"],
            args=[],
            description="Custom {plugin_name} MCP server",
            timeout=30,
            metadata={{"plugin": "{plugin_name}"}}
        )

    async def get_capabilities(self) -> List[MCPCapability]:
        """Get plugin capabilities."""
        # Define your plugin's capabilities here
        return [
            MCPCapability(
                name="example_tool",
                type="tool",
                description="Example tool provided by {plugin_name}",
                server_id="{plugin_name}",
                parameters={{"param": {{"type": "string", "description": "Example parameter"}}}}
            )
        ]
'''

    try:
        output_file = output_dir / f"{plugin_name}_plugin.py"
        with open(output_file, "w") as f:
            f.write(template)

        logger.info(f"Created plugin template: {output_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to create plugin template: {e}")
        return False
