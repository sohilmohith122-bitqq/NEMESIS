"""
NEMESIS Plugin - Phone Manager (Legitimate)
Manages Android phones via ADB (Android Debug Bridge) for authorized devices.
Requires: USB debugging enabled, device authorized, ADB installed.
"""

import subprocess
import sys
import os
from pathlib import Path

PLUGIN = {
    "name": "phone_manager",
    "description": (
        "Manage your Android phone via ADB (Android Debug Bridge). "
        "Requires: USB debugging enabled, device connected and authorized, ADB installed. "
        "Features: battery status, installed apps, backup, reboot, screen capture."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "battery | apps | backup | reboot | screenshot | push | pull | shell",
            },
            "target": {
                "type": "STRING",
                "description": "For push/pull: local file path. For shell: command to run.",
            },
            "destination": {
                "type": "STRING",
                "description": "For push/pull: destination path on device or computer.",
            },
        },
        "required": ["action"],
    },
}

def _run_adb(args: list, timeout: int = 30) -> dict:
    """Run an ADB command and return result."""
    try:
        cmd = ["adb"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "ADB not found. Install Android SDK Platform Tools."}
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "ADB command timed out"}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}

def _check_device() -> bool:
    """Check if an Android device is connected and authorized."""
    result = _run_adb(["devices"])
    if result["success"]:
        lines = result["stdout"].strip().split("\n")
        # Skip header line, check for device with "device" status
        for line in lines[1:]:
            if line.strip() and "device" in line and "unauthorized" not in line:
                return True
    return False

def _get_battery_info() -> str:
    """Get battery status from connected device."""
    if not _check_device():
        return "No authorized device connected. Enable USB debugging and authorize the device."
    
    # Get battery level
    level = _run_adb(["shell", "dumpsys", "battery", "|", "grep", "level"])
    status = _run_adb(["shell", "dumpsys", "battery", "|", "grep", "status"])
    
    if level["success"]:
        return f"Battery Info:\n{level['stdout']}\n{status['stdout']}"
    return "Could not retrieve battery info."

def _get_installed_apps() -> str:
    """Get list of installed apps."""
    if not _check_device():
        return "No authorized device connected."
    
    result = _run_adb(["shell", "pm", "list", "packages", "-3"], timeout=60)
    if result["success"]:
        packages = result["stdout"].split("\n")
        return f"Third-party apps ({len(packages)}):\n" + "\n".join(packages[:50])  # Limit to 50
    return "Could not retrieve app list."

def _backup_device(destination: str) -> str:
    """Backup device data to computer."""
    if not _check_device():
        return "No authorized device connected."
    
    dest = destination or str(Path.home() / "Desktop" / "phone_backup.ab")
    result = _run_adb(["backup", "-all", "-f", dest], timeout=300)  # 5 min timeout
    if result["success"]:
        return f"Backup saved to: {dest}"
    return f"Backup failed: {result['stderr']}"

def _take_screenshot() -> str:
    """Take screenshot from device."""
    if not _check_device():
        return "No authorized device connected."
    
    # Take screenshot on device
    result = _run_adb(["shell", "screencap", "-p", "/sdcard/screenshot.png"])
    if not result["success"]:
        return f"Screenshot failed: {result['stderr']}"
    
    # Pull to computer
    dest = str(Path.home() / "Desktop" / "phone_screenshot.png")
    pull = _run_adb(["pull", "/sdcard/screenshot.png", dest])
    if pull["success"]:
        # Clean up on device
        _run_adb(["shell", "rm", "/sdcard/screenshot.png"])
        return f"Screenshot saved to: {dest}"
    return f"Failed to pull screenshot: {pull['stderr']}"

def _reboot_device(mode: str = "normal") -> str:
    """Reboot device (normal, recovery, bootloader)."""
    if not _check_device():
        return "No authorized device connected."
    
    if mode == "recovery":
        cmd = ["reboot", "recovery"]
    elif mode == "bootloader":
        cmd = ["reboot", "bootloader"]
    else:
        cmd = ["reboot"]
    
    result = _run_adb(cmd)
    if result["success"]:
        return f"Device rebooting ({mode} mode)..."
    return f"Reboot failed: {result['stderr']}"

def _push_file(source: str, destination: str) -> str:
    """Push file from computer to device."""
    if not _check_device():
        return "No authorized device connected."
    
    if not source or not destination:
        return "Specify source (computer) and destination (device) paths."
    
    result = _run_adb(["push", source, destination])
    if result["success"]:
        return f"File pushed: {source} -> {destination}"
    return f"Push failed: {result['stderr']}"

def _pull_file(source: str, destination: str) -> str:
    """Pull file from device to computer."""
    if not _check_device():
        return "No authorized device connected."
    
    if not source:
        return "Specify source path on device."
    
    dest = destination or str(Path.home() / "Desktop" / Path(source).name)
    result = _run_adb(["pull", source, dest])
    if result["success"]:
        return f"File pulled: {source} -> {dest}"
    return f"Pull failed: {result['stderr']}"

def _run_shell_command(command: str) -> str:
    """Run shell command on device."""
    if not _check_device():
        return "No authorized device connected."
    
    if not command:
        return "Specify a shell command to run."
    
    result = _run_adb(["shell", command])
    if result["success"]:
        return result["stdout"] if result["stdout"] else "Command executed (no output)"
    return f"Command failed: {result['stderr']}"

def run(parameters: dict, player=None, session_memory=None) -> str:
    """Main plugin entry point."""
    action = parameters.get("action", "").lower()
    target = parameters.get("target", "")
    destination = parameters.get("destination", "")
    
    if action == "battery":
        return _get_battery_info()
    elif action == "apps":
        return _get_installed_apps()
    elif action == "backup":
        return _backup_device(destination)
    elif action == "screenshot":
        return _take_screenshot()
    elif action == "reboot":
        mode = target if target in ["recovery", "bootloader"] else "normal"
        return _reboot_device(mode)
    elif action == "push":
        return _push_file(target, destination)
    elif action == "pull":
        return _pull_file(target, destination)
    elif action == "shell":
        return _run_shell_command(target)
    else:
        return (
            "Phone Manager Actions:\n"
            "• battery - Get battery status\n"
            "• apps - List installed apps\n"
            "• backup - Backup device (specify destination path)\n"
            "• screenshot - Take screenshot\n"
            "• reboot - Reboot device (normal/recovery/bootloader)\n"
            "• push - Push file to device (target=source, destination=device_path)\n"
            "• pull - Pull file from device (target=device_path, destination=local_path)\n"
            "• shell - Run shell command (target=command)\n\n"
            "Note: Requires ADB installed and USB debugging enabled on device."
        )
