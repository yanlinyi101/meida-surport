"""
Storage service for handling file uploads and management.
"""
import hashlib
import os
import secrets
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID
from fastapi import UploadFile, HTTPException, status

from ..core.config import settings


class StorageService:
    """Service for handling file storage operations."""
    
    def __init__(self):
        self.upload_root = settings.upload_root
        self.ticket_receipt_dir = settings.ticket_receipt_dir
        self.max_upload_bytes = settings.max_upload_bytes
        self.allowed_types = settings.allowed_image_types_list
    
    def validate_image_file(self, file: UploadFile) -> None:
        """
        Validate uploaded image file.
        
        Args:
            file: The uploaded file
            
        Raises:
            HTTPException: If validation fails
        """
        # Check file extension
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in self.allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型。允许的类型: {', '.join(self.allowed_types)}"
            )
        
        # Check MIME type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件必须是图片格式"
            )
        
        # Check file size (FastAPI doesn't provide size directly, so we'll check during read)
        # This will be checked in save_ticket_image method
    
    def generate_secure_filename(self, original_filename: str) -> str:
        """
        Generate a secure filename with random prefix.
        
        Args:
            original_filename: The original filename
            
        Returns:
            Secure filename with format: {random_prefix}_{timestamp}.{extension}
        """
        if not original_filename:
            raise ValueError("Original filename cannot be empty")
        
        # Extract extension
        parts = original_filename.rsplit('.', 1)
        if len(parts) != 2:
            raise ValueError("Filename must have an extension")
        
        ext = parts[1].lower()
        
        # Generate secure filename
        random_prefix = secrets.token_urlsafe(16)
        timestamp = int(os.path.getmtime(__file__) if os.path.exists(__file__) else 0)
        
        return f"{random_prefix}_{timestamp}.{ext}"
    
    def calculate_sha256(self, file_content: bytes) -> str:
        """
        Calculate SHA256 checksum of file content.
        
        Args:
            file_content: The file content as bytes
            
        Returns:
            SHA256 checksum as hexadecimal string
        """
        return hashlib.sha256(file_content).hexdigest()
    
    async def save_ticket_image(
        self, 
        ticket_id: UUID, 
        file: UploadFile
    ) -> Tuple[str, str, str, int, str]:
        """
        Save uploaded image for a ticket.
        
        Args:
            ticket_id: The ticket ID
            file: The uploaded file
            
        Returns:
            Tuple of (file_path, filename, mime_type, size_bytes, checksum_sha256)
            
        Raises:
            HTTPException: If save operation fails
        """
        # Validate file
        self.validate_image_file(file)
        
        # Read file content
        try:
            file_content = await file.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"读取文件失败: {str(e)}"
            )
        
        # Check file size
        if len(file_content) > self.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过限制 ({settings.max_upload_mb}MB)"
            )
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件不能为空"
            )
        
        # Generate secure filename
        try:
            secure_filename = self.generate_secure_filename(file.filename)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Create ticket directory
        ticket_dir = self.upload_root / self.ticket_receipt_dir / str(ticket_id)
        ticket_dir.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        file_path = ticket_dir / secure_filename
        
        # Save file
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"保存文件失败: {str(e)}"
            )
        
        # Calculate checksum
        checksum = self.calculate_sha256(file_content)
        
        # Return relative path from upload root
        relative_path = str(file_path.relative_to(self.upload_root))
        
        return (
            relative_path,
            secure_filename,
            file.content_type or "application/octet-stream",
            len(file_content),
            checksum
        )
    
    def get_file_path(self, relative_path: str) -> Path:
        """
        Get absolute file path from relative path.
        
        Args:
            relative_path: Relative path from upload root
            
        Returns:
            Absolute file path
        """
        return self.upload_root / relative_path
    
    def file_exists(self, relative_path: str) -> bool:
        """
        Check if file exists.
        
        Args:
            relative_path: Relative path from upload root
            
        Returns:
            True if file exists, False otherwise
        """
        return self.get_file_path(relative_path).exists()
    
    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file.
        
        Args:
            relative_path: Relative path from upload root
            
        Returns:
            True if file was deleted, False if file didn't exist
        """
        file_path = self.get_file_path(relative_path)
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception:
                return False
        return False
    
    def get_file_info(self, relative_path: str) -> Optional[dict]:
        """
        Get file information.
        
        Args:
            relative_path: Relative path from upload root
            
        Returns:
            Dictionary with file info or None if file doesn't exist
        """
        file_path = self.get_file_path(relative_path)
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        return {
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
        } 