"""
Audit logging service for tracking user actions and system events.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from ..models.audit import AuditLog, AuditLogCreate, AuditLogResponse, AuditLogFilter
from ..models.user import User


class AuditService:
    """Service for managing audit logs."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(
        self,
        action: str,
        actor_user_id: Optional[int] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log an action to the audit trail.
        
        Args:
            action: Action performed (e.g., "user.login", "user.create")
            actor_user_id: ID of user performing the action (None for system actions)
            target_type: Type of target object (e.g., "user", "role")
            target_id: ID of target object
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional context information
        
        Returns:
            Created audit log entry
        """
        audit_log = AuditLog(
            action=action,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return audit_log
    
    def get_audit_logs(
        self,
        filters: AuditLogFilter
    ) -> tuple[List[AuditLogResponse], int]:
        """
        Get audit logs with filtering and pagination.
        
        Args:
            filters: Filter criteria and pagination parameters
        
        Returns:
            Tuple of (audit logs, total count)
        """
        query = self.db.query(AuditLog).options(
            joinedload(AuditLog.actor_user)
        )
        
        # Apply filters
        if filters.actor_user_id is not None:
            query = query.filter(AuditLog.actor_user_id == filters.actor_user_id)
        
        if filters.action:
            query = query.filter(AuditLog.action.ilike(f"%{filters.action}%"))
        
        if filters.target_type:
            query = query.filter(AuditLog.target_type == filters.target_type)
        
        if filters.target_id:
            query = query.filter(AuditLog.target_id == filters.target_id)
        
        if filters.date_from:
            query = query.filter(AuditLog.timestamp >= filters.date_from)
        
        if filters.date_to:
            query = query.filter(AuditLog.timestamp <= filters.date_to)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        audit_logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(filters.page_size).all()
        
        # Convert to response format
        response_logs = []
        for log in audit_logs:
            log_response = AuditLogResponse(
                id=log.id,
                timestamp=log.timestamp,
                actor_user_id=log.actor_user_id,
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                details=log.details,
                actor_email=log.actor_user.email if log.actor_user else None,
                actor_display_name=log.actor_user.display_name if log.actor_user else None
            )
            response_logs.append(log_response)
        
        return response_logs, total_count
    
    def log_user_login(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log user login attempt."""
        action = "user.login.success" if success else "user.login.failed"
        return self.log_action(
            action=action,
            actor_user_id=user.id if success else None,
            target_type="user",
            target_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {}
        )
    
    def log_user_logout(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log user logout."""
        return self.log_action(
            action="user.logout",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_user_created(
        self,
        created_user: User,
        creator_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log user creation."""
        return self.log_action(
            action="user.create",
            actor_user_id=creator_user_id,
            target_type="user",
            target_id=created_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": created_user.email, "display_name": created_user.display_name}
        )
    
    def log_user_updated(
        self,
        updated_user: User,
        updater_user_id: int,
        changes: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log user update."""
        return self.log_action(
            action="user.update",
            actor_user_id=updater_user_id,
            target_type="user",
            target_id=updated_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"changes": changes}
        )
    
    def log_password_reset(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log password reset."""
        return self.log_action(
            action="user.password.reset",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_2fa_enabled(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log 2FA enabled."""
        return self.log_action(
            action="user.2fa.enabled",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_2fa_disabled(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log 2FA disabled."""
        return self.log_action(
            action="user.2fa.disabled",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        ) 