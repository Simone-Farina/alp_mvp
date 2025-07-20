from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alp.db.models import Base

from contextlib import contextmanager

DATA_DIR = Path.home() / '.alp'
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / 'mvp.db'

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.

    Usage:
        with session_scope() as db:
            db.add(obj)
            ...
    Commits on success, rolls back on exception
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()