from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class User(Base, TimestampMixin):
    """
    User model - represents a user account.
    
    Users can authenticate and access protected resources.
    """
    __tablename__ = "users"
    
    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, username='{self.username}', email='{self.email}')>"