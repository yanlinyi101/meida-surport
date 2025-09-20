"""
Security utilities for authentication and authorization.
Handles password hashing, JWT token generation/validation, and security helpers.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
from .config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityError(Exception):
    """Base security exception."""
    pass


class TokenError(SecurityError):
    """Token-related security exception."""
    pass


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        # 尝试bcrypt验证
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # 回退到简单SHA256验证（紧急情况）
        import hashlib
        simple_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        return simple_hash == hashed_password


def generate_random_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Token expiration time
        additional_claims: Additional claims to include
    
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.jwt_access_ttl_seconds)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Token expiration time
        jti: JWT ID (unique identifier)
    
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.jwt_refresh_ttl_seconds)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    if jti:
        to_encode["jti"] = jti
    
    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )


def create_password_reset_token(email: str) -> str:
    """Create a one-time password reset token."""
    expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    
    to_encode = {
        "sub": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "password_reset",
        "jti": generate_random_token(16)  # Unique ID to prevent reuse
    }
    
    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        token_type: Expected token type
    
    Returns:
        Decoded token payload
        
    Raises:
        TokenError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            raise TokenError(f"Invalid token type. Expected {token_type}")
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise TokenError(f"Invalid token: {str(e)}")


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return generate_random_token(32)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage."""
    return hash_password(token)


def verify_refresh_token_hash(token: str, token_hash: str) -> bool:
    """Verify a refresh token against its hash."""
    return verify_password(token, token_hash) 