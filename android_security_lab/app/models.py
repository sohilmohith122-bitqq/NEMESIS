"""
Android Security Lab - Data Models

Pydantic models for request/response schemas and database models.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class DeviceStatus(str, Enum):
    """Device authorization status."""
    DISCOVERED = "DISCOVERED"
    PAIRING = "PAIRING"
    AUTHORIZED = "AUTHORIZED"
    REVOKED = "REVOKED"


class Severity(str, Enum):
    """Security finding severity levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# Device Models
class Device(BaseModel):
    """Device information model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    ip_address: str
    mac_address: Optional[str] = None
    manufacturer: Optional[str] = None
    status: DeviceStatus = DeviceStatus.DISCOVERED
    services: list[str] = Field(default_factory=list)
    adb_serial: Optional[str] = None
    last_seen: datetime = Field(default_factory=datetime.now)
    authorized_at: Optional[datetime] = None
    authorization_expires: Optional[datetime] = None
    pairing_token: Optional[str] = None
    pairing_token_expires: Optional[datetime] = None
    public_key: Optional[str] = None


class DeviceCreate(BaseModel):
    """Model for creating a new device."""
    name: str
    ip_address: str
    mac_address: Optional[str] = None
    manufacturer: Optional[str] = None
    services: list[str] = Field(default_factory=list)


class DevicePair(BaseModel):
    """Model for device pairing request."""
    device_id: str
    pairing_token: str
    public_key: Optional[str] = None


# Network Discovery Models
class NetworkDevice(BaseModel):
    """Network discovery result."""
    ip_address: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    manufacturer: Optional[str] = None
    services: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class ScanResult(BaseModel):
    """Network scan result."""
    cidr: str
    devices: list[NetworkDevice] = Field(default_factory=list)
    scan_time: datetime = Field(default_factory=datetime.now)
    duration: float = 0.0


# ADB Models
class DeviceInfo(BaseModel):
    """ADB device information."""
    serial: str
    model: str
    manufacturer: str
    android_version: str
    sdk_version: str
    security_patch: str
    is_emulator: bool = False


class BatteryInfo(BaseModel):
    """Battery status information."""
    level: int
    status: str  # Charging, Discharging, Full, etc.
    temperature: Optional[float] = None
    voltage: Optional[float] = None


class NetworkInfo(BaseModel):
    """Network information from device."""
    wifi_enabled: bool
    connected: bool
    ssid: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None


# Security Audit Models
class SecurityFinding(BaseModel):
    """Security audit finding."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity: Severity
    title: str
    description: str
    recommendation: str
    category: str


class SecurityAudit(BaseModel):
    """Security audit result."""
    device_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    score: int = Field(ge=0, le=100)
    findings: list[SecurityFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class SecurityReport(BaseModel):
    """Security report model."""
    device_id: str
    device_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    authorized: bool
    score: int
    findings: list[SecurityFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# API Models
class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    lab_mode: bool
    timestamp: datetime = Field(default_factory=datetime.now)


class PairingResponse(BaseModel):
    """Pairing response."""
    device_id: str
    status: DeviceStatus
    pairing_token: str
    expires_in: int


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


# Authentication Lab Models
class AuthAttempt(BaseModel):
    """Authentication attempt log."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    username: str
    success: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuthTestResult(BaseModel):
    """Authentication test result."""
    test_name: str
    passed: bool
    description: str
    findings: list[str] = Field(default_factory=list)
