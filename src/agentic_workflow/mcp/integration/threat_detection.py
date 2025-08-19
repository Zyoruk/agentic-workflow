"""
Advanced threat detection system for MCP integration.

Provides real-time monitoring and detection of malicious connections,
suspicious activities, and advanced security threats.
"""

import hashlib
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)


class ThreatLevel(Enum):
    """Threat severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """Types of security threats."""

    MALICIOUS_CONNECTION = "malicious_connection"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    DATA_EXFILTRATION = "data_exfiltration"
    INJECTION_ATTACK = "injection_attack"
    BRUTE_FORCE = "brute_force"
    ANOMALOUS_TRAFFIC = "anomalous_traffic"
    MALFORMED_REQUEST = "malformed_request"
    PRIVILEGE_ESCALATION = "privilege_escalation"


@dataclass
class ThreatIndicator:
    """Security threat indicator."""

    indicator_type: str
    value: str
    threat_types: List[ThreatType]
    confidence: float  # 0.0 to 1.0
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    hit_count: int = 0


@dataclass
class ThreatEvent:
    """Detected security threat event."""

    event_id: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    agent_id: str
    description: str
    server_id: Optional[str] = None
    tool_name: Optional[str] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    blocked: bool = False
    false_positive: bool = False


class ThreatDetectionEngine:
    """
    Advanced threat detection engine for MCP security.

    Monitors connections, requests, and responses for malicious activities
    and implements real-time threat detection and response.
    """

    def __init__(self) -> None:
        """Initialize threat detection engine."""
        self.threat_indicators: Dict[str, ThreatIndicator] = {}
        self.threat_events: List[ThreatEvent] = []
        self.connection_profiles: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.behavior_baselines: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # Detection patterns
        self.malicious_patterns = {
            "injection_patterns": [
                r"(\bselect\b.*\bfrom\b.*\bwhere\b)",  # SQL injection
                r"(\bunion\b.*\bselect\b)",
                r"(script.*?javascript)",  # XSS
                r"(\beval\s*\()",  # Code injection
                r"(\bexec\s*\()",
                r"(__import__)",  # Python injection
                r"(rm\s+-rf\s+/)",  # Destructive commands
                r"(\.\.\/)",  # Path traversal
                r"(\bsudo\b.*\broot\b)",  # Privilege escalation
            ],
            "suspicious_domains": [
                r".*\.tk$",
                r".*\.ml$",
                r".*\.ga$",  # Suspicious TLDs
                r".*bit\.ly.*",
                r".*tinyurl.*",  # URL shorteners
            ],
            "data_exfiltration": [
                r"(password|token|key|secret|credential)",
                r"(api_key|access_token|auth_token)",
                r"(private_key|cert|certificate)",
                r"(database|db_|mysql|postgres)",
            ],
        }

        # Rate limiting and anomaly detection
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.error_patterns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Configuration
        self.max_events = 10000
        self.learning_period = timedelta(hours=24)
        self.threat_threshold = 0.7

        # Initialize threat indicators
        self._initialize_threat_indicators()

    def _initialize_threat_indicators(self) -> None:
        """Initialize known threat indicators."""
        # Known malicious IP patterns
        self.add_threat_indicator(
            ThreatIndicator(
                indicator_type="ip_pattern",
                value=r"^(10\.0\.0\.|192\.168\.|127\.0\.0\.1)",
                threat_types=[ThreatType.SUSPICIOUS_BEHAVIOR],
                confidence=0.3,
                description="Private IP ranges (potential internal threat)",
            )
        )

        # Suspicious user agents
        self.add_threat_indicator(
            ThreatIndicator(
                indicator_type="user_agent",
                value="curl|wget|python-requests|boto3",
                threat_types=[ThreatType.SUSPICIOUS_BEHAVIOR],
                confidence=0.4,
                description="Automated tool user agents",
            )
        )

        # High-risk commands
        self.add_threat_indicator(
            ThreatIndicator(
                indicator_type="command_pattern",
                value=r"(delete|drop|truncate|rm|kill|shutdown)",
                threat_types=[ThreatType.MALICIOUS_CONNECTION],
                confidence=0.8,
                description="High-risk destructive commands",
            )
        )

    def add_threat_indicator(self, indicator: ThreatIndicator) -> None:
        """Add a threat indicator to the detection system."""
        key = f"{indicator.indicator_type}:{indicator.value}"
        self.threat_indicators[key] = indicator
        logger.info(f"Added threat indicator: {indicator.description}")

    async def analyze_connection_attempt(
        self, agent_id: str, server_id: str, connection_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """
        Analyze connection attempt for malicious indicators.

        Args:
            agent_id: Agent attempting connection
            server_id: Target server
            connection_data: Connection metadata

        Returns:
            ThreatEvent if threat detected, None otherwise
        """
        threats = []

        # Check connection frequency
        now = datetime.now()
        key = f"{agent_id}:{server_id}"

        # Record connection attempt
        self.request_history[key].append(now)

        # Analyze connection patterns
        threat = await self._analyze_connection_patterns(agent_id, server_id)
        if threat:
            threats.append(threat)

        # Check against threat indicators
        threat = await self._check_threat_indicators(
            agent_id, server_id, connection_data
        )
        if threat:
            threats.append(threat)

        # Analyze connection metadata
        threat = await self._analyze_connection_metadata(
            agent_id, server_id, connection_data
        )
        if threat:
            threats.append(threat)

        # Return highest severity threat
        if threats:
            return max(threats, key=lambda t: t.confidence)

        return None

    async def analyze_request(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        request_data: Dict[str, Any],
    ) -> Optional[ThreatEvent]:
        """
        Analyze tool execution request for malicious content.

        Args:
            agent_id: Agent making request
            server_id: Target server
            tool_name: Tool being executed
            request_data: Request parameters and data

        Returns:
            ThreatEvent if threat detected, None otherwise
        """
        threats = []

        # Analyze request patterns
        threat = await self._analyze_injection_patterns(
            agent_id, server_id, tool_name, request_data
        )
        if threat:
            threats.append(threat)

        # Check for data exfiltration attempts
        threat = await self._analyze_data_access_patterns(
            agent_id, server_id, tool_name, request_data
        )
        if threat:
            threats.append(threat)

        # Analyze parameter anomalies
        threat = await self._analyze_parameter_anomalies(
            agent_id, server_id, tool_name, request_data
        )
        if threat:
            threats.append(threat)

        # Return highest severity threat
        if threats:
            return max(threats, key=lambda t: t.confidence)

        return None

    async def analyze_response(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        response_data: Dict[str, Any],
    ) -> Optional[ThreatEvent]:
        """
        Analyze response for security issues and data leakage.

        Args:
            agent_id: Agent receiving response
            server_id: Source server
            tool_name: Tool that generated response
            response_data: Response data

        Returns:
            ThreatEvent if threat detected, None otherwise
        """
        threats = []

        # Check for sensitive data exposure
        threat = await self._analyze_sensitive_data_exposure(
            agent_id, server_id, tool_name, response_data
        )
        if threat:
            threats.append(threat)

        # Analyze response patterns for anomalies
        threat = await self._analyze_response_anomalies(
            agent_id, server_id, tool_name, response_data
        )
        if threat:
            threats.append(threat)

        # Return highest severity threat
        if threats:
            return max(threats, key=lambda t: t.confidence)

        return None

    async def _analyze_connection_patterns(
        self, agent_id: str, server_id: str
    ) -> Optional[ThreatEvent]:
        """Analyze connection patterns for suspicious behavior."""
        key = f"{agent_id}:{server_id}"
        history = self.request_history[key]

        if len(history) < 10:
            return None

        now = datetime.now()
        recent_window = timedelta(minutes=1)
        recent_requests = [t for t in history if now - t < recent_window]

        # Check for rapid-fire connections (potential brute force)
        if len(recent_requests) > 50:
            return ThreatEvent(
                event_id=self._generate_event_id(agent_id, server_id, "brute_force"),
                threat_type=ThreatType.BRUTE_FORCE,
                threat_level=ThreatLevel.HIGH,
                agent_id=agent_id,
                server_id=server_id,
                description=f"Excessive connection attempts: {len(recent_requests)} in 1 minute",
                evidence={"request_count": len(recent_requests), "window_minutes": 1},
                confidence=0.9,
            )

        # Check for unusual timing patterns
        if len(recent_requests) > 5:
            intervals = []
            for i in range(1, len(recent_requests)):
                interval = (recent_requests[i] - recent_requests[i - 1]).total_seconds()
                intervals.append(interval)

            # Very regular intervals might indicate automation
            if len(set(round(i, 1) for i in intervals)) == 1:
                return ThreatEvent(
                    event_id=self._generate_event_id(
                        agent_id, server_id, "automated_pattern"
                    ),
                    threat_type=ThreatType.SUSPICIOUS_BEHAVIOR,
                    threat_level=ThreatLevel.MEDIUM,
                    agent_id=agent_id,
                    server_id=server_id,
                    description="Highly regular request timing suggests automation",
                    evidence={"intervals": intervals},
                    confidence=0.6,
                )

        return None

    async def _check_threat_indicators(
        self, agent_id: str, server_id: str, connection_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """Check connection data against known threat indicators."""
        for key, indicator in self.threat_indicators.items():
            indicator_type, pattern = key.split(":", 1)

            # Check different data fields based on indicator type
            check_value = None
            if indicator_type == "ip_pattern" and "source_ip" in connection_data:
                check_value = connection_data["source_ip"]
            elif indicator_type == "user_agent" and "user_agent" in connection_data:
                check_value = connection_data["user_agent"]
            elif indicator_type == "command_pattern" and "command" in connection_data:
                check_value = connection_data["command"]

            if check_value and re.search(pattern, str(check_value), re.IGNORECASE):
                indicator.hit_count += 1
                indicator.last_seen = datetime.now()

                return ThreatEvent(
                    event_id=self._generate_event_id(
                        agent_id, server_id, "indicator_match"
                    ),
                    threat_type=indicator.threat_types[0],
                    threat_level=self._confidence_to_level(indicator.confidence),
                    agent_id=agent_id,
                    server_id=server_id,
                    description=f"Matched threat indicator: {indicator.description}",
                    evidence={"indicator": key, "matched_value": check_value},
                    confidence=indicator.confidence,
                )

        return None

    async def _analyze_connection_metadata(
        self, agent_id: str, server_id: str, connection_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """Analyze connection metadata for anomalies."""
        # Check for missing or suspicious metadata
        required_fields = ["timestamp", "source"]
        missing_fields = [f for f in required_fields if f not in connection_data]

        if missing_fields:
            return ThreatEvent(
                event_id=self._generate_event_id(
                    agent_id, server_id, "missing_metadata"
                ),
                threat_type=ThreatType.MALFORMED_REQUEST,
                threat_level=ThreatLevel.MEDIUM,
                agent_id=agent_id,
                server_id=server_id,
                description=f"Missing required connection metadata: {missing_fields}",
                evidence={"missing_fields": missing_fields},
                confidence=0.5,
            )

        # Check for suspicious timing
        if "timestamp" in connection_data:
            timestamp = connection_data["timestamp"]
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    return ThreatEvent(
                        event_id=self._generate_event_id(
                            agent_id, server_id, "invalid_timestamp"
                        ),
                        threat_type=ThreatType.MALFORMED_REQUEST,
                        threat_level=ThreatLevel.LOW,
                        agent_id=agent_id,
                        server_id=server_id,
                        description="Invalid timestamp format in connection data",
                        evidence={"timestamp": connection_data["timestamp"]},
                        confidence=0.3,
                    )

            # Check for future timestamps (potential clock manipulation)
            if timestamp > datetime.now() + timedelta(minutes=5):
                return ThreatEvent(
                    event_id=self._generate_event_id(
                        agent_id, server_id, "future_timestamp"
                    ),
                    threat_type=ThreatType.SUSPICIOUS_BEHAVIOR,
                    threat_level=ThreatLevel.MEDIUM,
                    agent_id=agent_id,
                    server_id=server_id,
                    description="Connection timestamp is in the future",
                    evidence={"timestamp": timestamp.isoformat()},
                    confidence=0.6,
                )

        return None

    async def _analyze_injection_patterns(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        request_data: Dict[str, Any],
    ) -> Optional[ThreatEvent]:
        """Analyze request for injection attack patterns."""
        request_str = json.dumps(request_data).lower()

        for pattern_type, patterns in self.malicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, request_str, re.IGNORECASE):
                    threat_type = ThreatType.INJECTION_ATTACK
                    if pattern_type == "data_exfiltration":
                        threat_type = ThreatType.DATA_EXFILTRATION

                    return ThreatEvent(
                        event_id=self._generate_event_id(
                            agent_id, server_id, pattern_type
                        ),
                        threat_type=threat_type,
                        threat_level=ThreatLevel.HIGH,
                        agent_id=agent_id,
                        server_id=server_id,
                        tool_name=tool_name,
                        description=f"Detected {pattern_type.replace('_', ' ')} pattern in request",
                        evidence={"pattern": pattern, "matched_content": request_str},
                        confidence=0.8,
                    )

        return None

    async def _analyze_data_access_patterns(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        request_data: Dict[str, Any],
    ) -> Optional[ThreatEvent]:
        """Analyze request for suspicious data access patterns."""
        # Check for attempts to access sensitive data
        sensitive_keywords = [
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "private",
            "confidential",
            "internal",
            "admin",
        ]

        request_str = json.dumps(request_data).lower()

        suspicious_count = sum(
            1 for keyword in sensitive_keywords if keyword in request_str
        )

        if suspicious_count >= 3:
            return ThreatEvent(
                event_id=self._generate_event_id(
                    agent_id, server_id, "sensitive_data_access"
                ),
                threat_type=ThreatType.DATA_EXFILTRATION,
                threat_level=ThreatLevel.HIGH,
                agent_id=agent_id,
                server_id=server_id,
                tool_name=tool_name,
                description="Multiple sensitive data keywords detected in request",
                evidence={
                    "keyword_count": suspicious_count,
                    "request_content": request_str,
                },
                confidence=0.7,
            )

        return None

    async def _analyze_parameter_anomalies(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        request_data: Dict[str, Any],
    ) -> Optional[ThreatEvent]:
        """Analyze request parameters for anomalies."""
        # Check for unusually large parameters
        for key, value in request_data.items():
            if isinstance(value, str) and len(value) > 10000:
                return ThreatEvent(
                    event_id=self._generate_event_id(
                        agent_id, server_id, "large_parameter"
                    ),
                    threat_type=ThreatType.ANOMALOUS_TRAFFIC,
                    threat_level=ThreatLevel.MEDIUM,
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    description=f"Unusually large parameter detected: {key}",
                    evidence={"parameter": key, "size": len(value)},
                    confidence=0.5,
                )

        # Check for unusual parameter names
        suspicious_param_patterns = [
            r"__.*__",  # Python magic methods
            r"\$\{.*\}",  # Variable substitution
            r"<%.*%>",  # Template injection
        ]

        for key in request_data.keys():
            for pattern in suspicious_param_patterns:
                if re.search(pattern, key):
                    return ThreatEvent(
                        event_id=self._generate_event_id(
                            agent_id, server_id, "suspicious_parameter"
                        ),
                        threat_type=ThreatType.INJECTION_ATTACK,
                        threat_level=ThreatLevel.HIGH,
                        agent_id=agent_id,
                        server_id=server_id,
                        tool_name=tool_name,
                        description=f"Suspicious parameter name pattern: {key}",
                        evidence={"parameter": key, "pattern": pattern},
                        confidence=0.8,
                    )

        return None

    async def _analyze_sensitive_data_exposure(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        response_data: Dict[str, Any],
    ) -> Optional[ThreatEvent]:
        """Check response for sensitive data exposure."""
        response_str = json.dumps(response_data).lower()

        # Pattern for detecting credentials in responses
        credential_patterns = [
            r'password["\s]*[:=]["\s]*[^\s"]{8,}',
            r'token["\s]*[:=]["\s]*[a-zA-Z0-9]{20,}',
            r'key["\s]*[:=]["\s]*[a-zA-Z0-9]{16,}',
            r'secret["\s]*[:=]["\s]*[a-zA-Z0-9]{16,}',
        ]

        for pattern in credential_patterns:
            if re.search(pattern, response_str):
                return ThreatEvent(
                    event_id=self._generate_event_id(
                        agent_id, server_id, "data_exposure"
                    ),
                    threat_type=ThreatType.DATA_EXFILTRATION,
                    threat_level=ThreatLevel.CRITICAL,
                    agent_id=agent_id,
                    server_id=server_id,
                    tool_name=tool_name,
                    description="Potential sensitive data exposed in response",
                    evidence={"pattern": pattern},
                    confidence=0.9,
                )

        return None

    async def _analyze_response_anomalies(
        self,
        agent_id: str,
        server_id: str,
        tool_name: str,
        response_data: Dict[str, Any],
    ) -> Optional[ThreatEvent]:
        """Analyze response for anomalies."""
        # Check for unusually large responses
        response_size = len(json.dumps(response_data))
        if response_size > 1000000:  # 1MB
            return ThreatEvent(
                event_id=self._generate_event_id(agent_id, server_id, "large_response"),
                threat_type=ThreatType.ANOMALOUS_TRAFFIC,
                threat_level=ThreatLevel.MEDIUM,
                agent_id=agent_id,
                server_id=server_id,
                tool_name=tool_name,
                description="Unusually large response detected",
                evidence={"response_size": response_size},
                confidence=0.4,
            )

        return None

    def _generate_event_id(self, agent_id: str, server_id: str, event_type: str) -> str:
        """Generate unique event ID."""
        timestamp = datetime.now().isoformat()
        data = f"{agent_id}:{server_id}:{event_type}:{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()

    def _confidence_to_level(self, confidence: float) -> ThreatLevel:
        """Convert confidence score to threat level."""
        if confidence >= 0.9:
            return ThreatLevel.CRITICAL
        elif confidence >= 0.7:
            return ThreatLevel.HIGH
        elif confidence >= 0.5:
            return ThreatLevel.MEDIUM
        elif confidence >= 0.3:
            return ThreatLevel.LOW
        else:
            return ThreatLevel.INFO

    def add_threat_event(self, event: ThreatEvent) -> None:
        """Add threat event to history."""
        self.threat_events.append(event)

        # Maintain max events limit
        if len(self.threat_events) > self.max_events:
            self.threat_events = self.threat_events[-self.max_events :]

        logger.warning(
            f"Threat detected: {event.description} (confidence: {event.confidence})"
        )

    def get_threat_summary(
        self, time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get summary of detected threats."""
        if time_window:
            cutoff = datetime.now() - time_window
            events = [e for e in self.threat_events if e.timestamp > cutoff]
        else:
            events = self.threat_events

        summary: Dict[str, Any] = {
            "total_threats": len(events),
            "threat_types": {},
            "threat_levels": {},
            "top_agents": {},
            "top_servers": {},
            "blocked_events": 0,
            "false_positives": 0,
        }

        for event in events:
            # Count by type
            threat_type = event.threat_type.value
            summary["threat_types"][threat_type] = (
                summary["threat_types"].get(threat_type, 0) + 1
            )

            # Count by level
            threat_level = event.threat_level.value
            summary["threat_levels"][threat_level] = (
                summary["threat_levels"].get(threat_level, 0) + 1
            )

            # Count by agent
            summary["top_agents"][event.agent_id] = (
                summary["top_agents"].get(event.agent_id, 0) + 1
            )

            # Count by server
            if event.server_id:
                summary["top_servers"][event.server_id] = (
                    summary["top_servers"].get(event.server_id, 0) + 1
                )

            # Count blocked and false positives
            if event.blocked:
                summary["blocked_events"] += 1
            if event.false_positive:
                summary["false_positives"] += 1

        # Sort top agents and servers
        summary["top_agents"] = dict(
            sorted(summary["top_agents"].items(), key=lambda x: x[1], reverse=True)[:10]
        )
        summary["top_servers"] = dict(
            sorted(summary["top_servers"].items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
        )

        return summary

    def get_agent_risk_score(
        self, agent_id: str, time_window: timedelta = timedelta(hours=24)
    ) -> float:
        """Calculate risk score for an agent based on threat history."""
        cutoff = datetime.now() - time_window
        agent_events = [
            e
            for e in self.threat_events
            if e.agent_id == agent_id and e.timestamp > cutoff
        ]

        if not agent_events:
            return 0.0

        # Calculate weighted risk score
        risk_score = 0.0
        weights = {
            ThreatLevel.INFO: 0.1,
            ThreatLevel.LOW: 0.3,
            ThreatLevel.MEDIUM: 0.6,
            ThreatLevel.HIGH: 0.8,
            ThreatLevel.CRITICAL: 1.0,
        }

        for event in agent_events:
            weight = weights[event.threat_level]
            confidence = event.confidence
            risk_score += weight * confidence

        # Normalize by time window and event count
        risk_score = risk_score / max(1, len(agent_events))

        return min(1.0, risk_score)
