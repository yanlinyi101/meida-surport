"""
Audit log model for tracking user actions.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from ..db.base import Base


class AuditLog(Base):
    """Audit log database model."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Null for system actions
    action = Column(String(100), nullable=False, index=True)  # e.g., "user.login", "user.create"
    target_type = Column(String(50), nullable=True, index=True)  # e.g., "user", "role"
    target_id = Column(String(50), nullable=True, index=True)  # ID of the target object
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    details = Column(JSON, nullable=True)  # Additional context as JSON
    
    # Relationships
    actor_user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', actor_user_id={self.actor_user_id})>"


# Pydantic schemas
class AuditLogBase(BaseModel):
    """Base audit log schema."""
    action: str = Field(..., min_length=1, max_length=100)
    target_type: Optional[str] = Field(None, max_length=50)
    target_id: Optional[str] = Field(None, max_length=50)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class AuditLogCreate(AuditLogBase):
    """Schema for creating an audit log entry."""
    actor_user_id: Optional[int] = None


class AuditLogInDB(AuditLogBase):
    """Audit log schema with database fields."""
    id: int
    timestamp: datetime
    actor_user_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class AuditLogResponse(AuditLogInDB):
    """Audit log schema for API responses."""
    actor_email: Optional[str] = None  # Email of the actor user
    actor_display_name: Optional[str] = None  # Display name of the actor user


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""
    actor_user_id: Optional[int] = None
    action: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100) 