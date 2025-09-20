"""
Tickets API for fault management workflow.
"""
import hashlib
from datetime import date, time
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.deps import get_current_active_user, require_permissions
from ..db.session import get_db
from ..models.user import User
from ..models.ticket import (
    Ticket, TicketStatus, TicketCreate, TicketResponse, TicketUpdate,
    TicketEventResponse
)
from ..models.technician import Technician, TechnicianResponse
from ..models.ticket_image import TicketImage, TicketImageResponse, ImageType
from ..services.tickets_service import TicketsService
from ..services.storage_service import StorageService
from ..services.audit_service import AuditService

# Create router
router = APIRouter(tags=["Tickets"])


# Request/Response models
class BookingRequest(BaseModel):
    """Public booking request model."""
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=5, max_length=30)
    address: str = Field(..., min_length=1, max_length=200)
    date: date
    time: time
    issue: str = Field(..., min_length=1, max_length=500)


class BookingResponse(BaseModel):
    """Public booking response model."""
    ok: bool
    ticket_id: UUID
    message: str


class TicketConfirmResponse(BaseModel):
    """Ticket confirmation response."""
    ok: bool
    status: TicketStatus


class TicketAssignRequest(BaseModel):
    """Ticket assignment request."""
    technician_id: Optional[UUID] = None
    auto: bool = False
    lat: Optional[float] = None
    lng: Optional[float] = None
    note: Optional[str] = None
    version: int


class TicketAssignResponse(BaseModel):
    """Ticket assignment response."""
    ok: bool
    technician: TechnicianResponse
    status: TicketStatus
    version: int


class TicketCompleteResponse(BaseModel):
    """Ticket completion response."""
    ok: bool
    status: TicketStatus


class TicketListResponse(BaseModel):
    """Ticket list response."""
    tickets: List[TicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TicketDetailResponse(TicketResponse):
    """Detailed ticket response with events and images."""
    events: List[TicketEventResponse] = []
    images: List[TicketImageResponse] = []


class ImageUploadResponse(BaseModel):
    """Image upload response."""
    ok: bool
    image: TicketImageResponse


def hash_phone(phone: str) -> str:
    """Hash phone number for privacy."""
    return hashlib.sha256(phone.encode()).hexdigest()


# Public endpoints (no authentication required)
@router.post("/public/booking", response_model=BookingResponse)
async def submit_booking(
    booking: BookingRequest,
    db: Session = Depends(get_db)
):
    """
    Submit a new booking (public endpoint).
    Creates a ticket with BOOKED status.
    """
    tickets_service = TicketsService(db)
    
    # Create ticket
    ticket_data = TicketCreate(
        customer_name=booking.name,
        customer_phone_hash=hash_phone(booking.phone),
        address=booking.address,
        appointment_date=booking.date,
        appointment_time=booking.time,
        issue_desc=booking.issue
    )
    
    ticket = Ticket(**ticket_data.dict())
    db.add(ticket)
    
    # Create initial event
    tickets_service.create_ticket_event(
        ticket.id, 
        "CONFIRM", 
        details={"source": "public_booking"}
    )
    
    db.commit()
    
    return BookingResponse(
        ok=True,
        ticket_id=ticket.id,
        message="预约已提交，我们将尽快与您确认"
    )


# Authenticated endpoints
@router.post("/tickets/{ticket_id}/confirm", response_model=TicketConfirmResponse)
async def confirm_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.write"]))
):
    """Confirm a booked ticket."""
    tickets_service = TicketsService(db)
    audit_service = AuditService(db)
    
    ticket = tickets_service.confirm_ticket(ticket_id, current_user.id)
    
    # Log audit event
    await audit_service.log_async(
        user_id=current_user.id,
        action="ticket.confirm",
        resource_type="ticket",
        resource_id=str(ticket_id),
        details={"status": ticket.status.value}
    )
    
    return TicketConfirmResponse(
        ok=True,
        status=ticket.status
    )


@router.post("/tickets/{ticket_id}/assign", response_model=TicketAssignResponse)
async def assign_ticket(
    ticket_id: UUID,
    request: TicketAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.assign"]))
):
    """Assign a ticket to a technician."""
    tickets_service = TicketsService(db)
    audit_service = AuditService(db)
    
    ticket = tickets_service.assign_ticket(
        ticket_id=ticket_id,
        technician_id=request.technician_id,
        auto_assign=request.auto,
        actor_user_id=current_user.id,
        version=request.version,
        note=request.note,
        lat=request.lat,
        lng=request.lng
    )
    
    # Get technician info
    technician = db.query(Technician).filter(
        Technician.id == ticket.technician_id
    ).first()
    
    # Log audit event
    await audit_service.log_async(
        user_id=current_user.id,
        action="ticket.assign",
        resource_type="ticket",
        resource_id=str(ticket_id),
        details={
            "technician_id": str(ticket.technician_id),
            "technician_name": technician.name,
            "assignment_method": "auto" if request.auto else "manual",
            "version": ticket.version
        }
    )
    
    return TicketAssignResponse(
        ok=True,
                    technician=TechnicianResponse.model_validate(technician),
        status=ticket.status,
        version=ticket.version
    )


