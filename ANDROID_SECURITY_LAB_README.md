# 📱 Android Security Lab Plugin

## Quick Start

```python
from plugins.android_security_lab import run

# List devices
result = run({"action": "list"})

# Get device info
result = run({"action": "info", "serial": "EMULATOR_5554"})

# Get battery
result = run({"action": "battery", "serial": "EMULATOR_5554"})

# Security audit
result = run({"action": "audit", "serial": "EMULATOR_5554"})
```

## Commands

| Action | Description | Required |
|--------|-------------|----------|
| `list` | List connected devices | - |
| `info` | Get device details | serial |
| `battery` | Get battery status | serial |
| `audit` | Run security audit | serial |
| `plugin_info` | Show plugin info | - |

## Requirements

1. **Install ADB**: https://developer.android.com/studio/releases/platform-tools
2. **Enable USB Debugging** on device
3. **Authorize device** in plugin

## Example Output

```
📱 Connected Devices:

  EMULATOR_5554 | device | ✓ AUTHORIZED
  RFCR88JHNZ7 | device | ✗ NOT AUTHORIZED
```

## Safety

- ✅ Only authorized devices
- ✅ No PIN extraction
- ✅ No lock bypass
- ✅ Educational use only
