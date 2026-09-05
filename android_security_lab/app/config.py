"""
Android Security Lab - Configuration Module

Centralized configuration management using environment variables.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Android Security Lab"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Lab Mode - STRICT safety controls
    lab_mode: bool = True  # When True, enables all safety restrictions
    
    # Database
    database_url: str = "sqlite:///android_security_lab.db"
    
    # Network Discovery
    scan_cidr: str = "192.168.1.0/24"  # Default CIDR range
    allowed_cidrs: list[str] = ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
    scan_timeout: int = 5  # seconds
    max_scan_concurrent: int = 50
    
    # Device Authorization
    pairing_token_expiry: int = 300  # seconds (5 minutes)
    authorization_expiry: int = 86400  # seconds (24 hours)
    require_pairing_approval: bool = True
    
    # ADB Configuration
    adb_path: str = "adb"
    adb_timeout: int = 10  # seconds
    allowed_adb_commands: list[str] = [
        "devices", "shell getprop", "shell dumpsys battery",
        "shell dumpsys wifi", "shell settings get"
    ]
    
    # Authentication Lab
    auth_lab_host: str = "127.0.0.1"
    auth_lab_port: int = 8443
    auth_lab_enabled: bool = False
    
    # Test Credentials (for lab only)
    test_username: str = "student"
    test_password: str = "lab-password-123"
    
    # Rate Limiting
    rate_limit_max_attempts: int = 5
    rate_limit_window: int = 300  # seconds
    account_lockout_duration: int = 900  # seconds (15 minutes)
    
    # Security Audit
    audit_log_retention_days: int = 30
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "security_lab.log"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # API Security
    api_key: str = Field(default="dev-key-change-in-production")
    api_key_header: str = "X-API-Key"
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent
    reports_dir: Path = Path("reports")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Safety Constants
PROHIBITED_ACTIONS = [
    "bypass_lock_screen",
    "extract_password",
    "crack_pin",
    "keylog",
    "install_spyware",
    "remote_control_bypass",
    "credential_theft",
    "unauthorized_access",
]

# Device Status Constants
class DeviceStatus:
    DISCOVERED = "DISCOVERED"
    PAIRING = "PAIRING"
    AUTHORIZED = "AUTHORIZED"
    REVOKED = "REVOKED"
    
    @classmethod
    def __call__(cls, value):
        return value


# Severity Levels
class Severity:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
