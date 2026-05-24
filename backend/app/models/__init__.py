"""SQLAlchemy ORM models.

Owns DB schema. KHÔNG chứa business logic — chỉ field/relationship + simple
validators. Naming: PascalCase singular class, snake_case plural table.
"""

from app.models.base import Base
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import (
    Group,
    RevokedToken,
    User,
    UserRole,
    UserStatus,
    user_groups_table,
)

__all__ = [
    "Base",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "Group",
    "RevokedToken",
    "User",
    "UserRole",
    "UserStatus",
    "user_groups_table",
]
