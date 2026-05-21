from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings


def build_engine(database_url: str | None = None):
    settings = get_settings()
    return create_engine(
        database_url or settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

