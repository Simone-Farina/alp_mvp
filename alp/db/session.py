from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from alp.db.models import Base

# Determine database file path (allow override via environment variable for testing)
_default_db_path = Path.home() / ".alp" / "mvp.db"
db_path = Path(os.getenv("ALP_DB_PATH", _default_db_path))
db_path.parent.mkdir(exist_ok=True)

engine = create_engine(f"sqlite:///{db_path}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# Create all tables in the database
Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Generator[Session, Any, None]:
    """
    Provide a transactional scope around a series of operations.

    Usage:
        with session_scope() as db:
            db.add(obj)
            ...  # Perform DB operations
        (Commits on success, rolls back on exception)
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
