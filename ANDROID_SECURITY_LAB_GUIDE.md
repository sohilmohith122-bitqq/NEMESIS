# Android Security Lab - Usage Guide

## Quick Start

### 1. Basic Setup

```python
from plugins.android_security_lab import create_plugin

# Create the plugin instance
lab = create_plugin()
```

### 2. Add Authorized Devices

```python
# Add device serial numbers you own/have permission to access
lab.allowed_devices.add("EMULATOR_5554")  # Android Emulator
lab.allowed_devices.add("RFCR88JHNZ7")    # Physical device serial
```

### 3. List Connected Devices

```python
devices = lab.list_devices()

for device in devices:
    print(f"Serial: {device.serial}")
    print(f"State: {device.state}")
    print(f"Authorized: {device.authorized}")
    print("---")
```

---

## Available Methods

### `list_devices()`
Discover all ADB-connected devices.

```python
devices = lab.list_devices()
# Returns: list[AndroidDevice]
# AndroidDevice has: serial, state, authorized
```

### `device_info(serial)`
Get detailed device information.

```python
info = lab.device_info("EMULATOR_5554")
# Returns: dict with serial, manufacturer, model, 
#          android_version, security_patch
```

### `battery(serial)`
Get battery status.

```python
battery_info = lab.battery("EMULATOR_5554")
# Returns: battery dumpsys output as string
```

### `security_audit(serial)`
Run a security audit on the device.

```python
audit = lab.security_audit("EMULATOR_5554")
# Returns: dict with device, android_version, 
#          security_patch, findings, note
```

### `plugin_info()`
Get plugin information.

```python
info = lab.plugin_info()
# Returns: dict with name, version, capabilities, restrictions
```

---

## Complete Example

```python
from plugins.android_security_lab import create_plugin

def main():
    # 1. Create plugin
    lab = create_plugin()
    
    # 2. Authorize your devices
    lab.allowed_devices.add("EMULATOR_5554")
    
    # 3. List devices
    print("=== Connected Devices ===")
    devices = lab.list_devices()
    for d in devices:
        status = "✓ AUTHORIZED" if d.authorized else "✗ NOT AUTHORIZED"
        print(f"{d.serial} | {d.state} | {status}")
    
    # 4. Get device info (if authorized)
    print("\n=== Device Info ===")
    try:
        info = lab.device_info("EMULATOR_5554")
        for key, value in info.items():
            print(f"{key}: {value}")
    except PermissionError as e:
        print(f"Error: {e}")
    
    # 5. Get battery status
    print("\n=== Battery Status ===")
    try:
        battery = lab.battery("EMULATOR_5554")
        print(battery)
    except PermissionError as e:
        print(f"Error: {e}")
    
    # 6. Run security audit
    print("\n=== Security Audit ===")
    try:
        audit = lab.security_audit("EMULATOR_5554")
        for key, value in audit.items():
            print(f"{key}: {value}")
    except PermissionError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

---

## Error Handling

### PermissionError
Raised when trying to access an unauthorized device.

```python
try:
    info = lab.device_info("UNAUTHORIZED_DEVICE")
except PermissionError as e:
    print(f"Access denied: {e}")
    # Add the device to allowed_devices first
    lab.allowed_devices.add("UNAUTHORIZED_DEVICE")
```

### RuntimeError
Raised when ADB command fails.

```python
try:
    devices = lab.list_devices()
except RuntimeError as e:
    print(f"ADB error: {e}")
    # Check if ADB is installed and running
```

---

## Prerequisites

### 1. Install ADB (Android Debug Bridge)

**Windows:**
```bash
# Download Android SDK Platform Tools
# https://developer.android.com/studio/releases/platform-tools
# Add to PATH
```

**macOS/Linux:**
```bash
# macOS
brew install android-platform-tools

# Ubuntu/Debian
sudo apt install adb
```

### 2. Enable USB Debugging on Device

1. Go to **Settings** → **About Phone**
2. Tap **Build Number** 7 times (enables Developer Options)
3. Go to **Settings** → **Developer Options**
4. Enable **USB Debugging**

### 3. Connect Device

```bash
# Verify ADB sees your device
adb devices

# You should see something like:
# List of devices attached
# EMULATOR_5554    device
# RFCR88JHNZ7     device
```

---

## NEMESIS Integration

The plugin integrates with NEMESIS's existing configuration:

```python
# In your NEMESIS setup
from plugins.android_security_lab import create_plugin

# Create plugin with your authorized devices
lab = create_plugin()

# Add devices from your configuration
lab.allowed_devices.update([
    "EMULATOR_5554",
    "YOUR_DEVICE_SERIAL",
])
```

---

## Safety Features

### Built-in Restrictions

The plugin **intentionally does NOT** support:

- ✗ PIN/password extraction
- ✗ Lock-screen bypass
- ✗ Credential cracking
- ✗ Unauthorized device access
- ✗ Spyware functionality

### Authorization Required

Every operation checks authorization:

```python
def _check_authorized(self, serial: str) -> None:
    if serial not in self.allowed_devices:
        raise PermissionError(
            f"Device {serial!r} is not authorized for NEMESIS."
        )
```

### Educational Purpose Only

This plugin is designed for:
- Learning about Android security
- Authorized penetration testing
- Security research in controlled environments
- Understanding ADB and device management

---

## Troubleshooting

### "ADB not found"
```bash
# Verify ADB is in your PATH
adb version

# If not found, add Android SDK Platform Tools to PATH
```

### "Device unauthorized"
1. Check if USB debugging is enabled
2. Look for authorization prompt on device
3. Tap "Allow" on the device

### "Device not found"
```bash
# List all ADB devices
adb devices

# Restart ADB server
adb kill-server
adb start-server
```

### PermissionError
- Add the device serial to `lab.allowed_devices`
- Verify you own the device or have permission

---

## Example Output

```
=== Connected Devices ===
EMULATOR_5554 | device | ✓ AUTHORIZED
RFCR88JHNZ7 | device | ✗ NOT AUTHORIZED

=== Device Info ===
serial: EMULATOR_5554
manufacturer: Google
model: sdk_gphone64_x86_64
android_version: 14
security_patch: 2024-01-05

=== Battery Status ===
Current Battery Service state:
  AC powered: false
  USB powered: true
  status: 2
  level: 85
  temperature: 250

=== Security Audit ===
device: EMULATOR_5554
android_version: 14
security_patch: 2024-01-05
findings: []
note: Security audit completed. Authentication bypass is intentionally not supported.
```
