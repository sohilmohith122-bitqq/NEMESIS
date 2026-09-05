"""
Android Security Lab - Device Authorization Tests
"""

import pytest
from app.authorization.devices import device_manager, AuthorizationError
from app.models import DeviceCreate, DeviceStatus
from app.database import db


class TestDeviceAuthorization:
    """Test device authorization functionality."""
    
    def setup_method(self):
        """Setup test data."""
        self.test_device = DeviceCreate(
            name="Test Device",
            ip_address="192.168.1.100",
            mac_address="AA:BB:CC:DD:EE:FF",
            manufacturer="Test Manufacturer"
        )
    
    def test_register_device(self):
        """Test device registration."""
        device = device_manager.register_device(self.test_device)
        
        assert device.name == "Test Device"
        assert device.ip_address == "192.168.1.100"
        assert device.status == DeviceStatus.DISCOVERED
    
    def test_get_device(self):
        """Test getting device by ID."""
        device = device_manager.register_device(self.test_device)
        retrieved = device_manager.get_device(device.id)
        
        assert retrieved is not None
        assert retrieved.id == device.id
    
    def test_list_devices(self):
        """Test listing all devices."""
        device_manager.register_device(self.test_device)
        devices = device_manager.list_devices()
        
        assert len(devices) >= 1
    
    def test_initiate_pairing(self):
        """Test pairing initiation."""
        device = device_manager.register_device(self.test_device)
        pairing = device_manager.initiate_pairing(device.id)
        
        assert "pairing_token" in pairing
        assert "expires_in" in pairing
    
    def test_complete_pairing(self):
        """Test completing pairing."""
        device = device_manager.register_device(self.test_device)
        pairing = device_manager.initiate_pairing(device.id)
        
        authorized_device = device_manager.complete_pairing(
            device.id, pairing["pairing_token"]
        )
        
        assert authorized_device.status == DeviceStatus.AUTHORIZED
    
    def test_revoke_device(self):
        """Test device revocation."""
        device = device_manager.register_device(self.test_device)
        device_manager.initiate_pairing(device.id)
        
        success = device_manager.revoke_device(device.id)
        assert success is True
        
        revoked_device = device_manager.get_device(device.id)
        assert revoked_device.status == DeviceStatus.REVOKED
    
    def test_require_authorized_device(self):
        """Test authorization requirement."""
        device = device_manager.register_device(self.test_device)
        
        # Should raise error for non-authorized device
        with pytest.raises(AuthorizationError):
            device_manager.require_authorized_device(device.id)
    
    def test_require_authorized_device_success(self):
        """Test authorization requirement succeeds for authorized device."""
        device = device_manager.register_device(self.test_device)
        pairing = device_manager.initiate_pairing(device.id)
        device_manager.complete_pairing(device.id, pairing["pairing_token"])
        
        # Should not raise error for authorized device
        authorized = device_manager.require_authorized_device(device.id)
        assert authorized.status == DeviceStatus.AUTHORIZED
    
    def test_unauthorized_device_rejection(self):
        """Test that unauthorized devices cannot be managed."""
        device = device_manager.register_device(self.test_device)
        
        # Try to access device info - should fail
        with pytest.raises(AuthorizationError):
            device_manager.require_authorized_device(device.id)
        
        # Verify device is still DISCOVERED
        retrieved = device_manager.get_device(device.id)
        assert retrieved.status == DeviceStatus.DISCOVERED
