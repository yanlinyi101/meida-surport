"""
Role and Permission models with RBAC relationships.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from ..db.base import Base


# Association tables for many-to-many relationships
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)


class Role(Base):
    """Role database model."""
    
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles cannot be deleted or renamed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class Permission(Base):
    """Permission database model."""
    
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, index=True, nullable=False)  # e.g., "users.read"
    description = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, default="general")  # users/roles/permissions/audit/tickets/warranty/centers/ai/geo
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
    def __repr__(self):
        return f"<Permission(id={self.id}, code='{self.code}')>"


# Pydantic schemas
class PermissionBase(BaseModel):
    """Base permission schema."""
    code: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    category: str = Field(..., min_length=1, max_length=50)


class PermissionCreate(PermissionBase):
    """Schema for creating a permission."""
    pass


class PermissionInDB(PermissionBase):
    """Permission schema with database fields."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PermissionResponse(PermissionInDB):
    """Permission schema for API responses."""
    pass


class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    is_system: bool = False


class RoleCreate(RoleBase):
    """Schema for creating a role."""
    permission_codes: List[str] = []  # List of permission codes to assign


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    permission_codes: Optional[List[str]] = None
    # Note: is_system cannot be updated via API for security


class RoleInDB(RoleBase):
    """Role schema with database fields."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleResponse(RoleInDB):
    """Role schema for API responses."""
    permissions: List[PermissionResponse] = []
    permissions_count: int = 0  # Number of permissions assigned to this role
    user_count: int = 0  # Number of users with this role


class UserRoleAssignment(BaseModel):
    """Schema for assigning roles to users."""
    user_id: int
    role_names: List[str] 