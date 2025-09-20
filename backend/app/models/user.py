"""
User model and related schemas.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, Field
from ..db.base import Base


class User(Base):
    """User database model."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)
    twofa_secret = Column(String(32), nullable=True)  # Base32 encoded secret
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - use string references to avoid circular imports
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    session_tokens = relationship("SessionToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="actor_user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', display_name='{self.display_name}')>"


# Pydantic schemas for API
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """User schema with database fields."""
    id: int
    is_active: bool
    is_2fa_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    """User schema for API responses."""
    roles: List[str] = []  # Role names
    permissions: List[str] = []  # Permission codes (deprecated, use effective_permissions)
    effective_permissions: List[str] = []  # Aggregated permission codes from all roles


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str
    otp: Optional[str] = Field(None, pattern=r"^\d{6}$")  # 6-digit OTP


class UserRegister(UserCreate):
    """Schema for user registration."""
    pass


class PasswordReset(BaseModel):
    """Schema for password reset."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordForgot(BaseModel):
    """Schema for forgot password."""
    email: EmailStr


class TwoFASetup(BaseModel):
    """Schema for 2FA setup response."""
    secret: str
    qr_code: str  # Base64 encoded QR code
    backup_codes: List[str]


class TwoFAVerify(BaseModel):
    """Schema for 2FA verification."""
    otp: str = Field(..., pattern=r"^\d{6}$")


class ChangePassword(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128) 