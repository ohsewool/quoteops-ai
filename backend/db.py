"""PostgreSQL-only SQLAlchemy session lifecycle for V2."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import Settings

SessionFactory = Callable[[], Session]


def build_engine(settings: Settings) -> Engine:
    """Create an engine without connecting or creating schema at import time."""

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


def build_session_factory(settings: Settings) -> sessionmaker[Session]:
    return sessionmaker(
        bind=build_engine(settings),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
