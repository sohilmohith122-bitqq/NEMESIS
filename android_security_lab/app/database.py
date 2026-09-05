"""
Android Security Lab - Database Module

SQLite database operations using SQLAlchemy.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, JSON, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings

Base = declarative_base()


import uuid

class DeviceRecord(Base):
    """Device database record."""
    __tablename__ = "devices"
    
    id = Column(String(8), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    name = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    mac_address = Column(String(17), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    status = Column(String(20), default="DISCOVERED")
    services = Column(JSON, default=list)
    adb_serial = Column(String(50), nullable=True)
    last_seen = Column(DateTime, default=datetime.now)
    authorized_at = Column(DateTime, nullable=True)
    authorization_expires = Column(DateTime, nullable=True)
    pairing_token = Column(String(100), nullable=True)
    pairing_token_expires = Column(DateTime, nullable=True)
    public_key = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


import uuid

class AuditRecord(Base):
    """Security audit database record."""
    __tablename__ = "audits"
    
    id = Column(String(8), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    device_id = Column(String(8), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    score = Column(Integer, nullable=False)
    findings = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)


class AuthAttemptRecord(Base):
    """Authentication attempt database record."""
    __tablename__ = "auth_attempts"
    
    id = Column(String(8), primary_key=True)
    username = Column(String(100), nullable=False)
    success = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.now)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)


class Database:
    """Database manager class."""
    
    def __init__(self):
        settings = get_settings()
        self.engine = create_engine(settings.database_url, echo=settings.debug)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def create_device(self, device_data: dict) -> DeviceRecord:
        """Create a new device record."""
        session = self.get_session()
        try:
            device = DeviceRecord(**device_data)
            session.add(device)
            session.commit()
            session.refresh(device)
            return device
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_device(self, device_id: str) -> Optional[DeviceRecord]:
        """Get device by ID."""
        session = self.get_session()
        try:
            return session.query(DeviceRecord).filter(DeviceRecord.id == device_id).first()
        finally:
            session.close()
    
    def get_all_devices(self) -> list[DeviceRecord]:
        """Get all devices."""
        session = self.get_session()
        try:
            return session.query(DeviceRecord).all()
        finally:
            session.close()
    
    def update_device(self, device_id: str, update_data: dict) -> Optional[DeviceRecord]:
        """Update device record."""
        session = self.get_session()
        try:
            device = session.query(DeviceRecord).filter(DeviceRecord.id == device_id).first()
            if device:
                for key, value in update_data.items():
                    setattr(device, key, value)
                device.updated_at = datetime.now()
                session.commit()
                session.refresh(device)
            return device
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_device(self, device_id: str) -> bool:
        """Delete device record."""
        session = self.get_session()
        try:
            device = session.query(DeviceRecord).filter(DeviceRecord.id == device_id).first()
            if device:
                session.delete(device)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def create_audit(self, audit_data: dict) -> AuditRecord:
        """Create security audit record."""
        session = self.get_session()
        try:
            audit = AuditRecord(**audit_data)
            session.add(audit)
            session.commit()
            session.refresh(audit)
            return audit
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_device_audits(self, device_id: str) -> list[AuditRecord]:
        """Get all audits for a device."""
        session = self.get_session()
        try:
            return session.query(AuditRecord).filter(
                AuditRecord.device_id == device_id
            ).order_by(AuditRecord.timestamp.desc()).all()
        finally:
            session.close()
    
    def log_auth_attempt(self, attempt_data: dict) -> AuthAttemptRecord:
        """Log authentication attempt."""
        session = self.get_session()
        try:
            attempt = AuthAttemptRecord(**attempt_data)
            session.add(attempt)
            session.commit()
            session.refresh(attempt)
            return attempt
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_failed_attempts(self, username: str, window_seconds: int = 300) -> int:
        """Get failed attempts for username within time window."""
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(seconds=window_seconds)
            return session.query(AuthAttemptRecord).filter(
                AuthAttemptRecord.username == username,
                AuthAttemptRecord.success == False,
                AuthAttemptRecord.timestamp >= cutoff
            ).count()
        finally:
            session.close()


# Global database instance
db = Database()
