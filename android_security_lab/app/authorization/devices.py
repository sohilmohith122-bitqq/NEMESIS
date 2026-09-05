"""
Android Security Lab - Device Authorization

Explicit authorization system for devices.
Devices must be explicitly paired and authorized before use.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from ..config import get_settings
from ..models import Device, DeviceCreate, DevicePair, DeviceStatus
from ..database import db
import logging

logger = logging.getLogger(__name__)


class AuthorizationError(Exception):
    """Raised when device is not authorized."""
    pass


class DeviceManager:
    """Device management and authorization."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def register_device(self, device_data: DeviceCreate) -> Device:
        """
        Register a newly discovered device.
        
        Args:
            device_data: Device information from network discovery
            
        Returns:
            Registered device with DISCOVERED status
        """
        device_dict = device_data.model_dump()
        device_dict["status"] = DeviceStatus.DISCOVERED
        
        # Create device in database
        db_device = db.create_device(device_dict)
        
        device = Device(
            id=db_device.id,
            name=db_device.name,
            ip_address=db_device.ip_address,
            mac_address=db_device.mac_address,
            manufacturer=db_device.manufacturer,
            status=DeviceStatus(db_device.status),
            services=db_device.services or []
        )
        
        logger.info(f"Device registered: {device.id} ({device.name}) at {device.ip_address}")
        return device
    
    def initiate_pairing(self, device_id: str) -> dict:
        """
        Initiate pairing process for a device.
        
        Args:
            device_id: Device ID to pair
            
        Returns:
            Pairing information including token and QR code data
        """
        device = db.get_device(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        
        if device.status == DeviceStatus.AUTHORIZED:
            raise ValueError(f"Device already authorized: {device_id}")
        
        # Generate pairing token
        pairing_token = secrets.token_urlsafe(32)
        token_expires = datetime.now() + timedelta(seconds=self.settings.pairing_token_expiry)
        
        # Generate QR code data (for mobile app scanning)
        qr_data = {
            "device_id": device_id,
            "token": pairing_token,
            "lab_name": self.settings.app_name,
            "expires": token_expires.isoformat()
        }
        
        # Update device status
        db.update_device(device_id, {
            "status": DeviceStatus.PAIRING,
            "pairing_token": pairing_token,
            "pairing_token_expires": token_expires
        })
        
        logger.info(f"Pairing initiated for device {device_id}")
        
        return {
            "device_id": device_id,
            "pairing_token": pairing_token,
            "qr_data": qr_data,
            "expires_in": self.settings.pairing_token_expiry,
            "expires_at": token_expires
        }
    
    def complete_pairing(self, device_id: str, pairing_token: str, public_key: Optional[str] = None) -> Device:
        """
        Complete device pairing with token verification.
        
        Args:
            device_id: Device ID
            pairing_token: Token from pairing initiation
            public_key: Optional public key for secure communication
            
        Returns:
            Authorized device
        """
        device = db.get_device(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")
        
        if device.status != DeviceStatus.PAIRING:
            raise ValueError(f"Device is not in pairing state: {device.status}")
        
        # Verify pairing token
        if device.pairing_token != pairing_token:
            raise ValueError("Invalid pairing token")
        
        # Check token expiry
        if device.pairing_token_expires and device.pairing_token_expires < datetime.now():
            raise ValueError("Pairing token has expired")
        
        # Generate authorization key
        auth_key = secrets.token_urlsafe(32)
        
        # Update device to authorized
        authorized_at = datetime.now()
        authorization_expires = authorized_at + timedelta(seconds=self.settings.authorization_expiry)
        
        db.update_device(device_id, {
            "status": DeviceStatus.AUTHORIZED,
            "authorized_at": authorized_at,
            "authorization_expires": authorization_expires,
            "pairing_token": None,  # Clear pairing token
            "pairing_token_expires": None,
            "public_key": public_key
        })
        
        device = db.get_device(device_id)
        
        logger.info(f"Device authorized: {device_id}")
        
        return Device(
            id=device.id,
            name=device.name,
            ip_address=device.ip_address,
            mac_address=device.mac_address,
            manufacturer=device.manufacturer,
            status=DeviceStatus(device.status),
            services=device.services or [],
            adb_serial=device.adb_serial,
            authorized_at=device.authorized_at,
            authorization_expires=device.authorization_expires,
            public_key=device.public_key
        )
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID."""
        db_device = db.get_device(device_id)
        if not db_device:
            return None
        
        return Device(
            id=db_device.id,
            name=db_device.name,
            ip_address=db_device.ip_address,
            mac_address=db_device.mac_address,
            manufacturer=db_device.manufacturer,
            status=DeviceStatus(db_device.status),
            services=db_device.services or [],
            adb_serial=db_device.adb_serial,
            last_seen=db_device.last_seen,
            authorized_at=db_device.authorized_at,
            authorization_expires=db_device.authorization_expires,
            public_key=db_device.public_key
        )
    
    def list_devices(self) -> list[Device]:
        """List all registered devices."""
        db_devices = db.get_all_devices()
        
        devices = []
        for db_device in db_devices:
            devices.append(Device(
                id=db_device.id,
                name=db_device.name,
                ip_address=db_device.ip_address,
                mac_address=db_device.mac_address,
                manufacturer=db_device.manufacturer,
                status=DeviceStatus(db_device.status),
                services=db_device.services or [],
                adb_serial=db_device.adb_serial,
                last_seen=db_device.last_seen,
                authorized_at=db_device.authorized_at,
                authorization_expires=db_device.authorization_expires,
                public_key=db_device.public_key
            ))
        
        return devices
    
    def revoke_device(self, device_id: str) -> bool:
        """Revoke device authorization."""
        device = db.get_device(device_id)
        if not device:
            return False
        
        db.update_device(device_id, {
            "status": DeviceStatus.REVOKED,
            "authorization_expires": None
        })
        
        logger.info(f"Device authorization revoked: {device_id}")
        return True
    
    def require_authorized_device(self, device_id: str) -> Device:
        """
        Require that a device is explicitly authorized.
        
        Args:
            device_id: Device ID to check
            
        Returns:
            Authorized device
            
        Raises:
            AuthorizationError: If device is not authorized
        """
        device = db.get_device(device_id)
        
        if not device:
            raise AuthorizationError(f"Device not found: {device_id}")
        
        if device.status != DeviceStatus.AUTHORIZED:
            raise AuthorizationError(
                f"Device is not explicitly authorized for laboratory testing. "
                f"Current status: {device.status}"
            )
        
        # Check authorization expiry
        if device.authorization_expires and device.authorization_expires < datetime.now():
            db.update_device(device_id, {"status": DeviceStatus.REVOKED})
            raise AuthorizationError(
                "Device authorization has expired. Please re-pair the device."
            )
        
        return Device(
            id=device.id,
            name=device.name,
            ip_address=device.ip_address,
            mac_address=device.mac_address,
            manufacturer=device.manufacturer,
            status=DeviceStatus(device.status),
            services=device.services or [],
            adb_serial=device.adb_serial,
            authorized_at=device.authorized_at,
            authorization_expires=device.authorization_expires,
            public_key=device.public_key
        )
    
    def generate_device_id(self) -> str:
        """Generate a unique device ID."""
        return secrets.token_hex(4)


# Singleton instance
device_manager = DeviceManager()
