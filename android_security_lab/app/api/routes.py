"""
Android Security Lab - API Routes

FastAPI endpoints for device management and security operations.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from ..config import get_settings
from ..models import DeviceCreate, DevicePair
from ..authorization.devices import device_manager, AuthorizationError
from ..android.adb import adb_manager, ADBError
from ..discovery.scanner import scanner
from ..security.audit import auditor
from ..security.report import report_generator
from ..security.authentication_lab import auth_lab
from .schemas import (
    HealthResponse, DeviceResponse, DeviceListResponse,
    PairingResponse, BatteryResponse, NetworkResponse,
    AuditResponse, ReportResponse, ErrorResponse,
    DevicePairRequest, ScanResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key for protected endpoints."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        version=settings.app_version,
        lab_mode=settings.lab_mode,
        timestamp=datetime.now()
    )


@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(api_key: str = Depends(verify_api_key)):
    """List all registered devices."""
    devices = device_manager.list_devices()
    return DeviceListResponse(
        devices=[
            DeviceResponse(
                id=d.id,
                name=d.name,
                ip_address=d.ip_address,
                mac_address=d.mac_address,
                manufacturer=d.manufacturer,
                status=d.status,
                services=d.services,
                adb_serial=d.adb_serial,
                last_seen=d.last_seen,
                authorized_at=d.authorized_at,
                authorization_expires=d.authorization_expires
            )
            for d in devices
        ],
        total=len(devices)
    )


@router.post("/devices/{device_id}/pair", response_model=PairingResponse)
async def pair_device(
    device_id: str,
    request: DevicePairRequest,
    api_key: str = Depends(verify_api_key)
):
    """Complete device pairing with token."""
    try:
        device = device_manager.complete_pairing(
            device_id=device_id,
            pairing_token=request.pairing_token,
            public_key=request.public_key
        )
        
        return PairingResponse(
            device_id=device.id,
            status=device.status,
            pairing_token=request.pairing_token,
            expires_in=settings.authorization_expiry,
            qr_data={"device_id": device.id, "status": device.status.value}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get device information."""
    device = device_manager.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return DeviceResponse(
        id=device.id,
        name=device.name,
        ip_address=device.ip_address,
        mac_address=device.mac_address,
        manufacturer=device.manufacturer,
        status=device.status,
        services=device.services,
        adb_serial=device.adb_serial,
        last_seen=device.last_seen,
        authorized_at=device.authorized_at,
        authorization_expires=device.authorization_expires
    )


@router.get("/devices/{device_id}/battery", response_model=BatteryResponse)
async def get_battery(
    device_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get device battery information."""
    try:
        adb_device = adb_manager.get_device(device_id)
        battery = await adb_device.get_battery()
        
        return BatteryResponse(
            device_id=device_id,
            level=battery.level,
            status=battery.status,
            temperature=battery.temperature,
            voltage=battery.voltage
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ADBError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/network", response_model=NetworkResponse)
async def get_network(
    device_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get device network information."""
    try:
        adb_device = adb_manager.get_device(device_id)
        network = await adb_device.get_network_info()
        
        return NetworkResponse(
            device_id=device_id,
            wifi_enabled=network.wifi_enabled,
            connected=network.connected,
            ssid=network.ssid,
            ip_address=network.ip_address,
            mac_address=network.mac_address
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ADBError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/{device_id}/audit", response_model=AuditResponse)
async def run_audit(
    device_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Run security audit on device."""
    try:
        audit = auditor.run_security_audit(device_id)
        
        return AuditResponse(
            device_id=audit.device_id,
            timestamp=audit.timestamp,
            score=audit.score,
            findings=[
                {
                    "id": f.id,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "category": f.category
                }
                for f in audit.findings
            ],
            recommendations=audit.recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{device_id}", response_model=ReportResponse)
async def get_report(
    device_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get security report for device."""
    try:
        report = auditor.generate_report(device_id)
        
        # Generate JSON report
        json_path = report_generator.generate_json_report(report)
        
        return ReportResponse(
            device_id=report.device_id,
            device_name=report.device_name,
            timestamp=report.timestamp,
            authorized=report.authorized,
            score=report.score,
            findings=[
                {
                    "id": f.id,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "category": f.category
                }
                for f in report.findings
            ],
            recommendations=report.recommendations,
            json_report_path=json_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan")
async def scan_network(
    cidr: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """Scan network for devices."""
    try:
        result = await scanner.scan_network(cidr)
        
        return {
            "cidr": result.cidr,
            "devices": [
                {
                    "ip_address": d.ip_address,
                    "hostname": d.hostname,
                    "mac_address": d.mac_address,
                    "manufacturer": d.manufacturer,
                    "services": d.services
                }
                for d in result.devices
            ],
            "scan_time": result.scan_time,
            "duration": result.duration
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/devices/register")
async def register_device(
    device_data: DeviceCreate,
    api_key: str = Depends(verify_api_key)
):
    """Register a new device."""
    try:
        device = device_manager.register_device(device_data)
        
        # Initiate pairing
        pairing = device_manager.initiate_pairing(device.id)
        
        return {
            "device_id": device.id,
            "status": device.status,
            "pairing_token": pairing["pairing_token"],
            "expires_in": pairing["expires_in"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Revoke device authorization."""
    success = device_manager.revoke_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"message": "Device authorization revoked"}


# Authentication Lab routes
@router.post("/auth/plaintext")
async def auth_plaintext(username: str, password: str):
    """Plaintext authentication (INSECURE - for demonstration only)."""
    from ..security.authentication_lab import AuthRequest
    
    request = AuthRequest(username=username, password=password)
    return await auth_lab.app.router.app.auth_plaintext(request)


@router.post("/auth/hash")
async def auth_hash(username: str, password: str):
    """Hashed password authentication."""
    from ..security.authentication_lab import AuthRequest
    
    request = AuthRequest(username=username, password=password)
    return await auth_lab.app.router.app.auth_hash(request)


@router.post("/auth/secure")
async def auth_secure(username: str, password: str):
    """Secure authentication with rate limiting."""
    from ..security.authentication_lab import AuthRequest
    
    request = AuthRequest(username=username, password=password)
    return await auth_lab.app.router.app.auth_secure(request)


@router.get("/auth/tests")
async def run_auth_tests():
    """Run authentication tests."""
    return auth_lab.run_tests()
