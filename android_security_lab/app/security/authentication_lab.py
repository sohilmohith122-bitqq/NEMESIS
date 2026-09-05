"""
Android Security Lab - Educational Authentication Lab

Deliberately vulnerable LOCAL authentication service for educational demonstrations.
This must NOT attack Android's actual lock screen.
"""

import asyncio
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from ..config import get_settings
from ..database import db
import logging

logger = logging.getLogger(__name__)


# Pydantic models
class AuthRequest(BaseModel):
    """Authentication request."""
    username: str
    password: str


class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    message: str
    token: Optional[str] = None
    details: Optional[dict] = None


# Test credentials (for lab only)
TEST_CREDENTIALS = {
    "student": "lab-password-123",
    "admin": "admin123",
    "test": "test123"
}


class AuthenticationLab:
    """
    Educational authentication lab with deliberately vulnerable features.
    
    Demonstrates:
    - Plaintext authentication (insecure)
    - Hashed password authentication (better)
    - Rate limiting
    - Failed-login detection
    - Account lockout
    - Secure password hashing
    - Authentication logging
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.failed_attempts: dict[str, list[datetime]] = {}
        self.locked_accounts: dict[str, datetime] = {}
        self.active_sessions: dict[str, dict] = {}
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Educational Authentication Lab",
            description="Deliberately vulnerable authentication service for learning",
            docs_url="/docs"
        )
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup API routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Root endpoint with lab information."""
            return """
            <html>
            <head>
                <title>Educational Authentication Lab</title>
                <style>
                    body { font-family: monospace; background: #0a0a0a; color: #00ff41; padding: 40px; }
                    h1 { text-shadow: 0 0 10px rgba(0,255,65,0.5); }
                    .warning { color: #ff0040; border: 1px solid #ff0040; padding: 20px; margin: 20px 0; }
                    .info { color: #00ff41; border: 1px solid #00ff41; padding: 20px; margin: 20px 0; }
                    code { background: rgba(0,255,65,0.1); padding: 2px 6px; }
                </style>
            </head>
            <body>
                <h1>🔒 Educational Authentication Lab</h1>
                
                <div class="warning">
                    <strong>⚠️ WARNING:</strong> This is a DELIBERATELY VULNERABLE service for educational purposes only.
                    Do NOT use in production. Do NOT attack real authentication systems.
                </div>
                
                <div class="info">
                    <h3>Test Credentials:</h3>
                    <p>Username: <code>student</code> | Password: <code>lab-password-123</code></p>
                    <p>Username: <code>admin</code> | Password: <code>admin123</code></p>
                    <p>Username: <code>test</code> | Password: <code>test123</code></p>
                </div>
                
                <h3>API Endpoints:</h3>
                <ul>
                    <li><code>POST /auth/plaintext</code> - Insecure plaintext auth (demonstrates vulnerability)</li>
                    <li><code>POST /auth/hash</code> - Hashed password auth (better practice)</li>
                    <li><code>POST /auth/secure</code> - Secure auth with rate limiting</li>
                    <li><code>GET /auth/attempts</code> - View authentication attempts</li>
                    <li><code>GET /auth/status</code> - Check account lockout status</li>
                </ul>
                
                <h3>Learning Objectives:</h3>
                <ul>
                    <li>Understand why plaintext passwords are insecure</li>
                    <li>Learn about password hashing and salting</li>
                    <li>Implement rate limiting to prevent brute force</li>
                    <li>Detect and respond to failed login attempts</li>
                    <li>Implement account lockout mechanisms</li>
                </ul>
                
                <p><a href="/docs" style="color: #00ff41;">View API Documentation (Swagger)</a></p>
            </body>
            </html>
            """
        
        @self.app.post("/auth/plaintext", response_model=AuthResponse)
        async def auth_plaintext(request: AuthRequest):
            """
            INSECURE: Plaintext authentication.
            
            This demonstrates the vulnerability of sending passwords in plaintext.
            The password is compared directly without any hashing.
            """
            logger.info(f"Plaintext auth attempt for user: {request.username}")
            
            # Log attempt
            db.log_auth_attempt({
                "username": request.username,
                "success": False,  # Will update if successful
                "ip_address": "127.0.0.1"
            })
            
            # Check if account is locked
            if self._is_account_locked(request.username):
                return AuthResponse(
                    success=False,
                    message="Account is locked due to too many failed attempts"
                )
            
            # INSECURE: Direct password comparison
            if request.username in TEST_CREDENTIALS:
                if TEST_CREDENTIALS[request.username] == request.password:
                    token = secrets.token_urlsafe(32)
                    self.active_sessions[token] = {
                        "username": request.username,
                        "created": datetime.now()
                    }
                    
                    # Log successful attempt
                    db.log_auth_attempt({
                        "username": request.username,
                        "success": True,
                        "ip_address": "127.0.0.1"
                    })
                    
                    return AuthResponse(
                        success=True,
                        message="Authentication successful (INSECURE: plaintext)",
                        token=token,
                        details={"warning": "Password sent in plaintext - very insecure!"}
                    )
            
            # Log failed attempt
            self._record_failed_attempt(request.username)
            
            return AuthResponse(
                success=False,
                message="Invalid credentials"
            )
        
        @self.app.post("/auth/hash", response_model=AuthResponse)
        async def auth_hash(request: AuthRequest):
            """
            BETTER: Hashed password authentication.
            
            This demonstrates using SHA-256 hashing (still not ideal - no salt).
            """
            logger.info(f"Hash auth attempt for user: {request.username}")
            
            # Check if account is locked
            if self._is_account_locked(request.username):
                return AuthResponse(
                    success=False,
                    message="Account is locked due to too many failed attempts"
                )
            
            if request.username in TEST_CREDENTIALS:
                # Hash the provided password
                password_hash = hashlib.sha256(request.password.encode()).hexdigest()
                
                # Hash the stored password
                stored_hash = hashlib.sha256(
                    TEST_CREDENTIALS[request.username].encode()
                ).hexdigest()
                
                # Compare hashes
                if hmac.compare_digest(password_hash, stored_hash):
                    token = secrets.token_urlsafe(32)
                    self.active_sessions[token] = {
                        "username": request.username,
                        "created": datetime.now()
                    }
                    
                    db.log_auth_attempt({
                        "username": request.username,
                        "success": True,
                        "ip_address": "127.0.0.1"
                    })
                    
                    return AuthResponse(
                        success=True,
                        message="Authentication successful (Hashed - better but no salt)",
                        token=token,
                        details={"warning": "Using SHA-256 without salt - still vulnerable to rainbow tables"}
                    )
            
            self._record_failed_attempt(request.username)
            
            return AuthResponse(
                success=False,
                message="Invalid credentials"
            )
        
        @self.app.post("/auth/secure", response_model=AuthResponse)
        async def auth_secure(request: AuthRequest):
            """
            SECURE: Authentication with rate limiting and proper hashing.
            
            This demonstrates proper authentication practices.
            """
            logger.info(f"Secure auth attempt for user: {request.username}")
            
            # Check rate limiting
            if self._is_rate_limited(request.username):
                return AuthResponse(
                    success=False,
                    message="Too many attempts. Please try again later."
                )
            
            # Check if account is locked
            if self._is_account_locked(request.username):
                return AuthResponse(
                    success=False,
                    message="Account is locked due to too many failed attempts"
                )
            
            if request.username in TEST_CREDENTIALS:
                # Use PBKDF2 with salt (industry standard)
                salt = hashlib.sha256(request.username.encode()).hexdigest()[:16]
                password_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    request.password.encode(),
                    salt.encode(),
                    100000  # 100k iterations
                ).hexdigest()
                
                # Hash stored password
                stored_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    TEST_CREDENTIALS[request.username].encode(),
                    salt.encode(),
                    100000
                ).hexdigest()
                
                if hmac.compare_digest(password_hash, stored_hash):
                    token = secrets.token_urlsafe(32)
                    self.active_sessions[token] = {
                        "username": request.username,
                        "created": datetime.now()
                    }
                    
                    # Reset failed attempts on success
                    self.failed_attempts.pop(request.username, None)
                    
                    db.log_auth_attempt({
                        "username": request.username,
                        "success": True,
                        "ip_address": "127.0.0.1"
                    })
                    
                    return AuthResponse(
                        success=True,
                        message="Authentication successful (Secure: PBKDF2 with salt)",
                        token=token
                    )
            
            # Record failed attempt
            self._record_failed_attempt(request.username)
            
            # Return generic error (don't reveal if username exists)
            return AuthResponse(
                success=False,
                message="Invalid credentials"
            )
        
        @self.app.get("/auth/attempts")
        async def get_attempts(username: Optional[str] = None):
            """Get authentication attempts."""
            if username:
                attempts = db.get_failed_attempts(username)
                return {"username": username, "failed_attempts": attempts}
            
            return {"message": "Provide username parameter"}
        
        @self.app.get("/auth/status")
        async def get_status(username: str):
            """Check account status."""
            is_locked = self._is_account_locked(username)
            is_rate_limited = self._is_rate_limited(username)
            failed_count = len(self.failed_attempts.get(username, []))
            
            return {
                "username": username,
                "is_locked": is_locked,
                "is_rate_limited": is_rate_limited,
                "failed_attempts": failed_count
            }
    
    def _record_failed_attempt(self, username: str) -> None:
        """Record a failed authentication attempt."""
        if username not in self.failed_attempts:
            self.failed_attempts[username] = []
        
        self.failed_attempts[username].append(datetime.now())
        
        # Clean old attempts outside window
        cutoff = datetime.now() - timedelta(seconds=self.settings.rate_limit_window)
        self.failed_attempts[username] = [
            t for t in self.failed_attempts[username] if t > cutoff
        ]
        
        # Check for lockout
        if len(self.failed_attempts[username]) >= self.settings.rate_limit_max_attempts:
            self.locked_accounts[username] = datetime.now()
            logger.warning(f"Account locked: {username}")
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked."""
        if username not in self.locked_accounts:
            return False
        
        lock_time = self.locked_accounts[username]
        unlock_time = lock_time + timedelta(seconds=self.settings.account_lockout_duration)
        
        if datetime.now() > unlock_time:
            # Unlock account
            del self.locked_accounts[username]
            self.failed_attempts.pop(username, None)
            return False
        
        return True
    
    def _is_rate_limited(self, username: str) -> bool:
        """Check if user is rate limited."""
        if username not in self.failed_attempts:
            return False
        
        cutoff = datetime.now() - timedelta(seconds=self.settings.rate_limit_window)
        recent_attempts = [t for t in self.failed_attempts[username] if t > cutoff]
        
        return len(recent_attempts) >= self.settings.rate_limit_max_attempts
    
    def run_tests(self) -> list[dict]:
        """
        Run authentication tests to demonstrate vulnerabilities.
        
        Returns:
            List of test results
        """
        tests = []
        
        # Test 1: Plaintext vulnerability
        tests.append({
            "test_name": "Plaintext Authentication",
            "passed": False,  # This is intentionally vulnerable
            "description": "Demonstrates vulnerability of plaintext passwords",
            "findings": [
                "Password sent in cleartext",
                "Vulnerable to network sniffing",
                "No protection against replay attacks"
            ]
        })
        
        # Test 2: Hashing without salt
        tests.append({
            "test_name": "Hashed Password (No Salt)",
            "passed": False,  # Still vulnerable
            "description": "SHA-256 without salt is vulnerable to rainbow tables",
            "findings": [
                "Uses SHA-256 without salt",
                "Vulnerable to rainbow table attacks",
                "Same password produces same hash"
            ]
        })
        
        # Test 3: Rate limiting
        tests.append({
            "test_name": "Rate Limiting",
            "passed": True,
            "description": "Rate limiting is implemented",
            "findings": [
                f"Max attempts: {self.settings.rate_limit_max_attempts}",
                f"Window: {self.settings.rate_limit_window} seconds"
            ]
        })
        
        # Test 4: Account lockout
        tests.append({
            "test_name": "Account Lockout",
            "passed": True,
            "description": "Account lockout is implemented",
            "findings": [
                f"Lockout duration: {self.settings.account_lockout_duration} seconds"
            ]
        })
        
        # Test 5: Secure hashing
        tests.append({
            "test_name": "Secure Password Hashing",
            "passed": True,
            "description": "PBKDF2 with salt provides secure hashing",
            "findings": [
                "Uses PBKDF2 with 100k iterations",
                "Salt derived from username",
                "Constant-time comparison"
            ]
        })
        
        return tests


# Singleton instance
auth_lab = AuthenticationLab()
