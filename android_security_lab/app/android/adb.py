"""
Android Security Lab - ADB Support

Optional ADB support for devices that the user owns and has explicitly authorized.
"""

import asyncio
import subprocess
import logging
from typing import Optional
from ..config import get_settings
from ..models import DeviceInfo, BatteryInfo, NetworkInfo
from ..authorization.devices import device_manager, AuthorizationError

logger = logging.getLogger(__name__)


class ADBError(Exception):
    """ADB operation error."""
    pass


class ADBDevice:
    """ADB device operations."""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.settings = get_settings()
        self._verify_authorization()
    
    def _verify_authorization(self) -> None:
        """Verify device is authorized before any ADB operation."""
        self.device = device_manager.require_authorized_device(self.device_id)
        logger.info(f"ADB operations authorized for device {self.device_id}")
    
    async def _run_adb_command(self, command: str, timeout: Optional[int] = None) -> dict:
        """
        Run an ADB command with authorization checks.
        
        Args:
            command: ADB command to run
            timeout: Command timeout in seconds
            
        Returns:
            Command result
        """
        # Re-verify authorization
        self._verify_authorization()
        
        # Check if command is allowed
        cmd_parts = command.split()
        if cmd_parts and not any(cmd in command for cmd in self.settings.allowed_adb_commands):
            logger.warning(f"ADB command not in allowed list: {command}")
            raise ADBError(f"Command not allowed: {command}")
        
        # Build full ADB command
        if self.device.adb_serial:
            adb_cmd = [self.settings.adb_path, "-s", self.device.adb_serial] + cmd_parts
        else:
            adb_cmd = [self.settings.adb_path] + cmd_parts
        
        logger.info(f"Running ADB command: {' '.join(adb_cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *adb_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout or self.settings.adb_timeout
            )
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="ignore").strip(),
                "stderr": stderr.decode("utf-8", errors="ignore").strip(),
                "returncode": process.returncode
            }
            
        except asyncio.TimeoutError:
            raise ADBError(f"ADB command timed out: {command}")
        except FileNotFoundError:
            raise ADBError("ADB not found. Please install Android SDK Platform Tools.")
        except Exception as e:
            raise ADBError(f"ADB command failed: {e}")
    
    async def get_device_info(self) -> DeviceInfo:
        """
        Get device information via ADB.
        
        Returns:
            DeviceInfo with device details
        """
        logger.info(f"Getting device info for {self.device_id}")
        
        # Get device properties
        properties = {
            "model": "ro.product.model",
            "manufacturer": "ro.product.manufacturer",
            "android_version": "ro.build.version.release",
            "sdk_version": "ro.build.version.sdk",
            "security_patch": "ro.build.version.security_patch",
            "serial": "ro.serialno"
        }
        
        info = {}
        for key, prop in properties.items():
            result = await self._run_adb_command(f"shell getprop {prop}")
            info[key] = result["stdout"] if result["success"] else "Unknown"
        
        # Check if emulator
        is_emulator = "goldfish" in info.get("model", "").lower() or \
                     "ranchu" in info.get("model", "").lower() or \
                     "sdk" in info.get("model", "").lower()
        
        return DeviceInfo(
            serial=info.get("serial", "Unknown"),
            model=info.get("model", "Unknown"),
            manufacturer=info.get("manufacturer", "Unknown"),
            android_version=info.get("android_version", "Unknown"),
            sdk_version=info.get("sdk_version", "Unknown"),
            security_patch=info.get("security_patch", "Unknown"),
            is_emulator=is_emulator
        )
    
    async def get_battery(self) -> BatteryInfo:
        """
        Get battery status via ADB.
        
        Returns:
            BatteryInfo with battery details
        """
        logger.info(f"Getting battery info for {self.device_id}")
        
        result = await self._run_adb_command("shell dumpsys battery")
        
        if not result["success"]:
            raise ADBError("Failed to get battery info")
        
        # Parse battery info
        info = {"level": 0, "status": "Unknown"}
        
        for line in result["stdout"].split("\n"):
            line = line.strip()
            if "level:" in line:
                info["level"] = int(line.split(":")[1].strip())
            elif "status:" in line:
                status_code = int(line.split(":")[1].strip())
                status_map = {
                    1: "Unknown", 2: "Charging", 3: "Discharging",
                    4: "Not charging", 5: "Full"
                }
                info["status"] = status_map.get(status_code, "Unknown")
            elif "temperature:" in line:
                info["temperature"] = int(line.split(":")[1].strip()) / 10.0
            elif "voltage:" in line:
                info["voltage"] = int(line.split(":")[1].strip()) / 1000.0
        
        return BatteryInfo(
            level=info.get("level", 0),
            status=info.get("status", "Unknown"),
            temperature=info.get("temperature"),
            voltage=info.get("voltage")
        )
    
    async def get_network_info(self) -> NetworkInfo:
        """
        Get network information via ADB.
        
        Returns:
            NetworkInfo with network details
        """
        logger.info(f"Getting network info for {self.device_id}")
        
        # Check WiFi status
        wifi_result = await self._run_adb_command("shell settings get global wifi_on")
        wifi_enabled = wifi_result["stdout"] == "1" if wifi_result["success"] else False
        
        # Get WiFi info
        wifi_info_result = await self._run_adb_command("shell dumpsys wifi")
        
        ssid = None
        ip_address = None
        mac_address = None
        connected = False
        
        if wifi_info_result["success"]:
            for line in wifi_info_result["stdout"].split("\n"):
                if "mWifiInfo" in line or "WifiInfo" in line:
                    connected = "SSID:" in line
                    if "SSID:" in line:
                        ssid = line.split("SSID:")[1].strip().strip('"')
                    if "mFrequency" in line:
                        pass  # Could extract frequency
                elif "mIpAddress" in line:
                    # Convert IP integer to string
                    try:
                        ip_int = int(line.split("mIpAddress:")[1].strip())
                        ip_address = f"{ip_int & 0xFF}.{(ip_int >> 8) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 24) & 0xFF}"
                    except:
                        pass
                elif "mMacAddress" in line:
                    mac_address = line.split("mMacAddress:")[1].strip()
        
        return NetworkInfo(
            wifi_enabled=wifi_enabled,
            connected=connected,
            ssid=ssid,
            ip_address=ip_address,
            mac_address=mac_address
        )
    
    async def execute_safe_command(self, command: str) -> str:
        """
        Execute a safe, allowed shell command.
        
        Args:
            command: Command to execute (must be in allowed list)
            
        Returns:
            Command output
        """
        # Only allow specific safe commands
        allowed_commands = [
            "ls", "pwd", "date", "uptime", "id", "whoami",
            "cat /proc/version", "cat /proc/meminfo", "cat /proc/cpuinfo"
        ]
        
        if command not in allowed_commands:
            raise ADBError(f"Command not allowed: {command}")
        
        result = await self._run_adb_command(f"shell {command}")
        
        if result["success"]:
            return result["stdout"]
        else:
            raise ADBError(f"Command failed: {result['stderr']}")


