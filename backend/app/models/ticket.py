"""
Ticket model for fault management workflow.
"""
import enum
from datetime import date, time, datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, Date, Time, Text, Integer, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from ..db.base import Base


class TicketStatus(str, enum.Enum):
    """Ticket status enumeration."""
    BOOKED = "BOOKED"           # 已预约
    CONFIRMED = "CONFIRMED"     # 已确认
    ASSIGNED = "ASSIGNED"       # 已分配
    IN_PROGRESS = "IN_PROGRESS" # 进行中
    COMPLETED = "COMPLETED"     # 已完成
    CANCELED = "CANCELED"       # 已取消


class Ticket(Base):
    """
    Ticket model for fault management workflow.
    
    Workflow: BOOKED -> CONFIRMED -> ASSIGNED -> IN_PROGRESS -> COMPLETED
    """
    __tablename__ = "tickets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    
    # Customer information
    customer_name = Column(String(100), nullable=False, comment="客户姓名")
    customer_phone_hash = Column(String(64), nullable=False, comment="客户电话哈希值")
    address = Column(Text, nullable=False, comment="服务地址")
    
    # Appointment details
    appointment_date = Column(Date, nullable=False, comment="预约日期")
    appointment_time = Column(Time, nullable=False, comment="预约时间")
    issue_desc = Column(Text, nullable=False, comment="问题描述")
    
    # Status and assignment
    status = Column(
        Enum(TicketStatus), 
        nullable=False, 
        default=TicketStatus.BOOKED,
        comment="工单状态"
    )
    center_id = Column(String(36), nullable=True, comment="服务中心ID")
    technician_id = Column(
        String(36), 
        ForeignKey("technicians.id"), 
        nullable=True,
        comment="分配的技师ID"
    )
    
    # AI integration (optional)
    ai_run_id = Column(String(100), nullable=True, comment="AI工作流运行ID")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # Optimistic locking
    version = Column(Integer, default=1, nullable=False, comment="版本号")
    
    # Relationships
    technician = relationship("Technician", back_populates="tickets")
    images = relationship("TicketImage", back_populates="ticket", cascade="all, delete-orphan")
    events = relationship("TicketEvent", back_populates="ticket", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_ticket_status', 'status'),
        Index('idx_ticket_appointment_date', 'appointment_date'),
        Index('idx_ticket_technician_id', 'technician_id'),
        Index('idx_ticket_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Ticket(id={self.id}, status={self.status}, customer={self.customer_name})>"


class TicketEvent(Base):
    """
    Ticket event log for audit trail.
    """
    __tablename__ = "ticket_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    action = Column(
        Enum("CONFIRM", "ASSIGN", "UPLOAD_RECEIPT", "COMPLETE", "CANCEL", "STATUS_CHANGE", name="ticket_action"),
        nullable=False,
        comment="操作类型"
    )
    details_json = Column(Text, nullable=True, comment="操作详情JSON")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="events")
    actor = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_ticket_event_ticket_id', 'ticket_id'),
        Index('idx_ticket_event_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<TicketEvent(id={self.id}, action={self.action}, ticket_id={self.ticket_id})>"


# Pydantic schemas
class TicketBase(BaseModel):
    """Base ticket schema."""
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_phone_hash: str = Field(..., max_length=64)
    address: str = Field(..., min_length=1)
    appointment_date: date
    appointment_time: time
    issue_desc: str = Field(..., min_length=1)


class TicketCreate(TicketBase):
    """Schema for creating a new ticket."""
    pass


class TicketUpdate(BaseModel):
    """Schema for updating a ticket."""
    status: Optional[TicketStatus] = None
    technician_id: Optional[UUID] = None
    center_id: Optional[UUID] = None
    version: int = Field(..., description="Current version for optimistic locking")


class TicketResponse(TicketBase):
    """Schema for ticket response."""
    id: UUID
    status: TicketStatus
    center_id: Optional[UUID]
    technician_id: Optional[UUID]
    ai_run_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    version: int

    class Config:
        from_attributes = True


class TicketEventCreate(BaseModel):
    """Schema for creating ticket events."""
    ticket_id: UUID
    actor_user_id: Optional[UUID]
    action: str
    details_json: Optional[str]


class TicketEventResponse(BaseModel):
    """Schema for ticket event response."""
    id: UUID
    ticket_id: UUID
    actor_user_id: Optional[UUID]
    action: str
    details_json: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True 