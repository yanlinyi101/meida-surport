"""
Models package initialization.
"""
from ..db.base import Base

# Import all models to ensure they are registered with SQLAlchemy
from . import user, role, session, audit, ticket, technician, ticket_image

__all__ = [
    "Base",
    "user",
    "role", 
    "session",
    "audit",
    "ticket",
    "technician",
    "ticket_image"
] 