from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.db_uri, pool_size=5, max_overflow=10, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(_get_db)]
