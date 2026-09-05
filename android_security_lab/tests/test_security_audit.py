"""
Android Security Lab - Security Audit Tests
"""

import pytest
from app.security.audit import auditor
from app.authorization.devices import device_manager
from app.models import DeviceCreate, DeviceStatus
from app.database import db


class TestSecurityAudit:
    """Test security audit functionality."""
    
    def setup_method(self):
        """Setup test data."""
        self.test_device = DeviceCreate(
            name="Audit Test Device",
            ip_address="192.168.1.101",
            mac_address="11:22:33:44:55:66",
            manufacturer="Test Manufacturer"
        )
    
    def test_run_audit_unauthorized_device(self):
        """Test audit on unauthorized device."""
        device = device_manager.register_device(self.test_device)
        
        audit = auditor.run_security_audit(device.id)
        
        assert audit.score < 100  # Should have findings
        assert len(audit.findings) > 0
    
    def test_run_audit_authorized_device(self):
        """Test audit on authorized device."""
        device = device_manager.register_device(self.test_device)
        pairing = device_manager.initiate_pairing(device.id)
        device_manager.complete_pairing(device.id, pairing["pairing_token"])
        
        audit = auditor.run_security_audit(device.id)
        
        assert audit.score <= 100
        assert isinstance(audit.findings, list)
        assert isinstance(audit.recommendations, list)
    
    def test_security_score_range(self):
        """Test security score is within valid range."""
        device = device_manager.register_device(self.test_device)
        
        audit = auditor.run_security_audit(device.id)
        
        assert 0 <= audit.score <= 100
    
    def test_findings_have_required_fields(self):
        """Test that findings have all required fields."""
        device = device_manager.register_device(self.test_device)
        
        audit = auditor.run_security_audit(device.id)
        
        for finding in audit.findings:
            assert hasattr(finding, 'id')
            assert hasattr(finding, 'severity')
            assert hasattr(finding, 'title')
            assert hasattr(finding, 'description')
            assert hasattr(finding, 'recommendation')
            assert hasattr(finding, 'category')
    
    def test_generate_report(self):
        """Test report generation."""
        device = device_manager.register_device(self.test_device)
        
        report = auditor.generate_report(device.id)
        
        assert report.device_id == device.id
        assert report.device_name == device.name
        assert report.score <= 100
        assert isinstance(report.findings, list)
    
    def test_audit_logged_to_database(self):
        """Test that audit is logged to database."""
        device = device_manager.register_device(self.test_device)
        
        auditor.run_security_audit(device.id)
        
        audits = db.get_device_audits(device.id)
        assert len(audits) >= 1
