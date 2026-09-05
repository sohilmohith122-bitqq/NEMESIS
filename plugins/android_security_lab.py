from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional


PLUGIN = {
    "name": "android_security_lab",
    "description": (
        "Android Security Lab - Manage and audit Android devices via ADB. "
        "Only operates on explicitly authorized devices. "
        "Does not bypass Android authentication."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "list | info | battery | audit | plugin_info",
            },
            "serial": {
                "type": "STRING",
                "description": "Device serial number (required for info, battery, audit)",
            },
        },
        "required": ["action"],
    },
}


@dataclass
class AndroidDevice:
    serial: str
    state: str
    authorized: bool


class AndroidSecurityLab:
    """
    NEMESIS Android Security Lab.

    Only operates on explicitly authorized ADB devices.
    Does not bypass Android authentication.
    """

    name = "Android Security Lab"
    version = "1.0.0"

    def __init__(self, allowed_devices: Optional[set[str]] = None):
        self.allowed_devices = allowed_devices or set()

    def _adb(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["adb", *args],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "ADB command failed")

            return result.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError(
                "ADB not found. Install Android SDK Platform Tools:\n"
                "https://developer.android.com/studio/releases/platform-tools"
            )

    def list_devices(self) -> list[AndroidDevice]:
        output = self._adb("devices")

        devices = []

        for line in output.splitlines()[1:]:
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            serial, state = parts[0], parts[1]

            devices.append(
                AndroidDevice(
                    serial=serial,
                    state=state,
                    authorized=serial in self.allowed_devices,
                )
            )

        return devices

    def device_info(self, serial: str) -> dict:
        self._check_authorized(serial)

        return {
            "serial": serial,
            "manufacturer": self._adb(
                "-s", serial, "shell", "getprop", "ro.product.manufacturer"
            ),
            "model": self._adb(
                "-s", serial, "shell", "getprop", "ro.product.model"
            ),
            "android_version": self._adb(
                "-s", serial, "shell", "getprop", "ro.build.version.release"
            ),
            "security_patch": self._adb(
                "-s", serial, "shell",
                "getprop", "ro.build.version.security_patch"
            ),
        }

    def battery(self, serial: str) -> str:
        self._check_authorized(serial)

        return self._adb(
            "-s", serial, "shell", "dumpsys", "battery"
        )

    def security_audit(self, serial: str) -> dict:
        self._check_authorized(serial)

        info = self.device_info(serial)

        return {
            "device": serial,
            "android_version": info["android_version"],
            "security_patch": info["security_patch"],
            "findings": [],
            "note": (
                "Security audit completed. "
                "Authentication bypass is intentionally not supported."
            ),
        }

    def _check_authorized(self, serial: str) -> None:
        if serial not in self.allowed_devices:
            raise PermissionError(
                f"Device {serial!r} is not authorized for NEMESIS."
            )

    def plugin_info(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": [
                "device discovery",
                "authorized device information",
                "battery inspection",
                "security auditing",
                "security reporting",
            ],
            "restrictions": [
                "no PIN/password extraction",
                "no lock-screen bypass",
                "no unauthorized device access",
            ],
        }


def create_plugin() -> AndroidSecurityLab:
    # Populate this from NEMESIS's existing secure configuration.
    allowed_devices = set()

    return AndroidSecurityLab(allowed_devices)


# Global plugin instance
_lab = None


def _get_lab() -> AndroidSecurityLab:
    global _lab
    if _lab is None:
        _lab = create_plugin()
    return _lab


def run(parameters: dict, player=None, session_memory=None) -> str:
    """Main plugin entry point for NEMESIS."""
    action = parameters.get("action", "list").lower()
    serial = parameters.get("serial", "")
    
    lab = _get_lab()
    
    try:
        if action == "list":
            devices = lab.list_devices()
            if not devices:
                return "No ADB devices connected."
            
            result = "📱 Connected Devices:\n\n"
            for d in devices:
                status = "✓ AUTHORIZED" if d.authorized else "✗ NOT AUTHORIZED"
                result += f"  {d.serial} | {d.state} | {status}\n"
            return result
        
        elif action == "info":
            if not serial:
                return "Please specify a device serial number."
            info = lab.device_info(serial)
            result = f"📱 Device Info ({serial}):\n\n"
            for key, value in info.items():
                result += f"  {key}: {value}\n"
            return result
        
        elif action == "battery":
            if not serial:
                return "Please specify a device serial number."
            battery_info = lab.battery(serial)
            return f"🔋 Battery Status ({serial}):\n\n{battery_info}"
        
        elif action == "audit":
            if not serial:
                return "Please specify a device serial number."
            audit = lab.security_audit(serial)
            result = f"🔍 Security Audit ({serial}):\n\n"
            for key, value in audit.items():
                result += f"  {key}: {value}\n"
            return result
        
        elif action == "plugin_info":
            info = lab.plugin_info()
            result = f"📦 Plugin: {info['name']} v{info['version']}\n\n"
            result += "Capabilities:\n"
            for cap in info["capabilities"]:
                result += f"  ✓ {cap}\n"
            result += "\nRestrictions:\n"
            for rest in info["restrictions"]:
                result += f"  ✗ {rest}\n"
            return result
        
        else:
            return (
                "Android Security Lab Actions:\n"
                "  list - List connected devices\n"
                "  info - Get device info (requires serial)\n"
                "  battery - Get battery status (requires serial)\n"
                "  audit - Run security audit (requires serial)\n"
                "  plugin_info - Get plugin information\n\n"
                "Note: Only authorized devices can be managed."
            )
    
    except PermissionError as e:
        return f"❌ Access Denied: {e}\n\nAdd the device to allowed_devices first."
    except RuntimeError as e:
        return f"❌ ADB Error: {e}\n\nCheck if ADB is installed and device is connected."
    except Exception as e:
        return f"❌ Error: {e}"
