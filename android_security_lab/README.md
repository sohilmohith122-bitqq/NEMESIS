# Android Security Lab

**Educational cybersecurity testing tool for authorized security testing and learning.**

## ⚠️ IMPORTANT SECURITY NOTICE

This project is **strictly for authorized security testing and education only**.

### DO NOT use this tool for:
- Phone PIN/password extraction
- Lock-screen bypass
- Password/PIN cracking against real devices
- Credential theft
- Keylogging
- Spyware
- Unauthorized remote control
- Exploitation of arbitrary phones on a network
- Bypassing Android authentication
- Accessing another person's private data

### Authorization Requirement
**A phone being connected to the same Wi-Fi/LAN MUST NOT be treated as authorization.**

This tool only interacts with:
1. **Explicitly authorized devices** - Devices that have gone through the pairing process
2. **Locally controlled Android emulators** - Your own development emulators
3. **Deliberately vulnerable test applications** - Created specifically for this lab

---

## 🚀 Features

- **Network Discovery** - Scan for devices on your private network
- **Device Authorization** - Explicit pairing system with QR codes and tokens
- **ADB Support** - Manage authorized Android devices via ADB
- **Security Auditing** - Comprehensive security assessments
- **Authentication Lab** - Educational vulnerable authentication service
- **Reporting** - JSON and terminal-based security reports
- **CLI Interface** - Command-line tools for all operations
- **REST API** - FastAPI-based API for integration

---

## 📦 Installation

### Prerequisites

- Python 3.11+
- pip or poetry
- ADB (optional, for Android device management)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd android_security_lab
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LAB_MODE` | `true` | Enable safety restrictions |
| `SCAN_CIDR` | `192.168.1.0/24` | Network range to scan |
| `API_KEY` | `dev-key-change-in-production` | API authentication key |
| `AUTH_LAB_PORT` | `8443` | Authentication lab port |

### Safety Settings

When `LAB_MODE=true`:
- Scanning restricted to private CIDR ranges only
- Only registered test devices can be managed
- Credential extraction disabled
- Lock-screen bypass disabled

---

## 🏃 Running the Application

### Start the API Server

```bash
python -m app.main
```

The API will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### Start Authentication Lab

```bash
python -m app.cli auth-lab-start
```

The lab will be available at: `http://localhost:8443`

---

## 📱 CLI Commands

### Network Discovery

```bash
# Scan network for devices
python -m app.cli scan --cidr 192.168.1.0/24
```

### Device Management

```bash
# List all registered devices
python -m app.cli devices

# Register a new device
# (Use the API for registration)

# Pair a device
python -m app.cli pair <DEVICE_ID>

# Get device info
python -m app.cli info <DEVICE_ID>

# Get battery status
python -m app.cli battery <DEVICE_ID>
```

### Security Operations

```bash
# Run security audit
python -m app.cli audit <DEVICE_ID>

# Generate security report
python -m app.cli report <DEVICE_ID>
```

### Authentication Lab

```bash
# Start authentication lab
python -m app.cli auth-lab-start

# Run authentication tests
python -m app.cli auth-lab-test
```

---

## 🔐 Device Authorization Flow

1. **Discover Device**
   ```bash
   python -m app.cli scan
   ```

2. **Register Device** (via API)
   ```
   POST /api/devices/register
   {
     "name": "My Test Phone",
     "ip_address": "192.168.1.100",
     "services": ["adb"]
   }
   ```

3. **Initiate Pairing**
   ```bash
   python -m app.cli pair <DEVICE_ID>
   ```

4. **Complete Pairing**
   ```
   POST /api/devices/<DEVICE_ID>/pair
   {
     "pairing_token": "<TOKEN_FROM_STEP_3>"
   }
   ```

5. **Device is Now Authorized**
   - Can run security audits
   - Can access device info via ADB
   - Can generate reports

---

## 🔍 Security Auditing

### What Gets Checked

- Authorization status
- ADB authorization
- Insecure services
- Configuration issues
- Logging configuration
- Authentication lab vulnerabilities

### Security Score

The audit produces a score from 0-100:

- **90-100**: Excellent security
- **80-89**: Good security
- **60-79**: Needs improvement
- **0-59**: Critical issues

### Example Output

```
Security Score: 82/100

Findings:

HIGH
Test authentication endpoint does not enforce rate limiting.

MEDIUM
HTTP is being used instead of HTTPS in the laboratory service.

LOW
Verbose authentication errors reveal whether a username exists.
```

