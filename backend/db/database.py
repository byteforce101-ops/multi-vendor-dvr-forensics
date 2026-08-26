"""Database engine and session lifecycle."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import get_settings


def create_session_factory(database_url: str):
    options = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **options)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


engine, SessionLocal = create_session_factory(get_settings().database_url)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
