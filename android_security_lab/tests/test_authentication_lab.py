"""
Android Security Lab - Authentication Lab Tests
"""

import pytest
from app.security.authentication_lab import auth_lab


class TestAuthenticationLab:
    """Test authentication lab functionality."""
    
    def test_lab_initialization(self):
        """Test authentication lab initializes correctly."""
        assert auth_lab is not None
        assert auth_lab.settings is not None
    
    def test_test_credentials_exist(self):
        """Test that test credentials are defined."""
        from app.security.authentication_lab import TEST_CREDENTIALS
        
        assert "student" in TEST_CREDENTIALS
        assert "admin" in TEST_CREDENTIALS
        assert "test" in TEST_CREDENTIALS
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        username = "testuser"
        
        # Simulate multiple failed attempts
        for _ in range(5):
            auth_lab._record_failed_attempt(username)
        
        # Check if rate limited
        assert auth_lab._is_rate_limited(username) is True
    
    def test_account_lockout(self):
        """Test account lockout functionality."""
        username = "lockoutuser"
        
        # Simulate max failed attempts
        for _ in range(5):
            auth_lab._record_failed_attempt(username)
        
        # Check if account is locked
        assert auth_lab._is_account_locked(username) is True
    
    def test_run_tests(self):
        """Test that authentication tests run."""
        tests = auth_lab.run_tests()
        
        assert len(tests) > 0
        assert all("test_name" in t for t in tests)
        assert all("passed" in t for t in tests)
    
    def test_plaintext_vulnerability_detected(self):
        """Test that plaintext authentication is flagged as vulnerable."""
        tests = auth_lab.run_tests()
        
        plaintext_test = next(t for t in tests if "Plaintext" in t["test_name"])
        assert plaintext_test["passed"] is False  # Should be vulnerable
    
    def test_hashing_vulnerability_detected(self):
        """Test that hashing without salt is flagged as vulnerable."""
        tests = auth_lab.run_tests()
        
        hash_test = next(t for t in tests if "Hashed" in t["test_name"])
        assert hash_test["passed"] is False  # Should be vulnerable
    
    def test_rate_limiting_implemented(self):
        """Test that rate limiting is implemented."""
        tests = auth_lab.run_tests()
        
        rate_test = next(t for t in tests if "Rate Limiting" in t["test_name"])
        assert rate_test["passed"] is True
    
    def test_account_lockout_implemented(self):
        """Test that account lockout is implemented."""
        tests = auth_lab.run_tests()
        
        lockout_test = next(t for t in tests if "Account Lockout" in t["test_name"])
        assert lockout_test["passed"] is True
    
    def test_secure_hashing_implemented(self):
        """Test that secure hashing is implemented."""
        tests = auth_lab.run_tests()
        
        secure_test = next(t for t in tests if "Secure" in t["test_name"])
        assert secure_test["passed"] is True
