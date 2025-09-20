"""
Authentication service for handling user login, logout, token refresh, and 2FA.
"""
import secrets
import base64
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from io import BytesIO
import pyotp
import qrcode
from sqlalchemy.orm import Session
from ..models.user import User, UserCreate, UserLogin, UserResponse
from ..models.session import SessionToken
from ..core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    verify_token, TokenError, hash_refresh_token, verify_refresh_token_hash,
    generate_random_token
)
from ..core.config import settings
from .rbac_service import RBACService
from .audit_service import AuditService


class AuthenticationError(Exception):
    """Authentication related errors."""
    pass


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.rbac_service = RBACService(db)
        self.audit_service = AuditService(db)
    
    def create_user(
        self,
        user_data: UserCreate,
        creator_user_id: Optional[int] = None,
        role_names: Optional[list[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            creator_user_id: ID of user creating this user (for audit)
            role_names: List of role names to assign
            ip_address: IP address for audit
            user_agent: User agent for audit
        
        Returns:
            Created user
        
        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing_user = self.db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create user
        user = User(
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            display_name=user_data.display_name
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Assign roles if provided
        if role_names:
            self.rbac_service.assign_roles_to_user(user, role_names)
        
        # Log user creation
        self.audit_service.log_user_created(
            created_user=user,
            creator_user_id=creator_user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return user
    
    def authenticate_user(
        self,
        login_data: UserLogin,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, str, str]:
        """
        Authenticate user and create session tokens.
        
        Args:
            login_data: Login credentials
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Tuple of (user, access_token, refresh_token)
        
        Raises:
            AuthenticationError: If authentication fails
        """
        # Get user by email
        user = self.db.query(User).filter(User.email == login_data.email).first()
        
        if not user:
            self.audit_service.log_action(
                action="user.login.failed",
                details={"reason": "user_not_found", "email": login_data.email},
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationError("Invalid credentials")
        
        # Check if user is active
        if not user.is_active:
            self.audit_service.log_action(
                action="user.login.failed",
                target_type="user",
                target_id=user.id,
                details={"reason": "user_inactive"},
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationError("Account is inactive")
        
        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            self.audit_service.log_user_login(
                user=user,
                success=False,
                details={"reason": "invalid_password"},
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise AuthenticationError("Invalid credentials")
        
        # Check 2FA if enabled
        if user.is_2fa_enabled:
            if not login_data.otp:
                raise AuthenticationError("2FA code required")
            
            if not self.verify_2fa_token(user, login_data.otp):
                self.audit_service.log_user_login(
                    user=user,
                    success=False,
                    details={"reason": "invalid_2fa"},
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise AuthenticationError("Invalid 2FA code")
        
        # Create tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        
        # Store refresh token in database
        self._store_refresh_token(user.id, refresh_token, ip_address, user_agent)
        
        # Log successful login
        self.audit_service.log_user_login(
            user=user,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return user, access_token, refresh_token
    
    def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Tuple of (new_access_token, new_refresh_token)
        
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            # Verify refresh token
            payload = verify_token(refresh_token, "refresh")
            user_id = int(payload.get("sub"))
            
            # Find session token in database
            session_token = self.db.query(SessionToken).filter(
                SessionToken.user_id == user_id,
                SessionToken.revoked == False
            ).first()
            
            if not session_token or not session_token.is_valid:
                raise AuthenticationError("Invalid refresh token")
            
            # Verify refresh token hash
            if not verify_refresh_token_hash(refresh_token, session_token.refresh_token_hash):
                raise AuthenticationError("Invalid refresh token")
            
            # Get user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            
            # Create new tokens
            new_access_token = create_access_token(str(user.id))
            new_refresh_token = create_refresh_token(str(user.id))
            
            # Update session token
            session_token.refresh_token_hash = hash_refresh_token(new_refresh_token)
            session_token.ip_address = ip_address
            session_token.user_agent = user_agent
            self.db.commit()
            
            return new_access_token, new_refresh_token
        
        except (TokenError, ValueError) as e:
            raise AuthenticationError("Invalid refresh token")
    
    def logout_user(
        self,
        user: User,
        refresh_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Logout user by revoking refresh token.
        
        Args:
            user: User to logout
            refresh_token: Refresh token to revoke
            ip_address: Client IP address
            user_agent: Client user agent
        """
        if refresh_token:
            # Revoke specific refresh token
            session_token = self.db.query(SessionToken).filter(
                SessionToken.user_id == user.id,
                SessionToken.revoked == False
            ).first()
            
            if session_token and verify_refresh_token_hash(refresh_token, session_token.refresh_token_hash):
                session_token.revoked = True
                session_token.revoked_at = datetime.utcnow()
                self.db.commit()
        else:
            # Revoke all refresh tokens for user
            self.db.query(SessionToken).filter(
                SessionToken.user_id == user.id,
                SessionToken.revoked == False
            ).update({
                "revoked": True,
                "revoked_at": datetime.utcnow()
            })
            self.db.commit()
        
        # Log logout
        self.audit_service.log_user_logout(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def get_user_response(self, user: User) -> UserResponse:
        """
        Get user response with roles and aggregated permissions.
        
        Args:
            user: User to get response for
        
        Returns:
            User response with roles and effective permissions
        """
        roles = self.rbac_service.get_user_roles(user)
        # Keep legacy permissions for backward compatibility
        permissions = list(self.rbac_service.get_user_permissions(user))
        # New aggregated permissions
        effective_permissions = list(self.rbac_service.aggregate_permissions(user))
        
        return UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            is_2fa_enabled=user.is_2fa_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=roles,
            permissions=permissions,  # Legacy field
            effective_permissions=effective_permissions  # New aggregated field
        )
    
    def setup_2fa(self, user: User) -> Dict[str, Any]:
        """
        Setup 2FA for user.
        
        Args:
            user: User to setup 2FA for
        
        Returns:
            Dictionary with secret, QR code, and backup codes
        """
        # Generate secret
        secret = pyotp.random_base32()
        
        # Create TOTP
        totp = pyotp.TOTP(secret)
        
        # Generate QR code
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.app_name
        )
        
        # Create QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Convert to base64
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Generate backup codes
        backup_codes = [generate_random_token(8) for _ in range(10)]
        
        # Store secret temporarily (not enabled until verified)
        user.twofa_secret = secret
        self.db.commit()
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "backup_codes": backup_codes
        }
    
    def verify_2fa_setup(
        self,
        user: User,
        otp: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Verify 2FA setup and enable it.
        
        Args:
            user: User to verify 2FA for
            otp: OTP code to verify
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            True if verification successful
        """
        if not user.twofa_secret:
            return False
        
        if self.verify_2fa_token(user, otp):
            user.is_2fa_enabled = True
            self.db.commit()
            
            # Log 2FA enabled
            self.audit_service.log_2fa_enabled(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return True
        
        return False
    
    def disable_2fa(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Disable 2FA for user.
        
        Args:
            user: User to disable 2FA for
            ip_address: Client IP address
            user_agent: Client user agent
        """
        user.is_2fa_enabled = False
        user.twofa_secret = None
        self.db.commit()
        
        # Log 2FA disabled
        self.audit_service.log_2fa_disabled(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def verify_2fa_token(self, user: User, otp: str) -> bool:
        """
        Verify 2FA token.
        
        Args:
            user: User to verify token for
            otp: OTP code to verify
        
        Returns:
            True if token is valid
        """
        if not user.twofa_secret:
            return False
        
        totp = pyotp.TOTP(user.twofa_secret)
        return totp.verify(otp, valid_window=1)  # Allow 30 seconds window
    
    def reset_password(
        self,
        email: str,
        token: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Reset user password using reset token.
        
        Args:
            email: User's email
            token: Password reset token
            new_password: New password
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            True if password was reset successfully
        
        Raises:
            AuthenticationError: If token is invalid or user not found
        """
        try:
            # Verify reset token
            payload = verify_token(token, "password_reset")
            token_email = payload.get("sub")
            
            if token_email != email:
                raise AuthenticationError("Invalid reset token")
            
            # Get user
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                raise AuthenticationError("User not found")
            
            # Update password
            user.password_hash = hash_password(new_password)
            self.db.commit()
            
            # Revoke all existing sessions
            self.db.query(SessionToken).filter(
                SessionToken.user_id == user.id,
                SessionToken.revoked == False
            ).update({
                "revoked": True,
                "revoked_at": datetime.utcnow()
            })
            self.db.commit()
            
            # Log password reset
            self.audit_service.log_password_reset(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return True
        
        except TokenError:
            raise AuthenticationError("Invalid or expired reset token")
    
    def _store_refresh_token(
        self,
        user_id: int,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SessionToken:
        """
        Store refresh token in database.
        
        Args:
            user_id: User ID
            refresh_token: Refresh token to store
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Created session token
        """
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(seconds=settings.jwt_refresh_ttl_seconds)
        
        # Hash the refresh token
        token_hash = hash_refresh_token(refresh_token)
        
        # Create session token
        session_token = SessionToken(
            user_id=user_id,
            refresh_token_hash=token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at
        )
        
        self.db.add(session_token)
        self.db.commit()
        self.db.refresh(session_token)
        
        return session_token 