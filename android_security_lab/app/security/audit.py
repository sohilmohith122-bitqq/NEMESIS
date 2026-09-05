"""
Android Security Lab - Security Audit

Implements security auditing for devices and the authentication lab.
"""

from datetime import datetime
from typing import Optional
from ..config import get_settings, Severity
from ..models import SecurityAudit, SecurityFinding, SecurityReport
from ..database import db
from ..authorization.devices import device_manager, AuthorizationError
from .authentication_lab import auth_lab
import logging

logger = logging.getLogger(__name__)


class SecurityAuditor:
    """Security audit engine."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def run_security_audit(self, device_id: str) -> SecurityAudit:
        """
        Run comprehensive security audit on a device.
        
        Args:
            device_id: Device ID to audit
            
        Returns:
            SecurityAudit with findings and score
        """
        logger.info(f"Running security audit for device {device_id}")
        
        findings = []
        recommendations = []
        device = None
        
        # Check 1: Device authorization
        try:
            device = device_manager.require_authorized_device(device_id)
            findings.append(SecurityFinding(
                severity=Severity.INFO,
                title="Device Authorization Verified",
                description=f"Device {device.name} is properly authorized.",
                recommendation="Continue using explicit authorization for device access.",
                category="authorization"
            ))
        except AuthorizationError as e:
            findings.append(SecurityFinding(
                severity=Severity.HIGH,
                title="Device Not Authorized",
                description=str(e),
                recommendation="Use the pairing process to explicitly authorize the device.",
                category="authorization"
            ))
        
        # Check 2: Authorization expiry
        if device and device.authorization_expires:
            days_left = (device.authorization_expires - datetime.now()).days
            if days_left < 7:
                findings.append(SecurityFinding(
                    severity=Severity.MEDIUM,
                    title="Authorization Expiring Soon",
                    description=f"Device authorization expires in {days_left} days.",
                    recommendation="Plan to re-authorize the device before expiry.",
                    category="authorization"
                ))
        
        # Check 3: ADB authorization
        if device and device.adb_serial:
            findings.append(SecurityFinding(
                severity=Severity.INFO,
                title="ADB Connection Configured",
                description=f"Device has ADB serial: {device.adb_serial}",
                recommendation="Ensure ADB debugging is only enabled when needed.",
                category="adb"
            ))
        
        # Check 4: Device services
        if device and device.services:
            insecure_services = [s for s in device.services if "insecure" in s.lower() or "http" in s.lower()]
            if insecure_services:
                findings.append(SecurityFinding(
                    severity=Severity.MEDIUM,
                    title="Insecure Services Detected",
                    description=f"Device exposes insecure services: {insecure_services}",
                    recommendation="Disable unnecessary services or use encrypted alternatives.",
                    category="services"
                ))
        
        # Check 5: Authentication lab security
        auth_findings = self._audit_authentication_lab()
        findings.extend(auth_findings)
        
        # Check 6: Configuration audit
        config_findings = self._audit_configuration()
        findings.extend(config_findings)
        
        # Check 7: Logging audit
        logging_findings = self._audit_logging()
        findings.extend(logging_findings)
        
        # Calculate score
        score = self._calculate_score(findings)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(findings)
        
        audit = SecurityAudit(
            device_id=device_id,
            score=score,
            findings=findings,
            recommendations=recommendations
        )
        
        # Save audit to database
        db.create_audit({
            "device_id": device_id,
            "score": score,
            "findings": [f.model_dump() for f in findings],
            "recommendations": recommendations
        })
        
        logger.info(f"Security audit completed for device {device_id}: Score {score}/100")
        
        return audit
    
    def _audit_authentication_lab(self) -> list[SecurityFinding]:
        """Audit the authentication lab for vulnerabilities."""
        findings = []
        
        # Check: Plaintext auth enabled
        findings.append(SecurityFinding(
            severity=Severity.HIGH,
            title="Plaintext Authentication Enabled",
            description="The /auth/plaintext endpoint sends passwords in cleartext.",
            recommendation="Disable plaintext authentication or enforce HTTPS.",
            category="authentication"
        ))
        
        # Check: Hashing without salt
        findings.append(SecurityFinding(
            severity=Severity.MEDIUM,
            title="Hashing Without Salt",
            description="The /auth/hash endpoint uses SHA-256 without salt.",
            recommendation="Use PBKDF2, bcrypt, or Argon2 with proper salting.",
            category="authentication"
        ))
        
        # Check: Rate limiting
        if self.settings.rate_limit_max_attempts > 10:
            findings.append(SecurityFinding(
                severity=Severity.MEDIUM,
                title="Weak Rate Limiting",
                description="Rate limit allows too many attempts before lockout.",
                recommendation="Reduce max attempts to 5 or fewer.",
                category="authentication"
            ))
        
        # Check: Lab mode
        if not self.settings.lab_mode:
            findings.append(SecurityFinding(
                severity=Severity.HIGH,
                title="Lab Mode Disabled",
                description="Safety restrictions are disabled.",
                recommendation="Enable LAB_MODE=true for safety.",
                category="configuration"
            ))
        
        return findings
    
    def _audit_configuration(self) -> list[SecurityFinding]:
        """Audit configuration for security issues."""
        findings = []
        
        # Check: Default API key
        if self.settings.api_key == "dev-key-change-in-production":
            findings.append(SecurityFinding(
                severity=Severity.HIGH,
                title="Default API Key in Use",
                description="Using default development API key.",
                recommendation="Generate and use a unique API key for production.",
                category="configuration"
            ))
        
        # Check: Debug mode
        if self.settings.debug:
            findings.append(SecurityFinding(
                severity=Severity.MEDIUM,
                title="Debug Mode Enabled",
                description="Application is running in debug mode.",
                recommendation="Disable debug mode in production.",
                category="configuration"
            ))
        
        # Check: HTTP vs HTTPS
        if self.settings.auth_lab_port == 8080 or self.settings.auth_lab_port == 80:
            findings.append(SecurityFinding(
                severity=Severity.MEDIUM,
                title="HTTP Service on Standard Port",
                description="Authentication lab running on standard HTTP port.",
                recommendation="Use HTTPS for secure communication.",
                category="configuration"
            ))
        
        return findings
    
    def _audit_logging(self) -> list[SecurityFinding]:
        """Audit logging configuration."""
        findings = []
        
        # Check: Log level
        if self.settings.log_level == "DEBUG":
            findings.append(SecurityFinding(
                severity=Severity.LOW,
                title="Verbose Logging Enabled",
                description="Debug logging may expose sensitive information.",
                recommendation="Use INFO or WARNING level in production.",
                category="logging"
            ))
        
        # Check: Log file
        if not self.settings.log_file:
            findings.append(SecurityFinding(
                severity=Severity.LOW,
                title="No Log File Configured",
                description="Logs may not be persisted for review.",
                recommendation="Configure a log file for audit trail.",
                category="logging"
            ))
        
        return findings
    
    def _calculate_score(self, findings: list[SecurityFinding]) -> int:
        """Calculate security score based on findings."""
        score = 100
        
        for finding in findings:
            if finding.severity == Severity.HIGH:
                score -= 15
            elif finding.severity == Severity.MEDIUM:
                score -= 10
            elif finding.severity == Severity.LOW:
                score -= 5
        
        return max(0, min(100, score))
    
    def _generate_recommendations(self, findings: list[SecurityFinding]) -> list[str]:
        """Generate recommendations based on findings."""
        recommendations = []
        
        high_findings = [f for f in findings if f.severity == Severity.HIGH]
        if high_findings:
            recommendations.append("Address all HIGH severity findings immediately.")
        
        if any(f.category == "authentication" for f in findings):
            recommendations.append("Review and strengthen authentication mechanisms.")
        
        if any(f.category == "configuration" for f in findings):
            recommendations.append("Review application configuration for security best practices.")
        
        if any(f.category == "logging" for f in findings):
            recommendations.append("Improve logging and monitoring.")
        
        return recommendations
    
    def generate_report(self, device_id: str) -> SecurityReport:
        """
        Generate comprehensive security report.
        
        Args:
            device_id: Device ID
            
        Returns:
            SecurityReport with full details
        """
        # Get device info
        device = device_manager.get_device(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        
        # Run audit
        audit = self.run_security_audit(device_id)
        
        return SecurityReport(
            device_id=device_id,
            device_name=device.name,
            authorized=device.status.value == "AUTHORIZED",
            score=audit.score,
            findings=audit.findings,
            recommendations=audit.recommendations
        )


# Singleton instance
auditor = SecurityAuditor()
