"""
FastAPI dependencies for authentication, authorization, and database access.
"""
from typing import Optional, List, Callable, Union
from functools import wraps
from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..models.user import User
from ..models.role import Role, Permission
from ..services.rbac_service import RBACService
from .security import verify_token, TokenError
from .config import settings


class AuthError(HTTPException):
    """Authentication error exception."""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class PermissionError(HTTPException):
    """Permission error exception."""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_current_user_from_token(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from access token cookie.
    Returns None if no token or invalid token.
    """
    if not access_token:
        return None
    
    try:
        payload = verify_token(access_token, "access")
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            return None
        
        return user
    
    except (TokenError, ValueError):
        return None


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_from_token)
) -> User:
    """Get current authenticated user. Raises 401 if not authenticated."""
    if not user:
        raise AuthError("Authentication required")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user. Raises 401 if not active."""
    if not current_user.is_active:
        raise AuthError("Inactive user")
    return current_user


def require_permissions(permissions: List[str]):
    """
    Dependency factory to require specific permissions.
    
    Args:
        permissions: List of required permission codes
    
    Returns:
        FastAPI dependency function
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        rbac_service = RBACService(db)
        
        # Check if user has required permissions
        if not rbac_service.user_has_permissions(current_user, permissions):
            raise PermissionError(
                f"Missing required permissions: {', '.join(permissions)}"
            )
        
        return current_user
    
    return permission_checker


def require_role(role_name: str):
    """
    Dependency factory to require a specific role.
    
    Args:
        role_name: Required role name
    
    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        rbac_service = RBACService(db)
        
        if not rbac_service.user_has_role(current_user, role_name):
            raise PermissionError(f"Role '{role_name}' required")
        
        return current_user
    
    return role_checker


async def get_current_user_optional(
    user: Optional[User] = Depends(get_current_user_from_token)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    return user


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded IP first (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP (some proxies use this)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request."""
    return request.headers.get("User-Agent", "unknown")


def require_perms(*codes: str, mode: str = "all") -> Callable:
    """
    Create a FastAPI dependency that requires specific permissions.
    
    Args:
        *codes: Permission codes to require
        mode: "all" (user must have all permissions) or "any" (user must have at least one)
    
    Returns:
        FastAPI dependency function
    """
    def permission_dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        if not current_user:
            raise AuthError("Authentication required")
        
        rbac_service = RBACService(db)
        user_permissions = rbac_service.aggregate_permissions(current_user)
        
        if mode == "all":
            # User must have all required permissions
            if not all(code in user_permissions for code in codes):
                missing = [code for code in codes if code not in user_permissions]
                raise PermissionError(f"Missing required permissions: {missing}")
        elif mode == "any":
            # User must have at least one required permission
            if not any(code in user_permissions for code in codes):
                raise PermissionError(f"Missing any of required permissions: {list(codes)}")
        else:
            raise ValueError("Mode must be 'all' or 'any'")
        
        return current_user
    
    return permission_dependency


def require_permission(code: str) -> Callable:
    """
    Create a FastAPI dependency that requires a single permission.
    
    Args:
        code: Permission code to require
    
    Returns:
        FastAPI dependency function
    """
    return require_perms(code, mode="all")


# Permission-based dependencies
require_users_read = require_permission("users.read")
require_users_write = require_permission("users.write")
require_roles_read = require_permission("roles.read")
require_roles_write = require_permission("roles.write")
require_permissions_read = require_permission("permissions.read")
require_audit_read = require_permission("audit.read")

# Common permission combinations
require_admin = require_role("admin")
require_ops_manager = require_perms("users.read", "tickets.read", mode="all")
require_agent = require_perms("tickets.read", "tickets.write", mode="all")
require_viewer = require_permissions(["tickets.read"]) 