from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import get_database_type, get_settings


def get_engine_kwargs(database_url: str) -> dict:
    database_type = get_database_type(database_url)
    if database_type == "sqlite":
        return {"connect_args": {"check_same_thread": False}}
    if database_type == "postgresql":
        return {"pool_pre_ping": True}
    return {}


settings = get_settings()
engine = create_engine(settings.database_url, **get_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def create_db_and_tables() -> None:
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def database_connection_ok() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
