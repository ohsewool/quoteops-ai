from __future__ import annotations

from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.domain.roles import UserRole
from backend.models.user import User


class UserRepository(Protocol):
    def get_by_username(self, username: str) -> User | None: ...

    def get_active_by_id(self, user_id: int) -> User | None: ...


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def get_active_by_id(self, user_id: int) -> User | None:
        return self.session.scalar(select(User).where(User.id == user_id, User.active.is_(True)))

    def user_count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(User)) or 0)

    def create(
        self,
        *,
        username: str,
        display_name: str,
        password_hash: str,
        role: UserRole,
    ) -> User:
        user = User(
            username=username,
            display_name=display_name,
            password_hash=password_hash,
            role=role,
            active=True,
        )
        self.session.add(user)
        self.session.flush()
        return user
