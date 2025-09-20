"""
Admin API routes for user and role management.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..db.session import get_db
from ..core.deps import (
    get_current_active_user, require_admin, get_client_ip, get_user_agent,
    require_users_read, require_users_write, require_roles_read, require_roles_write,
    require_permissions_read, require_audit_read, require_permissions
)
from ..models.user import User, UserCreate, UserUpdate, UserResponse
from ..models.role import RoleCreate, RoleUpdate, RoleResponse, PermissionResponse, UserRoleAssignment
from ..models.audit import AuditLogFilter, AuditLogResponse
from ..services.auth_service import AuthService
from ..services.rbac_service import RBACService
from ..services.audit_service import AuditService
from ..services.email_service import EmailService
from ..core.security import generate_random_token

# Create router
router = APIRouter(prefix="/admin", tags=["Admin"])


# User Management
@router.get("/users", response_model=dict)
async def get_users(
    request: Request,
    query: Optional[str] = Query(None, description="Search query for email or display name"),
    role: Optional[str] = Query(None, description="Filter by role name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_users_read),
    db: Session = Depends(get_db)
):
    """
    Get users with filtering and pagination.
    """
    # Build query
    users_query = db.query(User)
    
    # Apply text search
    if query:
        users_query = users_query.filter(
            or_(
                User.email.ilike(f"%{query}%"),
                User.display_name.ilike(f"%{query}%")
            )
        )
    
    # Apply role filter
    if role:
        from ..models.role import Role
        users_query = users_query.join(User.roles).filter(Role.name == role)
    
    # Get total count
    total_count = users_query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    users = users_query.offset(offset).limit(page_size).all()
    
    # Convert to response format
    auth_service = AuthService(db)
    user_responses = [auth_service.get_user_response(user) for user in users]
    
    return {
        "users": [user.dict() for user in user_responses],
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: Request,
    user_data: UserCreate,
    send_welcome_email: bool = Query(False, description="Send welcome email to new user"),
    role_names: Optional[List[str]] = Query(None, description="Role names to assign"),
    current_user: User = Depends(require_permissions(["users.write"])),
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    """
    try:
        auth_service = AuthService(db)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        # Generate temporary password if sending welcome email
        temp_password = None
        if send_welcome_email:
            temp_password = generate_random_token(12)
            user_data.password = temp_password
        
        new_user = auth_service.create_user(
            user_data,
            creator_user_id=current_user.id,
            role_names=role_names,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Send welcome email if requested
        if send_welcome_email:
            email_service = EmailService()
            await email_service.send_welcome_email(
                new_user.email,
                new_user.display_name,
                temp_password
            )
        
        return auth_service.get_user_response(new_user)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permissions(["users.read"])),
    db: Session = Depends(get_db)
):
    """
    Get user by ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    auth_service = AuthService(db)
    return auth_service.get_user_response(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: Request,
    user_data: UserUpdate,
    current_user: User = Depends(require_permissions(["users.write"])),
    db: Session = Depends(get_db)
):
    """
    Update user information.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Track changes for audit
    changes = {}
    
    if user_data.display_name is not None:
        old_name = user.display_name
        user.display_name = user_data.display_name
        changes["display_name"] = {"old": old_name, "new": user_data.display_name}
    
    if user_data.is_active is not None:
        old_active = user.is_active
        user.is_active = user_data.is_active
        changes["is_active"] = {"old": old_active, "new": user_data.is_active}
    
    db.commit()
    db.refresh(user)
    
    # Log changes
    if changes:
        audit_service = AuditService(db)
        audit_service.log_user_updated(
            updated_user=user,
            updater_user_id=current_user.id,
            changes=changes,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
    
    auth_service = AuthService(db)
    return auth_service.get_user_response(user)


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_permissions(["users.write"])),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    user.is_active = False
    db.commit()
    
    # Revoke all sessions
    from ..models.session import SessionToken
    from datetime import datetime
    db.query(SessionToken).filter(
        SessionToken.user_id == user_id,
        SessionToken.revoked == False
    ).update({
        "revoked": True,
        "revoked_at": datetime.utcnow()
    })
    db.commit()
    
    # Log action
    audit_service = AuditService(db)
    audit_service.log_action(
        action="user.deactivate",
        actor_user_id=current_user.id,
        target_type="user",
        target_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {"ok": True, "message": "User deactivated successfully"}


@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_permissions(["users.write"])),
    db: Session = Depends(get_db)
):
    """
    Reactivate a user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    # Log action
    audit_service = AuditService(db)
    audit_service.log_action(
        action="user.reactivate",
        actor_user_id=current_user.id,
        target_type="user",
        target_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    
    return {"ok": True, "message": "User reactivated successfully"}


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_permissions(["users.write"])),
    db: Session = Depends(get_db)
):
    """
    Send password reset email to user (admin action).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Send password reset email
    email_service = EmailService()
    success, reset_token = await email_service.send_password_reset_email(
        user.email, user.display_name
    )
    
    if success:
        # Log action
        audit_service = AuditService(db)
        audit_service.log_action(
            action="user.password.reset.admin",
            actor_user_id=current_user.id,
            target_type="user",
            target_id=user_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        return {"ok": True, "message": "Password reset email sent"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email"
        )


@router.post("/users/{user_id}/roles")
async def assign_user_roles(
    user_id: int,
    request: Request,
    role_assignment: UserRoleAssignment,
    current_user: User = Depends(require_permissions(["users.write"])),
    db: Session = Depends(get_db)
):
    """
    Assign roles to a user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    rbac_service = RBACService(db)
    old_roles = rbac_service.get_user_roles(user)
    assigned_roles = rbac_service.assign_roles_to_user(user, role_assignment.role_names)
    
    # Log action
    audit_service = AuditService(db)
    audit_service.log_action(
        action="user.roles.assign",
        actor_user_id=current_user.id,
        target_type="user",
        target_id=user_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"old_roles": old_roles, "new_roles": assigned_roles}
    )
    
    return {
        "ok": True,
        "message": "Roles assigned successfully",
        "assigned_roles": assigned_roles
    }


# Role Management
@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    current_user: User = Depends(require_permissions(["roles.read"])),
    db: Session = Depends(get_db)
):
    """
    Get all roles with permissions and user counts.
    """
    rbac_service = RBACService(db)
    return rbac_service.get_all_roles()


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    request: Request,
    role_data: RoleCreate,
    current_user: User = Depends(require_permissions(["roles.write"])),
    db: Session = Depends(get_db)
):
    """
    Create a new role.
    """
    try:
        rbac_service = RBACService(db)
        role = rbac_service.create_role(role_data)
        
        # Log action
        audit_service = AuditService(db)
        audit_service.log_action(
            action="role.create",
            actor_user_id=current_user.id,
            target_type="role",
            target_id=role.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={"name": role.name, "permissions": role_data.permission_codes}
        )
        
        return rbac_service.get_role(role.id)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(require_permissions(["roles.read"])),
    db: Session = Depends(get_db)
):
    """
    Get role by ID.
    """
    rbac_service = RBACService(db)
    role = rbac_service.get_role(role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return role


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    request: Request,
    role_data: RoleUpdate,
    current_user: User = Depends(require_permissions(["roles.write"])),
    db: Session = Depends(get_db)
):
    """
    Update role.
    """
    rbac_service = RBACService(db)
    
    # Get old role data for audit
    old_role = rbac_service.get_role(role_id)
    if not old_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    updated_role = rbac_service.update_role(role_id, role_data)
    if not updated_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Log action
    audit_service = AuditService(db)
    changes = {}
    if role_data.name is not None:
        changes["name"] = {"old": old_role.name, "new": role_data.name}
    if role_data.description is not None:
        changes["description"] = {"old": old_role.description, "new": role_data.description}
    if role_data.permission_codes is not None:
        old_permissions = [p.code for p in old_role.permissions]
        changes["permissions"] = {"old": old_permissions, "new": role_data.permission_codes}
    
    audit_service.log_action(
        action="role.update",
        actor_user_id=current_user.id,
        target_type="role",
        target_id=role_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"changes": changes}
    )
    
    return rbac_service.get_role(role_id)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    request: Request,
    current_user: User = Depends(require_permissions(["roles.write"])),
    db: Session = Depends(get_db)
):
    """
    Delete role.
    """
    rbac_service = RBACService(db)
    
    # Get role data for audit before deletion
    role = rbac_service.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    success = rbac_service.delete_role(role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Log action
    audit_service = AuditService(db)
    audit_service.log_action(
        action="role.delete",
        actor_user_id=current_user.id,
        target_type="role",
        target_id=role_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"name": role.name}
    )
    
    return {"ok": True, "message": "Role deleted successfully"}


@router.get("/permissions", response_model=List[PermissionResponse])
async def get_permissions(
    current_user: User = Depends(require_permissions(["roles.read"])),
    db: Session = Depends(get_db)
):
    """
    Get all available permissions.
    """
    rbac_service = RBACService(db)
    return rbac_service.get_all_permissions()


# Audit Logs
@router.get("/audit-logs", response_model=dict)
async def get_audit_logs(
    actor_user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permissions(["audit.read"])),
    db: Session = Depends(get_db)
):
    """
    Get audit logs with filtering and pagination.
    """
    from datetime import datetime
    
    # Parse date filters
    parsed_date_from = None
    parsed_date_to = None
    
    try:
        if date_from:
            parsed_date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        if date_to:
            parsed_date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
        )
    
    filters = AuditLogFilter(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        page=page,
        page_size=page_size
    )
    
    audit_service = AuditService(db)
    audit_logs, total_count = audit_service.get_audit_logs(filters)
    
    return {
        "logs": [log.dict() for log in audit_logs],
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }


# RBAC v2 API Routes

@router.get("/permissions", response_model=List[dict])
async def get_permissions(
    current_user: User = Depends(require_permissions_read),
    db: Session = Depends(get_db)
):
    """
    Get all permissions organized by category.
    """
    rbac_service = RBACService(db)
    permissions_by_category = rbac_service.get_permissions_by_category()
    
    # Convert to list format expected by frontend
    result = []
    for category, permissions in permissions_by_category.items():
        result.append({
            "category": category,
            "items": permissions
        })
    
    return result


@router.get("/roles", response_model=dict)
async def get_roles(
    q: Optional[str] = Query(None, description="Search query for role name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(require_roles_read),
    db: Session = Depends(get_db)
):
    """
    Get roles with pagination and optional search.
    """
    rbac_service = RBACService(db)
    return rbac_service.get_roles_paginated(q, page, page_size)


@router.post("/roles", response_model=dict)
async def create_role(
    role_data: RoleCreate,
    request: Request,
    current_user: User = Depends(require_roles_write),
    db: Session = Depends(get_db)
):
    """
    Create a new role with permissions.
    """
    rbac_service = RBACService(db)
    
    # Validate permission codes
    if not rbac_service.validate_permission_codes(role_data.permission_codes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more permission codes are invalid"
        )
    
    # Check if role name already exists
    existing_role = db.query(Role).filter(Role.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role with name '{role_data.name}' already exists"
        )
    
    # Create role
    role = rbac_service.create_role(role_data)
    
    # Log audit
    audit_service = AuditService(db)
    audit_service.log_action(
        actor_user=current_user,
        action="role.create",
        target_type="role",
        target_id=role.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={
            "role_name": role.name,
            "permissions": role_data.permission_codes
        }
    )
    
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "created_at": role.created_at,
        "updated_at": role.updated_at
    }


@router.get("/roles/{role_id}", response_model=dict)
async def get_role(
    role_id: int,
    current_user: User = Depends(require_roles_read),
    db: Session = Depends(get_db)
):
    """
    Get a role by ID with permissions.
    """
    rbac_service = RBACService(db)
    role_response = rbac_service.get_role(role_id)
    
    if not role_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return {
        "id": role_response.id,
        "name": role_response.name,
        "description": role_response.description,
        "is_system": role_response.is_system,
        "permissions": [perm.code for perm in role_response.permissions],
        "created_at": role_response.created_at,
        "updated_at": role_response.updated_at
    }


@router.patch("/roles/{role_id}", response_model=dict)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    request: Request,
    current_user: User = Depends(require_roles_write),
    db: Session = Depends(get_db)
):
    """
    Update a role with system role protection.
    """
    rbac_service = RBACService(db)
    
    # Get original role for audit logging
    original_role = rbac_service.get_role(role_id)
    if not original_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Update role
    try:
        updated_role = rbac_service.update_role(role_id, role_data)
        if not updated_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
    except HTTPException:
        raise  # Re-raise HTTPExceptions from the service
    
    # Log audit
    audit_service = AuditService(db)
    changes = {}
    if role_data.name is not None and role_data.name != original_role.name:
        changes["name"] = {"from": original_role.name, "to": role_data.name}
    if role_data.description is not None and role_data.description != original_role.description:
        changes["description"] = {"from": original_role.description, "to": role_data.description}
    if role_data.permission_codes is not None:
        original_perms = [p.code for p in original_role.permissions]
        changes["permissions"] = {"from": original_perms, "to": role_data.permission_codes}
    
    audit_service.log_action(
        actor_user=current_user,
        action="role.update",
        target_type="role",
        target_id=role_id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        details=changes
    )
    
    return {
        "id": updated_role.id,
        "name": updated_role.name,
        "description": updated_role.description,
        "is_system": updated_role.is_system,
        "updated_at": updated_role.updated_at
    }


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    request: Request,
    current_user: User = Depends(require_roles_write),
    db: Session = Depends(get_db)
):
    """
    Delete a role with protection for system roles and roles with users.
    """
    rbac_service = RBACService(db)
    
    # Get role for audit logging
    role_to_delete = rbac_service.get_role(role_id)
    if not role_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Delete role
    try:
        success = rbac_service.delete_role(role_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
    except HTTPException:
        raise  # Re-raise HTTPExceptions from the service
    
    # Log audit
    audit_service = AuditService(db)
    audit_service.log_action(
        actor_user=current_user,
        action="role.delete",
        target_type="role",
        target_id=role_id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={
            "role_name": role_to_delete.name,
            "permissions_count": role_to_delete.permissions_count
        }
    )
    
    return {"ok": True}


@router.post("/users/{user_id}/roles")
async def assign_roles_to_user(
    user_id: int,
    assignment: UserRoleAssignment,
    request: Request,
    current_user: User = Depends(require_users_write),
    db: Session = Depends(get_db)
):
    """
    Assign roles to a user (replaces existing roles).
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get original roles for audit
    original_role_ids = [role.id for role in user.roles]
    
    # Assign roles
    rbac_service = RBACService(db)
    try:
        success = rbac_service.assign_roles_to_user(user_id, assignment.role_ids)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except HTTPException:
        raise  # Re-raise HTTPExceptions from the service
    
    # Log audit
    audit_service = AuditService(db)
    audit_service.log_action(
        actor_user=current_user,
        action="user.roles.update",
        target_type="user",
        target_id=user_id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={
            "user_email": user.email,
            "roles": {
                "from": original_role_ids,
                "to": assignment.role_ids
            }
        }
    )
    
    return {"ok": True} 