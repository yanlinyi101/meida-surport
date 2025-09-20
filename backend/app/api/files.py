"""
File download API for secure file access.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.deps import get_current_active_user, require_permissions
from ..db.session import get_db
from ..models.user import User
from ..models.ticket_image import TicketImage
from ..services.storage_service import StorageService

# Create router
router = APIRouter(tags=["Files"])


@router.get("/files/ticket-receipt/{image_id}")
async def download_ticket_receipt(
    image_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["tickets.read"]))
):
    """
    Download a ticket receipt image.
    Requires tickets.read permission.
    """
    # Get image record
    image = db.query(TicketImage).filter(TicketImage.id == image_id).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图片不存在"
        )
    
    # Check file exists
    storage_service = StorageService()
    if not storage_service.file_exists(image.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # Get absolute file path
    file_path = storage_service.get_file_path(image.file_path)
    
    # Return file response
    return FileResponse(
        path=str(file_path),
        media_type=image.mime_type,
        filename=image.file_name
    ) 