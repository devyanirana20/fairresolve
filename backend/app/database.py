"""
Database engine + session setup.

Defaults to a local SQLite file for zero-setup development. To run against
Postgres instead, set the DATABASE_URL environment variable, e.g.:

    export DATABASE_URL="postgresql://user:pass@localhost:5432/fairresolve"

No model or business-logic code needs to change to make that switch --
that's the point of using SQLAlchemy's ORM layer rather than raw SQLite calls.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./fairresolve.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import Base
    Base.metadata.create_all(bind=engine)
