"""Repository for User persistence operations in SQLite."""

from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.persistence import User


class UserRepository:
    """Handles CRUD persistence operations for User accounts."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        """Fetch user by primary key."""
        stmt = select(User).where(User.id == user_id)
        return self.db.execute(stmt).scalars().first()

    def get_by_username(self, username: str) -> User | None:
        """Fetch user by unique username."""
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalars().first()

    def create(self, username: str, password_hash: str) -> User:
        """Create and persist a new user record."""
        user = User(username=username, password_hash=password_hash)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
