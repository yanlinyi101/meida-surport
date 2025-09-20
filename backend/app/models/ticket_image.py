"""
Ticket image model for receipt and documentation.
"""
import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from ..db.base import Base


class ImageType(str, enum.Enum):
    """Image type enumeration."""
    RECEIPT = "RECEIPT"     # 售后回执
    BEFORE = "BEFORE"       # 维修前照片
    AFTER = "AFTER"         # 维修后照片
    PARTS = "PARTS"         # 配件照片


class TicketImage(Base):
    """
    Ticket image model for storing receipt and documentation images.
    """
    __tablename__ = "ticket_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    
    # Image details
    type = Column(
        Enum(ImageType), 
        nullable=False, 
        default=ImageType.RECEIPT,
        comment="图片类型"
    )
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    mime_type = Column(String(100), nullable=False, comment="MIME类型")
    size_bytes = Column(Integer, nullable=False, comment="文件大小(字节)")
    checksum_sha256 = Column(String(64), nullable=False, comment="SHA256校验和")
    
    # Upload info
    uploaded_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="上传时间")
    
    # Relationships
    ticket = relationship("Ticket", back_populates="images")
    uploaded_by = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_ticket_image_ticket_id', 'ticket_id'),
        Index('idx_ticket_image_type', 'type'),
        Index('idx_ticket_image_uploaded_at', 'uploaded_at'),
    )

    def __repr__(self):
        return f"<TicketImage(id={self.id}, type={self.type}, ticket_id={self.ticket_id})>"


# Pydantic schemas
class TicketImageBase(BaseModel):
    """Base ticket image schema."""
    ticket_id: UUID
    type: ImageType = ImageType.RECEIPT
    file_name: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=500)
    mime_type: str = Field(..., max_length=100)
    size_bytes: int = Field(..., gt=0)
    checksum_sha256: str = Field(..., max_length=64)


class TicketImageCreate(TicketImageBase):
    """Schema for creating a new ticket image."""
    uploaded_by_user_id: Optional[UUID] = None


class TicketImageResponse(TicketImageBase):
    """Schema for ticket image response."""
    id: UUID
    uploaded_by_user_id: Optional[UUID]
    uploaded_at: datetime
    
    # Computed fields
    url: Optional[str] = None  # Download URL

    class Config:
        from_attributes = True


class TicketImageListResponse(BaseModel):
    """Schema for ticket image list response."""
    images: list[TicketImageResponse]
    total: int 