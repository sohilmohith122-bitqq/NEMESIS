"""
Android Security Lab - Network Discovery Tests
"""

import pytest
from app.discovery.scanner import NetworkScanner
from app.config import Settings


class TestNetworkDiscovery:
    """Test network discovery functionality."""
    
    def test_scanner_initialization(self):
        """Test scanner initializes with valid settings."""
        scanner = NetworkScanner()
        assert scanner.settings is not None
        assert scanner.settings.scan_cidr is not None
    
    def test_cidr_validation_valid(self):
        """Test valid CIDR range is accepted."""
        scanner = NetworkScanner()
        # Should not raise exception
        assert scanner.settings.scan_cidr is not None
    
    @pytest.mark.asyncio
    async def test_scan_network_returns_result(self):
        """Test scan_network returns ScanResult."""
        scanner = NetworkScanner()
        result = await scanner.scan_network()
        
        assert hasattr(result, 'cidr')
        assert hasattr(result, 'devices')
        assert hasattr(result, 'scan_time')
        assert hasattr(result, 'duration')
    
    @pytest.mark.asyncio
    async def test_scan_for_adb(self):
        """Test ADB-specific scanning."""
        scanner = NetworkScanner()
        devices = await scanner.scan_for_adb("127.0.0.0/32")
        assert isinstance(devices, list)
