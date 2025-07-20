import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import alp.db.session as session_module

@pytest.fixture(autouse=True)
def use_temp_db(monkeypatch):
    """
    Fixture to redirect database operations to an in-memory SQLite for tests.
    This avoids persistent side effects and speeds up tests by using a fresh DB.
    """
    # Create an in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    # Monkeypatch the global engine and session factory in the session module
    monkeypatch.setattr(session_module, "engine", engine)
    monkeypatch.setattr(session_module, "SessionLocal", SessionLocal)
    # Recreate all tables in the in-memory database
    session_module.Base.metadata.create_all(engine)
    yield
    # Teardown: dispose the engine (database will be discarded as it's in memory)
    engine.dispose()
