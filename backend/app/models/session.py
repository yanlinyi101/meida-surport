"""
Session token model for refresh token management.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from ..db.base import Base


class SessionToken(Base):
    """Session token database model for refresh tokens."""
    
    __tablename__ = "session_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    refresh_token_hash = Column(String(255), nullable=False, index=True)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)  # Supports IPv6
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="session_tokens")
    
    def __repr__(self):
        return f"<SessionToken(id={self.id}, user_id={self.user_id}, revoked={self.revoked})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not revoked and not expired)."""
        return not self.revoked and not self.is_expired


# Pydantic schemas
class SessionTokenBase(BaseModel):
    """Base session token schema."""
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class SessionTokenInDB(SessionTokenBase):
    """Session token schema with database fields."""
    id: int
    user_id: int
    expires_at: datetime
    revoked: bool
    created_at: datetime
    revoked_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SessionTokenResponse(SessionTokenInDB):
    """Session token schema for API responses."""
    is_expired: bool
    is_valid: bool 