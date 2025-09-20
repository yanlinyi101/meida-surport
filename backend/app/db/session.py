"""
Database session management.
"""
from typing import Generator
from sqlalchemy.orm import Session
from .base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    Ensures proper cleanup after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 