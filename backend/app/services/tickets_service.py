"""
Tickets service for managing ticket lifecycle and business logic.
"""
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from fastapi import HTTPException, status

from ..models.ticket import Ticket, TicketStatus, TicketEvent
from ..models.technician import Technician
from ..models.ticket_image import TicketImage, ImageType
from ..models.user import User


class TicketsService:
    """Service for managing tickets and their lifecycle."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Status machine validation
    ALLOWED_TRANSITIONS = {
        TicketStatus.BOOKED: [TicketStatus.CONFIRMED, TicketStatus.CANCELED],
        TicketStatus.CONFIRMED: [TicketStatus.ASSIGNED, TicketStatus.CANCELED],
        TicketStatus.ASSIGNED: [TicketStatus.IN_PROGRESS, TicketStatus.CONFIRMED, TicketStatus.CANCELED],
        TicketStatus.IN_PROGRESS: [TicketStatus.COMPLETED, TicketStatus.ASSIGNED, TicketStatus.CANCELED],
        TicketStatus.COMPLETED: [],  # Terminal state
        TicketStatus.CANCELED: [],   # Terminal state
    }
    
    def validate_status_transition(self, current_status: TicketStatus, new_status: TicketStatus) -> bool:
        """
        Validate if status transition is allowed.
        
        Args:
            current_status: Current ticket status
            new_status: Target ticket status
            
        Returns:
            True if transition is allowed, False otherwise
        """
        return new_status in self.ALLOWED_TRANSITIONS.get(current_status, [])
    
    def get_ticket_by_id(self, ticket_id: UUID, with_relations: bool = False) -> Optional[Ticket]:
        """
        Get ticket by ID.
        
        Args:
            ticket_id: The ticket ID
            with_relations: Whether to load relationships
            
        Returns:
            Ticket instance or None if not found
        """
        query = self.db.query(Ticket)
        
        if with_relations:
            query = query.options(
                joinedload(Ticket.technician),
                joinedload(Ticket.images),
                joinedload(Ticket.events).joinedload(TicketEvent.actor)
            )
        
        return query.filter(Ticket.id == ticket_id).first()
    
    def create_ticket_event(
        self, 
        ticket_id: UUID, 
        action: str, 
        actor_user_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> TicketEvent:
        """
        Create a ticket event for audit trail.
        
        Args:
            ticket_id: The ticket ID
            action: The action performed
            actor_user_id: ID of the user who performed the action
            details: Additional details as dictionary
            
        Returns:
            Created TicketEvent instance
        """
        event = TicketEvent(
            ticket_id=ticket_id,
            actor_user_id=actor_user_id,
            action=action,
            details_json=json.dumps(details) if details else None
        )
        self.db.add(event)
        return event
    
    def confirm_ticket(self, ticket_id: UUID, actor_user_id: Optional[UUID] = None) -> Ticket:
        """
        Confirm a booked ticket.
        
        Args:
            ticket_id: The ticket ID
            actor_user_id: ID of the user confirming the ticket
            
        Returns:
            Updated ticket
            
        Raises:
            HTTPException: If ticket not found or invalid status transition
        """
        ticket = self.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工单不存在"
            )
        
        if not self.validate_status_transition(ticket.status, TicketStatus.CONFIRMED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法从状态 {ticket.status.value} 转换到 CONFIRMED"
            )
        
        # Update ticket
        ticket.status = TicketStatus.CONFIRMED
        ticket.updated_at = datetime.utcnow()
        
        # Create event
        self.create_ticket_event(ticket_id, "CONFIRM", actor_user_id)
        
        self.db.commit()
        return ticket
    
    def get_available_technicians(self, center_id: Optional[UUID] = None) -> List[Technician]:
        """
        Get available technicians for assignment.
        
        Args:
            center_id: Optional center ID to filter by
            
        Returns:
            List of available technicians
        """
        query = self.db.query(Technician).filter(Technician.is_active == True)
        
        if center_id:
            query = query.filter(Technician.center_id == center_id)
        
        return query.all()
    
    def get_technician_workload(self, technician_id: UUID, days: int = 7) -> int:
        """
        Get technician's current workload (assigned/in-progress tickets in last N days).
        
        Args:
            technician_id: The technician ID
            days: Number of days to look back
            
        Returns:
            Number of active tickets
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        count = self.db.query(Ticket).filter(
            and_(
                Ticket.technician_id == technician_id,
                Ticket.status.in_([TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS]),
                Ticket.created_at >= since_date
            )
        ).count()
        
        return count
    
    def auto_assign_technician(
        self, 
        center_id: Optional[UUID] = None
    ) -> Optional[Technician]:
        """
        Automatically assign a technician based on workload.
        
        Args:
            center_id: Optional center ID to filter by
            
        Returns:
            Selected technician or None if none available
        """
        available_technicians = self.get_available_technicians(center_id)
        
        if not available_technicians:
            return None
        
        # Find technician with least workload
        best_technician = None
        min_workload = float('inf')
        
        for technician in available_technicians:
            workload = self.get_technician_workload(technician.id)
            if workload < min_workload:
                min_workload = workload
                best_technician = technician
        
        return best_technician
    
    def assign_ticket(
        self, 
        ticket_id: UUID, 
        technician_id: Optional[UUID] = None,
        auto_assign: bool = False,
        actor_user_id: Optional[UUID] = None,
        version: int = None,
        **kwargs
    ) -> Ticket:
        """
        Assign a ticket to a technician.
        
        Args:
            ticket_id: The ticket ID
            technician_id: ID of technician to assign (if not auto-assigning)
            auto_assign: Whether to auto-assign based on workload
            actor_user_id: ID of the user performing the assignment
            version: Current version for optimistic locking
            **kwargs: Additional assignment details
            
        Returns:
            Updated ticket
            
        Raises:
            HTTPException: If ticket not found, invalid status, or version conflict
        """
        ticket = self.get_ticket_by_id(ticket_id)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工单不存在"
            )
        
        # Optimistic locking check
        if version is not None and ticket.version != version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="工单已被其他用户修改，请刷新后重试"
            )
        
        if not self.validate_status_transition(ticket.status, TicketStatus.ASSIGNED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法从状态 {ticket.status.value} 分配工单"
            )
        
        # Determine technician
        if auto_assign:
            technician = self.auto_assign_technician(ticket.center_id)
            if not technician:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="没有可用的技师进行自动分配"
                )
            technician_id = technician.id
        else:
            if not technician_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="必须指定技师ID或启用自动分配"
                )
            
            # Verify technician exists and is active
            technician = self.db.query(Technician).filter(
                and_(
                    Technician.id == technician_id,
                    Technician.is_active == True
                )
            ).first()
            
            if not technician:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="指定的技师不存在或不可用"
                )
        
        # Update ticket
        ticket.status = TicketStatus.ASSIGNED
        ticket.technician_id = technician_id
        ticket.updated_at = datetime.utcnow()
        ticket.version += 1
        
        # Create event with assignment details
        event_details = {
            "technician_id": str(technician_id),
            "technician_name": technician.name,
            "assignment_method": "auto" if auto_assign else "manual",
            **kwargs
        }
        self.create_ticket_event(ticket_id, "ASSIGN", actor_user_id, event_details)
        
        self.db.commit()
        return ticket
    
    def complete_ticket(self, ticket_id: UUID, actor_user_id: Optional[UUID] = None) -> Ticket:
        """
        Complete a ticket.
        
        Args:
            ticket_id: The ticket ID
            actor_user_id: ID of the user completing the ticket
            
        Returns:
            Updated ticket
            
        Raises:
            HTTPException: If ticket not found, invalid status, or missing receipt
        """
        ticket = self.get_ticket_by_id(ticket_id, with_relations=True)
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工单不存在"
            )
        
        if ticket.status not in [TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"只能完成已分配或进行中的工单，当前状态: {ticket.status.value}"
            )
        
        # Check if ticket has at least one receipt image
        receipt_count = self.db.query(TicketImage).filter(
            and_(
                TicketImage.ticket_id == ticket_id,
                TicketImage.type == ImageType.RECEIPT
            )
        ).count()
        
        if receipt_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须上传至少一张售后回执图片才能完成工单"
            )
        
        # Update ticket
        ticket.status = TicketStatus.COMPLETED
        ticket.completed_at = datetime.utcnow()
        ticket.updated_at = datetime.utcnow()
        
        # Create event
        self.create_ticket_event(ticket_id, "COMPLETE", actor_user_id)
        
        self.db.commit()
        return ticket
    
    def list_tickets(
        self,
        status: Optional[TicketStatus] = None,
        technician_id: Optional[UUID] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List tickets with filtering and pagination.
        
        Args:
            status: Filter by status
            technician_id: Filter by technician
            date_from: Filter by appointment date from (YYYY-MM-DD)
            date_to: Filter by appointment date to (YYYY-MM-DD)
            search_query: Search in customer name, address, or issue
            page: Page number (1-based)
            page_size: Items per page
            
        Returns:
            Dictionary with tickets, total count, and pagination info
        """
        query = self.db.query(Ticket).options(joinedload(Ticket.technician))
        
        # Apply filters
        if status:
            query = query.filter(Ticket.status == status)
        
        if technician_id:
            query = query.filter(Ticket.technician_id == technician_id)
        
        if date_from:
            query = query.filter(Ticket.appointment_date >= date_from)
        
        if date_to:
            query = query.filter(Ticket.appointment_date <= date_to)
        
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    Ticket.customer_name.ilike(search_pattern),
                    Ticket.address.ilike(search_pattern),
                    Ticket.issue_desc.ilike(search_pattern)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        tickets = query.order_by(desc(Ticket.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return {
            "tickets": tickets,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        } 