@router.post("/tickets/{ticket_id}/images", response_model=ImageUploadResponse)
async def upload_ticket_image(
    ticket_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.upload"]))
):
    """Upload a receipt image for a ticket."""
    tickets_service = TicketsService(db)
    storage_service = StorageService()
    audit_service = AuditService(db)
    
    # Verify ticket exists
    ticket = tickets_service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在"
        )
    
    # Save file
    file_path, filename, mime_type, size_bytes, checksum = await storage_service.save_ticket_image(
        ticket_id, file
    )
    
    # Create image record
    image = TicketImage(
        ticket_id=ticket_id,
        type=ImageType.RECEIPT,
        file_name=filename,
        file_path=file_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        checksum_sha256=checksum,
        uploaded_by_user_id=current_user.id
    )
    db.add(image)
    
    # Create event
    tickets_service.create_ticket_event(
        ticket_id,
        "UPLOAD_RECEIPT",
        current_user.id,
        {"image_id": str(image.id), "filename": filename}
    )
    
    db.commit()
    
    # Log audit event
    await audit_service.log_async(
        user_id=current_user.id,
        action="ticket.upload",
        resource_type="ticket",
        resource_id=str(ticket_id),
        details={
            "image_id": str(image.id),
            "filename": filename,
            "size_bytes": size_bytes
        }
    )
    
    # Create response with download URL
    image_response = TicketImageResponse.model_validate(image)
    image_response.url = f"/api/files/ticket-receipt/{image.id}"
    
    return ImageUploadResponse(
        ok=True,
        image=image_response
    )


@router.get("/tickets/{ticket_id}/images", response_model=List[TicketImageResponse])
async def get_ticket_images(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.read"]))
):
    """Get all images for a ticket."""
    images = db.query(TicketImage).filter(
        TicketImage.ticket_id == ticket_id
    ).all()
    
    # Add download URLs
    response_images = []
    for image in images:
        image_response = TicketImageResponse.model_validate(image)
        image_response.url = f"/api/files/ticket-receipt/{image.id}"
        response_images.append(image_response)
    
    return response_images


@router.post("/tickets/{ticket_id}/complete", response_model=TicketCompleteResponse)
async def complete_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.complete"]))
):
    """Complete a ticket."""
    tickets_service = TicketsService(db)
    audit_service = AuditService(db)
    
    ticket = tickets_service.complete_ticket(ticket_id, current_user.id)
    
    # Log audit event
    await audit_service.log_async(
        user_id=current_user.id,
        action="ticket.complete",
        resource_type="ticket",
        resource_id=str(ticket_id),
        details={
            "status": ticket.status.value,
            "completed_at": ticket.completed_at.isoformat() if ticket.completed_at else None
        }
    )
    
    return TicketCompleteResponse(
        ok=True,
        status=ticket.status
    )


@router.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: UUID,
    update: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.write"]))
):
    """Update ticket status (for manual status changes)."""
    tickets_service = TicketsService(db)
    audit_service = AuditService(db)
    
    ticket = tickets_service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在"
        )
    
    # Optimistic locking check
    if ticket.version != update.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="工单已被其他用户修改，请刷新后重试"
        )
    
    old_status = ticket.status
    
    if update.status and update.status != old_status:
        if not tickets_service.validate_status_transition(old_status, update.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法从状态 {old_status.value} 转换到 {update.status.value}"
            )
        
        ticket.status = update.status
        ticket.version += 1
        
        # Create event
        tickets_service.create_ticket_event(
            ticket_id,
            "STATUS_CHANGE",
            current_user.id,
            {"old_status": old_status.value, "new_status": update.status.value}
        )
        
        db.commit()
        
        # Log audit event
        await audit_service.log_async(
            user_id=current_user.id,
            action="ticket.status_change",
            resource_type="ticket",
            resource_id=str(ticket_id),
            details={
                "old_status": old_status.value,
                "new_status": update.status.value,
                "version": ticket.version
            }
        )
    
    return {"ok": True, "status": ticket.status, "version": ticket.version}


@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(
    status: Optional[TicketStatus] = None,
    technician_id: Optional[UUID] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.read"]))
):
    """List tickets with filtering and pagination."""
    tickets_service = TicketsService(db)
    
    result = tickets_service.list_tickets(
        status=status,
        technician_id=technician_id,
        date_from=date_from,
        date_to=date_to,
        search_query=q,
        page=page,
        page_size=page_size
    )
    
    tickets_response = [TicketResponse.model_validate(ticket) for ticket in result["tickets"]]
    
    return TicketListResponse(
        tickets=tickets_response,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"]
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket_detail(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.read"]))
):
    """Get detailed ticket information."""
    tickets_service = TicketsService(db)
    
    ticket = tickets_service.get_ticket_by_id(ticket_id, with_relations=True)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工单不存在"
        )
    
    # Convert to response model
    ticket_response = TicketDetailResponse.model_validate(ticket)
    
    # Add events
    ticket_response.events = [
        TicketEventResponse.model_validate(event) for event in ticket.events
    ]
    
    # Add images with URLs
    images_with_urls = []
    for image in ticket.images:
        image_response = TicketImageResponse.model_validate(image)
        image_response.url = f"/api/files/ticket-receipt/{image.id}"
        images_with_urls.append(image_response)
    ticket_response.images = images_with_urls
    
    return ticket_response


# Technician endpoints
@router.get("/technicians", response_model=List[TechnicianResponse])
async def list_technicians(
    center_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.assign"]))
):
    """List available technicians for assignment."""
    tickets_service = TicketsService(db)
    
    technicians = tickets_service.get_available_technicians(center_id)
    
    # Add workload info
    response_technicians = []
    for tech in technicians:
        tech_response = TechnicianResponse.model_validate(tech)
        tech_response.assigned_tickets_count = tickets_service.get_technician_workload(tech.id)
        response_technicians.append(tech_response)
    
    return response_technicians 