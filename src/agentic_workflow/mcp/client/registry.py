"""
MCP Server Registry for managing server configurations and discovery.
"""

import asyncio
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from agentic_workflow.core.logging_config import get_logger

from .base import MCPClient, MCPServerConfig

logger = get_logger(__name__)


@dataclass
class ServerCategory:
    """Represents a category of MCP servers."""

    name: str
    description: str
    servers: List[str]
    priority: int = 1  # 1=high, 2=medium, 3=low


class MCPServerRegistry:
    """
    Registry for managing MCP server configurations and discovery.

    Provides centralized management of server configurations,
    automatic discovery, and categorization of available servers.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize server registry.

        Args:
            config_dir: Directory for server configurations
        """
        self.config_dir = config_dir or Path.home() / ".agentic_workflow" / "mcp"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.categories: Dict[str, ServerCategory] = {}
        self.client: Optional[MCPClient] = None
        self.auto_discovery_enabled = True
        self._config_file = self.config_dir / "servers.yaml"
        self._categories_file = self.config_dir / "categories.yaml"

    async def initialize(self, client: MCPClient) -> None:
        """Initialize registry with MCP client."""
        self.client = client
        await self.load_configurations()
        await self.setup_default_categories()

        if self.auto_discovery_enabled:
            await self.discover_available_servers()

    async def load_configurations(self) -> None:
        """Load server configurations from file."""
        try:
            if self._config_file.exists():
                with open(self._config_file, "r") as f:
                    data = yaml.safe_load(f)

                for server_data in data.get("servers", []):
                    config = MCPServerConfig(**server_data)
                    self.server_configs[config.name] = config

                logger.info(f"Loaded {len(self.server_configs)} server configurations")
        except Exception as e:
            logger.error(f"Failed to load server configurations: {e}")

    async def save_configurations(self) -> None:
        """Save server configurations to file."""
        try:
            data = {
                "servers": [asdict(config) for config in self.server_configs.values()]
            }

            with open(self._config_file, "w") as f:
                yaml.dump(data, f, default_flow_style=False)

            logger.info(f"Saved {len(self.server_configs)} server configurations")
        except Exception as e:
            logger.error(f"Failed to save server configurations: {e}")

    async def setup_default_categories(self) -> None:
        """Setup default server categories."""
        default_categories = {
            "development": ServerCategory(
                name="development",
                description="Development tools and IDE integrations",
                servers=[
                    "github",
                    "git",
                    "vscode",
                    "jetbrains",
                    "code-analysis",
                    "build-tools",
                    "package-managers",
                    "debuggers",
                ],
                priority=1,
            ),
            "data": ServerCategory(
                name="data",
                description="Data sources and management",
                servers=[
                    "postgresql",
                    "mongodb",
                    "redis",
                    "sqlite",
                    "mysql",
                    "elasticsearch",
                    "file-system",
                    "cloud-storage",
                ],
                priority=1,
            ),
            "devops": ServerCategory(
                name="devops",
                description="DevOps and infrastructure tools",
                servers=[
                    "docker",
                    "kubernetes",
                    "jenkins",
                    "github-actions",
                    "aws",
                    "azure",
                    "gcp",
                    "terraform",
                    "ansible",
                ],
                priority=2,
            ),
            "communication": ServerCategory(
                name="communication",
                description="Communication and collaboration tools",
                servers=[
                    "slack",
                    "teams",
                    "discord",
                    "email",
                    "jira",
                    "trello",
                    "notion",
                    "confluence",
                ],
                priority=2,
            ),
            "security": ServerCategory(
                name="security",
                description="Security and compliance tools",
                servers=[
                    "security-scanner",
                    "secret-manager",
                    "vulnerability-scanner",
                    "compliance-checker",
                    "audit-tools",
                ],
                priority=3,
            ),
            "monitoring": ServerCategory(
                name="monitoring",
                description="Monitoring and observability",
                servers=[
                    "prometheus",
                    "grafana",
                    "datadog",
                    "new-relic",
                    "elk-stack",
                    "metrics-collector",
                ],
                priority=3,
            ),
            "custom": ServerCategory(
                name="custom",
                description="Custom agentic workflow servers",
                servers=[
                    "workflow-manager",
                    "code-intelligence",
                    "dev-environment",
                    "agent-communication",
                    "knowledge-manager",
                    "project-intelligence",
                ],
                priority=1,
            ),
        }

        self.categories.update(default_categories)
        await self.save_categories()

    async def save_categories(self) -> None:
        """Save categories to file."""
        try:
            data = {
                "categories": {
                    name: asdict(category) for name, category in self.categories.items()
                }
            }

            with open(self._categories_file, "w") as f:
                yaml.dump(data, f, default_flow_style=False)

        except Exception as e:
            logger.error(f"Failed to save categories: {e}")

    async def register_server(
        self, config: MCPServerConfig, category: Optional[str] = None
    ) -> bool:
        """
        Register a server configuration.

        Args:
            config: Server configuration
            category: Server category (optional)

        Returns:
            True if registration successful
        """
        try:
            # Validate configuration
            if not await self._validate_server_config(config):
                return False

            # Store configuration
            self.server_configs[config.name] = config

            # Add to category if specified
            if category and category in self.categories:
                if config.name not in self.categories[category].servers:
                    self.categories[category].servers.append(config.name)

            # Save configurations
            await self.save_configurations()
            await self.save_categories()

            logger.info(f"Registered server: {config.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to register server {config.name}: {e}")
            return False

    async def _validate_server_config(self, config: MCPServerConfig) -> bool:
        """Validate server configuration."""
        if not config.name:
            logger.error("Server name is required")
            return False

        if not config.command:
            logger.error("Server command is required")
            return False

        # Check for duplicate names
        if config.name in self.server_configs:
            logger.warning(f"Server {config.name} already registered")

        return True

    async def unregister_server(self, server_name: str) -> bool:
        """
        Unregister a server.

        Args:
            server_name: Name of server to unregister

        Returns:
            True if unregistration successful
        """
        try:
            if server_name not in self.server_configs:
                logger.warning(f"Server {server_name} not found")
                return False

            # Disconnect from client if connected
            if self.client and server_name in self.client.servers:
                await self.client.disconnect_server(server_name)

            # Remove from configurations
            del self.server_configs[server_name]

            # Remove from categories
            for category in self.categories.values():
                if server_name in category.servers:
                    category.servers.remove(server_name)

            # Save configurations
            await self.save_configurations()
            await self.save_categories()

            logger.info(f"Unregistered server: {server_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister server {server_name}: {e}")
            return False

    async def connect_servers(
        self, category: Optional[str] = None, priority: Optional[int] = None
    ) -> Dict[str, bool]:
        """
        Connect to registered servers.

        Args:
            category: Connect servers from specific category
            priority: Connect servers with specific priority

        Returns:
            Dictionary of server names and connection results
        """
        if not self.client:
            logger.error("MCP client not initialized")
            return {}

        # Determine which servers to connect
        servers_to_connect = []

        if category:
            # Connect servers from specific category
            if category in self.categories:
                servers_to_connect = [
                    name
                    for name in self.categories[category].servers
                    if name in self.server_configs
                ]
        elif priority:
            # Connect servers with specific priority
            for cat in self.categories.values():
                if cat.priority == priority:
                    servers_to_connect.extend(
                        [name for name in cat.servers if name in self.server_configs]
                    )
        else:
            # Connect all registered servers
            servers_to_connect = list(self.server_configs.keys())

        # Connect servers
        results = {}
        for server_name in servers_to_connect:
            config = self.server_configs[server_name]
            results[server_name] = await self.client.register_server(config)

        connected_count = sum(1 for success in results.values() if success)
        logger.info(f"Connected to {connected_count}/{len(results)} servers")

        return results

    async def discover_available_servers(self) -> List[MCPServerConfig]:
        """
        Discover available MCP servers on the system.

        Returns:
            List of discovered server configurations
        """
        discovered = []

        # Common MCP server locations and commands
        server_patterns = {
            "file-system": {
                "commands": ["mcp-server-filesystem", "filesystem-server"],
                "description": "File system access server",
                "category": "data",
            },
            "git": {
                "commands": ["mcp-server-git", "git-server"],
                "description": "Git repository server",
                "category": "development",
            },
            "github": {
                "commands": ["mcp-server-github", "github-server"],
                "description": "GitHub integration server",
                "category": "development",
            },
            "postgresql": {
                "commands": ["mcp-server-postgres", "postgres-server"],
                "description": "PostgreSQL database server",
                "category": "data",
            },
            "sqlite": {
                "commands": ["mcp-server-sqlite", "sqlite-server"],
                "description": "SQLite database server",
                "category": "data",
            },
            "docker": {
                "commands": ["mcp-server-docker", "docker-server"],
                "description": "Docker container server",
                "category": "devops",
            },
            "slack": {
                "commands": ["mcp-server-slack", "slack-server"],
                "description": "Slack integration server",
                "category": "communication",
            },
        }

        for server_name, info in server_patterns.items():
            for command in info["commands"]:
                if await self._check_command_available(command):
                    config = MCPServerConfig(
                        name=server_name,
                        command=[command],
                        description=info["description"],
                        metadata={"category": info["category"], "discovered": True},
                    )
                    discovered.append(config)

                    # Auto-register if not already registered
                    if server_name not in self.server_configs:
                        await self.register_server(config, info["category"])
                    break

        logger.info(f"Discovered {len(discovered)} available servers")
        return discovered

    async def _check_command_available(self, command: str) -> bool:
        """Check if a command is available on the system."""
        try:
            process = await asyncio.create_subprocess_shell(
                f"which {command}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    def get_servers_by_category(self, category: str) -> List[MCPServerConfig]:
        """Get servers in a specific category."""
        if category not in self.categories:
            return []

        return [
            self.server_configs[name]
            for name in self.categories[category].servers
            if name in self.server_configs
        ]

    def get_servers_by_priority(self, priority: int) -> List[MCPServerConfig]:
        """Get servers with specific priority."""
        servers = []
        for category in self.categories.values():
            if category.priority == priority:
                servers.extend(
                    [
                        self.server_configs[name]
                        for name in category.servers
                        if name in self.server_configs
                    ]
                )
        return servers

    def search_servers(self, query: str) -> List[MCPServerConfig]:
        """Search servers by name or description."""
        query_lower = query.lower()
        results = []

        for config in self.server_configs.values():
            if query_lower in config.name.lower() or (
                config.description and query_lower in config.description.lower()
            ):
                results.append(config)

        return results

    def get_server_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a server."""
        if server_name not in self.server_configs:
            return None

        config = self.server_configs[server_name]

        # Find category
        category = None
        for cat_name, cat_info in self.categories.items():
            if server_name in cat_info.servers:
                category = cat_name
                break

        # Get connection status if client available
        status = None
        capabilities = []
        if self.client:
            status = self.client.get_server_status(server_name)
            # Note: capabilities would need to be fetched in an async context

        return {
            "config": asdict(config),
            "category": category,
            "status": status,
            "capabilities": [],  # Would be populated in async context
        }

    def list_categories(self) -> Dict[str, ServerCategory]:
        """List all server categories."""
        return self.categories.copy()

    def list_servers(self, include_status: bool = False) -> Dict[str, Any]:
        """List all registered servers."""
        servers = {}

        for name, config in self.server_configs.items():
            server_info = {"config": asdict(config)}

            if include_status and self.client:
                server_info["status"] = self.client.get_server_status(name)

            servers[name] = server_info

        return servers

    async def create_server_preset(
        self, preset_name: str, server_names: List[str], description: str = ""
    ) -> bool:
        """
        Create a preset of server configurations.

        Args:
            preset_name: Name of the preset
            server_names: List of server names to include
            description: Preset description

        Returns:
            True if preset creation successful
        """
        try:
            # Validate servers exist
            missing_servers = [
                name for name in server_names if name not in self.server_configs
            ]
            if missing_servers:
                logger.error(f"Missing servers for preset: {missing_servers}")
                return False

            # Create preset category
            preset_category = ServerCategory(
                name=f"preset_{preset_name}",
                description=description or f"Preset: {preset_name}",
                servers=server_names.copy(),
                priority=1,
            )

            self.categories[preset_category.name] = preset_category
            await self.save_categories()

            logger.info(
                f"Created preset '{preset_name}' with {len(server_names)} servers"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create preset {preset_name}: {e}")
            return False

    async def load_preset(self, preset_name: str) -> bool:
        """
        Load and connect servers from a preset.

        Args:
            preset_name: Name of the preset to load

        Returns:
            True if preset loading successful
        """
        preset_category = f"preset_{preset_name}"
        if preset_category not in self.categories:
            logger.error(f"Preset '{preset_name}' not found")
            return False

        results = await self.connect_servers(category=preset_category)
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        logger.info(
            f"Loaded preset '{preset_name}': {success_count}/{total_count} servers connected"
        )
        return success_count > 0

    async def export_configuration(self, file_path: Path) -> bool:
        """Export registry configuration to file."""
        try:
            data = {
                "servers": [asdict(config) for config in self.server_configs.values()],
                "categories": {
                    name: asdict(category) for name, category in self.categories.items()
                },
            }

            with open(file_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False)

            logger.info(f"Exported configuration to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False

    async def import_configuration(self, file_path: Path) -> bool:
        """Import registry configuration from file."""
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)

            # Import servers
            for server_data in data.get("servers", []):
                config = MCPServerConfig(**server_data)
                self.server_configs[config.name] = config

            # Import categories
            for cat_name, cat_data in data.get("categories", {}).items():
                category = ServerCategory(**cat_data)
                self.categories[cat_name] = category

            await self.save_configurations()
            await self.save_categories()

            logger.info(f"Imported configuration from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False
