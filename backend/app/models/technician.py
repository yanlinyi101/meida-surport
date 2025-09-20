"""
Technician model for service technicians.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from ..db.base import Base


class Technician(Base):
    """
    Technician model for service technicians.
    """
    __tablename__ = "technicians"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    
    # Basic information
    name = Column(String(100), nullable=False, comment="技师姓名")
    phone_masked = Column(String(20), nullable=False, comment="脱敏电话号码")
    
    # Service center association
    center_id = Column(String(36), nullable=True, comment="所属服务中心ID")
    
    # Skills and capabilities (stored as JSON string)
    skills = Column(Text, nullable=True, comment="技能描述JSON")
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, comment="是否活跃")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    
    # Relationships
    tickets = relationship("Ticket", back_populates="technician")
    
    # Indexes
    __table_args__ = (
        Index('idx_technician_center_id', 'center_id'),
        Index('idx_technician_is_active', 'is_active'),
    )

    def __repr__(self):
        return f"<Technician(id={self.id}, name={self.name}, active={self.is_active})>"


# Pydantic schemas
class TechnicianBase(BaseModel):
    """Base technician schema."""
    name: str = Field(..., min_length=1, max_length=100)
    phone_masked: str = Field(..., max_length=20)
    center_id: Optional[UUID] = None
    skills: Optional[str] = None
    is_active: bool = True


class TechnicianCreate(TechnicianBase):
    """Schema for creating a new technician."""
    pass


class TechnicianUpdate(BaseModel):
    """Schema for updating a technician."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_masked: Optional[str] = Field(None, max_length=20)
    center_id: Optional[UUID] = None
    skills: Optional[str] = None
    is_active: Optional[bool] = None


class TechnicianResponse(TechnicianBase):
    """Schema for technician response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    assigned_tickets_count: Optional[int] = None

    class Config:
        from_attributes = True


class TechnicianListResponse(BaseModel):
    """Schema for technician list response."""
    technicians: List[TechnicianResponse]
    total: int
    page: int
    page_size: int 