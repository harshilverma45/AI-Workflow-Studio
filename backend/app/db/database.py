from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def create_db_and_tables() -> None:
    """Create database tables for the current configuration."""
    from app.models import execution, iteration  # noqa: F401

    Base.metadata.create_all(bind=engine)
