"""
Prompt and response security scanner for MCP integration.

Provides real-time scanning of prompts and responses for security threats,
injection attacks, sensitive data exposure, and malicious content.
"""

import asyncio
import hashlib
import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from urllib.parse import urlparse
import base64

from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)


class SecurityScanResult(Enum):
    """Security scan result types."""
    SAFE = "safe"
    WARNING = "warning" 
    THREAT = "threat"
    BLOCKED = "blocked"


class SecurityRiskType(Enum):
    """Types of security risks in prompts/responses."""
    INJECTION_ATTACK = "injection_attack"
    DATA_EXPOSURE = "data_exposure"
    MALICIOUS_CONTENT = "malicious_content"
    SUSPICIOUS_PATTERNS = "suspicious_patterns"
    PRIVACY_VIOLATION = "privacy_violation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    ENCODING_ATTACK = "encoding_attack"


@dataclass
class SecurityViolation:
    """Security violation found in content."""
    risk_type: SecurityRiskType
    severity: float  # 0.0 to 1.0
    description: str
    evidence: str
    pattern: str
    location: str  # prompt/response/parameter
    remediation: Optional[str] = None


@dataclass
class ScanReport:
    """Security scan report."""
    content_id: str
    content_type: str  # prompt/response
    scan_result: SecurityScanResult
    violations: List[SecurityViolation] = field(default_factory=list)
    risk_score: float = 0.0
    scan_timestamp: datetime = field(default_factory=datetime.now)
    scan_duration_ms: float = 0.0
    blocked_content: Optional[str] = None
    sanitized_content: Optional[str] = None


