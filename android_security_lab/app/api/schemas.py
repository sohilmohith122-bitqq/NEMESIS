"""
Android Security Lab - API Schemas

Pydantic models for API request/response schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from ..models import DeviceStatus, Severity


# Request Schemas
class DevicePairRequest(BaseModel):
    """Device pairing request."""
    pairing_token: str
    public_key: Optional[str] = None


class AuditRequest(BaseModel):
    """Security audit request."""
    device_id: str


# Response Schemas
class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    lab_mode: bool
    timestamp: datetime = Field(default_factory=datetime.now)


class DeviceResponse(BaseModel):
    """Device information response."""
    id: str
    name: str
    ip_address: str
    mac_address: Optional[str] = None
    manufacturer: Optional[str] = None
    status: DeviceStatus
    services: list[str] = []
    adb_serial: Optional[str] = None
    last_seen: datetime
    authorized_at: Optional[datetime] = None
    authorization_expires: Optional[datetime] = None


class DeviceListResponse(BaseModel):
    """Device list response."""
    devices: list[DeviceResponse]
    total: int


class PairingResponse(BaseModel):
    """Pairing response."""
    device_id: str
    status: DeviceStatus
    pairing_token: str
    expires_in: int
    qr_data: dict


class BatteryResponse(BaseModel):
    """Battery information response."""
    device_id: str
    level: int
    status: str
    temperature: Optional[float] = None
    voltage: Optional[float] = None


class NetworkResponse(BaseModel):
    """Network information response."""
    device_id: str
    wifi_enabled: bool
    connected: bool
    ssid: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None


class SecurityFindingResponse(BaseModel):
    """Security finding response."""
    id: str
    severity: Severity
    title: str
    description: str
    recommendation: str
    category: str


class AuditResponse(BaseModel):
    """Security audit response."""
    device_id: str
    timestamp: datetime
    score: int
    findings: list[SecurityFindingResponse]
    recommendations: list[str]


class ReportResponse(BaseModel):
    """Security report response."""
    device_id: str
    device_name: str
    timestamp: datetime
    authorized: bool
    score: int
    findings: list[SecurityFindingResponse]
    recommendations: list[str]
    json_report_path: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


class ScanResponse(BaseModel):
    """Network scan response."""
    cidr: str
    devices: list[dict]
    scan_time: datetime
    duration: float