class ADBManager:
    """ADB device manager."""
    
    def __init__(self):
        self.devices: dict[str, ADBDevice] = {}
    
    def get_device(self, device_id: str) -> ADBDevice:
        """
        Get ADB device instance.
        
        Args:
            device_id: Device ID
            
        Returns:
            ADBDevice instance
        """
        if device_id not in self.devices:
            self.devices[device_id] = ADBDevice(device_id)
        return self.devices[device_id]
    
    async def check_adb_connection(self, device_id: str) -> bool:
        """Check if ADB can connect to device."""
        try:
            adb_device = self.get_device(device_id)
            await adb_device._run_adb_command("devices")
            return True
        except Exception:
            return False
    
    async def get_all_adb_devices(self) -> list[dict]:
        """Get list of all ADB devices."""
        try:
            process = await asyncio.create_subprocess_exec(
                "adb", "devices", "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            lines = stdout.decode("utf-8").strip().split("\n")
            
            devices = []
            for line in lines[1:]:  # Skip header
                if line.strip() and "device" in line:
                    parts = line.split()
                    devices.append({
                        "serial": parts[0],
                        "status": parts[1],
                        "info": " ".join(parts[2:]) if len(parts) > 2 else ""
                    })
            
            return devices
            
        except FileNotFoundError:
            return []


# Singleton instance
adb_manager = ADBManager()