class PromptResponseScanner:
    """
    Advanced security scanner for prompts and responses.
    
    Scans for injection attacks, data exposure, malicious content,
    and compliance violations in MCP communications.
    """
    
    def __init__(self):
        """Initialize prompt/response scanner."""
        self.scan_reports: List[ScanReport] = []
        self.max_reports = 10000
        
        # Security patterns
        self.injection_patterns = {
            'sql_injection': [
                r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|create\s+table)",
                r"(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1|'\s*or\s*'.*'=')",
                r"(?i)(exec\s*\(|execute\s*\(|sp_executesql)",
                r"(?i)(xp_cmdshell|sp_configure|openrowset)",
            ],
            'xss_injection': [
                r"(?i)(<script[^>]*>.*?</script>|javascript:|vbscript:)",
                r"(?i)(on\w+\s*=\s*['\"][^'\"]*['\"]|<iframe|<object|<embed)",
                r"(?i)(eval\s*\(|setTimeout\s*\(|setInterval\s*\()",
                r"(?i)(document\.cookie|window\.location|location\.href)",
            ],
            'command_injection': [
                r"(?i)(;\s*cat\s+|;\s*ls\s+|;\s*rm\s+|;\s*sudo\s+)",
                r"(?i)(\|\s*nc\s+|\|\s*netcat\s+|\|\s*curl\s+|\|\s*wget\s+)",
                r"(?i)(&&\s*rm\s+|&&\s*cat\s+|&&\s*chmod\s+)",
                r"(?i)(`.*`|\$\(.*\)|%%.*%%)",
            ],
            'ldap_injection': [
                r"(?i)(\)\s*\(\||&\s*\(|\|\s*\()",
                r"(?i)(\*\s*\)\s*\(|\(\s*\|\s*\()",
            ],
            'xpath_injection': [
                r"(?i)(and\s+count\s*\(|or\s+count\s*\()",
                r"(?i)(\[\s*position\s*\(|\[\s*last\s*\()",
            ],
            'template_injection': [
                r"(?i)(\{\{.*\}\}|\{%.*%\}|\$\{.*\})",
                r"(?i)(<%.*%>|<?.*?>)",
                r"(?i)(__import__|getattr|setattr|delattr)",
            ],
            'code_injection': [
                r"(?i)(eval\s*\(|exec\s*\(|compile\s*\()",
                r"(?i)(__import__\s*\(|importlib\.|globals\s*\(\))",
                r"(?i)(subprocess\.|os\.system|os\.popen)",
                r"(?i)(pickle\.loads|marshal\.loads|dill\.loads)",
            ]
        }
        
        self.data_exposure_patterns = {
            'credentials': [
                r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{6,}",
                r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}",
                r"(?i)(secret[_-]?key|secretkey)\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}",
                r"(?i)(access[_-]?token|accesstoken)\s*[:=]\s*['\"]?[a-zA-Z0-9]{20,}",
                r"(?i)(bearer\s+[a-zA-Z0-9]{20,}|token\s*[:=]\s*['\"]?[a-zA-Z0-9]{20,})",
            ],
            'private_keys': [
                r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
                r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----",
                r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----",
                r"-----BEGIN\s+DSA\s+PRIVATE\s+KEY-----",
            ],
            'database_info': [
                r"(?i)(database|db)[_\s]*[:=]\s*['\"]?[\w\-\.]+['\"]?",
                r"(?i)(server|host)[_\s]*[:=]\s*['\"]?[\w\-\.]+['\"]?",
                r"(?i)(port)[_\s]*[:=]\s*['\"]?\d{1,5}['\"]?",
                r"(?i)(connection[_\s]*string|conn[_\s]*str)",
            ],
            'personal_info': [
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
                r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",  # Credit card
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
                r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # Phone
            ],
            'aws_credentials': [
                r"(?i)AKIA[0-9A-Z]{16}",  # AWS Access Key
                r"(?i)[a-zA-Z0-9/+=]{40}",  # AWS Secret Key pattern
                r"(?i)aws[_\s]*secret[_\s]*access[_\s]*key",
            ],
            'github_tokens': [
                r"(?i)ghp_[a-zA-Z0-9]{36}",  # GitHub Personal Access Token
                r"(?i)ghs_[a-zA-Z0-9]{36}",  # GitHub Server Token
                r"(?i)ghr_[a-zA-Z0-9]{36}",  # GitHub Refresh Token
            ]
        }
        
        self.malicious_patterns = {
            'suspicious_urls': [
                r"(?i)(bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly)/\w+",
                r"(?i)(download|install|execute|run)[_\s]*(malware|virus|trojan)",
                r"(?i)(phishing|scam|fake|fraud)",
            ],
            'suspicious_domains': [
                r"(?i)\b[\w\-]+\.(tk|ml|ga|cf|cc)\b",  # Suspicious TLDs
                r"(?i)\b[\w\-]+(admin|login|secure|bank|paypal)[\w\-]*\.(com|net|org)\b",
            ],
            'suspicious_content': [
                r"(?i)(click\s+here|download\s+now|limited\s+time|act\s+now)",
                r"(?i)(congratulations|winner|prize|lottery|jackpot)",
                r"(?i)(urgent|immediate|expire|suspend|verify\s+account)",
            ],
            'malware_indicators': [
                r"(?i)(rootkit|keylogger|backdoor|trojan|ransomware)",
                r"(?i)(payload|shellcode|exploit|vulnerability)",
                r"(?i)(c2|command\s+and\s+control|botnet)",
            ]
        }
        
        self.encoding_patterns = {
            'base64_suspicious': [
                r"[A-Za-z0-9+/=]{50,}",  # Long base64 strings
            ],
            'hex_suspicious': [
                r"(?i)(0x)?[a-f0-9]{40,}",  # Long hex strings
            ],
            'url_encoding': [
                r"(%[0-9a-fA-F]{2}){10,}",  # Excessive URL encoding
            ],
            'unicode_evasion': [
                r"\\u[0-9a-fA-F]{4}",  # Unicode escapes
                r"\\x[0-9a-fA-F]{2}",  # Hex escapes
            ]
        }
        
        # Compliance patterns
        self.compliance_patterns = {
            'gdpr_violations': [
                r"(?i)(personal\s+data|pii|personally\s+identifiable)",
                r"(?i)(process|store|collect).*personal.*data",
            ],
            'hipaa_violations': [
                r"(?i)(medical|health|patient).*record",
                r"(?i)(phi|protected\s+health\s+information)",
            ],
            'pci_violations': [
                r"(?i)(card\s+number|credit\s+card|payment\s+card)",
                r"(?i)(cvv|cvc|card\s+verification)",
            ]
        }
        
        # Trusted domains and patterns (whitelist)
        self.trusted_patterns = {
            'domains': [
                r"(?i)\b[\w\-]+\.(github|gitlab|bitbucket|stackoverflow|docs\.python|docs\.microsoft)\.com\b",
                r"(?i)\b[\w\-]+\.(python|nodejs|rust-lang|golang)\.org\b",
            ],
            'safe_encodings': [
                r"data:image/(png|jpg|jpeg|gif|svg\+xml);base64,",  # Image data URLs
            ]
        }
    
    async def scan_prompt(self, agent_id: str, prompt: str, context: Optional[Dict[str, Any]] = None) -> ScanReport:
        """
        Scan a prompt for security issues.
        
        Args:
            agent_id: Agent ID sending the prompt
            prompt: Prompt content to scan
            context: Additional context for scanning
            
        Returns:
            Scan report with findings
        """
        start_time = datetime.now()
        content_id = self._generate_content_id(agent_id, prompt, "prompt")
        
        violations = []
        
        # Scan for injection attacks
        injection_violations = await self._scan_injection_patterns(prompt, "prompt")
        violations.extend(injection_violations)
        
        # Scan for data exposure
        exposure_violations = await self._scan_data_exposure(prompt, "prompt")
        violations.extend(exposure_violations)
        
        # Scan for malicious content
        malicious_violations = await self._scan_malicious_patterns(prompt, "prompt")
        violations.extend(malicious_violations)
        
        # Scan for encoding attacks
        encoding_violations = await self._scan_encoding_attacks(prompt, "prompt")
        violations.extend(encoding_violations)
        
        # Scan for compliance violations
        compliance_violations = await self._scan_compliance_patterns(prompt, "prompt")
        violations.extend(compliance_violations)
        
        # Calculate risk score and determine result
        risk_score = self._calculate_risk_score(violations)
        scan_result = self._determine_scan_result(risk_score, violations)
        
        # Generate sanitized content if needed
        sanitized_content = None
        blocked_content = None
        
        if scan_result == SecurityScanResult.BLOCKED:
            blocked_content = prompt
        elif scan_result in [SecurityScanResult.THREAT, SecurityScanResult.WARNING]:
            sanitized_content = await self._sanitize_content(prompt, violations)
        
        # Create scan report
        scan_duration = (datetime.now() - start_time).total_seconds() * 1000
        
        report = ScanReport(
            content_id=content_id,
            content_type="prompt",
            scan_result=scan_result,
            violations=violations,
            risk_score=risk_score,
            scan_duration_ms=scan_duration,
            blocked_content=blocked_content,
            sanitized_content=sanitized_content
        )
        
        # Store report
        self.scan_reports.append(report)
        if len(self.scan_reports) > self.max_reports:
            self.scan_reports = self.scan_reports[-self.max_reports:]
        
        if violations:
            logger.warning(f"Security violations found in prompt from {agent_id}: {len(violations)} violations")
        
        return report
    
    async def scan_response(self, agent_id: str, response: str, context: Optional[Dict[str, Any]] = None) -> ScanReport:
        """
        Scan a response for security issues.
        
        Args:
            agent_id: Agent ID receiving the response
            response: Response content to scan
            context: Additional context for scanning
            
        Returns:
            Scan report with findings
        """
        start_time = datetime.now()
        content_id = self._generate_content_id(agent_id, response, "response")
        
        violations = []
        
        # Focus on data exposure for responses
        exposure_violations = await self._scan_data_exposure(response, "response")
        violations.extend(exposure_violations)
        
        # Scan for malicious content in responses
        malicious_violations = await self._scan_malicious_patterns(response, "response")
        violations.extend(malicious_violations)
        
        # Scan for compliance violations
        compliance_violations = await self._scan_compliance_patterns(response, "response")
        violations.extend(compliance_violations)
        
        # Scan for suspicious patterns that might indicate compromise
        suspicious_violations = await self._scan_suspicious_response_patterns(response, "response")
        violations.extend(suspicious_violations)
        
        # Calculate risk score and determine result
        risk_score = self._calculate_risk_score(violations)
        scan_result = self._determine_scan_result(risk_score, violations)
        
        # Generate sanitized content if needed
        sanitized_content = None
        blocked_content = None
        
        if scan_result == SecurityScanResult.BLOCKED:
            blocked_content = response
        elif scan_result in [SecurityScanResult.THREAT, SecurityScanResult.WARNING]:
            sanitized_content = await self._sanitize_content(response, violations)
        
        # Create scan report
        scan_duration = (datetime.now() - start_time).total_seconds() * 1000
        
        report = ScanReport(
            content_id=content_id,
            content_type="response",
            scan_result=scan_result,
            violations=violations,
            risk_score=risk_score,
            scan_duration_ms=scan_duration,
            blocked_content=blocked_content,
            sanitized_content=sanitized_content
        )
        
        # Store report
        self.scan_reports.append(report)
        if len(self.scan_reports) > self.max_reports:
            self.scan_reports = self.scan_reports[-self.max_reports:]
        
        if violations:
            logger.warning(f"Security violations found in response to {agent_id}: {len(violations)} violations")
        
        return report
    
    async def _scan_injection_patterns(self, content: str, location: str) -> List[SecurityViolation]:
        """Scan for injection attack patterns."""
        violations = []
        
        for attack_type, patterns in self.injection_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    # Check if this is a false positive
                    if self._is_false_positive(match.group(), content, attack_type):
                        continue
                    
                    violation = SecurityViolation(
                        risk_type=SecurityRiskType.INJECTION_ATTACK,
                        severity=self._get_injection_severity(attack_type),
                        description=f"Potential {attack_type.replace('_', ' ')} detected",
                        evidence=match.group(),
                        pattern=pattern,
                        location=location,
                        remediation=f"Remove or sanitize {attack_type.replace('_', ' ')} patterns"
                    )
                    violations.append(violation)
        
        return violations
    
    async def _scan_data_exposure(self, content: str, location: str) -> List[SecurityViolation]:
        """Scan for sensitive data exposure."""
        violations = []
        
        for data_type, patterns in self.data_exposure_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    # Check if this is in a trusted context
                    if self._is_trusted_context(match.group(), content):
                        continue
                    
                    violation = SecurityViolation(
                        risk_type=SecurityRiskType.DATA_EXPOSURE,
                        severity=self._get_data_exposure_severity(data_type),
                        description=f"Potential {data_type.replace('_', ' ')} exposure",
                        evidence=self._mask_sensitive_data(match.group()),
                        pattern=pattern,
                        location=location,
                        remediation=f"Remove or mask {data_type.replace('_', ' ')}"
                    )
                    violations.append(violation)
        
        return violations
    
    async def _scan_malicious_patterns(self, content: str, location: str) -> List[SecurityViolation]:
        """Scan for malicious content patterns."""
        violations = []
        
        for malware_type, patterns in self.malicious_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    violation = SecurityViolation(
                        risk_type=SecurityRiskType.MALICIOUS_CONTENT,
                        severity=self._get_malicious_severity(malware_type),
                        description=f"Potential {malware_type.replace('_', ' ')} detected",
                        evidence=match.group(),
                        pattern=pattern,
                        location=location,
                        remediation=f"Remove {malware_type.replace('_', ' ')} content"
                    )
                    violations.append(violation)
        
        return violations
    
    async def _scan_encoding_attacks(self, content: str, location: str) -> List[SecurityViolation]:
        """Scan for encoding-based attacks."""
        violations = []
        
        for encoding_type, patterns in self.encoding_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    # Check if this is a legitimate encoding
                    if self._is_legitimate_encoding(match.group(), content, encoding_type):
                        continue
                    
                    violation = SecurityViolation(
                        risk_type=SecurityRiskType.ENCODING_ATTACK,
                        severity=self._get_encoding_severity(encoding_type),
                        description=f"Suspicious {encoding_type.replace('_', ' ')} detected",
                        evidence=match.group()[:100] + "..." if len(match.group()) > 100 else match.group(),
                        pattern=pattern,
                        location=location,
                        remediation=f"Validate and decode {encoding_type.replace('_', ' ')}"
                    )
                    violations.append(violation)
        
        return violations
    
    async def _scan_compliance_patterns(self, content: str, location: str) -> List[SecurityViolation]:
        """Scan for compliance violations."""
        violations = []
        
        for compliance_type, patterns in self.compliance_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    violation = SecurityViolation(
                        risk_type=SecurityRiskType.COMPLIANCE_VIOLATION,
                        severity=0.7,  # High severity for compliance
                        description=f"Potential {compliance_type.replace('_', ' ')} violation",
                        evidence=match.group(),
                        pattern=pattern,
                        location=location,
                        remediation=f"Review for {compliance_type.replace('_', ' ')} compliance"
                    )
                    violations.append(violation)
        
        return violations
    
    async def _scan_suspicious_response_patterns(self, content: str, location: str) -> List[SecurityViolation]:
        """Scan for suspicious patterns in responses that might indicate compromise."""
        violations = []
        
        # Check for error messages that reveal system information
        error_patterns = [
            r"(?i)(sql\s+error|mysql\s+error|oracle\s+error|postgresql\s+error)",
            r"(?i)(stack\s+trace|exception\s+in|fatal\s+error)",
            r"(?i)(internal\s+server\s+error|debug\s+info|traceback)",
            r"(?i)(root@|admin@|system@|user@[\w\-\.]+)",
            r"(?i)(c:\\|/etc/|/var/|/home/|/root/)",
        ]
        
        for pattern in error_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                violation = SecurityViolation(
                    risk_type=SecurityRiskType.SUSPICIOUS_PATTERNS,
                    severity=0.6,
                    description="Suspicious error pattern that may reveal system information",
                    evidence=match.group(),
                    pattern=pattern,
                    location=location,
                    remediation="Review error handling and information disclosure"
                )
                violations.append(violation)
        
        return violations
    
    def _generate_content_id(self, agent_id: str, content: str, content_type: str) -> str:
        """Generate unique content ID for tracking."""
        timestamp = datetime.now().isoformat()
        data = f"{agent_id}:{content_type}:{timestamp}:{len(content)}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _get_injection_severity(self, attack_type: str) -> float:
        """Get severity score for injection attack type."""
        severity_map = {
            'sql_injection': 0.9,
            'command_injection': 0.95,
            'code_injection': 0.95,
            'xss_injection': 0.7,
            'template_injection': 0.8,
            'ldap_injection': 0.6,
            'xpath_injection': 0.6,
        }
        return severity_map.get(attack_type, 0.7)
    
    def _get_data_exposure_severity(self, data_type: str) -> float:
        """Get severity score for data exposure type."""
        severity_map = {
            'credentials': 0.95,
            'private_keys': 1.0,
            'aws_credentials': 0.9,
            'github_tokens': 0.8,
            'database_info': 0.7,
            'personal_info': 0.8,
        }
        return severity_map.get(data_type, 0.6)
    
    def _get_malicious_severity(self, malware_type: str) -> float:
        """Get severity score for malicious content type."""
        severity_map = {
            'malware_indicators': 0.9,
            'suspicious_urls': 0.7,
            'suspicious_domains': 0.6,
            'suspicious_content': 0.5,
        }
        return severity_map.get(malware_type, 0.5)
    
    def _get_encoding_severity(self, encoding_type: str) -> float:
        """Get severity score for encoding attack type."""
        severity_map = {
            'base64_suspicious': 0.6,
            'hex_suspicious': 0.5,
            'url_encoding': 0.7,
            'unicode_evasion': 0.8,
        }
        return severity_map.get(encoding_type, 0.5)
    
    def _is_false_positive(self, match: str, content: str, attack_type: str) -> bool:
        """Check if a match is likely a false positive."""
        # Check for common false positives
        if attack_type == "sql_injection":
            # Common words that might trigger false positives
            if re.search(r"(?i)(select\s+option|from\s+scratch|insert\s+mode)", match):
                return True
        
        return False
    
    def _is_trusted_context(self, match: str, content: str) -> bool:
        """Check if a match is in a trusted context."""
        # Check for trusted domains
        for pattern in self.trusted_patterns['domains']:
            if re.search(pattern, content):
                return True
        
        # Check for documentation or example contexts
        if re.search(r"(?i)(example|demo|test|documentation|tutorial)", content):
            return True
        
        return False
    
    def _is_legitimate_encoding(self, match: str, content: str, encoding_type: str) -> bool:
        """Check if encoding is legitimate."""
        if encoding_type == "base64_suspicious":
            # Check for legitimate base64 usage
            for pattern in self.trusted_patterns['safe_encodings']:
                if re.search(pattern, content):
                    return True
        
        return False
    
    def _mask_sensitive_data(self, data: str) -> str:
        """Mask sensitive data for evidence."""
        if len(data) <= 8:
            return "*" * len(data)
        
        return data[:4] + "*" * (len(data) - 8) + data[-4:]
    
    def _calculate_risk_score(self, violations: List[SecurityViolation]) -> float:
        """Calculate overall risk score from violations."""
        if not violations:
            return 0.0
        
        # Weight violations by severity and type
        risk_weights = {
            SecurityRiskType.INJECTION_ATTACK: 1.0,
            SecurityRiskType.DATA_EXPOSURE: 0.9,
            SecurityRiskType.MALICIOUS_CONTENT: 0.8,
            SecurityRiskType.COMPLIANCE_VIOLATION: 0.7,
            SecurityRiskType.ENCODING_ATTACK: 0.6,
            SecurityRiskType.SUSPICIOUS_PATTERNS: 0.5,
            SecurityRiskType.PRIVACY_VIOLATION: 0.7,
        }
        
        total_risk = 0.0
        for violation in violations:
            weight = risk_weights.get(violation.risk_type, 0.5)
            total_risk += violation.severity * weight
        
        # Normalize by number of violations (diminishing returns)
        normalized_risk = total_risk / (1 + len(violations) * 0.1)
        
        return min(1.0, normalized_risk)
    
    def _determine_scan_result(self, risk_score: float, violations: List[SecurityViolation]) -> SecurityScanResult:
        """Determine scan result based on risk score and violations."""
        # Check for critical violations that should be blocked immediately
        critical_types = {SecurityRiskType.INJECTION_ATTACK, SecurityRiskType.DATA_EXPOSURE}
        critical_violations = [v for v in violations if v.risk_type in critical_types and v.severity >= 0.8]
        
        if critical_violations:
            return SecurityScanResult.BLOCKED
        elif risk_score >= 0.8:
            return SecurityScanResult.THREAT
        elif risk_score >= 0.5:
            return SecurityScanResult.WARNING
        else:
            return SecurityScanResult.SAFE
    
    async def _sanitize_content(self, content: str, violations: List[SecurityViolation]) -> str:
        """Sanitize content by removing or masking violations."""
        sanitized = content
        
        for violation in violations:
            if violation.risk_type in {SecurityRiskType.INJECTION_ATTACK, SecurityRiskType.MALICIOUS_CONTENT}:
                # Remove malicious patterns
                sanitized = re.sub(violation.pattern, "[REMOVED_SUSPICIOUS_CONTENT]", sanitized, flags=re.IGNORECASE)
            elif violation.risk_type == SecurityRiskType.DATA_EXPOSURE:
                # Mask sensitive data
                sanitized = re.sub(violation.pattern, "[MASKED_SENSITIVE_DATA]", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def get_scan_statistics(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get scanning statistics."""
        if time_window:
            cutoff = datetime.now() - time_window
            reports = [r for r in self.scan_reports if r.scan_timestamp > cutoff]
        else:
            reports = self.scan_reports
        
        if not reports:
            return {"total_scans": 0}
        
        stats = {
            "total_scans": len(reports),
            "scan_results": {},
            "violation_types": {},
            "average_risk_score": 0.0,
            "average_scan_time_ms": 0.0,
            "total_violations": 0,
            "blocked_content_count": 0,
            "sanitized_content_count": 0,
        }
        
        total_risk = 0.0
        total_scan_time = 0.0
        total_violations = 0
        
        for report in reports:
            # Count scan results
            result = report.scan_result.value
            stats["scan_results"][result] = stats["scan_results"].get(result, 0) + 1
            
            # Count violations
            total_violations += len(report.violations)
            for violation in report.violations:
                vtype = violation.risk_type.value
                stats["violation_types"][vtype] = stats["violation_types"].get(vtype, 0) + 1
            
            # Accumulate metrics
            total_risk += report.risk_score
            total_scan_time += report.scan_duration_ms
            
            if report.blocked_content:
                stats["blocked_content_count"] += 1
            if report.sanitized_content:
                stats["sanitized_content_count"] += 1
        
        stats["average_risk_score"] = total_risk / len(reports)
        stats["average_scan_time_ms"] = total_scan_time / len(reports)
        stats["total_violations"] = total_violations
        
        return stats
    
    def get_agent_security_profile(self, agent_id: str, time_window: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """Get security profile for a specific agent."""
        cutoff = datetime.now() - time_window
        
        # Find reports for this agent (need to track agent_id in reports)
        # This would require modifying the scan methods to store agent_id
        # For now, return a placeholder
        
        return {
            "agent_id": agent_id,
            "time_window_hours": time_window.total_seconds() / 3600,
            "total_scans": 0,
            "violation_count": 0,
            "risk_score": 0.0,
            "security_status": "unknown"
        }