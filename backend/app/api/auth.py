"""
Authentication API routes.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from ..db.session import get_db
from ..core.deps import (
    get_current_user, get_current_active_user, get_current_user_optional,
    get_client_ip, get_user_agent
)
from ..core.config import settings
from ..models.user import (
    UserLogin, UserRegister, UserResponse, PasswordReset, PasswordForgot,
    TwoFASetup, TwoFAVerify, ChangePassword
)
from ..services.auth_service import AuthService, AuthenticationError
from ..services.email_service import EmailService

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=dict)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def login(
    request: Request,
    response: Response,
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    User login endpoint.
    Sets HttpOnly cookies for access and refresh tokens.
    """
    try:
        auth_service = AuthService(db)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        user, access_token, refresh_token = auth_service.authenticate_user(
            login_data, ip_address, user_agent
        )
        
        # Set cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.jwt_access_ttl_seconds
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.jwt_refresh_ttl_seconds
        )
        
        # Return user info
        user_response = auth_service.get_user_response(user)
        
        return {
            "ok": True,
            "user": user_response.dict()
        }
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    current_user: Optional[object] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    User logout endpoint.
    Clears cookies and revokes refresh token.
    """
    if current_user:
        auth_service = AuthService(db)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        auth_service.logout_user(
            current_user, refresh_token, ip_address, user_agent
        )
    
    # Clear cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"ok": True, "message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )
    
    try:
        auth_service = AuthService(db)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        new_access_token, new_refresh_token = auth_service.refresh_access_token(
            refresh_token, ip_address, user_agent
        )
        
        # Set new cookies
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.jwt_access_ttl_seconds
        )
        
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.jwt_refresh_ttl_seconds
        )
        
        return {"ok": True, "message": "Token refreshed successfully"}
    
    except AuthenticationError as e:
        # Clear invalid cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: object = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information with roles and permissions.
    """
    auth_service = AuthService(db)
    return auth_service.get_user_response(current_user)


@router.post("/register", response_model=UserResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    User registration endpoint (only if enabled).
    """
    if not settings.allow_self_register:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is disabled"
        )
    
    try:
        auth_service = AuthService(db)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        user = auth_service.create_user(
            user_data, 
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return auth_service.get_user_response(user)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/password/forgot")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def forgot_password(
    request: Request,
    forgot_data: PasswordForgot,
    db: Session = Depends(get_db)
):
    """
    Send password reset email.
    """
    from ..models.user import User
    
    # Find user (don't reveal if user exists or not)
    user = db.query(User).filter(User.email == forgot_data.email).first()
    
    if user and user.is_active:
        email_service = EmailService()
        success, reset_token = await email_service.send_password_reset_email(
            user.email, user.display_name
        )
        
        if not success:
            # Log email failure but don't expose to user
            pass
    
    # Always return success to prevent email enumeration
    return {
        "ok": True,
        "message": "If the email exists, a password reset link has been sent"
    }


@router.post("/password/reset")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def reset_password(
    request: Request,
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset password using reset token.
    """
    try:
        auth_service = AuthService(db)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        # Extract email from token for validation
        from ..core.security import verify_token
        payload = verify_token(reset_data.token, "password_reset")
        email = payload.get("sub")
        
        success = auth_service.reset_password(
            email, reset_data.token, reset_data.new_password,
            ip_address, user_agent
        )
        
        if success:
            return {"ok": True, "message": "Password reset successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reset password"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


@router.post("/2fa/setup", response_model=TwoFASetup)
async def setup_2fa(
    current_user: object = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Setup 2FA for current user.
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )
    
    auth_service = AuthService(db)
    setup_data = auth_service.setup_2fa(current_user)
    
    return TwoFASetup(**setup_data)


@router.post("/2fa/verify")
async def verify_2fa_setup(
    request: Request,
    verify_data: TwoFAVerify,
    current_user: object = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verify and enable 2FA.
    """
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )
    
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    if auth_service.verify_2fa_setup(current_user, verify_data.otp, ip_address, user_agent):
        return {"ok": True, "message": "2FA enabled successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )


@router.post("/2fa/disable")
async def disable_2fa(
    request: Request,
    current_user: object = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disable 2FA for current user.
    """
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )
    
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    auth_service.disable_2fa(current_user, ip_address, user_agent)
    
    # Send notification email
    email_service = EmailService()
    await email_service.send_2fa_disabled_notification(
        current_user.email, current_user.display_name
    )
    
    return {"ok": True, "message": "2FA disabled successfully"}


@router.post("/password/change")
async def change_password(
    request: Request,
    password_data: ChangePassword,
    current_user: object = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    """
    from ..core.security import verify_password, hash_password
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    db.commit()
    
    # Log password change
    auth_service = AuthService(db)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    auth_service.audit_service.log_action(
        action="user.password.change",
        actor_user_id=current_user.id,
        target_type="user",
        target_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return {"ok": True, "message": "Password changed successfully"}


# Rate limit exception handler will be added to the main app 