---

## 🧪 Authentication Lab

### Test Credentials

| Username | Password |
|----------|----------|
| student | lab-password-123 |
| admin | admin123 |
| test | test123 |

### API Endpoints

- `POST /auth-lab/auth/plaintext` - Insecure plaintext auth
- `POST /auth-lab/auth/hash` - Hashed password auth
- `POST /auth-lab/auth/secure` - Secure auth with rate limiting

### Learning Objectives

1. Understand why plaintext passwords are insecure
2. Learn about password hashing and salting
3. Implement rate limiting to prevent brute force
4. Detect and respond to failed login attempts
5. Implement account lockout mechanisms

---

## 🌐 REST API

### Authentication

All management endpoints require API key:

```
X-API-Key: your-api-key-here
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/devices` | List devices |
| POST | `/api/devices/register` | Register device |
| GET | `/api/devices/<id>` | Get device info |
| GET | `/api/devices/<id>/battery` | Get battery |
| GET | `/api/devices/<id>/network` | Get network info |
| POST | `/api/devices/<id>/audit` | Run audit |
| GET | `/api/reports/<id>` | Get report |
| POST | `/api/scan` | Scan network |

---

## 🧪 Testing

### Run All Tests

```bash
pytest
```

### Run Specific Tests

```bash
# Discovery tests
pytest tests/test_discovery.py

# Authorization tests
pytest tests/test_authorization.py

# Authentication lab tests
pytest tests/test_authentication_lab.py

# Security audit tests
pytest tests/test_security_audit.py
```

### Test Coverage

```bash
pytest --cov=app --cov-report=html
```

---

## 📁 Project Structure

```
android_security_lab/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py             # Configuration management
│   ├── models.py             # Pydantic models
│   ├── database.py           # SQLite database
│   ├── cli.py                # CLI interface
│   │
│   ├── discovery/
│   │   ├── __init__.py
│   │   └── scanner.py        # Network scanner
│   │
│   ├── authorization/
│   │   ├── __init__.py
│   │   └── devices.py        # Device authorization
│   │
│   ├── android/
│   │   ├── __init__.py
│   │   └── adb.py            # ADB support
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── audit.py          # Security auditing
│   │   ├── authentication_lab.py  # Auth lab
│   │   └── report.py         # Report generation
│   │
│   └── api/
│       ├── __init__.py
│       ├── routes.py         # API routes
│       └── schemas.py        # API schemas
│
├── tests/
│   ├── __init__.py
│   ├── test_discovery.py
│   ├── test_authorization.py
│   ├── test_authentication_lab.py
│   └── test_security_audit.py
│
├── requirements.txt
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 🔒 Safety Guardrails

### Central Authorization Check

Every device-management operation calls `require_authorized_device()`:

```python
def require_authorized_device(device_id: str) -> Device:
    device = db.get_device(device_id)
    
    if not device:
        raise AuthorizationError(f"Device not found: {device_id}")
    
    if device.status != DeviceStatus.AUTHORIZED:
        raise AuthorizationError(
            "Device is not explicitly authorized for laboratory testing."
        )
    
    return device
```

### Lab Mode

When `LAB_MODE=true`:
- Scanning restricted to configured private CIDR ranges
- Only registered test devices can be managed
- Credential extraction disabled
- Lock-screen bypass disabled

---

## ⚖️ Ethical and Legal Considerations

### Authorized Testing Only

This tool is designed for:
- Educational cybersecurity courses
- Authorized penetration testing
- Security research in controlled environments
- Learning about authentication vulnerabilities

### Prohibited Use

Do NOT use this tool for:
- Unauthorized access to devices
- Real-world penetration testing without explicit permission
- Any illegal activities
- Harassment or stalking
- Corporate espionage

### Liability

Users are responsible for ensuring they have proper authorization before using this tool. The developers are not responsible for misuse.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Follow ethical guidelines
2. Add tests for new features
3. Update documentation
4. Use type hints
5. Follow the existing code style

---

## 📄 License

This project is for educational purposes only. Use responsibly.

---

## 🆘 Support

- Check the documentation
- Run tests to verify setup
- Review the security audit output for guidance

---

## ⚠️ Final Reminder

**This tool is for authorized educational use only.**

**Being connected to the same network does NOT authorize access to a device.**

**Always obtain explicit permission before testing on any device.**

**Use this tool responsibly and ethically.**
