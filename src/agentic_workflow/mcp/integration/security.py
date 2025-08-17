"""
Security framework for MCP integration.

Provides authentication, authorization, audit logging, and security monitoring
for MCP server connections and tool executions. Includes advanced threat detection,
prompt/response scanning, and malicious connection handling.
"""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from agentic_workflow.core.logging_config import get_logger
from agentic_workflow.mcp.client.base import MCPCapability, MCPServerConfig

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security levels for MCP operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionType(Enum):
    """Types of permissions for MCP operations."""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class SecurityPolicy:
    """Security policy for MCP operations."""

    name: str
    description: str
    server_patterns: List[str] = field(default_factory=list)  # Server name patterns
    tool_patterns: List[str] = field(default_factory=list)  # Tool name patterns
    allowed_permissions: Set[PermissionType] = field(default_factory=set)
    denied_operations: Set[str] = field(default_factory=set)
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    max_execution_time: int = 300  # seconds
    max_resource_usage: Dict[str, Any] = field(default_factory=dict)
    audit_required: bool = True
    approval_required: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    valid_until: Optional[datetime] = None


@dataclass
class SecurityCredential:
    """Security credential for MCP server authentication."""

    server_name: str
    credential_type: str  # 'token', 'certificate', 'key'
    credential_data: str  # Encrypted credential data
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEvent:
    """Security audit event."""

    event_id: str
    event_type: str  # 'server_connection', 'tool_execution', 'policy_violation', etc.
    agent_id: str
    server_id: Optional[str] = None
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityManager:
    """
    Central security manager for MCP integration.

    Handles authentication, authorization, policy enforcement,
    security auditing, threat detection, and prompt/response scanning
    for MCP operations.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize security manager.

        Args:
            config_dir: Directory for security configuration files
        """
        self.config_dir = config_dir or Path.home() / ".agentic_workflow" / "security"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Security policies
        self.policies: Dict[str, SecurityPolicy] = {}
        self.default_policy: Optional[SecurityPolicy] = None

        # Credentials management
        self.credentials: Dict[str, SecurityCredential] = {}
        self.encryption_key: Optional[bytes] = None

        # Audit system
        self.audit_events: List[AuditEvent] = []
        self.max_audit_events = 10000
        self.audit_callbacks: List[Callable[[AuditEvent], None]] = []

        # Security state
        self.security_enabled = True
        self.blocked_servers: Set[str] = set()
        self.blocked_tools: Set[str] = set()
        self.blocked_agents: Set[str] = set()  # New: blocked agents
        self.rate_limits: Dict[str, Dict[str, Any]] = {}

        # Threat detection
        self.suspicious_activities: List[Dict[str, Any]] = []
        self.threat_threshold = 5
        self.malicious_indicators: Set[str] = set()  # New: malicious IP/domains

        # Advanced security components (will be initialized later)
        self.threat_detector = None
        self.prompt_scanner = None

        # Files
        self._policies_file = self.config_dir / "policies.json"
        self._credentials_file = self.config_dir / "credentials.json"
        self._audit_file = self.config_dir / "audit.log"
        self._blocklist_file = self.config_dir / "blocklist.json"

    async def initialize(self) -> None:
        """Initialize security manager."""
        logger.info("Initializing MCP security manager")

        # Load or create encryption key
        await self._setup_encryption()

        # Load security policies
        await self._load_policies()

        # Setup default policy if none exists
        if not self.default_policy:
            await self._create_default_policy()

        # Load credentials
        await self._load_credentials()

        # Load blocklists
        await self._load_blocklists()

        # Setup audit logging
        await self._setup_audit_logging()

        # Initialize advanced security components
        await self._initialize_advanced_security()

        logger.info("MCP security manager initialized")

    async def _setup_encryption(self) -> None:
        """Setup encryption for sensitive data."""
        key_file = self.config_dir / "encryption.key"

        if key_file.exists():
            # Load existing key
            with open(key_file, "rb") as f:
                self.encryption_key = f.read()
        else:
            # Generate new key
            self.encryption_key = os.urandom(32)
            with open(key_file, "wb") as f:
                f.write(self.encryption_key)
            os.chmod(key_file, 0o600)  # Restrict access

    async def _load_policies(self) -> None:
        """Load security policies from file."""
        try:
            if self._policies_file.exists():
                with open(self._policies_file, "r") as f:
                    data = json.load(f)

                for policy_data in data.get("policies", []):
                    policy = SecurityPolicy(**policy_data)
                    self.policies[policy.name] = policy

                default_policy_name = data.get("default_policy")
                if default_policy_name and default_policy_name in self.policies:
                    self.default_policy = self.policies[default_policy_name]

                logger.info(f"Loaded {len(self.policies)} security policies")
        except Exception as e:
            logger.error(f"Failed to load security policies: {e}")

    async def _create_default_policy(self) -> None:
        """Create default security policy."""
        default_policy = SecurityPolicy(
            name="default",
            description="Default security policy for MCP operations",
            server_patterns=["*"],
            tool_patterns=["*"],
            allowed_permissions={PermissionType.READ, PermissionType.EXECUTE},
            denied_operations={"system", "admin", "delete"},
            security_level=SecurityLevel.MEDIUM,
            max_execution_time=300,
            audit_required=True,
            approval_required=False,
        )

        await self.add_policy(default_policy, is_default=True)

    async def _load_credentials(self) -> None:
        """Load encrypted credentials from file."""
        try:
            if self._credentials_file.exists():
                with open(self._credentials_file, "r") as f:
                    data = json.load(f)

                for cred_data in data.get("credentials", []):
                    credential = SecurityCredential(**cred_data)
                    self.credentials[credential.server_name] = credential

                logger.info(f"Loaded {len(self.credentials)} credentials")
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")

    async def _setup_audit_logging(self) -> None:
        """Setup audit logging."""
        # Setup file handler for audit events
        audit_handler = logging.FileHandler(self._audit_file)
        audit_handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        audit_handler.setFormatter(formatter)

        # Create audit logger
        self.audit_logger = logging.getLogger("mcp_security_audit")
        self.audit_logger.addHandler(audit_handler)
        self.audit_logger.setLevel(logging.INFO)

    async def add_policy(
        self, policy: SecurityPolicy, is_default: bool = False
    ) -> bool:
        """
        Add a security policy.

        Args:
            policy: Security policy to add
            is_default: Whether this is the default policy

        Returns:
            True if policy added successfully
        """
        try:
            self.policies[policy.name] = policy

            if is_default:
                self.default_policy = policy

            await self._save_policies()

            logger.info(f"Added security policy: {policy.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to add policy {policy.name}: {e}")
            return False

    async def _save_policies(self) -> None:
        """Save security policies to file."""
        try:
            data = {
                "policies": [
                    {
                        "name": policy.name,
                        "description": policy.description,
                        "server_patterns": policy.server_patterns,
                        "tool_patterns": policy.tool_patterns,
                        "allowed_permissions": [
                            p.value for p in policy.allowed_permissions
                        ],
                        "denied_operations": list(policy.denied_operations),
                        "security_level": policy.security_level.value,
                        "max_execution_time": policy.max_execution_time,
                        "max_resource_usage": policy.max_resource_usage,
                        "audit_required": policy.audit_required,
                        "approval_required": policy.approval_required,
                        "created_at": policy.created_at.isoformat(),
                        "valid_until": (
                            policy.valid_until.isoformat()
                            if policy.valid_until
                            else None
                        ),
                    }
                    for policy in self.policies.values()
                ],
                "default_policy": (
                    self.default_policy.name if self.default_policy else None
                ),
            }

            with open(self._policies_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save policies: {e}")

    async def add_credential(self, credential: SecurityCredential) -> bool:
        """
        Add encrypted credential for server authentication.

        Args:
            credential: Security credential

        Returns:
            True if credential added successfully
        """
        try:
            # Encrypt credential data
            encrypted_data = self._encrypt_data(credential.credential_data)
            credential.credential_data = encrypted_data

            self.credentials[credential.server_name] = credential
            await self._save_credentials()

            logger.info(f"Added credential for server: {credential.server_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to add credential for {credential.server_name}: {e}")
            return False

    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        # Simple XOR encryption for demo (use proper encryption in production)
        if not self.encryption_key:
            return data

        data_bytes = data.encode("utf-8")
        encrypted = bytearray()

        for i, byte in enumerate(data_bytes):
            key_byte = self.encryption_key[i % len(self.encryption_key)]
            encrypted.append(byte ^ key_byte)

        return encrypted.hex()

    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not self.encryption_key:
            return encrypted_data

        try:
            encrypted_bytes = bytes.fromhex(encrypted_data)
            decrypted = bytearray()

            for i, byte in enumerate(encrypted_bytes):
                key_byte = self.encryption_key[i % len(self.encryption_key)]
                decrypted.append(byte ^ key_byte)

            return decrypted.decode("utf-8")
        except Exception:
            return encrypted_data

    async def _save_credentials(self) -> None:
        """Save encrypted credentials to file."""
        try:
            data = {
                "credentials": [
                    {
                        "server_name": cred.server_name,
                        "credential_type": cred.credential_type,
                        "credential_data": cred.credential_data,  # Already encrypted
                        "created_at": cred.created_at.isoformat(),
                        "expires_at": (
                            cred.expires_at.isoformat() if cred.expires_at else None
                        ),
                        "metadata": cred.metadata,
                    }
                    for cred in self.credentials.values()
                ]
            }

            with open(self._credentials_file, "w") as f:
                json.dump(data, f, indent=2)

            os.chmod(self._credentials_file, 0o600)  # Restrict access

        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    async def validate_server_connection(
        self, agent_id: str, server_config: MCPServerConfig
    ) -> bool:
        """
        Validate server connection against security policies.

        Args:
            agent_id: Agent requesting connection
            server_config: Server configuration

        Returns:
            True if connection allowed
        """
        try:
            # Check if server is blocked
            if server_config.name in self.blocked_servers:
                await self._log_security_event(
                    event_type="server_connection_blocked",
                    agent_id=agent_id,
                    server_id=server_config.name,
                    success=False,
                    error_message="Server is blocked",
                    security_level=SecurityLevel.HIGH,
                )
                return False

            # Find applicable policy
            policy = self._find_applicable_policy(server_name=server_config.name)

            # Check policy validity
            if policy.valid_until and datetime.now() > policy.valid_until:
                await self._log_security_event(
                    event_type="policy_expired",
                    agent_id=agent_id,
                    server_id=server_config.name,
                    success=False,
                    error_message="Security policy expired",
                    security_level=SecurityLevel.MEDIUM,
                )
                return False

            # Check rate limits
            if not await self._check_rate_limit(
                agent_id, f"server_connection:{server_config.name}"
            ):
                await self._log_security_event(
                    event_type="rate_limit_exceeded",
                    agent_id=agent_id,
                    server_id=server_config.name,
                    success=False,
                    error_message="Rate limit exceeded",
                    security_level=SecurityLevel.MEDIUM,
                )
                return False

            # Log successful validation
            await self._log_security_event(
                event_type="server_connection_allowed",
                agent_id=agent_id,
                server_id=server_config.name,
                success=True,
                security_level=policy.security_level,
            )

            return True

        except Exception as e:
            logger.error(f"Error validating server connection: {e}")
            return False

    async def validate_tool_execution(
        self, agent_id: str, server_id: str, tool_name: str, parameters: Dict[str, Any]
    ) -> bool:
        """
        Validate tool execution against security policies.

        Args:
            agent_id: Agent requesting execution
            server_id: Server hosting the tool
            tool_name: Tool to execute
            parameters: Tool parameters

        Returns:
            True if execution allowed
        """
        try:
            # Check if tool is blocked
            if tool_name in self.blocked_tools:
                await self._log_security_event(
                    event_type="tool_execution_blocked",
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    success=False,
                    error_message="Tool is blocked",
                    security_level=SecurityLevel.HIGH,
                )
                return False

            # Find applicable policy
            policy = self._find_applicable_policy(
                server_name=server_id, tool_name=tool_name
            )

            # Check permissions
            if PermissionType.EXECUTE not in policy.allowed_permissions:
                await self._log_security_event(
                    event_type="insufficient_permissions",
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    success=False,
                    error_message="Execute permission denied",
                    security_level=SecurityLevel.MEDIUM,
                )
                return False

            # Check denied operations
            if any(
                denied_op in tool_name.lower() for denied_op in policy.denied_operations
            ):
                await self._log_security_event(
                    event_type="denied_operation",
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    success=False,
                    error_message="Operation explicitly denied",
                    security_level=SecurityLevel.HIGH,
                )
                return False

            # Check parameter safety
            if not await self._validate_parameters(parameters, policy):
                await self._log_security_event(
                    event_type="unsafe_parameters",
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    success=False,
                    error_message="Unsafe parameters detected",
                    security_level=SecurityLevel.HIGH,
                )
                return False

            # Check rate limits
            if not await self._check_rate_limit(
                agent_id, f"tool_execution:{tool_name}"
            ):
                await self._log_security_event(
                    event_type="rate_limit_exceeded",
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    success=False,
                    error_message="Rate limit exceeded",
                    security_level=SecurityLevel.MEDIUM,
                )
                return False

            # Log successful validation
            await self._log_security_event(
                event_type="tool_execution_allowed",
                agent_id=agent_id,
                server_id=server_id,
                tool_name=tool_name,
                parameters=parameters,
                success=True,
                security_level=policy.security_level,
            )

            return True

        except Exception as e:
            logger.error(f"Error validating tool execution: {e}")
            return False

    def _find_applicable_policy(
        self, server_name: Optional[str] = None, tool_name: Optional[str] = None
    ) -> SecurityPolicy:
        """Find the most specific applicable policy."""
        applicable_policies = []

        for policy in self.policies.values():
            # Check server pattern match
            server_match = server_name is None or any(
                self._pattern_match(pattern, server_name)
                for pattern in policy.server_patterns
            )

            # Check tool pattern match
            tool_match = tool_name is None or any(
                self._pattern_match(pattern, tool_name)
                for pattern in policy.tool_patterns
            )

            if server_match and tool_match:
                applicable_policies.append(policy)

        if not applicable_policies:
            return self.default_policy or SecurityPolicy(
                name="fallback",
                description="Fallback policy",
                security_level=SecurityLevel.HIGH,
                allowed_permissions=set(),
                audit_required=True,
            )

        # Return most restrictive policy
        return min(applicable_policies, key=lambda p: len(p.allowed_permissions))

    def _pattern_match(self, pattern: str, value: str) -> bool:
        """Simple pattern matching with wildcards."""
        if pattern == "*":
            return True
        if "*" not in pattern:
            return pattern == value

        # Simple wildcard matching
        import re

        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(regex_pattern, value))

    async def _validate_parameters(
        self, parameters: Dict[str, Any], policy: SecurityPolicy
    ) -> bool:
        """Validate tool parameters for safety."""
        # Check for dangerous patterns
        dangerous_patterns = [
            "rm -rf",
            "delete",
            "drop table",
            "truncate",
            "exec",
            "eval",
            "import os",
            "subprocess",
            "../",
            "~",
            "/etc/",
            "/root/",
        ]

        param_str = json.dumps(parameters).lower()

        for pattern in dangerous_patterns:
            if pattern in param_str:
                return False

        return True

    async def _check_rate_limit(self, agent_id: str, operation: str) -> bool:
        """Check rate limits for agent operations."""
        current_time = datetime.now()
        window_size = timedelta(minutes=1)
        max_requests = 60  # 60 requests per minute

        key = f"{agent_id}:{operation}"

        if key not in self.rate_limits:
            self.rate_limits[key] = []

        # Remove old requests
        self.rate_limits[key] = [
            timestamp
            for timestamp in self.rate_limits[key]
            if current_time - timestamp < window_size
        ]

        # Check limit
        if len(self.rate_limits[key]) >= max_requests:
            return False

        # Add current request
        self.rate_limits[key].append(current_time)
        return True

    async def _log_security_event(
        self,
        event_type: str,
        agent_id: str,
        success: bool,
        server_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
    ) -> None:
        """Log security event for audit."""
        event = AuditEvent(
            event_id=hashlib.md5(
                f"{datetime.now().isoformat()}{agent_id}{event_type}".encode()
            ).hexdigest(),
            event_type=event_type,
            agent_id=agent_id,
            server_id=server_id,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            success=success,
            error_message=error_message,
            security_level=security_level,
        )

        # Add to memory audit
        self.audit_events.append(event)
        if len(self.audit_events) > self.max_audit_events:
            self.audit_events = self.audit_events[-self.max_audit_events :]

        # Log to file
        self.audit_logger.info(
            json.dumps(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "agent_id": event.agent_id,
                    "server_id": event.server_id,
                    "tool_name": event.tool_name,
                    "success": event.success,
                    "error_message": event.error_message,
                    "security_level": event.security_level.value,
                    "timestamp": event.timestamp.isoformat(),
                }
            )
        )

        # Detect suspicious activity
        if not success:
            await self._detect_threats(agent_id, event_type)

        # Notify callbacks
        for callback in self.audit_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in audit callback: {e}")

    async def _detect_threats(self, agent_id: str, event_type: str) -> None:
        """Detect suspicious activities and threats."""
        recent_time = datetime.now() - timedelta(minutes=10)

        # Count recent failed events for this agent
        recent_failures = [
            event
            for event in self.audit_events
            if (
                event.agent_id == agent_id
                and not event.success
                and event.timestamp > recent_time
            )
        ]

        if len(recent_failures) >= self.threat_threshold:
            # Block agent temporarily
            await self._handle_threat(agent_id, "excessive_failures", recent_failures)

    async def _handle_threat(
        self, agent_id: str, threat_type: str, related_events: List[AuditEvent]
    ) -> None:
        """Handle detected security threat."""
        threat_info = {
            "agent_id": agent_id,
            "threat_type": threat_type,
            "detected_at": datetime.now().isoformat(),
            "related_events": [event.event_id for event in related_events],
            "action_taken": "agent_blocked",
        }

        self.suspicious_activities.append(threat_info)

        # Log critical security event
        await self._log_security_event(
            event_type="threat_detected",
            agent_id=agent_id,
            success=False,
            error_message=f"Threat detected: {threat_type}",
            security_level=SecurityLevel.CRITICAL,
        )

        logger.critical(f"Security threat detected for agent {agent_id}: {threat_type}")

    def add_audit_callback(self, callback: Callable[[AuditEvent], None]) -> None:
        """Add audit event callback."""
        self.audit_callbacks.append(callback)

    def get_audit_events(
        self,
        agent_id: Optional[str] = None,
        event_type: Optional[str] = None,
        security_level: Optional[SecurityLevel] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Get audit events with optional filtering."""
        events = self.audit_events

        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if security_level:
            events = [e for e in events if e.security_level == security_level]

        if limit:
            events = events[-limit:]

        return events

    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and statistics."""
        total_events = len(self.audit_events)
        failed_events = len([e for e in self.audit_events if not e.success])

        metrics = {
            "total_audit_events": total_events,
            "failed_events": failed_events,
            "success_rate": (
                (total_events - failed_events) / total_events if total_events > 0 else 0
            ),
            "security_policies_count": len(self.policies),
            "blocked_servers_count": len(self.blocked_servers),
            "blocked_tools_count": len(self.blocked_tools),
            "suspicious_activities_count": len(self.suspicious_activities),
            "rate_limits_active": len(self.rate_limits),
        }

        # Event type distribution
        event_types = {}
        for event in self.audit_events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        metrics["event_type_distribution"] = event_types

        # Security level distribution
        security_levels = {}
        for event in self.audit_events:
            level = event.security_level.value
            security_levels[level] = security_levels.get(level, 0) + 1
        metrics["security_level_distribution"] = security_levels

        return metrics

    async def block_server(self, server_name: str, reason: str = "") -> None:
        """Block a server from connections."""
        self.blocked_servers.add(server_name)
        logger.warning(f"Blocked server: {server_name} - {reason}")

    async def unblock_server(self, server_name: str) -> None:
        """Unblock a server."""
        self.blocked_servers.discard(server_name)
        logger.info(f"Unblocked server: {server_name}")

    async def block_tool(self, tool_name: str, reason: str = "") -> None:
        """Block a tool from execution."""
        self.blocked_tools.add(tool_name)
        logger.warning(f"Blocked tool: {tool_name} - {reason}")

    async def unblock_tool(self, tool_name: str) -> None:
        """Unblock a tool."""
        self.blocked_tools.discard(tool_name)
        logger.info(f"Unblocked tool: {tool_name}")

    async def export_audit_log(self, file_path: Path, format: str = "json") -> bool:
        """Export audit log to file."""
        try:
            if format == "json":
                with open(file_path, "w") as f:
                    json.dump(
                        [
                            {
                                "event_id": event.event_id,
                                "event_type": event.event_type,
                                "agent_id": event.agent_id,
                                "server_id": event.server_id,
                                "tool_name": event.tool_name,
                                "parameters": event.parameters,
                                "result": event.result,
                                "success": event.success,
                                "error_message": event.error_message,
                                "security_level": event.security_level.value,
                                "timestamp": event.timestamp.isoformat(),
                                "metadata": event.metadata,
                            }
                            for event in self.audit_events
                        ],
                        f,
                        indent=2,
                    )

            logger.info(f"Exported audit log to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export audit log: {e}")
            return False

    async def _initialize_advanced_security(self) -> None:
        """Initialize advanced security components."""
        try:
            # Initialize threat detection engine
            from .threat_detection import ThreatDetectionEngine

            self.threat_detector = ThreatDetectionEngine()

            # Initialize prompt/response scanner
            from .prompt_security import PromptResponseScanner

            self.prompt_scanner = PromptResponseScanner()

            logger.info("Advanced security components initialized")
        except Exception as e:
            logger.error(f"Failed to initialize advanced security components: {e}")

    async def _load_blocklists(self) -> None:
        """Load security blocklists."""
        try:
            if self._blocklist_file.exists():
                with open(self._blocklist_file, "r") as f:
                    data = json.load(f)

                self.blocked_servers.update(data.get("blocked_servers", []))
                self.blocked_tools.update(data.get("blocked_tools", []))
                self.blocked_agents.update(data.get("blocked_agents", []))
                self.malicious_indicators.update(data.get("malicious_indicators", []))

                logger.info(
                    f"Loaded blocklists: {len(self.blocked_servers)} servers, "
                    f"{len(self.blocked_tools)} tools, {len(self.blocked_agents)} agents, "
                    f"{len(self.malicious_indicators)} indicators"
                )
        except Exception as e:
            logger.error(f"Failed to load blocklists: {e}")

    async def _save_blocklists(self) -> None:
        """Save security blocklists."""
        try:
            data = {
                "blocked_servers": list(self.blocked_servers),
                "blocked_tools": list(self.blocked_tools),
                "blocked_agents": list(self.blocked_agents),
                "malicious_indicators": list(self.malicious_indicators),
                "updated_at": datetime.now().isoformat(),
            }

            with open(self._blocklist_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved security blocklists")
        except Exception as e:
            logger.error(f"Failed to save blocklists: {e}")

    async def validate_connection_security(
        self,
        agent_id: str,
        server_config: MCPServerConfig,
        connection_data: Dict[str, Any],
    ) -> bool:
        """
        Enhanced connection validation with threat detection.

        Args:
            agent_id: Agent requesting connection
            server_config: Server configuration
            connection_data: Connection metadata for threat analysis

        Returns:
            True if connection allowed
        """
        # Check if agent is blocked
        if agent_id in self.blocked_agents:
            await self._log_security_event(
                event_type="blocked_agent_connection",
                agent_id=agent_id,
                server_id=server_config.name,
                success=False,
                error_message="Agent is blocked",
                security_level=SecurityLevel.CRITICAL,
            )
            return False

        # Check basic server validation first
        if not await self.validate_server_connection(agent_id, server_config):
            return False

        # Advanced threat detection
        if self.threat_detector:
            threat_event = await self.threat_detector.analyze_connection_attempt(
                agent_id, server_config.name, connection_data
            )

            if threat_event:
                # Block high-confidence threats
                if threat_event.confidence >= 0.8:
                    await self._handle_security_threat(
                        agent_id, server_config.name, threat_event
                    )
                    return False

                # Log lower-confidence threats
                self.threat_detector.add_threat_event(threat_event)

        return True

    async def validate_request_security(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        request_data: Dict[str, Any],
    ) -> bool:
        """
        Enhanced request validation with threat detection.

        Args:
            agent_id: Agent making request
            server_id: Target server
            tool_name: Tool being executed
            request_data: Request data for analysis

        Returns:
            True if request allowed
        """
        # Check basic tool validation first
        if not await self.validate_tool_execution(
            agent_id, server_id, tool_name, request_data
        ):
            return False

        # Advanced threat detection
        if self.threat_detector:
            threat_event = await self.threat_detector.analyze_request(
                agent_id, server_id, tool_name, request_data
            )

            if threat_event:
                # Block high-confidence threats
                if threat_event.confidence >= 0.7:
                    await self._handle_security_threat(
                        agent_id, server_id, threat_event
                    )
                    return False

                # Log threats
                self.threat_detector.add_threat_event(threat_event)

        return True

    async def scan_prompt_security(
        self, agent_id: str, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Scan prompt for security issues.

        Args:
            agent_id: Agent sending prompt
            prompt: Prompt content
            context: Additional context

        Returns:
            Scan results with security assessment
        """
        if not self.prompt_scanner:
            return {"status": "scanner_unavailable"}

        try:
            scan_report = await self.prompt_scanner.scan_prompt(
                agent_id, prompt, context
            )

            # Handle security violations
            if scan_report.scan_result.value in ["threat", "blocked"]:
                await self._log_security_event(
                    event_type="prompt_security_violation",
                    agent_id=agent_id,
                    success=False,
                    error_message=f"Prompt scan result: {scan_report.scan_result.value}",
                    security_level=SecurityLevel.HIGH,
                )

            return {
                "status": scan_report.scan_result.value,
                "risk_score": scan_report.risk_score,
                "violations": len(scan_report.violations),
                "sanitized": scan_report.sanitized_content is not None,
                "blocked": scan_report.blocked_content is not None,
            }

        except Exception as e:
            logger.error(f"Failed to scan prompt security: {e}")
            return {"status": "scan_error", "error": str(e)}

    async def scan_response_security(
        self, agent_id: str, response: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Scan response for security issues.

        Args:
            agent_id: Agent receiving response
            response: Response content
            context: Additional context

        Returns:
            Scan results with security assessment
        """
        if not self.prompt_scanner:
            return {"status": "scanner_unavailable"}

        try:
            scan_report = await self.prompt_scanner.scan_response(
                agent_id, response, context
            )

            # Handle security violations
            if scan_report.scan_result.value in ["threat", "blocked"]:
                await self._log_security_event(
                    event_type="response_security_violation",
                    agent_id=agent_id,
                    success=False,
                    error_message=f"Response scan result: {scan_report.scan_result.value}",
                    security_level=SecurityLevel.HIGH,
                )

            return {
                "status": scan_report.scan_result.value,
                "risk_score": scan_report.risk_score,
                "violations": len(scan_report.violations),
                "sanitized": scan_report.sanitized_content is not None,
                "blocked": scan_report.blocked_content is not None,
            }

        except Exception as e:
            logger.error(f"Failed to scan response security: {e}")
            return {"status": "scan_error", "error": str(e)}

    async def _handle_security_threat(
        self, agent_id: str, server_id: str, threat_event
    ) -> None:
        """Handle detected security threat."""
        logger.critical(
            f"Security threat detected: {threat_event.description} "
            f"(confidence: {threat_event.confidence})"
        )

        # Block the threat
        threat_event.blocked = True

        # Consider blocking agent if multiple high-confidence threats
        if self.threat_detector:
            agent_risk = self.threat_detector.get_agent_risk_score(agent_id)
            if agent_risk >= 0.8:
                await self.block_agent(agent_id, f"High risk score: {agent_risk}")

        # Log critical security event
        await self._log_security_event(
            event_type="critical_threat_blocked",
            agent_id=agent_id,
            server_id=server_id,
            success=False,
            error_message=f"Blocked threat: {threat_event.description}",
            security_level=SecurityLevel.CRITICAL,
        )

    async def block_agent(self, agent_id: str, reason: str = "") -> None:
        """Block an agent from MCP operations."""
        self.blocked_agents.add(agent_id)
        await self._save_blocklists()
        logger.critical(f"Blocked agent: {agent_id} - {reason}")

    async def unblock_agent(self, agent_id: str) -> None:
        """Unblock an agent."""
        self.blocked_agents.discard(agent_id)
        await self._save_blocklists()
        logger.info(f"Unblocked agent: {agent_id}")

    async def add_malicious_indicator(self, indicator: str, reason: str = "") -> None:
        """Add malicious indicator (IP, domain, etc.)."""
        self.malicious_indicators.add(indicator)
        await self._save_blocklists()
        logger.warning(f"Added malicious indicator: {indicator} - {reason}")

    async def remove_malicious_indicator(self, indicator: str) -> None:
        """Remove malicious indicator."""
        self.malicious_indicators.discard(indicator)
        await self._save_blocklists()
        logger.info(f"Removed malicious indicator: {indicator}")

    def get_comprehensive_security_metrics(self) -> Dict[str, Any]:
        """Get comprehensive security metrics including advanced components."""
        base_metrics = self.get_security_metrics()

        # Add advanced metrics
        if self.threat_detector:
            threat_summary = self.threat_detector.get_threat_summary()
            base_metrics.update(
                {
                    "threat_detection": threat_summary,
                    "total_threats_detected": threat_summary.get("total_threats", 0),
                    "critical_threats": threat_summary.get("threat_levels", {}).get(
                        "critical", 0
                    ),
                }
            )

        if self.prompt_scanner:
            scan_stats = self.prompt_scanner.get_scan_statistics()
            base_metrics.update(
                {
                    "prompt_scanning": scan_stats,
                    "total_scans": scan_stats.get("total_scans", 0),
                    "blocked_content": scan_stats.get("blocked_content_count", 0),
                }
            )

        # Add blocklist metrics
        base_metrics.update(
            {
                "blocked_agents_count": len(self.blocked_agents),
                "malicious_indicators_count": len(self.malicious_indicators),
            }
        )

        return base_metrics

    async def generate_security_report(
        self, time_window: timedelta = timedelta(hours=24)
    ) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        report = {
            "report_generated": datetime.now().isoformat(),
            "time_window_hours": time_window.total_seconds() / 3600,
            "security_metrics": self.get_comprehensive_security_metrics(),
            "threat_analysis": {},
            "scanning_analysis": {},
            "recommendations": [],
        }

        # Add threat analysis
        if self.threat_detector:
            threat_summary = self.threat_detector.get_threat_summary(time_window)
            report["threat_analysis"] = threat_summary

            # Generate recommendations based on threats
            if threat_summary.get("total_threats", 0) > 10:
                report["recommendations"].append(
                    "High threat activity detected. Consider reviewing security policies."
                )

        # Add scanning analysis
        if self.prompt_scanner:
            scan_stats = self.prompt_scanner.get_scan_statistics(time_window)
            report["scanning_analysis"] = scan_stats

            # Generate recommendations based on scans
            if scan_stats.get("blocked_content_count", 0) > 5:
                report["recommendations"].append(
                    "Multiple content blocks detected. Review content filtering policies."
                )

        # General recommendations
        if len(self.blocked_agents) > 0:
            report["recommendations"].append(
                f"{len(self.blocked_agents)} agents are currently blocked. Review agent permissions."
            )

        return report
