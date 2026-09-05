"""
Android Security Lab - Network Scanner

Scans network for discoverable devices with safety safeguards.
Only scans configured private CIDR ranges.
"""

import asyncio
import ipaddress
import socket
import time
from datetime import datetime
from typing import Optional
from ..config import get_settings, DeviceStatus
from ..models import NetworkDevice, ScanResult
import logging

logger = logging.getLogger(__name__)


class NetworkScanner:
    """Network scanner for authorized laboratory devices."""
    
    def __init__(self):
        self.settings = get_settings()
        self._validate_cidr()
    
    def _validate_cidr(self) -> None:
        """Validate that scan CIDR is within allowed ranges."""
        scan_network = ipaddress.ip_network(self.settings.scan_cidr, strict=False)
        allowed = False
        
        for allowed_cidr in self.settings.allowed_cidrs:
            allowed_network = ipaddress.ip_network(allowed_cidr, strict=False)
            # Check if scan network is within allowed network
            if all(ip in allowed_network for ip in [scan_network.network_address, scan_network.broadcast_address]):
                allowed = True
                break
        
        if not allowed:
            raise ValueError(
                f"Scan CIDR {self.settings.scan_cidr} is not within allowed ranges: "
                f"{self.settings.allowed_cidrs}"
            )
    
    async def scan_network(self, cidr: Optional[str] = None) -> ScanResult:
        """
        Scan network for discoverable devices.
        
        Args:
            cidr: Optional CIDR range to scan (must be in allowed ranges)
            
        Returns:
            ScanResult with discovered devices
        """
        target_cidr = cidr or self.settings.scan_cidr
        
        # Validate CIDR is allowed
        scan_network = ipaddress.ip_network(target_cidr, strict=False)
        allowed = False
        for allowed_cidr in self.settings.allowed_cidrs:
            allowed_network = ipaddress.ip_network(allowed_cidr, strict=False)
            # Check if scan network is within allowed network
            if all(ip in allowed_network for ip in [scan_network.network_address, scan_network.broadcast_address]):
                allowed = True
                break
        
        if not allowed:
            raise ValueError(
                f"Cannot scan {target_cidr}: not in allowed CIDR ranges"
            )
        
        logger.info(f"Starting network scan on {target_cidr}")
        start_time = time.time()
        
        devices = []
        
        # Scan IPs in parallel
        ip_list = list(scan_network.hosts())[:self.settings.max_scan_concurrent]
        
        tasks = [self._scan_host(ip) for ip in ip_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, NetworkDevice):
                devices.append(result)
        
        duration = time.time() - start_time
        
        return ScanResult(
            cidr=target_cidr,
            devices=devices,
            scan_time=datetime.now(),
            duration=duration
        )
    
    async def _scan_host(self, ip: ipaddress.IPv4Address) -> Optional[NetworkDevice]:
        """Scan a single host for services."""
        ip_str = str(ip)
        
        try:
            # Check common ports
            services = []
            common_ports = [22, 80, 443, 5555, 8080, 8443]  # 5555 = ADB
            
            for port in common_ports:
                if await self._check_port(ip_str, port):
                    services.append(f"port-{port}")
            
            if not services:
                return None
            
            # Try to get hostname
            try:
                hostname = socket.gethostbyaddr(ip_str)[0]
            except socket.herror:
                hostname = None
            
            # Try to get MAC address (requires root on some systems)
            mac_address = await self._get_mac_address(ip_str)
            
            # Try to identify manufacturer
            manufacturer = await self._identify_manufacturer(mac_address) if mac_address else None
            
            return NetworkDevice(
                ip_address=ip_str,
                hostname=hostname,
                mac_address=mac_address,
                manufacturer=manufacturer,
                services=services,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.debug(f"Error scanning {ip_str}: {e}")
            return None
    
    async def _check_port(self, ip: str, port: int) -> bool:
        """Check if a port is open."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=self.settings.scan_timeout / 10
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
    
    async def _get_mac_address(self, ip: str) -> Optional[str]:
        """Get MAC address from ARP table."""
        try:
            # This is platform-specific and may require elevated privileges
            # For now, return None - can be enhanced with platform-specific implementations
            return None
        except Exception:
            return None
    
    async def _identify_manufacturer(self, mac_address: Optional[str]) -> Optional[str]:
        """Identify manufacturer from MAC address OUI."""
        if not mac_address:
            return None
        
        # Common OUI prefixes for mobile devices
        oui_map = {
            "00:1A:11": "Google",
            "3C:5A:B4": "Google",
            "AC:BC:32": "Apple",
            "F0:18:98": "Apple",
            "00:1B:63": "Samsung",
            "30:96:FB": "Samsung",
            "00:1E:58": "OnePlus",
            "40:B0:34": "OnePlus",
        }
        
        prefix = mac_address[:8].upper()
        return oui_map.get(prefix, None)
    
    async def scan_for_adb(self, cidr: Optional[str] = None) -> list[NetworkDevice]:
        """Scan specifically for ADB-enabled devices."""
        target_cidr = cidr or self.settings.scan_cidr
        scan_network = ipaddress.ip_network(target_cidr, strict=False)
        
        adb_devices = []
        
        for ip in scan_network.hosts():
            if await self._check_port(str(ip), 5555):
                device = NetworkDevice(
                    ip_address=str(ip),
                    services=["adb"],
                    timestamp=datetime.now()
                )
                adb_devices.append(device)
        
        return adb_devices


# Singleton instance
scanner = NetworkScanner()
