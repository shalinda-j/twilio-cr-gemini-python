# database.py - SQLAlchemy engine + session. SQLite by default; swap DATABASE_URL for Postgres.
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/dashboard.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    if DATABASE_URL.startswith("sqlite:///") and "/data/" in DATABASE_URL:
        os.makedirs("data", exist_ok=True)
    from . import models  # noqa: F401  (register models)
    Base.metadata.create_all(bind=engine)
